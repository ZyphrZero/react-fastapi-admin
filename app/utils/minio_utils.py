#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import hashlib
import os
import io
import re
from datetime import timedelta
from pathlib import Path
from typing import Optional

from minio import Minio
from minio.error import S3Error
from urllib3 import PoolManager
from urllib3.exceptions import HTTPError as Urllib3HTTPError
from urllib3.util.timeout import Timeout

from app.core.exceptions import CustomHTTPException
from app.models.enums import StrEnum
from app.settings import settings  # 供 resolve_bucket_name 的 settings 参数缺省时回退（参数名遮蔽模块级 settings）
from app.settings import settings as _default_settings
from app.utils.log_control import logger

"""
@Project ： 
@File    ：minio_utils.py.py
@IDE     ：PyCharm 
@Author  ：bixuejun(bxjgood@163.com)
@Date    ：2025/12/14 17:02 
@explain : MinIO 客户端工具类封装
基于 app.settings.config 中的 MINIO_* 配置，对常用的 MinIO 操作
（创建桶、上传文件、上传字节流、生成预签名访问 URL 等）进行简单封装。
"""


# =====================================================================
# CWA 存储基础件（存储基础件）：桶枚举、对象键校验、业务异常、异步门面
# =====================================================================

OBJECT_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9/._-]*\Z")

# 网络层异常族（台账②：MinIO 不可达/超时等非 S3Error 异常统一转译
# 503 STORAGE_UNAVAILABLE，防 urllib3 MaxRetryError 长挂后裸 500）
STORAGE_NETWORK_ERRORS = (Urllib3HTTPError, ConnectionError, TimeoutError)

# HTTP 读超时（秒，模块常量）：50MB 对象流式传输单次 socket 读的宽松上限；
# 连接超时用 settings.MINIO_CONNECTION_TIMEOUT（不可达快速失败，台账②）
STORAGE_HTTP_READ_TIMEOUT_SECONDS = 60.0


class StorageError(CustomHTTPException):
    """
    存储层业务异常基类（data 携带 STORAGE_ 错误码）

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-24 14:39:07

    Args:
        status_code: HTTP 语义状态码
        detail: 中文用户可读消息
        error_code: STORAGE_ 错误码
    """

    def __init__(self, status_code: int, detail: str, error_code: str, **extra):
        super().__init__(status_code=status_code, detail=detail, data={"error_code": error_code, **extra})
        self.error_code = error_code


class ObjectExistsError(StorageError):
    """immutable 对象已存在（409 STORAGE_OBJECT_EXISTS）。"""

    def __init__(self, bucket: str, object_key: str):
        super().__init__(
            status_code=409,
            detail=f"对象已存在且不可变: {bucket}/{object_key}",
            error_code="STORAGE_OBJECT_EXISTS",
            bucket=bucket,
            object_key=object_key,
        )


class StorageObjectNotFoundError(StorageError):
    """对象不存在（404 STORAGE_OBJECT_NOT_FOUND）。"""

    def __init__(self, bucket: str, object_key: str):
        super().__init__(
            status_code=404,
            detail=f"对象不存在: {bucket}/{object_key}",
            error_code="STORAGE_OBJECT_NOT_FOUND",
            bucket=bucket,
            object_key=object_key,
        )


class StorageUnavailableError(StorageError):
    """MinIO 不可达（503 STORAGE_UNAVAILABLE）。"""

    def __init__(self, reason: str = "对象存储不可用"):
        super().__init__(status_code=503, detail=reason, error_code="STORAGE_UNAVAILABLE")


class StorageBucket(StrEnum):
    """
    通用桶枚举（实际桶名经 resolve_bucket_name 读 settings 可覆盖；业务项目可扩展成员）

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-24 14:39:07  # 北京时间 UTC+8
    """

    DEFAULT = "app"
    TMP = "app-tmp"


def validate_object_key(object_key: str) -> str:
    """
    校验桶内对象键格式：仅 [a-z0-9/._-]、不以 / 开头结尾、不含连续 //、非纯点段

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-24 14:39:07

    Args:
        object_key: 桶内键（不含 bucket 段）

    Returns:
        str: 校验通过的原文

    Raises:
        StorageError: 422 STORAGE_OBJECT_KEY_INVALID
    """
    if (
        not object_key
        or not OBJECT_KEY_PATTERN.match(object_key)
        or object_key.startswith("/")
        or object_key.endswith("/")
        or "//" in object_key
        or any(part.strip(".") == "" for part in object_key.split("/"))
    ):
        raise StorageError(
            status_code=422,
            detail=f"对象键包含非法字符或格式（只允许小写字母/数字/点/横线/下划线/斜杠）: {object_key!r}",
            error_code="STORAGE_OBJECT_KEY_INVALID",
            object_key=object_key,
        )
    return object_key


def resolve_bucket_name(bucket: StorageBucket, settings=None) -> str:
    """
    解析桶的实际桶名（settings 桶键可覆盖枚举默认值）

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-24 14:39:07

    Args:
        bucket: 桶枚举成员
        settings: 可选 Settings 实例（默认用全局 settings）

    Returns:
        str: 实际桶名
    """
    if settings is None:
        settings = _default_settings  # 参数名遮蔽模块级 settings，经模块级别名取全局配置

    mapping = {
        StorageBucket.DEFAULT: settings.MINIO_BUCKET_NAME,
        StorageBucket.TMP: settings.MINIO_BUCKET_TMP,
    }
    return mapping[bucket]


class MinioClient:
    """
    MinIO 客户端封装类
    使用 settings 中的 MINIO 配置创建客户端，并提供常用操作方法。
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        secure: Optional[bool] = None,
    ):
        """
        初始化 MinIO 客户端

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-12-14 17:00:12
        Args:
            endpoint: MinIO 服务端点，形如 "localhost:9000"，默认取 settings.MINIO_ENDPOINT
            access_key: 访问密钥，默认取 settings.MINIO_ACCESS_KEY
            secret_key: 访问密钥，默认取 settings.MINIO_SECRET_KEY
            bucket_name: 默认存储桶名称，默认取 settings.MINIO_BUCKET_NAME
            secure: 是否使用 HTTPS，默认 None（读 settings.MINIO_SECURE）

        Returns:
            None
        """
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.bucket_name = bucket_name or settings.MINIO_BUCKET_NAME
        self.secure = secure if secure is not None else settings.MINIO_SECURE
        self._bucket_ready: set[str] = set()

        # 台账②：自定义 http_client 收紧超时——connect 取 settings.MINIO_CONNECTION_TIMEOUT
        # （不可达地址 TCP connect 由 OS 级 ~21s×3 次重试收敛到秒级快速失败）、read 60s；
        # retries=0 禁底层连接重试（应用层经幂等记录重试，语义更清晰）
        self._client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
            http_client=PoolManager(
                timeout=Timeout(connect=settings.MINIO_CONNECTION_TIMEOUT, read=STORAGE_HTTP_READ_TIMEOUT_SECONDS),
                retries=0,
                maxsize=10,
            ),
        )

    def ensure_bucket(self, bucket_name: Optional[str] = None) -> bool:
        """
        确保存储桶存在，不存在时自动创建

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-12-14 17:00:12
        Args:
            bucket_name: 桶名称，默认使用初始化时的 bucket_name

        Returns:
            bool: True 表示桶已存在或创建成功，False 表示失败
        """
        bucket = bucket_name or self.bucket_name
        if bucket in self._bucket_ready:
            return True
        try:
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)
                logger.info(f"MinIO 桶已创建: {bucket}")
            else:
                logger.debug(f"MinIO 桶已存在: {bucket}")
            self._bucket_ready.add(bucket)
            return True
        except S3Error as e:
            logger.error(f"MinIO 确保存储桶失败: endpoint={self.endpoint}, bucket={bucket}, error={e}")
            return False

    def upload_file(
        self,
        object_name: str,
        file_path: str,
        bucket_name: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Optional[str]:
        """
        上传本地文件到 MinIO

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-12-14 17:00:12
        Args:
            object_name: 对象在桶中的名称（路径），如 "jsa/2025/xxx.pdf"
            file_path: 本地文件路径
            bucket_name: 桶名称，默认使用初始化时的 bucket_name
            content_type: 文件类型，例如 "application/pdf"、"image/png" 等

        Returns:
            Optional[str]: 上传成功后构造的文件 URL（简单拼接），失败时返回 None
        """
        bucket = bucket_name or self.bucket_name
        if not self.ensure_bucket(bucket):
            return None

        try:
            self._client.fput_object(
                bucket_name=bucket,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type,
            )
            url = self.build_object_url(object_name, bucket)
            logger.info(f"MinIO 文件上传成功: bucket={bucket}, object={object_name}, url={url}")
            return url
        except S3Error as e:
            logger.error(
                f"MinIO 文件上传失败: endpoint={self.endpoint}, bucket={bucket}, object={object_name}, file={file_path}, error={e}"
            )
            return None

    def upload_bytes(
        self,
        object_name: str,
        data: bytes,
        bucket_name: Optional[str] = None,
        content_type: Optional[str] = None,
        *,
        skip_ensure_bucket: bool = False,
    ) -> Optional[str]:
        """
        上传字节数据到 MinIO

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-12-14 17:00:12
        Args:
            object_name: 对象在桶中的名称（路径）
            data: 二进制数据
            bucket_name: 桶名称，默认使用初始化时的 bucket_name
            content_type: 文件类型，例如 "application/pdf"、"image/png" 等

        Returns:
            Optional[str]: 上传成功后构造的文件 URL，失败时返回 None
        """
        bucket = bucket_name or self.bucket_name
        if not skip_ensure_bucket and not self.ensure_bucket(bucket):
            return None

        try:
            data_stream = io.BytesIO(data)
            data_len = len(data)
            self._client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=data_stream,
                length=data_len,
                content_type=content_type,
            )
            url = self.build_object_url(object_name, bucket)
            logger.info(f"MinIO 字节流上传成功: bucket={bucket}, object={object_name}, url={url}")
            return url
        except S3Error as e:
            logger.error(
                f"MinIO 字节流上传失败: endpoint={self.endpoint}, bucket={bucket}, object={object_name}, size={len(data)}, error={e}"
            )
            return None

    def get_presigned_url(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
        expires: int = 3600,
    ) -> Optional[str]:
        """
        生成对象的预签名访问 URL

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-12-14 17:00:12
        Args:
            object_name: 对象在桶中的名称（路径）
            bucket_name: 桶名称，默认使用初始化时的 bucket_name
            expires: 过期时间（秒），默认 3600 秒

        Returns:
            Optional[str]: 预签名 URL，失败时返回 None
        """
        bucket = bucket_name or self.bucket_name
        try:
            url = self._client.presigned_get_object(
                bucket_name=bucket,
                object_name=object_name,
                expires=timedelta(seconds=expires),
            )
            logger.debug(f"MinIO 预签名 URL 生成成功: bucket={bucket}, object={object_name}")
            return url
        except S3Error as e:
            logger.error(
                f"MinIO 预签名 URL 生成失败:endpoint={self.endpoint}, bucket={bucket}, object={object_name}, error={e}"
            )
            return None

    def delete_object(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
    ) -> bool:
        """
        删除 MinIO 中的对象

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-12-14 17:00:12
        Args:
            object_name: 对象在桶中的名称（路径）
            bucket_name: 桶名称，默认使用初始化时的 bucket_name

        Returns:
            bool: True 表示删除成功，False 表示失败
        """
        bucket = bucket_name or self.bucket_name
        try:
            self._client.remove_object(bucket_name=bucket, object_name=object_name)
            logger.info(f"MinIO 对象删除成功: bucket={bucket}, object={object_name}")
            return True
        except S3Error as e:
            logger.error(
                f"MinIO 对象删除失败:endpoint={self.endpoint}, bucket={bucket}, object={object_name}, error={e}"
            )
            return False

    def build_object_url(self, object_name: str, bucket_name: Optional[str] = None) -> str:
        """
        根据 endpoint / bucket / object_name 构造一个简单的 HTTP 访问 URL

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-12-14 17:00:12
        Args:
            bucket_name: 桶名称
            object_name: 对象名称（路径）

        Returns:
            str: 拼接后的 URL 字符串
        """
        bucket = bucket_name or self.bucket_name
        scheme = "https" if self.secure else "http"
        return f"{scheme}://{self.endpoint}/{bucket}/{object_name}"

    def build_endpoint(self, bucket_name: Optional[str] = None) -> str:
        """
        构造 MinIO 的 endpoint

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-12-14 17:00:12

        Returns:
            str: 拼接后的 endpoint 字符串
        """
        bucket = bucket_name or self.bucket_name
        scheme = "https" if self.secure else "http"
        return f"{scheme}://{self.endpoint}/{bucket}"

    def get_object(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
    ) -> bytes:
        """
        从 MinIO 获取对象数据

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2026-02-20 17:30:00

        Args:
            object_name: 对象在桶中的名称（路径）
            bucket_name: 桶名称，默认使用初始化时的 bucket_name

        Returns:
            bytes: 对象的二进制数据

        Raises:
            S3Error: 当获取对象失败时
        """
        bucket = bucket_name or self.bucket_name
        try:
            response = self._client.get_object(bucket_name=bucket, object_name=object_name)
            data = response.read()
            response.close()
            response.release_conn()
            logger.debug(f"MinIO 对象获取成功: bucket={bucket}, object={object_name}, size={len(data)}")
            return data
        except S3Error as e:
            logger.error(
                f"MinIO 对象获取失败:endpoint={self.endpoint}, bucket={bucket}, object={object_name}, error={e}"
            )
            raise

    def download_file(
        self,
        object_name: str,
        download_path: str,
        bucket_name: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        从 MinIO 下载文件到指定目录

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2025-12-30 10:30:00
        Args:
            object_name: 对象在桶中的名称（路径）
            download_path: 本地下载目录路径
            bucket_name: 桶名称，默认使用初始化时的 bucket_name

        Returns:
            tuple[bool, str]: 第一个是布尔值表示是否成功，第二个是字符串表示本地文件路径或错误信息
        """

        bucket = bucket_name or self.bucket_name

        try:
            # 确保下载目录存在
            os.makedirs(download_path, exist_ok=True)

            # 构造本地文件路径
            local_file_path = os.path.join(download_path, os.path.basename(object_name))

            # 从 MinIO 下载文件
            self._client.fget_object(bucket_name=bucket, object_name=object_name, file_path=local_file_path)

            logger.info(f"MinIO 文件下载成功: bucket={bucket}, object={object_name}, local_path={local_file_path}")
            return True, local_file_path

        except S3Error as e:
            error_msg = (
                f"MinIO 文件下载失败: endpoint={self.endpoint}, bucket={bucket}, object={object_name}, error={e}"
            )
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"下载过程中发生未知错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


minio_client = MinioClient()


class AsyncMinioStorage:
    """
    MinIO 异步门面（业务代码唯一存储入口；组合共享 minio_client，多 bucket 路由）

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-24 22:59:42
    """

    MAX_GET_OBJECT_BYTES = 64 * 1024 * 1024  # get_object 全量读取上限 64MB

    def __init__(self, client: Optional[MinioClient] = None):
        self._sync = client or minio_client

    # ---- 内部工具 -------------------------------------------------

    def _bucket(self, bucket: StorageBucket) -> str:
        return resolve_bucket_name(bucket)

    @staticmethod
    def _translate_s3_error(e: Exception, bucket: str, object_key: str) -> Exception:
        """S3Error → 业务异常转译（NoSuchKey→404，其余→503）。"""
        code = getattr(e, "code", "")
        if code in ("NoSuchKey", "NoSuchObject"):
            return StorageObjectNotFoundError(bucket, object_key)
        return StorageUnavailableError(f"MinIO 操作失败: {getattr(e, 'message', e)}")

    @staticmethod
    def _raise_storage_error(e: Exception, bucket: str, object_key: str) -> None:
        """
        统一存储异常转译（台账②）：S3Error 走语义转译，网络层异常（连接超时/
        连接重试耗尽/读写超时等）一律 503 STORAGE_UNAVAILABLE 快速清洁报错。

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2026-09-27 12:00:00

        Args:
            e: 捕获的底层异常
            bucket: 实际桶名
            object_key: 对象键

        Returns:
            None

        Raises:
            StorageObjectNotFoundError / StorageUnavailableError: 必然抛出
        """
        if isinstance(e, S3Error):
            raise AsyncMinioStorage._translate_s3_error(e, bucket, object_key) from e
        raise StorageUnavailableError(f"MinIO 网络异常（{type(e).__name__}）: {e}") from e

    # ---- 公开接口 -------------------------------------------------

    async def ensure_buckets(self) -> None:
        """
        启动时确保全部桶存在（幂等）

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2026-09-24 22:59:42

        Returns:
            None

        Raises:
            StorageUnavailableError: 任一桶 ensure 失败
        """
        for bucket in StorageBucket:
            name = self._bucket(bucket)
            try:
                ok = await asyncio.to_thread(self._sync.ensure_bucket, name)
            except STORAGE_NETWORK_ERRORS as e:
                raise StorageUnavailableError(f"桶不可用: {name}（{type(e).__name__}）") from e
            if not ok:
                raise StorageUnavailableError(f"桶不可用: {name}")

    async def put_object(
        self,
        bucket: StorageBucket,
        object_key: str,
        data,
        *,
        content_type: str = "application/octet-stream",
        length: Optional[int] = None,
        immutable: bool = False,
    ) -> str:
        """
        上传字节/流对象；immutable=True 时 stat 命中即抛 ObjectExistsError，put 后回读 etag 复核

        Author  ：bixuejun(bxjgood@163.com)
        Date    ：2026-09-24 22:59:42

        Args:
            bucket: 桶枚举成员
            object_key: 桶内键
            data: bytes 或 BinaryIO
            content_type: MIME 类型
            length: data 为流时的长度（bytes 自动计算）
            immutable: 是否不可变写入

        Returns:
            str: etag

        Raises:
            ObjectExistsError / StorageError / StorageUnavailableError
        """
        validate_object_key(object_key)
        name = self._bucket(bucket)

        if immutable:
            try:
                await asyncio.to_thread(self._sync._client.stat_object, name, object_key)
            except STORAGE_NETWORK_ERRORS as e:
                self._raise_storage_error(e, name, object_key)
            except S3Error as e:
                if e.code != "NoSuchKey":
                    raise StorageUnavailableError(f"stat 失败: {e.message}") from e
            else:
                raise ObjectExistsError(name, object_key)

        if isinstance(data, (bytes, bytearray)):
            stream = io.BytesIO(bytes(data))
            length = len(data)
        else:
            stream = data
            if length is None:
                raise StorageError(
                    422, "流式上传必须提供 length", "STORAGE_OBJECT_KEY_INVALID", reason="length_required"
                )

        try:
            result = await asyncio.to_thread(
                self._sync._client.put_object,
                bucket_name=name,
                object_name=object_key,
                data=stream,
                length=length,
                content_type=content_type,
            )
        except (S3Error, *STORAGE_NETWORK_ERRORS) as e:
            self._raise_storage_error(e, name, object_key)

        # R27：put 后回读 etag 复核（同键不同内容仅可能来自 bug）
        if immutable:
            try:
                stat = await asyncio.to_thread(self._sync._client.stat_object, name, object_key)
            except (S3Error, *STORAGE_NETWORK_ERRORS) as e:
                self._raise_storage_error(e, name, object_key)
            if stat.etag != result.etag:
                logger.error(f"immutable 对象 etag 复核不一致（疑似同键不同内容）: {name}/{object_key}")
                raise StorageError(
                    409, "immutable 对象写入校验失败", "STORAGE_OBJECT_EXISTS", bucket=name, object_key=object_key
                )
        return result.etag

    async def put_file(
        self,
        bucket: StorageBucket,
        object_key: str,
        file_path,
        *,
        content_type: Optional[str] = None,
        immutable: bool = False,
    ) -> str:
        """
        上传本地文件（immutable 语义同 put_object）。返回 etag。
        """
        validate_object_key(object_key)
        name = self._bucket(bucket)
        if immutable:
            try:
                await asyncio.to_thread(self._sync._client.stat_object, name, object_key)
            except STORAGE_NETWORK_ERRORS as e:
                self._raise_storage_error(e, name, object_key)
            except S3Error as e:
                if e.code != "NoSuchKey":
                    raise StorageUnavailableError(f"stat 失败: {e.message}") from e
            else:
                raise ObjectExistsError(name, object_key)
        try:
            result = await asyncio.to_thread(
                self._sync._client.fput_object,
                bucket_name=name,
                object_name=object_key,
                file_path=str(file_path),
                content_type=content_type,
            )
        except (S3Error, *STORAGE_NETWORK_ERRORS) as e:
            self._raise_storage_error(e, name, object_key)
        return result.etag

    async def get_object(self, bucket: StorageBucket, object_key: str) -> bytes:
        """全量读取小对象（>64MB 抛防护错误）。"""
        validate_object_key(object_key)
        name = self._bucket(bucket)
        try:
            stat = await asyncio.to_thread(self._sync._client.stat_object, name, object_key)
            if stat.size > self.MAX_GET_OBJECT_BYTES:
                raise StorageError(
                    422,
                    f"对象过大，禁止全量读取（{stat.size} 字节），请使用 download_to_file",
                    "STORAGE_OBJECT_TOO_LARGE",
                    bucket=name,
                    object_key=object_key,
                )
            response = await asyncio.to_thread(self._sync._client.get_object, name, object_key)
            try:
                return await asyncio.to_thread(response.read)
            finally:
                await asyncio.to_thread(response.close)
                await asyncio.to_thread(response.release_conn)
        except StorageError:
            raise
        except (S3Error, *STORAGE_NETWORK_ERRORS) as e:
            self._raise_storage_error(e, name, object_key)

    async def download_to_file(self, bucket: StorageBucket, object_key: str, dest_path) -> Path:
        """流式下载到精确目标路径（父目录自动创建；注意与同步版 download_file 落目录语义不同）。"""
        validate_object_key(object_key)
        name = self._bucket(bucket)
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            await asyncio.to_thread(self._sync._client.fget_object, name, object_key, str(dest))
        except (S3Error, *STORAGE_NETWORK_ERRORS) as e:
            self._raise_storage_error(e, name, object_key)
        return dest

    async def stat_object(self, bucket: StorageBucket, object_key: str):
        """获取对象元信息（minio.datatypes.Object）。"""
        validate_object_key(object_key)
        name = self._bucket(bucket)
        try:
            return await asyncio.to_thread(self._sync._client.stat_object, name, object_key)
        except (S3Error, *STORAGE_NETWORK_ERRORS) as e:
            self._raise_storage_error(e, name, object_key)

    async def presigned_get_url(
        self, bucket: StorageBucket, object_key: str, expires_seconds: Optional[int] = None
    ) -> str:
        """生成短期预签名 GET URL（有效期默认/上限 settings.MINIO_URL_EXPIRES，默认 ≤300s）。"""
        validate_object_key(object_key)
        name = self._bucket(bucket)
        limit = settings.MINIO_URL_EXPIRES
        seconds = min(expires_seconds or limit, limit)
        try:
            return await asyncio.to_thread(
                self._sync._client.presigned_get_object, name, object_key, timedelta(seconds=seconds)
            )
        except (S3Error, *STORAGE_NETWORK_ERRORS) as e:
            self._raise_storage_error(e, name, object_key)
        raise StorageUnavailableError("unreachable")

    async def remove_object(self, bucket: StorageBucket, object_key: str) -> None:
        """删除对象（仅回收任务使用，业务代码禁止调用）。"""
        validate_object_key(object_key)
        name = self._bucket(bucket)
        try:
            await asyncio.to_thread(self._sync._client.remove_object, name, object_key)
        except (S3Error, *STORAGE_NETWORK_ERRORS) as e:
            self._raise_storage_error(e, name, object_key)

    async def list_objects(self, bucket: StorageBucket, prefix: str):
        """按前缀列举桶内对象键（async 生成器）。"""
        name = self._bucket(bucket)

        def _collect():
            return [obj.object_name for obj in self._sync._client.list_objects(name, prefix=prefix, recursive=True)]

        try:
            object_names = await asyncio.to_thread(_collect)
        except (S3Error, *STORAGE_NETWORK_ERRORS) as e:
            self._raise_storage_error(e, name, prefix)
        for object_name in object_names:
            yield object_name

    async def sha256_of(self, bucket: StorageBucket, object_key: str) -> str:
        """流式计算对象 sha256，返回 'sha256:<hex>'（文件校验统一口径）。"""
        validate_object_key(object_key)
        name = self._bucket(bucket)

        def _hash():
            digest = hashlib.sha256()
            response = self._sync._client.get_object(name, object_key)
            try:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    digest.update(chunk)
            finally:
                response.close()
                response.release_conn()
            return f"sha256:{digest.hexdigest()}"

        try:
            return await asyncio.to_thread(_hash)
        except (S3Error, *STORAGE_NETWORK_ERRORS) as e:
            self._raise_storage_error(e, name, object_key)
        raise StorageUnavailableError("unreachable")


_storage_instance: Optional[AsyncMinioStorage] = None


def get_storage() -> AsyncMinioStorage:
    """
    进程内单例入口（FastAPI 与 Worker 各进程独立持有）

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-24 22:59:42

    Returns:
        AsyncMinioStorage: 门面单例
    """
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = AsyncMinioStorage()
    return _storage_instance

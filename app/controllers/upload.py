import os
import shutil
import uuid
from datetime import datetime
from typing import Dict, List

from fastapi import HTTPException, UploadFile, status

from app.settings.config import settings
from app.services.system_setting_service import system_setting_service

# 条件导入 oss2，如果不存在则设为 None
try:
    import oss2
    OSS_AVAILABLE = True
except ImportError:
    oss2 = None
    OSS_AVAILABLE = False


class UploadController:
    """文件上传控制器"""

    def ensure_storage_directory(self, path: str) -> None:
        """
        确保存储目录存在（仅在需要时创建）

        Args:
            path: 需要创建的目录路径
        """
        os.makedirs(path, exist_ok=True)

    def get_file_extension(self, filename: str) -> str:
        """获取文件扩展名"""
        return os.path.splitext(filename)[1] if "." in filename else ""

    async def get_storage_settings(self) -> dict:
        return await system_setting_service.get_runtime_storage_settings()

    @staticmethod
    def is_object_storage_enabled(storage_settings: dict) -> bool:
        return storage_settings.get("provider") == "oss"

    @staticmethod
    def is_local_file_key(file_key: str, storage_settings: dict) -> bool:
        local_full_url = storage_settings.get("local_full_url", "").rstrip("/")
        return file_key.startswith("/static/") or (local_full_url and file_key.startswith(local_full_url))

    def generate_oss_file_name(self, original_filename: str) -> str:
        """生成对象存储中的文件名，基于时间和UUID"""
        ext = self.get_file_extension(original_filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_uuid = str(uuid.uuid4()).replace("-", "")[:8]
        return f"{timestamp}_{random_uuid}{ext}"

    def generate_oss_path(self, upload_dir: str, file_type: str = "common") -> str:
        """
        根据文件类型和当前日期生成对象存储路径

        Args:
            upload_dir: 对象存储上传目录
            file_type: 文件类型，用于分类存储，如image、document等

        Returns:
            str: 对象存储路径
        """
        today = datetime.now()
        date_str = today.strftime("%Y%m%d")  # 使用连续的年月日格式

        # 对象存储使用正斜杠，Windows 下 os.path.join 会生成反斜杠，因此统一替换。
        path = os.path.join(upload_dir, file_type, date_str)
        return path.replace("\\", "/")

    def generate_local_path(self, storage_settings: dict, file_type: str = "common") -> str:
        """
        根据文件类型和当前日期生成本地存储路径

        Args:
            storage_settings: 当前存储配置
            file_type: 文件类型，用于分类存储，如image、document等

        Returns:
            tuple: (本地文件系统路径, URL路径)
        """
        today = datetime.now()
        date_str = today.strftime("%Y%m%d")  # 使用连续的年月日格式
        local_upload_dir = storage_settings["local_upload_dir"]
        local_url_prefix = storage_settings["local_url_prefix"]

        # 本地文件系统路径
        fs_path = os.path.join(settings.storage_root_path, local_upload_dir, file_type, date_str)
        # URL路径
        url_path = os.path.join(local_url_prefix, file_type, date_str).replace("\\", "/")

        # 仅在实际需要时确保目录存在
        self.ensure_storage_directory(fs_path)

        return fs_path, url_path

    async def check_image_file(self, file: UploadFile) -> bytes:
        """
        检查图片文件是否符合要求

        Args:
            file: 上传的文件

        Returns:
            bytes: 文件内容

        Raises:
            HTTPException: 文件不符合要求时抛出异常
        """
        # 检查文件类型
        file_extension = self.get_file_extension(file.filename).lower()
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的图片格式，仅支持: {', '.join(allowed_extensions)}",
            )

        # 读取文件内容
        file_content = await file.read()

        # 检查文件大小（限制为10MB）
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"文件大小超出限制，最大允许10MB")

        return file_content

    async def check_file(self, file: UploadFile) -> bytes:
        """
        检查普通文件是否符合要求

        Args:
            file: 上传的文件

        Returns:
            bytes: 文件内容

        Raises:
            HTTPException: 文件不符合要求时抛出异常
        """
        # 读取文件内容
        file_content = await file.read()

        # 检查文件大小（限制为10MB）
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"文件大小超出限制，最大允许10MB")

        return file_content

    def validate_object_storage_config(self, storage_settings: dict) -> None:
        if not OSS_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="对象存储 SDK 不可用，请安装 oss2 或切换为本地存储",
            )

        required_fields = {
            "oss_access_key_id": "AccessKey ID",
            "oss_access_key_secret": "AccessKey Secret",
            "oss_bucket_name": "Bucket 名称",
            "oss_endpoint": "Endpoint",
        }
        missing_fields = [label for field, label in required_fields.items() if not storage_settings.get(field)]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"对象存储配置不完整，缺少: {', '.join(missing_fields)}",
            )

    def build_oss_bucket(self, storage_settings: dict):
        self.validate_object_storage_config(storage_settings)
        auth = oss2.Auth(storage_settings["oss_access_key_id"], storage_settings["oss_access_key_secret"])
        return oss2.Bucket(auth, storage_settings["oss_endpoint"], storage_settings["oss_bucket_name"])

    @staticmethod
    def build_oss_file_url(storage_settings: dict, object_key: str) -> str:
        bucket_domain = storage_settings.get("oss_bucket_domain", "")
        if bucket_domain:
            return f"https://{bucket_domain}/{object_key}"
        return f"https://{storage_settings['oss_bucket_name']}.{storage_settings['oss_endpoint']}/{object_key}"

    async def upload_to_local(
        self,
        file_content: bytes,
        filename: str,
        storage_settings: dict,
        file_type: str = "common",
    ) -> str:
        """
        上传文件到本地存储

        Args:
            file_content: 文件内容
            filename: 文件名
            storage_settings: 当前存储配置
            file_type: 文件类型，如image、document等

        Returns:
            str: 文件的URL

        Raises:
            HTTPException: 上传失败时抛出异常
        """
        try:
            # 获取本地存储路径
            local_storage_full_url = storage_settings["local_full_url"]
            local_upload_dir = storage_settings["local_upload_dir"]
            fs_path, url_path = self.generate_local_path(storage_settings, file_type)

            # 文件完整路径
            file_path = os.path.join(fs_path, filename)

            # 写入文件
            with open(file_path, "wb") as f:
                f.write(file_content)

            # 返回文件URL
            if local_storage_full_url:
                relative_path = url_path[len("/static/") :].lstrip("/")
                file_url = f"{local_storage_full_url.rstrip('/')}/{relative_path}/{filename}"
            else:
                # 否则使用相对路径
                file_url = f"{url_path}/{filename}"

            return file_url

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"上传到本地存储失败: {str(e)}"
            )

    async def upload_to_oss(self, file_content: bytes, oss_file_name: str, file_type: str = "common") -> str:
        """
        上传文件到对象存储或本地存储

        Args:
            file_content: 文件内容
            oss_file_name: 对象存储中的文件名
            file_type: 文件类型，如image、document等

        Returns:
            str: 文件的URL

        Raises:
            HTTPException: 上传失败时抛出异常
        """
        storage_settings = await self.get_storage_settings()
        if not self.is_object_storage_enabled(storage_settings):
            return await self.upload_to_local(file_content, oss_file_name, storage_settings, file_type)

        bucket = self.build_oss_bucket(storage_settings)

        # 构建完整的OSS文件路径，增加按日期分类的目录结构
        upload_dir = storage_settings.get("oss_upload_dir") or "uploads"
        oss_path = self.generate_oss_path(upload_dir, file_type)
        # 使用os.path.join连接路径，然后转换为OSS格式
        oss_file_path = os.path.join(oss_path, oss_file_name).replace("\\", "/")

        # 上传文件
        try:
            # 上传文件并设置ACL为公共读，确保文件可以被公开访问
            headers = {"x-oss-object-acl": "public-read"}
            bucket.put_object(oss_file_path, file_content, headers=headers)

            return self.build_oss_file_url(storage_settings, oss_file_path)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"上传到对象存储失败: {str(e)}",
            )

    async def upload_image(self, file: UploadFile) -> Dict:
        """
        上传单个图片到对象存储或本地存储

        Args:
            file: 上传的图片文件

        Returns:
            Dict: 包含上传结果的字典
        """
        # 检查文件
        file_content = await self.check_image_file(file)

        # 生成文件名
        file_name = self.generate_oss_file_name(file.filename)

        # 上传文件，根据配置选择对象存储或本地存储
        file_url = await self.upload_to_oss(file_content, file_name, file_type="image")

        # 返回结果
        return {"url": file_url, "name": file.filename, "size": len(file_content)}

    async def upload_files(self, files: List[UploadFile]) -> List[Dict]:
        """
        批量上传文件到对象存储或本地存储

        Args:
            files: 上传的文件列表

        Returns:
            List[Dict]: 包含上传结果的字典列表
        """
        if not files:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有提供要上传的文件")

        # 限制最大上传数量
        max_files = 10
        if len(files) > max_files:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"一次最多上传{max_files}个文件")

        result = []

        for file in files:
            # 检查文件
            file_content = await self.check_file(file)

            # 生成文件名
            file_name = self.generate_oss_file_name(file.filename)

            # 根据文件扩展名决定文件类型
            file_extension = self.get_file_extension(file.filename).lower()
            file_type = "common"

            # 根据扩展名确定文件类型
            if file_extension in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                file_type = "image"
            elif file_extension in [".doc", ".docx", ".pdf", ".txt", ".xls", ".xlsx"]:
                file_type = "document"
            elif file_extension in [".mp4", ".avi", ".mov", ".wmv"]:
                file_type = "video"

            # 上传文件，根据配置选择对象存储或本地存储
            file_url = await self.upload_to_oss(file_content, file_name, file_type=file_type)

            result.append({"url": file_url, "name": file.filename, "size": len(file_content)})

        return result

    async def list_files(self, prefix: str = None, max_keys: int = 100) -> List[Dict]:
        """
        获取对象存储中的文件列表

        Args:
            prefix: 路径前缀，例如 "image/"
            max_keys: 最大返回数量，默认100

        Returns:
            List[Dict]: 文件信息列表
        """
        storage_settings = await self.get_storage_settings()
        if not self.is_object_storage_enabled(storage_settings):
            return []

        try:
            bucket = self.build_oss_bucket(storage_settings)

            # 构建完整的前缀，使用os.path.join处理路径
            upload_dir = storage_settings.get("oss_upload_dir") or "uploads"
            if prefix:
                full_prefix = os.path.join(upload_dir, prefix).replace("\\", "/")
            else:
                full_prefix = upload_dir

            # 列举文件
            result = []
            for obj in oss2.ObjectIterator(bucket, prefix=full_prefix, max_keys=max_keys):
                if not obj.key.endswith("/"):  # 排除目录
                    file_name = os.path.basename(obj.key)

                    result.append(
                        {
                            "name": file_name,
                            "url": self.build_oss_file_url(storage_settings, obj.key),
                            "key": obj.key,
                            "size": obj.size,
                            "last_modified": obj.last_modified.strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )

            return result

        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取文件列表失败: {str(e)}")

    async def delete_local_file(self, file_path: str, storage_settings: dict) -> bool:
        """
        删除本地存储中的文件

        Args:
            file_path: 文件的相对路径或完整URL
            storage_settings: 当前存储配置

        Returns:
            bool: 是否删除成功
        """
        try:
            print(f"尝试删除本地文件: {file_path}")
            local_storage_full_url = storage_settings["local_full_url"].rstrip("/")

            if local_storage_full_url and file_path.startswith(local_storage_full_url):
                relative_path = file_path[len(local_storage_full_url) :].lstrip("/")
            elif file_path.startswith("/static/"):
                relative_path = file_path[len("/static/") :].lstrip("/")
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的本地文件路径")

            full_path = os.path.join(settings.storage_root_path, relative_path)

            print(f"解析后的完整路径: {full_path}")

            # 检查文件是否存在
            if os.path.isfile(full_path):
                os.remove(full_path)
                print(f"文件删除成功: {full_path}")
                return True

            # 如果文件不存在，记录错误信息但不抛出异常
            print(f"文件不存在: {full_path}")
            return False

        except HTTPException:
            raise
        except Exception as e:
            print(f"删除本地文件失败: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除本地文件失败: {str(e)}")

    async def delete_file(self, file_key: str) -> bool:
        """
        删除OSS或本地存储中的文件

        Args:
            file_key: 文件的OSS键值或本地存储路径

        Returns:
            bool: 是否删除成功
        """
        storage_settings = await self.get_storage_settings()
        if not self.is_object_storage_enabled(storage_settings) or self.is_local_file_key(file_key, storage_settings):
            return await self.delete_local_file(file_key, storage_settings)

        try:
            bucket = self.build_oss_bucket(storage_settings)

            # 删除文件
            bucket.delete_object(file_key)
            return True

        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除文件失败: {str(e)}")

    async def set_public_acl(self, prefix: str = None) -> Dict:
        """
        批量设置指定前缀下的文件ACL为公共读

        Args:
            prefix: 路径前缀，例如 "image/"

        Returns:
            Dict: 处理结果
        """
        storage_settings = await self.get_storage_settings()
        if not self.is_object_storage_enabled(storage_settings):
            return {
                "success": False,
                "message": "当前未启用对象存储",
                "count": 0,
                "error_count": 0,
            }

        try:
            bucket = self.build_oss_bucket(storage_settings)

            # 构建完整的前缀
            upload_dir = storage_settings.get("oss_upload_dir") or "uploads"
            if prefix:
                full_prefix = os.path.join(upload_dir, prefix).replace("\\", "/")
            else:
                full_prefix = upload_dir

            # 处理计数
            count = 0
            error_count = 0

            # 列举文件并设置ACL
            for obj in oss2.ObjectIterator(bucket, prefix=full_prefix):
                if not obj.key.endswith("/"):  # 排除目录
                    try:
                        # 设置文件ACL为公共读
                        bucket.put_object_acl(obj.key, oss2.OBJECT_ACL_PUBLIC_READ)
                        count += 1
                    except Exception:
                        error_count += 1

            return {
                "success": True,
                "message": f"成功设置 {count} 个文件的ACL为公共读，失败 {error_count} 个",
                "count": count,
                "error_count": error_count,
            }

        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"设置文件ACL失败: {str(e)}")


upload_controller = UploadController()

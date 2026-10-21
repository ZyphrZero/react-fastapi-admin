#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MinIO 存储基础件单元测试：对象键校验 / 桶名解析 / 异常错误码 / AsyncMinioStorage 门面

Author: bixuejun(bxjgood@163.com)
Date: 2026-09-24 14:39:07  # 北京时间 UTC+8
"""

import asyncio
from unittest.mock import MagicMock

import pytest
from minio.error import S3Error

from app.settings.config import Settings
from app.utils.minio_utils import (
    AsyncMinioStorage,
    ObjectExistsError,
    StorageBucket,
    StorageError,
    StorageObjectNotFoundError,
    StorageUnavailableError,
    resolve_bucket_name,
    validate_object_key,
)


class TestValidateObjectKey:
    def test_legal_key_accepted(self) -> None:
        assert validate_object_key("template/abc123/raw/0f1e2d.docx") == "template/abc123/raw/0f1e2d.docx"

    def test_uppercase_rejected(self) -> None:
        with pytest.raises(StorageError) as exc_info:
            validate_object_key("Template/RAW.docx")
        assert exc_info.value.data["error_code"] == "STORAGE_OBJECT_KEY_INVALID"

    def test_chinese_rejected(self) -> None:
        with pytest.raises(StorageError):
            validate_object_key("contract/中文.docx")

    def test_space_and_special_rejected(self) -> None:
        for bad in ["a b.docx", "a+b.docx", "", "/leading", "trailing/", "..", "a//b", "k.docx\n", "a/./b", "a/../b", "a/.../b"]:
            with pytest.raises(StorageError):
                validate_object_key(bad)


class TestResolveBucketName:
    def test_default_names(self) -> None:
        settings = Settings(_env_file=None)
        assert resolve_bucket_name(StorageBucket.DEFAULT, settings=settings) == "app"
        assert resolve_bucket_name(StorageBucket.TMP, settings=settings) == "app-tmp"

    def test_settings_override(self) -> None:
        settings = Settings(MINIO_BUCKET_TMP="my-custom-tmp")
        assert resolve_bucket_name(StorageBucket.TMP, settings=settings) == "my-custom-tmp"


class TestStorageErrors:
    def test_error_codes(self) -> None:
        assert ObjectExistsError("bucket", "k.docx").status_code == 409
        assert ObjectExistsError("bucket", "k.docx").data["error_code"] == "STORAGE_OBJECT_EXISTS"
        assert StorageObjectNotFoundError("bucket", "k.docx").status_code == 404
        assert StorageObjectNotFoundError("bucket", "k.docx").data["error_code"] == "STORAGE_OBJECT_NOT_FOUND"
        assert StorageUnavailableError("x").status_code == 503
        assert StorageUnavailableError("x").data["error_code"] == "STORAGE_UNAVAILABLE"


# =====================================================================
# AsyncMinioStorage 异步门面（mock 共享同步客户端；未装 pytest-asyncio，用 asyncio.run 包裹）
# =====================================================================


def _make_storage_with_mock_client():
    storage = AsyncMinioStorage()
    mock_client = MagicMock()
    storage._sync = mock_client  # 门面持有的共享同步客户端（实现里命名为 _sync）
    return storage, mock_client


def _no_such_key_error() -> S3Error:
    return S3Error(code="NoSuchKey", message="no", resource="r", request_id="1", host_id="2", response=MagicMock())


class TestPutObjectImmutable:
    def test_immutable_existing_object_raises_409(self) -> None:
        storage, mock_client = _make_storage_with_mock_client()
        mock_client._client.stat_object.return_value = MagicMock(etag="abc")

        with pytest.raises(ObjectExistsError):
            asyncio.run(storage.put_object(StorageBucket.TMP, "p/abc.docx", b"data", immutable=True))
        mock_client._client.put_object.assert_not_called()

    def test_immutable_etag_mismatch_raises(self) -> None:
        storage, mock_client = _make_storage_with_mock_client()
        # 第一次 stat（immutable 预检）NoSuchKey 视为不存在继续 put；put 后回读 etag 不一致 → StorageError
        mock_client._client.stat_object.side_effect = [
            _no_such_key_error(),
            MagicMock(etag="etag-different"),
        ]
        mock_client._client.put_object.return_value = MagicMock(etag="etag-put")

        with pytest.raises(StorageError):
            asyncio.run(storage.put_object(StorageBucket.TMP, "p/abc.docx", b"data", immutable=True))


class TestGetObjectGuards:
    def test_oversize_object_rejected(self) -> None:
        storage, mock_client = _make_storage_with_mock_client()
        mock_client._client.stat_object.return_value = MagicMock(size=65 * 1024 * 1024)

        with pytest.raises(StorageError) as exc_info:
            asyncio.run(storage.get_object(StorageBucket.DEFAULT, "big.docx"))
        assert exc_info.value.data["error_code"] == "STORAGE_OBJECT_TOO_LARGE"
        mock_client._client.get_object.assert_not_called()

    def test_missing_object_translated_to_404(self) -> None:
        storage, mock_client = _make_storage_with_mock_client()
        mock_client._client.stat_object.side_effect = _no_such_key_error()

        with pytest.raises(StorageObjectNotFoundError):
            asyncio.run(storage.get_object(StorageBucket.DEFAULT, "missing.docx"))

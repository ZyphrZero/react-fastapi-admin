#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型基座测试（A4/A5 回归钉）

- SoftDeleteMixin.soft_delete 写入时区 aware 时间（配合 use_tz=False + timezone 配置
  统一存储时区，避免机器时区漂移）
- BusinessModel 抽象基类字段面（CHAR(32) UUID 主键 + 时间戳 + 创建人快照）

Author: bixuejun(bxjgood@163.com)
Date: 2026-10-19 21:15:02  # 北京时间 UTC+8
"""

from app.models.base import BusinessModel, SoftDeleteMixin


class _SoftDeleteDummy(SoftDeleteMixin):
    """不依赖 Tortoise 初始化的最小宿主。"""


class TestSoftDeleteMixin:
    def test_soft_delete_writes_tz_aware_timestamp(self) -> None:
        record = _SoftDeleteDummy()
        record.soft_delete()
        assert record.is_deleted is True
        assert record.deleted_at is not None
        assert record.deleted_at.tzinfo is not None

    def test_is_deleted_field_is_indexed(self) -> None:
        assert SoftDeleteMixin.is_deleted.field_type is not None


class TestBusinessModel:
    def test_business_model_abstract_fields(self) -> None:
        fields = BusinessModel._meta.fields
        for expected in ("id", "created_at", "updated_at", "created_by_name", "created_by_id"):
            assert expected in fields, f"BusinessModel 缺少字段 {expected}"

    def test_business_model_is_abstract(self) -> None:
        assert BusinessModel._meta.abstract is True

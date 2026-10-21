#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库配置校验测试（DD-01 §2.1：mysql 必须 utf8mb4）

Author: bixuejun(bxjgood@163.com)
Date: 2026-09-24 22:09:17  # 北京时间 UTC+8
"""

import pytest
from pydantic import ValidationError

from app.settings.config import Settings


class TestDatabaseCharsetValidator:
    def test_mysql_with_wrong_charset_rejected(self) -> None:
        with pytest.raises(ValidationError, match="utf8mb4"):
            Settings(DB_CONNECTION="mysql", DB_CHARSET="latin1")

    def test_mysql_with_utf8mb4_accepted(self) -> None:
        settings = Settings(DB_CONNECTION="mysql", DB_CHARSET="utf8mb4")
        assert settings.DB_CHARSET == "utf8mb4"

    def test_sqlite_not_affected_by_charset_rule(self) -> None:
        settings = Settings(DB_CONNECTION="sqlite", DB_CHARSET="latin1")
        assert settings.DB_CONNECTION == "sqlite"

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户上下文接线测试（决策 17：认证成功后 CTX_USER_ID/CTX_USER_NAME 可用）

Author: bixuejun(bxjgood@163.com)
Date: 2026-10-19 21:32:10  # 北京时间 UTC+8
"""

from types import SimpleNamespace

from app.core.ctx import CTX_USER_ID, CTX_USER_NAME
from app.core.dependency import bind_user_context


class TestBindUserContext:
    def test_bind_user_context_sets_vars(self) -> None:
        user = SimpleNamespace(id=7, username="alice")
        try:
            bind_user_context(user)
            assert CTX_USER_ID.get() == 7
            assert CTX_USER_NAME.get() == "alice"
        finally:
            CTX_USER_ID.set(0)
            CTX_USER_NAME.set("")

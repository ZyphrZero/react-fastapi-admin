#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
角色数据范围（data_scope）校验测试：一期仅 SELF/ALL 生效，大小写归一化

Author: bixuejun(bxjgood@163.com)
Date: 2026-10-19 22:05:00  # 北京时间 UTC+8
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.exceptions import ValidationError
from app.schemas.roles import RoleCreate
from app.services.role_admin_service import role_admin_service


def _actor() -> SimpleNamespace:
    return SimpleNamespace(id=1, is_superuser=True, is_active=True)


class TestDataScopeValidation:
    def test_create_role_rejects_phase2_data_scope(self) -> None:
        """一期数据范围仅 SELF/ALL 生效，DEPARTMENT/ORG 拒绝。"""
        with patch(
            "app.services.role_admin_service.role_repository.exists_by_name",
            new=AsyncMock(return_value=False),
        ):
            async def scenario():
                try:
                    await role_admin_service.create_role(
                        RoleCreate(name="二期范围角色", data_scope="DEPARTMENT"),
                        actor=_actor(),
                    )
                except ValidationError as exc:
                    return exc

            exc = asyncio.run(scenario())
        assert exc is not None
        assert "数据范围仅支持" in str(exc)

    def test_create_role_normalizes_data_scope(self) -> None:
        """data_scope 大小写归一化，缺省回退 SELF。"""

        async def scenario():
            with (
                patch(
                    "app.services.role_admin_service.role_repository.exists_by_name",
                    new=AsyncMock(return_value=False),
                ),
                patch(
                    "app.services.role_admin_service.role_repository.create",
                    new=AsyncMock(),
                ) as create_mock,
                patch(
                    "app.services.role_admin_service.admin_permission_service.ensure_can_create_role",
                    new=AsyncMock(),
                ),
            ):
                await role_admin_service.create_role(
                    RoleCreate(name="全量角色", data_scope="all"),
                    actor=_actor(),
                )
            return create_mock

        create_mock = asyncio.run(scenario())
        assert create_mock.await_args.args[0]["data_scope"] == "ALL"

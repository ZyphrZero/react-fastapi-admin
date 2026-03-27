import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.overview import _build_module_activity, _build_status_distribution, get_platform_overview


class OverviewAggregationTestCase(unittest.TestCase):
    def test_build_module_activity_returns_ranked_top_modules(self) -> None:
        rows = [
            {"module": "用户管理"},
            {"module": "用户管理"},
            {"module": ""},
            {"module": "审计日志"},
            {"module": "用户管理"},
        ]

        result = _build_module_activity(rows, limit=2)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["label"], "用户管理")
        self.assertEqual(result[0]["count"], 3)
        self.assertEqual(result[0]["share"], 60)
        self.assertEqual(result[1]["label"], "基础模块")
        self.assertEqual(result[1]["count"], 1)

    def test_build_status_distribution_groups_status_by_family(self) -> None:
        rows = [
            {"status": 200},
            {"status": 201},
            {"status": 302},
            {"status": 404},
            {"status": 500},
            {"status": None},
        ]

        result = _build_status_distribution(rows)

        self.assertEqual([item["key"] for item in result], ["2xx", "3xx", "4xx", "5xx", "other"])
        self.assertEqual(result[0]["count"], 2)
        self.assertEqual(result[0]["share"], 33)
        self.assertEqual(result[3]["count"], 1)
        self.assertEqual(result[4]["label"], "其他状态")


class OverviewContractTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_get_platform_overview_exposes_explicit_operations_model(self) -> None:
        recent_logs = [
            SimpleNamespace(
                id=9,
                username="auditor",
                module="审计日志",
                summary="查看审计记录",
                operation_type="查看",
                method="GET",
                path="/api/v1/auditlog/list",
                status=200,
                log_level="info",
                response_time=12,
                created_at=datetime(2026, 3, 18, 10, 30, 0),
            )
        ]

        user_all = MagicMock()
        user_all.count = AsyncMock(return_value=5)
        user_active = MagicMock()
        user_active.count = AsyncMock(return_value=4)
        role_all = MagicMock()
        role_all.count = AsyncMock(return_value=2)
        api_all = MagicMock()
        api_all.count = AsyncMock(return_value=18)

        today_logs = MagicMock()
        today_logs.count = AsyncMock(return_value=7)
        recent_logs_query = MagicMock()
        recent_logs_query.order_by.return_value.limit = AsyncMock(return_value=recent_logs)
        chart_rows_query = MagicMock()
        chart_rows_query.values = AsyncMock(return_value=[{"module": "审计日志", "status": 200}])

        with (
            patch("app.core.overview.User.all", return_value=user_all),
            patch("app.core.overview.User.filter", return_value=user_active),
            patch("app.core.overview.Role.all", return_value=role_all),
            patch("app.core.overview.Api.all", return_value=api_all),
            patch(
                "app.core.overview.AuditLog.filter",
                side_effect=[today_logs, recent_logs_query, chart_rows_query],
            ),
            patch(
                "app.core.overview.AuditLog.get_logs_statistics",
                new=AsyncMock(return_value={"2026-03-18": 1}),
            ),
        ):
            result = await get_platform_overview()

        system = result["system"]
        self.assertIn("app_title", system)
        self.assertIn("migration_mode", system)
        self.assertIn("seed_mode", system)
        self.assertIn("api_catalog_mode", system)
        self.assertFalse(system["startup_side_effects_enabled"])
        self.assertEqual(system["management_entry"], "python -m app")
        self.assertNotIn("title", system)
        self.assertNotIn("run_migrations_on_startup", system)
        self.assertNotIn("seed_base_data_on_startup", system)
        self.assertNotIn("refresh_api_metadata_on_startup", system)

        self.assertEqual(len(result["recent_activities"]), 1)
        activity = result["recent_activities"][0]
        self.assertIn("created_at", activity)
        self.assertNotIn("time", activity)


if __name__ == "__main__":
    unittest.main()

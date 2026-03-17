import unittest

from app.core.overview import _build_module_activity, _build_status_distribution


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


if __name__ == "__main__":
    unittest.main()

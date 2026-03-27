import unittest

from app.cli import build_parser


class CliContractTestCase(unittest.TestCase):
    def test_build_parser_supports_single_entrypoint_commands(self) -> None:
        parser = build_parser()

        serve_args = parser.parse_args(["serve"])
        self.assertEqual(serve_args.command, "serve")

        upgrade_args = parser.parse_args(["db", "upgrade"])
        self.assertEqual(upgrade_args.command, "db")
        self.assertEqual(upgrade_args.db_command, "upgrade")

        refresh_args = parser.parse_args(["db", "refresh-api"])
        self.assertEqual(refresh_args.command, "db")
        self.assertEqual(refresh_args.db_command, "refresh-api")

        bootstrap_args = parser.parse_args(["bootstrap"])
        self.assertEqual(bootstrap_args.command, "bootstrap")

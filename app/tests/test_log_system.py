#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging system tests.
Verify that the refactored logging system works as expected.
"""

import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import patch

# Add the project root to the import path.
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# Set test environment variables.
os.environ["DEBUG"] = "true"
os.environ["LOG_RETENTION_DAYS"] = "3"
os.environ["LOG_ROTATION"] = "1 day"
os.environ["LOG_MAX_FILE_SIZE"] = "5 MB"
os.environ["LOG_ENABLE_ACCESS_LOG"] = "true"


def test_basic_logging():
    """Test basic logging behavior."""
    print("🧪 Testing basic logging...")
    from app.utils.log_control import logger, init_logging

    # Initialize the logging system.
    init_logging()

    # Test logs at different levels.
    logger.info("This is an info log")
    logger.warning("This is a warning log")
    logger.error("This is an error log")
    logger.debug("This is a debug log")

    print("✅ Basic logging test passed")


def test_convenience_functions():
    """Test convenience logging helpers."""
    print("🧪 Testing convenience helpers...")
    from app.utils.log_control import log_info, log_warning, log_error, log_debug, log_critical

    log_info("Testing log_info")
    log_warning("Testing log_warning")
    log_error("Testing log_error")
    log_debug("Testing log_debug")
    log_critical("Testing log_critical")

    print("✅ Convenience helper test passed")


def test_named_logger():
    """Test named loggers."""
    print("🧪 Testing named loggers...")
    from app.utils.log_control import get_logger

    # Fetch named loggers.
    user_logger = get_logger("user_service")
    api_logger = get_logger("api_handler")

    user_logger.info("User service log")
    api_logger.error("API handler log")

    print("✅ Named logger test passed")


def test_log_manager():
    """Test the log manager."""
    print("🧪 Testing the log manager...")
    from app.utils.log_control import log_manager

    # Fetch the current configuration.
    config = log_manager.get_log_config()
    print(f"📋 Current log configuration: {config}")

    print("✅ Log manager test passed")


def test_exception_logging():
    """Test exception logging."""
    print("🧪 Testing exception logging...")
    from app.utils.log_control import logger

    # Simulate an exception.
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Testing exception logging")

    print("✅ Exception logging test passed")


def test_structured_logging():
    """Test structured logging."""
    print("🧪 Testing structured logging...")
    from app.utils.log_control import logger

    # Emit a structured log entry.
    logger.info("User login", user_id=123, username="admin", ip_address="192.168.1.100", action="login")

    # Bind contextual fields.
    request_logger = logger.bind(request_id="req_123", user_id=456)
    request_logger.info("Handling user request")

    print("✅ Structured logging test passed")


def test_access_log_middleware():
    """Test the access log middleware."""
    print("🧪 Testing the access log middleware...")
    from app.utils.log_control import AccessLogMiddleware

    # Create the middleware instance.
    middleware = AccessLogMiddleware(app=None, skip_paths=["/health", "/metrics"])  # The test does not require a real app.

    # Verify skip-path behavior.
    should_skip = middleware.should_skip_logging("/health")
    assert should_skip is True, "The /health path should be skipped"

    should_not_skip = middleware.should_skip_logging("/api/users")
    assert should_not_skip is False, "The /api/users path should not be skipped"

    print("✅ Access log middleware test passed")


def test_health_path_is_excluded_from_audit_log():
    """Test that the health-check path is excluded from audit logs."""
    print("🧪 Testing audit-log exclusion for /health...")
    from app.core.init_app import make_middlewares
    from app.core.middlewares import HttpAuditLogMiddleware

    audit_middlewares = [item for item in make_middlewares() if item.cls is HttpAuditLogMiddleware]

    assert len(audit_middlewares) == 1, "Exactly one audit-log middleware should be registered"
    assert "/health" in audit_middlewares[0].kwargs["exclude_paths"], "Audit logging should skip the /health path"

    print("✅ Audit-log exclusion test for /health passed")


def test_background_task_exceptions_are_isolated():
    """Test that background-task exceptions do not interrupt the request flow."""
    print("🧪 Testing background-task exception isolation...")
    from app.core.bgtask import BgTasks

    executed = []

    async def failing_task():
        executed.append("fail")
        raise RuntimeError("boom")

    async def success_task():
        executed.append("success")

    async def run_test():
        await BgTasks.init_bg_tasks_obj()
        await BgTasks.add_task(failing_task)
        await BgTasks.add_task(success_task)

        with patch("app.core.bgtask.logger.exception") as mock_exception:
            await BgTasks.execute_tasks()

        mock_exception.assert_called_once()
        assert "Background task execution failed" in mock_exception.call_args.args[0]
        assert executed == ["fail", "success"], "Subsequent tasks should continue after a background-task exception is isolated"

    asyncio.run(run_test())

    print("✅ Background-task exception isolation test passed")


def main():
    """Main test runner."""
    print("🚀 Starting tests for the refactored logging system...")
    print("=" * 60)

    tests = [
        test_basic_logging,
        test_convenience_functions,
        test_named_logger,
        test_log_manager,
        test_exception_logging,
        test_structured_logging,
        test_access_log_middleware,
        test_health_path_is_excluded_from_audit_log,
        test_background_task_exceptions_are_isolated,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} raised an exception: {e}")
            failed += 1
        print()

    print("=" * 60)
    print(f"📊 Test results: passed {passed}, failed {failed}")

    if failed == 0:
        print("🎉 All tests passed! The logging system refactor succeeded!")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the logging system configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging control module.
Provides a unified logging system built on loguru, including logging setup and access log middleware.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from app.settings import settings


def _console_sink(message: str) -> None:
    stream = sys.stderr
    try:
        stream.write(message)
    except UnicodeEncodeError:
        encoding = stream.encoding or "utf-8"
        stream.write(message.encode(encoding, errors="replace").decode(encoding, errors="replace"))
    stream.flush()


class LogManager:
    """Log manager responsible for application-wide logging configuration."""

    def __init__(self):
        # Whether logging has already been configured.
        self._is_configured = False

    def get_log_config(self) -> dict:
        """Return the effective log configuration."""
        config = {
            "log_dir": str(settings.logs_path),
            "log_retention_days": settings.LOG_RETENTION_DAYS,
            "log_rotation": settings.LOG_ROTATION,
            "debug_mode": settings.DEBUG,
            "max_file_size": settings.LOG_MAX_FILE_SIZE,
        }

        # Apply production-focused overrides.
        if settings.is_production:
            config.update(
                {
                    "log_retention_days": 30,
                    "log_rotation": "00:00",
                    "debug_mode": False,
                    "max_file_size": "50 MB",
                }
            )

        return config

    def setup_logger(self, force: bool = False, **kwargs):
        """
        Configure the application logger.

        Args:
            force: Whether to force reconfiguration.
            **kwargs: Logging configuration overrides.
        """
        if self._is_configured and not force:
            return logger

        if force:
            logger.remove()
            self._is_configured = False

        config = self.get_log_config()
        config.update(kwargs)

        # Remove the default handlers.
        logger.remove()

        # Compute the effective log level.
        log_level = "DEBUG" if config["debug_mode"] else "INFO"

        # Ensure the log directory exists.
        log_path = Path(config["log_dir"])
        log_path.mkdir(parents=True, exist_ok=True)

        # Use the current date in the log file name.
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = log_path / f"{today}.log"

        # Console output settings.
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

        # File output settings.
        file_format = "{time:YYYY-MM-DD HH:mm:ss} | " "{level: <8} | " "{name}:{function}:{line} | " "{message}"

        # Add console logging.
        logger.add(
            sink=_console_sink,
            format=console_format,
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=config["debug_mode"],
        )

        # Add the main file logger.
        logger.add(
            sink=str(log_file),
            rotation=config["log_rotation"],
            retention=f"{config['log_retention_days']} days",
            format=file_format,
            level=log_level,
            encoding="utf-8",
            backtrace=True,
            diagnose=config["debug_mode"],
            enqueue=True,
            compression="zip",
        )

        # Persist error logs to a dedicated file.
        error_log_file = log_path / f"error_{today}.log"
        logger.add(
            sink=str(error_log_file),
            rotation=config["log_rotation"],
            retention=f"{config['log_retention_days']} days",
            format=file_format,
            level="ERROR",
            encoding="utf-8",
            backtrace=True,
            diagnose=config["debug_mode"],
            enqueue=True,
            compression="zip",
        )

        self._is_configured = True

        # Log the resolved configuration.
        logger.info(f"Logging system configured - environment: {settings.APP_ENV}")
        logger.info(f"Log directory: {config['log_dir']}")
        logger.info(f"Debug mode: {config['debug_mode']}")
        logger.info(f"Log retention days: {config['log_retention_days']}")

        return logger


class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    HTTP access log middleware.
    Records access logs for all HTTP requests.
    """

    def __init__(self, app, skip_paths: Optional[list[str]] = None):
        super().__init__(app)
        self.skip_paths = skip_paths or ["/docs", "/redoc", "/openapi.json", "/favicon.ico"]

    def should_skip_logging(self, path: str) -> bool:
        """Return whether logging should be skipped for the given path."""
        return any(skip_path in path for skip_path in self.skip_paths)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip paths that should not be logged.
        if self.should_skip_logging(request.url.path):
            return await call_next(request)

        start_time = datetime.now()

        # Safely resolve the client IP address.
        client_host = "unknown"
        if request.client:
            client_host = request.client.host

        # Read the user agent.
        user_agent = request.headers.get("user-agent", "")

        try:
            response = await call_next(request)
            end_time = datetime.now()
            process_time = (end_time - start_time).total_seconds()

            # Record the access log entry.
            log_message = (
                f"HTTP {response.status_code} | "
                f"{client_host} | "
                f"{request.method} | "
                f"{request.url} | "
                f"{process_time:.3f}s | "
                f"UA: {user_agent[:100]}"
            )

            # Select the log level based on the response status.
            if response.status_code >= 500:
                logger.error(log_message)
            elif response.status_code >= 400:
                logger.warning(log_message)
            else:
                logger.info(log_message)

            return response

        except Exception as e:
            end_time = datetime.now()
            process_time = (end_time - start_time).total_seconds()

            # Record exception details.
            logger.error(
                f"HTTP ERROR | "
                f"{client_host} | "
                f"{request.method} | "
                f"{request.url} | "
                f"{process_time:.3f}s | "
                f"Exception: {str(e)}"
            )
            raise


# Global log manager instance.
log_manager = LogManager()


def init_logging():
    """
    Initialize the logging system.
    Called during application startup.
    """
    log_manager.setup_logger()

    # Record startup information.
    logger.info("=" * 50)
    logger.info(f"{settings.APP_TITLE} is starting...")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Project root: {settings.BASE_DIR}")
    logger.info(f"Log directory: {settings.logs_path}")
    logger.info("=" * 50)

    return logger


def get_logger(name: Optional[str] = None):
    """
    Return a configured logger.

    Args:
        name: Logger name.

    Returns:
        The configured logger.
    """
    if not log_manager._is_configured:
        log_manager.setup_logger()

    if name:
        return logger.bind(name=name)
    return logger


# Convenience logging helpers.
def log_info(message: str, **kwargs):
    """Log an info message."""
    logger.info(message, **kwargs)


def log_warning(message: str, **kwargs):
    """Log a warning message."""
    logger.warning(message, **kwargs)


def log_error(message: str, **kwargs):
    """Log an error message."""
    logger.error(message, **kwargs)


def log_debug(message: str, **kwargs):
    """Log a debug message."""
    logger.debug(message, **kwargs)


def log_exception(message: str, **kwargs):
    """Log an exception message."""
    logger.exception(message, **kwargs)


def log_critical(message: str, **kwargs):
    """Log a critical message."""
    logger.critical(message, **kwargs)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from granian import Granian

from app.settings import settings
from app.settings.reload_config import RELOAD_CONFIG


def run_server() -> None:
    """启动 Granian 服务。"""
    Granian(
        "app:app",
        interface="asgi",
        address=settings.HOST,
        port=settings.PORT,
        reload=settings.server_reload_enabled,
        **RELOAD_CONFIG,
    ).serve()


if __name__ == "__main__":
    run_server()

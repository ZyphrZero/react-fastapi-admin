#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RequestId 中间件测试（DD-01 §7：生成/透传/响应头回写）

Author: bixuejun(bxjgood@163.com)
Date: 2026-09-24 15:28:33  # 北京时间 UTC+8
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.ctx import CTX_REQUEST_ID
from app.core.middlewares import RequestIdMiddleware


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/probe")
    def probe():
        return {"request_id": CTX_REQUEST_ID.get()}

    return app


class TestRequestIdMiddleware:
    def test_generates_id_and_echoes_header(self) -> None:
        client = TestClient(_make_app())
        response = client.get("/probe")
        assert response.status_code == 200
        echoed = response.headers["X-Request-Id"]
        assert len(echoed) == 16 and int(echoed, 16) >= 0
        assert response.json()["request_id"] == echoed

    def test_incoming_header_is_passed_through(self) -> None:
        client = TestClient(_make_app())
        response = client.get("/probe", headers={"X-Request-Id": "abc123def4567890"})
        assert response.headers["X-Request-Id"] == "abc123def4567890"
        assert response.json()["request_id"] == "abc123def4567890"


def test_validation_error_returns_chinese_message() -> None:
    """422 校验错误经统一异常处理器转为中文可读提示（code=422）。"""
    from fastapi import FastAPI, Query

    from app.core.exceptions import exception_handlers

    app = FastAPI()
    for exc_type, handler in exception_handlers.items():
        app.add_exception_handler(exc_type, handler)

    @app.get("/need")
    def need(keyword: str = Query(...)):
        return {"keyword": keyword}

    response = TestClient(app).get("/need")
    # 脚手架约定：HTTP 状态码与业务 code 一致（BaseResponse(status_code=code)）
    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == 422
    assert "请求参数有误" in payload["msg"]
    assert "keyword" in payload["msg"]

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM 客户端单元测试：导入/构造 + 思考模式参数注入（按服务商分发）

Author: bixuejun(bxjgood@163.com)
Date: 2026-10-19 21:55:00  # 北京时间 UTC+8
"""

from types import SimpleNamespace
from unittest.mock import patch

from app.utils.llm_client import LLMClient, Message, create_llm_client, get_llm_client


def _fake_settings(provider: str, thinking: bool) -> SimpleNamespace:
    return SimpleNamespace(
        LLM_PROVIDER=provider,
        LLM_ENABLE_THINKING=thinking,
        LLM_PRESERVE_THINKING=False,
        LLM_TOOL_CHOICE="none",
        LLM_MAX_TOKENS=128,
        LLM_API_ENABLED=True,
        LLM_API_KEY="k",
        LLM_API_BASE_URL="http://x",
        LLM_DEFAULT_MODEL="m",
        LLM_REQUEST_TIMEOUT=30,
    )


def _client() -> LLMClient:
    return LLMClient(api_key="k", base_url="http://x", default_model="m")


def _messages():
    return [Message(role="user", content="hi")]


class TestLLMClientBasics:
    def test_import_and_defaults(self) -> None:
        client = create_llm_client()
        assert isinstance(client, LLMClient)
        assert get_llm_client() is get_llm_client()  # 单例


class TestBuildPayloadThinking:
    def test_qwen_thinking_on_injects(self) -> None:
        with patch("app.utils.llm_client.settings", _fake_settings("qwen", True)):
            payload = _client()._build_payload(_messages(), model="m")
        assert payload["enable_thinking"] is True
        assert payload["preserve_thinking"] is False
        assert payload["tool_choice"] == "none"

    def test_qwen_thinking_off_no_private_kwargs(self) -> None:
        with patch("app.utils.llm_client.settings", _fake_settings("openai", False)):
            payload = _client()._build_payload(_messages(), model="m")
        assert "enable_thinking" not in payload
        assert "chat_template_kwargs" not in payload
        assert "thinking" not in payload

    def test_deepseek_injects_object_and_template_kwargs(self) -> None:
        with patch("app.utils.llm_client.settings", _fake_settings("deepseek", True)):
            payload = _client()._build_payload(_messages(), model="m")
        assert payload["thinking"] == {"type": "enabled"}
        assert payload["chat_template_kwargs"] == {"thinking": True}


class TestSyncRetryBackoff:
    def test_sync_chat_retries_back_off_via_time_sleep(self) -> None:
        """同步 chat 重试间隔必须真实阻塞（time.sleep），而非未 await 的协程。"""
        from unittest.mock import MagicMock

        good = MagicMock()
        good.raise_for_status.return_value = None
        good.json.return_value = {"choices": [{"message": {"content": "ok"}}], "model": "m", "usage": {}}
        good.text = ""

        attempts = {"n": 0}

        class _FlakyClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def post(self, *args, **kwargs):
                attempts["n"] += 1
                if attempts["n"] == 1:
                    raise RuntimeError("transient (test)")
                return good

        client = LLMClient(api_key="k", base_url="http://x", default_model="m")
        client.max_retries = 3

        with (
            patch("app.utils.llm_client.settings", _fake_settings("qwen", False)),
            patch("app.utils.llm_client.httpx.Client", _FlakyClient),
            patch("app.utils.llm_client.time.sleep") as sleep_mock,
        ):
            response = client.chat(_messages())

        assert response.success is True
        assert attempts["n"] == 2
        sleep_mock.assert_called_once()  # 第一次失败后真实退避一次

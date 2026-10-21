#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project ：
@File    ：llm_client.py
@IDE     ：PyCharm
@Author  ：bixuejun(bxjgood@163.com)
@Date    ：2025/12/14 17:02
@explain : LLM 客户端 - 兼容 OpenAI API
用于 AI 自动分类、智能审计分析、报告生成等功能
"""


import asyncio
import json
import time
from typing import Optional, Dict, List, Any, AsyncIterator, Iterator
from dataclasses import dataclass, field

import httpx
from loguru import logger
from app.settings.config import get_settings

settings = get_settings()

# 服务商私有参数的分发白名单，配置不在其中时不注入任何私有参数
KNOWN_PROVIDERS = ("qwen", "vllm", "openai", "deepseek")

# 启动时打印一次生效配置，便于确认 .env 是否被正确加载（尤其 provider 分支）
logger.info(
    f"[LLM配置] provider={settings.LLM_PROVIDER} base_url={settings.LLM_API_BASE_URL} "
    f"model={settings.LLM_DEFAULT_MODEL} max_tokens={settings.LLM_MAX_TOKENS} "
    f"enable_thinking={settings.LLM_ENABLE_THINKING}"
)
if settings.LLM_PROVIDER.strip().lower() not in KNOWN_PROVIDERS:
    logger.warning(
        f"LLM_PROVIDER={settings.LLM_PROVIDER!r} 不在 {KNOWN_PROVIDERS} 中，"
        f"思考模式等服务商私有参数将不会注入"
    )


@dataclass
class Message:
    """
    消息数据类

    Attributes:
        role: 角色（system/user/assistant）
        content: 消息内容
    """
    role: str
    content: str


@dataclass
class LLMResponse:
    """
    LLM 响应数据类

    Attributes:
        content: 响应内容
        model: 使用的模型
        usage: Token 使用信息
        raw_response: 原始响应
        success: 是否成功
        error: 错误信息
    """
    content: Optional[str] = None
    model: Optional[str] = None
    usage: Dict[str, int] = field(default_factory=dict)
    raw_response: Optional[Dict] = None
    success: bool = True
    error: Optional[str] = None


class LLMClient:
    """
    LLM 客户端 - 兼容 OpenAI API

    支持功能：
    - 同步/异步调用
    - 流式/非流式响应
    - 自动重试机制
    - 超时控制

    使用示例：
        # 同步调用
        client = LLMClient()
        response = client.chat(
            messages=[Message(role="user", content="你好")],
            model="gpt-4"
        )
        print(response.content)

        # 异步调用
        client = LLMClient()
        response = await client.chat_async(
            messages=[Message(role="user", content="你好")],
            model="gpt-4"
        )

        # 流式调用
        async for chunk in client.chat_stream_async(
            messages=[Message(role="user", content="写一首诗")],
            model="gpt-4"
        ):
            print(chunk, end="")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        初始化 LLM 客户端

        Args:
            api_key: API 密钥（默认从配置读取）
            base_url: API 基础 URL（默认从配置读取）
            default_model: 默认模型（默认从配置读取）
            timeout: 请求超时时间（秒，默认从配置读取）
        """
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = (base_url or settings.LLM_API_BASE_URL).rstrip("/")
        self.default_model = default_model or settings.LLM_DEFAULT_MODEL
        self.timeout = timeout or settings.LLM_REQUEST_TIMEOUT
        self.max_retries = 3
        self.retry_delay = 1.0

        if not self.api_key:
            logger.warning("LLM_API_KEY 未配置，LLM 功能将无法使用")

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _log_call(model: str, start: float, usage: Optional[Dict[str, Any]] = None, *, stream: bool = False) -> None:
        """
        统一记录一次 LLM 调用的服务商/模型/耗时/token 用量。

        输出速度(tok/s)是定位「接口慢」的关键指标：耗时高但速度正常说明输出量大，
        速度本身低则是模型服务端的问题。流式响应没有 usage，只记耗时。

        Args:
            model: 本次实际使用的模型名。
            start: 调用开始时的 time.perf_counter() 值。
            usage: 服务端返回的 token 用量，流式为 None。
            stream: 是否流式调用。
        """
        elapsed = time.perf_counter() - start
        usage = usage or {}
        completion = usage.get("completion_tokens") or 0
        speed = f"{completion / elapsed:.1f}" if elapsed > 0 and completion else "-"
        logger.info(
            f"[LLM] provider={settings.LLM_PROVIDER} model={model} "
            f"{'流式' if stream else '非流式'} 耗时={elapsed:.3f}s "
            f"输入={usage.get('prompt_tokens') or 0}tok 输出={completion}tok 速度={speed}tok/s"
        )

    def _build_payload(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        构建请求负载

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数（0-1）
            max_tokens: 最大 token 数
            stream: 是否流式响应
            **kwargs: 其他参数；其中 extra_body 的键会被平铺到请求体顶层

        Returns:
            请求负载字典
        """
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }

        effective_max_tokens = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS
        if effective_max_tokens:
            payload["max_tokens"] = effective_max_tokens

        # 思考模式等私有参数各家 key 不同，按 LLM_PROVIDER 分发。
        # 不按模型名判断：本地部署的 served-model-name 未必含 "qwen"，猜不准。
        provider = settings.LLM_PROVIDER.strip().lower()
        if provider == "qwen":
            payload["enable_thinking"] = settings.LLM_ENABLE_THINKING
            payload["preserve_thinking"] = settings.LLM_PRESERVE_THINKING
            payload["tool_choice"] = settings.LLM_TOOL_CHOICE
        elif provider == "vllm":
            # vLLM 侧思考开关是 chat template 的 Jinja 变量，只认 chat_template_kwargs；
            # 顶层 enable_thinking 会被静默忽略，导致输出进 reasoning_content 或 <think> 混入 content。
            # 变量名各家模板不同：Qwen 是 enable_thinking，DeepSeek V3.1+ 是 thinking，
            # 两个都传，模板用不到的变量会被 Jinja 忽略，互不影响
            payload["chat_template_kwargs"] = {
                "enable_thinking": settings.LLM_ENABLE_THINKING,
                "thinking": settings.LLM_ENABLE_THINKING,
            }
        elif provider == "deepseek":
            # DeepSeek 官方 API 使用对象形式的思考模式开关
            payload["thinking"] = {"type": "enabled" if settings.LLM_ENABLE_THINKING else "disabled"}
            # 自部署网关（vLLM/SGLang 等）走 chat template，变量名是 thinking；
            # 顶层 thinking 对象会被这类网关静默忽略，导致输出全进 reasoning_content
            payload["chat_template_kwargs"] = {"thinking": settings.LLM_ENABLE_THINKING}

        # 这里是裸 httpx 直发，没有 OpenAI SDK 把 extra_body 展开到顶层，需自行平铺，
        # 否则 top_k 等采样参数会作为未知字段被服务端忽略
        caller_extra_body = kwargs.pop("extra_body", None)
        if caller_extra_body:
            payload.update(caller_extra_body)

        # 调用方显式传参优先级最高，覆盖上面的服务商默认值
        payload.update(kwargs)

        # 各调用方按 DashScope 约定传 top_k=0 表示禁用，但 vLLM 类网关要求 -1 或 >=1，
        # 传 0 会被 400 拒绝（错误体还裹在 200 响应里）；温度=0 时本就等价贪心解码，直接去掉
        if payload.get("top_k") == 0:
            payload.pop("top_k")
        # result_format 是 DashScope 私有参数，非 qwen 网关可能校验失败
        if provider != "qwen":
            payload.pop("result_format", None)

        # 打印真实发出的参数（messages 另有 prompt 日志，此处排除），
        # 用于确认 chat_template_kwargs / top_k 等服务商私有参数确实带上了
        logger.info(
            f"[LLM请求参数] provider={provider} "
            f"{json.dumps({k: v for k, v in payload.items() if k != 'messages'}, ensure_ascii=False, default=str)}"
        )

        return payload

    def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        同步方式调用 LLM

        Args:
            messages: 消息列表
            model: 模型名称（默认使用 default_model）
            temperature: 温度参数（0-1）
            max_tokens: 最大 token 数
            **kwargs: 其他参数

        Returns:
            LLMResponse 对象
        """
        if not settings.LLM_API_ENABLED:
            return LLMResponse(success=False, error="LLM 服务未启用")

        if not self.api_key:
            return LLMResponse(success=False, error="API Key 未配置")

        model = model or self.default_model
        payload = self._build_payload(messages, model, temperature, max_tokens, False, **kwargs)

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._build_headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                    if not data.get("choices"):
                        # 网关可能用 200 返回错误对象，把原始响应体打出来定位根因
                        logger.error(f"LLM 响应缺少 choices，原始响应体: {response.text[:2000]}")

                    return LLMResponse(
                        content=data["choices"][0]["message"]["content"],
                        model=data.get("model", model),
                        usage=data.get("usage", {}),
                        raw_response=data,
                        success=True,
                    )

            except httpx.HTTPStatusError as e:
                logger.error(f"LLM API 请求失败: {e.response.status_code} - {e.response.text}")
                if attempt == self.max_retries - 1:
                    return LLMResponse(
                        success=False,
                        error=f"HTTP 错误: {e.response.status_code}"
                    )
            except Exception as e:
                logger.error(f"LLM 调用异常: {str(e)}")
                if attempt == self.max_retries - 1:
                    return LLMResponse(success=False, error=str(e))

            # 重试前等待（同步路径用 time.sleep 真实阻塞；源处 asyncio.sleep 未 await 属潜伏 bug）
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))

        return LLMResponse(success=False, error="达到最大重试次数")

    async def chat_async(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        异步方式调用 LLM

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            **kwargs: 其他参数

        Returns:
            LLMResponse 对象
        """
        if not settings.LLM_API_ENABLED:
            return LLMResponse(success=False, error="LLM 服务未启用")

        if not self.api_key:
            return LLMResponse(success=False, error="API Key 未配置")

        model = model or self.default_model
        payload = self._build_payload(messages, model, temperature, max_tokens, False, **kwargs)
        call_start = time.perf_counter()

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._build_headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                    usage = data.get("usage", {}) or {}
                    self._log_call(data.get("model", model), call_start, usage)

                    if not data.get("choices"):
                        # 网关可能用 200 返回错误对象，把原始响应体打出来定位根因
                        logger.error(f"LLM 响应缺少 choices，原始响应体: {response.text[:2000]}")
                    elif not data["choices"][0].get("message", {}).get("content"):
                        # content 为空多半是思考模式没关、token 全花在 reasoning_content 上，
                        # 打出原始 message 便于确认
                        logger.error(
                            f"LLM 返回 content 为空，原始 message: "
                            f"{json.dumps(data['choices'][0].get('message', {}), ensure_ascii=False)[:2000]}"
                        )

                    return LLMResponse(
                        content=data["choices"][0]["message"]["content"],
                        model=data.get("model", model),
                        usage=usage,
                        raw_response=data,
                        success=True,
                    )

            except httpx.HTTPStatusError as e:
                response_text = e.response.text[:500] if e.response.text else "无响应内容"
                logger.error(f"LLM API 请求失败: {e.response.status_code} - 响应: {response_text}")
                if attempt == self.max_retries - 1:
                    return LLMResponse(
                        success=False,
                        error=f"HTTP 错误: {e.response.status_code}"
                    )
            except Exception as e:
                logger.error(f"LLM 调用异常({attempt}/{self.max_retries-1}): {str(e)}")
                if attempt == self.max_retries - 1:
                    return LLMResponse(success=False, error=str(e))

            # 重试前等待
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        logger.error(f"LLM 调用异常,达到最大重试次数({self.max_retries})")
        return LLMResponse(success=False, error="达到最大重试次数")

    def chat_stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        同步流式调用 LLM

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            **kwargs: 其他参数

        Yields:
            响应内容片段
        """
        if not settings.LLM_API_ENABLED:
            yield "[LLM 服务未启用]"
            return

        if not self.api_key:
            yield "[API Key 未配置]"
            return

        model = model or self.default_model
        payload = self._build_payload(messages, model, temperature, max_tokens, True, **kwargs)

        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._build_headers(),
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if line.strip():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    data = json.loads(data_str)
                                    choices = data.get("choices") or []
                                    if not choices:
                                        continue
                                    choice = choices[0]
                                    if not isinstance(choice, dict):
                                        continue
                                    delta = choice.get("delta", {}) or {}
                                    if not isinstance(delta, dict):
                                        continue
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    continue

        except Exception as e:
            logger.error(f"LLM 流式调用异常: {str(e)}")
            yield f"[错误: {str(e)}]"

    async def chat_stream_async(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        raise_on_error: bool = False,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        异步流式调用 LLM

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            raise_on_error: 为 True 时将配置与流式调用异常抛出，避免错误文本混入业务正文。
            **kwargs: 其他参数

        Yields:
            响应内容片段
        """
        if not settings.LLM_API_ENABLED:
            if raise_on_error:
                raise RuntimeError("LLM 服务未启用")
            yield "[LLM 服务未启用]"
            return

        if not self.api_key:
            if raise_on_error:
                raise RuntimeError("API Key 未配置")
            yield "[API Key 未配置]"
            return

        model = model or self.default_model
        payload = self._build_payload(messages, model, temperature, max_tokens, True, **kwargs)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._build_headers(),
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.strip():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    data = json.loads(data_str)
                                    choices = data.get("choices") or []
                                    if not choices:
                                        continue
                                    choice = choices[0]
                                    if not isinstance(choice, dict):
                                        continue
                                    delta = choice.get("delta", {}) or {}
                                    if not isinstance(delta, dict):
                                        continue
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    continue

        except Exception as e:
            logger.error(f"LLM 流式调用异常: {str(e)}")
            if raise_on_error:
                raise
            yield f"[错误: {str(e)}]"

    def chat_with_json(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        调用 LLM 并解析 JSON 响应

        适用于需要结构化输出的场景（如分类结果）

        Args:
            messages: 消息列表
            model: 模型名称
            **kwargs: 其他参数

        Returns:
            LLMResponse 对象，content 包含解析后的 JSON 字典
        """
        response = self.chat(messages, model, **kwargs)

        if not response.success or not response.content:
            return response

        try:
            # 尝试从 markdown 代码块中提取 JSON
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            json_data = json.loads(content.strip())
            response.content = json_data
            return response

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {str(e)}, 原始内容: {response.content[:200]}")
            return LLMResponse(
                success=False,
                error=f"JSON 解析失败: {str(e)}"
            )


# 便捷函数
def create_llm_client() -> LLMClient:
    """创建 LLM 客户端实例"""
    return LLMClient()


# 全局单例客户端
_llm_client_instance: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    获取全局 LLM 客户端实例（单例模式）

    Returns:
        LLMClient 实例
    """
    global _llm_client_instance
    if _llm_client_instance is None:
        _llm_client_instance = LLMClient()
    return _llm_client_instance

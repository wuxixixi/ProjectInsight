"""
LLM 客户端封装
支持 OpenAI 兼容 API 的异步调用，高并发优化版本
"""
import asyncio
import aiohttp
import json
import os
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import logging
import random
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

logger = logging.getLogger(__name__)


def get_env_str(key: str, default: str) -> str:
    """获取字符串类型的环境变量"""
    return os.getenv(key, default)


def get_env_int(key: str, default: int) -> int:
    """获取整数类型的环境变量"""
    val = os.getenv(key)
    return int(val) if val else default


@dataclass
class LLMConfig:
    """LLM 配置 - 从环境变量读取默认值"""
    base_url: str = field(default_factory=lambda: get_env_str("LLM_BASE_URL", ""))
    api_key: str = field(default_factory=lambda: get_env_str("LLM_API_KEY", ""))
    model: str = field(default_factory=lambda: get_env_str("LLM_MODEL", "Qwen2.5-32B-Instruct"))
    max_concurrent: int = field(default_factory=lambda: get_env_int("LLM_MAX_CONCURRENT", 100))
    timeout: int = field(default_factory=lambda: get_env_int("LLM_TIMEOUT", 60))
    max_retries: int = field(default_factory=lambda: get_env_int("LLM_MAX_RETRIES", 5))
    temperature: float = 0.7
    max_tokens: int = 150
    seed: int = 42  # 随机种子（用于抖动等，issue #527）

    # 连接池配置
    connection_pool_size: int = 500  # 连接池大小
    connection_keepalive: int = 30  # 连接保持时间(秒)

    # 指数退避配置
    base_backoff: float = 1.0  # 基础退避时间(秒)
    max_backoff: float = 32.0  # 最大退避时间(秒)
    jitter: bool = True  # 是否添加随机抖动

    # 优先级标记（用于日志区分）
    priority: bool = False  # 是否为高优先级请求


def create_priority_llm_client() -> 'LLMClient':
    """
    创建高优先级 LLM 客户端，用于事件解析等关键任务

    特点：
    - 独立的 Semaphore，不受推演并发池影响
    - 更短的超时（30秒），快速失败
    - 更少的重试次数（2次）
    - 并发数较高，保证事件解析快速完成
    """
    config = LLMConfig(
        max_concurrent=20,  # 高并发，优先级通道不受推演阻塞
        timeout=60,         # 推演中服务端负载高，需要更长超时
        max_retries=3,      # 增加重试次数，提高成功率
        priority=True       # 标记为高优先级
    )
    return LLMClient(config)


class LLMClient:
    """
    异步 LLM 客户端 - 高并发优化版本

    特性:
    - OpenAI 兼容 API
    - 异步批量调用
    - 高并发控制 (Semaphore + 连接池)
    - 指数退避重试机制
    - 60秒超时控制
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        # 并发控制信号量
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._session: Optional[aiohttp.ClientSession] = None
        # 统计信息
        self._request_count = 0
        self._success_count = 0
        self._retry_count = 0
        # 实例级随机生成器 (issue #527)
        self._rng = random.Random(self.config.seed)

    async def __aenter__(self):
        # 配置连接池，解除默认限制
        connector = aiohttp.TCPConnector(
            limit=self.config.connection_pool_size,  # 总连接数限制
            limit_per_host=self.config.connection_pool_size,  # 每个host的连接数
            keepalive_timeout=self.config.connection_keepalive,
            enable_cleanup_closed=True,
            force_close=False,  # 复用连接
        )

        # 对于长耗时任务（如报告生成），socket读取超时需要与总超时一致
        sock_read_timeout = max(self.config.timeout - 10, 60)  # 留10秒给连接建立
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(
                total=self.config.timeout,
                connect=10,  # 连接超时10秒
                sock_read=sock_read_timeout  # socket读取超时，动态计算
            ),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
            self._session = None

    def _calculate_backoff(self, attempt: int) -> float:
        """
        计算指数退避时间

        Args:
            attempt: 当前重试次数

        Returns:
            等待时间(秒)
        """
        # 指数退避: base * 2^attempt
        backoff = self.config.base_backoff * (2 ** attempt)
        # 限制最大退避时间
        backoff = min(backoff, self.config.max_backoff)

        # 添加随机抖动，避免惊群效应
        if self.config.jitter:
            backoff = backoff * (0.5 + self._rng.random())

        return backoff

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        单次聊天请求，带指数退避重试

        Args:
            messages: OpenAI 格式的消息列表
            temperature: 温度参数
            max_tokens: 最大生成 token 数

        Returns:
            完整的 API 响应
        """
        if not self._session:
            raise RuntimeError("请使用 async with 上下文管理器")

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }

        self._request_count += 1
        last_error = None

        # 使用信号量控制并发
        async with self._semaphore:
            for attempt in range(self.config.max_retries + 1):
                try:
                    async with self._session.post(
                        f"{self.config.base_url}/chat/completions",
                        json=payload
                    ) as response:
                        if response.status == 200:
                            self._success_count += 1
                            return await response.json()

                        elif response.status == 429:  # 限流
                            self._retry_count += 1
                            wait_time = self._calculate_backoff(attempt)
                            logger.warning(
                                f"[重试 {attempt+1}/{self.config.max_retries}] "
                                f"API 限流，等待 {wait_time:.2f}s 后重试"
                            )
                            await asyncio.sleep(wait_time)

                        elif response.status >= 500:  # 服务端错误，可重试
                            self._retry_count += 1
                            wait_time = self._calculate_backoff(attempt)
                            logger.warning(
                                f"[重试 {attempt+1}/{self.config.max_retries}] "
                                f"服务端错误 {response.status}，等待 {wait_time:.2f}s 后重试"
                            )
                            await asyncio.sleep(wait_time)

                        else:  # 其他错误，不重试
                            error = await response.text()
                            logger.error(f"LLM API 错误: {response.status} - {error}")
                            raise Exception(f"LLM API 错误: {response.status}")

                except asyncio.TimeoutError as e:
                    last_error = e
                    self._retry_count += 1
                    if attempt < self.config.max_retries:
                        wait_time = self._calculate_backoff(attempt)
                        logger.warning(
                            f"[重试 {attempt+1}/{self.config.max_retries}] "
                            f"请求超时，等待 {wait_time:.2f}s 后重试"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"请求超时，已达最大重试次数")
                        raise Exception(f"请求超时: {self.config.timeout}s")

                except aiohttp.ClientError as e:
                    last_error = e
                    self._retry_count += 1
                    if attempt < self.config.max_retries:
                        wait_time = self._calculate_backoff(attempt)
                        logger.warning(
                            f"[重试 {attempt+1}/{self.config.max_retries}] "
                            f"网络错误: {e}，等待 {wait_time:.2f}s 后重试"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"网络错误，已达最大重试次数: {e}")
                        raise

        raise Exception(f"LLM 调用失败，已达最大重试次数: {last_error}")

    def _parse_json_content(self, content: str) -> Dict[str, Any]:
        """
        从 LLM 生成的文本中提取并解析 JSON
        """
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            text = content.strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # 容错：提取首个 JSON 对象，兼容模型在 JSON 前后夹带解释文本
                match = re.search(r"\{[\s\S]*\}", text)
                if match:
                    return json.loads(match.group(0))
                raise
        except (json.JSONDecodeError, IndexError):
            logger.warning(f"JSON 解析失败: {content}")
            return {"raw_content": content}

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        聊天并解析 JSON 响应
        自动提取 JSON 内容，同时保留原始响应信息
        """
        response = await self.chat(messages, **kwargs)
        content = response["choices"][0]["message"]["content"]
        parsed = self._parse_json_content(content)

        # 返回解析后的 JSON，同时保留原始响应信息
        return {
            **parsed,  # 解析后的字段（new_opinion, reasoning等）
            "_raw_response": {
                "content": content,
                "model": response.get("model"),
                "usage": response.get("usage"),
                "id": response.get("id")
            }
        }

    async def batch_chat(
        self,
        batch_messages: List[List[Dict[str, str]]],
        progress_callback: Optional[callable] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        批量聊天请求
        使用 asyncio.gather 并行执行，受信号量限制

        Args:
            batch_messages: 多组消息列表
            progress_callback: 进度回调函数 (completed, total)

        Returns:
            所有响应列表
        """
        total = len(batch_messages)
        completed = 0
        results = []

        async def chat_with_progress(messages):
            nonlocal completed
            result = await self.chat(messages, **kwargs)
            completed += 1
            if progress_callback:
                await progress_callback(completed, total)
            return result

        tasks = [chat_with_progress(messages) for messages in batch_messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤异常并记录日志
        success_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.warning(f"batch_chat: 请求 {i}/{total} 失败: {r}")
            else:
                success_results.append(r)

        return success_results

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        流式聊天请求 (生成器)

        Args:
            messages: OpenAI 格式的消息列表
            temperature: 温度参数
            max_tokens: 最大生成 token 数

        Yields:
            str: 每个 token 文本片段
        """
        if not self._session:
            raise RuntimeError("请使用 async with 上下文管理器")

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True  # 启用流式输出
        }

        self._request_count += 1

        async with self._semaphore:
            try:
                async with self._session.post(
                    f"{self.config.base_url}/chat/completions",
                    json=payload
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        logger.error(f"LLM API 错误: {response.status} - {error}")
                        raise Exception(f"LLM API 错误: {response.status}")

                    self._success_count += 1

                    # 读取 SSE 流
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if not line:
                            continue
                        if line.startswith('data: '):
                            data = line[6:]  # 去掉 "data: " 前缀
                            if data == '[DONE]':
                                break
                            try:
                                chunk = json.loads(data)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        yield content
                            except json.JSONDecodeError as e:
                                logger.debug(f"SSE 数据解析失败: {data[:100]}... 错误: {e}")
                                continue

            except asyncio.TimeoutError:
                logger.error("流式请求超时")
                raise Exception(f"请求超时: {self.config.timeout}s")
            except aiohttp.ClientError as e:
                logger.error(f"网络错误: {e}")
                raise

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            "total_requests": self._request_count,
            "successful": self._success_count,
            "retries": self._retry_count,
            "success_rate": self._success_count / max(self._request_count, 1)
        }


# 全局客户端实例
_llm_client: Optional[LLMClient] = None
_llm_client_lock = __import__('threading').Lock()


def get_llm_client(config: Optional[LLMConfig] = None) -> LLMClient:
    """获取全局 LLM 客户端实例（线程安全）"""
    global _llm_client
    if _llm_client is None:
        with _llm_client_lock:
            if _llm_client is None:
                _llm_client = LLMClient(config)
    return _llm_client

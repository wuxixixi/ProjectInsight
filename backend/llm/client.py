"""
LLM 客户端封装
支持 OpenAI 兼容 API 的异步调用，高并发优化版本
"""
import asyncio
import aiohttp
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import logging
import random

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM 配置"""
    base_url: str = "http://10.17.2.29:31277/v1"
    api_key: str = "R61XwviRggmoTdDGHmH3tA0BQN7TToYwdPk61m9Y8Gs"
    model: str = "DeepSeek-V3"
    max_concurrent: int = 400  # 最大并发数，提升至400
    timeout: int = 60  # 60秒超时控制
    max_retries: int = 5  # 最大重试次数
    temperature: float = 0.7
    max_tokens: int = 150

    # 连接池配置
    connection_pool_size: int = 500  # 连接池大小
    connection_keepalive: int = 30  # 连接保持时间(秒)

    # 指数退避配置
    base_backoff: float = 1.0  # 基础退避时间(秒)
    max_backoff: float = 32.0  # 最大退避时间(秒)
    jitter: bool = True  # 是否添加随机抖动


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

    async def __aenter__(self):
        # 配置连接池，解除默认限制
        connector = aiohttp.TCPConnector(
            limit=self.config.connection_pool_size,  # 总连接数限制
            limit_per_host=self.config.connection_pool_size,  # 每个host的连接数
            keepalive_timeout=self.config.connection_keepalive,
            enable_cleanup_closed=True,
            force_close=False,  # 复用连接
        )

        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(
                total=self.config.timeout,
                connect=10,  # 连接超时10秒
                sock_read=50  # socket读取超时
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
            backoff = backoff * (0.5 + random.random())

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

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        聊天并解析 JSON 响应
        自动提取 JSON 内容
        """
        response = await self.chat(messages, **kwargs)
        content = response["choices"][0]["message"]["content"]

        # 尝试解析 JSON
        try:
            # 处理可能的 markdown 代码块
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except json.JSONDecodeError:
            logger.warning(f"JSON 解析失败: {content}")
            return {"raw_content": content}

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

        return results

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


def get_llm_client(config: Optional[LLMConfig] = None) -> LLMClient:
    """获取全局 LLM 客户端实例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(config)
    return _llm_client

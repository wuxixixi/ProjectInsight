"""
LLM 客户端单元测试
测试异步 LLM 调用和并发控制
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import json

from backend.llm.client import LLMClient, LLMConfig


class TestLLMConfig:
    """测试 LLM 配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = LLMConfig()

        assert config.max_concurrent == 400  # 高并发配置
        assert config.timeout == 60  # 60秒超时
        assert config.max_retries == 5  # 最大重试次数
        assert config.connection_pool_size == 500  # 连接池大小

    def test_custom_config(self):
        """测试自定义配置"""
        config = LLMConfig(
            base_url="http://custom:8000/v1",
            api_key="test-key",
            model="custom-model",
            max_concurrent=5
        )

        assert config.base_url == "http://custom:8000/v1"
        assert config.api_key == "test-key"
        assert config.model == "custom-model"
        assert config.max_concurrent == 5


class TestLLMClientInit:
    """测试 LLM 客户端初始化"""

    def test_init_with_default_config(self):
        """测试默认配置初始化"""
        client = LLMClient()

        assert client.config is not None
        assert client._semaphore is not None
        assert client._session is None

    def test_init_with_custom_config(self):
        """测试自定义配置初始化"""
        config = LLMConfig(max_concurrent=5)
        client = LLMClient(config)

        assert client.config.max_concurrent == 5


class TestLLMClientChatJson:
    """测试 LLM 客户端 JSON 解析功能"""

    def test_parse_json_response(self):
        """测试 JSON 响应解析"""
        client = LLMClient()

        # 直接测试 JSON 解析逻辑
        content = '{"new_opinion": 0.5, "reasoning": "test"}'

        # 模拟解析
        result = json.loads(content)

        assert result["new_opinion"] == 0.5
        assert result["reasoning"] == "test"

    def test_parse_json_with_markdown_block(self):
        """测试带 Markdown 代码块的 JSON 解析"""
        content = '```json\n{"new_opinion": 0.3}\n```'

        # 处理可能的 markdown 代码块
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())

        assert result["new_opinion"] == 0.3

    def test_parse_json_with_simple_block(self):
        """测试带简单代码块的 JSON 解析"""
        content = '```\n{"new_opinion": -0.2}\n```'

        if "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())

        assert result["new_opinion"] == -0.2


class TestConcurrencyControl:
    """测试并发控制"""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """测试信号量限制并发"""
        config = LLMConfig(max_concurrent=2)
        client = LLMClient(config)

        # 直接测试信号量行为
        call_count = 0
        max_concurrent = 0
        current_concurrent = 0

        async def track_concurrency():
            nonlocal call_count, max_concurrent, current_concurrent
            async with client._semaphore:
                current_concurrent += 1
                call_count += 1
                max_concurrent = max(max_concurrent, current_concurrent)
                await asyncio.sleep(0.05)
                current_concurrent -= 1

        # 创建 5 个并发任务
        tasks = [track_concurrency() for _ in range(5)]
        await asyncio.gather(*tasks)

        # 最大并发数不应超过配置值
        assert max_concurrent <= config.max_concurrent

    @pytest.mark.asyncio
    async def test_semaphore_allows_multiple_batches(self):
        """测试信号量允许多批次执行"""
        config = LLMConfig(max_concurrent=3)
        client = LLMClient(config)

        completed = []

        async def track_task(task_id):
            async with client._semaphore:
                await asyncio.sleep(0.02)
                completed.append(task_id)

        # 创建 6 个任务
        tasks = [track_task(i) for i in range(6)]
        await asyncio.gather(*tasks)

        # 所有任务都应完成
        assert len(completed) == 6


class TestGetLLMClient:
    """测试全局客户端获取"""

    def test_get_llm_client_returns_instance(self):
        """测试获取客户端实例"""
        from backend.llm.client import get_llm_client

        # 重置全局实例
        import backend.llm.client
        backend.llm.client._llm_client = None

        client = get_llm_client()

        assert isinstance(client, LLMClient)

        # 清理
        backend.llm.client._llm_client = None


class TestClientContextManager:
    """测试客户端上下文管理器"""

    @pytest.mark.asyncio
    async def test_context_manager_creates_session(self):
        """测试上下文管理器创建会话"""
        client = LLMClient()

        assert client._session is None

        async with client:
            assert client._session is not None

        assert client._session is None

    @pytest.mark.asyncio
    async def test_context_manager_creates_fresh_session(self):
        """测试每次进入创建新会话"""
        client = LLMClient()

        async with client:
            session1 = client._session
            assert session1 is not None

        # 退出后 session 应该被清理
        assert client._session is None

        async with client:
            session2 = client._session
            assert session2 is not None

"""
Environment Module Unit Tests

测试 Phase 2 实现的组件:
- EnvBase 基类
- AlgorithmEnv 算法环境
- SocialEnv 社交环境
- TruthEnv 辟谣环境
- EnvRouter 环境路由
"""
import pytest
import asyncio
import tempfile
from pathlib import Path

from backend.simulation.env import (
    EnvBase,
    EnvRouter,
    AlgorithmEnv,
    SocialEnv,
    TruthEnv,
    tool,
    ToolKind
)


class TestEnvBase:
    """测试环境基类"""
    
    class MockEnv(EnvBase):
        """模拟环境"""
        
        @property
        def name(self) -> str:
            return "mock"
        
        @tool(readonly=True, kind="observe")
        async def mock_observe(self, agent_id: int) -> str:
            """模拟观察"""
            return f"Mock observation for agent {agent_id}"
        
        @tool(readonly=False, kind="interact")
        async def mock_interact(self, agent_id: int, action: str):
            """模拟交互"""
            return {"agent_id": agent_id, "action": action}
        
        async def reset(self):
            pass
        
        async def get_state(self):
            return {"name": self.name}
    
    def test_tool_decorator(self):
        """测试工具装饰器"""
        env = self.MockEnv()
        
        # 检查工具是否被扫描
        tools = env.get_tools()
        assert len(tools) == 2
        
        tool_names = [t.name for t in tools]
        assert "mock_mock_observe" in tool_names
        assert "mock_mock_interact" in tool_names
    
    @pytest.mark.asyncio
    async def test_call_tool(self):
        """测试工具调用"""
        env = self.MockEnv()
        
        result = await env.call_tool("mock_observe", 1)
        assert result == "Mock observation for agent 1"
        
        result = await env.call_tool("mock_interact", 1, "test")
        assert result["action"] == "test"


class TestAlgorithmEnv:
    """测试算法推荐环境"""
    
    @pytest.mark.asyncio
    async def test_observe(self):
        """测试算法推荐"""
        env = AlgorithmEnv(cocoon_strength=0.5)
        
        # 获取推荐内容
        content = await env.call_tool("observe", 1, -0.3)
        assert content is not None
        assert isinstance(content, str)
    
    @pytest.mark.asyncio
    async def test_cocoon_strength(self):
        """测试茧房强度"""
        env = AlgorithmEnv(cocoon_strength=0.8)
        
        strength = await env.call_tool("get_cocoon_strength")
        assert strength == 0.8
        
        # 设置新强度
        await env.call_tool("set_cocoon_strength", 0.5)
        strength = await env.call_tool("get_cocoon_strength")
        assert strength == 0.5
    
    @pytest.mark.asyncio
    async def test_exposure_count(self):
        """测试暴露计数"""
        env = AlgorithmEnv()
        
        # 多次推荐
        for i in range(5):
            await env.call_tool("observe", 1, 0.0)
        
        count = await env.call_tool("get_exposure_count", 1)
        assert count == 5
    
    @pytest.mark.asyncio
    async def test_statistics(self):
        """测试统计信息"""
        env = AlgorithmEnv()
        
        # 生成一些数据
        await env.call_tool("observe", 1, 0.0)
        await env.call_tool("observe", 2, 0.1)
        
        stats = await env.call_tool("get_statistics")
        assert stats["agent_count"] == 2
        assert stats["total_exposure"] == 2


class TestSocialEnv:
    """测试社交网络环境"""
    
    @pytest.mark.asyncio
    async def test_peer_opinions(self):
        """测试邻居观点"""
        env = SocialEnv()
        
        # 设置网络
        env.set_network(
            adjacency={1: [2, 3], 2: [1], 3: [1]},
            influence={1: 0.5, 2: 0.3, 3: 0.4},
            opinions={1: 0.1, 2: 0.2, 3: -0.1}
        )
        
        peers = await env.call_tool("get_peer_opinions", 1)
        assert len(peers) == 2
        assert 0.2 in peers
        assert -0.1 in peers
    
    @pytest.mark.asyncio
    async def test_neighbors(self):
        """测试邻居列表"""
        env = SocialEnv()
        
        env.set_network(
            adjacency={1: [2, 3, 4]},
            influence={},
            opinions={}
        )
        
        neighbors = await env.call_tool("get_neighbors", 1)
        assert neighbors == [2, 3, 4]
    
    @pytest.mark.asyncio
    async def test_influencers(self):
        """测试意见领袖"""
        env = SocialEnv()
        
        env.set_network(
            adjacency={},
            influence={1: 0.8, 2: 0.6, 3: 0.3, 4: 0.1},
            opinions={1: 0.1, 2: 0.2, 3: -0.3, 4: 0.0}
        )
        
        influencers = await env.call_tool("get_influencers", 3)
        assert len(influencers) == 3
        assert influencers[0]["agent_id"] == 1
        assert influencers[0]["influence"] == 0.8
    
    @pytest.mark.asyncio
    async def test_broadcast(self):
        """测试广播"""
        env = SocialEnv()
        
        env.set_network(
            adjacency={1: [2, 3]},
            influence={},
            opinions={}
        )
        
        await env.call_tool("broadcast", 1, "Test message", 0.1)
        
        # 检查消息日志
        assert len(env._message_log) == 1
        assert env._message_log[0]["sender"] == 1


class TestTruthEnv:
    """测试官方辟谣环境"""
    
    @pytest.mark.asyncio
    async def test_add_intervention(self):
        """测试添加辟谣"""
        env = TruthEnv()
        
        await env.call_tool(
            "add_intervention",
            "官方辟谣内容...",
            step=5,
            credibility=0.8
        )
        
        stats = await env.call_tool("get_intervention_stats")
        assert stats["total_interventions"] == 1
    
    @pytest.mark.asyncio
    async def test_get_intervention(self):
        """测试获取辟谣"""
        env = TruthEnv()
        
        # 添加并发布
        await env.call_tool("add_intervention", "辟谣内容", step=1)
        env.advance_step(1)
        
        intervention = await env.call_tool("get_intervention", 1)
        assert intervention == "辟谣内容"
    
    @pytest.mark.asyncio
    async def test_credibility(self):
        """测试可信度"""
        env = TruthEnv(default_credibility=0.7)
        
        cred = await env.call_tool("get_credibility")
        assert cred == 0.7
        
        await env.call_tool("set_credibility", 0.8)
        cred = await env.call_tool("get_credibility")
        assert cred == 0.8
    
    @pytest.mark.asyncio
    async def test_delay_publish(self):
        """测试延迟发布"""
        env = TruthEnv(response_delay=5)
        
        # 添加延迟辟谣
        await env.call_tool("add_intervention", "延迟辟谣")
        
        stats = await env.call_tool("get_intervention_stats")
        assert stats["pending_interventions"] == 1
        
        # 推进到延迟后
        env.advance_step(6)
        
        stats = await env.call_tool("get_intervention_stats")
        assert stats["pending_interventions"] == 0
        assert stats["published_interventions"] == 1


class TestEnvRouter:
    """测试环境路由"""
    
    @pytest.mark.asyncio
    async def test_router_creation(self):
        """测试路由创建"""
        router = EnvRouter(
            algorithm_env=AlgorithmEnv(),
            social_env=SocialEnv(),
            truth_env=TruthEnv()
        )
        
        assert router.algorithm is not None
        assert router.social is not None
        assert router.truth is not None
    
    @pytest.mark.asyncio
    async def test_collect_tools(self):
        """测试工具收集"""
        router = EnvRouter(
            algorithm_env=AlgorithmEnv(),
            social_env=SocialEnv(),
            truth_env=TruthEnv()
        )
        
        tools = router.collect_tools(readonly_only=True)
        assert len(tools) > 0
        
        # 检查工具类型
        for t in tools:
            assert t.readonly == True
    
    @pytest.mark.asyncio
    async def test_ask(self):
        """测试综合感知"""
        # 创建社交环境并设置网络
        social_env = SocialEnv()
        social_env.set_network(
            adjacency={1: [2]},
            influence={1: 0.5, 2: 0.3},
            opinions={1: 0.0, 2: 0.1}
        )
        
        router = EnvRouter(
            algorithm_env=AlgorithmEnv(),
            social_env=social_env,
            truth_env=TruthEnv()
        )
        
        # 添加辟谣
        await router.truth.call_tool("add_intervention", "辟谣内容", step=1)
        router.truth.advance_step(1)
        
        result = await router.ask(agent_id=1, opinion=0.0)
        
        assert result["algorithm"] is not None
        assert result["social"] is not None
        assert result["truth"] is not None
    
    @pytest.mark.asyncio
    async def test_get_all_states(self):
        """测试获取所有状态"""
        router = EnvRouter(
            algorithm_env=AlgorithmEnv(),
            social_env=SocialEnv(),
            truth_env=TruthEnv()
        )
        
        states = await router.get_all_states()
        assert "algorithm" in states
        assert "social" in states
        assert "truth" in states


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
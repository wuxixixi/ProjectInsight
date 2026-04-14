"""
LLM Agent 单元测试
测试 LLM 驱动的智能体
"""
import pytest
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from backend.simulation.llm_agents import LLMAgent, LLMAgentPopulation
from backend.llm.client import LLMConfig


class TestLLMAgent:
    """测试 LLM 智能体"""

    def test_agent_initialization(self):
        """测试智能体初始化"""
        agent = LLMAgent(
            agent_id=0,
            opinion=-0.5,
            belief_strength=0.6,
            influence=0.8,
            susceptibility=0.3
        )

        assert agent.id == 0
        assert agent.opinion == -0.5
        assert agent.belief_strength == 0.6
        assert agent.influence == 0.8
        assert agent.susceptibility == 0.3
        assert agent.exposed_to_rumor is True  # opinion < -0.2
        assert agent.exposed_to_truth is False

    def test_agent_to_dict(self):
        """测试智能体序列化"""
        agent = LLMAgent(
            agent_id=1,
            opinion=0.3,
            belief_strength=0.5,
            influence=0.7,
            susceptibility=0.4
        )

        result = agent.to_dict()

        assert result["id"] == 1
        assert result["opinion"] == 0.3
        assert result["belief_strength"] == 0.5
        assert result["influence"] == 0.7
        assert result["susceptibility"] == 0.4

    def test_build_prompt_basic(self):
        """测试 Prompt 构建"""
        agent = LLMAgent(
            agent_id=0,
            opinion=-0.5,
            belief_strength=0.6,
            influence=0.8,
            susceptibility=0.3
        )

        # 创建模拟邻居 Agent
        neighbor1 = MagicMock()
        neighbor1.id = 1
        neighbor1.opinion = 0.2
        neighbor1.is_silent = False
        neighbor2 = MagicMock()
        neighbor2.id = 2
        neighbor2.opinion = -0.3
        neighbor2.is_silent = False
        neighbor3 = MagicMock()
        neighbor3.id = 3
        neighbor3.opinion = 0.1
        neighbor3.is_silent = False

        prompt, _ = agent.build_prompt(
            neighbor_agents=[neighbor1, neighbor2, neighbor3],
            debunk_released=False,
            cocoon_strength=0.5
        )

        assert "当前观点: -0.50" in prompt
        assert "信念强度: 0.60" in prompt
        assert "邻居" in prompt

    def test_build_prompt_with_debunk(self):
        """测试带辟谣的 Prompt 构建"""
        agent = LLMAgent(
            agent_id=0,
            opinion=-0.5,
            belief_strength=0.6,
            influence=0.8,
            susceptibility=0.3
        )

        neighbor = MagicMock()
        neighbor.id = 1
        neighbor.opinion = 0.2
        neighbor.is_silent = False

        prompt, _ = agent.build_prompt(
            neighbor_agents=[neighbor],
            debunk_released=True,
            cocoon_strength=0.5
        )

        assert "辟谣" in prompt or "真相" in prompt or "官方" in prompt

    def test_build_prompt_with_cocoon(self):
        """测试带茧房效应的 Prompt 构建"""
        agent_rumor = LLMAgent(
            agent_id=0, opinion=-0.5, belief_strength=0.5,
            influence=0.5, susceptibility=0.5
        )
        agent_truth = LLMAgent(
            agent_id=1, opinion=0.5, belief_strength=0.5,
            influence=0.5, susceptibility=0.5
        )

        prompt_rumor, _ = agent_rumor.build_prompt(
            neighbor_agents=[], debunk_released=False, cocoon_strength=0.8
        )
        prompt_truth, _ = agent_truth.build_prompt(
            neighbor_agents=[], debunk_released=False, cocoon_strength=0.8
        )

        # 高茧房强度应该有推荐信息
        assert "算法推荐" in prompt_rumor
        assert "算法推荐" in prompt_truth

    @pytest.mark.asyncio
    async def test_decide_opinion_success(self):
        """测试成功的观点决策"""
        agent = LLMAgent(
            agent_id=0,
            opinion=-0.5,
            belief_strength=0.3,  # 低信念强度，更容易改变
            influence=0.5,
            susceptibility=0.5
        )

        # 创建模拟邻居
        neighbor = MagicMock()
        neighbor.id = 1
        neighbor.opinion = 0.2
        neighbor.is_silent = False

        mock_client = AsyncMock()
        mock_client.chat_json = AsyncMock(return_value={
            "new_opinion": -0.2,
            "reasoning": "受到邻居影响"
        })

        result = await agent.decide_opinion(
            mock_client,
            neighbor_agents=[neighbor],
            debunk_released=False,
            cocoon_strength=0.5
        )

        assert "new_opinion" in result
        assert result["new_opinion"] >= -1
        assert result["new_opinion"] <= 1

    @pytest.mark.asyncio
    async def test_decide_opinion_belief_constraint(self):
        """测试信念强度约束"""
        agent = LLMAgent(
            agent_id=0,
            opinion=-0.5,
            belief_strength=0.9,  # 高信念强度，难以改变
            influence=0.5,
            susceptibility=0.5
        )

        neighbor = MagicMock()
        neighbor.id = 1
        neighbor.opinion = 0.5
        neighbor.is_silent = False

        mock_client = AsyncMock()
        # LLM 返回极端变化
        mock_client.chat_json = AsyncMock(return_value={
            "new_opinion": 0.9,  # 从 -0.5 变到 0.9，变化 1.4
            "reasoning": "完全改变"
        })

        result = await agent.decide_opinion(
            mock_client,
            neighbor_agents=[neighbor],
            debunk_released=False,
            cocoon_strength=0.5
        )

        # 由于高信念强度，变化应该被限制
        change = abs(result["new_opinion"] - (-0.5))
        # 最大变化 = 0.3 * (1 - 0.9 * 0.5) = 0.3 * 0.55 = 0.165
        assert change <= 0.2  # 允许一定误差

    @pytest.mark.asyncio
    async def test_decide_opinion_failure_keeps_opinion(self):
        """测试决策失败时保持原观点"""
        agent = LLMAgent(
            agent_id=0,
            opinion=-0.5,
            belief_strength=0.5,
            influence=0.5,
            susceptibility=0.5
        )

        mock_client = AsyncMock()
        mock_client.chat_json = AsyncMock(side_effect=Exception("API Error"))

        result = await agent.decide_opinion(
            mock_client,
            neighbor_agents=[],
            debunk_released=False,
            cocoon_strength=0.5
        )

        # 失败时应保持原观点
        assert result["new_opinion"] == -0.5


class TestLLMAgentPopulation:
    """测试 LLM 智能体群体"""

    def test_population_initialization(self):
        """测试群体初始化"""
        pop = LLMAgentPopulation(size=50, initial_rumor_spread=0.3)

        assert pop.size == 50
        assert len(pop.agents) == 50

    def test_opinion_distribution(self):
        """测试观点分布"""
        pop = LLMAgentPopulation(size=100, initial_rumor_spread=0.3)

        # 约 30% 应该是谣言相信者
        rumor_believers = sum(1 for a in pop.agents if a.opinion < 0)
        assert rumor_believers >= 25  # 允许随机性

    def test_get_neighbors(self):
        """测试获取邻居"""
        pop = LLMAgentPopulation(size=50)

        neighbors = pop.get_neighbors(0)

        assert isinstance(neighbors, list)
        assert len(neighbors) > 0  # 小世界网络每个节点有邻居

    def test_get_neighbor_opinions(self):
        """测试获取邻居观点"""
        pop = LLMAgentPopulation(size=50)

        opinions = pop.get_neighbor_opinions(0)

        assert isinstance(opinions, list)
        assert all(-1 <= o <= 1 for o in opinions)

    def test_get_edges(self):
        """测试获取边"""
        pop = LLMAgentPopulation(size=50)

        edges = pop.get_edges()

        assert isinstance(edges, list)
        assert len(edges) > 0

    def test_get_opinion_histogram(self):
        """测试观点直方图"""
        pop = LLMAgentPopulation(size=100)

        hist = pop.get_opinion_histogram(bins=20)

        assert "counts" in hist
        assert "centers" in hist
        assert len(hist["counts"]) == 20

    def test_get_statistics(self):
        """测试统计计算"""
        pop = LLMAgentPopulation(size=100, initial_rumor_spread=0.3)

        stats = pop.get_statistics()

        assert "rumor_spread_rate" in stats
        assert "truth_acceptance_rate" in stats
        assert "avg_opinion" in stats
        assert "polarization_index" in stats

        # 检查范围
        assert 0 <= stats["rumor_spread_rate"] <= 1
        assert 0 <= stats["truth_acceptance_rate"] <= 1
        assert -1 <= stats["avg_opinion"] <= 1
        assert stats["polarization_index"] >= 0

    def test_apply_debunking(self):
        """测试辟谣应用"""
        pop = LLMAgentPopulation(size=100, initial_rumor_spread=0.5)

        # 记录辟谣前的观点
        pre_opinions = [a.opinion for a in pop.agents]

        pop.apply_debunking(effectiveness=0.2)

        # 检查辟谣效果
        for i, agent in enumerate(pop.agents):
            assert agent.exposed_to_truth is True
            # 相信谣言的人观点应该向正向移动
            if pre_opinions[i] < 0:
                assert agent.opinion >= pre_opinions[i]

    def test_to_agent_list(self):
        """测试转换为 Agent 列表"""
        pop = LLMAgentPopulation(size=10)

        agents = pop.to_agent_list()

        assert len(agents) == 10
        assert all("id" in a for a in agents)
        assert all("opinion" in a for a in agents)

    @pytest.mark.asyncio
    async def test_batch_decide(self):
        """测试批量决策"""
        pop = LLMAgentPopulation(size=10)

        mock_client = AsyncMock()
        mock_client.chat_json = AsyncMock(return_value={
            "new_opinion": 0.1,
            "reasoning": "test"
        })

        # 模拟 async with 上下文
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        async with mock_client:
            results = await pop.batch_decide(
                mock_client,
                debunk_released=False,
                cocoon_strength=0.5
            )

        assert len(results) == 10
        assert all("new_opinion" in r for r in results)

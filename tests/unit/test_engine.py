"""
SimulationEngine 单元测试
测试推演引擎的核心逻辑（支持 LLM 和数学模型两种模式）
"""
import pytest
import numpy as np
import asyncio
from unittest.mock import AsyncMock, patch

from backend.simulation.engine import SimulationEngine
from backend.simulation.agents import AgentPopulation
from backend.simulation.llm_agents import LLMAgentPopulation
from backend.models.schemas import SimulationState
from backend.llm.client import LLMConfig


class TestEngineInit:
    """测试引擎初始化"""

    def test_default_initialization(self):
        """测试默认参数初始化"""
        engine = SimulationEngine()

        assert engine.population_size == 200
        assert engine.cocoon_strength == 0.5
        assert engine.debunk_delay == 10
        assert engine.initial_rumor_spread == 0.3
        assert engine.network_type == "small_world"
        assert engine.step_count == 0
        assert engine.debunked is False
        assert engine.use_llm is True  # 默认使用 LLM

    def test_custom_initialization(self):
        """测试自定义参数初始化"""
        engine = SimulationEngine(
            population_size=100,
            cocoon_strength=0.8,
            debunk_delay=5,
            initial_rumor_spread=0.5,
            network_type="scale_free",
            use_llm=False
        )

        assert engine.population_size == 100
        assert engine.cocoon_strength == 0.8
        assert engine.debunk_delay == 5
        assert engine.initial_rumor_spread == 0.5
        assert engine.network_type == "scale_free"
        assert engine.use_llm is False


class TestEngineInitialize:
    """测试引擎初始化方法"""

    def test_initialize_creates_population_math_mode(self):
        """测试数学模型模式初始化创建群体"""
        engine = SimulationEngine(population_size=50, use_llm=False)
        state = engine.initialize()

        assert engine.population is not None
        assert isinstance(engine.population, AgentPopulation)
        assert engine.population.size == 50

    def test_initialize_creates_population_llm_mode(self):
        """测试 LLM 模式初始化创建群体"""
        engine = SimulationEngine(population_size=50, use_llm=True)
        state = engine.initialize()

        assert engine.llm_population is not None
        assert isinstance(engine.llm_population, LLMAgentPopulation)
        assert engine.llm_population.size == 50

    def test_initialize_returns_state(self):
        """测试初始化返回状态"""
        engine = SimulationEngine(population_size=50, use_llm=False)
        state = engine.initialize()

        assert isinstance(state, SimulationState)
        assert state.step == 0

    def test_initialize_resets_state(self):
        """测试初始化重置状态"""
        engine = SimulationEngine(population_size=50, use_llm=False)
        engine.initialize()
        engine.step()
        engine.step()

        # 重新初始化
        state = engine.initialize()

        assert engine.step_count == 0
        assert engine.debunked is False
        assert len(engine.history) == 1


class TestEngineStepMathMode:
    """测试引擎步进方法 - 数学模型模式"""

    def test_step_without_initialize_raises(self):
        """测试未初始化时步进抛出异常"""
        engine = SimulationEngine(use_llm=False)

        with pytest.raises(RuntimeError, match="请先调用 initialize"):
            engine.step()

    def test_step_increments_count(self):
        """测试步进增加计数"""
        engine = SimulationEngine(population_size=50, use_llm=False)
        engine.initialize()

        for i in range(5):
            state = engine.step()
            assert state.step == i + 1

    def test_step_returns_state(self):
        """测试步进返回状态"""
        engine = SimulationEngine(population_size=50, use_llm=False)
        engine.initialize()
        state = engine.step()

        assert isinstance(state, SimulationState)
        assert state.step == 1

    def test_step_records_history(self):
        """测试步进记录历史"""
        engine = SimulationEngine(population_size=50, use_llm=False)
        engine.initialize()

        for _ in range(3):
            engine.step()

        assert len(engine.history) == 4  # 初始 + 3步

    def test_step_updates_opinions(self):
        """测试步进更新观点"""
        engine = SimulationEngine(population_size=50, use_llm=False)
        engine.initialize()
        initial_opinions = engine.population.opinions.copy()

        engine.step()

        # 观点应该发生变化
        assert not np.allclose(engine.population.opinions, initial_opinions)


class TestEngineStepLLMMode:
    """测试引擎步进方法 - LLM 模式"""

    @pytest.mark.asyncio
    async def test_async_step_increments_count(self):
        """测试异步步进增加计数"""
        engine = SimulationEngine(population_size=10, use_llm=True)
        engine.initialize()

        # Mock LLM client
        mock_client = AsyncMock()
        mock_client.chat_json = AsyncMock(return_value={
            "new_opinion": 0.1,
            "reasoning": "test"
        })
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        engine.llm_client = mock_client

        state = await engine.async_step()

        assert state.step == 1

    @pytest.mark.asyncio
    async def test_llm_mode_raises_on_sync_step(self):
        """测试 LLM 模式调用同步步进抛出异常"""
        engine = SimulationEngine(population_size=10, use_llm=True)
        engine.initialize()

        with pytest.raises(RuntimeError, match="LLM 模式请使用 async_step"):
            engine.step()


class TestDebunking:
    """测试辟谣机制"""

    def test_debunking_releases_at_delay(self):
        """测试辟谣在延迟后发布"""
        engine = SimulationEngine(
            population_size=50,
            debunk_delay=3,
            use_llm=False
        )
        engine.initialize()

        # 前几步不应辟谣
        engine.step()
        engine.step()
        assert engine.debunked is False

        # 第3步应该辟谣
        engine.step()
        assert engine.debunked is True

    def test_debunking_affects_opinions(self):
        """测试辟谣影响观点"""
        engine = SimulationEngine(
            population_size=100,
            debunk_delay=1,
            initial_rumor_spread=0.5,
            use_llm=False
        )
        engine.initialize()

        # 获取辟谣前的观点
        pre_debunk_opinions = engine.population.opinions.copy()

        # 执行辟谣
        engine.step()

        # 相信谣言的人观点应该向真相方向移动
        rumor_believers_mask = pre_debunk_opinions < 0
        if sum(rumor_believers_mask) > 0:
            opinion_changes = engine.population.opinions[rumor_believers_mask] - pre_debunk_opinions[rumor_believers_mask]
            # 平均变化应该为正 (向真相方向)
            assert np.mean(opinion_changes) > 0


class TestStateComputation:
    """测试状态计算"""

    def test_compute_state_metrics(self):
        """测试状态指标计算"""
        engine = SimulationEngine(population_size=100, use_llm=False)
        state = engine.initialize()

        # 检查所有指标存在
        assert hasattr(state, 'step')
        assert hasattr(state, 'agents')
        assert hasattr(state, 'edges')
        assert hasattr(state, 'opinion_distribution')
        assert hasattr(state, 'rumor_spread_rate')
        assert hasattr(state, 'truth_acceptance_rate')
        assert hasattr(state, 'avg_opinion')
        assert hasattr(state, 'polarization_index')

    def test_rumor_spread_rate_calculation(self):
        """测试谣言传播率计算"""
        engine = SimulationEngine(
            population_size=100,
            initial_rumor_spread=0.3,
            use_llm=False
        )
        state = engine.initialize()

        # 初始谣言传播率应该接近 0.3
        assert 0.2 <= state.rumor_spread_rate <= 0.5

    def test_avg_opinion_in_valid_range(self):
        """测试平均观点在有效范围"""
        engine = SimulationEngine(population_size=100, use_llm=False)
        state = engine.initialize()

        assert -1 <= state.avg_opinion <= 1

    def test_polarization_non_negative(self):
        """测试极化指数非负"""
        engine = SimulationEngine(population_size=100, use_llm=False)
        state = engine.initialize()

        assert state.polarization_index >= 0


class TestReportGeneration:
    """测试报告生成"""

    def test_generate_report_returns_path(self):
        """测试生成报告返回路径"""
        engine = SimulationEngine(population_size=50, use_llm=False)
        engine.initialize()
        engine.step()
        engine.step()

        report_path = engine.generate_report()

        assert report_path is not None
        assert report_path.endswith(".md")

    def test_generate_report_without_history(self):
        """测试无历史时生成报告"""
        engine = SimulationEngine(use_llm=False)

        report_path = engine.generate_report()

        assert report_path == ""


class TestProgressCallback:
    """测试进度回调"""

    @pytest.mark.asyncio
    async def test_progress_callback_called(self):
        """测试进度回调被调用"""
        engine = SimulationEngine(population_size=10, use_llm=True)
        engine.initialize()

        # Mock LLM client
        mock_client = AsyncMock()
        mock_client.chat_json = AsyncMock(return_value={
            "new_opinion": 0.1,
            "reasoning": "test"
        })
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        engine.llm_client = mock_client

        # 记录回调调用
        callback_calls = []
        async def track_callback(step, total):
            callback_calls.append((step, total))

        engine.set_progress_callback(track_callback)

        await engine.async_step()

        # 回调应该被调用
        assert len(callback_calls) > 0


class TestEdgeCases:
    """测试边界情况"""

    def test_small_population(self):
        """测试小群体"""
        engine = SimulationEngine(population_size=10, use_llm=False)
        state = engine.initialize()

        assert len(state.agents) == 10

    def test_zero_cocoon_strength(self):
        """测试零茧房强度"""
        engine = SimulationEngine(
            population_size=50,
            cocoon_strength=0,
            use_llm=False
        )
        state = engine.initialize()

        for _ in range(5):
            state = engine.step()

        assert state is not None

    def test_immediate_debunk(self):
        """测试立即辟谣"""
        engine = SimulationEngine(
            population_size=50,
            debunk_delay=0,
            use_llm=False
        )
        state = engine.initialize()

        # 第一步就应该辟谣
        engine.step()
        assert engine.debunked is True

    def test_never_debunk(self):
        """测试永不辟谣"""
        engine = SimulationEngine(
            population_size=50,
            debunk_delay=1000,
            use_llm=False
        )
        state = engine.initialize()

        for _ in range(50):
            engine.step()

        assert engine.debunked is False

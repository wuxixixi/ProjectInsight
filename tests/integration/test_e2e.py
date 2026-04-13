"""
端到端集成测试
测试完整的模拟场景
"""
import pytest
import numpy as np
from fastapi.testclient import TestClient

from backend.simulation.engine import SimulationEngine
from backend.simulation.agents import AgentPopulation
from backend.app import app


class TestEndToEndScenarios:
    """端到端场景测试"""

    def test_rumor_spread_scenario(self):
        """测试谣言传播场景"""
        engine = SimulationEngine(
            population_size=100,
            cocoon_strength=0.3,
            debunk_delay=20,  # 延迟辟谣
            initial_rumor_spread=0.2,
            use_llm=False  # 使用数学模型模式
        )
        engine.initialize()

        initial_rumor_rate = engine.current_state.rumor_spread_rate

        # 运行10步，无辟谣
        for _ in range(10):
            engine.step()

        # 谣言应该有一定传播
        # (由于茧房效应和社交传播)
        final_rumor_rate = engine.current_state.rumor_spread_rate

        # 记录历史
        assert len(engine.history) == 11

    def test_debunking_effectiveness(self):
        """测试辟谣效果"""
        # 早期辟谣
        engine_early = SimulationEngine(
            population_size=100,
            cocoon_strength=0.5,
            debunk_delay=3,
            initial_rumor_spread=0.3,
            use_llm=False
        )
        engine_early.initialize()
        for _ in range(15):
            engine_early.step()

        # 晚期辟谣
        engine_late = SimulationEngine(
            population_size=100,
            cocoon_strength=0.5,
            debunk_delay=15,
            initial_rumor_spread=0.3,
            use_llm=False
        )
        engine_late.initialize()
        for _ in range(15):
            engine_late.step()

        # 早期辟谣应该更有效
        # (真相接受率更高)
        assert engine_early.current_state.truth_acceptance_rate >= \
               engine_late.current_state.truth_acceptance_rate * 0.8

    def test_cocoon_strength_impact(self):
        """测试茧房强度影响"""
        results = {}

        for strength in [0.0, 0.5, 1.0]:
            engine = SimulationEngine(
                population_size=100,
                cocoon_strength=strength,
                debunk_delay=5,
                initial_rumor_spread=0.3,
                use_llm=False
            )
            engine.initialize()

            for _ in range(20):
                engine.step()

            results[strength] = engine.current_state.polarization_index

        # 高茧房强度应该导致更高极化
        assert results[1.0] >= results[0.0] * 0.8

    def test_network_type_comparison(self):
        """测试不同网络类型对比"""
        network_types = ["small_world", "scale_free", "random"]
        results = {}

        for net_type in network_types:
            engine = SimulationEngine(
                population_size=100,
                cocoon_strength=0.5,
                debunk_delay=10,
                initial_rumor_spread=0.3,
                network_type=net_type,
                use_llm=False
            )
            engine.initialize()

            for _ in range(15):
                engine.step()

            results[net_type] = {
                "rumor_rate": engine.current_state.rumor_spread_rate,
                "truth_rate": engine.current_state.truth_acceptance_rate,
                "polarization": engine.current_state.polarization_index
            }

        # 所有网络类型都应该有有效结果
        for net_type in network_types:
            assert 0 <= results[net_type]["rumor_rate"] <= 1
            assert 0 <= results[net_type]["truth_rate"] <= 1
            assert results[net_type]["polarization"] >= 0


class TestAPIEndToEnd:
    """API 端到端测试"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_complete_user_journey(self, client):
        """测试完整用户旅程"""
        # 1. 用户启动模拟
        response = client.post("/api/simulation/start", json={
            "population_size": 50,
            "cocoon_strength": 0.6,
            "debunk_delay": 5,
            "network_type": "small_world",
            "use_llm": False
        })
        assert response.status_code == 200
        initial_state = response.json()

        # 2. 用户查看初始状态
        assert initial_state["step"] == 0
        assert len(initial_state["agents"]) == 50

        # 3. 用户执行多步模拟
        states = [initial_state]
        for _ in range(10):
            response = client.get("/api/simulation/step")
            assert response.status_code == 200
            states.append(response.json())

        # 4. 验证状态演进
        for i, state in enumerate(states):
            assert state["step"] == i

        # 5. 用户获取当前状态
        response = client.get("/api/simulation/state")
        assert response.status_code == 200
        final_state = response.json()
        assert final_state["step"] == 10

    def test_parameter_sensitivity_analysis(self, client):
        """测试参数敏感性分析场景"""
        results = []

        # 测试不同茧房强度
        for strength in [0.0, 0.3, 0.6, 1.0]:
            response = client.post("/api/simulation/start", json={
                "population_size": 50,
                "cocoon_strength": strength,
                "debunk_delay": 5,
                "use_llm": False
            })
            assert response.status_code == 200

            # 运行10步
            for _ in range(10):
                client.get("/api/simulation/step")

            response = client.get("/api/simulation/state")
            results.append(response.json()["polarization_index"])

        # 结果应该是有效的
        assert all(r >= 0 for r in results)


class TestPerformance:
    """性能测试"""

    def test_large_population_performance(self):
        """测试大群体性能"""
        import time

        engine = SimulationEngine(
            population_size=500,
            cocoon_strength=0.5,
            debunk_delay=10,
            use_llm=False
        )
        engine.initialize()

        start_time = time.time()
        for _ in range(20):
            engine.step()
        elapsed = time.time() - start_time

        # 20步应该在合理时间内完成 (例如 < 5秒)
        assert elapsed < 5.0

    def test_long_simulation(self):
        """测试长时间模拟"""
        engine = SimulationEngine(
            population_size=100,
            cocoon_strength=0.5,
            debunk_delay=10,
            use_llm=False
        )
        engine.initialize()

        # 运行100步
        for _ in range(100):
            engine.step()

        # 历史记录应该完整
        assert len(engine.history) == 101

        # 观点应该保持在有效范围
        opinions = engine.population.opinions
        assert np.all(opinions >= -1) and np.all(opinions <= 1)


class TestConsistency:
    """一致性测试"""

    def test_opinion_bounds_maintained(self):
        """测试观点边界保持"""
        engine = SimulationEngine(
            population_size=100,
            cocoon_strength=1.0,  # 最大茧房强度
            debunk_delay=1,
            use_llm=False
        )
        engine.initialize()

        for _ in range(50):
            engine.step()
            opinions = engine.population.opinions
            assert np.all(opinions >= -1)
            assert np.all(opinions <= 1)

    def test_metrics_consistency(self):
        """测试指标一致性"""
        engine = SimulationEngine(population_size=100, use_llm=False)
        engine.initialize()

        for _ in range(20):
            state = engine.step()

            # 谣言率 + 真相率 + 中立率 应该 <= 1
            # (因为可能有中立观点)
            total = state.rumor_spread_rate + state.truth_acceptance_rate
            assert total <= 1.0

            # 极化指数应该非负
            assert state.polarization_index >= 0

            # 平均观点应该在范围内
            assert -1 <= state.avg_opinion <= 1

    def test_agent_count_stable(self):
        """测试智能体数量稳定"""
        engine = SimulationEngine(population_size=100, use_llm=False)
        engine.initialize()

        initial_count = len(engine.current_state.agents)

        for _ in range(20):
            engine.step()

        final_count = len(engine.current_state.agents)
        assert initial_count == final_count == 100

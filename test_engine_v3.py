"""
Engine v3 Integration Tests

测试 v3 模块集成到 SimulationEngine
"""
import pytest
import numpy as np

from backend.simulation.engine import SimulationEngine
from backend.simulation.engine_v3 import EngineV3Integration
from backend.simulation.agent import BeliefState
from backend.simulation.psychology import NeedsHierarchy, TheoryOfPlannedBehavior


class TestEngineV3Integration:
    """测试 v3 集成适配层"""
    
    def test_integration_creation(self):
        """测试创建 v3 集成层"""
        v3 = EngineV3Integration(simulation_id="test_001")
        
        assert v3.simulation_id == "test_001"
        assert v3.enable_memory == True
        assert v3.enable_psychology == True
        assert v3.env_router is not None
    
    def test_initialize_agents(self):
        """测试初始化 Agent 状态"""
        v3 = EngineV3Integration(simulation_id="test_002")
        
        n = 50
        opinions = np.random.uniform(-1, 1, n)
        belief_strengths = np.random.uniform(0.3, 0.7, n)
        susceptibilities = np.random.uniform(0.2, 0.8, n)
        influences = np.random.uniform(0.1, 0.5, n)
        fear_of_isolations = np.random.uniform(0.2, 0.6, n)
        
        # 简单邻接表
        adjacency = {i: [j for j in range(n) if j != i and abs(j - i) < 3] for i in range(n)}
        
        v3.initialize_agents(
            opinions=opinions,
            belief_strengths=belief_strengths,
            susceptibilities=susceptibilities,
            influences=influences,
            fear_of_isolations=fear_of_isolations,
            adjacency=adjacency
        )
        
        # 验证 Agent 状态
        assert len(v3.belief_states) == n
        assert len(v3.needs_hierarchy) == n
        assert len(v3.tpb_models) == n
        
        # 验证信念状态初始化
        for i, belief in v3.belief_states.items():
            assert -1 <= belief.rumor_trust <= 1
            assert -1 <= belief.truth_trust <= 1
    
    def test_get_agent_v3_fields(self):
        """测试获取 Agent v3 字段"""
        v3 = EngineV3Integration(simulation_id="test_003")
        
        # 初始化简单数据
        n = 10
        opinions = np.array([0.5, -0.3, 0.0, 0.2, -0.5, 0.3, -0.2, 0.1, 0.4, -0.4])
        
        v3.initialize_agents(
            opinions=opinions,
            belief_strengths=np.ones(n) * 0.5,
            susceptibilities=np.ones(n) * 0.5,
            influences=np.ones(n) * 0.3,
            fear_of_isolations=np.ones(n) * 0.5,
            adjacency={i: [] for i in range(n)}
        )
        
        # 获取字段
        fields = v3.get_agent_v3_fields(0)
        
        assert "rumor_trust" in fields
        assert "truth_trust" in fields
        assert "dominant_need" in fields
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        v3 = EngineV3Integration(simulation_id="test_004")
        
        n = 20
        opinions = np.random.uniform(-1, 1, n)
        
        v3.initialize_agents(
            opinions=opinions,
            belief_strengths=np.ones(n) * 0.5,
            susceptibilities=np.ones(n) * 0.5,
            influences=np.ones(n) * 0.3,
            fear_of_isolations=np.ones(n) * 0.5,
            adjacency={i: [] for i in range(n)}
        )
        
        stats = v3.get_statistics()
        
        assert "avg_rumor_trust" in stats
        assert "avg_truth_trust" in stats
        assert "need_distribution" in stats
    
    def test_reset(self):
        """测试重置状态"""
        v3 = EngineV3Integration(simulation_id="test_005")
        
        n = 10
        v3.initialize_agents(
            opinions=np.random.uniform(-1, 1, n),
            belief_strengths=np.ones(n) * 0.5,
            susceptibilities=np.ones(n) * 0.5,
            influences=np.ones(n) * 0.3,
            fear_of_isolations=np.ones(n) * 0.5,
            adjacency={i: [] for i in range(n)}
        )
        
        assert len(v3.belief_states) == n
        
        v3.reset()
        
        assert len(v3.belief_states) == 0


class TestSimulationEngineV3:
    """测试 Engine v3 集成"""
    
    def test_engine_v3_disabled(self):
        """测试禁用 v3"""
        engine = SimulationEngine(
            population_size=50,
            use_llm=False,
            use_v3=False
        )
        
        assert engine.use_v3 == False
        assert engine.v3 is None
    
    def test_engine_v3_enabled(self):
        """测试启用 v3"""
        engine = SimulationEngine(
            population_size=50,
            use_llm=False,
            use_v3=True
        )
        
        assert engine.use_v3 == True
        assert engine.v3 is not None
    
    def test_engine_initialize_with_v3(self):
        """测试初始化带 v3"""
        engine = SimulationEngine(
            population_size=30,
            use_llm=False,
            use_v3=True
        )
        
        state = engine.initialize()
        
        # 验证 v3 Agent 状态已初始化
        assert len(engine.v3.belief_states) == 30
        
        # 验证 Agent 字段包含 v3 信息
        agents = state.agents
        assert len(agents) == 30
        
        # 验证 v3 统计字段
        assert hasattr(state, 'avg_rumor_trust')
        assert hasattr(state, 'avg_truth_trust')
    
    def test_engine_step_with_v3(self):
        """测试推演步骤带 v3"""
        engine = SimulationEngine(
            population_size=20,
            use_llm=False,
            use_v3=True,
            response_delay=5
        )
        
        engine.initialize()
        
        # 执行几步推演
        for _ in range(3):
            state = engine.step()
        
        # 验证 v3 状态更新
        assert len(engine.v3.belief_states) == 20
        
        # 验证统计变化
        assert engine.step_count == 3
    
    def test_engine_v3_fields_in_state(self):
        """测试状态包含 v3 字段"""
        engine = SimulationEngine(
            population_size=20,
            use_llm=False,
            use_v3=True
        )
        
        state = engine.initialize()
        
        # 转为 dict
        state_dict = state.to_dict()
        
        # 验证 v3 字段存在
        assert "avg_rumor_trust" in state_dict
        assert "avg_truth_trust" in state_dict
        
        # 验证 Agent 有 v3 字段
        agent = state_dict["agents"][0]
        assert "rumor_trust" in agent
        assert "truth_trust" in agent
    
    def test_engine_backward_compatibility(self):
        """测试向后兼容"""
        # 不使用 v3，验证旧字段正常
        engine = SimulationEngine(
            population_size=20,
            use_llm=False,
            use_v3=False
        )
        
        state = engine.initialize()
        state_dict = state.to_dict()
        
        # 旧字段应该存在
        assert "avg_opinion" in state_dict
        assert "polarization_index" in state_dict
        assert "believe_rate" in state_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
数据模型单元测试
测试 Pydantic 模型的验证和序列化
"""
import pytest
from pydantic import ValidationError
from backend.models.schemas import Agent, SimulationParams, SimulationState


class TestAgent:
    """测试 Agent 模型"""

    def test_valid_agent(self):
        """测试有效智能体"""
        agent = Agent(
            id=0,
            opinion=0.5,
            belief_strength=0.7,
            influence=0.3,
            susceptibility=0.4
        )

        assert agent.id == 0
        assert agent.opinion == 0.5
        assert agent.belief_strength == 0.7
        assert agent.influence == 0.3
        assert agent.susceptibility == 0.4
        assert agent.exposed_to_rumor is False
        assert agent.exposed_to_truth is False

    def test_agent_with_exposure(self):
        """测试带曝光状态的智能体"""
        agent = Agent(
            id=1,
            opinion=-0.5,
            belief_strength=0.5,
            influence=0.5,
            susceptibility=0.5,
            exposed_to_rumor=True,
            exposed_to_truth=True
        )

        assert agent.exposed_to_rumor is True
        assert agent.exposed_to_truth is True

    def test_agent_dict_conversion(self):
        """测试智能体字典转换"""
        agent = Agent(
            id=0,
            opinion=0.5,
            belief_strength=0.7,
            influence=0.3,
            susceptibility=0.4
        )

        agent_dict = agent.model_dump()

        assert isinstance(agent_dict, dict)
        assert agent_dict['id'] == 0
        assert agent_dict['opinion'] == 0.5


class TestSimulationParams:
    """测试 SimulationParams 模型"""

    def test_default_params(self):
        """测试默认参数"""
        params = SimulationParams()

        assert params.cocoon_strength == 0.5
        assert params.debunk_delay == 10
        assert params.population_size == 200
        assert params.initial_rumor_spread == 0.3
        assert params.network_type == "small_world"

    def test_custom_params(self):
        """测试自定义参数"""
        params = SimulationParams(
            cocoon_strength=0.8,
            debunk_delay=5,
            population_size=100,
            initial_rumor_spread=0.4,
            network_type="scale_free"
        )

        assert params.cocoon_strength == 0.8
        assert params.debunk_delay == 5
        assert params.population_size == 100
        assert params.initial_rumor_spread == 0.4
        assert params.network_type == "scale_free"


class TestSimulationState:
    """测试 SimulationState 模型"""

    def test_valid_state(self):
        """测试有效状态"""
        state = SimulationState(
            step=0,
            agents=[{"id": 0, "opinion": 0.5, "belief_strength": 0.5,
                     "influence": 0.5, "susceptibility": 0.5}],
            edges=[(0, 1)],
            opinion_distribution={"counts": [1, 2, 3], "centers": [-0.5, 0, 0.5]},
            rumor_spread_rate=0.3,
            truth_acceptance_rate=0.2,
            avg_opinion=0.1,
            polarization_index=0.5
        )

        assert state.step == 0
        assert len(state.agents) == 1
        assert len(state.edges) == 1

    def test_state_to_dict(self):
        """测试状态字典转换"""
        state = SimulationState(
            step=1,
            agents=[],
            edges=[],
            opinion_distribution={"counts": [], "centers": []},
            rumor_spread_rate=0.0,
            truth_acceptance_rate=0.0,
            avg_opinion=0.0,
            polarization_index=0.0
        )

        state_dict = state.to_dict()

        assert isinstance(state_dict, dict)
        assert state_dict['step'] == 1
        assert 'agents' in state_dict
        assert 'edges' in state_dict
        assert 'opinion_distribution' in state_dict
        assert 'rumor_spread_rate' in state_dict
        assert 'truth_acceptance_rate' in state_dict
        assert 'avg_opinion' in state_dict
        assert 'polarization_index' in state_dict

    def test_state_serialization(self):
        """测试状态序列化"""
        state = SimulationState(
            step=5,
            agents=[
                {"id": 0, "opinion": 0.5, "belief_strength": 0.5,
                 "influence": 0.5, "susceptibility": 0.5}
            ],
            edges=[(0, 1), (1, 2)],
            opinion_distribution={"counts": [10, 20], "centers": [-0.5, 0.5]},
            rumor_spread_rate=0.25,
            truth_acceptance_rate=0.35,
            avg_opinion=0.15,
            polarization_index=0.6
        )

        state_dict = state.to_dict()

        # 验证所有字段都正确序列化
        assert state_dict['step'] == 5
        assert state_dict['rumor_spread_rate'] == 0.25
        assert state_dict['truth_acceptance_rate'] == 0.35
        assert state_dict['avg_opinion'] == 0.15
        assert state_dict['polarization_index'] == 0.6

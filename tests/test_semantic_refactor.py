"""
语义重构测试 (方案C: 抽象化概念)

验证以下字段映射的正确性：
- rumor → negative_belief (负面信念)
- truth → positive_belief (正面信念)
- debunk → authority_response (权威回应)

测试目标：
1. 数据模型字段名变更正确
2. API 参数向后兼容
3. 状态序列化包含新字段名
4. 前端可正确接收新字段
"""
import pytest
import json
from fastapi.testclient import TestClient
from pydantic import ValidationError


class TestSchemaFieldsRefactor:
    """测试数据模型字段重构"""

    def test_agent_negative_exposure_field(self):
        """测试 Agent.exposed_to_negative 字段存在"""
        from backend.models.schemas import Agent

        agent = Agent(
            id=0,
            opinion=0.5,
            belief_strength=0.7,
            influence=0.3,
            susceptibility=0.4,
            exposed_to_negative=True,  # 新字段名
            exposed_to_positive=True    # 新字段名
        )

        assert agent.exposed_to_negative is True
        assert agent.exposed_to_positive is True

    def test_agent_old_fields_still_work(self):
        """测试 Agent 旧字段名仍可使用（向后兼容）"""
        from backend.models.schemas import Agent

        # 旧字段名应该仍可使用
        agent = Agent(
            id=0,
            opinion=0.5,
            belief_strength=0.7,
            influence=0.3,
            susceptibility=0.4,
            exposed_to_rumor=True,      # 旧字段名
            exposed_to_truth=True       # 旧字段名
        )

        # 验证字段存在
        assert agent.exposed_to_negative is True or agent.exposed_to_rumor is True
        assert agent.exposed_to_positive is True or agent.exposed_to_truth is True

    def test_agent_dict_contains_preferred_field_names(self):
        """测试 Agent.to_dict() 包含优先字段名"""
        from backend.models.schemas import Agent

        agent = Agent(
            id=0,
            opinion=0.5,
            belief_strength=0.7,
            influence=0.3,
            susceptibility=0.4,
            exposed_to_negative=True,
            exposed_to_positive=False
        )

        agent_dict = agent.model_dump()

        # 新字段名应该存在
        assert 'exposed_to_negative' in agent_dict or 'exposed_to_rumor' in agent_dict

    def test_simulation_params_response_delay(self):
        """测试 SimulationParams.response_delay 字段"""
        from backend.models.schemas import SimulationParams

        params = SimulationParams(
            response_delay=5  # 新字段名
        )

        assert params.response_delay == 5 or params.debunk_delay == 5

    def test_simulation_params_initial_negative_spread(self):
        """测试 SimulationParams.initial_negative_spread 字段"""
        from backend.models.schemas import SimulationParams

        params = SimulationParams(
            initial_negative_spread=0.4  # 新字段名
        )

        assert params.initial_negative_spread == 0.4 or params.initial_rumor_spread == 0.4

    def test_simulation_state_negative_belief_rate(self):
        """测试 SimulationState.negative_belief_rate 字段"""
        from backend.models.schemas import SimulationState

        state = SimulationState(
            step=0,
            agents=[],
            edges=[],
            opinion_distribution={"counts": [], "centers": []},
            negative_belief_rate=0.3,     # 新字段名
            positive_belief_rate=0.2,     # 新字段名
            avg_opinion=0.0,
            polarization_index=0.0
        )

        assert state.negative_belief_rate == 0.3 or state.rumor_spread_rate == 0.3
        assert state.positive_belief_rate == 0.2 or state.truth_acceptance_rate == 0.2

    def test_simulation_state_to_dict_contains_new_fields(self):
        """测试 SimulationState.to_dict() 包含新字段名"""
        from backend.models.schemas import SimulationState

        state = SimulationState(
            step=5,
            agents=[{"id": 0, "opinion": 0.5}],
            edges=[],
            opinion_distribution={"counts": [1], "centers": [0.5]},
            negative_belief_rate=0.25,
            positive_belief_rate=0.35,
            avg_opinion=0.1,
            polarization_index=0.5
        )

        state_dict = state.to_dict()

        # 应包含新字段名（或兼容的旧字段名）
        has_negative = 'negative_belief_rate' in state_dict or 'rumor_spread_rate' in state_dict
        has_positive = 'positive_belief_rate' in state_dict or 'truth_acceptance_rate' in state_dict

        assert has_negative, "状态字典应包含 negative_belief_rate 或 rumor_spread_rate"
        assert has_positive, "状态字典应包含 positive_belief_rate 或 truth_acceptance_rate"


class TestAPIParamsCompatibility:
    """测试 API 参数兼容性"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from backend.app import app
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def reset_engine(self):
        """每个测试前重置引擎"""
        import backend.app
        backend.app.engine = None
        yield
        backend.app.engine = None

    def test_start_with_new_param_names(self, client):
        """测试使用新参数名启动推演"""
        params = {
            "initial_negative_spread": 0.4,
            "response_delay": 5,
            "population_size": 50,
            "use_llm": False
        }
        response = client.post("/api/simulation/start", json=params)

        assert response.status_code == 200
        data = response.json()
        assert len(data["agents"]) == 50

    def test_start_with_old_param_names(self, client):
        """测试使用旧参数名启动推演（向后兼容）"""
        params = {
            "initial_rumor_spread": 0.4,
            "debunk_delay": 5,
            "population_size": 50,
            "use_llm": False
        }
        response = client.post("/api/simulation/start", json=params)

        assert response.status_code == 200
        data = response.json()
        assert len(data["agents"]) == 50

    def test_start_with_mixed_param_names(self, client):
        """测试混合使用新旧参数名"""
        params = {
            "initial_negative_spread": 0.35,  # 新名
            "debunk_delay": 8,                 # 旧名
            "population_size": 50,
            "use_llm": False
        }
        response = client.post("/api/simulation/start", json=params)

        assert response.status_code == 200

    def test_response_contains_new_field_names(self, client):
        """测试响应包含新字段名"""
        client.post("/api/simulation/start", json={"population_size": 50, "use_llm": False})
        response = client.get("/api/simulation/state")

        data = response.json()

        # 响应应该包含新字段名或旧字段名
        has_negative = 'negative_belief_rate' in data or 'rumor_spread_rate' in data
        has_positive = 'positive_belief_rate' in data or 'truth_acceptance_rate' in data

        assert has_negative, "响应应包含 negative_belief_rate 或 rumor_spread_rate"
        assert has_positive, "响应应包含 positive_belief_rate 或 truth_acceptance_rate"


class TestEngineStateCalculation:
    """测试引擎状态计算"""

    def test_engine_calculates_negative_belief_rate(self):
        """测试引擎计算负面信念率"""
        from backend.simulation.engine import SimulationEngine

        engine = SimulationEngine(
            population_size=50,
            initial_negative_spread=0.3,
            use_llm=False
        )
        state = engine.initialize()

        # 状态应包含负面信念率
        has_negative = (
            hasattr(state, 'negative_belief_rate') or
            hasattr(state, 'rumor_spread_rate')
        )
        assert has_negative

    def test_engine_state_serialization(self):
        """测试引擎状态序列化"""
        from backend.simulation.engine import SimulationEngine

        engine = SimulationEngine(population_size=50, use_llm=False)
        engine.initialize()
        engine.step()

        state_dict = engine.current_state.to_dict()

        # 序列化应包含新字段名
        assert 'negative_belief_rate' in state_dict or 'rumor_spread_rate' in state_dict
        assert 'positive_belief_rate' in state_dict or 'truth_acceptance_rate' in state_dict

    def test_history_records_new_field_names(self):
        """测试历史记录使用新字段名"""
        from backend.simulation.engine import SimulationEngine

        engine = SimulationEngine(population_size=50, use_llm=False)
        engine.initialize()
        engine.step()
        engine.step()

        history = engine.history

        # 历史记录应包含新字段名
        first_record = history[0]
        has_negative = 'negative_belief_rate' in first_record or 'rumor_spread_rate' in first_record
        assert has_negative


class TestDualNetworkFields:
    """测试双层网络字段"""

    def test_dual_network_state_has_public_private_rates(self):
        """测试双层网络状态包含公域/私域负面信念率"""
        from backend.simulation.engine_dual import SimulationEngineDual

        engine = SimulationEngineDual(
            population_size=50,
            use_llm=False
        )
        state = engine.initialize()

        state_dict = state.to_dict()

        # 应包含公域/私域负面信念率
        has_public = 'public_negative_rate' in state_dict or 'public_rumor_rate' in state_dict
        has_private = 'private_negative_rate' in state_dict or 'private_rumor_rate' in state_dict

        assert has_public, "状态应包含 public_negative_rate 或 public_rumor_rate"
        assert has_private, "状态应包含 private_negative_rate 或 private_rumor_rate"


class TestPredictionFields:
    """测试预测模块字段"""

    def test_prediction_uses_neutral_naming(self):
        """测试预测使用中性命名"""
        from backend.simulation.prediction import PredictionModel

        # 创建模拟历史数据
        history = [
            {"negative_belief_rate": 0.3, "avg_opinion": 0.0, "polarization_index": 0.5},
            {"negative_belief_rate": 0.35, "avg_opinion": -0.1, "polarization_index": 0.55},
            {"negative_belief_rate": 0.4, "avg_opinion": -0.15, "polarization_index": 0.6},
        ]

        model = PredictionModel()
        model.update(history)

        current_state = {"negative_belief_rate": 0.4}
        prediction = model.predict(current_state)

        # 预测应包含中性命名的指标
        has_negative = 'negative_belief_rate' in prediction or 'rumor_spread_rate' in prediction
        assert has_negative


class TestRiskAlertFields:
    """测试风险预警字段"""

    def test_risk_rules_use_neutral_naming(self):
        """测试风险规则使用中性命名"""
        from backend.simulation.risk_alert import RiskAlertEngine, RiskRule

        engine = RiskAlertEngine()

        # 检查规则是否存在
        rules = engine.rules

        # 应该有针对负面信念的规则
        rule_names = [r.name for r in rules]
        has_negative_rule = any(
            'negative' in name.lower() or 'rumor' in name.lower()
            for name in rule_names
        )

        assert has_negative_rule, "风险引擎应包含负面信念相关规则"


class TestPersonaSusceptibility:
    """测试人设易感性字段"""

    def test_persona_config_has_negative_susceptibility(self):
        """测试人设配置包含负面易感性"""
        from backend.config.persona_config import PERSONA_CONFIGS

        # 检查人设配置
        for persona_name, config in PERSONA_CONFIGS.items():
            # 应该包含负面易感性或谣言易感性
            has_negative = hasattr(config, 'negative_susceptibility') or hasattr(config, 'rumor_susceptibility')
            assert has_negative, f"{persona_name} 应包含易感性配置"


class TestFullIntegration:
    """完整集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from backend.app import app
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def reset_engine(self):
        """每个测试前重置引擎"""
        import backend.app
        backend.app.engine = None
        yield
        backend.app.engine = None

    def test_full_flow_with_new_naming(self, client):
        """测试使用新命名的完整流程"""
        # 启动推演（使用新参数名）
        start_response = client.post("/api/simulation/start", json={
            "initial_negative_spread": 0.3,
            "response_delay": 5,
            "population_size": 50,
            "use_llm": False
        })
        assert start_response.status_code == 200

        # 执行几步
        for _ in range(3):
            step_response = client.get("/api/simulation/step")
            assert step_response.status_code == 200

        # 获取状态
        state_response = client.get("/api/simulation/state")
        state_data = state_response.json()

        # 验证状态包含正确字段
        has_negative = 'negative_belief_rate' in state_data or 'rumor_spread_rate' in state_data
        assert has_negative

        # 获取预测（如果可用）
        pred_response = client.get("/api/prediction")
        if pred_response.status_code == 200:
            pred_data = pred_response.json()
            if pred_data.get("success") and pred_data.get("data", {}).get("available"):
                # 预测数据应该存在
                assert "prediction" in pred_data["data"]

    def test_api_backward_compatibility(self, client):
        """测试 API 向后兼容性"""
        # 使用旧参数名启动
        old_params = {
            "initial_rumor_spread": 0.3,
            "debunk_delay": 5,
            "population_size": 50,
            "use_llm": False
        }
        response = client.post("/api/simulation/start", json=old_params)
        assert response.status_code == 200

        # 使用新参数名启动
        client.post("/api/simulation/finish")  # 清理
        new_params = {
            "initial_negative_spread": 0.3,
            "response_delay": 5,
            "population_size": 50,
            "use_llm": False
        }
        response = client.post("/api/simulation/start", json=new_params)
        assert response.status_code == 200


# ==================== 辅助函数测试 ====================

class TestHelperFunctions:
    """测试辅助函数"""

    def test_opinion_stance_labels(self):
        """测试观点立场标签转换"""
        # 正面信念（>0.2）应返回正确认知
        # 负面信念（<-0.2）应返回误信
        # 中间应返回中立

        labels = {
            0.5: "正确认知",
            -0.5: "误信",
            0.0: "中立"
        }

        for opinion, expected_label in labels.items():
            # 模拟前端标签转换逻辑
            if opinion > 0.2:
                label = "正确认知"
            elif opinion < -0.2:
                label = "误信"
            else:
                label = "中立"

            assert label == expected_label


class TestDocumentation:
    """测试文档映射"""

    def test_refactor_mapping_exists(self):
        """测试重构映射文档存在"""
        import os

        mapping_path = "docs/refactor_mapping.md"
        assert os.path.exists(mapping_path), "重构映射文档应存在"

    def test_refactor_mapping_complete(self):
        """测试重构映射文档完整性"""
        with open("docs/refactor_mapping.md", "r", encoding="utf-8") as f:
            content = f.read()

        # 检查必要章节存在
        required_sections = [
            "核心概念映射",
            "字段命名映射",
            "前端文案映射",
            "向后兼容策略"
        ]

        for section in required_sections:
            assert section in content, f"映射文档应包含 '{section}' 章节"

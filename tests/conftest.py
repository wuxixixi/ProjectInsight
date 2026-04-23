"""
信息茧房推演系统测试配置
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(autouse=True)
def reset_global_state():
    """每个测试前重置全局状态，避免测试间污染"""
    from backend.simulation.persona import clear_agent_snapshots
    from backend import state

    clear_agent_snapshots()
    state.reset_state()

    # 重置 LLM 客户端全局实例
    import backend.llm.client
    backend.llm.client._llm_client = None

    # 重置 GraphParserAgent 全局单例
    from backend.simulation.graph_parser_agent import reset_graph_parser
    reset_graph_parser()

    # 重置 RiskAlertEngine 全局实例
    from backend.simulation.risk_alert import reset_risk_engine
    reset_risk_engine()

    # issue #1076: 重置 PersonAgent 类变量
    from backend.simulation.agent.person_agent import PersonAgent
    PersonAgent.opinion_max_change_factor = 0.3
    PersonAgent.social_influence_coeff = 0.3
    # issue #1148: 重置沉默阈值类变量
    PersonAgent.silence_fear_threshold = 0.6
    PersonAgent.silence_delta_threshold = 0.1

    yield

    clear_agent_snapshots()
    state.reset_state()
    backend.llm.client._llm_client = None
    reset_graph_parser()
    reset_risk_engine()
    PersonAgent.opinion_max_change_factor = 0.3
    PersonAgent.social_influence_coeff = 0.3
    PersonAgent.silence_fear_threshold = 0.6
    PersonAgent.silence_delta_threshold = 0.1

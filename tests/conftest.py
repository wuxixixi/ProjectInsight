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
    state.engine = None
    state.prediction_model = None
    state.pending_knowledge_graph = None
    state.pending_event_content = None
    state.pending_event_source = None
    state.injection_in_progress = False
    yield
    clear_agent_snapshots()
    state.engine = None
    state.prediction_model = None

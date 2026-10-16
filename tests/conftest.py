"""
ProjectInsight test configuration.
"""
import sys
from pathlib import Path

import pytest

# Add project root to Python path.
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def _reset_global_state_impl():
    """Helper function to reset mutable global state."""
    from backend import state
    import backend.llm.client
    from backend.simulation.graph_parser_agent import reset_graph_parser
    from backend.simulation.persona import clear_agent_snapshots
    from backend.simulation.risk_alert import reset_risk_engine
    from backend.simulation.agent.person_agent import PersonAgent

    clear_agent_snapshots()
    state.reset_state()
    backend.llm.client._llm_client = None
    reset_graph_parser()
    reset_risk_engine()

    PersonAgent.opinion_max_change_factor = 0.3
    PersonAgent.social_influence_coeff = 0.3
    PersonAgent.silence_fear_threshold = 0.6
    PersonAgent.silence_delta_threshold = 0.1

    try:
        from backend.simulation.env.truth_env import Intervention
        Intervention.reset_id_counter()
    except ImportError:
        pass


@pytest.fixture
def reset_global_state():
    """Reset mutable global state between tests."""
    _reset_global_state_impl()
    yield
    _reset_global_state_impl()

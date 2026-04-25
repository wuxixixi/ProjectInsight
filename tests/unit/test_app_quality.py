"""app.py 代码质量回归测试"""
import inspect

from backend import app as backend_app


def test_websocket_stance_uses_shared_opinion_thresholds():
    source = inspect.getsource(backend_app.websocket_simulation)

    assert "OPINION_THRESHOLD_NEGATIVE" in source
    assert "OPINION_THRESHOLD_POSITIVE" in source
    assert "agent_opinion < -0.3" not in source
    assert "agent_opinion > 0.3" not in source


def test_websocket_loop_does_not_import_time_repeatedly():
    source = inspect.getsource(backend_app.websocket_simulation)

    assert "import time" not in source

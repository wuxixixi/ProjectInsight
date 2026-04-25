"""
WebSocket 集成测试
测试 WebSocket 实时通信功能（支持新的 start/step/auto/stop/finish 协议）
"""
import pytest
from fastapi.testclient import TestClient
import json
import asyncio

from backend.app import app


@pytest.fixture
def client(reset_global_state):
    """创建测试客户端"""
    return TestClient(app)


# 注意：全局状态重置由 tests/conftest.py 的 reset_global_state fixture 统一处理


class TestWebSocketConnection:
    """测试 WebSocket 连接"""

    def test_websocket_connect(self, client):
        """测试 WebSocket 连接"""
        with client.websocket_connect("/ws/simulation") as websocket:
            # 连接成功，无异常即通过
            pass

    def test_websocket_step_without_init(self, client):
        """测试未初始化时步进"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({"action": "step"})
            response = websocket.receive_json()

            assert response["type"] == "error"
            assert "请先启动模拟" in response["message"]


class TestWebSocketStart:
    """测试 WebSocket 启动"""

    def test_websocket_start_math_mode(self, client):
        """测试数学模型模式启动"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({
                "action": "start",
                "params": {
                    "population_size": 30,
                    "use_llm": False
                }
            })
            response = websocket.receive_json()

            assert response["type"] == "state"
            assert response["data"]["step"] == 0
            assert len(response["data"]["agents"]) == 30

    def test_websocket_start_with_custom_params(self, client):
        """测试自定义参数启动"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({
                "action": "start",
                "params": {
                    "population_size": 50,
                    "cocoon_strength": 0.8,
                    "debunk_delay": 5,
                    "use_llm": False
                }
            })
            response = websocket.receive_json()

            assert response["type"] == "state"
            assert response["data"]["step"] == 0


class TestWebSocketStep:
    """测试 WebSocket 步进"""

    def test_websocket_step_math_mode(self, client):
        """测试数学模型模式步进"""
        with client.websocket_connect("/ws/simulation") as websocket:
            # 启动
            websocket.send_json({
                "action": "start",
                "params": {"population_size": 30, "use_llm": False}
            })
            websocket.receive_json()

            # 步进
            websocket.send_json({"action": "step"})
            response = websocket.receive_json()

            assert response["type"] == "state"
            assert response["data"]["step"] == 1

    def test_websocket_multiple_steps(self, client):
        """测试多次步进"""
        with client.websocket_connect("/ws/simulation") as websocket:
            # 启动
            websocket.send_json({
                "action": "start",
                "params": {"population_size": 30, "use_llm": False}
            })
            websocket.receive_json()

            # 执行多步
            for i in range(5):
                websocket.send_json({"action": "step"})
                response = websocket.receive_json()
                assert response["data"]["step"] == i + 1


class TestWebSocketAutoMode:
    """测试 WebSocket 自动推演"""

    def test_websocket_auto_mode(self, client):
        """测试自动推演模式"""
        with client.websocket_connect("/ws/simulation") as websocket:
            # 启动
            websocket.send_json({
                "action": "start",
                "params": {"population_size": 20, "use_llm": False}
            })
            websocket.receive_json()

            # 启动自动推演（间隔 100ms）
            websocket.send_json({"action": "auto", "interval": 100})

            # 接收多个状态
            states = []
            for _ in range(3):
                response = websocket.receive_json()
                if response["type"] == "state":
                    states.append(response["data"])

            # 停止
            websocket.send_json({"action": "stop"})

            # 验证步数递增
            steps = [s["step"] for s in states]
            assert steps == sorted(steps)

    def test_websocket_auto_without_start(self, client):
        """测试未启动时自动推演"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({"action": "auto", "interval": 100})
            response = websocket.receive_json()

            assert response["type"] == "error"


class TestWebSocketFinish:
    """测试 WebSocket 完成和报告"""

    def test_websocket_finish(self, client):
        """测试完成并生成报告"""
        with client.websocket_connect("/ws/simulation") as websocket:
            # 启动
            websocket.send_json({
                "action": "start",
                "params": {"population_size": 30, "use_llm": False}
            })
            websocket.receive_json()

            # 步进
            websocket.send_json({"action": "step"})
            websocket.receive_json()

            # 完成
            websocket.send_json({"action": "finish"})
            response = websocket.receive_json()

            assert response["type"] == "report"
            assert response["data"]["success"] is True
            assert "report_path" in response["data"]

    def test_websocket_finish_without_start(self, client):
        """测试未启动时完成"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({"action": "finish"})
            response = websocket.receive_json()

            assert response["type"] == "error"


class TestWebSocketStateConsistency:
    """测试 WebSocket 状态一致性"""

    def test_websocket_state_after_steps(self, client):
        """测试多步后状态一致"""
        with client.websocket_connect("/ws/simulation") as websocket:
            # 启动
            websocket.send_json({
                "action": "start",
                "params": {"population_size": 30, "use_llm": False}
            })
            init_state = websocket.receive_json()

            # 执行多步
            for _ in range(5):
                websocket.send_json({"action": "step"})
                websocket.receive_json()

            # 验证步数
            # 最后一个状态的 step 应该是 5
            websocket.send_json({"action": "step"})
            final_state = websocket.receive_json()

            assert final_state["data"]["step"] == 6


class TestWebSocketEdgeCases:
    """测试 WebSocket 边界情况"""

    def test_websocket_unknown_action(self, client):
        """测试未知动作"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({"action": "unknown"})
            # 不应崩溃，连接保持

    def test_websocket_empty_message(self, client):
        """测试空消息"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({})
            # 不应崩溃

    def test_websocket_partial_params(self, client):
        """测试部分参数"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({
                "action": "start",
                "params": {"cocoon_strength": 0.8}  # 只提供部分参数
            })
            response = websocket.receive_json()
            # 应使用默认值
            assert response["type"] == "state"
            assert response["data"]["step"] == 0


class TestWebSocketLLMMode:
    """测试 LLM 模式的 WebSocket 行为"""

    def test_websocket_llm_mode_start(self, client):
        """测试 LLM 模式启动"""
        with client.websocket_connect("/ws/simulation") as websocket:
            websocket.send_json({
                "action": "start",
                "params": {
                    "population_size": 10,
                    "use_llm": True
                }
            })
            response = websocket.receive_json()

            assert response["type"] == "state"
            assert response["data"]["step"] == 0

    # 注意: LLM 模式的步进测试需要真实的 LLM 连接或 mock
    # 这里只测试启动，步进会在集成测试中覆盖

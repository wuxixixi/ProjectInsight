"""
API 集成测试
测试 FastAPI 端点的完整功能（支持 LLM 和数学模型两种模式）
"""
import pytest
from fastapi.testclient import TestClient
import json

from backend.app import app


@pytest.fixture
def client(reset_global_state):
    """创建测试客户端"""
    return TestClient(app)


# 注意：全局状态重置由 tests/conftest.py 的 reset_global_state fixture 统一处理


class TestRootEndpoint:
    """测试根端点"""

    def test_root_returns_ok(self, client):
        """测试根路径返回正常状态"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "version" in data


class TestSimulationStart:
    """测试模拟启动端点"""

    def test_start_with_default_params(self, client):
        """测试使用默认参数启动（数学模型模式）"""
        response = client.post("/api/simulation/start", json={"use_llm": False})

        assert response.status_code == 200
        data = response.json()
        assert data["step"] == 0
        assert "agents" in data
        assert "edges" in data
        assert "opinion_distribution" in data

    def test_start_with_custom_params(self, client):
        """测试使用自定义参数启动"""
        params = {
            "cocoon_strength": 0.8,
            "debunk_delay": 5,
            "population_size": 100,
            "initial_rumor_spread": 0.4,
            "network_type": "scale_free",
            "use_llm": False
        }
        response = client.post("/api/simulation/start", json=params)

        assert response.status_code == 200
        data = response.json()
        assert len(data["agents"]) == 100

    def test_start_returns_valid_state(self, client):
        """测试启动返回有效状态"""
        response = client.post("/api/simulation/start", json={"use_llm": False})
        data = response.json()

        # 验证状态字段
        assert "step" in data
        assert "agents" in data
        assert "edges" in data
        assert "opinion_distribution" in data
        assert "rumor_spread_rate" in data
        assert "truth_acceptance_rate" in data
        assert "avg_opinion" in data
        assert "polarization_index" in data

    def test_start_initializes_engine(self, client):
        """测试启动初始化引擎"""
        import backend.state

        client.post("/api/simulation/start", json={"use_llm": False})

        assert backend.state.engine is not None
        assert backend.state.engine.use_llm is False


class TestSimulationStep:
    """测试模拟步进端点"""

    def test_step_without_start_returns_error(self, client):
        """测试未启动时步进返回错误"""
        response = client.get("/api/simulation/step")

        assert response.status_code == 400
        assert "error" in response.json()

    def test_step_after_start_math_mode(self, client):
        """测试数学模型模式启动后步进"""
        client.post("/api/simulation/start", json={"population_size": 50, "use_llm": False})
        response = client.get("/api/simulation/step")

        assert response.status_code == 200
        data = response.json()
        assert data["step"] == 1

    def test_step_llm_mode_returns_error(self, client):
        """测试 LLM 模式下同步步进返回错误"""
        client.post("/api/simulation/start", json={"population_size": 50, "use_llm": True})
        response = client.get("/api/simulation/step")

        assert response.status_code == 400
        assert "LLM 模式请使用 WebSocket" in response.json()["error"]

    def test_step_increments_count(self, client):
        """测试步进增加计数"""
        client.post("/api/simulation/start", json={"population_size": 50, "use_llm": False})

        for i in range(5):
            response = client.get("/api/simulation/step")
            assert response.json()["step"] == i + 1

    def test_step_updates_state(self, client):
        """测试步进更新状态"""
        client.post("/api/simulation/start", json={"population_size": 50, "use_llm": False})

        state1 = client.get("/api/simulation/state").json()
        client.get("/api/simulation/step")
        state2 = client.get("/api/simulation/state").json()

        assert state2["step"] > state1["step"]


class TestSimulationState:
    """测试状态获取端点"""

    def test_state_without_start_returns_error(self, client):
        """测试未启动时获取状态返回错误"""
        response = client.get("/api/simulation/state")

        assert response.status_code == 400
        assert "error" in response.json()

    def test_state_after_start(self, client):
        """测试启动后获取状态"""
        client.post("/api/simulation/start", json={"population_size": 50, "use_llm": False})
        response = client.get("/api/simulation/state")

        assert response.status_code == 200
        data = response.json()
        assert data["step"] == 0


class TestReportEndpoints:
    """测试报告相关端点"""

    def test_finish_without_start_returns_error(self, client):
        """测试未启动时完成返回错误"""
        response = client.post("/api/simulation/finish")

        assert response.status_code == 400

    def test_finish_generates_report(self, client):
        """测试完成生成报告"""
        client.post("/api/simulation/start", json={"population_size": 50, "use_llm": False})
        client.get("/api/simulation/step")

        response = client.post("/api/simulation/finish")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "report_path" in data

    def test_list_reports(self, client):
        """测试列出报告"""
        response = client.get("/api/report/list")

        assert response.status_code == 200
        assert "reports" in response.json()

    def test_open_report_not_found(self, client):
        """测试打开不存在的报告"""
        response = client.post("/api/report/open", json={"path": "/nonexistent/report.md"})

        assert response.status_code == 404


class TestFullSimulation:
    """完整模拟流程测试"""

    def test_full_simulation_flow(self, client):
        """测试完整模拟流程（数学模型模式）"""
        # 启动模拟
        start_response = client.post("/api/simulation/start", json={
            "population_size": 50,
            "cocoon_strength": 0.5,
            "debunk_delay": 3,
            "use_llm": False
        })
        assert start_response.status_code == 200

        # 执行多步
        for i in range(10):
            step_response = client.get("/api/simulation/step")
            assert step_response.status_code == 200
            data = step_response.json()
            assert data["step"] == i + 1

        # 获取最终状态
        state_response = client.get("/api/simulation/state")
        assert state_response.status_code == 200

    def test_restart_simulation(self, client):
        """测试重新启动模拟"""
        # 第一次启动
        client.post("/api/simulation/start", json={"population_size": 50, "use_llm": False})
        client.get("/api/simulation/step")
        client.get("/api/simulation/step")

        # 重新启动
        response = client.post("/api/simulation/start", json={"population_size": 30, "use_llm": False})
        assert response.status_code == 200
        assert len(response.json()["agents"]) == 30
        assert response.json()["step"] == 0

    def test_different_network_types(self, client):
        """测试不同网络类型"""
        network_types = ["small_world", "scale_free", "random"]

        for net_type in network_types:
            response = client.post("/api/simulation/start", json={
                "population_size": 30,
                "network_type": net_type,
                "use_llm": False
            })
            assert response.status_code == 200


class TestErrorHandling:
    """测试错误处理"""

    def test_invalid_json(self, client):
        """测试无效 JSON"""
        response = client.post(
            "/api/simulation/start",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_invalid_param_types(self, client):
        """测试无效参数类型"""
        response = client.post("/api/simulation/start", json={
            "population_size": "not_a_number"
        })
        assert response.status_code == 422

"""
API 集成测试
测试 FastAPI 端点的完整功能（支持 LLM 和数学模型两种模式）
"""
import pytest
from fastapi.testclient import TestClient
import json
from pathlib import Path
import shutil
import uuid

from backend.app import app
import backend.simulation.realistic_population as realistic_population


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

    def test_generate_intelligence_requires_llm_engine(self, client):
        """测试智库专报接口已挂载且会校验LLM推演状态"""
        response = client.post("/api/report/generate")

        assert response.status_code == 400
        assert "success" in response.json()

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


class TestProfileLibraryApi:
    """测试用户资料画像资料库 API"""

    def test_list_upload_build_and_start_with_custom_profile(self, client, monkeypatch):
        base = Path("data") / "test_profile_api" / uuid.uuid4().hex
        cache_dir = base / "profiles"
        library_dir = base / "library"
        cache_dir.mkdir(parents=True, exist_ok=True)
        library_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv("REALISTIC_PROFILE_CACHE_DIR", str(cache_dir))
        monkeypatch.setenv("USER_PROFILE_LIBRARY_DIR", str(library_dir))
        monkeypatch.setattr(realistic_population, "PROFILE_CACHE_DIR", cache_dir)
        monkeypatch.setattr(realistic_population, "USER_PROFILE_LIBRARY_DIR", library_dir)

        list_response = client.get("/api/profiles")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["success"] is True
        assert any(item["profile_id"] == "shass_news_institute" for item in list_data["profiles"])

        upload_response = client.post(
            "/api/profiles/upload",
            data={
                "profile_id": "demo_team",
                "display_name": "演示团队",
            },
            files=[
                ("files", ("people.csv", "姓名,部门,职称,研究方向,年龄,工龄,简介\n张三,新闻所,研究员,舆情治理,48,24,长期研究舆情治理。\n", "text/csv")),
                ("files", ("notes.md", "# 成员\n姓名: 李四\n部门: 传播室\n职称: 副研究员\n研究方向: 国际传播\n年龄: 39\n工龄: 12\n", "text/markdown")),
            ],
        )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert upload_data["success"] is True
        assert upload_data["profile_id"] == "demo_team"
        assert len(upload_data["saved"]) == 2

        build_response = client.post(
            "/api/profiles/build",
            json={
                "profile_id": "demo_team",
                "display_name": "演示团队",
            },
        )
        assert build_response.status_code == 200
        build_data = build_response.json()
        assert build_data["success"] is True
        assert build_data["profile"]["profile_id"] == "demo_team"
        assert build_data["profile"]["size"] == 2
        assert build_data["profile"]["agents"][0]["generation_trace"]["source"] == "user_profile_library"

        start_response = client.post("/api/simulation/start", json={
            "use_llm": False,
            "population_profile_id": "demo_team",
            "refresh_realistic_profile": False,
        })
        assert start_response.status_code == 200
        start_data = start_response.json()
        assert len(start_data["agents"]) == 2
        assert start_data["agents"][0]["realistic_profile"]["generation_trace"]["source"] == "user_profile_library"

        list_response_after = client.get("/api/profiles")
        assert list_response_after.status_code == 200
        list_data_after = list_response_after.json()
        demo_profile = next(item for item in list_data_after["profiles"] if item["profile_id"] == "demo_team")
        assert demo_profile["kind"] == "user"
        assert demo_profile["size"] == 2
        assert demo_profile["ready"] is True
        shutil.rmtree(base, ignore_errors=True)

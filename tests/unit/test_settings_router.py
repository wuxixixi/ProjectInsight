from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import app


def test_llm_settings_round_trip(monkeypatch, reset_global_state):
    test_dir = Path("data/test_runtime_settings")
    test_dir.mkdir(parents=True, exist_ok=True)
    settings_path = test_dir / "system_settings.json"
    monkeypatch.setenv("SYSTEM_SETTINGS_PATH", str(settings_path))

    client = TestClient(app)

    payload = {
        "simulation_llm": {
            "base_url": "http://sim/v1",
            "api_key": "sim-key",
            "model": "DeepSeek-V3.2",
        },
        "report_llm": {
            "base_url": "http://report/v1",
            "api_key": "report-key",
            "model": "DeepSeek-R1-0528-64k",
        },
    }

    save_resp = client.post("/api/settings/llm", json=payload)
    assert save_resp.status_code == 200
    save_data = save_resp.json()
    assert save_data["success"] is True
    assert save_data["data"]["simulation_llm"]["model"] == "DeepSeek-V3.2"
    assert save_data["data"]["report_llm"]["model"] == "DeepSeek-R1-0528-64k"

    get_resp = client.get("/api/settings/llm")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["success"] is True
    assert get_data["data"]["simulation_llm"]["base_url"] == "http://sim/v1"
    assert get_data["data"]["report_llm"]["base_url"] == "http://report/v1"
    assert settings_path.exists()

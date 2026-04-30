import shutil
import uuid
from pathlib import Path

from backend.helpers import StartRequest
import backend.simulation.realistic_population as realistic_population
from backend.simulation.engine import SimulationEngine
from backend.simulation.realistic_population import load_realistic_population


def _workspace_cache_dir() -> Path:
    path = Path("data") / "test_realistic_profiles" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_start_request_accepts_realistic_population_fields():
    request = StartRequest(
        population_profile_id="shass_news_institute",
        realistic_profile_source_path="missing.xlsx",
        refresh_realistic_profile=False,
    )

    assert request.population_profile_id == "shass_news_institute"
    assert request.realistic_profile_source_path == "missing.xlsx"


def test_load_realistic_population_falls_back_to_anonymized_synthetic_profile(monkeypatch):
    cache_dir = _workspace_cache_dir()
    monkeypatch.setenv("REALISTIC_PROFILE_CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(realistic_population, "PROFILE_CACHE_DIR", cache_dir)

    try:
        profile = load_realistic_population(
            "shass_news_institute",
            source_path=str(cache_dir / "missing.xlsx"),
        )

        assert profile.size == 27
        assert profile.profile_id == "shass_news_institute"
        assert profile.source_path == "synthetic://shass_news_institute"
        assert all(agent.persona["profile_mode"] == "realistic" for agent in profile.agents)
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)


def test_simulation_engine_applies_realistic_profile_to_math_population(monkeypatch):
    cache_dir = _workspace_cache_dir()
    monkeypatch.setenv("REALISTIC_PROFILE_CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(realistic_population, "PROFILE_CACHE_DIR", cache_dir)
    try:
        engine = SimulationEngine(
            use_llm=False,
            population_size=200,
            population_profile_id="shass_news_institute",
            realistic_profile_source_path=str(cache_dir / "missing.xlsx"),
            use_v3=False,
        )

        state = engine.initialize()

        assert engine.population_size == 27
        assert engine.population.size == 27
        assert len(state.agents) == 27
        assert state.agents[0]["realistic_profile"]["department"] == "上海社会科学院新闻研究所"
        assert state.agents[0]["persona"]["profile_mode"] == "realistic"
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)

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
        assert profile.agents[0].generation_trace["source"] == "synthetic_roster"
        assert "belief_strength" in profile.agents[0].generation_trace["metrics"]
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
        assert state.agents[0]["realistic_profile"]["generation_trace"]["source"] in {"synthetic_roster", "workbook"}
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)


def test_simulation_engine_applies_realistic_profile_to_llm_population(monkeypatch):
    cache_dir = _workspace_cache_dir()
    monkeypatch.setenv("REALISTIC_PROFILE_CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(realistic_population, "PROFILE_CACHE_DIR", cache_dir)
    try:
        engine = SimulationEngine(
            use_llm=True,
            population_size=27,
            population_profile_id="shass_news_institute",
            realistic_profile_source_path=str(cache_dir / "missing.xlsx"),
            use_v3=False,
        )

        state = engine.initialize()

        assert engine.population_size == 27
        assert engine.llm_population is not None
        assert len(state.agents) == 27
        assert state.agents[0]["realistic_profile"]["name"]
        assert state.agents[0]["realistic_profile"]["generation_trace"]["source"] in {"synthetic_roster", "workbook"}
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)


def test_user_defined_profile_builds_and_reuses_offline_cache(monkeypatch):
    cache_dir = _workspace_cache_dir()
    library_dir = cache_dir / "library"
    monkeypatch.setenv("REALISTIC_PROFILE_CACHE_DIR", str(cache_dir / "profiles"))
    monkeypatch.setenv("USER_PROFILE_LIBRARY_DIR", str(library_dir))
    monkeypatch.setattr(realistic_population, "PROFILE_CACHE_DIR", cache_dir / "profiles")
    monkeypatch.setattr(realistic_population, "USER_PROFILE_LIBRARY_DIR", library_dir)
    try:
        source_dir = realistic_population.get_user_profile_source_dir("demo_team")
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "people.csv").write_text(
            "姓名,部门,职称,研究方向,年龄,工龄,简介\n"
            "张三,新闻所,研究员,舆情治理,48,24,长期研究舆情治理和平台治理。\n"
            "李四,传播室,副研究员,国际传播,39,12,关注国际传播和新媒体研究。\n",
            encoding="utf-8",
        )

        profile = realistic_population.build_user_defined_population_profile(
            "demo_team",
            display_name="演示团队",
        )
        cached = load_realistic_population("demo_team")

        assert profile.size == 2
        assert cached.size == 2
        assert cached.profile_id == "demo_team"
        assert cached.display_name == "演示团队"
        assert cached.agents[0].name == "张三"
        assert cached.agents[0].persona["type"] == "用户资料画像"
        assert cached.agents[0].generation_trace["source"] == "user_profile_library"
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)


def test_simulation_engine_applies_user_defined_profile_to_math_population(monkeypatch):
    cache_dir = _workspace_cache_dir()
    library_dir = cache_dir / "library"
    monkeypatch.setenv("REALISTIC_PROFILE_CACHE_DIR", str(cache_dir / "profiles"))
    monkeypatch.setenv("USER_PROFILE_LIBRARY_DIR", str(library_dir))
    monkeypatch.setattr(realistic_population, "PROFILE_CACHE_DIR", cache_dir / "profiles")
    monkeypatch.setattr(realistic_population, "USER_PROFILE_LIBRARY_DIR", library_dir)
    try:
        source_dir = realistic_population.get_user_profile_source_dir("policy_team")
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "profiles.json").write_text(
            '[{"name":"王五","department":"政策室","title":"副研究员","specialty":"公共政策传播","age":42}]',
            encoding="utf-8",
        )
        realistic_population.build_user_defined_population_profile("policy_team", display_name="政策团队")

        engine = SimulationEngine(
            use_llm=False,
            population_size=200,
            population_profile_id="policy_team",
            use_v3=False,
        )
        state = engine.initialize()

        assert engine.population_size == 1
        assert len(state.agents) == 1
        assert state.agents[0]["realistic_profile"]["name"] == "王五"
        assert state.agents[0]["realistic_profile"]["generation_trace"]["source"] == "user_profile_library"
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)

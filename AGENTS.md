# AGENTS.md

## Project Overview

Multi-agent opinion simulation system ("信息茧房推演系统"). Two simulation modes:
- **Math model**: formula-based fast evolution (`backend/simulation/engine.py`)
- **LLM-driven**: agents decide via LLM calls (`backend/simulation/engine_dual.py` default, `engine.py` with `use_llm=True`)

Two network architectures:
- **Single-layer** (`SimulationEngine`): one social graph, selectable topology
- **Dual-layer** (`SimulationEngineDual`): public (scale-free) + private (stochastic block model) networks — this is the default when `use_dual_network=True`

## Quick Reference

```bash
# Backend
pip install -r requirements.txt
uvicorn backend.app:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev   # dev server at :3000, proxies /api and /ws to :8000

# Tests
pytest tests/ -v                            # all tests
pytest tests/unit/ -v                       # unit only
pytest tests/integration/ -v                # integration only
pytest tests/unit/test_engine.py -v         # single file
pytest tests/unit/test_engine.py::TestEngineInit -v  # single class
pytest tests/ --cov=backend --cov-report=html
```

## Critical Architecture Facts

### Global State (`backend/state.py`)
- Module uses a custom `_StateModule` class that replaces `sys.modules[__name__]` to intercept attribute access
- `state.engine`, `state.injection_in_progress`, etc. are all thread-safe via `RLock`
- Tests MUST use the `reset_global_state` fixture (defined in `tests/conftest.py`) which resets: `state`, LLM client singleton, graph parser, risk engine, agent snapshots, and `PersonAgent` class-level params
- Without this fixture, state leaks between tests

### LLM Client (`backend/llm/client.py`)
- Requires `.env` file with `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` (see `.env.example`)
- `LLMClient` must be used as `async with LLMClient() as client` — raises `RuntimeError` otherwise
- Global singleton via `get_llm_client()`; tests reset it via `backend.llm.client._llm_client = None`
- Concurrency auto-calculated from `population_size`; override via `LLM_CONCURRENCY_PROFILE` env var

### Pydantic v2 Compatibility
- `backend/models/schemas.py` uses `@model_validator(mode='before')` for backward-compatible field mapping (e.g. `exposed_to_rumor` → `exposed_to_negative`)
- `json_encoders` and class-based `config` deprecation warnings are suppressed in `pytest.ini`

### Two Engine Classes
- `SimulationEngine` (`engine.py`): supports both math and LLM modes via `use_llm` flag
- `SimulationEngineDual` (`engine_dual.py`): dual-layer network, always LLM-capable
- Both share the same `SimulationState` schema and `async_step()` / `step()` interface
- LLM mode requires `async_step()`; calling sync `step()` in LLM mode raises `RuntimeError`

### pytest Configuration (`pytest.ini`)
- `asyncio_mode = auto` — async tests run automatically without `@pytest.mark.asyncio` (though the decorator is still used in some tests)
- Test paths: `tests/integration`, `tests/unit`, `tests` (includes root-level files in `tests/`)
- Root-level `test_*.py` files (e.g. `test_engine_v3.py`) are NOT discovered by default pytest paths — they import from `backend` directly and test v3 integration

### Frontend
- Single Vue 3 SPA in `frontend/src/` (just `App.vue`, `main.js`, `assets/`)
- Vite proxies `/api` → `http://localhost:8000` and `/ws` → `ws://localhost:8000`
- Build uses terser, manual chunks for vendor/echarts/markdown/d3
- `npm run lint` runs eslint, `npm run format` runs prettier

## Common Pitfalls

1. **Missing `.env`**: LLM tests that hit the real API will fail without valid credentials. Mock LLM client in unit tests.
2. **Root-level test files**: `test_engine_v3.py`, `test_agent_module.py`, etc. at repo root are standalone — run them with `python -m pytest test_engine_v3.py` if needed.
3. **State leakage**: Always use `reset_global_state` fixture in integration tests. The `backend/state.py` module proxy means `import backend.state` gives you the intercepted module.
4. **Sync vs async step**: `engine.step()` in LLM mode raises. Use `await engine.async_step()`.
5. **Dual-network defaults**: `use_dual_network=True` is the default in `StartRequest`; tests that want single-layer must explicitly set `use_dual_network=False`.

## Key Directories

| Path | Purpose |
|------|---------|
| `backend/simulation/engine.py` | Single-layer engine (math + LLM) |
| `backend/simulation/engine_dual.py` | Dual-layer engine (public/private networks) |
| `backend/simulation/agent/` | v3 agent model: `PersonAgent`, `BeliefState`, memory, skills |
| `backend/simulation/env/` | v3 environments: `AlgorithmEnv`, `SocialEnv`, `TruthEnv` |
| `backend/simulation/psychology/` | Maslow needs hierarchy, Theory of Planned Behavior |
| `backend/simulation/message/` | P2P, P2G, group chat messaging |
| `backend/llm/client.py` | LLM client with retry, backoff, streaming |
| `backend/routers/` | FastAPI routers: simulation, report, event, prediction |
| `backend/models/schemas.py` | Pydantic v2 models with legacy field mapping |
| `backend/state.py` | Thread-safe global state (module-level proxy) |
| `frontend/src/App.vue` | Main UI (single-file SPA) |
| `tests/conftest.py` | Shared fixtures, especially `reset_global_state` |
| `data/` | SQLite DBs (memory, replay), realistic population profiles |
| `reports/` | Generated markdown reports (gitignored) |

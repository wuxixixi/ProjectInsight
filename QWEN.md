# QWEN.md

This file provides guidance to Qwen Code when working in this repository.

## Project Overview

ProjectInsight（“觉测·洞鉴 - 信息茧房推演系统”）is a multi-agent public-opinion and information-cocoon simulation system. It visualizes how algorithmic recommendation, social-network propagation, and official/authoritative responses affect group beliefs over time.

The project is a full-stack codebase:

- **Backend:** Python 3.10+, FastAPI, Pydantic v2, NumPy, NetworkX, AsyncIO, SQLite-backed memory/replay components, optional LLM integration.
- **Frontend:** Vue 3 + Vite, ECharts, D3.js, Marked, DOMPurify, Axios.
- **Testing:** pytest + pytest-asyncio.
- **LLM integration:** OpenAI-compatible API configuration via environment variables, with examples targeting Qwen/DeepSeek-style endpoints.

Core backend concepts include:

- Simulation engines supporting mathematical and LLM-driven agent decisions.
- Sandbox and news-driven simulation modes.
- Dual-layer/public-private network modeling.
- Pydantic schemas with backward-compatible legacy field mappings.
- WebSocket-driven real-time simulation updates.
- Report generation and analyst-agent style output.

## Repository Structure

```text
ProjectInsight/
├── backend/                 # Python FastAPI backend
│   ├── app.py               # FastAPI app entrypoint and WebSocket endpoint
│   ├── constants.py         # Shared backend constants
│   ├── helpers.py           # Shared helper utilities
│   ├── state.py             # Global runtime simulation state
│   ├── config/              # Backend configuration modules
│   ├── llm/                 # LLM client/configuration
│   ├── models/              # Pydantic schemas and API models
│   ├── routers/             # FastAPI route modules
│   └── simulation/          # Core simulation engines, agents, psychology/model logic
├── frontend/                # Vue 3 + Vite frontend
│   ├── src/                 # Vue application source
│   ├── public/              # Static frontend assets
│   ├── package.json         # Frontend scripts and dependencies
│   └── vite.config.js       # Vite config and dev-server proxy
├── tests/                   # pytest test suite
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── manual/              # Manual or exploratory tests
├── docs/                    # Project documentation
├── ops/                     # Deployment/operations assets
├── reports/                 # Generated reports
├── data/                    # Runtime or sample data
├── requirements.txt         # Python dependencies
├── pytest.ini               # pytest configuration
├── .env.example             # Example LLM/runtime environment configuration
└── README.md                # Main project documentation
```

## Building, Running, and Testing

### Backend environment

Use Python 3.10+.

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

The README also documents a conda environment option:

```bash
conda create -n info-cocoon python=3.10
conda activate info-cocoon
pip install -r requirements.txt
```

### Environment variables

Copy `.env.example` to `.env` before using LLM-backed functionality:

```bash
cp .env.example .env
```

Important variables include:

- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_CONCURRENCY_PROFILE`
- `LLM_MAX_CONCURRENT`
- `LLM_TIMEOUT`
- `LLM_MAX_RETRIES`
- `CORS_ALLOWED_ORIGINS`
- `WS_RATE_LIMIT`
- `INJECTION_TIMEOUT`

Never commit real API keys or secrets.

### Run backend

```bash
uvicorn backend.app:app --reload --port 8000
```

For LAN/container-style access, existing comments indicate this form is also used:

```bash
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

### Run frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on port `3000`. `vite.config.js` proxies:

- `/api` → `http://localhost:8000`
- `/ws` → `ws://localhost:8000`

### Build frontend

```bash
cd frontend
npm run build
```

### Preview frontend production build

```bash
cd frontend
npm run preview
```

### Run tests

The pytest configuration is in `pytest.ini`:

```bash
pytest
```

Useful marker-based test commands:

```bash
pytest -m unit
pytest -m integration
pytest -m "not slow"
pytest -m "not skip_llm"
```

Configured pytest conventions:

- Test paths: `tests`
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Default addopts: `--tb=short -q`
- Async mode: `auto`

## API and Runtime Notes

Backend entrypoint: `backend/app.py`.

Registered FastAPI route groups currently include simulation, report, event, and prediction routers.

Important API/WebSocket paths documented in the README and backend include:

- `GET /` — health check
- `/api/...` — REST API routes registered from `backend/routers/`
- `WS /ws/simulation` — real-time simulation control and state updates

WebSocket messages are JSON objects with an `action` string, for example:

```json
{"action": "start", "params": {}}
{"action": "step"}
{"action": "auto", "interval": 2000}
{"action": "stop"}
{"action": "finish"}
```

The backend validates WebSocket JSON shape and applies message rate limiting via `WS_RATE_LIMIT`.

## Development Conventions

### Python/backend conventions

- Prefer Python type hints and Pydantic models for API/runtime data structures.
- Keep FastAPI routes organized under `backend/routers/` rather than adding all endpoints directly to `backend/app.py`.
- Preserve existing semantic refactor conventions:
  - New terminology prefers generic names such as negative/positive belief and authority response.
  - Legacy names such as rumor/truth/debunk are still mapped for backward compatibility in schemas and engine parameters.
- When adding request/response fields, update Pydantic schemas in `backend/models/schemas.py` and maintain compatibility where existing clients may depend on old field names.
- Use `logging.getLogger(__name__)` style logging, consistent with existing backend code.
- Avoid logging secrets, API keys, full LLM credentials, or sensitive request payloads.
- Async code is common; preserve async boundaries for FastAPI and WebSocket flows.
- Be careful with global runtime state in `backend/state.py`; simulation endpoints and WebSocket flows may share engine state.

### Simulation conventions

- The main simulation engine supports both LLM and mathematical-model modes.
- Parameters often have new canonical names plus legacy aliases. Do not remove legacy aliases without updating tests and compatibility logic.
- Default randomness is seed-based in core engine paths. Preserve deterministic behavior in tests when possible.
- Reports are written under `reports/`.

### Frontend conventions

- Frontend is Vue 3 with Vite and ES modules (`"type": "module"`).
- Use the `@` alias for `frontend/src` where appropriate; it is configured in `vite.config.js`.
- Use existing dependencies before adding new ones: Vue, Axios, ECharts, D3, Marked, DOMPurify.
- The dev server expects backend API/WebSocket access through Vite proxy paths rather than hard-coding backend URLs in components.
- Production build uses terser minification and manual vendor chunks.

### Testing conventions

- Add or update tests for backend behavior changes whenever feasible.
- Use pytest markers already declared in `pytest.ini`: `unit`, `integration`, `slow`, `skip_llm`.
- Avoid requiring live LLM calls in default tests. Mark such tests as `slow` or `skip_llm` as appropriate.
- For schema compatibility changes, add tests covering both new and legacy field names.

### Configuration and security

- Use `.env.example` only as a template; never store real credentials in repository files.
- Production CORS should be configured with `CORS_ALLOWED_ORIGINS`. Avoid wildcard origins in production.
- Be cautious when changing rate limits, timeout values, or concurrency defaults because they affect LLM cost/load and WebSocket stability.

## Common Workflows for Qwen Code

When modifying backend code:

1. Read the relevant router/schema/engine files first.
2. Preserve compatibility mappings unless the user explicitly requests a breaking change.
3. Add or update pytest tests.
4. Run targeted tests, then broader `pytest` if feasible.

When modifying frontend code:

1. Inspect neighboring Vue components and styles first.
2. Use existing libraries and Vite proxy behavior.
3. Run `npm run build` from `frontend/` after changes when feasible.

When changing API contracts:

1. Update backend schemas and router logic.
2. Update frontend consumers.
3. Update tests.
4. Update README/docs if public behavior changes.

## Notes for Future Agents

- This is a code project, not just documentation.
- The README is detailed and should be checked before changing run commands or public behavior.
- Existing `CLAUDE.md` may contain additional historical assistant guidance, but this `QWEN.md` is the project-level context for Qwen Code.
- Keep responses and code comments concise. Add comments only when they explain non-obvious reasoning.

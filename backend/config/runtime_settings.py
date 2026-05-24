"""
Runtime-configurable system settings persisted on disk.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Dict


_SETTINGS_LOCK = threading.RLock()

_LLM_ENV_KEYS = {
    "simulation_llm": {
        "base_url": "LLM_BASE_URL",
        "api_key": "LLM_API_KEY",
        "model": "LLM_MODEL",
    },
    "report_llm": {
        "base_url": "REPORT_LLM_BASE_URL",
        "api_key": "REPORT_LLM_API_KEY",
        "model": "REPORT_LLM_MODEL",
    },
}


def get_settings_path() -> Path:
    override = os.getenv("SYSTEM_SETTINGS_PATH", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "data" / "system_settings.json"


def _normalize_value(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_payload(payload: Dict) -> Dict[str, Dict[str, str]]:
    normalized: Dict[str, Dict[str, str]] = {}
    for section, fields in _LLM_ENV_KEYS.items():
        section_payload = payload.get(section, {}) if isinstance(payload, dict) else {}
        section_result: Dict[str, str] = {}
        if isinstance(section_payload, dict):
            for field in fields:
                section_result[field] = _normalize_value(section_payload.get(field))
        else:
            for field in fields:
                section_result[field] = ""
        normalized[section] = section_result
    return normalized


def load_runtime_settings() -> Dict[str, Dict[str, str]]:
    path = get_settings_path()
    if not path.exists():
        return _normalize_payload({})
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _normalize_payload({})
    return _normalize_payload(data)


def _write_runtime_settings(data: Dict[str, Dict[str, str]]) -> None:
    path = get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _apply_settings_to_env(data: Dict[str, Dict[str, str]]) -> None:
    for section, fields in _LLM_ENV_KEYS.items():
        section_data = data.get(section, {})
        for field, env_key in fields.items():
            value = _normalize_value(section_data.get(field))
            if value:
                os.environ[env_key] = value
            else:
                os.environ.pop(env_key, None)


def bootstrap_runtime_settings() -> None:
    with _SETTINGS_LOCK:
        path = get_settings_path()
        if not path.exists():
            return
        _apply_settings_to_env(load_runtime_settings())


def get_effective_llm_settings() -> Dict[str, Dict[str, str]]:
    from ..llm.client import create_llm_config_from_env

    simulation = create_llm_config_from_env("LLM")
    report = create_llm_config_from_env("REPORT_LLM")
    return {
        "simulation_llm": {
            "base_url": simulation.base_url,
            "api_key": simulation.api_key,
            "model": simulation.model,
        },
        "report_llm": {
            "base_url": report.base_url,
            "api_key": report.api_key,
            "model": report.model,
        },
    }


def _refresh_live_llm_state() -> None:
    from .. import state
    from ..llm.client import create_llm_config_from_env
    from ..simulation.graph_parser_agent import reset_graph_parser
    import backend.llm.client as llm_client_module

    simulation = create_llm_config_from_env("LLM")

    engine = state.engine
    if engine is not None:
        for target in (
            engine,
            getattr(engine, "llm_population", None),
            getattr(engine, "population", None),
        ):
            llm_config = getattr(target, "llm_config", None)
            if llm_config is not None:
                llm_config.base_url = simulation.base_url
                llm_config.api_key = simulation.api_key
                llm_config.model = simulation.model

        llm_client = getattr(engine, "llm_client", None)
        if llm_client is not None:
            llm_client.config.base_url = simulation.base_url
            llm_client.config.api_key = simulation.api_key
            llm_client.config.model = simulation.model

        if hasattr(engine, "_graph_parser"):
            engine._graph_parser = None

    llm_client_module._llm_client = None
    reset_graph_parser()


def save_runtime_settings(payload: Dict) -> Dict[str, Dict[str, str]]:
    normalized = _normalize_payload(payload)
    with _SETTINGS_LOCK:
        _write_runtime_settings(normalized)
        _apply_settings_to_env(normalized)
        _refresh_live_llm_state()
        return get_effective_llm_settings()

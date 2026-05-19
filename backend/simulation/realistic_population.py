"""Real-world organization population profiles.

The loader reads source files only when a sanitized cache is missing or
explicitly refreshed. Runtime simulations use the JSON cache. Sensitive fields
are never written to the cache or prompt payloads.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np


DEFAULT_SHASS_NEWS_INSTITUTE_PATH = r"E:\wuxi_xws\名单\251231 新闻所在职人员名单.xlsx"
PROFILE_CACHE_DIR = Path(os.getenv("REALISTIC_PROFILE_CACHE_DIR", "data/realistic_profiles"))
EVIDENCE_QUEUE_DIR = Path(os.getenv("PUBLIC_EVIDENCE_QUEUE_DIR", "data/public_evidence_queue"))
USER_PROFILE_LIBRARY_DIR = Path(os.getenv("USER_PROFILE_LIBRARY_DIR", "data/user_profiles"))
USER_PROFILE_SOURCE_DIRNAME = "sources"
USER_PROFILE_META_FILENAME = "profile.meta.json"

SENSITIVE_COLUMNS = {
    "公民身份号码",
    "身份证号",
    "联系地址",
    "手机",
    "Email",
    "邮箱",
    "健康状况",
    "婚姻状况",
    "血型",
    "户口所在地",
    "出生日期",
}

EXCLUDED_NAMES = {"徐清泉"}
SHASS_PROFILE_ALIASES = {"shass_news_institute", "上海社科院新闻所", "news_institute"}
TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
TABLE_EXTENSIONS = {".csv", ".tsv", ".json", ".jsonl", ".xlsx", ".xls"}


@dataclass(frozen=True)
class RealisticAgentProfile:
    agent_id: int
    name: str
    role_label: str
    department: str
    specialty: str
    title: str
    seniority_label: str
    community_id: int
    is_influencer: bool
    opinion: float
    belief_strength: float
    influence: float
    susceptibility: float
    fear_of_isolation: float
    conviction: float
    persona: Dict[str, Any]
    public_evidence: List[Dict[str, str]]
    search_queries: List[str]
    generation_trace: Dict[str, Any]

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role_label": self.role_label,
            "department": self.department,
            "specialty": self.specialty,
            "title": self.title,
            "seniority_label": self.seniority_label,
            "community_id": self.community_id,
            "is_influencer": self.is_influencer,
            "public_evidence": self.public_evidence,
            "search_queries": self.search_queries,
            "generation_trace": self.generation_trace,
        }

    def to_cache_dict(self) -> Dict[str, Any]:
        return {
            **self.to_public_dict(),
            "opinion": self.opinion,
            "belief_strength": self.belief_strength,
            "influence": self.influence,
            "susceptibility": self.susceptibility,
            "fear_of_isolation": self.fear_of_isolation,
            "conviction": self.conviction,
            "persona": self.persona,
        }

    @classmethod
    def from_cache_dict(cls, data: Dict[str, Any]) -> "RealisticAgentProfile":
        return cls(
            agent_id=int(data["agent_id"]),
            name=str(data.get("name", "")) or f"匿名成员 #{int(data['agent_id']) + 1}",
            role_label=str(data.get("role_label", "")),
            department=str(data.get("department", "")),
            specialty=str(data.get("specialty", "")),
            title=str(data.get("title", "")),
            seniority_label=str(data.get("seniority_label", "")),
            community_id=int(data.get("community_id", 0)),
            is_influencer=bool(data.get("is_influencer", False)),
            opinion=float(data.get("opinion", 0.0)),
            belief_strength=float(data.get("belief_strength", 0.5)),
            influence=float(data.get("influence", 0.3)),
            susceptibility=float(data.get("susceptibility", 0.4)),
            fear_of_isolation=float(data.get("fear_of_isolation", 0.5)),
            conviction=float(data.get("conviction", 0.5)),
            persona=dict(data.get("persona", {})),
            public_evidence=list(data.get("public_evidence", [])),
            search_queries=list(data.get("search_queries", [])),
            generation_trace=_coerce_generation_trace(data.get("generation_trace"), data),
        )


@dataclass(frozen=True)
class RealisticPopulationProfile:
    profile_id: str
    display_name: str
    source_path: str
    agents: List[RealisticAgentProfile]
    warnings: List[str]
    cache_path: str
    generated_at: str

    @property
    def size(self) -> int:
        return len(self.agents)

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "source_path": self.source_path,
            "size": self.size,
            "warnings": self.warnings,
            "cache_path": self.cache_path,
            "generated_at": self.generated_at,
            "agents": [agent.to_public_dict() for agent in self.agents],
        }

    def to_cache_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "source_path": self.source_path,
            "warnings": self.warnings,
            "cache_path": self.cache_path,
            "generated_at": self.generated_at,
            "agents": [agent.to_cache_dict() for agent in self.agents],
        }

    @classmethod
    def from_cache_dict(cls, data: Dict[str, Any]) -> "RealisticPopulationProfile":
        return cls(
            profile_id=str(data["profile_id"]),
            display_name=str(data.get("display_name", "")),
            source_path=str(data.get("source_path", "")),
            warnings=list(data.get("warnings", [])),
            cache_path=str(data.get("cache_path", "")),
            generated_at=str(data.get("generated_at", "")),
            agents=[RealisticAgentProfile.from_cache_dict(item) for item in data.get("agents", [])],
        )


def resolve_population_path(path: Optional[str] = None) -> str:
    return path or os.getenv("SHASS_NEWS_INSTITUTE_XLSX") or DEFAULT_SHASS_NEWS_INSTITUTE_PATH


def normalize_profile_id(profile_id: str) -> str:
    value = (profile_id or "").strip()
    if not value:
        raise ValueError("Profile id is required")
    if value.lower() in SHASS_PROFILE_ALIASES:
        return "shass_news_institute"
    normalized = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", value).strip("_")
    if not normalized:
        raise ValueError(f"Invalid profile id: {profile_id}")
    return normalized[:80]


def get_profile_cache_path(profile_id: str) -> Path:
    PROFILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILE_CACHE_DIR / f"{normalize_profile_id(profile_id)}.sanitized.json"


def get_user_profile_dir(profile_id: str) -> Path:
    return USER_PROFILE_LIBRARY_DIR / normalize_profile_id(profile_id)


def get_user_profile_source_dir(profile_id: str) -> Path:
    return get_user_profile_dir(profile_id) / USER_PROFILE_SOURCE_DIRNAME


def get_user_profile_meta_path(profile_id: str) -> Path:
    return get_user_profile_dir(profile_id) / USER_PROFILE_META_FILENAME


def get_available_realistic_profiles() -> List[Dict[str, Any]]:
    """Return built-in and user-built profiles visible to the frontend."""
    profiles: Dict[str, Dict[str, Any]] = {
        "shass_news_institute": {
            "profile_id": "shass_news_institute",
            "display_name": "上海社会科学院新闻研究所现实组织画像",
            "kind": "built_in",
            "size": None,
            "ready": get_profile_cache_path("shass_news_institute").exists(),
            "source_count": None,
            "updated_at": None,
        }
    }

    for meta_path in USER_PROFILE_LIBRARY_DIR.glob(f"*/{USER_PROFILE_META_FILENAME}"):
        try:
            with meta_path.open("r", encoding="utf-8") as handle:
                meta = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        profile_id = normalize_profile_id(str(meta.get("profile_id") or meta_path.parent.name))
        profiles[profile_id] = {
            "profile_id": profile_id,
            "display_name": meta.get("display_name") or profile_id,
            "kind": "user",
            "size": meta.get("size"),
            "ready": get_profile_cache_path(profile_id).exists(),
            "source_count": meta.get("source_count", 0),
            "updated_at": meta.get("updated_at") or meta.get("created_at"),
            "warnings": meta.get("warnings", []),
        }

    for cache_path in PROFILE_CACHE_DIR.glob("*.sanitized.json"):
        profile_id = cache_path.name.removesuffix(".sanitized.json")
        if profile_id in profiles:
            if profiles[profile_id].get("size") is None:
                try:
                    cached = _load_profile_cache(cache_path)
                    profiles[profile_id]["size"] = cached.size
                    profiles[profile_id]["display_name"] = cached.display_name or profiles[profile_id]["display_name"]
                except Exception:
                    pass
            profiles[profile_id]["ready"] = True
            continue
        try:
            cached = _load_profile_cache(cache_path)
        except Exception:
            continue
        profiles[profile_id] = {
            "profile_id": cached.profile_id,
            "display_name": cached.display_name,
            "kind": "cache",
            "size": cached.size,
            "ready": True,
            "source_count": None,
            "updated_at": cached.generated_at,
            "warnings": cached.warnings,
        }

    return sorted(profiles.values(), key=lambda item: (item.get("kind") != "built_in", item["display_name"]))


def load_realistic_population(
    profile_id: str,
    source_path: Optional[str] = None,
    *,
    include_public_enrichment: bool = False,
    refresh_cache: bool = False,
) -> RealisticPopulationProfile:
    normalized = normalize_profile_id(profile_id)
    if normalized in {"", "theory", "theoretical"}:
        raise ValueError("No realistic population profile requested")
    if normalized != "shass_news_institute":
        return load_user_defined_population(
            normalized,
            source_path=source_path,
            refresh_cache=refresh_cache,
        )

    resolved_path = resolve_population_path(source_path)
    if not Path(resolved_path).exists():
        cache_path = get_profile_cache_path("shass_news_institute")
        if cache_path.exists() and not refresh_cache:
            return _load_profile_cache(cache_path)
        profile = _build_synthetic_shass_news_institute_profile()
        cache_path = get_profile_cache_path(profile.profile_id)
        profile = RealisticPopulationProfile(
            profile_id=profile.profile_id,
            display_name=profile.display_name,
            source_path=profile.source_path,
            agents=profile.agents,
            warnings=profile.warnings,
            cache_path=str(cache_path),
            generated_at=profile.generated_at,
        )
        _write_json(cache_path, profile.to_cache_dict())
        return profile

    cache_path = get_profile_cache_path("shass_news_institute")
    if cache_path.exists() and not refresh_cache:
        return _load_profile_cache(cache_path)

    return refresh_realistic_population_cache(
        "shass_news_institute",
        source_path=source_path,
        include_public_enrichment=include_public_enrichment,
    )


def refresh_realistic_population_cache(
    profile_id: str,
    source_path: Optional[str] = None,
    *,
    include_public_enrichment: bool = False,
) -> RealisticPopulationProfile:
    normalized = normalize_profile_id(profile_id)
    if normalized != "shass_news_institute":
        return build_user_defined_population_profile(
            normalized,
            source_path=source_path,
            display_name=None,
            refresh_cache=True,
        )

    profile = _build_shass_news_institute_profile(
        resolve_population_path(source_path),
        include_public_enrichment=include_public_enrichment,
    )
    cache_path = get_profile_cache_path(profile.profile_id)
    profile = RealisticPopulationProfile(
        profile_id=profile.profile_id,
        display_name=profile.display_name,
        source_path=profile.source_path,
        agents=profile.agents,
        warnings=profile.warnings,
        cache_path=str(cache_path),
        generated_at=profile.generated_at,
    )
    _write_json(cache_path, profile.to_cache_dict())
    return profile


def apply_realistic_profile_to_llm_population(population: Any, profile: RealisticPopulationProfile) -> None:
    if len(population.agents) != profile.size:
        raise ValueError(f"Population size {len(population.agents)} does not match profile size {profile.size}")

    for agent, profile_agent in zip(population.agents, profile.agents):
        agent.opinion = profile_agent.opinion
        agent.belief_strength = profile_agent.belief_strength
        agent.influence = profile_agent.influence
        agent.susceptibility = profile_agent.susceptibility
        agent.fear_of_isolation = profile_agent.fear_of_isolation
        agent.conviction = profile_agent.conviction
        agent.persona = dict(profile_agent.persona)
        agent.realistic_profile = profile_agent.to_public_dict()
        if hasattr(agent, "community_id"):
            agent.community_id = profile_agent.community_id
        if hasattr(agent, "is_influencer"):
            agent.is_influencer = profile_agent.is_influencer


def apply_realistic_profile_to_math_population(population: Any, profile: RealisticPopulationProfile) -> None:
    if population.size != profile.size:
        raise ValueError(f"Population size {population.size} does not match profile size {profile.size}")

    population.opinions = np.array([agent.opinion for agent in profile.agents], dtype=float)
    population.belief_strength = np.array([agent.belief_strength for agent in profile.agents], dtype=float)
    population.influence = np.array([agent.influence for agent in profile.agents], dtype=float)
    population.susceptibility = np.array([agent.susceptibility for agent in profile.agents], dtype=float)
    population.fear_of_isolation = np.array([agent.fear_of_isolation for agent in profile.agents], dtype=float)
    population.conviction = np.array([agent.conviction for agent in profile.agents], dtype=float)
    population.exposed_to_negative = population.opinions < -0.1
    population.exposed_to_positive = np.zeros(profile.size, dtype=bool)
    population.realistic_profiles = [agent.to_public_dict() for agent in profile.agents]
    population.personas = [agent.persona.get("type", "现实组织画像") for agent in profile.agents]
    population.community_ids = np.array([agent.community_id for agent in profile.agents], dtype=int)
    population.is_influencer = np.array([agent.is_influencer for agent in profile.agents], dtype=bool)
    if hasattr(population, "invalidate_cache"):
        population.invalidate_cache()


def create_public_evidence_queue(profile: RealisticPopulationProfile) -> Dict[str, Any]:
    EVIDENCE_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    queue_path = EVIDENCE_QUEUE_DIR / f"{profile.profile_id}.candidates.json"
    payload = {
        "profile_id": profile.profile_id,
        "status": "pending_review",
        "generated_at": _utc_now(),
        "policy": "Search results are evidence candidates only. Review manually before attaching to profiles.",
        "agents": [
            {
                "agent_id": agent.agent_id,
                "role_label": agent.role_label,
                "search_queries": agent.search_queries,
                "candidates": agent.public_evidence,
                "approved": [],
                "rejected": [],
            }
            for agent in profile.agents
        ],
    }
    _write_json(queue_path, payload)
    return {"queue_path": str(queue_path), "agents": len(profile.agents)}


def save_user_profile_sources(profile_id: str, files: Iterable[Tuple[str, bytes]]) -> Dict[str, Any]:
    """Store uploaded source files in the user's offline profile library."""
    normalized = normalize_profile_id(profile_id)
    source_dir = get_user_profile_source_dir(normalized)
    source_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for filename, content in files:
        safe_name = _safe_filename(filename)
        if not safe_name:
            continue
        target = source_dir / safe_name
        stem = target.stem
        suffix = target.suffix
        counter = 1
        while target.exists():
            target = source_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        target.write_bytes(content)
        saved.append({"filename": target.name, "size": len(content), "path": str(target)})

    meta = _read_user_profile_meta(normalized)
    meta.update({
        "profile_id": normalized,
        "display_name": meta.get("display_name") or normalized,
        "source_count": len(list(_iter_source_files(source_dir))),
        "updated_at": _utc_now(),
    })
    _write_json(get_user_profile_meta_path(normalized), meta)
    return {"profile_id": normalized, "saved": saved, "source_dir": str(source_dir)}


def update_user_profile_meta(profile_id: str, **updates: Any) -> Dict[str, Any]:
    normalized = normalize_profile_id(profile_id)
    meta = _read_user_profile_meta(normalized)
    meta.update({key: value for key, value in updates.items() if value is not None})
    meta.setdefault("profile_id", normalized)
    meta["updated_at"] = _utc_now()
    _write_json(get_user_profile_meta_path(normalized), meta)
    return meta


def load_user_defined_population(
    profile_id: str,
    source_path: Optional[str] = None,
    *,
    refresh_cache: bool = False,
) -> RealisticPopulationProfile:
    normalized = normalize_profile_id(profile_id)
    cache_path = get_profile_cache_path(normalized)
    if cache_path.exists() and not refresh_cache:
        return _load_profile_cache(cache_path)

    source_root = Path(source_path) if source_path else get_user_profile_source_dir(normalized)
    if not source_root.exists() and cache_path.exists():
        return _load_profile_cache(cache_path)
    if not source_root.exists():
        raise FileNotFoundError(f"User profile source directory not found: {source_root}")

    meta = _read_user_profile_meta(normalized)
    return build_user_defined_population_profile(
        normalized,
        source_path=str(source_root),
        display_name=meta.get("display_name") or normalized,
        refresh_cache=True,
    )


def build_user_defined_population_profile(
    profile_id: str,
    *,
    source_path: Optional[str] = None,
    display_name: Optional[str] = None,
    refresh_cache: bool = True,
) -> RealisticPopulationProfile:
    """Build a reusable offline profile from user-provided local documents."""
    normalized = normalize_profile_id(profile_id)
    source_root = Path(source_path) if source_path else get_user_profile_source_dir(normalized)
    rows, warnings, source_files = _load_user_source_records(source_root)

    if not rows:
        raise ValueError(f"No usable profile records found in {source_root}")

    agents = [
        _build_user_defined_agent_profile(i, row, normalized)
        for i, row in enumerate(rows)
    ]
    generated_at = _utc_now()
    cache_path = get_profile_cache_path(normalized)
    profile = RealisticPopulationProfile(
        profile_id=normalized,
        display_name=display_name or normalized,
        source_path=str(source_root),
        agents=agents,
        warnings=warnings,
        cache_path=str(cache_path),
        generated_at=generated_at,
    )
    if refresh_cache:
        _write_json(cache_path, profile.to_cache_dict())

    meta = _read_user_profile_meta(normalized)
    meta.update({
        "profile_id": normalized,
        "display_name": display_name or meta.get("display_name") or normalized,
        "source_dir": str(source_root),
        "source_count": len(source_files),
        "record_count": len(rows),
        "size": profile.size,
        "cache_path": str(cache_path),
        "warnings": warnings,
        "updated_at": generated_at,
    })
    _write_json(get_user_profile_meta_path(normalized), meta)
    return profile


def _build_shass_news_institute_profile(
    source_path: str,
    *,
    include_public_enrichment: bool,
) -> RealisticPopulationProfile:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas/openpyxl is required to load realistic population profiles") from exc

    workbook = Path(source_path)
    if not workbook.exists():
        raise FileNotFoundError(f"Population workbook not found: {source_path}")

    df = pd.read_excel(workbook, sheet_name="在职").dropna(how="all")
    warnings: List[str] = []

    name_column = "姓名"
    if name_column in df.columns:
        before = len(df)
        df = df[~df[name_column].astype(str).str.strip().isin(EXCLUDED_NAMES)]
        excluded = before - len(df)
        if excluded:
            warnings.append(f"Excluded retired/non-active personnel by name: {excluded}")

    if len(df) != 27:
        warnings.append(f"Sanitized active roster contains {len(df)} rows; expected 27 after exclusions.")

    unsafe_present = sorted(set(df.columns).intersection(SENSITIVE_COLUMNS))
    if unsafe_present:
        warnings.append("Sensitive columns were detected and excluded: " + ", ".join(unsafe_present))

    safe_rows = _drop_sensitive_columns(df.to_dict(orient="records"))
    agents = [
        _build_agent_profile(i, row, include_public_enrichment=include_public_enrichment)
        for i, row in enumerate(safe_rows)
    ]

    return RealisticPopulationProfile(
        profile_id="shass_news_institute",
        display_name="上海社会科学院新闻研究所现实组织画像",
        source_path=str(workbook),
        agents=agents,
        warnings=warnings,
        cache_path="",
        generated_at=_utc_now(),
    )


def _build_synthetic_shass_news_institute_profile() -> RealisticPopulationProfile:
    specialties = [
        "新闻传播理论", "舆情治理", "新媒体研究", "国际传播", "城市传播", "文化传播",
        "新闻史论", "平台治理", "媒介伦理", "公共政策传播", "数字传播", "青年传播",
        "传媒经济", "算法治理", "社会调查", "视觉传播", "危机传播", "基层传播",
        "智库研究", "国际舆论", "网络社会", "融合出版", "数据新闻", "传播效果",
        "公共关系", "社会心理", "政策评估",
    ]
    seniority_cycle = ["资深", "中坚", "青年"]
    agents = []
    warnings = [
        "Using anonymized synthetic roster because no sanitized cache or source workbook is available.",
        "Profiles represent role-based research priors only; they are not claims about any real person's attitude.",
    ]
    for i, specialty in enumerate(specialties):
        rng = np.random.default_rng(20_000 + i)
        seniority_label = seniority_cycle[i % len(seniority_cycle)]
        seniority_score = {"资深": 0.78, "中坚": 0.55, "青年": 0.28}[seniority_label]
        is_admin = i in {0, 5}
        title = {"资深": "研究员", "中坚": "副研究员", "青年": "助理研究员"}[seniority_label]
        role_label = f"{seniority_label}{title} / {specialty}"
        if is_admin:
            role_label += " / 管理职责"
        influence = float(np.clip(0.22 + seniority_score * 0.55 + (0.14 if is_admin else 0.0), 0.1, 1.0))
        susceptibility = float(np.clip(0.58 - seniority_score * 0.25 + rng.normal(0, 0.03), 0.15, 0.75))
        belief_strength = float(np.clip(0.43 + seniority_score * 0.28 + rng.normal(0, 0.04), 0.2, 0.9))
        fear_of_isolation = float(np.clip(0.44 + (0.12 if is_admin else 0.0) + rng.normal(0, 0.05), 0.15, 0.85))
        conviction = float(np.clip(0.45 + seniority_score * 0.25 + rng.normal(0, 0.05), 0.2, 0.9))
        opinion = float(np.clip(rng.normal(0.0, 0.06), -0.18, 0.18))
        generation_trace = _build_generation_trace(
            source="synthetic_roster",
            inputs={
                "seniority_label": seniority_label,
                "title": title,
                "specialty": specialty,
                "admin_role": "管理职责" if is_admin else "",
                "education": "",
                "degree": "",
                "age": None,
                "work_years": None,
                "org_years": None,
            },
            seniority_score=seniority_score,
            metrics={
                "opinion": opinion,
                "belief_strength": belief_strength,
                "influence": influence,
                "susceptibility": susceptibility,
                "fear_of_isolation": fear_of_isolation,
                "conviction": conviction,
            },
            formulas=_synthetic_metric_formulas(),
            community_id=_community_id(specialty, "上海社会科学院新闻研究所"),
            is_influencer=bool(influence >= 0.72 or is_admin),
        )
        persona = {
            "type": "现实组织画像",
            "desc": (
                f"{role_label}。专业背景：{specialty}。"
                "该画像基于匿名组织角色和研究方向生成，只用于模拟近身科研群体的可能判断差异。"
            ),
            "profile_mode": "realistic",
            "role_label": role_label,
            "specialty": specialty,
            "seniority": seniority_label,
            "privacy_note": "synthetic anonymized profile; no personal identifiers used",
        }
        agents.append(RealisticAgentProfile(
            agent_id=i,
            name=f"匿名成员 #{i + 1}",
            role_label=role_label,
            department="上海社会科学院新闻研究所",
            specialty=specialty,
            title=title,
            seniority_label=seniority_label,
            community_id=_community_id(specialty, "上海社会科学院新闻研究所"),
            is_influencer=bool(influence >= 0.72 or is_admin),
            opinion=opinion,
            belief_strength=belief_strength,
            influence=influence,
            susceptibility=susceptibility,
            fear_of_isolation=fear_of_isolation,
            conviction=conviction,
            persona=persona,
            public_evidence=[],
            search_queries=[],
            generation_trace=generation_trace,
        ))
    return RealisticPopulationProfile(
        profile_id="shass_news_institute",
        display_name="上海社会科学院新闻研究所匿名现实组织画像",
        source_path="synthetic://shass_news_institute",
        agents=agents,
        warnings=warnings,
        cache_path="",
        generated_at=_utc_now(),
    )


def _load_profile_cache(path: Path) -> RealisticPopulationProfile:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    profile = RealisticPopulationProfile.from_cache_dict(data)
    if not profile.cache_path:
        profile = RealisticPopulationProfile(
            profile_id=profile.profile_id,
            display_name=profile.display_name,
            source_path=profile.source_path,
            agents=profile.agents,
            warnings=profile.warnings,
            cache_path=str(path),
            generated_at=profile.generated_at,
        )
    return profile


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _read_user_profile_meta(profile_id: str) -> Dict[str, Any]:
    path = get_user_profile_meta_path(profile_id)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def _safe_filename(filename: str) -> str:
    name = Path(filename or "").name.strip()
    if not name:
        return ""
    return re.sub(r"[^0-9A-Za-z_\-\.\u4e00-\u9fff]+", "_", name)[:160]


def _iter_source_files(source_root: Path) -> List[Path]:
    if source_root.is_file():
        return [source_root]
    if not source_root.exists():
        return []
    allowed = TEXT_EXTENSIONS | TABLE_EXTENSIONS
    return [
        path
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix.lower() in allowed
    ]


def _load_user_source_records(source_root: Path) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    warnings: List[str] = []
    rows: List[Dict[str, Any]] = []
    files = _iter_source_files(source_root)
    for path in files:
        suffix = path.suffix.lower()
        try:
            if suffix in {".csv", ".tsv"}:
                records = _load_delimited_records(path, delimiter="\t" if suffix == ".tsv" else ",")
            elif suffix == ".json":
                records = _load_json_records(path)
            elif suffix == ".jsonl":
                records = _load_jsonl_records(path)
            elif suffix in {".xlsx", ".xls"}:
                records = _load_excel_records(path, warnings)
            elif suffix in TEXT_EXTENSIONS:
                records = _load_text_records(path)
            else:
                records = []
            for record in records:
                record.setdefault("source_file", path.name)
            rows.extend(records)
        except Exception as exc:
            warnings.append(f"Skipped {path.name}: {exc}")

    deduped: List[Dict[str, Any]] = []
    seen = set()
    for row in rows:
        normalized = _normalize_user_record(row)
        name = normalized.get("name") or ""
        key = name.strip() or hashlib.sha256(json.dumps(normalized, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)

    if not files:
        warnings.append(f"No supported source files found in {source_root}")
    return deduped, warnings, [str(path) for path in files]


def _load_delimited_records(path: Path, *, delimiter: str) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        return [dict(row) for row in reader]


def _load_json_records(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("agents", "people", "persons", "members", "records", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [data]
    return []


def _load_jsonl_records(path: Path) -> List[Dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            item = json.loads(text)
            if isinstance(item, dict):
                records.append(item)
    return records


def _load_excel_records(path: Path, warnings: List[str]) -> List[Dict[str, Any]]:
    try:
        import pandas as pd
    except ImportError:
        warnings.append(f"Skipped {path.name}: pandas/openpyxl is required for Excel sources")
        return []
    frames = pd.read_excel(path, sheet_name=None)
    records: List[Dict[str, Any]] = []
    for sheet, frame in frames.items():
        if frame.empty:
            continue
        for row in frame.dropna(how="all").to_dict(orient="records"):
            row["_sheet"] = sheet
            records.append(row)
    return records


def _load_text_records(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    frontmatter = _parse_text_frontmatter(text)
    if frontmatter:
        frontmatter.setdefault("source_file", path.name)
        frontmatter.setdefault("notes", _compact_text(text))
        return [frontmatter]

    records = []
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*(?:---+|#{1,3}\s+人物|#{1,3}\s+成员)\s*\n", text) if chunk.strip()]
    for idx, chunk in enumerate(chunks):
        fields = _parse_loose_profile_text(chunk)
        fields.setdefault("name", _infer_name_from_text(chunk, fallback=f"{path.stem}-{idx + 1}"))
        fields.setdefault("source_file", path.name)
        fields.setdefault("notes", _compact_text(chunk))
        records.append(fields)
    return records or [{
        "name": path.stem,
        "source_file": path.name,
        "notes": _compact_text(text),
        "specialty": _infer_specialty_from_text(text),
    }]


def _parse_text_frontmatter(text: str) -> Dict[str, Any]:
    match = re.match(r"^\s*---\s*\n(?P<body>[\s\S]+?)\n---\s*", text)
    if not match:
        return {}
    fields: Dict[str, Any] = {}
    for line in match.group("body").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _parse_loose_profile_text(text: str) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}
    key_aliases = {
        "姓名": "name",
        "名称": "name",
        "名字": "name",
        "单位": "department",
        "部门": "department",
        "机构": "department",
        "职务": "title",
        "职称": "title",
        "岗位": "title",
        "研究方向": "specialty",
        "专业": "specialty",
        "领域": "specialty",
        "学历": "education",
        "学位": "degree",
        "年龄": "age",
        "工龄": "work_years",
        "本单位工龄": "org_years",
    }
    for line in text.splitlines():
        line = line.strip(" -*\t")
        if not line or (":" not in line and "：" not in line):
            continue
        key, value = re.split(r"[:：]", line, maxsplit=1)
        key = key.strip()
        normalized = key_aliases.get(key)
        if normalized:
            fields[normalized] = value.strip()
    return fields


def _normalize_user_record(row: Dict[str, Any]) -> Dict[str, Any]:
    aliases = {
        "name": ("name", "姓名", "名称", "名字", "人员", "作者", "person"),
        "department": ("department", "部门", "单位", "机构", "所在单位", "organization"),
        "specialty": ("specialty", "研究方向", "专业", "领域", "关键词", "tags", "topic"),
        "title": ("title", "职称", "职务", "岗位", "position", "role"),
        "admin_role": ("admin_role", "行政职务", "行政职务名称", "管理职责"),
        "party_role": ("party_role", "党内职务", "党内职务名称"),
        "education": ("education", "学历", "最高学历"),
        "degree": ("degree", "学位", "最高学位"),
        "age": ("age", "年龄"),
        "work_years": ("work_years", "工龄", "工作年限"),
        "org_years": ("org_years", "本单位工龄", "本单位年限"),
        "notes": ("notes", "简介", "摘要", "内容", "文本", "报道", "文章", "bio", "description"),
        "source_file": ("source_file", "_source_file", "文件", "来源文件"),
    }
    normalized: Dict[str, Any] = {}
    for target, keys in aliases.items():
        for key in keys:
            if key in row and _text(row.get(key)):
                normalized[target] = row.get(key)
                break

    if "specialty" not in normalized and normalized.get("notes"):
        normalized["specialty"] = _infer_specialty_from_text(str(normalized["notes"]))
    if "name" not in normalized:
        normalized["name"] = _infer_name_from_record(row)
    for key, value in row.items():
        if key in SENSITIVE_COLUMNS:
            continue
        if key not in normalized and key not in aliases:
            normalized.setdefault("extra", {})[str(key)] = _text(value)
    return normalized


def _infer_name_from_record(row: Dict[str, Any]) -> str:
    ignored_keys = {"source_file", "_source_file", "_sheet"}
    for key, value in row.items():
        if str(key) in ignored_keys or str(key) in SENSITIVE_COLUMNS:
            continue
        text = _text(value)
        if 2 <= len(text) <= 12 and not any(char in text for char in "，。；;:：/\\."):
            return text
    seed = json.dumps(row, ensure_ascii=False, sort_keys=True)
    return "资料成员 " + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:6]


def _infer_name_from_text(text: str, *, fallback: str) -> str:
    fields = _parse_loose_profile_text(text)
    if fields.get("name"):
        return fields["name"]
    first_line = next((line.strip("# -*\t") for line in text.splitlines() if line.strip()), "")
    if 2 <= len(first_line) <= 20:
        return first_line
    return fallback


def _infer_specialty_from_text(text: str) -> str:
    keywords = [
        "舆情", "新闻", "传播", "新媒体", "算法", "平台", "治理", "公共政策", "国际传播",
        "城市传播", "文化传播", "社会调查", "危机传播", "数据新闻", "媒介伦理", "人工智能",
        "经济", "金融", "教育", "法律", "医疗", "基层", "党建", "政策评估",
    ]
    hits = [word for word in keywords if word in text]
    return " / ".join(hits[:3]) if hits else "综合研究"


def _compact_text(text: str, limit: int = 600) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:limit]


def _synthetic_metric_formulas() -> Dict[str, str]:
    return {
        "opinion": "以中性为中心叠加小幅随机扰动，并限制在[-0.18, 0.18]，避免初始立场过于极化",
        "belief_strength": "以资历分为基础，再叠加少量随机扰动，形成初始信念强度",
        "influence": "资历分越高、若有管理职责则再提高，最后限制在0.1到1.0之间",
        "susceptibility": "资历分越高通常越不容易受影响，再叠加少量随机扰动，最后限制在0.15到0.75之间",
        "fear_of_isolation": "有管理职责时会略微提高对孤立的敏感度，再叠加少量随机扰动，最后限制在0.15到0.85之间",
        "conviction": "资历分越高通常越坚定，再叠加少量随机扰动，最后限制在0.2到0.9之间",
    }


def _workbook_metric_formulas() -> Dict[str, str]:
    return {
        "opinion": "以中性为中心叠加小幅随机扰动，并限制在[-0.20, 0.20]，避免把现实人员预设为明确立场",
        "belief_strength": "以资历分为基础，再叠加少量随机扰动，形成初始信念强度",
        "influence": "资历分和行政职务共同影响影响力，最后限制在0.1到1.0之间",
        "susceptibility": "资历分越高通常越不容易受影响，博士学历会再略微下调，最后限制在0.12到0.75之间",
        "fear_of_isolation": "行政或党内职务会略微提高对孤立的敏感度，再叠加少量随机扰动，最后限制在0.15到0.9之间",
        "conviction": "资历分越高通常越坚定，再叠加少量随机扰动，最后限制在0.2到0.9之间",
    }


def _friendly_metric_formulas(source: str, formulas: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    if formulas and not any(
        isinstance(text, str) and any(token in text for token in ("clip", "seniority_score", "N("))
        for text in formulas.values()
    ):
        return formulas
    if source == "workbook":
        return _workbook_metric_formulas()
    return _synthetic_metric_formulas()


def _coerce_generation_trace(value: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(value, dict) and value:
        normalized = dict(value)
        normalized["formulas"] = _friendly_metric_formulas(
            str(normalized.get("source") or data.get("generation_source") or "cached_profile"),
            normalized.get("formulas", {}),
        )
        return normalized
    return _build_cached_generation_trace(data)


def _years_band(value: Optional[float]) -> str:
    if value is None:
        return ""
    if value < 5:
        return "5年以内"
    if value < 10:
        return "5-10年"
    if value < 20:
        return "10-20年"
    if value < 30:
        return "20-30年"
    return "30年以上"


def _age_band(value: Optional[float]) -> str:
    if value is None:
        return ""
    if value < 35:
        return "35岁以下"
    if value < 45:
        return "35-44岁"
    if value < 55:
        return "45-54岁"
    return "55岁以上"


def _build_generation_trace(
    *,
    source: str,
    inputs: Dict[str, Any],
    seniority_score: float,
    metrics: Dict[str, float],
    formulas: Dict[str, str],
    community_id: int,
    is_influencer: bool,
) -> Dict[str, Any]:
    return {
        "source": source,
        "inputs": inputs,
        "derived": {
            "seniority_score": round(float(seniority_score), 3),
            "community_id": int(community_id),
            "is_influencer": bool(is_influencer),
        },
        "metrics": {k: round(float(v), 4) for k, v in metrics.items()},
        "formulas": formulas,
    }


def _build_cached_generation_trace(data: Dict[str, Any]) -> Dict[str, Any]:
    source = str(data.get("generation_source", "cached_profile"))
    return {
        "source": source,
        "inputs": data.get("generation_inputs", {}),
        "derived": data.get("generation_derived", {}),
        "metrics": {
            k: data.get(k)
            for k in ("opinion", "belief_strength", "influence", "susceptibility", "fear_of_isolation", "conviction")
            if data.get(k) is not None
        },
        "formulas": _friendly_metric_formulas(source, data.get("generation_formulas", {})),
    }


def _drop_sensitive_columns(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{key: value for key, value in row.items() if key not in SENSITIVE_COLUMNS} for row in rows]


def _build_user_defined_agent_profile(
    agent_id: int,
    row: Dict[str, Any],
    profile_id: str,
) -> RealisticAgentProfile:
    rng = np.random.default_rng(_stable_seed(profile_id, agent_id, row))
    name = _text(row.get("name")) or f"资料成员 #{agent_id + 1}"
    department = _text(row.get("department")) or "用户自定义群体"
    notes = _text(row.get("notes"))
    specialty = _text(row.get("specialty")) or _infer_specialty_from_text(notes)
    title = _text(row.get("title")) or "资料画像成员"
    admin_role = _text(row.get("admin_role"))
    party_role = _text(row.get("party_role"))
    education = _text(row.get("education"))
    degree = _text(row.get("degree"))
    age = _number(row.get("age"), default=40.0)
    org_years = _number(row.get("org_years"), default=5.0)
    work_years = _number(row.get("work_years"), default=max(1.0, age - 25.0))
    source_file = _text(row.get("source_file"))

    seniority_score = _seniority_score(age, work_years, org_years, title, admin_role)
    seniority_label = _seniority_label(seniority_score)
    role_label = _role_label(seniority_label, title, admin_role, specialty)

    evidence_bonus = min(len(notes) / 2000.0, 0.12)
    influence = float(np.clip(0.23 + seniority_score * 0.48 + (0.14 if admin_role else 0.0) + evidence_bonus, 0.1, 1.0))
    susceptibility = float(np.clip(0.58 - seniority_score * 0.22 - (0.06 if "博士" in degree + education else 0.0) - evidence_bonus * 0.5, 0.12, 0.78))
    belief_strength = float(np.clip(0.42 + seniority_score * 0.28 + evidence_bonus + rng.normal(0, 0.04), 0.2, 0.9))
    fear_of_isolation = float(np.clip(0.44 + (0.13 if admin_role or party_role else 0.0) + rng.normal(0, 0.05), 0.15, 0.9))
    conviction = float(np.clip(0.43 + seniority_score * 0.24 + evidence_bonus + rng.normal(0, 0.05), 0.2, 0.9))
    opinion = float(np.clip(rng.normal(0.0, 0.08), -0.2, 0.2))
    community_id = _community_id(specialty, department)
    is_influencer = bool(influence >= 0.72 or admin_role)
    generation_trace = _build_generation_trace(
        source="user_profile_library",
        inputs={
            "source_file": source_file,
            "age": age,
            "age_band": _age_band(age),
            "work_years": work_years,
            "work_years_band": _years_band(work_years),
            "org_years": org_years,
            "org_years_band": _years_band(org_years),
            "title": title,
            "admin_role": admin_role,
            "party_role": party_role,
            "education": education,
            "degree": degree,
            "specialty": specialty,
            "notes_excerpt": notes[:240],
        },
        seniority_score=seniority_score,
        metrics={
            "opinion": opinion,
            "belief_strength": belief_strength,
            "influence": influence,
            "susceptibility": susceptibility,
            "fear_of_isolation": fear_of_isolation,
            "conviction": conviction,
        },
        formulas=_user_metric_formulas(),
        community_id=community_id,
        is_influencer=is_influencer,
    )
    persona = {
        "type": "用户资料画像",
        "desc": (
            f"{role_label}。资料来源：{source_file or '用户资料库'}。"
            "该画像由用户提供的离线资料抽取和规则化生成，不代表本人真实态度。"
        ),
        "profile_mode": "realistic",
        "role_label": role_label,
        "specialty": specialty,
        "seniority": seniority_label,
        "privacy_note": "user-provided offline profile cache; sensitive columns are excluded when recognized",
    }
    public_evidence = []
    if source_file:
        public_evidence.append({"type": "local_source", "title": source_file, "url": ""})

    return RealisticAgentProfile(
        agent_id=agent_id,
        name=name,
        role_label=role_label,
        department=department,
        specialty=specialty,
        title=title,
        seniority_label=seniority_label,
        community_id=community_id,
        is_influencer=is_influencer,
        opinion=opinion,
        belief_strength=belief_strength,
        influence=influence,
        susceptibility=susceptibility,
        fear_of_isolation=fear_of_isolation,
        conviction=conviction,
        persona=persona,
        public_evidence=public_evidence,
        search_queries=[],
        generation_trace=generation_trace,
    )


def _build_agent_profile(
    agent_id: int,
    row: Dict[str, Any],
    *,
    include_public_enrichment: bool,
) -> RealisticAgentProfile:
    rng = np.random.default_rng(10_000 + agent_id)
    name = _text(row.get("姓名")) or _text(row.get("濮撳悕")) or f"成员 #{agent_id + 1}"
    department = _text(row.get("部门")) or _text(row.get("单位")) or "新闻研究所"
    specialty = _text(row.get("现从事专业")) or "新闻传播研究"
    title = _text(row.get("聘任专技职务")) or _text(row.get("专技职务资格")) or _text(row.get("院岗位类别")) or "科研人员"
    admin_role = _text(row.get("行政职务名称"))
    party_role = _text(row.get("党内职务名称"))
    education = _text(row.get("最高学历"))
    degree = _text(row.get("最高学位"))
    age = _number(row.get("年龄"), default=40.0)
    org_years = _number(row.get("本单位工龄"), default=5.0)
    work_years = _number(row.get("工龄"), default=max(1.0, age - 25.0))

    seniority_score = _seniority_score(age, work_years, org_years, title, admin_role)
    seniority_label = _seniority_label(seniority_score)
    role_label = _role_label(seniority_label, title, admin_role, specialty)

    influence = float(np.clip(0.25 + seniority_score * 0.5 + (0.15 if admin_role else 0.0), 0.1, 1.0))
    susceptibility = float(np.clip(0.55 - seniority_score * 0.25 - (0.08 if "博士" in degree + education else 0.0), 0.12, 0.75))
    belief_strength = float(np.clip(0.45 + seniority_score * 0.3 + rng.normal(0, 0.04), 0.2, 0.9))
    fear_of_isolation = float(np.clip(0.45 + (0.15 if admin_role or party_role else 0.0) + rng.normal(0, 0.06), 0.15, 0.9))
    conviction = float(np.clip(0.45 + seniority_score * 0.25 + rng.normal(0, 0.05), 0.2, 0.9))
    opinion = float(np.clip(rng.normal(0.0, 0.08), -0.2, 0.2))
    community_id = _community_id(specialty, department)
    is_influencer = bool(influence >= 0.72 or admin_role)
    queries = _build_search_queries(row, specialty)
    generation_trace = _build_generation_trace(
        source="workbook",
        inputs={
            "age": age,
            "age_band": _age_band(age),
            "work_years": work_years,
            "work_years_band": _years_band(work_years),
            "org_years": org_years,
            "org_years_band": _years_band(org_years),
            "title": title,
            "admin_role": admin_role,
            "party_role": party_role,
            "education": education,
            "degree": degree,
            "specialty": specialty,
        },
        seniority_score=seniority_score,
        metrics={
            "opinion": opinion,
            "belief_strength": belief_strength,
            "influence": influence,
            "susceptibility": susceptibility,
            "fear_of_isolation": fear_of_isolation,
            "conviction": conviction,
        },
        formulas=_workbook_metric_formulas(),
        community_id=community_id,
        is_influencer=is_influencer,
    )

    public_evidence: List[Dict[str, str]] = []
    if include_public_enrichment:
        public_evidence.append({
            "type": "pending_search",
            "title": "No public evidence attached until manual review",
            "url": "",
        })

    persona = {
        "type": "现实组织画像",
        "desc": (
            f"{role_label}。专业背景：{specialty}；学历/学位：{education}{degree}。"
            "该画像只基于组织角色、公开学术背景和模拟参数，不代表本人真实态度。"
        ),
        "profile_mode": "realistic",
        "role_label": role_label,
        "specialty": specialty,
        "seniority": seniority_label,
        "privacy_note": "anonymized; no ID card, phone, address, health, marriage, or contact fields used",
    }

    return RealisticAgentProfile(
        agent_id=agent_id,
        name=name,
        role_label=role_label,
        department=department,
        specialty=specialty,
        title=title,
        seniority_label=seniority_label,
        community_id=community_id,
        is_influencer=is_influencer,
        opinion=opinion,
        belief_strength=belief_strength,
        influence=influence,
        susceptibility=susceptibility,
        fear_of_isolation=fear_of_isolation,
        conviction=conviction,
            persona=persona,
            public_evidence=public_evidence,
            search_queries=queries,
            generation_trace=generation_trace,
        )


def _user_metric_formulas() -> Dict[str, str]:
    return {
        "opinion": "以中性为中心叠加小幅稳定扰动，并限制在[-0.20, 0.20]，避免根据资料预设明确立场",
        "belief_strength": "以资历分和资料丰富度为基础，再叠加小幅稳定扰动，形成初始信念强度",
        "influence": "资历分、管理职责和资料丰富度共同影响影响力，最后限制在0.1到1.0之间",
        "susceptibility": "资历分越高通常越不容易受影响；高学历和资料丰富度会略微降低易感性，最后限制在0.12到0.78之间",
        "fear_of_isolation": "行政或党内职务会略微提高对孤立的敏感度，再叠加小幅稳定扰动，最后限制在0.15到0.9之间",
        "conviction": "资历分和资料丰富度越高通常越坚定，再叠加小幅稳定扰动，最后限制在0.2到0.9之间",
    }


def _stable_seed(profile_id: str, agent_id: int, row: Dict[str, Any]) -> int:
    payload = json.dumps({"profile_id": profile_id, "agent_id": agent_id, "row": row}, ensure_ascii=False, sort_keys=True)
    return int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8], 16)


def _build_search_queries(row: Dict[str, Any], specialty: str) -> List[str]:
    name = _text(row.get("姓名"))
    if not name:
        return []
    return [
        f'"{name}" "上海社会科学院" 新闻 论文',
        f'"{name}" "Shanghai Academy of Social Sciences" journalism',
        f'"{name}" "{specialty}" 论文',
    ]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and np.isnan(value):
        return ""
    return str(value).strip()


def _number(value: Any, *, default: float) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, float) and np.isnan(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _seniority_score(age: float, work_years: float, org_years: float, title: str, admin_role: str) -> float:
    score = 0.0
    score += min(max((age - 30.0) / 30.0, 0.0), 1.0) * 0.25
    score += min(max(work_years / 35.0, 0.0), 1.0) * 0.25
    score += min(max(org_years / 25.0, 0.0), 1.0) * 0.15
    if any(token in title for token in ("正高", "研究员", "教授")):
        score += 0.25
    elif any(token in title for token in ("副高", "副研究员", "副教授")):
        score += 0.18
    elif any(token in title for token in ("中级", "助理研究员")):
        score += 0.1
    if admin_role:
        score += 0.12
    return float(np.clip(score, 0.0, 1.0))


def _seniority_label(score: float) -> str:
    if score >= 0.72:
        return "资深"
    if score >= 0.45:
        return "中坚"
    return "青年"


def _role_label(seniority_label: str, title: str, admin_role: str, specialty: str) -> str:
    base = f"{seniority_label}科研人员"
    if any(token in title for token in ("研究员", "教授", "正高")):
        base = f"{seniority_label}研究员"
    elif any(token in title for token in ("副研究员", "副教授", "副高")):
        base = f"{seniority_label}副研究员"
    elif "助理" in title:
        base = f"{seniority_label}助理研究员"
    if admin_role:
        base += " / 管理职责"
    if specialty:
        base += f" / {specialty}"
    return base


def _community_id(specialty: str, department: str) -> int:
    key = specialty or department
    if any(token in key for token in ("舆情", "新媒体", "互联网", "网络")):
        return 0
    if any(token in key for token in ("新闻", "传播", "传媒")):
        return 1
    if any(token in key for token in ("国际", "外宣", "全球")):
        return 2
    if any(token in key for token in ("文化", "城市", "社会")):
        return 3
    return 4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

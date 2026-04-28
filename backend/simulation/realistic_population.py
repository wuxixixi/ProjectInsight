"""Anonymized real-world organization population profiles.

The loader reads a local personnel workbook only when the sanitized cache is
missing or explicitly refreshed. Runtime simulations use the JSON cache.
Sensitive fields are never written to the cache or prompt payloads.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np


DEFAULT_SHASS_NEWS_INSTITUTE_PATH = r"E:\wuxi_xws\名单\251231 新闻所在职人员名单.xlsx"
PROFILE_CACHE_DIR = Path(os.getenv("REALISTIC_PROFILE_CACHE_DIR", "data/realistic_profiles"))
EVIDENCE_QUEUE_DIR = Path(os.getenv("PUBLIC_EVIDENCE_QUEUE_DIR", "data/public_evidence_queue"))

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


@dataclass(frozen=True)
class RealisticAgentProfile:
    agent_id: int
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

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role_label": self.role_label,
            "department": self.department,
            "specialty": self.specialty,
            "title": self.title,
            "seniority_label": self.seniority_label,
            "community_id": self.community_id,
            "is_influencer": self.is_influencer,
            "public_evidence": self.public_evidence,
            "search_queries": self.search_queries,
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


def get_profile_cache_path(profile_id: str) -> Path:
    PROFILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILE_CACHE_DIR / f"{profile_id}.sanitized.json"


def load_realistic_population(
    profile_id: str,
    source_path: Optional[str] = None,
    *,
    include_public_enrichment: bool = False,
    refresh_cache: bool = False,
) -> RealisticPopulationProfile:
    normalized = (profile_id or "").strip().lower()
    if normalized in {"", "theory", "theoretical"}:
        raise ValueError("No realistic population profile requested")
    if normalized not in SHASS_PROFILE_ALIASES:
        raise ValueError(f"Unsupported population profile: {profile_id}")

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
    normalized = (profile_id or "").strip().lower()
    if normalized not in SHASS_PROFILE_ALIASES:
        raise ValueError(f"Unsupported population profile: {profile_id}")

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


def _drop_sensitive_columns(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{key: value for key, value in row.items() if key not in SENSITIVE_COLUMNS} for row in rows]


def _build_agent_profile(
    agent_id: int,
    row: Dict[str, Any],
    *,
    include_public_enrichment: bool,
) -> RealisticAgentProfile:
    rng = np.random.default_rng(10_000 + agent_id)
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
    )


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

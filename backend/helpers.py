"""
辅助函数与 Pydantic 模型定义
"""
import os
from typing import Optional, Dict, List

from pydantic import BaseModel

from .llm.client import LLMConfig
from . import state


# ==================== 请求模型 ====================

class StartRequest(BaseModel):
    """推演启动请求参数"""
    # 推演模式
    mode: str = "sandbox"  # sandbox(沙盘) / news(新闻)

    # 基础参数
    cocoon_strength: float = 0.5
    debunk_delay: int = 10                              # 兼容旧参数名
    response_delay: Optional[int] = None                # 权威回应延迟（新参数名，优先于 debunk_delay）
    population_size: int = 200
    initial_rumor_spread: float = 0.3                   # 兼容旧参数名
    initial_negative_spread: Optional[float] = None    # 初始负面信念传播率（新参数名，优先）
    network_type: str = "small_world"
    use_llm: bool = True

    # LLM并发参数（留空则自动计算）
    max_concurrent: Optional[int] = None  # None 表示根据 population_size 自动计算
    connection_pool_size: int = 600
    timeout: int = 60
    max_retries: int = 5

    # 双层网络参数
    use_dual_network: bool = True     # 是否使用双层网络模式
    num_communities: int = 8          # 私域社群数量
    public_m: int = 3                 # 公域网络 BA 模型参数

    # 增强版数学模型参数
    debunk_credibility: float = 0.7       # 兼容旧参数名
    response_credibility: Optional[float] = None  # 权威回应来源可信度（新参数名，优先） [0, 1]
    authority_factor: float = 0.5        # 权威影响力系数 [0, 1]
    backfire_strength: float = 0.3       # 逆火效应强度 [0, 1]
    silence_threshold: float = 0.3       # 沉默阈值 [0, 1]
    polarization_factor: float = 0.3     # 群体极化系数 [0, 1]
    echo_chamber_factor: float = 0.2     # 回音室效应系数 [0, 1]

    # Phase 3: 新闻模式专用参数
    init_distribution: Optional[Dict[str, float]] = None
    """真实分布锚定，格式:
    {
        "believe_rumor": 0.25,  # 初始误信比例
        "believe_truth": 0.15,  # 初始正确认知比例
        "neutral": 0.60         # 中立比例
    }
    """
    time_acceleration: float = 1.0  # 时间加速比


class ParseRequest(BaseModel):
    """知识图谱解析请求参数"""
    content: str  # 新闻文本内容


class AirdropRequest(BaseModel):
    """事件注入请求参数"""
    content: str  # 事件文本内容
    source: str = "public"  # 来源 (public/private)
    skip_parse: bool = False  # 跳过知识图谱解析（快速注入模式）
    credibility: str = "不确定"  # 新闻可信度 (高可信/低可信/不确定)


# ==================== 辅助函数 ====================

def _is_local_llm_runtime(llm_config: LLMConfig) -> bool:
    """根据 LLM 配置判断是否本地推理环境（如 Ollama）。"""
    base_url = (llm_config.base_url or "").lower()
    local_hosts = ("localhost", "127.0.0.1", "::1")
    return any(host in base_url for host in local_hosts) or "11434" in base_url


def _infer_ollama_model_size_b(model_name: str) -> int:
    """
    从模型名推断参数规模（如 gemma4:31b -> 31）。
    解析失败返回 0。
    """
    if not model_name:
        return 0
    model_name = model_name.lower()
    if "b" not in model_name or ":" not in model_name:
        return 0
    try:
        suffix = model_name.split(":")[-1]
        if suffix.endswith("b"):
            return int(suffix[:-1])
    except ValueError:
        return 0
    return 0


def calculate_max_concurrent(population_size: int) -> int:
    """
    根据 Agent 数量自动计算合理的并发数

    默认 auto 策略会按运行环境自适应：
    - local: 本地推理（如 Ollama），更保守，避免超时重试风暴
    - remote: 远程推理服务，允许更高并发

    可通过环境变量覆盖：
    - LLM_CONCURRENCY_PROFILE=local|remote|auto
    """
    profile = os.getenv("LLM_CONCURRENCY_PROFILE", "auto").strip().lower()
    llm_config = LLMConfig()
    is_local = _is_local_llm_runtime(llm_config)
    model_size_b = _infer_ollama_model_size_b(llm_config.model)

    if profile == "local" or (profile == "auto" and is_local):
        # 本地推理：默认保守；超大模型（>=20B）更保守
        max_cap = 16 if model_size_b >= 20 else 20
        return max(4, min(int(population_size * 0.2), max_cap))

    # remote / auto(remote)
    return max(10, min(int(population_size * 0.5), 100))


def _build_perceived_climate_summary(agent_id: int) -> dict:
    """
    统一构建 Agent 邻居舆论气候（兼容单层/双层网络）。
    返回前端透视面板所需的扁平字段。
    """
    engine = state.engine

    default_climate = {
        "total": 0,
        "pro_rumor_ratio": 0.0,
        "pro_truth_ratio": 0.0,
        "neutral_ratio": 1.0,
        "silent_ratio": 0.0,
        "avg_opinion": 0.0
    }

    if engine is None or not getattr(engine, "use_llm", False) or not getattr(engine, "llm_population", None):
        return default_climate

    population = engine.llm_population
    if agent_id < 0 or agent_id >= len(population.agents):
        return default_climate

    try:
        # 双层网络模式：合并公域+私域邻居去重后统计
        if hasattr(population, "get_public_neighbor_agents") and hasattr(population, "get_private_neighbor_agents"):
            public_neighbors = population.get_public_neighbor_agents(agent_id)
            private_neighbors = population.get_private_neighbor_agents(agent_id)
            neighbor_map = {n.id: n for n in (public_neighbors + private_neighbors)}
            neighbors = list(neighbor_map.values())
        # 单层网络模式
        elif hasattr(population, "get_neighbor_agents"):
            neighbors = population.get_neighbor_agents(agent_id)
        else:
            neighbors = []
    except Exception:
        neighbors = []

    if not neighbors:
        return default_climate

    total = len(neighbors)
    pro_rumor = sum(1 for n in neighbors if n.opinion < -0.2)
    pro_truth = sum(1 for n in neighbors if n.opinion > 0.2)
    neutral = total - pro_rumor - pro_truth
    silent = sum(1 for n in neighbors if getattr(n, "is_silent", False))
    avg_opinion = sum(float(n.opinion) for n in neighbors) / total

    return {
        "total": total,
        "pro_rumor_ratio": pro_rumor / total,
        "pro_truth_ratio": pro_truth / total,
        "neutral_ratio": neutral / total,
        "silent_ratio": silent / total,
        "avg_opinion": avg_opinion
    }


def _normalize_snapshot_climate(snapshot: dict) -> dict:
    """
    规范化快照中的 perceived_climate，保证前端字段可用。
    """
    agent_id = int(snapshot.get("agent_id", -1))
    climate = snapshot.get("perceived_climate")

    # 1) 已是前端需要的扁平结构，补默认值后直接返回
    if isinstance(climate, dict) and "total" in climate:
        climate.setdefault("pro_rumor_ratio", 0.0)
        climate.setdefault("pro_truth_ratio", 0.0)
        climate.setdefault("neutral_ratio", 1.0)
        climate.setdefault("silent_ratio", 0.0)
        climate.setdefault("avg_opinion", 0.0)
        snapshot["perceived_climate"] = climate
        return snapshot

    # 2) 双层结构（public/private）或缺失时，统一重算扁平结构
    snapshot["perceived_climate"] = _build_perceived_climate_summary(agent_id)
    return snapshot


def _get_v3_agent_fields(agent_id: int) -> dict:
    """
    获取指定 Agent 的 v3.0 字段（rumor_trust, truth_trust, dominant_need, predicted_behavior 等）
    """
    engine = state.engine
    if engine is None:
        return {}

    v3_fields = {}

    # 优先从 v3 获取（最准确）
    if hasattr(engine, 'v3') and engine.v3:
        agent_state = engine.v3.get_agent_v3_fields(agent_id)
        if agent_state:
            v3_fields.update(agent_state)

    # 从 engine 的 current_state 中获取 agent 列表（补充）
    if hasattr(engine, 'current_state') and engine.current_state:
        agents = engine.current_state.agents if hasattr(engine.current_state, 'agents') else []
        for agent in agents:
            agent_dict = agent.model_dump() if hasattr(agent, 'model_dump') else agent
            if agent_dict.get('id') == agent_id:
                # 只在 v3_fields 没有值时才覆盖
                if not v3_fields.get('rumor_trust') and agent_dict.get('rumor_trust'):
                    v3_fields['rumor_trust'] = agent_dict.get('rumor_trust', 0.0)
                if not v3_fields.get('truth_trust') and agent_dict.get('truth_trust'):
                    v3_fields['truth_trust'] = agent_dict.get('truth_trust', 0.0)
                if not v3_fields.get('dominant_need') and agent_dict.get('dominant_need'):
                    v3_fields['dominant_need'] = agent_dict.get('dominant_need', '')
                if not v3_fields.get('predicted_behavior') and agent_dict.get('predicted_behavior'):
                    v3_fields['predicted_behavior'] = agent_dict.get('predicted_behavior', '')
                if 'behavior_confidence' not in v3_fields:
                    v3_fields['behavior_confidence'] = agent_dict.get('behavior_confidence', 0.0)
                if 'cognitive_closed_need' not in v3_fields:
                    v3_fields['cognitive_closed_need'] = agent_dict.get('cognitive_closed_need', 0.5)
                break

    return v3_fields


def _state_to_dict(state_obj) -> dict:
    """将 SimulationState 转换为字典，并附加引擎级别数据（如 event_pool）"""
    d = state_obj.to_dict()
    d["event_pool"] = list(getattr(state.engine, "event_pool", [])) if state.engine else []
    return d

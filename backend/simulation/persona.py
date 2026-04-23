"""
共享人设模块

提供 Agent 人设模板和生成函数，供 llm_agents.py 和 llm_agents_dual.py 共用。
"""
import numpy as np
from typing import Dict, Any


# 人设模板
PERSONA_TEMPLATES = [
    {"type": "低媒介素养", "desc": "对网络信息缺乏辨别能力，容易被情绪化内容影响"},
    {"type": "理性分析型", "desc": "习惯多方求证，对信息持审慎态度"},
    {"type": "易恐慌型", "desc": "对负面信息敏感，容易产生焦虑情绪"},
    {"type": "从众型", "desc": "容易受周围人影响，倾向于跟随主流观点"},
    {"type": "怀疑论者", "desc": "对官方信息持怀疑态度，不容易被说服"},
    {"type": "意见领袖", "desc": "有较强影响力，观点容易影响他人"},
    {"type": "信息茧房受害者", "desc": "长期接触单一观点信息，固守既有立场"},
]


def get_persona(agent_id: int, opinion: float, susceptibility: float) -> Dict:
    """
    根据属性生成人设

    Args:
        agent_id: Agent 唯一标识（用于随机种子）
        opinion: 当前观点值 [-1, 1]
        susceptibility: 易感性 [0, 1]

    Returns:
        人设字典 {type, desc}
    """
    rng = np.random.RandomState(agent_id)
    if susceptibility > 0.5:
        pool = [PERSONA_TEMPLATES[0], PERSONA_TEMPLATES[2], PERSONA_TEMPLATES[3]]
    elif opinion < -0.3:
        pool = [PERSONA_TEMPLATES[4], PERSONA_TEMPLATES[6]]
    else:
        pool = PERSONA_TEMPLATES
    return rng.choice(pool)


# 全局决策快照存储 (agent_id -> 上下文快照)
AGENT_DECISION_SNAPSHOTS: Dict[int, Dict[str, Any]] = {}


def get_agent_snapshot(agent_id: int) -> Dict[str, Any]:
    """获取全局决策快照"""
    return AGENT_DECISION_SNAPSHOTS.get(agent_id)


def set_agent_snapshot(agent_id: int, snapshot: Dict[str, Any]):
    """设置全局决策快照"""
    AGENT_DECISION_SNAPSHOTS[agent_id] = snapshot


def clear_agent_snapshots():
    """清空所有快照"""
    AGENT_DECISION_SNAPSHOTS.clear()

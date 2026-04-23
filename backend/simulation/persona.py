"""
共享人设模块

提供 Agent 人设模板和生成函数，供 llm_agents.py 和 llm_agents_dual.py 共用。
"""
import numpy as np
import threading
from typing import Dict, Any, Optional


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

# 人设-属性相关性权重矩阵
# 行：人设索引，列：[high_susceptibility, negative_opinion, high_influence]
PERSONA_ATTRIBUTE_WEIGHTS = [
    [0.8, 0.3, 0.2],  # 低媒介素养：高易感性关联
    [0.2, 0.5, 0.5],  # 理性分析型：中等关联
    [0.7, 0.6, 0.2],  # 易恐慌型：高易感性+负面观点关联
    [0.6, 0.4, 0.2],  # 从众型：高易感性关联
    [0.3, 0.7, 0.3],  # 怀疑论者：负面观点强关联
    [0.3, 0.4, 0.9],  # 意见领袖：高影响力关联
    [0.5, 0.6, 0.4],  # 信息茧房受害者：负面观点关联
]


def get_persona(
    agent_id: int,
    opinion: float,
    susceptibility: float,
    influence: Optional[float] = None
) -> Dict:
    """
    根据属性生成人设（基于权重的方法）

    使用人设-属性相关性矩阵计算每个人设的适配权重，
    然后进行加权随机选择。

    Args:
        agent_id: Agent 唯一标识（用于随机种子）
        opinion: 当前观点值 [-1, 1]
        susceptibility: 易感性 [0, 1]
        influence: 影响力 [0, 1]（可选）

    Returns:
        人设字典 {type, desc}
    """
    rng = np.random.RandomState(agent_id)
    influence = influence or 0.5

    # 计算属性向量
    attributes = np.array([
        susceptibility,
        max(0, -opinion),  # 负面观点强度
        influence
    ])

    # 计算每个人设的适配得分
    weights = np.array([
        np.dot(w, attributes) for w in PERSONA_ATTRIBUTE_WEIGHTS
    ])

    # Softmax 归一化为概率分布
    exp_weights = np.exp(weights - np.max(weights))
    probs = exp_weights / exp_weights.sum()

    # 加权随机选择
    chosen_idx = rng.choice(len(PERSONA_TEMPLATES), p=probs)
    return PERSONA_TEMPLATES[chosen_idx]


class SnapshotManager:
    """
    线程安全的决策快照管理器

    替代全局可变字典，提供线程安全的快照存储。
    每个引擎实例可持有独立的 SnapshotManager。
    支持字典式访问以保持向后兼容。
    """

    def __init__(self):
        self._snapshots: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def get(self, agent_id: int) -> Optional[Dict[str, Any]]:
        """获取指定 Agent 的快照"""
        with self._lock:
            return self._snapshots.get(agent_id)

    def set(self, agent_id: int, snapshot: Dict[str, Any]):
        """设置指定 Agent 的快照"""
        with self._lock:
            self._snapshots[agent_id] = snapshot

    def clear(self):
        """清空所有快照"""
        with self._lock:
            self._snapshots.clear()

    def get_all(self) -> Dict[int, Dict[str, Any]]:
        """获取所有快照的副本"""
        with self._lock:
            return dict(self._snapshots)

    # 字典式访问支持（向后兼容）
    def __getitem__(self, agent_id: int) -> Optional[Dict[str, Any]]:
        return self.get(agent_id)

    def __setitem__(self, agent_id: int, snapshot: Dict[str, Any]):
        self.set(agent_id, snapshot)

    def __contains__(self, agent_id: int) -> bool:
        with self._lock:
            return agent_id in self._snapshots


# 全局默认实例（向后兼容）
_global_snapshot_manager = SnapshotManager()


def get_agent_snapshot(agent_id: int) -> Optional[Dict[str, Any]]:
    """获取全局决策快照（向后兼容函数）"""
    return _global_snapshot_manager.get(agent_id)


def set_agent_snapshot(agent_id: int, snapshot: Dict[str, Any]):
    """设置全局决策快照（向后兼容函数）"""
    _global_snapshot_manager.set(agent_id, snapshot)


def clear_agent_snapshots():
    """清空所有快照（向后兼容函数）"""
    _global_snapshot_manager.clear()


# 类型别名，供需要独立实例的模块使用
AGENT_DECISION_SNAPSHOTS = _global_snapshot_manager

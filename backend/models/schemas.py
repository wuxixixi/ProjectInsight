"""
数据模型定义
"""
from pydantic import BaseModel
from typing import List, Dict, Optional
import numpy as np


class Agent(BaseModel):
    """个体智能体"""
    id: int
    opinion: float           # 观点值 [-1, 1], -1=完全相信谣言, 1=完全相信真相
    belief_strength: float   # 信念强度 [0, 1]
    influence: float         # 影响力
    susceptibility: float    # 易感性
    exposed_to_rumor: bool = False
    exposed_to_truth: bool = False


class SimulationParams(BaseModel):
    """模拟参数"""
    cocoon_strength: float = 0.5
    debunk_delay: int = 10
    population_size: int = 200
    initial_rumor_spread: float = 0.3
    network_type: str = "small_world"


class SimulationState(BaseModel):
    """模拟状态快照"""
    step: int
    agents: List[Dict]
    edges: List[tuple]
    opinion_distribution: Dict[str, List]  # 直方图数据
    rumor_spread_rate: float
    truth_acceptance_rate: float
    avg_opinion: float
    polarization_index: float  # 极化指数

    def to_dict(self) -> dict:
        """转换为可序列化的字典"""
        return {
            "step": self.step,
            "agents": self.agents,
            "edges": self.edges,
            "opinion_distribution": self.opinion_distribution,
            "rumor_spread_rate": self.rumor_spread_rate,
            "truth_acceptance_rate": self.truth_acceptance_rate,
            "avg_opinion": self.avg_opinion,
            "polarization_index": self.polarization_index
        }

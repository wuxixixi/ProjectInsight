"""
数据模型定义 - 双层模态信息场版本
"""
from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum
import numpy as np


class SimulationMode(Enum):
    """推演模式枚举"""
    SANDBOX = "sandbox"  # 沙盘推演模式（参数驱动）
    NEWS = "news"        # 新闻推演模式（真实分布锚定）


class Agent(BaseModel):
    """个体智能体"""
    id: int
    opinion: float           # 观点值 [-1, 1], -1=完全相信谣言, 1=完全相信真相
    belief_strength: float   # 信念强度 [0, 1]
    influence: float         # 影响力
    susceptibility: float    # 易感性
    exposed_to_rumor: bool = False
    exposed_to_truth: bool = False
    # 沉默的螺旋
    fear_of_isolation: float = 0.5
    conviction: float = 0.5
    is_silent: bool = False
    perceived_climate: Optional[Dict] = None
    # 双层网络属性
    is_influencer: bool = False    # 是否为大V（公域超级节点）
    community_id: int = 0          # 所属私域社群ID
    publish_channel: str = "none"  # 发布渠道


class SimulationParams(BaseModel):
    """模拟参数"""
    # 推演模式
    mode: str = "sandbox"  # sandbox(沙盘) / news(新闻)
    
    cocoon_strength: float = 0.5
    debunk_delay: int = 10
    population_size: int = 200
    initial_rumor_spread: float = 0.3
    network_type: str = "small_world"
    # 双层网络参数
    use_dual_network: bool = False     # 是否使用双层网络
    num_communities: int = 8           # 私域社群数量
    public_m: int = 3                  # 公域网络 BA 模型参数
    # 增强版数学模型参数
    debunk_credibility: float = 0.7      # 辟谣来源可信度 [0, 1]
    authority_factor: float = 0.5        # 权威影响力系数 [0, 1]
    backfire_strength: float = 0.3       # 逆火效应强度 [0, 1]
    silence_threshold: float = 0.3       # 沉默阈值 [0, 1]
    polarization_factor: float = 0.3     # 群体极化系数 [0, 1]
    echo_chamber_factor: float = 0.2     # 回音室效应系数 [0, 1]
    
    # 新闻模式专用参数 - 真实分布锚定
    init_distribution: Optional[Dict[str, float]] = None
    """真实分布锚定，格式:
    {
        "believe_rumor": 0.25,  # 初始相信谣言比例
        "believe_truth": 0.15,  # 初始相信真相比例
        "neutral": 0.60         # 中立比例
    }
    """
    time_acceleration: float = 1.0  # 时间加速比（新闻模式）


class SimulationState(BaseModel):
    """模拟状态快照 - 双层网络版本"""
    step: int
    agents: List[Dict]
    # 双层网络边（公域和私域分开）
    public_edges: List[tuple] = []     # 公域网络边
    private_edges: List[tuple] = []    # 私域网络边
    edges: List[tuple] = []            # 兼容旧版（公域边）
    opinion_distribution: Dict[str, List]
    # 整体统计
    rumor_spread_rate: float
    truth_acceptance_rate: float
    avg_opinion: float
    polarization_index: float
    silence_rate: float = 0.0
    # 双层网络统计
    public_rumor_rate: float = 0.0     # 公域谣言率
    public_truth_rate: float = 0.0     # 公域真相率
    private_rumor_rate: float = 0.0    # 私域谣言率
    private_truth_rate: float = 0.0    # 私域真相率
    num_communities: int = 0           # 社群数量
    num_influencers: int = 0           # 大V数量
    # Phase 3: 新闻模式专用
    mode: str = "sandbox"              # 运行模式
    entity_impact_summary: Optional[Dict[str, float]] = None  # 实体影响摘要

    def to_dict(self) -> dict:
        """转换为可序列化的字典"""
        return {
            "step": self.step,
            "agents": self.agents,
            "public_edges": self.public_edges,
            "private_edges": self.private_edges,
            "edges": self.edges,
            "opinion_distribution": self.opinion_distribution,
            "rumor_spread_rate": self.rumor_spread_rate,
            "truth_acceptance_rate": self.truth_acceptance_rate,
            "avg_opinion": self.avg_opinion,
            "polarization_index": self.polarization_index,
            "silence_rate": self.silence_rate,
            "public_rumor_rate": self.public_rumor_rate,
            "public_truth_rate": self.public_truth_rate,
            "private_rumor_rate": self.private_rumor_rate,
            "private_truth_rate": self.private_truth_rate,
            "num_communities": self.num_communities,
            "num_influencers": self.num_influencers,
            "mode": self.mode,
            "entity_impact_summary": self.entity_impact_summary
        }


class DualNetworkInfo(BaseModel):
    """双层网络元信息"""
    num_nodes: int
    num_communities: int
    num_influencers: int
    public_edges: int
    private_edges: int
    influencer_ids: List[int]

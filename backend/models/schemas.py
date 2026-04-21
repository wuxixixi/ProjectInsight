"""
数据模型定义 - 双层模态信息场版本

语义重构：将特定的"谣言/辟谣"语义抽象为通用的"负面信念/权威回应"语义
- rumor → negative (负面信念)
- truth → positive (正面信念)
- debunk → authority_response (权威回应)

向后兼容：旧字段名通过 model_validator 自动映射到新字段名
"""
from pydantic import BaseModel, model_validator
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
    opinion: float           # 观点值 [-1, 1], -1=完全误信, 1=完全正确认知
    belief_strength: float   # 信念强度 [0, 1]
    influence: float         # 影响力
    susceptibility: float    # 易感性
    # 接触状态（新字段名优先，旧字段名兼容）
    exposed_to_negative: bool = False   # 是否接触过负面信息
    exposed_to_positive: bool = False   # 是否接触过正面信息
    # 沉默的螺旋
    fear_of_isolation: float = 0.5
    conviction: float = 0.5
    is_silent: bool = False
    perceived_climate: Optional[Dict] = None
    # 双层网络属性
    is_influencer: bool = False    # 是否为大V（公域超级节点）
    community_id: int = 0          # 所属私域社群ID
    publish_channel: str = "none"  # 发布渠道

    @model_validator(mode='before')
    @classmethod
    def _map_legacy_fields(cls, data):
        """向后兼容：旧字段名映射到新字段名"""
        if isinstance(data, dict):
            # exposed_to_rumor → exposed_to_negative
            if 'exposed_to_rumor' in data and 'exposed_to_negative' not in data:
                data['exposed_to_negative'] = data.pop('exposed_to_rumor')
            elif 'exposed_to_rumor' in data and 'exposed_to_negative' in data:
                data.pop('exposed_to_rumor', None)
            # exposed_to_truth → exposed_to_positive
            if 'exposed_to_truth' in data and 'exposed_to_positive' not in data:
                data['exposed_to_positive'] = data.pop('exposed_to_truth')
            elif 'exposed_to_truth' in data and 'exposed_to_positive' in data:
                data.pop('exposed_to_truth', None)
        return data

    @property
    def exposed_to_rumor(self) -> bool:
        """向后兼容属性"""
        return self.exposed_to_negative

    @exposed_to_rumor.setter
    def exposed_to_rumor(self, value: bool):
        self.exposed_to_negative = value

    @property
    def exposed_to_truth(self) -> bool:
        """向后兼容属性"""
        return self.exposed_to_positive

    @exposed_to_truth.setter
    def exposed_to_truth(self, value: bool):
        self.exposed_to_positive = value


class SimulationParams(BaseModel):
    """模拟参数"""
    # 推演模式
    mode: str = "sandbox"  # sandbox(沙盘) / news(新闻)

    cocoon_strength: float = 0.5
    response_delay: int = 10              # 新：权威回应延迟步数
    debunk_delay: Optional[int] = None    # 旧：辟谣延迟步数（兼容）
    population_size: int = 200
    initial_negative_spread: float = 0.3  # 新：初始负面信念传播率
    initial_rumor_spread: Optional[float] = None  # 旧：兼容
    network_type: str = "small_world"
    # 双层网络参数
    use_dual_network: bool = False     # 是否使用双层网络
    num_communities: int = 8           # 私域社群数量
    public_m: int = 3                  # 公域网络 BA 模型参数
    # 增强版数学模型参数
    response_credibility: float = 0.7       # 新：权威回应可信度 [0, 1]
    debunk_credibility: Optional[float] = None  # 旧：兼容
    authority_factor: float = 0.5        # 权威影响力系数 [0, 1]
    backfire_strength: float = 0.3       # 逆火效应强度 [0, 1]
    silence_threshold: float = 0.3       # 沉默阈值 [0, 1]
    polarization_factor: float = 0.3     # 群体极化系数 [0, 1]
    echo_chamber_factor: float = 0.2     # 回音室效应系数 [0, 1]

    # 新闻模式专用参数 - 真实分布锚定
    init_distribution: Optional[Dict[str, float]] = None
    """真实分布锚定，格式:
    {
        "believe_negative": 0.25,  # 初始误信比例（兼容旧名 believe_rumor）
        "believe_positive": 0.15,  # 初始正确认知比例（兼容旧名 believe_truth）
        "neutral": 0.60            # 中立比例
    }
    """
    time_acceleration: float = 1.0  # 时间加速比（新闻模式）

    @model_validator(mode='before')
    @classmethod
    def _map_legacy_fields(cls, data):
        """向后兼容：旧参数名映射到新参数名"""
        if isinstance(data, dict):
            # debunk_delay → response_delay
            if 'debunk_delay' in data and 'response_delay' not in data:
                data['response_delay'] = data.pop('debunk_delay')
            elif 'debunk_delay' in data and 'response_delay' in data:
                data.pop('debunk_delay', None)

            # initial_rumor_spread → initial_negative_spread
            if 'initial_rumor_spread' in data and 'initial_negative_spread' not in data:
                data['initial_negative_spread'] = data.pop('initial_rumor_spread')
            elif 'initial_rumor_spread' in data and 'initial_negative_spread' in data:
                data.pop('initial_rumor_spread', None)

            # debunk_credibility → response_credibility
            if 'debunk_credibility' in data and 'response_credibility' not in data:
                data['response_credibility'] = data.pop('debunk_credibility')
            elif 'debunk_credibility' in data and 'response_credibility' in data:
                data.pop('debunk_credibility', None)

            # init_distribution 中的 believe_rumor/truth → believe_negative/positive
            if 'init_distribution' in data and data['init_distribution'] is not None:
                dist = dict(data['init_distribution'])
                if 'believe_rumor' in dist and 'believe_negative' not in dist:
                    dist['believe_negative'] = dist.pop('believe_rumor')
                if 'believe_truth' in dist and 'believe_positive' not in dist:
                    dist['believe_positive'] = dist.pop('believe_truth')
                data['init_distribution'] = dist
        return data

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 同步兼容字段的默认值
        if self.debunk_delay is None:
            object.__setattr__(self, 'debunk_delay', self.response_delay)
        if self.initial_rumor_spread is None:
            object.__setattr__(self, 'initial_rumor_spread', self.initial_negative_spread)
        if self.debunk_credibility is None:
            object.__setattr__(self, 'debunk_credibility', self.response_credibility)


class SimulationState(BaseModel):
    """模拟状态快照 - 双层网络版本"""
    step: int
    agents: List[Dict]
    # 双层网络边（公域和私域分开）
    public_edges: List[tuple] = []     # 公域网络边
    private_edges: List[tuple] = []    # 私域网络边
    edges: List[tuple] = []            # 兼容旧版（公域边）
    opinion_distribution: Dict[str, List]
    # 整体统计（新字段名）
    negative_belief_rate: float        # 负面信念率（替代 rumor_spread_rate）
    positive_belief_rate: float        # 正面信念率（替代 truth_acceptance_rate）
    avg_opinion: float
    polarization_index: float
    silence_rate: float = 0.0
    # 双层网络统计（新字段名）
    public_negative_rate: float = 0.0  # 公域负面信念率
    public_positive_rate: float = 0.0  # 公域正面信念率
    private_negative_rate: float = 0.0 # 私域负面信念率
    private_positive_rate: float = 0.0 # 私域正面信念率
    num_communities: int = 0           # 社群数量
    num_influencers: int = 0           # 大V数量
    # Phase 3: 新闻模式专用
    mode: str = "sandbox"              # 运行模式
    entity_impact_summary: Optional[Dict[str, float]] = None  # 实体影响摘要

    @model_validator(mode='before')
    @classmethod
    def _map_legacy_fields(cls, data):
        """向后兼容：旧字段名映射到新字段名"""
        if isinstance(data, dict):
            # rumor_spread_rate → negative_belief_rate
            if 'rumor_spread_rate' in data and 'negative_belief_rate' not in data:
                data['negative_belief_rate'] = data.pop('rumor_spread_rate')
            elif 'rumor_spread_rate' in data and 'negative_belief_rate' in data:
                data.pop('rumor_spread_rate', None)

            # truth_acceptance_rate → positive_belief_rate
            if 'truth_acceptance_rate' in data and 'positive_belief_rate' not in data:
                data['positive_belief_rate'] = data.pop('truth_acceptance_rate')
            elif 'truth_acceptance_rate' in data and 'positive_belief_rate' in data:
                data.pop('truth_acceptance_rate', None)

            # public_rumor_rate → public_negative_rate
            if 'public_rumor_rate' in data and 'public_negative_rate' not in data:
                data['public_negative_rate'] = data.pop('public_rumor_rate')
            elif 'public_rumor_rate' in data and 'public_negative_rate' in data:
                data.pop('public_rumor_rate', None)

            # public_truth_rate → public_positive_rate
            if 'public_truth_rate' in data and 'public_positive_rate' not in data:
                data['public_positive_rate'] = data.pop('public_truth_rate')
            elif 'public_truth_rate' in data and 'public_positive_rate' in data:
                data.pop('public_truth_rate', None)

            # private_rumor_rate → private_negative_rate
            if 'private_rumor_rate' in data and 'private_negative_rate' not in data:
                data['private_negative_rate'] = data.pop('private_rumor_rate')
            elif 'private_rumor_rate' in data and 'private_negative_rate' in data:
                data.pop('private_rumor_rate', None)

            # private_truth_rate → private_positive_rate
            if 'private_truth_rate' in data and 'private_positive_rate' not in data:
                data['private_positive_rate'] = data.pop('private_truth_rate')
            elif 'private_truth_rate' in data and 'private_positive_rate' in data:
                data.pop('private_truth_rate', None)
        return data

    @property
    def rumor_spread_rate(self) -> float:
        """向后兼容属性"""
        return self.negative_belief_rate

    @rumor_spread_rate.setter
    def rumor_spread_rate(self, value: float):
        self.negative_belief_rate = value

    @property
    def truth_acceptance_rate(self) -> float:
        """向后兼容属性"""
        return self.positive_belief_rate

    @truth_acceptance_rate.setter
    def truth_acceptance_rate(self, value: float):
        self.positive_belief_rate = value

    @property
    def public_rumor_rate(self) -> float:
        return self.public_negative_rate

    @public_rumor_rate.setter
    def public_rumor_rate(self, value: float):
        self.public_negative_rate = value

    @property
    def public_truth_rate(self) -> float:
        return self.public_positive_rate

    @public_truth_rate.setter
    def public_truth_rate(self, value: float):
        self.public_positive_rate = value

    @property
    def private_rumor_rate(self) -> float:
        return self.private_negative_rate

    @private_rumor_rate.setter
    def private_rumor_rate(self, value: float):
        self.private_negative_rate = value

    @property
    def private_truth_rate(self) -> float:
        return self.private_positive_rate

    @private_truth_rate.setter
    def private_truth_rate(self, value: float):
        self.private_positive_rate = value

    def to_dict(self) -> dict:
        """转换为可序列化的字典（输出新字段名，同时保留旧字段名兼容）"""
        return {
            "step": self.step,
            "agents": self.agents,
            "public_edges": self.public_edges,
            "private_edges": self.private_edges,
            "edges": self.edges,
            "opinion_distribution": self.opinion_distribution,
            # 新字段名
            "negative_belief_rate": self.negative_belief_rate,
            "positive_belief_rate": self.positive_belief_rate,
            "avg_opinion": self.avg_opinion,
            "polarization_index": self.polarization_index,
            "silence_rate": self.silence_rate,
            "public_negative_rate": self.public_negative_rate,
            "public_positive_rate": self.public_positive_rate,
            "private_negative_rate": self.private_negative_rate,
            "private_positive_rate": self.private_positive_rate,
            "num_communities": self.num_communities,
            "num_influencers": self.num_influencers,
            "mode": self.mode,
            "entity_impact_summary": self.entity_impact_summary,
            # 旧字段名兼容（前端过渡期）
            "rumor_spread_rate": self.negative_belief_rate,
            "truth_acceptance_rate": self.positive_belief_rate,
            "public_rumor_rate": self.public_negative_rate,
            "public_truth_rate": self.public_positive_rate,
            "private_rumor_rate": self.private_negative_rate,
            "private_truth_rate": self.private_positive_rate,
        }


class DualNetworkInfo(BaseModel):
    """双层网络元信息"""
    num_nodes: int
    num_communities: int
    num_influencers: int
    public_edges: int
    private_edges: int
    influencer_ids: List[int]

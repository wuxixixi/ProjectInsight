"""
AlgorithmEnv - 算法推荐环境

模拟信息茧房效应:
- 根据用户观点推荐相似内容
- 强化既有观点
- 追踪信息多样性指数
"""
from typing import Dict, List, Any, Optional
import random
import logging

from .base import EnvBase, tool, ToolKind
from ...constants import OPINION_THRESHOLD_NEGATIVE, OPINION_THRESHOLD_POSITIVE

logger = logging.getLogger(__name__)


# 默认推荐内容池
DEFAULT_CONTENT_POOL = {
    "negative": [
        "相关分析：局势可能进一步恶化...",
        "专家警告：情况不容乐观...",
        "多方质疑：官方说法存疑...",
        "深度调查：真相尚未浮出水面...",
        "舆论关注：事件仍有诸多疑点..."
    ],
    "neutral": [
        "多方观点交织，建议理性看待...",
        "情况复杂，需进一步观察...",
        "各方说法不一，真相待揭晓...",
        "事件仍在发展中，请持续关注..."
    ],
    "positive": [
        "官方通报：情况已得到有效控制...",
        "专家解读：措施得当，形势向好...",
        "权威发布：事实真相已查明...",
        "多方证实：信息不实，请勿传谣..."
    ]
}


class AlgorithmEnv(EnvBase):
    """
    算法推荐环境
    
    模拟推荐算法的信息茧房效应:
    - 基于用户观点历史生成推荐内容
    - 茧房强度决定内容与用户观点的一致性
    - 追踪每个用户的信息暴露历史
    """
    
    def __init__(
        self,
        cocoon_strength: float = 0.5,
        diversity_threshold: float = 0.3,
        content_pool: Optional[Dict[str, List[str]]] = None,
        seed: int = 42,
        content_threshold_negative: float = None,
        content_threshold_positive: float = None
    ):
        super().__init__()

        self._cocoon_strength = cocoon_strength
        self._diversity_threshold = diversity_threshold

        # 用户暴露历史: agent_id -> List[ExposureRecord]
        self._exposure_history: Dict[int, List[Dict]] = {}

        # 推荐内容库（支持外部注入）
        self._content_pool = content_pool or DEFAULT_CONTENT_POOL

        # 实例级随机生成器（确保可重现性）
        self._rng = random.Random(seed)

        # 内容分类阈值（使用 constants.py 中的默认值，issue #440）
        self._content_threshold_negative = content_threshold_negative if content_threshold_negative is not None else OPINION_THRESHOLD_NEGATIVE
        self._content_threshold_positive = content_threshold_positive if content_threshold_positive is not None else OPINION_THRESHOLD_POSITIVE
    
    @property
    def name(self) -> str:
        return "algorithm"
    
    @tool(readonly=True, kind="observe")
    async def observe(self, agent_id: int, opinion: float) -> str:
        """
        感知算法推荐内容
        
        Args:
            agent_id: Agent ID
            opinion: 当前观点值 [-1, 1]
        
        Returns:
            推荐内容
        """
        # 根据观点和茧房强度选择内容
        recommended = self._generate_recommendation(opinion)
        
        # 记录暴露历史
        self._record_exposure(agent_id, recommended, opinion)
        
        return recommended
    
    @tool(readonly=True, kind="statistics")
    async def get_diversity_index(self, agent_id: int) -> float:
        """
        获取用户信息多样性指数

        使用 Shannon 熵衡量推荐内容类型的多样性，
        而非观点方差（方差反映分散度而非信息来源多样性）。

        Args:
            agent_id: Agent ID

        Returns:
            多样性指数 [0, 1]，越高越多样
        """
        history = self._exposure_history.get(agent_id, [])
        if len(history) < 2:
            return 1.0

        # 基于内容分类计数计算 Shannon 熵
        import math
        categories = {"negative": 0, "neutral": 0, "positive": 0}
        for h in history:
            alignment = h.get("content_alignment", 0)
            if alignment < self._content_threshold_negative:
                categories["negative"] += 1
            elif alignment > self._content_threshold_positive:
                categories["positive"] += 1
            else:
                categories["neutral"] += 1

        total = sum(categories.values())
        if total == 0:
            return 0.0

        # Shannon 熵
        entropy = 0.0
        for count in categories.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        # 最大熵 = log2(3) ≈ 1.585（三类均匀分布时）
        max_entropy = math.log2(3)
        diversity = min(1.0, entropy / max_entropy) if max_entropy > 0 else 0.0

        return diversity
    
    @tool(readonly=True, kind="statistics")
    async def get_cocoon_strength(self) -> float:
        """
        获取当前茧房强度
        
        Returns:
            茧房强度 [0, 1]
        """
        return self._cocoon_strength
    
    @tool(readonly=True, kind="statistics")
    async def get_exposure_count(self, agent_id: int) -> int:
        """
        获取用户暴露次数
        
        Args:
            agent_id: Agent ID
        
        Returns:
            暴露次数
        """
        return len(self._exposure_history.get(agent_id, []))
    
    @tool(readonly=True, kind="statistics")
    async def get_statistics(self) -> Dict[str, Any]:
        """
        获取算法环境统计信息
        
        Returns:
            统计数据
        """
        total_exposure = sum(len(h) for h in self._exposure_history.values())
        agent_count = len(self._exposure_history)
        
        return {
            "cocoon_strength": self._cocoon_strength,
            "total_exposure": total_exposure,
            "agent_count": agent_count,
            "avg_exposure_per_agent": total_exposure / agent_count if agent_count > 0 else 0
        }
    
    @tool(readonly=False, kind="interact")
    async def set_cocoon_strength(self, strength: float):
        """
        设置茧房强度
        
        Args:
            strength: 茧房强度 [0, 1]
        """
        self._cocoon_strength = max(0.0, min(1.0, strength))
    
    def _generate_recommendation(self, opinion: float) -> str:
        """
        生成推荐内容
        
        Args:
            opinion: 用户观点值
        
        Returns:
            推荐内容
        """
        # 茧房效应：高强度时推荐与观点一致的内容
        if self._rng.random() < self._cocoon_strength:
            # 推荐与当前观点一致的内容
            if opinion < self._content_threshold_negative:
                pool = self._content_pool["negative"]
            elif opinion > self._content_threshold_positive:
                pool = self._content_pool["positive"]
            else:
                pool = self._content_pool["neutral"]
        else:
            # 低概率推荐多元内容
            pool = self._content_pool["neutral"] + self._rng.choice([
                self._content_pool["negative"],
                self._content_pool["positive"]
            ])
        
        return self._rng.choice(pool)
    
    def _record_exposure(self, agent_id: int, content: str, alignment: float):
        """记录信息暴露"""
        if agent_id not in self._exposure_history:
            self._exposure_history[agent_id] = []
        
        self._exposure_history[agent_id].append({
            "content": content,
            "content_alignment": alignment,
            "cocoon_strength": self._cocoon_strength
        })
    
    async def reset(self):
        """重置环境状态"""
        self._exposure_history.clear()
    
    async def get_state(self) -> Dict[str, Any]:
        """获取环境状态"""
        return {
            "cocoon_strength": self._cocoon_strength,
            "exposure_history": {
                k: len(v) for k, v in self._exposure_history.items()
            }
        }

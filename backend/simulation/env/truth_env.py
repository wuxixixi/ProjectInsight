"""
TruthEnv - 官方辟谣环境

模拟官方权威信息发布:
- 辟谣内容管理
- 发布时机模拟
- 权威可信度模型
- 辟谣效果追踪
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import numpy as np

from .base import EnvBase, tool

logger = logging.getLogger(__name__)


class Intervention:
    """官方干预（辟谣）事件"""

    _next_id: int = 0

    def __init__(
        self,
        step: int,
        content: str,
        credibility: float = 0.7,
        reach: float = 1.0,
        timing: str = "delayed"
    ):
        Intervention._next_id += 1
        self.id = Intervention._next_id
        self.step = step
        self.content = content
        self.credibility = credibility
        self.reach = reach  # 覆盖范围 [0, 1]
        self.timing = timing  # "immediate" | "delayed" | "reactive"
        self.active = True
        self.exposure_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "step": self.step,
            "content": self.content,
            "credibility": self.credibility,
            "reach": self.reach,
            "timing": self.timing,
            "active": self.active,
            "exposure_count": self.exposure_count
        }


class TruthEnv(EnvBase):
    """
    官方辟谣环境
    
    管理:
    - 辟谣内容队列
    - 发布时机控制
    - 权威可信度
    - 辟谣效果追踪
    """
    
    def __init__(
        self,
        response_delay: int = 10,
        default_credibility: float = 0.7
    ):
        super().__init__()
        
        self._response_delay = response_delay
        self._default_credibility = default_credibility
        
        # 干预事件列表
        self._interventions: List[Intervention] = []
        
        # 已发布的干预
        self._published: List[Intervention] = []
        
        # 辟谣效果追踪: agent_id -> set of intervention ids (issue #340)
        self._exposure_tracking: Dict[int, set] = {}
        
        # 当前步数
        self._current_step = 0
    
    @property
    def name(self) -> str:
        return "truth"
    
    @tool(readonly=True, kind="observe")
    async def get_intervention(self, agent_id: int) -> Optional[str]:
        """
        获取当前可用的辟谣信息

        Args:
            agent_id: Agent ID

        Returns:
            辟谣内容（如有），否则 None
        """
        for intervention in self._published:
            if not intervention.active:
                continue

            # 使用确定性随机（基于 agent_id 和 step）确保可重现性
            rng = np.random.RandomState(agent_id + self._current_step * 1000)
            if rng.random() < intervention.reach:
                # 记录暴露（使用稳定的业务ID）
                if agent_id not in self._exposure_tracking:
                    self._exposure_tracking[agent_id] = set()
                self._exposure_tracking[agent_id].add(intervention.id)
                intervention.exposure_count += 1

                return intervention.content

        return None
    
    @tool(readonly=True, kind="observe")
    async def get_credibility(self) -> float:
        """
        获取官方信息可信度
        
        Returns:
            可信度 [0, 1]
        """
        return self._default_credibility
    
    @tool(readonly=True, kind="statistics")
    async def get_intervention_stats(self) -> Dict[str, Any]:
        """
        获取辟谣统计信息
        
        Returns:
            辟谣统计数据
        """
        return {
            "total_interventions": len(self._interventions),
            "published_interventions": len(self._published),
            "pending_interventions": len(self._interventions) - len(self._published),
            "total_exposure": sum(len(exposures) for exposures in self._exposure_tracking.values()),
            "agents_reached": len(self._exposure_tracking)
        }
    
    @tool(readonly=True, kind="statistics")
    async def get_timing_analysis(self) -> Dict[str, Any]:
        """
        获取辟谣时机分析
        
        Returns:
            时机分析数据
        """
        if not self._published:
            return {"avg_delay": 0, "timing_categories": {}}
        
        delays = [i.step for i in self._published]
        timing_categories = {}
        for i in self._published:
            timing_categories[i.timing] = timing_categories.get(i.timing, 0) + 1
        
        return {
            "avg_delay": sum(delays) / len(delays),
            "earliest": min(delays),
            "latest": max(delays),
            "timing_categories": timing_categories
        }
    
    @tool(readonly=False, kind="interact")
    async def add_intervention(
        self,
        content: str,
        step: Optional[int] = None,
        credibility: Optional[float] = None,
        reach: float = 1.0,
        timing: str = "delayed"
    ):
        """
        添加辟谣干预
        
        Args:
            content: 辟谣内容
            step: 发布步数（None 则为当前步 + 延迟）
            credibility: 可信度
            reach: 覆盖范围
            timing: 时机类型
        """
        if step is None:
            step = self._current_step + self._response_delay
        
        intervention = Intervention(
            step=step,
            content=content,
            credibility=credibility or self._default_credibility,
            reach=reach,
            timing=timing
        )
        
        self._interventions.append(intervention)
    
    @tool(readonly=False, kind="interact")
    async def set_credibility(self, credibility: float):
        """
        设置官方信息可信度
        
        Args:
            credibility: 可信度 [0, 1]
        """
        self._default_credibility = max(0.0, min(1.0, credibility))
    
    def advance_step(self, step: int):
        """
        推进步数，检查是否有干预需要发布
        
        Args:
            step: 当前步数
        """
        self._current_step = step
        
        # 检查待发布的干预
        for intervention in self._interventions:
            if intervention not in self._published and intervention.step <= step:
                self._published.append(intervention)
                logger.info(f"TruthEnv: 步骤 {step} 发布辟谣 - {intervention.content[:30]}...")
    
    async def reset(self):
        """重置环境状态"""
        self._interventions.clear()
        self._published.clear()
        self._exposure_tracking.clear()
        self._current_step = 0
    
    async def get_state(self) -> Dict[str, Any]:
        """获取环境状态"""
        return {
            "current_step": self._current_step,
            "pending_interventions": len(self._interventions) - len(self._published),
            "published_count": len(self._published),
            "default_credibility": self._default_credibility
        }

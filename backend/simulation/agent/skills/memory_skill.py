"""
Memory Skill - 记忆检索技能

优先级: 20
功能: 检索相关记忆，提供历史上下文
"""
from typing import Dict, Any, List, Optional
import logging

from .base import SkillBase, SkillMetadata, SkillContext, SkillResult
from .loader import SkillLoader

logger = logging.getLogger(__name__)


@SkillLoader.register("memory")
class MemorySkill(SkillBase):
    """
    记忆检索技能

    负责:
    - 从短时记忆检索最近交互
    - 从长时记忆检索信念历史
    - 提供上下文给后续技能
    """

    def __init__(
        self,
        recent_interactions_limit: int = 5,
        belief_history_limit: int = 10,
        trend_window: int = 5,
        metadata: Optional["SkillMetadata"] = None
    ):
        """
        Args:
            recent_interactions_limit: 短时记忆截断数量（issue #633）
            belief_history_limit: 信念历史截断数量
            trend_window: 趋势分析窗口大小
        """
        super().__init__(metadata)
        self.recent_interactions_limit = recent_interactions_limit
        self.belief_history_limit = belief_history_limit
        self.trend_window = trend_window

    def _get_default_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="memory",
            description="检索相关记忆，提供历史上下文",
            priority=20,
            requires=["observation"],  # 依赖观察结果
            provides=["recent_interactions", "belief_history", "exposure_summary"],
            readonly=True
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行记忆检索"""
        # 从上下文获取记忆数据
        memory = context.memory

        # 1. 短时记忆: 最近交互
        recent_interactions = memory.get("recent_interactions", [])

        # 2. 长时记忆: 信念历史趋势
        belief_history = memory.get("belief_history", [])

        # 3. 暴露历史摘要
        exposure_summary = memory.get("exposure_summary", {})

        # 4. 分析信念变化趋势
        trend = self._analyze_belief_trend(belief_history)

        return SkillResult(
            skill_name="memory",
            success=True,
            output={
                "recent_interactions": recent_interactions[-self.recent_interactions_limit:],
                "belief_history": belief_history[-self.belief_history_limit:],
                "exposure_summary": exposure_summary,
                "belief_trend": trend
            },
            reasoning=f"检索到 {len(recent_interactions)} 条近期交互, 信念趋势: {trend}"
        )

    def _analyze_belief_trend(self, history: List[Dict]) -> str:
        """分析信念变化趋势（基于线性回归斜率，issue #450）"""
        if len(history) < 2:
            return "数据不足"

        recent = history[-self.trend_window:] if len(history) >= self.trend_window else history
        opinions = [h.get("opinion", 0) for h in recent if "opinion" in h]

        if len(opinions) < 2:
            return "数据不足"

        # 线性回归计算斜率
        n = len(opinions)
        x_mean = (n - 1) / 2.0
        y_mean = sum(opinions) / n
        numerator = sum((i - x_mean) * (opinions[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "保持稳定"

        slope = numerator / denominator

        # 斜率阈值判定趋势
        if slope > 0.02:
            return "趋向正面"
        elif slope < -0.02:
            return "趋向负面"
        else:
            return "保持稳定"
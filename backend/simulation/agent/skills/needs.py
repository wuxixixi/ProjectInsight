"""
Needs Skill - 需求分析技能

优先级: 30
功能: 基于马斯洛需求层次分析信息接受度
"""
from typing import Dict, Any, List
import logging

from .base import SkillBase, SkillMetadata, SkillContext, SkillResult
from .loader import SkillLoader

logger = logging.getLogger(__name__)


# 马斯洛需求层次
NEED_LEVELS = [
    "physiological",  # 生理需求
    "safety",         # 安全需求
    "love",           # 社交需求
    "esteem",         # 尊重需求
    "cognitive"       # 认知需求
]


@SkillLoader.register("needs")
class NeedsSkill(SkillBase):
    """
    需求分析技能

    基于马斯洛需求层次理论:
    - 分析信息与需求的匹配度
    - 计算信息接受度
    - 预测观点影响程度
    """

    def __init__(
        self,
        safety_fear_threshold: float = 0.6,
        social_susceptibility_threshold: float = 0.6,
        cognitive_strength_threshold: float = 0.4,
        base_acceptance: float = 0.3,
        need_bonus_factor: float = 0.3,
        strength_penalty_factor: float = 0.2
    ):
        """
        初始化需求分析技能

        Args:
            safety_fear_threshold: 触发安全需求的恐惧阈值
            social_susceptibility_threshold: 触发社交需求的易感性阈值
            cognitive_strength_threshold: 触发认知需求的信念强度阈值
            base_acceptance: 基础信息接受度
            need_bonus_factor: 需求匹配加成系数
            strength_penalty_factor: 信念强度减成系数
        """
        super().__init__()
        self.safety_fear_threshold = safety_fear_threshold
        self.social_susceptibility_threshold = social_susceptibility_threshold
        self.cognitive_strength_threshold = cognitive_strength_threshold
        self.base_acceptance = base_acceptance
        self.need_bonus_factor = need_bonus_factor
        self.strength_penalty_factor = strength_penalty_factor

    def _get_default_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="needs",
            description="基于马斯洛需求层次分析信息接受度",
            priority=30,
            requires=["observation", "memory"],
            provides=["need_state", "information_acceptance", "motivation_factor"],
            readonly=True,
            config={
                "need_weights": {
                    "physiological": 0.1,
                    "safety": 0.25,
                    "love": 0.25,
                    "esteem": 0.2,
                    "cognitive": 0.2
                }
            }
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行需求分析"""
        # 获取当前需求状态
        need_state = self._assess_need_state(context)
        
        # 分析信息与需求匹配
        exposures = context.previous_results.get("observation", {}).get("exposures", [])
        info_acceptance = self._compute_info_acceptance(exposures, need_state, context)
        
        # 计算动机因子
        motivation = self._compute_motivation(need_state, context)
        
        return SkillResult(
            skill_name="needs",
            success=True,
            output={
                "need_state": need_state,
                "information_acceptance": info_acceptance,
                "motivation_factor": motivation
            },
            reasoning=f"主导需求: {need_state['dominant_need']}, 信息接受度: {info_acceptance:.2f}"
        )
    
    def _assess_need_state(self, context: SkillContext) -> Dict[str, Any]:
        """评估当前需求状态"""
        # 基于 Agent 特征推断需求层次
        belief = context.belief_state
        fear = belief.get("fear_of_isolation", 0.5)
        susceptibility = belief.get("susceptibility", 0.5)

        # 阈值参数化映射
        needs = {}

        # 高恐惧 → 安全需求主导
        if fear > self.safety_fear_threshold:
            needs["dominant_need"] = "safety"
            needs["safety_urgency"] = fear
        # 高易感性 → 社交需求主导
        elif susceptibility > self.social_susceptibility_threshold:
            needs["dominant_need"] = "love"
            needs["social_urgency"] = susceptibility
        # 低信念强度 → 认知需求
        elif belief.get("belief_strength", 0.5) < self.cognitive_strength_threshold:
            needs["dominant_need"] = "cognitive"
            needs["cognitive_urgency"] = 1 - belief.get("belief_strength", 0.5)
        else:
            needs["dominant_need"] = "esteem"
            needs["esteem_urgency"] = 0.5

        return needs

    def _compute_info_acceptance(
        self,
        exposures: List[Dict],
        need_state: Dict,
        context: SkillContext
    ) -> float:
        """计算信息接受度"""
        if not exposures:
            return 0.5

        # 需求匹配加成
        dominant = need_state.get("dominant_need", "safety")
        urgency = need_state.get(f"{dominant}_urgency", 0.5)
        need_bonus = urgency * self.need_bonus_factor

        # 信念强度减成（信念越强，越难接受新信息）
        strength_penalty = context.belief_state.get("belief_strength", 0.5) * self.strength_penalty_factor

        acceptance = self.base_acceptance + need_bonus - strength_penalty
        return max(0.1, min(0.9, acceptance))
    
    def _compute_motivation(self, need_state: Dict, context: SkillContext) -> float:
        """计算动机因子"""
        dominant = need_state.get("dominant_need", "safety")
        
        # 需求层次 → 动机强度
        level_index = NEED_LEVELS.index(dominant) if dominant in NEED_LEVELS else 2
        level_factor = (level_index + 1) / len(NEED_LEVELS)
        
        # 认知闭合需求
        closed_need = context.belief_state.get("cognitive_closed_need", 0.5)
        
        # 综合动机
        motivation = level_factor * 0.6 + closed_need * 0.4
        return min(1.0, motivation)
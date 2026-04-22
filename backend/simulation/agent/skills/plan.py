"""
Plan Skill - 规划技能

优先级: 50
功能: 规划行动策略，决定最终行为
"""
from typing import Dict, Any, List
import logging

from .base import SkillBase, SkillMetadata, SkillContext, SkillResult
from .loader import SkillLoader

logger = logging.getLogger(__name__)


@SkillLoader.register("plan")
class PlanSkill(SkillBase):
    """
    规划技能
    
    负责:
    - 决定是否沉默
    - 选择行动类型
    - 生成输出内容
    """
    
    def _get_default_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="plan",
            description="规划行动策略，决定最终行为",
            priority=50,
            requires=["observation", "cognition"],
            provides=["action", "is_silent", "generated_comment"],
            readonly=False
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行规划"""
        # 收集输入
        observation = context.previous_results.get("observation", {})
        cognition = context.previous_results.get("cognition", {})
        
        # 1. 决定是否沉默（沉默的螺旋）
        is_silent = self._decide_silence(observation, context)
        
        # 2. 选择行动类型
        action = self._select_action(cognition, is_silent, context)
        
        # 3. 生成评论（如果需要）
        generated_comment = None
        if action == "评论":
            generated_comment = self._generate_comment(cognition, context)
        
        return SkillResult(
            skill_name="plan",
            success=True,
            output={
                "action": action,
                "is_silent": is_silent,
                "generated_comment": generated_comment,
                "emotion": self._infer_emotion(cognition, context)
            },
            reasoning=f"选择行动: {action}" + (" (沉默)" if is_silent else "")
        )
    
    def _decide_silence(self, observation: Dict, context: SkillContext) -> bool:
        """决定是否沉默"""
        social_pressure = observation.get("social_pressure", 0.0)
        fear_of_isolation = context.belief_state.get("fear_of_isolation", 0.5)
        
        # 沉默条件: 高社交压力 + 高孤立恐惧
        if social_pressure > 0.5 and fear_of_isolation > 0.6:
            # 计算"观点偏离主流"程度
            peer_opinions = observation.get("peer_opinions", [])
            if peer_opinions:
                current = context.belief_state.get("opinion", 0.0)
                avg_peer = sum(peer_opinions) / len(peer_opinions)
                
                # 观点偏离且恐惧 → 沉默
                if abs(current - avg_peer) > 0.3:
                    return True
        
        return False
    
    def _select_action(
        self,
        cognition: Dict,
        is_silent: bool,
        context: SkillContext
    ) -> str:
        """选择行动类型"""
        if is_silent:
            return "沉默"
        
        belief_delta = abs(cognition.get("belief_delta", 0.0))
        
        # 基于观点变化程度选择行动
        if belief_delta < 0.05:
            return "观望"
        elif belief_delta < 0.15:
            # 有变化但不剧烈
            influence = context.belief_state.get("influence", 0.5)
            if influence > 0.6:
                return "转发"  # 高影响力者倾向于转发
            else:
                return "观望"
        else:
            # 剧烈变化
            susceptibility = context.belief_state.get("susceptibility", 0.5)
            if susceptibility > 0.6:
                return "转发"
            else:
                return "评论"
    
    def _generate_comment(self, cognition: Dict, context: SkillContext) -> str:
        """生成评论内容"""
        new_opinion = cognition.get("new_opinion", 0.0)
        
        # 基于观点生成简单评论
        if new_opinion > 0.3:
            comments = [
                "事实确实如此，大家要理性看待。",
                "支持官方说法，不信谣不传谣。",
                "还是要相信权威信息。"
            ]
        elif new_opinion < -0.3:
            comments = [
                "有些事情还需要进一步调查...",
                "官方说法未必全面，保持警惕。",
                "希望真相早日大白。"
            ]
        else:
            comments = [
                "情况复杂，还需观察。",
                "让子弹再飞一会儿。",
                "理性分析，不要急着下结论。"
            ]
        
        import random
        return random.choice(comments)
    
    def _infer_emotion(self, cognition: Dict, context: SkillContext) -> str:
        """推断情绪状态"""
        delta = cognition.get("belief_delta", 0.0)
        
        if abs(delta) < 0.05:
            return "冷静"
        elif delta > 0.1:
            return "释然"
        elif delta < -0.1:
            return "焦虑"
        elif "truth" in str(cognition):
            return "怀疑"
        else:
            return "冷静"
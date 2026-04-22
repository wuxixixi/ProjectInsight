"""
Cognition Skill - 认知推理技能

优先级: 40
功能: 推理观点变化，生成信念更新
"""
from typing import Dict, Any, List
import logging

from .base import SkillBase, SkillMetadata, SkillContext, SkillResult
from .loader import SkillLoader

logger = logging.getLogger(__name__)


@SkillLoader.register("cognition")
class CognitionSkill(SkillBase):
    """
    认知推理技能
    
    负责:
    - 综合环境信息和记忆
    - 推理观点变化
    - 生成信念更新决策
    """
    
    def _get_default_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="cognition",
            description="推理观点变化，生成信念更新",
            priority=40,
            requires=["observation", "memory", "needs"],
            provides=["belief_delta", "new_opinion", "reasoning"],
            readonly=False,  # 会修改信念状态
            config={
                "reasoning_depth": 3,
                "include_uncertainty": True
            }
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行认知推理"""
        # 收集输入
        observation = context.previous_results.get("observation", {})
        memory = context.previous_results.get("memory", {})
        needs = context.previous_results.get("needs", {})
        
        current_opinion = context.belief_state.get("opinion", 0.0)
        
        # 1. 社会影响推理
        social_delta = self._reason_social_influence(observation, context)
        
        # 2. 算法茧房推理
        algorithm_delta = self._reason_algorithm_effect(observation, context)
        
        # 3. 官方影响推理
        truth_delta = self._reason_truth_effect(observation, context)
        
        # 4. 记忆调节推理
        memory_factor = self._reason_memory_effect(memory, context)
        
        # 5. 需求驱动推理
        need_factor = needs.get("information_acceptance", 0.5)
        
        # 综合计算
        total_delta = (social_delta + algorithm_delta + truth_delta) * memory_factor * need_factor
        
        # 应用信念强度限制
        strength = context.belief_state.get("belief_strength", 0.5)
        max_change = 0.3 * (1 - strength)
        total_delta = max(-max_change, min(max_change, total_delta))
        
        new_opinion = current_opinion + total_delta
        new_opinion = max(-1.0, min(1.0, new_opinion))
        
        # 生成推理过程
        reasoning = self._generate_reasoning(
            social_delta, algorithm_delta, truth_delta,
            memory_factor, need_factor, total_delta
        )
        
        return SkillResult(
            skill_name="cognition",
            success=True,
            output={
                "belief_delta": total_delta,
                "new_opinion": new_opinion,
                "social_delta": social_delta,
                "algorithm_delta": algorithm_delta,
                "truth_delta": truth_delta,
                "reasoning": reasoning
            },
            reasoning=reasoning
        )
    
    def _reason_social_influence(self, observation: Dict, context: SkillContext) -> float:
        """推理社会影响"""
        peer_opinions = observation.get("peer_opinions", [])
        if not peer_opinions:
            return 0.0
        
        current = context.belief_state.get("opinion", 0.0)
        susceptibility = context.belief_state.get("susceptibility", 0.5)
        
        # 计算邻居平均观点
        avg_peer = sum(peer_opinions) / len(peer_opinions)
        
        # 从众效应: 向邻居观点靠拢
        social_influence = (avg_peer - current) * susceptibility * 0.3
        
        return social_influence
    
    def _reason_algorithm_effect(self, observation: Dict, context: SkillContext) -> float:
        """推理算法茧房效应"""
        social_pressure = observation.get("social_pressure", 0.0)
        
        # 高社交压力 → 更依赖算法推荐（承认茧房）
        if social_pressure > 0.5:
            current = context.belief_state.get("opinion", 0.0)
            # 茧房强化既有观点
            return current * 0.05 * social_pressure
        
        return 0.0
    
    def _reason_truth_effect(self, observation: Dict, context: SkillContext) -> float:
        """推理官方辟谣影响"""
        exposures = observation.get("exposures", [])
        
        truth_effect = 0.0
        for exposure in exposures:
            if exposure.get("source") == "truth":
                credibility = exposure.get("credibility", 0.5)
                alignment = exposure.get("alignment", 1.0)
                
                # 官方信息倾向于正面（提升 truth_trust）
                truth_effect += credibility * alignment * 0.15
        
        return truth_effect
    
    def _reason_memory_effect(self, memory: Dict, context: SkillContext) -> float:
        """推理记忆效应"""
        trend = memory.get("belief_trend", "保持稳定")
        
        # 信念趋势影响改变难度
        if trend == "趋向正面":
            return 1.1  # 正向趋势更容易继续正向
        elif trend == "趋向负面":
            return 0.9  # 负向趋势更难转向
        else:
            return 1.0
    
    def _generate_reasoning(
        self,
        social_delta: float,
        algorithm_delta: float,
        truth_delta: float,
        memory_factor: float,
        need_factor: float,
        total_delta: float
    ) -> str:
        """生成推理描述"""
        parts = []
        
        if abs(social_delta) > 0.01:
            direction = "正向" if social_delta > 0 else "负面"
            parts.append(f"社交影响{direction}{abs(social_delta):.2f}")
        
        if abs(algorithm_delta) > 0.01:
            parts.append(f"茧房强化{abs(algorithm_delta):.2f}")
        
        if abs(truth_delta) > 0.01:
            parts.append(f"官方影响{truth_delta:.2f}")
        
        if memory_factor != 1.0:
            parts.append(f"记忆调节{memory_factor:.1f}")
        
        parts.append(f"综合变化{total_delta:+.2f}")
        
        return " | ".join(parts) if parts else "观点保持稳定"
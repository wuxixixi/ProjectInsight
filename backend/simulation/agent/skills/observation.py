"""
Observation Skill - 观察技能

优先级: 10
功能: 感知环境信息，收集暴露事件
"""
from typing import Dict, Any, List, Optional
import logging

from ..belief_state import ExposureEvent, ExposureSource
from .base import SkillBase, SkillMetadata, SkillContext, SkillResult
from .loader import SkillLoader

logger = logging.getLogger(__name__)


@SkillLoader.register("observation")
class ObservationSkill(SkillBase):
    """
    观察技能

    负责感知环境信息:
    - 算法推荐内容
    - 社交圈观点
    - 官方辟谣信息
    - 注入事件
    """

    def __init__(
        self,
        algorithm_credibility: float = 0.5,
        max_peer_observations: int = 5,
        truth_default_alignment: float = 1.0,
        truth_default_credibility: float = 0.7,
        metadata: Optional["SkillMetadata"] = None
    ):
        """
        Args:
            algorithm_credibility: 算法推荐内容默认可信度（issue #630）
            max_peer_observations: 最多观察邻居数量
            truth_default_alignment: 官方信息默认倾向
            truth_default_credibility: 官方信息默认可信度
        """
        super().__init__(metadata)
        self.algorithm_credibility = algorithm_credibility
        self.max_peer_observations = max_peer_observations
        self.truth_default_alignment = truth_default_alignment
        self.truth_default_credibility = truth_default_credibility

    def _get_default_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="observation",
            description="感知环境信息，收集信息暴露事件",
            priority=10,  # 最高优先级
            requires=[],  # 无依赖
            provides=["exposures", "peer_opinions", "social_pressure", "algorithm_content"],
            readonly=True
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行观察"""
        exposures: List[ExposureEvent] = []
        
        # 1. 算法推荐内容
        algorithm_content = self._observe_algorithm(context)
        if algorithm_content:
            exposures.append(algorithm_content)
        
        # 2. 社交圈观点
        peer_exposures, peer_opinions = self._observe_social(context)
        exposures.extend(peer_exposures)
        
        # 3. 官方辟谣
        truth_exposure = self._observe_truth(context)
        if truth_exposure:
            exposures.append(truth_exposure)
        
        # 4. 注入事件
        injected_exposure = self._observe_injected(context)
        if injected_exposure:
            exposures.append(injected_exposure)
        
        # 计算社交压力
        social_pressure = self._compute_social_pressure(peer_opinions, context)
        
        return SkillResult(
            skill_name="observation",
            success=True,
            output={
                "exposures": exposures,
                "exposure_count": len(exposures),
                "peer_opinions": peer_opinions,
                "social_pressure": social_pressure,
                "algorithm_content": algorithm_content.content if algorithm_content else None
            },
            reasoning=f"观察到 {len(exposures)} 条信息"
        )
    
    def _observe_algorithm(self, context: SkillContext) -> ExposureEvent:
        """观察算法推荐"""
        # 从配置或上下文获取算法内容
        algo_content = context.config.get("algorithm_content")
        if not algo_content:
            # 模拟算法推荐：基于当前观点生成相似内容
            opinion = context.belief_state.get("opinion", 0.0)
            if opinion < -0.3:
                algo_content = "相关分析：局势可能进一步恶化..."
            elif opinion > 0.3:
                algo_content = "官方通报：情况已得到有效控制..."
            else:
                algo_content = "多方观点交织，建议理性看待..."
        
        return ExposureEvent(
            step=context.step,
            source=ExposureSource.ALGORITHM,
            content=algo_content,
            alignment=context.belief_state.get("opinion", 0.0),  # 茧房效应：推荐与观点一致的内容
            credibility=self.algorithm_credibility
        )
    
    def _observe_social(self, context: SkillContext) -> tuple:
        """观察社交圈"""
        peer_opinions = context.observation.get("peer_opinions", [])
        peer_ids = context.observation.get("peer_ids", [])
        
        exposures = []
        for i, peer_op in enumerate(peer_opinions[:self.max_peer_observations]):
            exposures.append(ExposureEvent(
                step=context.step,
                source=ExposureSource.SOCIAL,
                content=f"邻居观点: {peer_op:.2f}",
                alignment=peer_op,
                sender_id=peer_ids[i] if i < len(peer_ids) else None
            ))
        
        return exposures, peer_opinions
    
    def _observe_truth(self, context: SkillContext) -> ExposureEvent:
        """观察官方辟谣"""
        truth_content = context.config.get("truth_content")
        if not truth_content:
            return None
        
        return ExposureEvent(
            step=context.step,
            source=ExposureSource.TRUTH,
            content=truth_content,
            alignment=self.truth_default_alignment,  # 官方信息倾向正面
            credibility=context.config.get("truth_credibility", self.truth_default_credibility)
        )
    
    def _observe_injected(self, context: SkillContext) -> ExposureEvent:
        """观察注入事件"""
        injected_content = context.config.get("injected_event")
        if not injected_content:
            return None
        
        return ExposureEvent(
            step=context.step,
            source=ExposureSource.INJECTED,
            content=injected_content,
            alignment=context.config.get("injected_alignment", 0.0),
            credibility=context.config.get("injected_credibility", 0.5)
        )
    
    def _compute_social_pressure(self, peer_opinions: List[float], context: SkillContext) -> float:
        """计算社交压力"""
        if not peer_opinions:
            return 0.0
        
        opinion = context.belief_state.get("opinion", 0.0)
        avg_peer = sum(peer_opinions) / len(peer_opinions)
        
        # 观点差异 × 孤立恐惧
        fear = context.belief_state.get("fear_of_isolation", 0.5)
        pressure = abs(opinion - avg_peer) * fear
        return min(1.0, pressure)
"""
AgentBase - Agent 抽象基类

定义 Agent 的核心接口和通用功能:
- 信念状态管理
- 记忆系统访问
- 环境交互
- 技能管道
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import logging

from .belief_state import BeliefState, ExposureEvent
from .memory import AgentMemory

logger = logging.getLogger(__name__)


class AgentProfile(BaseModel):
    """Agent 人设配置"""
    agent_id: int
    name: str = ""
    age: Optional[int] = None
    occupation: Optional[str] = None
    
    # 心理特征
    susceptibility: float = Field(0.5, ge=0.0, le=1.0, description="易感性")
    influence: float = Field(0.5, ge=0.0, le=1.0, description="影响力")
    fear_of_isolation: float = Field(0.5, ge=0.0, le=1.0, description="孤立恐惧感")
    
    # 认知特征
    media_literacy: float = Field(0.5, ge=0.0, le=1.0, description="媒介素养")
    cognitive_closed_need: float = Field(0.5, ge=0.0, le=1.0, description="认知闭合需求")
    
    # 人设标签
    persona_type: str = "普通用户"
    persona_desc: str = "普通社交媒体用户"
    
    class Config:
        extra = "allow"  # 允许额外字段


class AgentBase(ABC):
    """
    Agent 抽象基类
    
    定义所有 Agent 必须实现的接口:
    - step(): 执行一个推演步骤
    - observe(): 感知环境
    - decide(): 做出决策
    - act(): 执行动作
    """
    
    def __init__(
        self,
        profile: AgentProfile,
        initial_belief: Optional[BeliefState] = None
    ):
        self.profile = profile
        self.id = profile.agent_id
        
        # 信念状态
        self.belief_state = initial_belief or BeliefState(
            cognitive_closed_need=profile.cognitive_closed_need
        )
        
        # 记忆系统
        self.memory = AgentMemory(agent_id=self.id)
        
        # 技能字典 (懒加载)
        self._skills: Dict[str, Any] = {}
        
        # 状态标记
        self.is_active = True
        self.is_silent = False
        
        # 统计
        self.step_count = 0
    
    @abstractmethod
    async def step(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行一个推演步骤
        
        Args:
            context: 推演上下文，包含:
                - step: 当前步数
                - algorithm_content: 算法推荐内容
                - peer_opinions: 邻居观点
                - truth_content: 官方辟谣内容（如有）
                - knowledge_graph: 知识图谱（如有）
        
        Returns:
            步骤结果，包含:
                - new_opinion: 新观点值
                - action: 行动类型
                - is_silent: 是否沉默
                - reasoning: 推理过程（可选）
        """
        pass
    
    @abstractmethod
    async def observe(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        感知环境信息
        
        Returns:
            感知结果，包含:
                - exposures: 暴露事件列表
                - social_pressure: 社交压力
        """
        pass
    
    @abstractmethod
    async def decide(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于感知结果做决策
        
        Returns:
            决策结果，包含:
                - new_belief: 新信念状态
                - action: 行动选择
                - is_silent: 是否沉默
        """
        pass
    
    @abstractmethod
    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行决策动作
        
        Returns:
            动作结果
        """
        pass
    
    # ==================== 通用方法 ====================
    
    def get_opinion(self) -> float:
        """获取当前观点值（兼容旧版）"""
        return self.belief_state.to_opinion()
    
    def set_opinion(self, opinion: float):
        """设置观点值（兼容旧版）"""
        self.belief_state.update_from_opinion(opinion)
    
    def update_belief(
        self, 
        new_belief: BeliefState,
        reasoning: Optional[str] = None
    ):
        """更新信念状态"""
        new_belief.reasoning_trace = reasoning
        self.belief_state = new_belief
        self.belief_state.last_updated = datetime.now(timezone.utc)
        
        # 存储到记忆
        self.memory.store_belief(new_belief, self.step_count)
    
    def add_exposure(self, event: ExposureEvent):
        """添加信息暴露事件"""
        self.belief_state.add_exposure(event)
        self.memory.add_interaction(event)
        self.memory.store_exposure(event, self.step_count)
    
    def get_recent_exposures(self, n: int = 5) -> List[ExposureEvent]:
        """获取最近暴露记录"""
        return self.belief_state.get_recent_exposures(n)
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "id": self.id,
            "profile": self.profile.dict(),
            "belief_state": self.belief_state.to_dict(),
            "opinion": self.get_opinion(),
            "is_active": self.is_active,
            "is_silent": self.is_silent,
            "step_count": self.step_count
        }
    
    def __repr__(self) -> str:
        return f"Agent(id={self.id}, opinion={self.get_opinion():.2f}, type={self.profile.persona_type})"


class MathModelAgent(AgentBase):
    """
    数学模型驱动的 Agent
    
    使用数学公式计算观点变化，不依赖 LLM
    """
    
    async def step(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """数学模型推演步骤"""
        self.step_count = context.get("step", self.step_count + 1)
        
        # 感知
        observation = await self.observe(context)
        
        # 决策（数学公式）
        decision = await self.decide(observation)
        
        # 行动
        result = await self.act(decision)
        
        return result
    
    async def observe(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """感知环境"""
        exposures = []
        
        # 算法推荐
        if "algorithm_content" in context:
            from .belief_state import ExposureSource
            exposures.append(ExposureEvent(
                step=self.step_count,
                source=ExposureSource.ALGORITHM,
                content=context["algorithm_content"],
                alignment=context.get("algorithm_alignment", 0.0)
            ))
        
        # 社交影响
        peer_opinions = context.get("peer_opinions", [])
        if peer_opinions:
            from .belief_state import ExposureSource
            avg_peer = sum(peer_opinions) / len(peer_opinions)
            exposures.append(ExposureEvent(
                step=self.step_count,
                source=ExposureSource.SOCIAL,
                content=f"邻居平均观点: {avg_peer:.2f}",
                alignment=avg_peer
            ))
        
        # 官方辟谣
        if context.get("truth_content"):
            from .belief_state import ExposureSource
            exposures.append(ExposureEvent(
                step=self.step_count,
                source=ExposureSource.TRUTH,
                content=context["truth_content"],
                alignment=1.0,  # 官方信息倾向正面
                credibility=context.get("truth_credibility", 0.7)
            ))
        
        return {
            "exposures": exposures,
            "peer_opinions": peer_opinions,
            "social_pressure": self._compute_social_pressure(peer_opinions)
        }
    
    async def decide(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """数学模型决策"""
        current_opinion = self.get_opinion()
        
        # 计算观点变化
        delta = 0.0
        
        # 社会影响
        peer_opinions = observation.get("peer_opinions", [])
        if peer_opinions:
            avg_peer = sum(peer_opinions) / len(peer_opinions)
            social_influence = (avg_peer - current_opinion) * self.profile.susceptibility * 0.3
            delta += social_influence
        
        # 官方影响
        for exposure in observation.get("exposures", []):
            if exposure.source.value == "truth":
                authority_effect = exposure.alignment * exposure.credibility * 0.2
                delta += authority_effect
        
        # 信念强度限制变化幅度
        max_change = 0.3 * (1 - self.belief_state.belief_strength)
        delta = max(-max_change, min(max_change, delta))
        
        new_opinion = current_opinion + delta
        new_opinion = max(-1.0, min(1.0, new_opinion))
        
        # 沉默判断
        social_pressure = observation.get("social_pressure", 0.0)
        is_silent = (
            social_pressure > 0.5 and 
            self.profile.fear_of_isolation > 0.6 and
            abs(current_opinion - self._get_majority_opinion(peer_opinions)) > 0.3
        )
        
        return {
            "new_opinion": new_opinion,
            "delta": delta,
            "is_silent": is_silent,
            "action": "沉默" if is_silent else "观望"
        }
    
    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """执行决策"""
        new_opinion = decision["new_opinion"]
        self.set_opinion(new_opinion)
        self.is_silent = decision["is_silent"]
        
        # 更新记忆
        self.memory.store_belief(self.belief_state, self.step_count)
        
        return {
            "agent_id": self.id,
            "new_opinion": new_opinion,
            "delta": decision["delta"],
            "is_silent": self.is_silent,
            "action": decision["action"]
        }
    
    def _compute_social_pressure(self, peer_opinions: List[float]) -> float:
        """计算社交压力"""
        if not peer_opinions:
            return 0.0
        
        current = self.get_opinion()
        avg_peer = sum(peer_opinions) / len(peer_opinions)
        
        # 观点差异越大，压力越大
        pressure = abs(current - avg_peer) * self.profile.fear_of_isolation
        return min(1.0, pressure)
    
    def _get_majority_opinion(self, peer_opinions: List[float]) -> float:
        """获取主流观点"""
        if not peer_opinions:
            return 0.0
        avg = sum(peer_opinions) / len(peer_opinions)
        return 1.0 if avg > 0 else -1.0 if avg < 0 else 0.0

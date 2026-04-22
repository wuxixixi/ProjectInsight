"""
BeliefState - 结构化信念状态模型

替代单一 opinion: float，提供更丰富的信念表示:
- rumor_trust: 谣言信任度 [-1, 1]
- truth_trust: 真相信任度 [-1, 1]
- belief_strength: 信念强度 [0, 1]
- cognitive_closed_need: 认知闭合需求 [0, 1]
- exposure_history: 信息暴露历史
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ExposureSource(str, Enum):
    """信息暴露来源"""
    ALGORITHM = "algorithm"  # 算法推荐
    SOCIAL = "social"        # 社交传播
    TRUTH = "truth"          # 官方辟谣
    INJECTED = "injected"    # 外部注入事件


class ExposureEvent(BaseModel):
    """信息暴露事件 - 记录 Agent 接收到的信息"""
    timestamp: datetime = Field(default_factory=datetime.now)
    step: int = 0
    source: ExposureSource
    content: str
    alignment: float = Field(0.0, ge=-1.0, le=1.0, description="内容倾向: -1负面/0中立/1正面")
    trust_delta: float = Field(0.0, description="观点变化量")
    sender_id: Optional[int] = None
    credibility: float = Field(0.5, ge=0.0, le=1.0, description="信息可信度")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BeliefState(BaseModel):
    """
    结构化信念状态
    
    设计理念:
    - 区分谣言信任和真相信任，模拟"知道真相但仍相信谣言"的认知失调
    - belief_strength 表示信念坚定程度，影响改变难度
    - cognitive_closed_need 表示认知闭合需求，影响信息处理方式
    
    向后兼容:
    - to_opinion() 转换为旧版单一观点值
    - from_legacy_opinion() 从旧版数据构造
    """
    
    # 核心观点维度
    rumor_trust: float = Field(
        0.0, 
        ge=-1.0, 
        le=1.0, 
        description="谣言信任度: -1完全不信任, 0中立, 1完全信任"
    )
    truth_trust: float = Field(
        0.0, 
        ge=-1.0, 
        le=1.0, 
        description="真相信任度: -1完全不信任, 0中立, 1完全信任"
    )
    
    # 信念属性
    belief_strength: float = Field(
        0.5, 
        ge=0.0, 
        le=1.0, 
        description="信念强度: 0动摇, 1坚定"
    )
    cognitive_closed_need: float = Field(
        0.5, 
        ge=0.0, 
        le=1.0, 
        description="认知闭合需求: 0开放探索, 1急于下结论"
    )
    
    # 暴露历史 (最近 N 条，用于短时记忆)
    exposure_history: List[ExposureEvent] = Field(
        default_factory=list,
        description="信息暴露历史"
    )
    
    # 元数据
    last_updated: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="最后更新时间"
    )
    
    # 推理轨迹 (LLM 模式下记录)
    reasoning_trace: Optional[str] = Field(
        None,
        description="最近的推理过程"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    def to_opinion(self) -> float:
        """
        转换为单一观点值 [-1, 1]
        
        映射规则:
        - rumor_trust 高 → opinion 负（误信）
        - truth_trust 高 → opinion 正（正确认知）
        - 综合值 = truth_trust - rumor_trust
        
        这保持了与旧版 opinion 语义的兼容:
        - opinion < 0: 误信负面信息
        - opinion > 0: 正确认知
        - opinion ≈ 0: 中立/不确定
        """
        return self.truth_trust - self.rumor_trust
    
    @classmethod
    def from_legacy_opinion(
        cls, 
        opinion: float, 
        strength: float = 0.5,
        cognitive_closed_need: float = 0.5
    ) -> "BeliefState":
        """
        从旧版观点值构造 BeliefState
        
        转换规则:
        - opinion > 0: truth_trust = opinion, rumor_trust = 0
        - opinion < 0: truth_trust = 0, rumor_trust = -opinion
        - opinion ≈ 0: 两者都接近 0
        """
        if opinion > 0:
            return cls(
                truth_trust=opinion,
                rumor_trust=0.0,
                belief_strength=strength,
                cognitive_closed_need=cognitive_closed_need
            )
        else:
            return cls(
                truth_trust=0.0,
                rumor_trust=-opinion,
                belief_strength=strength,
                cognitive_closed_need=cognitive_closed_need
            )
    
    def update_from_opinion(self, new_opinion: float, max_change: float = None):
        """
        从新观点值更新信念状态
        
        Args:
            new_opinion: 新的观点值
            max_change: 最大变化限制（可选）
        """
        old_opinion = self.to_opinion()
        delta = new_opinion - old_opinion
        
        # 应用变化限制
        if max_change is not None:
            delta = max(-max_change, min(max_change, delta))
        
        new_opinion = old_opinion + delta
        
        # 更新 belief_state
        if new_opinion > 0:
            self.truth_trust = min(1.0, new_opinion)
            self.rumor_trust = max(0.0, self.rumor_trust - abs(delta) * 0.3)
        else:
            self.rumor_trust = min(1.0, -new_opinion)
            self.truth_trust = max(0.0, self.truth_trust - abs(delta) * 0.3)
        
        self.last_updated = datetime.now()
    
    def add_exposure(self, event: ExposureEvent):
        """添加信息暴露事件"""
        self.exposure_history.append(event)
        # 保持历史长度限制 (默认保留最近 20 条)
        if len(self.exposure_history) > 20:
            self.exposure_history = self.exposure_history[-20:]
    
    def get_recent_exposures(self, n: int = 5) -> List[ExposureEvent]:
        """获取最近 N 条暴露记录"""
        return self.exposure_history[-n:]
    
    def get_exposure_summary(self) -> Dict[str, Any]:
        """获取暴露历史摘要"""
        if not self.exposure_history:
            return {"total": 0, "by_source": {}}
        
        by_source = {}
        for event in self.exposure_history:
            source = event.source.value
            if source not in by_source:
                by_source[source] = {"count": 0, "total_delta": 0.0}
            by_source[source]["count"] += 1
            by_source[source]["total_delta"] += event.trust_delta
        
        return {
            "total": len(self.exposure_history),
            "by_source": by_source,
            "avg_alignment": sum(e.alignment for e in self.exposure_history) / len(self.exposure_history)
        }
    
    def is_convinced(self, threshold: float = 0.3) -> bool:
        """判断是否已形成明确观点"""
        return abs(self.to_opinion()) > threshold
    
    def is_conflicted(self) -> bool:
        """判断是否存在认知失调（同时相信谣言和真相）"""
        return self.rumor_trust > 0.3 and self.truth_trust > 0.3
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典（用于序列化）"""
        return {
            "rumor_trust": self.rumor_trust,
            "truth_trust": self.truth_trust,
            "belief_strength": self.belief_strength,
            "cognitive_closed_need": self.cognitive_closed_need,
            "opinion": self.to_opinion(),
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "exposure_count": len(self.exposure_history)
        }

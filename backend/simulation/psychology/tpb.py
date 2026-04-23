"""
TheoryOfPlannedBehavior - 计划行为理论

TPB 模型出自 Ajzen (1991)，用于解释和预测人类行为意向:
- 态度 (Attitude): 对行为的评价
- 主观规范 (Subjective Norm): 社会压力感知
- 知觉行为控制 (Perceived Behavioral Control): 自我效能感

行为意向 = w1*态度 + w2*主观规范 + w3*知觉行为控制

应用于舆情传播:
- 态度: 对信息内容的评价（有用/有害）
- 主观规范: 社交圈观点压力
- 知觉行为控制: 媒介素养、信息处理能力

预测行为:
- 是否转发
- 是否评论
- 是否沉默
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BehaviorType(str, Enum):
    """行为类型"""
    SHARE = "分享"          # 转发分享
    COMMENT = "评论"        # 评论互动
    OBSERVE = "观望"        # 观望
    SILENCE = "沉默"        # 沉默
    VERIFY = "核查"         # 求证/核查
    REJECT = "拒绝"         # 拒绝传播


class TPBResult(BaseModel):
    """TPB 计算结果"""
    intention: float = Field(..., ge=-1.0, le=1.0, description="行为意向 [-1, 1]")
    attitude: float = Field(..., ge=-1.0, le=1.0, description="态度")
    subjective_norm: float = Field(..., ge=-1.0, le=1.0, description="主观规范")
    perceived_control: float = Field(..., ge=0.0, le=1.0, description="知觉行为控制")
    predicted_behavior: BehaviorType = Field(..., description="预测行为")
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="预测置信度")


class TheoryOfPlannedBehavior(BaseModel):
    """
    计划行为理论模型

    核心公式:
    行为意向 = w1*态度 + w2*主观规范 + w3*知觉行为控制

    权重可调:
    - 默认: 态度 0.4, 主观规范 0.3, 知觉控制 0.3
    - 高从众 Agent: 主观规范权重提高
    - 高影响 Agent: 态度权重提高

    应用于舆情:
    1. 态度 = 信息可信度 × 内容相关性 - 认知失调成本
    2. 主观规范 = 社交压力 × 从众倾向
    3. 知觉行为控制 = 媒介素养 × 信息处理能力
    """

    # 权重配置
    attitude_weight: float = Field(0.4, ge=0.0, le=1.0)
    norm_weight: float = Field(0.3, ge=0.0, le=1.0)
    control_weight: float = Field(0.3, ge=0.0, le=1.0)

    # 阈值配置
    share_threshold: float = Field(0.5, description="转发阈值")
    silence_threshold: float = Field(-0.5, description="沉默阈值")
    verify_threshold: float = Field(0.1, description="求证阈值")

    # 行为判定阈值（issue #618: 参数化硬编码值）
    attitude_share_threshold: float = Field(0.3, description="转发态度阈值")
    control_share_threshold: float = Field(0.5, description="转发知觉控制阈值")
    opinion_comment_threshold: float = Field(0.3, description="评论观点阈值")
    control_verify_threshold: float = Field(0.6, description="求证知觉控制阈值")
    norm_silence_threshold: float = Field(-0.3, description="沉默主观规范阈值")
    
    def compute_intention(
        self,
        attitude: float,
        subjective_norm: float,
        perceived_control: float
    ) -> float:
        """
        计算行为意向
        
        Args:
            attitude: 态度 [-1, 1]，正向表示支持行为
            subjective_norm: 主观规范 [-1, 1]，正向表示感知到支持
            perceived_control: 知觉行为控制 [0, 1]，越高越有能力
        
        Returns:
            行为意向 [-1, 1]
        """
        # 标准化权重
        total_weight = self.attitude_weight + self.norm_weight + self.control_weight
        w1 = self.attitude_weight / total_weight
        w2 = self.norm_weight / total_weight
        w3 = self.control_weight / total_weight
        
        # 加权求和（知觉控制映射到 [-1, 1]）
        control_normalized = perceived_control * 2 - 1
        
        intention = (
            w1 * attitude + 
            w2 * subjective_norm + 
            w3 * control_normalized
        )
        
        return max(-1.0, min(1.0, intention))
    
    def predict_behavior(
        self,
        intention: float,
        attitude: float,
        subjective_norm: float,
        perceived_control: float,
        current_opinion: float = 0.0
    ) -> TPBResult:
        """
        预测具体行为
        
        Args:
            intention: 行为意向 [-1, 1]
            attitude: 态度 [-1, 1]
            subjective_norm: 主观规范 [-1, 1]
            perceived_control: 知觉行为控制 [0, 1]
            current_opinion: 当前观点值（辅助判断）
        
        Returns:
            TPBResult 包含预测行为和置信度
        """
        # 行为判定逻辑（issue #618: 使用参数化阈值）
        if intention > self.share_threshold:
            if attitude > self.attitude_share_threshold and perceived_control > self.control_share_threshold:
                predicted = BehaviorType.SHARE
            elif abs(current_opinion) > self.opinion_comment_threshold:
                predicted = BehaviorType.COMMENT
            else:
                predicted = BehaviorType.OBSERVE

        elif intention > self.verify_threshold:
            if perceived_control > self.control_verify_threshold:
                predicted = BehaviorType.VERIFY
            else:
                predicted = BehaviorType.OBSERVE

        elif intention > self.silence_threshold:
            if subjective_norm < self.norm_silence_threshold:
                predicted = BehaviorType.SILENCE
            else:
                predicted = BehaviorType.OBSERVE
        
        else:
            predicted = BehaviorType.SILENCE
        
        # 置信度计算（态度和意向的一致性）
        attitude_intention_alignment = 1 - abs(attitude - intention) / 2
        control_factor = perceived_control
        confidence = attitude_intention_alignment * 0.6 + control_factor * 0.4
        
        return TPBResult(
            intention=intention,
            attitude=attitude,
            subjective_norm=subjective_norm,
            perceived_control=perceived_control,
            predicted_behavior=predicted,
            confidence=confidence
        )
    
    def compute_full(
        self,
        info_credibility: float,
        content_relevance: float,
        cognitive_dissonance: float,
        social_pressure: float,
        conformity_tendency: float,
        media_literacy: float,
        current_opinion: float = 0.0,
        neighbor_avg_opinion: Optional[float] = None
    ) -> TPBResult:
        """
        完整 TPB 计算

        Args:
            info_credibility: 信息可信度 [0, 1]
            content_relevance: 内容相关性 [0, 1]
            cognitive_dissonance: 认知失调成本 [0, 1]
            social_pressure: 社交压力 [0, 1]
            conformity_tendency: 从众倾向 [0, 1]
            media_literacy: 媒介素养 [0, 1]
            current_opinion: 当前观点值
            neighbor_avg_opinion: 邻居平均观点值（用于主观规范方向）

        Returns:
            TPBResult
        """
        # 1. 态度计算
        attitude = info_credibility * content_relevance - cognitive_dissonance
        attitude = max(-1.0, min(1.0, attitude))

        # 2. 主观规范计算
        # 社交压力方向由邻居/舆论气候决定（改进：不再仅依赖自己观点）
        # 如果没有邻居信息，退化为基于自身观点（向后兼容）
        reference_opinion = neighbor_avg_opinion if neighbor_avg_opinion is not None else current_opinion
        norm_direction = 1 if reference_opinion > 0 else -1
        subjective_norm = norm_direction * social_pressure * conformity_tendency
        subjective_norm = max(-1.0, min(1.0, subjective_norm))

        # 3. 知觉行为控制计算
        perceived_control = media_literacy * 0.6 + content_relevance * 0.4

        # 4. 行为意向
        intention = self.compute_intention(attitude, subjective_norm, perceived_control)

        # 5. 预测行为
        return self.predict_behavior(
            intention, attitude, subjective_norm, perceived_control, current_opinion
        )
    
    @classmethod
    def for_high_conformity(cls) -> "TheoryOfPlannedBehavior":
        """创建高从众型 Agent 的 TPB 模型"""
        return cls(
            attitude_weight=0.25,
            norm_weight=0.50,
            control_weight=0.25
        )
    
    @classmethod
    def for_independent_thinker(cls) -> "TheoryOfPlannedBehavior":
        """创建独立思考型 Agent 的 TPB 模型"""
        return cls(
            attitude_weight=0.5,
            norm_weight=0.2,
            control_weight=0.3
        )
    
    @classmethod
    def for_high_control(cls) -> "TheoryOfPlannedBehavior":
        """创建高自我效能型 Agent 的 TPB 模型"""
        return cls(
            attitude_weight=0.3,
            norm_weight=0.25,
            control_weight=0.45
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "weights": {
                "attitude": self.attitude_weight,
                "norm": self.norm_weight,
                "control": self.control_weight
            },
            "thresholds": {
                "share": self.share_threshold,
                "silence": self.silence_threshold,
                "verify": self.verify_threshold
            }
        }

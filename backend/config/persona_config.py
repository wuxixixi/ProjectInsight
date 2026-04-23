"""
人设参数化配置

用于计算不同人设类型对信息的接受度和影响力
避免硬编码，便于调优
"""
import logging
from dataclasses import dataclass
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class PersonaWeights:
    """人设影响权重配置

    用于计算不同人设类型对信息的接受度和影响力
    """
    # 对权威信息的接受度 [0, 1]
    authority_acceptance: float = 0.7

    # 对误信的易感性 [0, 1]
    misbelief_susceptibility: float = 0.5

    # 对正确认知的接受度 [0, 1]
    positive_belief_acceptance: float = 0.6

    # 观点稳定性 [0, 1]，越高越难改变
    opinion_stability: float = 0.5

    # 社交影响力 [0, 1]
    social_influence: float = 0.5

    # 人设类型名称
    persona_type: str = "默认"

    # ---- 兼容属性访问器 ----
    # 旧字段名 rumor_susceptibility / truth_acceptance 仍可通过属性访问

    @property
    def rumor_susceptibility(self) -> float:
        """兼容旧字段名，映射到 misbelief_susceptibility"""
        return self.misbelief_susceptibility

    @rumor_susceptibility.setter
    def rumor_susceptibility(self, value: float) -> None:
        self.misbelief_susceptibility = value

    @property
    def truth_acceptance(self) -> float:
        """兼容旧字段名，映射到 positive_belief_acceptance"""
        return self.positive_belief_acceptance

    @truth_acceptance.setter
    def truth_acceptance(self, value: float) -> None:
        self.positive_belief_acceptance = value


# 预定义人设配置
PERSONA_CONFIGS: Dict[str, PersonaWeights] = {
    "意见领袖": PersonaWeights(
        authority_acceptance=0.9,
        misbelief_susceptibility=0.3,
        positive_belief_acceptance=0.8,
        opinion_stability=0.7,
        social_influence=0.9,
        persona_type="意见领袖"
    ),
    "怀疑论者": PersonaWeights(
        authority_acceptance=0.4,
        misbelief_susceptibility=0.2,
        positive_belief_acceptance=0.5,
        opinion_stability=0.8,
        social_influence=0.4,
        persona_type="怀疑论者"
    ),
    "从众者": PersonaWeights(
        authority_acceptance=0.7,
        misbelief_susceptibility=0.8,
        positive_belief_acceptance=0.7,
        opinion_stability=0.3,
        social_influence=0.3,
        persona_type="从众者"
    ),
    "理性派": PersonaWeights(
        authority_acceptance=0.6,
        misbelief_susceptibility=0.2,
        positive_belief_acceptance=0.9,
        opinion_stability=0.6,
        social_influence=0.5,
        persona_type="理性派"
    ),
    "激进派": PersonaWeights(
        authority_acceptance=0.3,
        misbelief_susceptibility=0.9,
        positive_belief_acceptance=0.3,
        opinion_stability=0.9,
        social_influence=0.7,
        persona_type="激进派"
    ),
    "中立观察者": PersonaWeights(
        authority_acceptance=0.5,
        misbelief_susceptibility=0.4,
        positive_belief_acceptance=0.5,
        opinion_stability=0.5,
        social_influence=0.3,
        persona_type="中立观察者"
    ),
    "官方发言": PersonaWeights(
        authority_acceptance=1.0,
        misbelief_susceptibility=0.1,
        positive_belief_acceptance=1.0,
        opinion_stability=0.95,
        social_influence=0.95,
        persona_type="官方发言"
    ),
    "媒体账号": PersonaWeights(
        authority_acceptance=0.8,
        misbelief_susceptibility=0.4,
        positive_belief_acceptance=0.7,
        opinion_stability=0.6,
        social_influence=0.85,
        persona_type="媒体账号"
    ),
    "普通用户": PersonaWeights(
        authority_acceptance=0.5,
        misbelief_susceptibility=0.5,
        positive_belief_acceptance=0.5,
        opinion_stability=0.5,
        social_influence=0.3,
        persona_type="普通用户"
    ),
}


def get_persona_weights(persona_type: str) -> PersonaWeights:
    """
    获取人设权重配置
    
    Args:
        persona_type: 人设类型名称
    
    Returns:
        对应的人设权重配置，未知类型返回默认配置
    """
    if persona_type in PERSONA_CONFIGS:
        return PERSONA_CONFIGS[persona_type]
    
    # 模糊匹配（限制最小匹配长度，避免单字误匹配，issue #852）
    min_match_len = 2
    if len(persona_type) >= min_match_len:
        for key, weights in PERSONA_CONFIGS.items():
            if (len(key) >= min_match_len and (key in persona_type or persona_type in key)):
                logger.debug(f"人设权重模糊匹配: '{persona_type}' → '{key}'")
                return weights
    
    # 返回默认配置
    return PersonaWeights(persona_type=persona_type)


def get_all_persona_types() -> list:
    """获取所有预定义人设类型"""
    return list(PERSONA_CONFIGS.keys())

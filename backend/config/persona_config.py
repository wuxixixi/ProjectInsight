"""
人设参数化配置

用于计算不同人设类型对信息的接受度和影响力
避免硬编码，便于调优
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class PersonaWeights:
    """人设影响权重配置
    
    用于计算不同人设类型对信息的接受度和影响力
    """
    # 对权威信息的接受度 [0, 1]
    authority_acceptance: float = 0.7
    
    # 对谣言的易感性 [0, 1]
    rumor_susceptibility: float = 0.5
    
    # 对真相的接受度 [0, 1]
    truth_acceptance: float = 0.6
    
    # 观点稳定性 [0, 1]，越高越难改变
    opinion_stability: float = 0.5
    
    # 社交影响力 [0, 1]
    social_influence: float = 0.5
    
    # 人设类型名称
    persona_type: str = "默认"


# 预定义人设配置
PERSONA_CONFIGS: Dict[str, PersonaWeights] = {
    "意见领袖": PersonaWeights(
        authority_acceptance=0.9,
        rumor_susceptibility=0.3,
        truth_acceptance=0.8,
        opinion_stability=0.7,
        social_influence=0.9,
        persona_type="意见领袖"
    ),
    "怀疑论者": PersonaWeights(
        authority_acceptance=0.4,
        rumor_susceptibility=0.2,
        truth_acceptance=0.5,
        opinion_stability=0.8,
        social_influence=0.4,
        persona_type="怀疑论者"
    ),
    "从众者": PersonaWeights(
        authority_acceptance=0.7,
        rumor_susceptibility=0.8,
        truth_acceptance=0.7,
        opinion_stability=0.3,
        social_influence=0.3,
        persona_type="从众者"
    ),
    "理性派": PersonaWeights(
        authority_acceptance=0.6,
        rumor_susceptibility=0.2,
        truth_acceptance=0.9,
        opinion_stability=0.6,
        social_influence=0.5,
        persona_type="理性派"
    ),
    "激进派": PersonaWeights(
        authority_acceptance=0.3,
        rumor_susceptibility=0.9,
        truth_acceptance=0.3,
        opinion_stability=0.9,
        social_influence=0.7,
        persona_type="激进派"
    ),
    "中立观察者": PersonaWeights(
        authority_acceptance=0.5,
        rumor_susceptibility=0.4,
        truth_acceptance=0.5,
        opinion_stability=0.5,
        social_influence=0.3,
        persona_type="中立观察者"
    ),
    "官方发言": PersonaWeights(
        authority_acceptance=1.0,
        rumor_susceptibility=0.1,
        truth_acceptance=1.0,
        opinion_stability=0.95,
        social_influence=0.95,
        persona_type="官方发言"
    ),
    "媒体账号": PersonaWeights(
        authority_acceptance=0.8,
        rumor_susceptibility=0.4,
        truth_acceptance=0.7,
        opinion_stability=0.6,
        social_influence=0.85,
        persona_type="媒体账号"
    ),
    "普通用户": PersonaWeights(
        authority_acceptance=0.5,
        rumor_susceptibility=0.5,
        truth_acceptance=0.5,
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
    
    # 模糊匹配
    for key, weights in PERSONA_CONFIGS.items():
        if key in persona_type or persona_type in key:
            return weights
    
    # 返回默认配置
    return PersonaWeights(persona_type=persona_type)


def get_all_persona_types() -> list:
    """获取所有预定义人设类型"""
    return list(PERSONA_CONFIGS.keys())

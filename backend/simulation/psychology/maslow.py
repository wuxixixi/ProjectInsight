"""
NeedsHierarchy - 马斯洛需求层次模型

将人类的五层需求映射到信息接受行为:
1. 生理需求: 基本生存信息
2. 安全需求: 风险预警、威胁信息
3. 社交需求: 归属感、认同信息
4. 尊重需求: 地位、成就信息
5. 认知需求: 真相、知识信息

关键洞察:
- 低层次需求未满足时，更容易接受负面/威胁类信息
- 高层次需求主导时，更趋向理性分析
- 需求层次与观点易感性相关
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NeedLevel(str, Enum):
    """马斯洛需求层次"""
    PHYSIOLOGICAL = "生理"  # 生理需求（底层）
    SAFETY = "安全"               # 安全需求
    LOVE = "社交"                   # 社交需求（归属与爱）
    ESTEEM = "尊重"               # 尊重需求
    COGNITIVE = "认知"         # 认知需求（顶层）


class NeedState(BaseModel):
    """单个需求层次的状态"""
    level: NeedLevel
    satisfaction: float = Field(0.5, ge=0.0, le=1.0, description="满足程度")
    urgency: float = Field(0.5, ge=0.0, le=1.0, description="紧迫程度")


class NeedsHierarchy(BaseModel):
    """
    马斯洛需求层次模型
    
    核心假设:
    - 需求满足度影响信息选择性注意
    - 低层次需求未满足 → 更易接受威胁性信息
    - 高层次需求满足 → 更具批判性思维
    
    应用于舆情:
    - 安全需求高的群体对负面信息更敏感
    - 社交需求高的群体更易受从众压力影响
    - 认知需求高的群体更理性分析
    """
    
    # 五层需求状态
    physiological: float = Field(0.8, ge=0.0, le=1.0, description="生理需求满足度")
    safety: float = Field(0.6, ge=0.0, le=1.0, description="安全需求满足度")
    love: float = Field(0.5, ge=0.0, le=1.0, description="社交需求满足度")
    esteem: float = Field(0.5, ge=0.0, le=1.0, description="尊重需求满足度")
    cognitive: float = Field(0.5, ge=0.0, le=1.0, description="认知需求满足度")
    
    # 当前主导需求（最低满足度的未满足层次）
    dominant_level: NeedLevel = Field(NeedLevel.SAFETY, description="主导需求层次")
    
    def compute_dominant_level(self) -> NeedLevel:
        """
        计算主导需求层次
        
        规则: 找出满足度最低的层次
        越不满足，越主导行为
        
        Returns:
            主导需求层次
        """
        levels = [
            (NeedLevel.PHYSIOLOGICAL, self.physiological),
            (NeedLevel.SAFETY, self.safety),
            (NeedLevel.LOVE, self.love),
            (NeedLevel.ESTEEM, self.esteem),
            (NeedLevel.COGNITIVE, self.cognitive),
        ]
        
        # 选择满足度最低的层次
        min_level = min(levels, key=lambda x: x[1])
        self.dominant_level = min_level[0]
        return self.dominant_level
    
    def compute_information_receptivity(self, content_type: str) -> float:
        """
        计算信息接受度
        
        不同类型信息与需求层次的匹配影响接受度
        
        Args:
            content_type: 信息类型
                - "threat": 威胁/负面信息
                - "social": 社交/归属信息
                - "status": 地位/成就信息
                - "knowledge": 知识/真相信息
        
        Returns:
            接受度系数 [0.5, 1.5]
        """
        self.compute_dominant_level()
        
        # 需求-内容匹配矩阵
        # 行: 主导需求层次, 列: 内容类型
        match_matrix = {
            NeedLevel.PHYSIOLOGICAL: {
                "threat": 1.5, "social": 1.0, "status": 0.8, "knowledge": 0.7
            },
            NeedLevel.SAFETY: {
                "threat": 1.4, "social": 1.1, "status": 0.9, "knowledge": 0.8
            },
            NeedLevel.LOVE: {
                "threat": 1.0, "social": 1.4, "status": 1.1, "knowledge": 0.9
            },
            NeedLevel.ESTEEM: {
                "threat": 0.8, "social": 1.2, "status": 1.4, "knowledge": 1.0
            },
            NeedLevel.COGNITIVE: {
                "threat": 0.7, "social": 0.9, "status": 1.0, "knowledge": 1.4
            },
        }
        
        base_receptivity = match_matrix.get(self.dominant_level, {}).get(content_type, 1.0)
        
        # 考虑整体需求满足度
        avg_satisfaction = (
            self.physiological + self.safety + self.love + 
            self.esteem + self.cognitive
        ) / 5
        
        # 需求未满足程度 → 信息敏感度提升
        deprivation_factor = 1 + (1 - avg_satisfaction) * 0.3
        
        return min(1.5, base_receptivity * deprivation_factor)
    
    def compute_opinion_change_factor(self) -> float:
        """
        计算观点变化能力
        
        高层次需求满足 → 更有能力理性分析 → 观点更有弹性
        低层次需求主导 → 更冲动接受 → 但也更容易被新信息改变
        
        Returns:
            观点变化因子 [0.5, 1.5]
        """
        level_order = [
            NeedLevel.PHYSIOLOGICAL,
            NeedLevel.SAFETY,
            NeedLevel.LOVE,
            NeedLevel.ESTEEM,
            NeedLevel.COGNITIVE
        ]
        
        dominant_index = level_order.index(self.dominant_level)
        
        # 低层次主导 → 变化因子较高（易受影响）
        # 高层次主导 → 变化因子适中（理性分析）
        # 中间层次 → 变化因子最高（社交压力敏感）
        
        if dominant_index <= 1:  # 生理/安全
            return 1.3  # 易受影响
        elif dominant_index == 2:  # 社交
            return 1.4  # 最易受社交影响
        elif dominant_index == 3:  # 尊重
            return 1.1
        else:  # 认知
            return 0.9  # 更理性，变化幅度小
    
    def get_description(self) -> str:
        """获取人设描述"""
        descriptions = {
            NeedLevel.PHYSIOLOGICAL: "基本生存需求主导，对任何信息都高度敏感",
            NeedLevel.SAFETY: "安全需求主导，对威胁性信息高度警惕",
            NeedLevel.LOVE: "社交需求主导，渴望归属感，易受群体影响",
            NeedLevel.ESTEEM: "尊重需求主导，关注地位和认可",
            NeedLevel.COGNITIVE: "认知需求主导，追求真相和理性分析",
        }
        return descriptions.get(self.dominant_level, "")
    
    @classmethod
    def from_agent_traits(
        cls,
        agent_id: int,
        fear_of_isolation: float,
        susceptibility: float,
        influence: float,
        mapping_config: Optional[Dict[str, float]] = None
    ) -> "NeedsHierarchy":
        """
        从 Agent 特征推断需求层次

        Args:
            agent_id: Agent ID（用于随机种子）
            fear_of_isolation: 孤立恐惧（映射到社交需求）
            susceptibility: 易感性（映射到安全需求）
            influence: 影响力（映射到尊重需求）
            mapping_config: 映射系数配置，覆盖默认值。格式:
                {
                    "safety_base": 0.55, "safety_susceptibility": -0.35,
                    "love_base": 0.45, "love_fear": -0.3,
                    "esteem_base": 0.35, "esteem_influence": 0.45,
                    "cognitive_base": 0.40, "physiological_base": 0.82
                }

        Returns:
            需求层次模型

        Note:
            映射公式为简化线性模型，假设关系为单调近似。
            系数缺乏直接实证支撑，仅作为理论到模型的桥梁假设。
            可通过 mapping_config 参数覆盖默认系数以适配不同场景。
        """
        import random
        import time

        # 默认映射系数（可被 mapping_config 覆盖）
        cfg = {
            "safety_base": 0.55, "safety_susceptibility": -0.35,
            "love_base": 0.45, "love_fear": -0.3,
            "esteem_base": 0.35, "esteem_influence": 0.45,
            "cognitive_base": 0.40, "physiological_base": 0.82,
        }
        if mapping_config:
            cfg.update(mapping_config)

        # 每个个体有独特的随机种子（agent_id + 时间戳微秒）
        base_seed = int(time.time() * 1000) % 100000
        seed = (agent_id * 10007 + base_seed) % (2**31)
        rng = random.Random(seed)

        # 个体差异化扰动
        noise = rng.uniform(-0.15, 0.15)
        cognitive_noise = rng.uniform(-0.25, 0.3)

        # 反向映射：高恐惧/易感性 = 需求未满足 = 低满足度
        safety = max(0.15, min(0.9, cfg["safety_base"] + susceptibility * cfg["safety_susceptibility"] + noise))
        love = max(0.15, min(0.9, cfg["love_base"] + fear_of_isolation * cfg["love_fear"] + noise))
        esteem = max(0.15, min(0.9, cfg["esteem_base"] + influence * cfg["esteem_influence"] + noise))
        cognitive = max(0.15, min(0.9, cfg["cognitive_base"] + cognitive_noise))

        # 生理需求基本满足（现代人都吃饱了）
        physiological = max(0.7, min(0.95, cfg["physiological_base"] + noise * 0.5))

        hierarchy = cls(
            physiological=physiological,
            safety=safety,
            love=love,
            esteem=esteem,
            cognitive=cognitive
        )

        hierarchy.compute_dominant_level()
        return hierarchy
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "physiological": self.physiological,
            "safety": self.safety,
            "love": self.love,
            "esteem": self.esteem,
            "cognitive": self.cognitive,
            "dominant_level": self.dominant_level.value,
            "description": self.get_description()
        }

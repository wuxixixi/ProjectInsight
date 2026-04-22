"""
Skill Pipeline Module - 技能管道系统

核心模式: 元数据优先 + 懒加载
- SKILL.yaml 定义技能元数据
- 按需加载技能实现
- 优先级顺序执行
"""

from .base import SkillBase, SkillMetadata, SkillContext, SkillResult
from .loader import SkillLoader

# 导入内建技能以触发注册装饰器
from .observation import ObservationSkill
from .memory_skill import MemorySkill
from .needs import NeedsSkill
from .cognition import CognitionSkill
from .plan import PlanSkill

__all__ = [
    "SkillBase",
    "SkillMetadata",
    "SkillContext",
    "SkillResult",
    "SkillLoader",
    "ObservationSkill",
    "MemorySkill",
    "NeedsSkill",
    "CognitionSkill",
    "PlanSkill",
]

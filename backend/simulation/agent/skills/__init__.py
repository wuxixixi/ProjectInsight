"""
Skill Pipeline Module - 技能管道系统

核心模式: 元数据优先 + 注册制
- 技能类通过装饰器自动注册到 SkillLoader
- 按优先级顺序执行
- 导入时即触发注册，非懒加载
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

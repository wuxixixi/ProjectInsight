# Backend config module
from types import MappingProxyType
from .persona_config import PersonaWeights, PERSONA_CONFIGS as _PERSONA_CONFIGS, get_persona_weights

# 导出不可变视图，防止意外修改全局配置（issue #931）
PERSONA_CONFIGS = MappingProxyType(_PERSONA_CONFIGS)

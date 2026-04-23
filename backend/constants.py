"""
全局常量定义

此模块不依赖 backend 内部任何模块，可被任意模块安全导入。
"""

# 观点分类阈值（统一使用，确保跨模块一致）
OPINION_THRESHOLD_NEGATIVE = -0.1  # 低于此值为误信负面信息
OPINION_THRESHOLD_POSITIVE = 0.1   # 高于此值为正确认知

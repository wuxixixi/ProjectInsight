"""
全局状态管理

集中管理推演引擎及相关的全局状态，替代模块级散落的全局变量。
"""
from typing import Optional, Dict, Any

from .simulation.engine import SimulationEngine
from .simulation.prediction import PredictionModel

# ==================== 核心状态 ====================

engine: Optional[SimulationEngine] = None

# 待注入的事件/知识图谱（推演开始前可预先准备）
pending_knowledge_graph: Optional[Dict[str, Any]] = None
pending_event_content: Optional[str] = None
pending_event_source: Optional[str] = None

# 事件注入进行中标志（推演时检查，暂停推演）
injection_in_progress: bool = False

# 预测模型
prediction_model: Optional[PredictionModel] = None

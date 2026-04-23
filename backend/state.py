"""
全局状态管理

集中管理推演引擎及相关的全局状态，替代模块级散落的全局变量。
支持线程安全的多用户并发访问。

使用方式（完全兼容旧代码）:
  from backend import state
  state.engine           # 线程安全读取
  state.engine = X       # 线程安全写入
  state.reset_state()    # 重置所有状态
"""
import sys
import threading
from typing import Optional, Dict, Any
from contextlib import contextmanager

from .simulation.engine import SimulationEngine
from .simulation.prediction import PredictionModel

_STATE_ATTRS = frozenset({
    "engine", "pending_knowledge_graph", "pending_event_content",
    "pending_event_source", "injection_in_progress", "prediction_model"
})


class GlobalState:
    """
    线程安全的全局状态管理器

    使用 RLock 保护所有状态读写，支持多线程并发。
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._engine: Optional[SimulationEngine] = None
        self._pending_knowledge_graph: Optional[Dict[str, Any]] = None
        self._pending_event_content: Optional[str] = None
        self._pending_event_source: Optional[str] = None
        self._injection_in_progress: bool = False
        self._prediction_model: Optional[PredictionModel] = None

    @property
    def engine(self) -> Optional[SimulationEngine]:
        with self._lock:
            return self._engine

    @engine.setter
    def engine(self, value: Optional[SimulationEngine]):
        with self._lock:
            self._engine = value

    @property
    def pending_knowledge_graph(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._pending_knowledge_graph

    @pending_knowledge_graph.setter
    def pending_knowledge_graph(self, value: Optional[Dict[str, Any]]):
        with self._lock:
            self._pending_knowledge_graph = value

    @property
    def pending_event_content(self) -> Optional[str]:
        with self._lock:
            return self._pending_event_content

    @pending_event_content.setter
    def pending_event_content(self, value: Optional[str]):
        with self._lock:
            self._pending_event_content = value

    @property
    def pending_event_source(self) -> Optional[str]:
        with self._lock:
            return self._pending_event_source

    @pending_event_source.setter
    def pending_event_source(self, value: Optional[str]):
        with self._lock:
            self._pending_event_source = value

    @property
    def injection_in_progress(self) -> bool:
        with self._lock:
            return self._injection_in_progress

    @injection_in_progress.setter
    def injection_in_progress(self, value: bool):
        with self._lock:
            self._injection_in_progress = value

    @property
    def prediction_model(self) -> Optional[PredictionModel]:
        with self._lock:
            return self._prediction_model

    @prediction_model.setter
    def prediction_model(self, value: Optional[PredictionModel]):
        with self._lock:
            self._prediction_model = value

    def reset(self):
        """重置所有状态"""
        with self._lock:
            self._engine = None
            self._pending_knowledge_graph = None
            self._pending_event_content = None
            self._pending_event_source = None
            self._injection_in_progress = False
            self._prediction_model = None

    @contextmanager
    def write_lock(self):
        """获取写锁的上下文管理器，用于批量原子操作"""
        with self._lock:
            yield self

    def get_snapshot(self) -> Dict[str, Any]:
        """获取当前状态的只读快照"""
        with self._lock:
            return {
                "has_engine": self._engine is not None,
                "has_pending_kg": self._pending_knowledge_graph is not None,
                "has_pending_event": self._pending_event_content is not None,
                "injection_in_progress": self._injection_in_progress,
                "has_prediction_model": self._prediction_model is not None,
            }


# 全局状态实例
_state = GlobalState()


# ==================== 便捷函数 ====================

def get_state() -> GlobalState:
    """获取全局状态管理器实例"""
    return _state


def reset_state():
    """重置所有全局状态（线程安全）"""
    _state.reset()


# ==================== 模块属性代理 ====================

class _StateModule(sys.modules[__name__].__class__):
    """模块子类，拦截属性读写以实现线程安全"""

    def __getattr__(self, name):
        if name in _STATE_ATTRS:
            return getattr(_state, name)
        raise AttributeError(f"module {self.__name__!r} has no attribute {name!r}")

    def __setattr__(self, name, value):
        if name in _STATE_ATTRS:
            setattr(_state, name, value)
        else:
            super().__setattr__(name, value)


# 替换模块实例
_original_module = sys.modules[__name__]
_new_module = _StateModule(__name__)
# 复制所有非状态属性到新模块（包括函数）
# 使用 dict() 创建完整副本以避免迭代时修改问题
_original_dict_copy = dict(_original_module.__dict__)
for k, v in _original_dict_copy.items():
    if k not in _STATE_ATTRS and not k.startswith('__'):
        setattr(_new_module, k, v)
sys.modules[__name__] = _new_module

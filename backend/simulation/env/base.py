"""
EnvBase - 环境模块基类

定义环境工具的标准接口:
- @tool 装饰器: 标注可调用方法
- EnvBase 抽象类: 定义环境模块接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio
import functools
import logging

logger = logging.getLogger(__name__)


class ToolKind(str, Enum):
    """工具类型"""
    OBSERVE = "observe"      # 感知类（只读）
    STATISTICS = "statistics"  # 统计类（只读）
    INTERACT = "interact"    # 交互类（可写）


@dataclass
class EnvTool:
    """环境工具描述"""
    name: str
    description: str
    kind: ToolKind
    readonly: bool
    parameters: Dict[str, Any]
    func: Callable


def tool(readonly: bool = True, kind: str = "observe"):
    """
    环境工具装饰器
    
    标注方法为可被 Agent 调用的环境工具
    
    Args:
        readonly: 是否只读（不修改环境状态）
        kind: 工具类型 (observe/statistics/interact)
    
    Example:
        @tool(readonly=True, kind="observe")
        async def get_recommendation(self, agent_id: int) -> str:
            return "推荐内容..."
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

        # 添加元数据
        wrapper._is_tool = True
        wrapper._readonly = readonly
        wrapper._kind = ToolKind(kind)

        return wrapper
    return decorator


class EnvBase(ABC):
    """
    环境模块抽象基类
    
    所有环境模块必须实现:
    - name: 环境名称
    - get_tools(): 返回可调用工具列表
    - reset(): 重置环境状态
    
    子类通过 @tool 装饰器标注可调用方法
    """
    
    def __init__(self):
        self._tools: Dict[str, EnvTool] = {}
        self._scan_tools()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """环境名称"""
        pass
    
    def _scan_tools(self):
        """扫描并注册带 @tool 装饰器的方法"""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, '_is_tool'):
                # 收集参数信息
                import inspect
                sig = inspect.signature(attr)
                params = {
                    name: param.annotation.__name__ if hasattr(param.annotation, '__name__') else str(param.annotation)
                    for name, param in sig.parameters.items()
                    if name != 'self'
                }
                
                self._tools[attr_name] = EnvTool(
                    name=f"{self.name}_{attr_name}",
                    description=attr.__doc__ or "",
                    kind=attr._kind,
                    readonly=attr._readonly,
                    parameters=params,
                    func=attr
                )
    
    def get_tools(self) -> List[EnvTool]:
        """获取所有可用工具"""
        return list(self._tools.values())
    
    def get_tool(self, name: str) -> Optional[EnvTool]:
        """获取指定工具"""
        return self._tools.get(name)
    
    async def call_tool(self, name: str, *args, **kwargs) -> Any:
        """调用工具"""
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Tool {name} not found in {self.name}")
        
        return await tool.func(*args, **kwargs)
    
    @abstractmethod
    async def reset(self):
        """重置环境状态"""
        pass
    
    @abstractmethod
    async def get_state(self) -> Dict[str, Any]:
        """获取环境状态"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "name": self.name,
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "kind": t.kind.value,
                    "readonly": t.readonly
                }
                for t in self._tools.values()
            ]
        }

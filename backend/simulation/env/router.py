"""
EnvRouter - 环境路由

ReAct式环境路由，统一访问所有环境模块:
- 收集各环境工具
- LLM 生成工具调用决策
- 统一执行并返回结果
"""
import asyncio
from typing import Dict, List, Any, Optional
import logging

from .base import EnvBase, EnvTool, ToolKind
from .algorithm_env import AlgorithmEnv
from .social_env import SocialEnv
from .truth_env import TruthEnv

logger = logging.getLogger(__name__)


class EnvRouter:
    """
    环境路由器
    
    统一管理所有环境模块:
    - AlgorithmEnv: 算法推荐
    - SocialEnv: 社交网络
    - TruthEnv: 官方辟谣
    
    提供:
    - ask(): Agent 向环境提问
    - collect_tools(): 收集所有可用工具
    - call(): 执行工具调用
    """
    
    def __init__(
        self,
        algorithm_env: Optional[AlgorithmEnv] = None,
        social_env: Optional[SocialEnv] = None,
        truth_env: Optional[TruthEnv] = None
    ):
        self._envs: Dict[str, EnvBase] = {}
        
        # 初始化环境模块
        if algorithm_env:
            self._envs["algorithm"] = algorithm_env
        if social_env:
            self._envs["social"] = social_env
        if truth_env:
            self._envs["truth"] = truth_env
    
    def register_env(self, name: str, env: EnvBase):
        """注册环境模块"""
        self._envs[name] = env
    
    def get_env(self, name: str) -> Optional[EnvBase]:
        """获取环境模块"""
        return self._envs.get(name)
    
    @property
    def algorithm(self) -> Optional[AlgorithmEnv]:
        """快捷访问算法环境"""
        return self._envs.get("algorithm")
    
    @property
    def social(self) -> Optional[SocialEnv]:
        """快捷访问社交环境"""
        return self._envs.get("social")
    
    @property
    def truth(self) -> Optional[TruthEnv]:
        """快捷访问辟谣环境"""
        return self._envs.get("truth")
    
    def collect_tools(self, readonly_only: bool = True) -> List[EnvTool]:
        """
        收集所有可用工具
        
        Args:
            readonly_only: 是否只收集只读工具
        
        Returns:
            工具列表
        """
        tools = []
        for env_name, env in self._envs.items():
            for tool in env.get_tools():
                if readonly_only and not tool.readonly:
                    continue
                tools.append(tool)
        return tools
    
    def get_tool_schema(self, readonly_only: bool = True) -> List[Dict[str, Any]]:
        """
        获取工具 JSON Schema（用于 LLM 工具调用）
        
        Args:
            readonly_only: 是否只包含只读工具
        
        Returns:
            工具 Schema 列表
        """
        tools = self.collect_tools(readonly_only)
        return [
            {
                "name": t.name,
                "description": t.description,
                "kind": t.kind.value,
                "parameters": t.parameters
            }
            for t in tools
        ]
    
    async def ask(
        self,
        agent_id: int,
        opinion: float,
        readonly: bool = True
    ) -> Dict[str, Any]:
        """
        Agent 向环境提问

        收集所有环境信息，返回综合感知结果
        使用 asyncio.gather 并行调用各环境，提升性能

        Args:
            agent_id: Agent ID
            opinion: 当前观点
            readonly: 是否只读模式

        Returns:
            综合感知结果
        """
        result = {
            "algorithm": None,
            "social": None,
            "truth": None
        }

        async def call_algorithm():
            if "algorithm" not in self._envs:
                return None
            try:
                content = await self._envs["algorithm"].call_tool(
                    "observe", agent_id, opinion
                )
                return {"content": content, "source": "algorithm"}
            except Exception as e:
                logger.error(f"AlgorithmEnv observe failed: {e}")
                return None

        async def call_social():
            if "social" not in self._envs:
                return None
            try:
                peer_opinions = await self._envs["social"].call_tool(
                    "get_peer_opinions", agent_id
                )
                return {"peer_opinions": peer_opinions, "source": "social"}
            except Exception as e:
                logger.error(f"SocialEnv get_peer_opinions failed: {e}")
                return None

        async def call_truth():
            if "truth" not in self._envs:
                return None
            try:
                intervention = await self._envs["truth"].call_tool(
                    "get_intervention", agent_id
                )
                if intervention:
                    return {"content": intervention, "source": "truth"}
                return None
            except Exception as e:
                logger.error(f"TruthEnv get_intervention failed: {e}")
                return None

        # 并行调用所有环境
        algo_result, social_result, truth_result = await asyncio.gather(
            call_algorithm(),
            call_social(),
            call_truth()
        )

        result["algorithm"] = algo_result
        result["social"] = social_result
        result["truth"] = truth_result

        return result
    
    async def call(self, env_name: str, tool_name: str, *args, **kwargs) -> Any:
        """
        直接调用指定环境的工具
        
        Args:
            env_name: 环境名称
            tool_name: 工具名称
            *args, **kwargs: 工具参数
        
        Returns:
            工具执行结果
        """
        env = self._envs.get(env_name)
        if env is None:
            raise ValueError(f"Environment {env_name} not found")
        
        return await env.call_tool(tool_name, *args, **kwargs)
    
    async def reset_all(self):
        """重置所有环境"""
        for env in self._envs.values():
            await env.reset()
    
    async def get_all_states(self) -> Dict[str, Any]:
        """获取所有环境状态"""
        return {
            name: await env.get_state()
            for name, env in self._envs.items()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "environments": {
                name: env.to_dict()
                for name, env in self._envs.items()
            }
        }

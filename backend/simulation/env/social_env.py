"""
SocialEnv - 社交网络环境

模拟社交网络中的观点传播:
- 网络拓扑管理
- 影响力传播
- 意见领袖识别
- 社区检测
"""
from typing import Dict, List, Any, Optional, Tuple
import logging
import random

from .base import EnvBase, tool

logger = logging.getLogger(__name__)


class SocialEnv(EnvBase):
    """
    社交网络环境
    
    管理:
    - 网络拓扑 (邻接表)
    - 影响力矩阵
    - 邻居观点收集
    - 意见领袖识别
    """
    
    def __init__(
        self,
        adjacency: Optional[Dict[int, List[int]]] = None,
        influence: Optional[Dict[int, float]] = None
    ):
        super().__init__()
        
        # 网络拓扑: agent_id -> [neighbor_ids]
        self._adjacency: Dict[int, List[int]] = adjacency or {}
        
        # 影响力: agent_id -> influence_value
        self._influence: Dict[int, float] = influence or {}
        
        # 当前观点快照: agent_id -> opinion
        self._opinions: Dict[int, float] = {}
        
        # 消息传播记录
        self._message_log: List[Dict] = []
    
    @property
    def name(self) -> str:
        return "social"
    
    @tool(readonly=True, kind="observe")
    async def get_peer_opinions(self, agent_id: int) -> List[float]:
        """
        获取邻居观点
        
        Args:
            agent_id: Agent ID
        
        Returns:
            邻居观点列表
        """
        neighbors = self._adjacency.get(agent_id, [])
        return [self._opinions.get(n, 0.0) for n in neighbors]
    
    @tool(readonly=True, kind="observe")
    async def get_neighbors(self, agent_id: int) -> List[int]:
        """
        获取邻居列表
        
        Args:
            agent_id: Agent ID
        
        Returns:
            邻居 ID 列表
        """
        return self._adjacency.get(agent_id, [])
    
    @tool(readonly=True, kind="statistics")
    async def get_influencers(self, top_k: int = 5) -> List[Dict]:
        """
        获取意见领袖排名
        
        Args:
            top_k: 返回前 K 个
        
        Returns:
            意见领袖列表 [{agent_id, influence, opinion}]
        """
        sorted_agents = sorted(
            self._influence.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {
                "agent_id": aid,
                "influence": inf,
                "opinion": self._opinions.get(aid, 0.0),
                "neighbor_count": len(self._adjacency.get(aid, []))
            }
            for aid, inf in sorted_agents[:top_k]
        ]
    
    @tool(readonly=True, kind="statistics")
    async def get_network_stats(self) -> Dict[str, Any]:
        """
        获取网络统计信息
        
        Returns:
            网络统计数据
        """
        node_count = len(self._adjacency)
        edge_count = sum(len(n) for n in self._adjacency.values()) // 2
        
        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "avg_degree": edge_count * 2 / node_count if node_count > 0 else 0,
            "opinion_mean": sum(self._opinions.values()) / len(self._opinions) if self._opinions else 0,
            "opinion_std": self._compute_opinion_std()
        }
    
    @tool(readonly=True, kind="observe")
    async def get_majority_opinion(self, agent_id: int, threshold: float = 0.1, discrete: bool = False) -> float:
        """
        获取主流观点（邻居平均观点）

        Args:
            agent_id: Agent ID
            threshold: 离散模式下判断方向性的阈值
            discrete: 是否返回离散值 (-1, 0, 1)，默认返回连续值

        Returns:
            主流观点值 (连续: [-1, 1], 离散: -1/0/1)
        """
        neighbors = self._adjacency.get(agent_id, [])
        if not neighbors:
            return 0.0

        neighbor_opinions = [self._opinions.get(n, 0.0) for n in neighbors]
        avg = sum(neighbor_opinions) / len(neighbor_opinions)

        if discrete:
            if avg > threshold:
                return 1.0
            elif avg < -threshold:
                return -1.0
            else:
                return 0.0

        return avg

    @tool(readonly=True, kind="observe")
    async def get_average_neighbor_opinion(self, agent_id: int) -> float:
        """
        获取邻居的平均观点值（连续值）

        Args:
            agent_id: Agent ID

        Returns:
            邻居平均观点值 [-1, 1]
        """
        neighbors = self._adjacency.get(agent_id, [])
        if not neighbors:
            return 0.0

        neighbor_opinions = [self._opinions.get(n, 0.0) for n in neighbors]
        return sum(neighbor_opinions) / len(neighbor_opinions)
    
    @tool(readonly=False, kind="interact")
    async def broadcast(self, agent_id: int, content: str, opinion: float):
        """
        Agent 广播消息到邻居
        
        Args:
            agent_id: 发送者 ID
            content: 消息内容
            opinion: 发送时观点
        """
        neighbors = self._adjacency.get(agent_id, [])
        
        # 记录消息
        self._message_log.append({
            "sender": agent_id,
            "receivers": neighbors,
            "content": content,
            "opinion": opinion
        })
    
    @tool(readonly=False, kind="interact")
    async def update_opinion(self, agent_id: int, opinion: float):
        """
        更新 Agent 观点快照
        
        Args:
            agent_id: Agent ID
            opinion: 新观点值
        """
        self._opinions[agent_id] = opinion
    
    def set_network(
        self,
        adjacency: Dict[int, List[int]],
        influence: Dict[int, float],
        opinions: Dict[int, float]
    ):
        """
        设置网络数据（由 Engine 调用）
        
        Args:
            adjacency: 邻接表
            influence: 影响力字典
            opinions: 观点字典
        """
        self._adjacency = adjacency
        self._influence = influence
        self._opinions = opinions
    
    def _compute_opinion_std(self) -> float:
        """计算观点标准差"""
        if not self._opinions:
            return 0.0
        
        values = list(self._opinions.values())
        avg = sum(values) / len(values)
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        return variance ** 0.5
    
    async def reset(self):
        """重置环境状态"""
        self._opinions.clear()
        self._message_log.clear()
    
    async def get_state(self) -> Dict[str, Any]:
        """获取环境状态"""
        return {
            "node_count": len(self._adjacency),
            "opinion_count": len(self._opinions),
            "message_count": len(self._message_log)
        }

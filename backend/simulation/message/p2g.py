"""
P2G Broadcaster - Agent 广播通信

实现一对多通信:
- 意见领袖广播
- 覆盖范围控制
- 影响力衰减
"""
from typing import Dict, List, Optional
import random
import math
import logging

from .models import Message, MessageType, MessageStatus

logger = logging.getLogger(__name__)


class P2GBroadcaster:
    """
    P2G 广播器

    管理意见领袖向群体的广播:
    - 一次广播影响多个邻居
    - 覆盖范围由影响力决定
    - 影响力随距离衰减
    """

    def __init__(
        self,
        seed: int = 42,
        # 传播概率参数 (issue #321)
        influence_coefficient: float = 0.7,
        # 影响力衰减参数 (issue #361)
        decay_rate: float = 0.15,
        max_distance: int = 3
    ):
        # 广播日志
        self._log: List[Message] = []

        # 邻接表（由 SocialEnv 提供）
        self._adjacency: Dict[int, List[int]] = {}

        # 实例级随机生成器
        self._rng = random.Random(seed)

        # 传播概率参数
        self._influence_coeff = influence_coefficient

        # 衰减参数
        self._decay_rate = decay_rate
        self._max_distance = max_distance
    
    def set_adjacency(self, adjacency: Dict[int, List[int]]):
        """设置网络邻接表"""
        self._adjacency = adjacency
    
    async def broadcast(
        self,
        sender_id: int,
        content: str,
        opinion: Optional[float] = None,
        influence: float = 0.5,
        reach: float = 0.8
    ) -> Message:
        """
        广播消息
        
        Args:
            sender_id: 发送者 ID
            content: 消息内容
            opinion: 发送时观点
            influence: 发送者影响力
            reach: 覆盖范围 [0, 1]
        
        Returns:
            广播消息
        """
        # 确定接收者
        neighbors = self._adjacency.get(sender_id, [])
        
        # 根据影响力和覆盖范围筛选
        actual_reach = min(1.0, influence * reach)
        max_receivers = max(1, int(len(neighbors) * actual_reach))
        
        # 随机选择接收者
        receivers = self._rng.sample(neighbors, min(max_receivers, len(neighbors))) if neighbors else []

        message = Message(
            message_type=MessageType.P2G,
            sender_id=sender_id,
            receiver_ids=receivers,
            content=content,
            opinion=opinion,
            credibility=influence,
            propagation_prob=influence * self._influence_coeff,
            status=MessageStatus.SENT
        )
        
        self._log.append(message)
        
        logger.debug(
            f"P2G broadcast from {sender_id} to {len(receivers)} agents "
            f"(influence={influence:.2f}, reach={actual_reach:.2f})"
        )
        
        return message
    
    async def receive_broadcast(
        self,
        message: Message,
        receiver_id: int,
        distance: int = 1
    ) -> bool:
        """
        接收广播消息

        考虑传播概率和影响力衰减

        Args:
            message: 广播消息
            receiver_id: 接收者 ID
            distance: 网络距离（跳数），默认为1表示直接邻居

        Returns:
            是否成功接收
        """
        if receiver_id not in message.receiver_ids:
            return False

        # 基础传播概率
        base_prob = message.propagation_prob

        # 影响力随距离衰减 (issue #361)
        # 使用指数衰减: decay_factor = exp(-decay_rate * (distance - 1))
        if distance > 1:
            decay_factor = math.exp(-self._decay_rate * (distance - 1))
            effective_prob = base_prob * decay_factor
        else:
            effective_prob = base_prob

        received = self._rng.random() < effective_prob

        if received:
            message.status = MessageStatus.DELIVERED
        else:
            message.status = MessageStatus.FAILED

        return received
    
    def get_broadcast_stats(self) -> Dict:
        """获取广播统计"""
        if not self._log:
            return {"total": 0, "avg_reach": 0}
        
        total_receivers = sum(len(m.receiver_ids) for m in self._log)
        
        return {
            "total_broadcasts": len(self._log),
            "total_receivers": total_receivers,
            "avg_reach": total_receivers / len(self._log) if self._log else 0
        }
    
    def clear(self):
        """清空日志"""
        self._log.clear()

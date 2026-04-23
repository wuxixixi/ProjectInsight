"""
P2P Messenger - Agent 间私聊

实现点对点通信:
- 发送消息
- 传播概率计算
- 消息队列管理
"""
from typing import Dict, List, Optional, Tuple
import random
import logging

from .models import Message, MessageType, MessageStatus

logger = logging.getLogger(__name__)


class P2PMessenger:
    """
    P2P 通信器

    管理 Agent 间的一对一通信:
    - 消息发送和接收
    - 传播概率计算
    - 消息队列
    """

    def __init__(self, seed: int = 42):
        # 消息队列: receiver_id -> [Message]
        self._inbox: Dict[int, List[Message]] = {}

        # 消息日志
        self._log: List[Message] = []

        # 实例级随机生成器（确保可重现性）
        self._rng = random.Random(seed)
    
    async def send(
        self,
        sender_id: int,
        receiver_id: int,
        content: str,
        opinion: Optional[float] = None,
        sender_credibility: float = 0.5
    ) -> Message:
        """
        发送 P2P 消息
        
        Args:
            sender_id: 发送者 ID
            receiver_id: 接收者 ID
            content: 消息内容
            opinion: 发送时观点
            sender_credibility: 发送者可信度
        
        Returns:
            消息对象
        """
        message = Message(
            message_type=MessageType.P2P,
            sender_id=sender_id,
            receiver_ids=[receiver_id],
            content=content,
            opinion=opinion,
            credibility=sender_credibility,
            status=MessageStatus.SENT
        )
        
        # 计算传播概率
        message.propagation_prob = min(1.0, sender_credibility * 0.5 + 0.3)
        
        # 投递到收件箱
        if receiver_id not in self._inbox:
            self._inbox[receiver_id] = []
        self._inbox[receiver_id].append(message)
        
        # 记录日志
        self._log.append(message)
        
        return message
    
    async def receive(self, receiver_id: int) -> List[Message]:
        """
        接收消息
        
        Args:
            receiver_id: 接收者 ID
        
        Returns:
            消息列表
        """
        messages = self._inbox.get(receiver_id, [])
        
        # 根据传播概率过滤
        received = []
        for msg in messages:
            if self._rng.random() < msg.propagation_prob:
                msg.status = MessageStatus.DELIVERED
                received.append(msg)
            else:
                msg.status = MessageStatus.FAILED
        
        # 清空收件箱
        self._inbox[receiver_id] = []
        
        return received
    
    def compute_propagation_probability(
        self,
        sender_opinion: float,
        receiver_opinion: float,
        sender_strength: float,
        content_alignment: float
    ) -> float:
        """
        计算传播概率
        
        综合考虑:
        - 发送者可信度（信念强度）
        - 观点相似度
        - 内容匹配度
        
        Args:
            sender_opinion: 发送者观点
            receiver_opinion: 接收者观点
            sender_strength: 发送者信念强度
            content_alignment: 内容与接收者匹配度
        
        Returns:
            传播概率 [0, 1]
        """
        # 发送者可信度
        credibility = sender_strength * 0.5 + 0.5
        
        # 观点相似度
        similarity = 1 - abs(sender_opinion - receiver_opinion) / 2
        
        # 综合概率
        p = credibility * 0.3 + similarity * 0.4 + content_alignment * 0.3
        
        return max(0.0, min(1.0, p))
    
    def get_inbox_size(self, agent_id: int) -> int:
        """获取收件箱大小"""
        return len(self._inbox.get(agent_id, []))
    
    def get_log(self, limit: int = 100) -> List[Dict]:
        """获取消息日志"""
        return [m.to_dict() for m in self._log[-limit:]]
    
    def clear(self):
        """清空所有消息"""
        self._inbox.clear()
        self._log.clear()

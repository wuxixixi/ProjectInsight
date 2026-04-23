"""
GroupChat - 群组讨论

实现多 Agent 群组通信:
- 群组管理
- 多轮讨论
- 观点碰撞
- 社会验证效应
"""
from typing import Dict, List, Optional, Set
import random
import logging

from .models import Message, MessageType, MessageStatus

logger = logging.getLogger(__name__)


class ChatGroup:
    """讨论组"""
    
    def __init__(self, group_id: str, members: List[int], topic: str = ""):
        self.group_id = group_id
        self.members = set(members)
        self.topic = topic
        self.messages: List[Message] = []
        self.active = True
    
    def add_member(self, agent_id: int):
        self.members.add(agent_id)
    
    def remove_member(self, agent_id: int):
        self.members.discard(agent_id)
    
    def is_member(self, agent_id: int) -> bool:
        return agent_id in self.members
    
    def to_dict(self) -> Dict:
        return {
            "group_id": self.group_id,
            "member_count": len(self.members),
            "message_count": len(self.messages),
            "topic": self.topic,
            "active": self.active
        }


class GroupChat:
    """
    群组讨论管理器

    管理:
    - 群组创建和销毁
    - 消息路由
    - 社会验证效应
    - 观点碰撞检测
    """

    def __init__(
        self,
        opinion_clash_threshold: float = 0.2,
        validation_weight_agreement: float = 0.6,
        validation_weight_neutrality: float = 0.4
    ):
        """
        初始化群组讨论管理器

        Args:
            opinion_clash_threshold: 观点碰撞检测阈值，观点绝对值超过此值视为明显立场
            validation_weight_agreement: 社会验证中一致性权重
            validation_weight_neutrality: 社会验证中中立性权重
        """
        self.opinion_clash_threshold = opinion_clash_threshold
        self.validation_weight_agreement = validation_weight_agreement
        self.validation_weight_neutrality = validation_weight_neutrality

        # 群组: group_id -> ChatGroup
        self._groups: Dict[str, ChatGroup] = {}

        # 消息日志
        self._log: List[Message] = []
    
    def create_group(
        self,
        group_id: str,
        members: List[int],
        topic: str = ""
    ) -> ChatGroup:
        """
        创建讨论组
        
        Args:
            group_id: 群组 ID
            members: 成员列表
            topic: 讨论主题
        
        Returns:
            创建的群组
        """
        group = ChatGroup(group_id, members, topic)
        self._groups[group_id] = group
        
        logger.info(f"GroupChat: 创建群组 {group_id}，成员 {len(members)} 人")
        
        return group
    
    def get_group(self, group_id: str) -> Optional[ChatGroup]:
        """获取群组"""
        return self._groups.get(group_id)
    
    async def send_to_group(
        self,
        group_id: str,
        sender_id: int,
        content: str,
        opinion: Optional[float] = None
    ) -> Optional[Message]:
        """
        在群组中发送消息
        
        Args:
            group_id: 群组 ID
            sender_id: 发送者 ID
            content: 消息内容
            opinion: 发送时观点
        
        Returns:
            消息对象
        """
        group = self._groups.get(group_id)
        if group is None:
            logger.error(f"GroupChat: 群组 {group_id} 不存在")
            return None
        
        if not group.is_member(sender_id):
            logger.warning(f"GroupChat: Agent {sender_id} 不在群组 {group_id} 中")
            return None
        
        # 确定接收者（群内其他成员）
        receiver_ids = list(group.members - {sender_id})
        
        message = Message(
            message_type=MessageType.GROUP_CHAT,
            sender_id=sender_id,
            receiver_ids=receiver_ids,
            content=content,
            opinion=opinion,
            propagation_prob=0.7,
            status=MessageStatus.SENT
        )
        
        group.messages.append(message)
        self._log.append(message)
        
        return message
    
    async def receive_group_messages(
        self,
        group_id: str,
        receiver_id: int,
        max_count: int = 10
    ) -> List[Message]:
        """
        接收群组消息
        
        Args:
            group_id: 群组 ID
            receiver_id: 接收者 ID
            max_count: 最多接收条数
        
        Returns:
            消息列表
        """
        group = self._groups.get(group_id)
        if group is None or not group.is_member(receiver_id):
            return []
        
        # 获取发送给该用户的消息
        messages = [
            m for m in group.messages
            if receiver_id in m.receiver_ids and m.status != MessageStatus.READ
        ]
        
        # 根据传播概率过滤
        received = []
        for msg in messages[:max_count]:
            if random.random() < msg.propagation_prob:
                msg.status = MessageStatus.DELIVERED
                received.append(msg)
        
        return received
    
    def compute_social_validation(
        self,
        group_id: str,
        agent_id: int,
        agent_opinion: float
    ) -> Dict:
        """
        计算社会验证效应
        
        评估群组对 Agent 观点的验证程度
        
        Args:
            group_id: 群组 ID
            agent_id: Agent ID
            agent_opinion: Agent 当前观点
        
        Returns:
            社会验证结果
        """
        group = self._groups.get(group_id)
        if group is None:
            return {"validation": 0.0, "agreement_ratio": 0.0}
        
        # 统计群组内观点分布
        group_opinions = []
        for msg in group.messages:
            if msg.opinion is not None and msg.sender_id != agent_id:
                group_opinions.append(msg.opinion)
        
        if not group_opinions:
            return {"validation": 0.5, "agreement_ratio": 0.0}
        
        # 计算认同比例
        agreeing = sum(1 for op in group_opinions if (op > 0) == (agent_opinion > 0))
        agreement_ratio = agreeing / len(group_opinions)
        
        # 社会验证强度
        validation = (agreement_ratio * self.validation_weight_agreement +
                      self.validation_weight_neutrality * (1 - abs(agent_opinion)))
        
        return {
            "validation": validation,
            "agreement_ratio": agreement_ratio,
            "group_size": len(group.members),
            "opinion_count": len(group_opinions)
        }
    
    def detect_opinion_clash(self, group_id: str) -> Optional[Dict]:
        """
        检测群组内的观点碰撞
        
        Args:
            group_id: 群组 ID
        
        Returns:
            碰撞信息（如有）
        """
        group = self._groups.get(group_id)
        if group is None:
            return None
        
        opinions = [m.opinion for m in group.messages if m.opinion is not None]
        if len(opinions) < 2:
            return None
        
        # 检查是否有明显对立
        threshold = self.opinion_clash_threshold
        positive = sum(1 for o in opinions if o > threshold)
        negative = sum(1 for o in opinions if o < -threshold)
        
        if positive > 0 and negative > 0:
            return {
                "group_id": group_id,
                "clash_detected": True,
                "positive_count": positive,
                "negative_count": negative,
                "polarization": abs(positive - negative) / len(opinions)
            }
        
        return None
    
    def get_group_stats(self) -> Dict:
        """获取群组统计"""
        return {
            "total_groups": len(self._groups),
            "total_messages": len(self._log),
            "groups": {gid: g.to_dict() for gid, g in self._groups.items()}
        }
    
    def clear(self):
        """清空所有群组"""
        self._groups.clear()
        self._log.clear()

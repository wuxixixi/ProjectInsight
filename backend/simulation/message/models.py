"""
Message Models - 消息数据模型

定义消息类型、状态和消息结构
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid


class MessageType(str, Enum):
    """消息类型"""
    P2P = "peer_to_peer"       # 私聊
    P2G = "peer_to_group"      # 广播
    GROUP_CHAT = "group_chat"  # 群聊


class MessageStatus(str, Enum):
    """消息状态"""
    PENDING = "pending"      # 待发送
    SENT = "sent"           # 已发送
    DELIVERED = "delivered"  # 已送达
    READ = "read"           # 已读
    FAILED = "failed"       # 发送失败


class Message(BaseModel):
    """
    消息模型
    
    Agent 间通信的基本单位
    """
    
    # 基本信息
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    message_type: MessageType = MessageType.P2P
    
    # 发送接收
    sender_id: int
    receiver_ids: List[int] = Field(default_factory=list)
    
    # 内容
    content: str
    opinion: Optional[float] = None  # 发送时观点
    
    # 时间
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # 状态
    status: MessageStatus = MessageStatus.PENDING
    
    # 传播属性
    propagation_prob: float = Field(0.5, ge=0.0, le=1.0, description="传播概率")
    credibility: float = Field(0.5, ge=0.0, le=1.0, description="发送者可信度")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "id": self.id,
            "type": self.message_type.value,
            "sender_id": self.sender_id,
            "receiver_ids": self.receiver_ids,
            "content": self.content,
            "opinion": self.opinion,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "propagation_prob": self.propagation_prob
        }


class MessageBatch(BaseModel):
    """消息批次"""
    step: int
    messages: List[Message]
    total_count: int
    delivered_count: int = 0
    
    def add_message(self, message: Message):
        """添加消息"""
        self.messages.append(message)
        self.total_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "total_count": self.total_count,
            "delivered_count": self.delivered_count,
            "message_ids": [m.id for m in self.messages]
        }

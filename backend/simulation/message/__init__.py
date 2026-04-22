"""
Message Module - 通信系统

支持多种通信模式:
- P2P: Agent 间私聊
- P2G: Agent → 群体广播
- GroupChat: 多 Agent 群组讨论
"""

from .models import Message, MessageType, MessageStatus
from .p2p import P2PMessenger
from .p2g import P2GBroadcaster
from .group_chat import GroupChat, ChatGroup

__all__ = [
    "Message",
    "MessageType",
    "MessageStatus",
    "P2PMessenger",
    "P2GBroadcaster",
    "GroupChat",
    "ChatGroup",
]

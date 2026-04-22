"""
Storage Module - 状态持久化

提供推演数据的持久化存储:
- ReplayWriter: 状态快照和回放
- QueryInterface: 数据查询
"""

from .replay_writer import ReplayWriter

__all__ = [
    "ReplayWriter",
]

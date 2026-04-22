"""
Message Module Unit Tests

测试 Phase 3 实现的组件:
- Message 模型
- P2PMessenger
- P2GBroadcaster
- GroupChat
"""
import pytest
import asyncio

from backend.simulation.message import (
    Message,
    MessageType,
    MessageStatus,
    P2PMessenger,
    P2GBroadcaster,
    GroupChat,
    ChatGroup
)
from backend.simulation.storage import ReplayWriter


class TestMessageModels:
    """测试消息模型"""
    
    def test_message_creation(self):
        """测试消息创建"""
        msg = Message(
            sender_id=1,
            receiver_ids=[2, 3],
            content="测试消息",
            opinion=0.5
        )
        
        assert msg.sender_id == 1
        assert len(msg.receiver_ids) == 2
        assert msg.opinion == 0.5
    
    def test_message_types(self):
        """测试消息类型"""
        p2p = Message(
            message_type=MessageType.P2P,
            sender_id=1,
            receiver_ids=[2],
            content="私聊"
        )
        assert p2p.message_type == MessageType.P2P
        
        p2g = Message(
            message_type=MessageType.P2G,
            sender_id=1,
            receiver_ids=[2, 3, 4],
            content="广播"
        )
        assert p2g.message_type == MessageType.P2G
    
    def test_message_to_dict(self):
        """测试消息序列化"""
        msg = Message(
            sender_id=1,
            receiver_ids=[2],
            content="测试"
        )
        
        d = msg.to_dict()
        assert d["sender_id"] == 1
        assert "content" in d


class TestP2PMessenger:
    """测试 P2P 通信"""
    
    @pytest.mark.asyncio
    async def test_send_and_receive(self):
        """测试发送和接收"""
        messenger = P2PMessenger()
        
        # 发送消息
        msg = await messenger.send(
            sender_id=1,
            receiver_id=2,
            content="你好",
            opinion=0.3
        )
        
        assert msg.sender_id == 1
        assert msg.receiver_ids == [2]
        
        # 接收消息
        received = await messenger.receive(2)
        # 由于传播概率，可能收到也可能没收到
        assert isinstance(received, list)
    
    @pytest.mark.asyncio
    async def test_propagation_probability(self):
        """测试传播概率计算"""
        messenger = P2PMessenger()
        
        prob = messenger.compute_propagation_probability(
            sender_opinion=0.5,
            receiver_opinion=0.4,
            sender_strength=0.6,
            content_alignment=0.7
        )
        
        assert 0 <= prob <= 1
        # 观点相似、信度高、内容匹配 → 高概率
        assert prob > 0.5
    
    def test_get_inbox_size(self):
        """测试收件箱大小"""
        messenger = P2PMessenger()
        assert messenger.get_inbox_size(1) == 0


class TestP2GBroadcaster:
    """测试 P2G 广播"""
    
    @pytest.mark.asyncio
    async def test_broadcast(self):
        """测试广播"""
        broadcaster = P2GBroadcaster()
        broadcaster.set_adjacency({1: [2, 3, 4, 5]})
        
        msg = await broadcaster.broadcast(
            sender_id=1,
            content="重要通知",
            influence=0.8,
            reach=0.75
        )
        
        assert msg.sender_id == 1
        assert msg.message_type == MessageType.P2G
        # 根据影响力和覆盖范围，实际接收者数量不等
        assert len(msg.receiver_ids) > 0
    
    @pytest.mark.asyncio
    async def test_receive_broadcast(self):
        """测试接收广播"""
        broadcaster = P2GBroadcaster()
        broadcaster.set_adjacency({1: [2]})
        
        msg = await broadcaster.broadcast(
            sender_id=1,
            content="广播消息"
        )
        
        # 尝试接收
        received = await broadcaster.receive_broadcast(msg, 2)
        # 概率性接收
        assert isinstance(received, bool)
    
    def test_broadcast_stats(self):
        """测试广播统计"""
        broadcaster = P2GBroadcaster()
        
        stats = broadcaster.get_broadcast_stats()
        assert stats["total"] == 0
        assert stats["avg_reach"] == 0


class TestGroupChat:
    """测试群组讨论"""
    
    @pytest.mark.asyncio
    async def test_create_group(self):
        """测试创建群组"""
        gc = GroupChat()
        
        group = gc.create_group(
            group_id="g1",
            members=[1, 2, 3],
            topic="测试讨论"
        )
        
        assert group.group_id == "g1"
        assert len(group.members) == 3
        assert group.topic == "测试讨论"
    
    @pytest.mark.asyncio
    async def test_send_to_group(self):
        """测试群组发送"""
        gc = GroupChat()
        gc.create_group("g1", [1, 2, 3])
        
        msg = await gc.send_to_group(
            group_id="g1",
            sender_id=1,
            content="大家好",
            opinion=0.5
        )
        
        assert msg is not None
        assert msg.sender_id == 1
        assert 2 in msg.receiver_ids
        assert 3 in msg.receiver_ids
    
    @pytest.mark.asyncio
    async def test_receive_group_messages(self):
        """测试群组接收"""
        gc = GroupChat()
        gc.create_group("g1", [1, 2])
        
        await gc.send_to_group("g1", 1, "消息", 0.3)
        
        messages = await gc.receive_group_messages("g1", 2)
        assert isinstance(messages, list)
    
    @pytest.mark.asyncio
    async def test_social_validation(self):
        """测试社会验证"""
        gc = GroupChat()
        gc.create_group("g1", [1, 2, 3])
        
        # 发送一些消息
        await gc.send_to_group("g1", 2, "正面观点", 0.5)
        await gc.send_to_group("g1", 3, "正面观点", 0.4)
        
        result = gc.compute_social_validation("g1", 1, 0.3)
        
        assert "validation" in result
        assert "agreement_ratio" in result
    
    @pytest.mark.asyncio
    async def test_opinion_clash(self):
        """测试观点碰撞检测"""
        gc = GroupChat()
        gc.create_group("g1", [1, 2, 3])
        
        # 发送对立观点
        await gc.send_to_group("g1", 1, "负面", -0.5)
        await gc.send_to_group("g1", 2, "正面", 0.5)
        
        clash = gc.detect_opinion_clash("g1")
        assert clash is not None
        assert clash["clash_detected"] == True


class TestReplayWriter:
    """测试持久化"""
    
    def test_save_agent_profile(self, tmp_path):
        """测试保存 Agent 配置"""
        writer = ReplayWriter(db_path=str(tmp_path / "test.db"))
        
        writer.save_agent_profile(
            agent_id=1,
            simulation_id="test_sim",
            persona_type="理性型",
            susceptibility=0.5,
            influence=0.6,
            initial_opinion=0.3
        )
        
        profiles = writer.get_agent_profiles("test_sim")
        assert len(profiles) == 1
        assert profiles[0]["persona_type"] == "理性型"
    
    def test_save_belief(self, tmp_path):
        """测试保存信念"""
        writer = ReplayWriter(db_path=str(tmp_path / "test.db"))
        
        writer.save_belief(
            simulation_id="test_sim",
            agent_id=1,
            step=1,
            rumor_trust=0.2,
            truth_trust=0.5,
            belief_strength=0.7,
            cognitive_closed_need=0.4,
            opinion=0.3
        )
        
        history = writer.get_belief_history("test_sim")
        assert len(history) == 1
        assert history[0]["opinion"] == 0.3
    
    def test_save_message(self, tmp_path):
        """测试保存消息"""
        writer = ReplayWriter(db_path=str(tmp_path / "test.db"))
        
        writer.save_message(
            simulation_id="test_sim",
            message_id="m1",
            message_type="p2p",
            sender_id=1,
            receiver_ids=[2, 3],
            content="测试消息",
            step=1
        )
        
        messages = writer.get_message_log("test_sim")
        assert len(messages) == 1
        assert messages[0]["content"] == "测试消息"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
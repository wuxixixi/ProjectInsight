"""
Agent Module Unit Tests

测试 Phase 1 实现的核心组件:
- BeliefState
- AgentMemory
- AgentBase
- PersonAgent
"""
import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

from backend.simulation.agent import (
    BeliefState,
    ExposureEvent,
    ExposureSource,
    AgentMemory,
    AgentBase,
    AgentProfile,
    MathModelAgent,
    PersonAgent
)
from backend.simulation.agent.skills import SkillBase, SkillContext, SkillLoader
from backend.simulation.agent.skills.observation import ObservationSkill


class TestBeliefState:
    """测试 BeliefState 结构化信念模型"""
    
    def test_belief_state_creation(self):
        """测试创建信念状态"""
        belief = BeliefState(
            rumor_trust=0.3,
            truth_trust=0.5,
            belief_strength=0.7,
            cognitive_closed_need=0.4
        )
        
        assert belief.rumor_trust == 0.3
        assert belief.truth_trust == 0.5
        assert belief.belief_strength == 0.7
    
    def test_to_opinion(self):
        """测试转换为单一观点值"""
        # 正向信念
        belief1 = BeliefState(rumor_trust=0.0, truth_trust=0.5)
        assert belief1.to_opinion() == 0.5
        
        # 负向信念
        belief2 = BeliefState(rumor_trust=0.3, truth_trust=0.0)
        assert belief2.to_opinion() == -0.3
        
        # 中立
        belief3 = BeliefState(rumor_trust=0.2, truth_trust=0.2)
        assert belief3.to_opinion() == 0.0
    
    def test_from_legacy_opinion(self):
        """测试从旧版观点值构造"""
        # 正向观点
        belief1 = BeliefState.from_legacy_opinion(0.5, strength=0.6)
        assert belief1.truth_trust == 0.5
        assert belief1.rumor_trust == 0.0
        assert belief1.belief_strength == 0.6
        
        # 负向观点
        belief2 = BeliefState.from_legacy_opinion(-0.3, strength=0.4)
        assert belief2.rumor_trust == 0.3
        assert belief2.truth_trust == 0.0
    
    def test_add_exposure(self):
        """测试添加信息暴露事件"""
        belief = BeliefState()
        
        event = ExposureEvent(
            step=1,
            source=ExposureSource.ALGORITHM,
            content="测试内容",
            alignment=0.5
        )
        
        belief.add_exposure(event)
        assert len(belief.exposure_history) == 1
        assert belief.exposure_history[0].content == "测试内容"
    
    def test_is_convinced(self):
        """测试观点形成判断"""
        belief1 = BeliefState(truth_trust=0.5)
        assert belief1.is_convinced(threshold=0.3) == True
        
        belief2 = BeliefState(rumor_trust=0.2, truth_trust=0.1)
        assert belief2.is_convinced(threshold=0.3) == False
    
    def test_is_conflicted(self):
        """测试认知失调判断"""
        # 存在认知失调
        belief1 = BeliefState(rumor_trust=0.5, truth_trust=0.4)
        assert belief1.is_conflicted() == True
        
        # 无认知失调
        belief2 = BeliefState(rumor_trust=0.1, truth_trust=0.6)
        assert belief2.is_conflicted() == False


class TestAgentMemory:
    """测试三层记忆系统"""
    
    def test_memory_creation(self, tmp_path):
        """测试创建记忆系统"""
        db_path = tmp_path / "test_memory.db"
        memory = AgentMemory(agent_id=1, db_path=str(db_path))
        
        assert memory.agent_id == 1
        assert len(memory.short_term) == 0
    
    def test_add_interaction(self, tmp_path):
        """测试添加短时记忆"""
        db_path = tmp_path / "test_memory.db"
        memory = AgentMemory(agent_id=1, db_path=str(db_path))
        
        event = ExposureEvent(
            step=1,
            source=ExposureSource.SOCIAL,
            content="邻居观点",
            alignment=0.3
        )
        
        memory.add_interaction(event)
        assert len(memory.short_term) == 1
    
    def test_store_belief(self, tmp_path):
        """测试存储信念到长时记忆"""
        db_path = tmp_path / "test_memory.db"
        memory = AgentMemory(agent_id=1, db_path=str(db_path))
        
        belief = BeliefState(rumor_trust=0.2, truth_trust=0.5)
        memory.store_belief(belief, step=1)
        
        # 查询历史
        history = memory.get_belief_history()
        assert len(history) == 1
        assert history[0]["rumor_trust"] == 0.2
    
    def test_cognition_buffer(self, tmp_path):
        """测试认知缓冲"""
        db_path = tmp_path / "test_memory.db"
        memory = AgentMemory(agent_id=1, db_path=str(db_path))
        
        memory.add_cognition(
            skill_name="test_skill",
            step=1,
            input_data={"key": "value"},
            output_data={"result": 0.5}
        )
        
        assert len(memory.cognition_buffer) == 1
        
        memory.flush_cognition(step=1)
        assert len(memory.cognition_buffer) == 0
    
    def test_memory_statistics(self, tmp_path):
        """测试记忆统计"""
        db_path = tmp_path / "test_memory.db"
        memory = AgentMemory(agent_id=1, db_path=str(db_path))
        
        stats = memory.get_statistics()
        assert stats["agent_id"] == 1
        assert "short_term_size" in stats


class TestAgentProfile:
    """测试 Agent 人设配置"""
    
    def test_profile_creation(self):
        """测试创建人设"""
        profile = AgentProfile(
            agent_id=1,
            name="测试用户",
            susceptibility=0.6,
            influence=0.3,
            fear_of_isolation=0.5
        )
        
        assert profile.agent_id == 1
        assert profile.susceptibility == 0.6
    
    def test_profile_validation(self):
        """测试参数范围验证"""
        # 应该抛出异常（超出范围）
        with pytest.raises(Exception):
            AgentProfile(
                agent_id=1,
                susceptibility=1.5  # 超出 [0, 1]
            )


class TestMathModelAgent:
    """测试数学模型 Agent"""
    
    @pytest.mark.asyncio
    async def test_math_agent_step(self):
        """测试数学模型推演步骤"""
        from backend.simulation.agent.base import MathModelAgent
        
        profile = AgentProfile(
            agent_id=1,
            susceptibility=0.5,
            influence=0.3,
            fear_of_isolation=0.4
        )
        
        agent = MathModelAgent(
            profile=profile,
            initial_belief=BeliefState.from_legacy_opinion(-0.3)
        )
        
        context = {
            "step": 1,
            "peer_opinions": [0.1, 0.2, -0.1],
            "algorithm_content": "测试推荐",
            "algorithm_alignment": -0.2
        }
        
        result = await agent.step(context)
        
        assert "new_opinion" in result
        assert "is_silent" in result
        assert -1 <= result["new_opinion"] <= 1


class TestPersonAgent:
    """测试 LLM 驱动的 Agent"""
    
    def test_person_agent_creation(self):
        """测试创建 PersonAgent"""
        profile = AgentProfile(
            agent_id=1,
            persona_type="理性分析型",
            persona_desc="习惯多方求证",
            susceptibility=0.3,
            influence=0.5
        )
        
        initial_belief = BeliefState.from_legacy_opinion(0.2)
        
        agent = PersonAgent(profile=profile, initial_belief=initial_belief)
        
        assert agent.id == 1
        assert agent.get_opinion() == 0.2
    
    @pytest.mark.asyncio
    async def test_person_agent_observe(self):
        """测试 PersonAgent 观察"""
        profile = AgentProfile(agent_id=1)
        agent = PersonAgent(profile=profile)
        
        context = {
            "step": 1,
            "peer_opinions": [0.1, 0.2],
            "algorithm_content": "测试推荐"
        }
        
        observation = await agent.observe(context)
        
        assert "exposures" in observation
        assert len(observation["exposures"]) > 0


class TestSkillPipeline:
    """测试技能管道"""
    
    @pytest.mark.asyncio
    async def test_skill_loader(self):
        """测试技能懒加载"""
        from backend.simulation.agent.skills.loader import SkillLoader
        
        loader = SkillLoader()
        
        available = loader.get_available_skills()
        assert "observation" in available
        assert "memory" in available
        assert "needs" in available
        assert "cognition" in available
        assert "plan" in available
    
    @pytest.mark.asyncio
    async def test_observation_skill(self):
        """测试观察技能"""
        from backend.simulation.agent.skills import SkillBase, SkillContext
        
        # 导入观察技能
        from backend.simulation.agent.skills.observation import ObservationSkill
        
        skill = ObservationSkill()
        
        context = SkillContext(
            agent_id=1,
            step=1,
            belief_state={"opinion": 0.2, "fear_of_isolation": 0.5},
            observation={"peer_opinions": [0.1, 0.3]},
            memory={},
            config={}
        )
        
        result = await skill.execute(context)
        
        assert result.success
        assert "exposures" in result.output


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
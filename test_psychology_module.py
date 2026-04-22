"""
Psychology Module Unit Tests

测试 Phase 4 实现的心理学模型:
- NeedsHierarchy (马斯洛需求层次)
- TheoryOfPlannedBehavior (计划行为理论)
"""
import pytest

from backend.simulation.psychology import (
    NeedsHierarchy,
    NeedLevel,
    TheoryOfPlannedBehavior,
    TPBResult,
    BehaviorType
)


class TestNeedsHierarchy:
    """测试马斯洛需求层次模型"""
    
    def test_creation(self):
        """测试创建需求层次"""
        hierarchy = NeedsHierarchy(
            safety=0.4,
            love=0.3,
            cognitive=0.7
        )
        
        assert hierarchy.safety == 0.4
        assert hierarchy.love == 0.3
    
    def test_compute_dominant_level(self):
        """测试计算主导需求"""
        hierarchy = NeedsHierarchy(
            physiological=0.9,
            safety=0.3,  # 最低
            love=0.5,
            esteem=0.6,
            cognitive=0.7
        )
        
        dominant = hierarchy.compute_dominant_level()
        assert dominant == NeedLevel.SAFETY
    
    def test_dominant_level_high(self):
        """测试高层需求主导"""
        hierarchy = NeedsHierarchy(
            physiological=0.9,
            safety=0.85,
            love=0.8,
            esteem=0.75,
            cognitive=0.3  # 最低
        )
        
        dominant = hierarchy.compute_dominant_level()
        assert dominant == NeedLevel.COGNITIVE
    
    def test_information_receptivity(self):
        """测试信息接受度"""
        hierarchy = NeedsHierarchy(
            safety=0.2,  # 安全需求未满足
            love=0.7
        )
        hierarchy.compute_dominant_level()
        
        # 安全需求主导 → 威胁信息接受度高
        receptivity = hierarchy.compute_information_receptivity("threat")
        assert receptivity > 1.0
        
        # 知识信息接受度相对较低
        receptivity_knowledge = hierarchy.compute_information_receptivity("knowledge")
        assert receptivity_knowledge < receptivity
    
    def test_receptivity_love_dominant(self):
        """测试社交需求主导的信息接受度"""
        hierarchy = NeedsHierarchy(
            safety=0.8,
            love=0.2,  # 社交需求未满足
            cognitive=0.7
        )
        hierarchy.compute_dominant_level()
        
        # 社交需求主导 → 社交信息接受度高
        receptivity = hierarchy.compute_information_receptivity("social")
        assert receptivity > 1.0
    
    def test_opinion_change_factor(self):
        """测试观点变化因子"""
        hierarchy = NeedsHierarchy(
            love=0.2,  # 社交需求主导
            safety=0.8,
            cognitive=0.7
        )
        hierarchy.compute_dominant_level()
        
        # 社交需求主导 → 最高变化因子
        factor = hierarchy.compute_opinion_change_factor()
        assert factor == 1.4
    
    def test_from_agent_traits(self):
        """测试从 Agent 特征推断"""
        # 高易感性、高孤立恐惧 → 安全/社交需求未满足
        hierarchy = NeedsHierarchy.from_agent_traits(
            fear_of_isolation=0.8,
            susceptibility=0.7,
            influence=0.3
        )
        
        assert hierarchy.safety < 0.7  # 安全需求未满足
        assert hierarchy.love < 0.7    # 社交需求未满足
    
    def test_description(self):
        """测试描述生成"""
        hierarchy = NeedsHierarchy(safety=0.2)
        hierarchy.compute_dominant_level()
        
        desc = hierarchy.get_description()
        assert "安全" in desc or "威胁" in desc


class TestTheoryOfPlannedBehavior:
    """测试计划行为理论"""
    
    def test_creation(self):
        """测试创建 TPB 模型"""
        tpb = TheoryOfPlannedBehavior()
        
        assert tpb.attitude_weight == 0.4
        assert tpb.norm_weight == 0.3
    
    def test_compute_intention(self):
        """测试行为意向计算"""
        tpb = TheoryOfPlannedBehavior()
        
        intention = tpb.compute_intention(
            attitude=0.8,
            subjective_norm=0.6,
            perceived_control=0.7
        )
        
        # 高态度、高规范、高控制 → 高意向
        assert intention > 0.4
    
    def test_intention_negative(self):
        """测试负向意向"""
        tpb = TheoryOfPlannedBehavior()
        
        intention = tpb.compute_intention(
            attitude=-0.5,
            subjective_norm=-0.3,
            perceived_control=0.4
        )
        
        # 负态度、负规范 → 负意向
        assert intention < 0
    
    def test_predict_behavior_share(self):
        """测试预测转发行为"""
        tpb = TheoryOfPlannedBehavior()
        
        result = tpb.predict_behavior(
            intention=0.7,
            attitude=0.6,
            subjective_norm=0.5,
            perceived_control=0.7,
            current_opinion=0.5
        )
        
        assert result.predicted_behavior in [BehaviorType.SHARE, BehaviorType.COMMENT]
        assert result.intention > 0.5
    
    def test_predict_behavior_silence(self):
        """测试预测沉默行为"""
        tpb = TheoryOfPlannedBehavior()
        
        result = tpb.predict_behavior(
            intention=-0.7,
            attitude=-0.5,
            subjective_norm=-0.6,
            perceived_control=0.3,
            current_opinion=0.2
        )
        
        assert result.predicted_behavior == BehaviorType.SILENCE
    
    def test_predict_behavior_verify(self):
        """测试预测求证行为"""
        tpb = TheoryOfPlannedBehavior()
        
        result = tpb.predict_behavior(
            intention=0.2,
            attitude=0.1,
            subjective_norm=0.0,
            perceived_control=0.8,  # 高媒介素养
            current_opinion=0.0
        )
        
        assert result.predicted_behavior in [BehaviorType.VERIFY, BehaviorType.OBSERVE]
    
    def test_compute_full(self):
        """测试完整 TPB 计算"""
        tpb = TheoryOfPlannedBehavior()
        
        result = tpb.compute_full(
            info_credibility=0.7,
            content_relevance=0.6,
            cognitive_dissonance=0.2,
            social_pressure=0.5,
            conformity_tendency=0.6,
            media_literacy=0.5,
            current_opinion=0.3
        )
        
        assert isinstance(result, TPBResult)
        assert -1 <= result.intention <= 1
        assert isinstance(result.predicted_behavior, BehaviorType)
    
    def test_factory_high_conformity(self):
        """测试高从众型工厂"""
        tpb = TheoryOfPlannedBehavior.for_high_conformity()
        
        # 主观规范权重最高
        assert tpb.norm_weight > tpb.attitude_weight
    
    def test_factory_independent(self):
        """测试独立思考型工厂"""
        tpb = TheoryOfPlannedBehavior.for_independent_thinker()
        
        # 态度权重最高
        assert tpb.attitude_weight > tpb.norm_weight
    
    def test_factory_high_control(self):
        """测试高自我效能型工厂"""
        tpb = TheoryOfPlannedBehavior.for_high_control()
        
        # 知觉控制权重最高
        assert tpb.control_weight > tpb.norm_weight
    
    def test_to_dict(self):
        """测试序列化"""
        tpb = TheoryOfPlannedBehavior()
        
        d = tpb.to_dict()
        assert "weights" in d
        assert "thresholds" in d


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
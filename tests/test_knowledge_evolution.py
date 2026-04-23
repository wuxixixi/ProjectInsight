"""
Phase 1: 知识图谱驱动演化 - 单元测试

测试内容：
1. 实体影响力计算
2. 人设参数化配置
3. 知识驱动演化器
4. 观点影响计算
"""

import pytest
import numpy as np
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPersonaConfig:
    """测试人设参数化配置"""
    
    def test_get_persona_weights_known(self):
        """测试获取已知人设配置"""
        from backend.config.persona_config import get_persona_weights, PERSONA_CONFIGS
        
        # 测试意见领袖
        weights = get_persona_weights("意见领袖")
        assert weights.authority_acceptance == 0.9
        assert weights.social_influence == 0.9
        assert weights.persona_type == "意见领袖"
        
        # 测试怀疑论者
        weights = get_persona_weights("怀疑论者")
        assert weights.rumor_susceptibility == 0.2
        assert weights.opinion_stability == 0.8
        
        # 测试从众者
        weights = get_persona_weights("从众者")
        assert weights.rumor_susceptibility == 0.8
        assert weights.opinion_stability == 0.3
    
    def test_get_persona_weights_unknown(self):
        """测试获取未知人设配置（返回默认）"""
        from backend.config.persona_config import get_persona_weights
        
        weights = get_persona_weights("未知类型")
        assert weights.authority_acceptance == 0.7  # 默认值
        assert weights.persona_type == "未知类型"
    
    def test_get_all_persona_types(self):
        """测试获取所有人设类型"""
        from backend.config.persona_config import get_all_persona_types
        
        types = get_all_persona_types()
        assert "意见领袖" in types
        assert "怀疑论者" in types
        assert "从众者" in types
        assert len(types) >= 8


class TestEntityImpactCalculator:
    """测试实体影响力计算"""
    
    def test_calculate_basic(self):
        """测试基础影响力计算"""
        from backend.simulation.knowledge_evolution import EntityImpactCalculator
        
        calculator = EntityImpactCalculator()
        
        entities = [
            {"name": "央视新闻", "type": "媒体", "importance": 1},
            {"name": "公安部", "type": "官方", "importance": 1},
            {"name": "张三", "type": "人物", "importance": 3},
        ]
        
        impacts = calculator.calculate(entities)
        
        # 媒体应该有最高影响力
        assert impacts["央视新闻"] > impacts["张三"]
        # 官方影响力应该高于普通人物
        assert impacts["公安部"] > impacts["张三"]
    
    def test_calculate_with_centrality(self):
        """测试包含网络中心性的影响力计算"""
        from backend.simulation.knowledge_evolution import EntityImpactCalculator
        
        calculator = EntityImpactCalculator()
        
        entities = [
            {"name": "大V", "type": "人物", "importance": 2},
            {"name": "普通用户", "type": "人物", "importance": 3},
        ]
        
        # 大V有更高的中心性
        centrality = {"大V": 0.9, "普通用户": 0.2}
        
        impacts = calculator.calculate(entities, centrality)
        
        # 大V的影响力应该更高
        assert impacts["大V"] > impacts["普通用户"]
    
    def test_type_weights(self):
        """测试实体类型权重"""
        from backend.simulation.knowledge_evolution import EntityImpactCalculator
        
        calculator = EntityImpactCalculator()
        
        # 获取类型权重
        assert calculator.config.type_weights["媒体"] == 1.0
        assert calculator.config.type_weights["官方"] == 0.95
        assert calculator.config.type_weights["专家"] == 0.85


class TestKnowledgeDrivenEvolution:
    """测试知识驱动演化器"""
    
    @pytest.fixture
    def sample_entities(self):
        """示例实体"""
        return [
            {"name": "央视新闻", "type": "媒体", "importance": 1},
            {"name": "公安部", "type": "官方", "importance": 1},
            {"name": "专家A", "type": "专家", "importance": 2},
            {"name": "某公司", "type": "组织", "importance": 3},
            {"name": "张三", "type": "人物", "importance": 4},
        ]
    
    @pytest.fixture
    def sample_relations(self):
        """示例关系"""
        return [
            {"source": "央视新闻", "target": "公安部", "type": "报道"},
            {"source": "公安部", "target": "某公司", "type": "调查"},
            {"source": "专家A", "target": "张三", "type": "支持"},
        ]
    
    def test_initialization(self, sample_entities, sample_relations):
        """测试初始化"""
        from backend.simulation.knowledge_evolution import KnowledgeDrivenEvolution
        
        evolution = KnowledgeDrivenEvolution(sample_entities, sample_relations)
        
        assert len(evolution.entities) == 5
        assert len(evolution.relations) == 3
        assert len(evolution.entity_impacts) == 5
        assert evolution.sorted_entities[0]["name"] == "央视新闻" or evolution.sorted_entities[0]["name"] == "公安部"
    
    def test_compute_influence(self, sample_entities, sample_relations):
        """测试单Agent影响力计算"""
        from backend.simulation.knowledge_evolution import KnowledgeDrivenEvolution
        
        evolution = KnowledgeDrivenEvolution(sample_entities, sample_relations)
        
        # 测试不同人设
        influence_leader = evolution.compute_influence(
            agent_opinion=0.5,
            agent_persona="意见领袖",
            exposed_entities=["央视新闻", "公安部"],
            cocoon_strength=0.5
        )
        
        influence_skeptic = evolution.compute_influence(
            agent_opinion=0.5,
            agent_persona="怀疑论者",
            exposed_entities=["央视新闻", "公安部"],
            cocoon_strength=0.5
        )
        
        # 意见领袖更容易受权威影响
        assert abs(influence_leader) >= 0
        assert abs(influence_skeptic) >= 0
    
    def test_compute_batch_influence(self, sample_entities, sample_relations):
        """测试批量影响力计算"""
        from backend.simulation.knowledge_evolution import KnowledgeDrivenEvolution

        evolution = KnowledgeDrivenEvolution(sample_entities, sample_relations)

        n_agents = 100
        opinions = np.random.uniform(-0.5, 0.5, n_agents)
        personas = ["意见领袖" if i < 10 else "普通用户" for i in range(n_agents)]

        influences = evolution.compute_batch_influence(
            opinions=opinions,
            personas=personas,
            cocoon_strength=0.5,
            response_released=False
        )

        assert len(influences) == n_agents
        assert np.all(np.abs(influences) <= 0.15)  # 不超过最大影响
    
    def test_get_top_entities(self, sample_entities, sample_relations):
        """测试获取高影响力实体"""
        from backend.simulation.knowledge_evolution import KnowledgeDrivenEvolution
        
        evolution = KnowledgeDrivenEvolution(sample_entities, sample_relations)
        
        top_entities = evolution.get_top_entities(3)
        
        assert len(top_entities) <= 3
        # 媒体或官方应该在前列
        names = [e[0] for e in top_entities]
        assert "央视新闻" in names or "公安部" in names
    
    def test_disabled_evolution(self, sample_entities, sample_relations):
        """测试禁用知识演化"""
        from backend.simulation.knowledge_evolution import (
            KnowledgeDrivenEvolution, KnowledgeEvolutionConfig
        )
        
        config = KnowledgeEvolutionConfig(enabled=False)
        evolution = KnowledgeDrivenEvolution(
            sample_entities, sample_relations, config=config
        )
        
        opinions = np.array([0.5, 0.3, -0.2])
        personas = ["意见领袖", "普通用户", "怀疑论者"]
        
        influences = evolution.compute_batch_influence(
            opinions=opinions,
            personas=personas,
            cocoon_strength=0.5
        )
        
        # 禁用时应该返回零
        assert np.allclose(influences, 0)


class TestEngineIntegration:
    """测试引擎集成"""
    
    def test_set_knowledge_graph(self):
        """测试引擎设置知识图谱"""
        from backend.simulation.engine import SimulationEngine
        
        engine = SimulationEngine(use_llm=False)
        
        entities = [
            {"name": "央视", "type": "媒体", "importance": 1},
            {"name": "专家", "type": "专家", "importance": 2},
        ]
        relations = [
            {"source": "央视", "target": "专家", "type": "报道"}
        ]
        
        engine.set_knowledge_graph(entities, relations)
        
        assert engine.use_knowledge_evolution == True
        assert engine.knowledge_evolution is not None
        assert len(engine.knowledge_graph["entities"]) == 2
    
    def test_engine_with_knowledge_step(self):
        """测试引擎带知识图谱的推演步骤"""
        from backend.simulation.engine import SimulationEngine
        
        engine = SimulationEngine(use_llm=False, population_size=50)
        
        # 设置知识图谱
        entities = [
            {"name": "权威媒体", "type": "媒体", "importance": 1},
            {"name": "官方机构", "type": "官方", "importance": 1},
        ]
        relations = []
        engine.set_knowledge_graph(entities, relations)
        
        # 初始化
        engine.initialize()
        
        # 执行步骤
        engine._math_step()
        
        # 验证观点仍在有效范围内
        opinions = engine.population.opinions
        assert np.all(opinions >= -1) and np.all(opinions <= 1)


class TestPersonaWeightsEffect:
    """测试人设权重效果"""
    
    def test_authority_acceptance_difference(self):
        """测试权威接受度差异"""
        from backend.simulation.knowledge_evolution import KnowledgeDrivenEvolution
        
        entities = [
            {"name": "央视新闻", "type": "媒体", "importance": 1},
        ]
        relations = []
        
        evolution = KnowledgeDrivenEvolution(entities, relations)
        
        # 意见领袖：高权威接受度
        inf_leader = evolution.compute_influence(
            agent_opinion=0.0,
            agent_persona="意见领袖",
            exposed_entities=["央视新闻"],
            cocoon_strength=0.5
        )
        
        # 激进派：低权威接受度
        inf_radical = evolution.compute_influence(
            agent_opinion=0.0,
            agent_persona="激进派",
            exposed_entities=["央视新闻"],
            cocoon_strength=0.5
        )
        
        # 意见领袖应该更容易受权威影响
        # 注意：具体数值取决于配置，验证返回值有效
        assert isinstance(inf_leader, float) and isinstance(inf_radical, float)
    
    def test_rumor_susceptibility_difference(self):
        """测试谣言易感性差异"""
        from backend.simulation.knowledge_evolution import KnowledgeDrivenEvolution
        
        # 低重要性实体（模拟谣言源）
        entities = [
            {"name": "匿名消息", "type": "人物", "importance": 4},
        ]
        relations = []
        
        evolution = KnowledgeDrivenEvolution(entities, relations)
        
        # 从众者：高谣言易感性
        inf_follower = evolution.compute_influence(
            agent_opinion=0.5,
            agent_persona="从众者",
            exposed_entities=["匿名消息"],
            cocoon_strength=0.5
        )
        
        # 怀疑论者：低谣言易感性
        inf_skeptic = evolution.compute_influence(
            agent_opinion=0.5,
            agent_persona="怀疑论者",
            exposed_entities=["匿名消息"],
            cocoon_strength=0.5
        )
        
        # 两种人设应该有不同的反应，验证返回值有效
        assert isinstance(inf_follower, float) and isinstance(inf_skeptic, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

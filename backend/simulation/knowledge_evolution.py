"""
知识图谱驱动的观点演化器

核心功能：
1. 实体影响力计算（类型+重要性+网络位置）
2. 人设调节（参数化配置）
3. 关系传导（立场传递）
4. 观点更新（知识驱动）

Phase 1 实现：让知识图谱参与观点演化，而非仅作为LLM上下文
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import logging
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.persona_config import get_persona_weights, PersonaWeights

logger = logging.getLogger(__name__)


@dataclass
class EntityImpactConfig:
    """实体影响力配置"""
    # 类型权重（媒体 > 官方 > 专家 > 组织 > 人物）
    type_weights: Dict[str, float] = None
    
    # 重要性衰减系数
    importance_decay: float = 0.8
    
    # 网络中心性权重
    centrality_weight: float = 0.3
    
    def __post_init__(self):
        if self.type_weights is None:
            self.type_weights = {
                "媒体": 1.0,
                "官方": 0.95,
                "专家": 0.85,
                "组织": 0.7,
                "人物": 0.5,
                "地点": 0.3,
                "概念": 0.2,
                "事件": 0.4,
                "证据": 0.6,
                # 英文类型兼容
                "organization": 0.7,
                "person": 0.5,
                "location": 0.3,
                "event": 0.4,
                "concept": 0.2,
                "evidence": 0.6,
            }


class EntityImpactCalculator:
    """实体影响力计算器"""
    
    def __init__(self, config: EntityImpactConfig = None):
        self.config = config or EntityImpactConfig()
    
    def calculate(
        self,
        entities: List[Dict],
        network_centrality: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        计算实体影响力
        
        综合考虑：
        1. 实体类型权重（媒体影响力最大）
        2. 重要性字段（1-5，越小越重要）
        3. 网络中心性（社交网络中的位置）
        
        Args:
            entities: 实体列表
            network_centrality: 实体在社交网络中的中心性 {实体名: 中心性}
        
        Returns:
            {实体名: 影响力权重 [0, 1]}
        """
        impacts = {}
        
        for entity in entities:
            name = entity.get("name", "")
            if not name:
                continue
            
            entity_type = entity.get("type", "人物")
            importance = entity.get("importance", 3)  # 1-5
            
            # 1. 类型权重
            type_weight = self.config.type_weights.get(entity_type, 0.5)
            
            # 2. 重要性权重（importance=1 -> weight=1.0, importance=5 -> weight=0.2）
            importance_weight = (6 - importance) / 5
            
            # 3. 网络中心性权重（如果有）
            centrality = 0.5  # 默认中等
            if network_centrality and name in network_centrality:
                centrality = network_centrality[name]
            
            # 综合计算
            impact = (
                type_weight * 0.4 +
                importance_weight * 0.4 +
                centrality * self.config.centrality_weight * 0.2
            )
            
            impacts[name] = min(1.0, max(0.0, impact))
        
        return impacts


@dataclass
class KnowledgeEvolutionConfig:
    """知识驱动演化配置"""
    # 证据链强度
    evidence_strength: float = 0.5
    
    # 权威回应效果系数
    response_effectiveness: float = 0.6
    
    # 关系传播衰减
    relation_decay: float = 0.7
    
    # 实体曝光上限（每个Agent最多关注N个实体）
    max_exposed_entities: int = 5
    
    # 是否启用知识驱动演化
    enabled: bool = True
    
    # 影响力限制（单步最大影响）
    max_influence_per_step: float = 0.15


class KnowledgeDrivenEvolution:
    """知识图谱驱动的观点演化器

    核心机制：
    1. 实体基础影响力 × 人设调节
    2. 观点同向/反向强化
    3. 茧房效应调节
    4. 权威回应效果（如已发布）
    """
    
    def __init__(
        self,
        entities: List[Dict],
        relations: List[Dict],
        config: KnowledgeEvolutionConfig = None,
        impact_config: EntityImpactConfig = None
    ):
        self.config = config or KnowledgeEvolutionConfig()
        self.impact_calculator = EntityImpactCalculator(impact_config)
        
        # 存储原始数据
        self.entities = entities
        self.relations = relations
        
        # 计算实体影响力
        self.entity_impacts = self.impact_calculator.calculate(entities)
        
        # 计算关系立场
        self.relation_stance = self._calculate_relation_stance(relations)
        
        # 构建实体关系图
        self.entity_graph = self._build_entity_graph(entities, relations)
        
        # 缓存实体列表（按影响力排序）
        self.sorted_entities = sorted(
            entities, 
            key=lambda e: self.entity_impacts.get(e.get("name", ""), 0),
            reverse=True
        )
        
        # 实体名称列表（用于随机选择）
        self.entity_names = [e.get("name", "") for e in self.sorted_entities if e.get("name")]
        
        # 实体权重（用于加权随机选择）
        if self.entity_names:
            weights = np.array([
                self.entity_impacts.get(name, 0.3) 
                for name in self.entity_names
            ])
            self.entity_weights = weights / weights.sum()
        else:
            self.entity_weights = np.array([])
        
        logger.info(f"知识驱动演化器初始化: {len(entities)} 实体, {len(relations)} 关系")
        if self.entity_impacts:
            top_entities = sorted(self.entity_impacts.items(), key=lambda x: -x[1])[:3]
            logger.info(f"影响力TOP3: {top_entities}")
    
    def _calculate_relation_stance(self, relations: List[Dict]) -> Dict[str, str]:
        """计算关系立场"""
        stance_map = {
            "支持": "support",
            "反对": "oppose",
            "对立": "oppose",
            "指控": "oppose",
            "否认": "oppose",
            "权威回应": "oppose",  # 权威回应
            "参与": "neutral",
            "导致": "neutral",
            "影响": "neutral",
            "关联": "neutral",
            "报道": "neutral",
            "提供证据": "support",
            "证实": "support",
        }
        
        stances = {}
        for rel in relations:
            source = rel.get("source", "")
            target = rel.get("target", "")
            if not source or not target:
                continue
            rel_id = f"{source}_{target}"
            rel_type = rel.get("type", "关联")
            stances[rel_id] = stance_map.get(rel_type, "neutral")
        return stances
    
    def _build_entity_graph(
        self, 
        entities: List[Dict], 
        relations: List[Dict]
    ) -> Dict[str, List[Tuple[str, str, float]]]:
        """构建实体关系图
        
        Returns:
            {实体名: [(关联实体名, 关系立场, 关系强度), ...]}
        """
        graph = {e.get("name", ""): [] for e in entities if e.get("name")}
        
        for rel in relations:
            source = rel.get("source", "")
            target = rel.get("target", "")
            if not source or not target:
                continue
            
            stance = self.relation_stance.get(f"{source}_{target}", "neutral")
            
            # 关系强度：支持/反对强于中立
            strength = 0.8 if stance != "neutral" else 0.4
            
            if source in graph:
                graph[source].append((target, stance, strength))
            if target in graph:
                graph[target].append((source, stance, strength))
        
        return graph
    
    def compute_influence(
        self,
        agent_opinion: float,
        agent_persona: str,
        exposed_entities: List[str],
        cocoon_strength: float = 0.5,
        response_released: bool = False
    ) -> float:
        """
        计算知识图谱对单个Agent的观点影响
        
        Args:
            agent_opinion: 当前观点 [-1, 1]
            agent_persona: 人设类型
            exposed_entities: 曝光的实体列表
            cocoon_strength: 茧房强度
            response_released: 是否已发布权威回应
        
        Returns:
            观点影响增量
        """
        if not exposed_entities or not self.config.enabled:
            return 0.0
        
        # 获取人设配置
        persona = get_persona_weights(agent_persona)
        
        total_impact = 0.0
        entity_count = 0
        
        for entity_name in exposed_entities:
            if entity_name not in self.entity_impacts:
                continue
            
            # 实体基础影响力
            base_impact = self.entity_impacts.get(entity_name, 0.3)
            
            # 人设调节
            # 意见领袖更受权威实体影响，怀疑论者更难改变
            if base_impact > 0.7:  # 高影响力实体（权威）
                modifier = persona.authority_acceptance
            else:
                modifier = persona.misbelief_susceptibility
            
            # 观点稳定性：稳定性越高，影响越小
            stability_factor = 1.0 - persona.opinion_stability * 0.5
            
            # 茧房效应：同向强化，反向削弱
            # 假设实体立场与新闻整体立场一致（简化）
            entity_stance = 1.0 if base_impact > 0.5 else -0.5  # 正面/负面
            alignment = agent_opinion * entity_stance
            cocoon_effect = 1.0 + cocoon_strength * alignment * 0.3
            
            # 综合影响
            impact = base_impact * modifier * stability_factor * cocoon_effect
            total_impact += impact
            entity_count += 1
        
        if entity_count == 0:
            return 0.0
        
        # 平均影响力 × 证据强度
        avg_impact = total_impact / entity_count
        result = avg_impact * self.config.evidence_strength
        
        # 权威回应效果：正向推动（向真相方向）
        if response_released:
            result += self.config.response_effectiveness * 0.1
        
        # 限制影响幅度
        return np.clip(result, -self.config.max_influence_per_step, self.config.max_influence_per_step)
    
    def compute_batch_influence(
        self,
        opinions: np.ndarray,
        personas: List[str],
        cocoon_strength: float = 0.5,
        response_released: bool = False
    ) -> np.ndarray:
        """
        批量计算对所有Agent的影响力
        
        自动为每个Agent分配最相关的实体（基于网络位置和影响力）
        
        Args:
            opinions: 所有Agent的观点值
            personas: 所有Agent的人设
            cocoon_strength: 茧房强度
            response_released: 是否已发布权威回应
        
        Returns:
            影响力增量数组
        """
        n = len(opinions)
        influences = np.zeros(n)
        
        if not self.entity_names or not self.config.enabled:
            return influences
        
        for i in range(n):
            # 随机选择实体（高影响力实体更容易被关注）
            n_entities = min(
                self.config.max_exposed_entities, 
                len(self.entity_names)
            )
            
            # 按影响力加权随机选择
            if len(self.entity_names) >= n_entities:
                selected_indices = np.random.choice(
                    len(self.entity_names),
                    size=n_entities,
                    replace=False,
                    p=self.entity_weights
                )
                exposed = [self.entity_names[j] for j in selected_indices]
            else:
                exposed = self.entity_names
            
            influences[i] = self.compute_influence(
                agent_opinion=opinions[i],
                agent_persona=personas[i] if i < len(personas) else "普通用户",
                exposed_entities=exposed,
                cocoon_strength=cocoon_strength,
                response_released=response_released
            )
        
        return influences
    
    def get_top_entities(self, n: int = 5) -> List[Tuple[str, float]]:
        """获取影响力最高的N个实体"""
        return [
            (e.get("name", ""), self.entity_impacts.get(e.get("name", ""), 0))
            for e in self.sorted_entities[:n]
            if e.get("name")
        ]
    
    def get_entity_impact_summary(self) -> Dict[str, float]:
        """获取实体影响力摘要（用于前端展示）"""
        # 只返回影响力 > 0.3 的实体
        return {
            name: impact 
            for name, impact in self.entity_impacts.items() 
            if impact > 0.3
        }


# ==================== 验证工具 ====================

class KnowledgeEvolutionValidator:
    """知识驱动演化验证器
    
    用于A/B测试：对比有/无知识图谱驱动的演化差异
    """
    
    @staticmethod
    def compare_trajectories(
        with_knowledge: List[Dict],
        without_knowledge: List[Dict]
    ) -> Dict:
        """
        对比两条演化轨迹
        
        Args:
            with_knowledge: 有知识图谱驱动的演化历史
            without_knowledge: 无知识图谱驱动的演化历史
        
        Returns:
            对比结果
        """
        if not with_knowledge or not without_knowledge:
            return {"error": "轨迹数据为空"}
        
        # 提取关键指标
        def extract_metrics(history):
            return {
                "negative_rates": [h.get("negative_belief_rate", h.get("rumor_spread_rate", 0)) for h in history],
                "truth_rates": [h.get("truth_acceptance_rate", 0) for h in history],
                "polarizations": [h.get("polarization_index", 0) for h in history]
            }
        
        m1 = extract_metrics(with_knowledge)
        m2 = extract_metrics(without_knowledge)

        # 计算差异
        min_len = min(len(m1["negative_rates"]), len(m2["negative_rates"]))

        result = {
            "negative_rate_diff": np.mean(m1["negative_rates"][:min_len]) - np.mean(m2["negative_rates"][:min_len]),
            "truth_rate_diff": np.mean(m1["truth_rates"][:min_len]) - np.mean(m2["truth_rates"][:min_len]),
            "polarization_diff": np.mean(m1["polarizations"][:min_len]) - np.mean(m2["polarizations"][:min_len]),
            "final_negative_diff": m1["negative_rates"][min_len-1] - m2["negative_rates"][min_len-1],
            "final_truth_diff": m1["truth_rates"][min_len-1] - m2["truth_rates"][min_len-1],
            "significant": False
        }

        # 判断是否显著（简化：差异超过5%）
        result["significant"] = abs(result["final_negative_diff"]) > 0.05

        return result

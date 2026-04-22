"""
Engine V3 Integration - 新模块集成适配层

将 Phase 1-4 实现的新模块集成到推演引擎:
- Agent 层: BeliefState, AgentMemory, PersonAgent
- Environment 层: AlgorithmEnv, SocialEnv, TruthEnv, EnvRouter
- 通信系统: P2P, P2G, GroupChat
- 心理学模型: NeedsHierarchy, TPB
- 持久化: ReplayWriter

设计原则:
- 向后兼容：通过 use_v3 参数启用新模块
- 渐进增强：新字段增量添加到现有输出
- 低侵入性：通过适配层隔离新旧实现
"""
from typing import Dict, List, Any, Optional
import numpy as np
import logging
from dataclasses import dataclass, field
from pathlib import Path

from ..simulation.agent import BeliefState, AgentMemory, AgentProfile, PersonAgent
from ..simulation.env import AlgorithmEnv, SocialEnv, TruthEnv, EnvRouter
from ..simulation.message import P2PMessenger, P2GBroadcaster, GroupChat, Message
from ..simulation.psychology import NeedsHierarchy, TheoryOfPlannedBehavior, BehaviorType
from ..simulation.storage import ReplayWriter

logger = logging.getLogger(__name__)


@dataclass
class V3AgentState:
    """v3 Agent 状态扩展"""
    agent_id: int
    
    # 新增信念字段
    rumor_trust: float = 0.0
    truth_trust: float = 0.0
    belief_strength: float = 0.5
    cognitive_closed_need: float = 0.5
    
    # 需求层次
    dominant_need: str = "safety"
    
    # TPB 预测
    predicted_behavior: str = "观望"
    behavior_confidence: float = 0.5
    
    # 记忆统计
    exposure_count: int = 0
    recent_exposure_summary: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "rumor_trust": self.rumor_trust,
            "truth_trust": self.truth_trust,
            "belief_strength": self.belief_strength,
            "cognitive_closed_need": self.cognitive_closed_need,
            "dominant_need": self.dominant_need,
            "predicted_behavior": self.predicted_behavior,
            "behavior_confidence": self.behavior_confidence,
            "exposure_count": self.exposure_count,
            "opinion": self.truth_trust - self.rumor_trust
        }


@dataclass
class V3SimulationContext:
    """v3 推演上下文"""
    step: int = 0
    simulation_id: str = ""
    
    # Environment states
    cocoon_strength: float = 0.5
    social_pressure_avg: float = 0.0
    truth_intervention_active: bool = False
    
    # Statistics
    total_messages: int = 0
    total_exposures: int = 0
    
    # Agent states
    agent_states: List[V3AgentState] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "simulation_id": self.simulation_id,
            "cocoon_strength": self.cocoon_strength,
            "social_pressure_avg": self.social_pressure_avg,
            "truth_intervention_active": self.truth_intervention_active,
            "total_messages": self.total_messages,
            "total_exposures": self.total_exposures,
            "agent_count": len(self.agent_states)
        }


class EngineV3Integration:
    """
    v3 模块集成适配器
    
    职责:
    1. 管理新模块实例的生命周期
    2. 数据格式转换（旧版 ↔ 新版）
    3. 提供统一的接口给 Engine
    """
    
    def __init__(
        self,
        simulation_id: str = "",
        enable_memory: bool = True,
        enable_psychology: bool = True,
        enable_message: bool = True,
        enable_replay: bool = True,
        replay_db_path: Optional[str] = None
    ):
        self.simulation_id = simulation_id
        self.enable_memory = enable_memory
        self.enable_psychology = enable_psychology
        self.enable_message = enable_message
        self.enable_replay = enable_replay
        
        # Environment Layer
        self.algorithm_env = AlgorithmEnv()
        self.social_env = SocialEnv()
        self.truth_env = TruthEnv()
        self.env_router = EnvRouter(
            algorithm_env=self.algorithm_env,
            social_env=self.social_env,
            truth_env=self.truth_env
        )
        
        # Message System
        self.p2p_messenger = P2PMessenger()
        self.p2g_broadcaster = P2GBroadcaster()
        self.group_chat = GroupChat()
        
        # Agent Belief States (indexed by agent_id)
        self.belief_states: Dict[int, BeliefState] = {}
        self.needs_hierarchy: Dict[int, NeedsHierarchy] = {}
        self.tpb_models: Dict[int, TheoryOfPlannedBehavior] = {}
        
        # Memory System (optional)
        self.memory_systems: Dict[int, AgentMemory] = {} if enable_memory else {}
        
        # Replay Writer (optional)
        self.replay_writer: Optional[ReplayWriter] = None
        if enable_replay:
            self.replay_writer = ReplayWriter(db_path=replay_db_path)
        
        # Context
        self.context = V3SimulationContext(simulation_id=simulation_id)
        
        logger.info(f"EngineV3Integration initialized: simulation_id={simulation_id}")
    
    # ==================== 初始化 ====================
    
    def initialize_agents(
        self,
        opinions: np.ndarray,
        belief_strengths: np.ndarray,
        susceptibilities: np.ndarray,
        influences: np.ndarray,
        fear_of_isolations: np.ndarray,
        adjacency: Dict[int, List[int]]
    ):
        """
        从旧版数据初始化 v3 Agent 状态
        
        Args:
            opinions: 观点数组
            belief_strengths: 信念强度数组
            susceptibilities: 易感性数组
            influences: 影响力数组
            fear_of_isolations: 孤立恐惧数组
            adjacency: 网络邻接表
        """
        n = len(opinions)
        
        # 设置网络
        self.social_env.set_network(
            adjacency=adjacency,
            influence={i: influences[i] for i in range(n)},
            opinions={i: opinions[i] for i in range(n)}
        )
        self.p2g_broadcaster.set_adjacency(adjacency)
        
        # 初始化每个 Agent
        for i in range(n):
            # 创建 BeliefState
            self.belief_states[i] = BeliefState.from_legacy_opinion(
                opinion=float(opinions[i]),
                strength=float(belief_strengths[i])
            )
            
            # 创建 NeedsHierarchy
            if self.enable_psychology:
                self.needs_hierarchy[i] = NeedsHierarchy.from_agent_traits(
                    agent_id=i,
                    fear_of_isolation=float(fear_of_isolations[i]),
                    susceptibility=float(susceptibilities[i]),
                    influence=float(influences[i])
                )
                
                # 创建 TPB 模型
                conformity = susceptibilities[i] * 0.6 + fear_of_isolations[i] * 0.4
                if conformity > 0.6:
                    self.tpb_models[i] = TheoryOfPlannedBehavior.for_high_conformity()
                elif influences[i] > 0.7:
                    self.tpb_models[i] = TheoryOfPlannedBehavior.for_independent_thinker()
                else:
                    self.tpb_models[i] = TheoryOfPlannedBehavior.for_high_control()
            
            # 创建 Memory
            if self.enable_memory:
                self.memory_systems[i] = AgentMemory(agent_id=i)
        
        logger.info(f"Initialized {n} v3 agent states")
    
    # ==================== 推演步骤 ====================

    def pre_step(self, step: int):
        """推演前处理"""
        self.context.step = step

        # 推进辟谣环境
        self.truth_env.advance_step(step)

    def process_agent_step(
        self,
        agent_id: int,
        old_opinion: float,
        new_opinion: float,
        neighbors: List[int],
        peer_opinions: List[float],
        algorithm_content: Optional[str] = None,
        truth_content: Optional[str] = None
    ) -> V3AgentState:
        """
        处理单个 Agent 的推演步骤
        
        Args:
            agent_id: Agent ID
            old_opinion: 旧观点
            new_opinion: 新观点
            neighbors: 邻居列表
            peer_opinions: 邻居观点列表
            algorithm_content: 算法推荐内容
            truth_content: 辟谣内容
        
        Returns:
            v3 Agent 状态
        """
        belief = self.belief_states.get(agent_id, BeliefState())
        
        # 1. 更新信念状态
        belief.update_from_opinion(new_opinion)
        
        # 2. 记录信息暴露
        if algorithm_content:
            from ..simulation.agent.belief_state import ExposureSource, ExposureEvent
            belief.add_exposure(ExposureEvent(
                step=self.context.step,
                source=ExposureSource.ALGORITHM,
                content=algorithm_content,
                alignment=new_opinion * 0.5  # 茧房效应
            ))
        
        if truth_content:
            from ..simulation.agent.belief_state import ExposureSource, ExposureEvent
            belief.add_exposure(ExposureEvent(
                step=self.context.step,
                source=ExposureSource.TRUTH,
                content=truth_content,
                alignment=1.0,
                credibility=0.7
            ))
        
        # 3. 心理学预测行为
        predicted_behavior = "观望"
        behavior_confidence = 0.5
        
        if self.enable_psychology and agent_id in self.tpb_models:
            tpb = self.tpb_models[agent_id]
            needs = self.needs_hierarchy.get(agent_id)
            
            if needs:
                needs.compute_dominant_level()
                content_type = "threat" if new_opinion < -0.3 else "knowledge"
                receptivity = needs.compute_information_receptivity(content_type)
            else:
                receptivity = 1.0
            
            # 计算 TPB
            import random
            result = tpb.compute_full(
                info_credibility=random.uniform(0.4, 0.8),
                content_relevance=0.5 + abs(new_opinion) * 0.3,
                cognitive_dissonance=max(0, abs(new_opinion - old_opinion) - 0.1),
                social_pressure=sum(peer_opinions) / len(peer_opinions) if peer_opinions else 0,
                conformity_tendency=0.5,
                media_literacy=0.5,
                current_opinion=new_opinion
            )
            
            predicted_behavior = result.predicted_behavior.value
            behavior_confidence = result.confidence
        
        # 4. 存储到记忆
        if self.enable_memory and agent_id in self.memory_systems:
            self.memory_systems[agent_id].store_belief(belief, self.context.step)
        
        # 5. 构建 V3AgentState
        needs = self.needs_hierarchy.get(agent_id)
        state = V3AgentState(
            agent_id=agent_id,
            rumor_trust=belief.rumor_trust,
            truth_trust=belief.truth_trust,
            belief_strength=belief.belief_strength,
            cognitive_closed_need=belief.cognitive_closed_need,
            dominant_need=needs.dominant_level.value if needs else "safety",
            predicted_behavior=predicted_behavior,
            behavior_confidence=behavior_confidence,
            exposure_count=len(belief.exposure_history),
            recent_exposure_summary=belief.get_exposure_summary()
        )
        
        # 更新缓存
        self.belief_states[agent_id] = belief
        
        return state
    
    def post_step(self, agent_states: List[V3AgentState]):
        """推演后处理"""
        self.context.agent_states = agent_states

        # 统计
        self.context.total_exposures = sum(s.exposure_count for s in agent_states) if agent_states else 0

        # 持久化（可选）
        if self.replay_writer:
            for state in agent_states:
                self.replay_writer.save_belief(
                    simulation_id=self.simulation_id,
                    agent_id=state.agent_id,
                    step=self.context.step,
                    rumor_trust=state.rumor_trust,
                    truth_trust=state.truth_trust,
                    belief_strength=state.belief_strength,
                    cognitive_closed_need=state.cognitive_closed_need,
                    opinion=state.truth_trust - state.rumor_trust
                )

    # ==================== Environment 操作 ====================

    async def get_algorithm_content(self, agent_id: int, opinion: float) -> str:
        """获取算法推荐内容"""
        return await self.algorithm_env.call_tool("observe", agent_id, opinion)

    async def get_peer_opinions(self, agent_id: int) -> List[float]:
        """获取邻居观点"""
        return await self.social_env.call_tool("get_peer_opinions", agent_id)

    def add_truth_intervention(
        self,
        content: str,
        step: Optional[int] = None,
        credibility: float = 0.7
    ):
        """添加辟谣干预（同步版本）"""
        self.truth_env.add_intervention(content, step=step or self.context.step, credibility=credibility)

    def get_truth_intervention(self, agent_id: int) -> Optional[str]:
        """获取辟谣内容（同步版本）"""
        return self.truth_env.get_intervention(agent_id)
    
    # ==================== 工具方法 ====================
    
    def get_agent_v3_fields(self, agent_id: int) -> Dict[str, Any]:
        """获取 Agent 的 v3 扩展字段"""
        belief = self.belief_states.get(agent_id, BeliefState())
        needs = self.needs_hierarchy.get(agent_id)
        tpb = self.tpb_models.get(agent_id)
        
        fields = {
            "rumor_trust": belief.rumor_trust,
            "truth_trust": belief.truth_trust,
            "belief_strength": belief.belief_strength,
            "cognitive_closed_need": belief.cognitive_closed_need
        }
        
        if needs:
            fields["dominant_need"] = needs.dominant_level.value
            fields["needs_description"] = needs.get_description()
        
        if tpb:
            fields["tpb_weights"] = tpb.to_dict()
            # 使用 belief 数据计算行为预测，参数动态化
            opinion_diff = belief.truth_trust - belief.rumor_trust
            info_cred = min(1.0, 0.3 + abs(opinion_diff) * 0.7)
            content_rel = min(1.0, 0.4 + abs(opinion_diff) * 0.6)
            cog_dissonance = max(0, 0.8 - abs(opinion_diff)) * 0.5
            social_press = min(1.0, 0.3 + abs(belief.belief_strength - 0.5) * 0.7)
            conformity = 0.3 + (1.0 - belief.belief_strength) * 0.4
            media_lit = 0.3 + belief.belief_strength * 0.4
            result = tpb.compute_full(
                info_credibility=info_cred,
                content_relevance=content_rel,
                cognitive_dissonance=cog_dissonance,
                social_pressure=social_press,
                conformity_tendency=conformity,
                media_literacy=media_lit,
                current_opinion=opinion_diff
            )
            fields["predicted_behavior"] = result.predicted_behavior.value
            fields["behavior_confidence"] = result.confidence

        return fields
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取 v3 统计信息"""
        if not self.belief_states:
            return {}
        
        avg_rumor_trust = np.mean([b.rumor_trust for b in self.belief_states.values()])
        avg_truth_trust = np.mean([b.truth_trust for b in self.belief_states.values()])
        
        # 需求分布
        need_distribution = {}
        for needs in self.needs_hierarchy.values():
            level = needs.dominant_level.value
            need_distribution[level] = need_distribution.get(level, 0) + 1

        # 行为预测分布
        behavior_distribution = {}
        for agent_id, belief in self.belief_states.items():
            tpb = self.tpb_models.get(agent_id)
            if tpb:
                opinion_diff = belief.truth_trust - belief.rumor_trust
                info_cred = min(1.0, 0.3 + abs(opinion_diff) * 0.7)
                content_rel = min(1.0, 0.4 + abs(opinion_diff) * 0.6)
                cog_dissonance = max(0, 0.8 - abs(opinion_diff)) * 0.5
                social_press = min(1.0, 0.3 + abs(belief.belief_strength - 0.5) * 0.7)
                conformity = 0.3 + (1.0 - belief.belief_strength) * 0.4
                media_lit = 0.3 + belief.belief_strength * 0.4
                result = tpb.compute_full(
                    info_credibility=info_cred,
                    content_relevance=content_rel,
                    cognitive_dissonance=cog_dissonance,
                    social_pressure=social_press,
                    conformity_tendency=conformity,
                    media_literacy=media_lit,
                    current_opinion=opinion_diff
                )
                bkey = result.predicted_behavior.value
                behavior_distribution[bkey] = behavior_distribution.get(bkey, 0) + 1

        return {
            "avg_rumor_trust": avg_rumor_trust,
            "avg_truth_trust": avg_truth_trust,
            "avg_belief_strength": np.mean([b.belief_strength for b in self.belief_states.values()]),
            "need_distribution": need_distribution,
            "behavior_distribution": behavior_distribution,
            "total_exposures": self.context.total_exposures,
            "truth_intervention_active": self.context.truth_intervention_active
        }
    
    def reset(self):
        """重置所有状态"""
        self.belief_states.clear()
        self.needs_hierarchy.clear()
        self.tpb_models.clear()

        if self.enable_memory:
            for memory in self.memory_systems.values():
                memory.clear()
            self.memory_systems.clear()

        self.p2p_messenger.clear()
        self.p2g_broadcaster.clear()
        self.group_chat.clear()

        self.context = V3SimulationContext(simulation_id=self.simulation_id)
    
    def close(self):
        """关闭资源"""
        if self.replay_writer:
            self.replay_writer.close()
        
        for memory in self.memory_systems.values():
            memory.close()

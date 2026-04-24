"""
推演引擎核心
支持 LLM 驱动和数学模型两种模式
支持沙盘推演和新闻推演两种运行模式

v3.0 新增:
- use_v3: 启用新版 Agent/Environment/Psychology 模块
- 新增字段: rumor_trust, truth_trust, dominant_need, predicted_behavior
"""
import numpy as np
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime, timezone
from pathlib import Path
import asyncio
import logging
import uuid

from .agents import AgentPopulation
from .llm_agents import LLMAgentPopulation
from .persona import AGENT_DECISION_SNAPSHOTS
from .math_model_enhanced import EnhancedMathModel, EnhancedMathParams
from .knowledge_evolution import KnowledgeDrivenEvolution, KnowledgeEvolutionConfig
from .engine_v3 import EngineV3Integration
from .agent import BeliefState
from ..models.schemas import SimulationState, SimulationMode
from ..constants import OPINION_THRESHOLD_NEGATIVE, OPINION_THRESHOLD_POSITIVE
from ..llm.client import LLMClient, LLMConfig

logger = logging.getLogger(__name__)


class SimulationEngine:
    """
    信息茧房推演引擎

    支持两种模式:
    1. LLM 模式: Agent 通过大模型决策观点变化
    2. 数学模型模式: 使用数学公式计算观点变化

    支持两种运行模式:
    1. 沙盘模式(SANDBOX): 参数驱动，研究传播机制
    2. 新闻模式(NEWS): 真实分布锚定，预测现实演进

    核心机制:
    1. 算法茧房效应: 根据用户观点推荐相似内容, 强化既有观点
    2. 社交传播: 个体受邻居影响更新观点
    3. 官方权威回应: 延迟后发布正确认知, 影响观点
    """

    def __init__(
        self,
        population_size: int = 200,
        cocoon_strength: float = 0.5,
        response_delay: int = 10,
        initial_negative_spread: float = 0.3,
        network_type: str = "small_world",
        use_llm: bool = True,
        llm_config: Optional[LLMConfig] = None,
        seed: Optional[int] = None,
        # 增强版数学模型参数
        response_credibility: float = 0.7,
        authority_factor: float = 0.5,
        backfire_strength: float = 0.3,
        silence_threshold: float = 0.3,
        polarization_factor: float = 0.3,
        echo_chamber_factor: float = 0.2,
        # Phase 3: 运行模式参数
        mode: str = "sandbox",
        init_distribution: Optional[Dict[str, float]] = None,
        time_acceleration: float = 1.0,
        # 兼容旧参数名（别名）
        debunk_delay: Optional[int] = None,
        initial_rumor_spread: Optional[float] = None,
        debunk_credibility: Optional[float] = None,
        # v3.0 新增参数
        use_v3: bool = True,
        v3_replay_db: Optional[str] = None,
        # 初始分布系数参数 (issue #283)
        news_base_negative_spread: float = 0.3,
        news_negative_boost: float = 0.15,
        news_positive_penalty: float = 0.05,
        news_entity_factor_per_entity: float = 0.015,
        news_entity_factor_max: float = 0.1,
        news_min_spread: float = 0.1,
        news_max_spread: float = 0.6,
        # 观点范围参数 (issue #289)
        opinion_range_rumor_low: float = -0.8,
        opinion_range_rumor_high: float = -0.2,
        opinion_range_truth_low: float = 0.2,
        opinion_range_truth_high: float = 0.8,
        opinion_range_neutral_radius: float = 0.05
    ):
        # 处理兼容参数：优先使用新参数名，旧参数名作为别名
        if debunk_delay is not None:
            response_delay = debunk_delay
        if initial_rumor_spread is not None:
            initial_negative_spread = initial_rumor_spread
        if debunk_credibility is not None:
            response_credibility = debunk_credibility
        self.population_size = population_size
        self.cocoon_strength = cocoon_strength
        self.response_delay = response_delay
        self.initial_negative_spread = initial_negative_spread
        self.network_type = network_type
        self.use_llm = use_llm

        # 随机种子和生成器 (issue #307)
        self.seed = seed if seed is not None else 42
        self._rng = np.random.default_rng(self.seed)
        self.llm_config = llm_config or LLMConfig()

        # 增强版数学模型参数
        self.response_credibility = response_credibility
        self.authority_factor = authority_factor
        self.backfire_strength = backfire_strength
        self.silence_threshold = silence_threshold
        self.polarization_factor = polarization_factor
        self.echo_chamber_factor = echo_chamber_factor

        # Phase 3: 运行模式
        self.mode = SimulationMode(mode) if isinstance(mode, str) else mode
        self.init_distribution = init_distribution
        self.time_acceleration = time_acceleration

        self.step_count = 0
        self.responded = False  # 新名称（兼容属性debunked会返回此值）
        self.current_state: Optional[SimulationState] = None

        # 增强版数学模型实例
        math_params = EnhancedMathParams(
            cocoon_strength=cocoon_strength,
            debunk_delay=response_delay,  # 内部使用旧参数名
            debunk_credibility=response_credibility,  # 内部使用旧参数名
            authority_factor=authority_factor,
            backfire_strength=backfire_strength,
            silence_threshold=silence_threshold,
            polarization_factor=polarization_factor,
            echo_chamber_factor=echo_chamber_factor
        )
        self.math_model = EnhancedMathModel(math_params, seed=self.seed)

        # 历史记录
        self.history: List[Dict] = []

        # 报告相关
        self.report_dir = Path(__file__).parent.parent.parent / "reports"
        self.report_dir.mkdir(exist_ok=True)
        self.start_time: Optional[str] = None

        # Agent 群体 (根据模式选择)
        self.population: Optional[AgentPopulation] = None
        self.llm_population: Optional[LLMAgentPopulation] = None
        self.llm_client: Optional[LLMClient] = None

        # 进度回调
        self.progress_callback: Optional[Callable] = None

        # 新闻和知识图谱
        self.news_content: str = ""  # 兼容：最后一个新闻
        self.news_source: str = "public"
        self.knowledge_graph: Dict = {}
        self.news_credibility: str = "不确定"  # 新闻可信度：高可信/低可信/不确定

        # 事件池：存储所有注入的新闻事件
        self.event_pool: List[Dict] = []  # [{"content": ..., "source": ..., "credibility": ..., "step": ...}, ...]

        # 知识驱动演化器（Phase 1 新增）
        self.knowledge_evolution: Optional[KnowledgeDrivenEvolution] = None
        self.use_knowledge_evolution: bool = False

        # v3.0 集成层
        self.use_v3 = use_v3
        self.v3: Optional[EngineV3Integration] = None
        if use_v3:
            self.v3 = EngineV3Integration(
                simulation_id=str(uuid.uuid4())[:8],
                enable_memory=True,
                enable_psychology=True,
                enable_message=True,
                enable_replay=bool(v3_replay_db),
                replay_db_path=v3_replay_db
            )

        # 初始分布系数参数
        self.news_base_negative_spread = news_base_negative_spread
        self.news_negative_boost = news_negative_boost
        self.news_positive_penalty = news_positive_penalty
        self.news_entity_factor_per_entity = news_entity_factor_per_entity
        self.news_entity_factor_max = news_entity_factor_max
        self.news_min_spread = news_min_spread
        self.news_max_spread = news_max_spread
        # 观点范围参数
        self.opinion_range_rumor_low = opinion_range_rumor_low
        self.opinion_range_rumor_high = opinion_range_rumor_high
        self.opinion_range_truth_low = opinion_range_truth_low
        self.opinion_range_truth_high = opinion_range_truth_high
        self.opinion_range_neutral_radius = opinion_range_neutral_radius

    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback

    @property
    def debunked(self) -> bool:
        """向后兼容属性：debunked → responded"""
        return self.responded

    @debunked.setter
    def debunked(self, value: bool):
        self.responded = value

    def set_news(self, content: str, source: str = "public", parse_graph: bool = True):
        """
        设置新闻内容和来源

        Args:
            content: 新闻内容
            source: 来源 (public/private)
            parse_graph: 是否解析知识图谱（数学模型不使用）
        """
        self.news_content = content
        self.news_source = source
        # 注意：数学模型模式不解析知识图谱
    
    def set_knowledge_graph(
        self,
        entities: List[Dict],
        relations: List[Dict],
        config: KnowledgeEvolutionConfig = None,
        merge: bool = True
    ):
        """
        设置知识图谱，启用知识驱动演化

        Args:
            entities: 实体列表
            relations: 关系列表
            config: 知识演化配置
            merge: 是否与现有图谱融合（默认True）
        """
        if not entities:
            logger.warning("实体列表为空，不启用知识驱动演化")
            return

        # 融合模式：与现有图谱合并
        if merge and self.knowledge_graph and self.knowledge_graph.get("entities"):
            from .knowledge_evolution import merge_knowledge_graphs
            incoming_graph = {"entities": entities, "relations": relations}
            merged = merge_knowledge_graphs(self.knowledge_graph, incoming_graph)
            entities = merged.get("entities", entities)
            relations = merged.get("relations", relations)
            self.knowledge_graph = merged
            logger.info(f"知识图谱已融合: {len(entities)} 实体, {len(relations)} 关系")
        else:
            self.knowledge_graph = {
                "entities": entities,
                "relations": relations
            }
            logger.info(f"知识图谱已设置: {len(entities)} 实体, {len(relations)} 关系")

        self.knowledge_evolution = KnowledgeDrivenEvolution(
            entities=entities,
            relations=relations,
            config=config
        )
        self.use_knowledge_evolution = True

    def broadcast_event(
        self,
        content: str,
        target_scope: str = "all",
        impact_strength: float = None,
        sentiment: str = "中性",
        credibility: str = "不确定"
    ) -> Dict:
        """
        向全网或特定圈层广播突发事件

        Args:
            content: 事件内容
            target_scope: 目标范围 (all/public/private)
            impact_strength: 冲击强度 (0-1)，None则自动计算
            sentiment: 情感倾向 (正面/中性/负面)
            credibility: 可信度 (高可信/不确定/低可信)

        Returns:
            事件数据
        """
        # 存储新闻可信度（用于后续统计判定）
        self.news_credibility = credibility

        # 更新当前新闻（兼容旧逻辑）
        self.news_content = content

        event = {
            "content": content,
            "scope": target_scope,
            "step": self.step_count,
            "sentiment": sentiment,
            "credibility": credibility,
            "impact_strength": impact_strength or 0.0
        }

        # 添加到事件池
        self.event_pool.append(event)

        # 如果引擎已初始化，触发事件冲击
        if self.population is not None or self.llm_population is not None:
            impact = self._apply_event_impact(
                content=content,
                target_scope=target_scope,
                impact_strength=impact_strength,
                sentiment=sentiment,
                credibility=credibility
            )
            event["impact_strength"] = impact["strength"]
            event["affected_agents"] = impact["affected_count"]
            event["avg_opinion_shift"] = impact["avg_shift"]

        return event

    def _apply_event_impact(
        self,
        content: str,
        target_scope: str = "all",
        impact_strength: float = None,
        sentiment: str = "中性",
        credibility: str = "不确定"
    ) -> Dict:
        """
        应用事件冲击到Agent群体

        冲击效果：
        - 负面新闻：推高误信率（观点向-1偏移）
        - 正面新闻：推高正面信念率（观点向+1偏移）
        - 可信度影响冲击强度

        Args:
            content: 事件内容
            target_scope: 目标范围
            impact_strength: 冲击强度
            sentiment: 情感倾向
            credibility: 可信度

        Returns:
            冲击效果统计
        """
        # 计算冲击强度
        if impact_strength is None:
            impact_strength = self._calculate_event_impact(sentiment, credibility)

        # 确定受影响的Agent范围
        if self.use_llm and self.llm_population:
            pop = self.llm_population
            opinions = np.array([a.opinion for a in pop.agents])
            influence = np.array([a.influence for a in pop.agents])
        else:
            pop = self.population
            opinions = pop.opinions
            influence = pop.influence

        # 根据target_scope确定影响范围
        if target_scope == "public":
            # 公域广场：主要影响影响力高的节点（大V）
            affected_mask = influence > np.percentile(influence, 50)
        elif target_scope == "private":
            # 私域茧房：主要影响普通节点
            affected_mask = influence <= np.percentile(influence, 50)
        else:
            # 全网
            affected_mask = np.ones(len(opinions), dtype=bool)

        # 计算观点偏移
        # 负面新闻 → 观点向-1偏移（相信负面信念）
        # 正面新闻 → 观点向+1偏移（相信正面信念）
        # 中性新闻 → 轻微随机波动
        if sentiment == "负面":
            shift_direction = -1
        elif sentiment == "正面":
            shift_direction = 1
        else:
            shift_direction = 0
            impact_strength *= 0.3  # 中性新闻冲击减弱

        # 应用冲击
        old_opinions = opinions.copy()
        impact_values = np.zeros(len(opinions))

        for i in range(len(opinions)):
            if affected_mask[i]:
                # 影响力越高的节点，受冲击影响越大（更敏感）
                sensitivity = 0.5 + 0.5 * influence[i]
                shift = shift_direction * impact_strength * sensitivity * self._rng.uniform(0.5, 1.5)
                opinions[i] = np.clip(opinions[i] + shift, -1, 1)
                impact_values[i] = shift

        # 更新观点
        if self.use_llm and self.llm_population:
            for i, agent in enumerate(pop.agents):
                agent.opinion = opinions[i]
        else:
            pop.opinions = opinions
            pop.invalidate_cache()

        # 计算统计
        avg_shift = np.mean(np.abs(impact_values[affected_mask])) if np.any(affected_mask) else 0

        logger.info(f"事件冲击: 强度={impact_strength:.3f}, 情感={sentiment}, "
                   f"影响{np.sum(affected_mask)}个Agent, 平均偏移={avg_shift:.4f}")

        return {
            "strength": impact_strength,
            "affected_count": int(np.sum(affected_mask)),
            "avg_shift": float(avg_shift)
        }

    def _calculate_event_impact(self, sentiment: str, credibility: str) -> float:
        """
        根据情感和可信度计算事件冲击强度

        Args:
            sentiment: 情感倾向
            credibility: 可信度

        Returns:
            冲击强度 (0-1)
        """
        # 情感强度
        sentiment_strength = {
            "负面": 0.15,  # 负面新闻冲击最大
            "正面": 0.10,
            "中性": 0.05
        }.get(sentiment, 0.05)

        # 可信度调节
        credibility_factor = {
            "高可信": 1.3,
            "不确定": 1.0,
            "低可信": 0.7
        }.get(credibility, 1.0)

        # 如果有知识图谱，考虑实体影响力
        entity_boost = 0.0
        if self.use_knowledge_evolution and self.knowledge_evolution:
            # 高影响力实体数量增加冲击
            entity_boost = min(0.1, len(self.knowledge_evolution.entities) * 0.02)

        impact = (sentiment_strength * credibility_factor) + entity_boost
        return min(impact, 0.3)  # 最大冲击0.3

    def set_initial_distribution_from_news(
        self,
        sentiment: str = "中性",
        credibility: str = "不确定",
        entity_count: int = 0
    ):
        """
        根据新闻内容设置初始观点分布

        替代固定的 initial_negative_spread 参数

        Args:
            sentiment: 情感倾向
            credibility: 可信度
            entity_count: 实体数量
        """
        # 基础误信率
        base_negative_spread = self.news_base_negative_spread

        # 情感影响
        if sentiment == "负面":
            negative_boost = self.news_negative_boost
        elif sentiment == "正面":
            negative_boost = -self.news_negative_boost * 0.33  # 正面情感约1/3反向抵消
        else:
            negative_boost = 0.0

        # 可信度影响
        if credibility == "低可信":
            positive_penalty = self.news_positive_penalty
        elif credibility == "高可信":
            positive_penalty = -self.news_positive_penalty * 0.6  # 高可信约60%反向
        else:
            positive_penalty = 0.0

        # 实体影响
        entity_factor = min(self.news_entity_factor_max, entity_count * self.news_entity_factor_per_entity)

        # 计算最终初始误信率
        self.initial_negative_spread = np.clip(
            base_negative_spread + negative_boost + positive_penalty + entity_factor,
            self.news_min_spread, self.news_max_spread
        )

        logger.info(f"根据新闻设置初始分布: 情感={sentiment}, 可信度={credibility}, "
                   f"实体数={entity_count}, 初始误信率={self.initial_negative_spread:.3f}")

    def initialize(self) -> SimulationState:
        """初始化模拟"""
        self.step_count = 0
        self.responded = False
        self.history = []
        self.start_time = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.event_pool = []  # 清空事件池
        self.news_content = ""
        self.news_credibility = "不确定"

        logger.info(f"初始化推演引擎: 模式={self.mode.value}, 人口={self.population_size}")

        if self.use_llm:
            # LLM 模式
            self.llm_population = LLMAgentPopulation(
                size=self.population_size,
                initial_negative_spread=self.initial_negative_spread,
                initial_rumor_spread=self.initial_negative_spread,  # 兼容旧参数名
                network_type=self.network_type,
                llm_config=self.llm_config
            )
            self.llm_client = LLMClient(self.llm_config)

            # 新闻模式：应用真实分布锚定
            if self.mode == SimulationMode.NEWS and self.init_distribution:
                self._apply_init_distribution_llm()
        else:
            # 数学模型模式
            self.population = AgentPopulation(
                size=self.population_size,
                initial_negative_spread=self.initial_negative_spread,
                initial_rumor_spread=self.initial_negative_spread,  # 兼容旧参数名
                network_type=self.network_type
            )

            # 新闻模式：应用真实分布锚定
            if self.mode == SimulationMode.NEWS and self.init_distribution:
                self._apply_init_distribution()

        # v3.0: 先初始化 v3 Agent 状态（必须在 _compute_state 之前）
        if self.use_v3 and self.v3:
            self._initialize_v3()

        self.current_state = self._compute_state()
        self.history.append(self.current_state.to_dict())

        return self.current_state

    def _initialize_v3(self):
        """
        初始化 v3 集成层

        从现有 population 数据初始化 v3 Agent 状态
        """
        if not self.v3:
            return
        
        if self.use_llm and self.llm_population:
            pop = self.llm_population
            opinions = np.array([a.opinion for a in pop.agents])
            belief_strengths = np.array([a.belief_strength for a in pop.agents])
            susceptibilities = np.array([a.susceptibility for a in pop.agents])
            influences = np.array([a.influence for a in pop.agents])
            fear_of_isolations = np.array([getattr(a, 'fear_of_isolation', 0.5) for a in pop.agents])
            
            # 构建邻接表
            adjacency = {}
            if hasattr(pop, 'graph'):
                import networkx as nx
                for i in range(pop.size):
                    adjacency[i] = list(pop.graph.neighbors(i))
            else:
                for i in range(pop.size):
                    adjacency[i] = []
        else:
            pop = self.population
            opinions = pop.opinions
            belief_strengths = pop.belief_strength
            susceptibilities = pop.susceptibility
            influences = pop.influence
            fear_of_isolations = pop.fear_of_isolation
            
            # 构建邻接表
            adjacency = {}
            for i in range(pop.size):
                adjacency[i] = pop.get_neighbors(i)
        
        # 初始化 v3 Agent 状态
        self.v3.initialize_agents(
            opinions=opinions,
            belief_strengths=belief_strengths,
            susceptibilities=susceptibilities,
            influences=influences,
            fear_of_isolations=fear_of_isolations,
            adjacency=adjacency
        )
        
        logger.info(f"v3 Integration initialized: {len(self.v3.belief_states)} agents")

    def _apply_init_distribution(self):
        """
        应用真实分布锚定（数学模型模式）

        根据真实舆情分布初始化 Agent 观点
        """
        dist = self.init_distribution
        n = self.population_size

        believe_rumor = dist.get("believe_rumor", 0)
        believe_truth = dist.get("believe_truth", 0)
        neutral = dist.get("neutral", 1 - believe_rumor - believe_truth)

        # 计算各群体数量
        n_rumor = int(n * believe_rumor)
        n_truth = int(n * believe_truth)
        n_neutral = n - n_rumor - n_truth

        logger.info(f"应用真实分布锚定: 误信={n_rumor}, 正面信念={n_truth}, 中立={n_neutral}")

        # 生成观点值
        opinions = np.zeros(n)

        # 相信负面信念 (opinion < 0 为误信)
        if n_rumor > 0:
            opinions[:n_rumor] = self._rng.uniform(
                self.opinion_range_rumor_low, self.opinion_range_rumor_high, n_rumor)

        # 相信正面信念 (opinion > 0 为正确认知)
        start = n_rumor
        end = start + n_truth
        if n_truth > 0:
            opinions[start:end] = self._rng.uniform(
                self.opinion_range_truth_low, self.opinion_range_truth_high, n_truth)

        # 不确定 (接近0)
        if n_neutral > 0:
            r = self.opinion_range_neutral_radius
            opinions[end:] = self._rng.uniform(-r, r, n_neutral)

        # 随机打乱
        self._rng.shuffle(opinions)

        # 应用到群体
        self.population.opinions = opinions

        # 更新暴露状态 (阈值0)
        self.population.exposed_to_negative = opinions < 0
        self.population.exposed_to_positive = opinions > 0

    def _apply_init_distribution_llm(self):
        """
        应用真实分布锚定（LLM模式）

        根据真实舆情分布初始化 LLM Agent 观点
        """
        dist = self.init_distribution
        n = self.population_size

        believe_rumor = dist.get("believe_rumor", 0)
        believe_truth = dist.get("believe_truth", 0)

        n_rumor = int(n * believe_rumor)
        n_truth = int(n * believe_truth)

        logger.info(f"LLM模式应用真实分布锚定: 误信={n_rumor}, 正面信念={n_truth}")

        for i, agent in enumerate(self.llm_population.agents):
            if i < n_rumor:
                agent.opinion = self._rng.uniform(
                    self.opinion_range_rumor_low, self.opinion_range_rumor_high)
            elif i < n_rumor + n_truth:
                agent.opinion = self._rng.uniform(
                    self.opinion_range_truth_low, self.opinion_range_truth_high)
            else:
                r = self.opinion_range_neutral_radius
                agent.opinion = self._rng.uniform(-r, r)

    async def async_step(self) -> SimulationState:
        """
        异步执行单步推演

        在 LLM 模式下使用异步批量决策
        """
        if self.use_llm and self.llm_population is None:
            raise RuntimeError("请先调用 initialize()")
        if not self.use_llm and self.population is None:
            raise RuntimeError("请先调用 initialize()")

        self.step_count += 1

        # v3: 推演前处理
        if self.use_v3 and self.v3:
            self.v3.pre_step(self.step_count)

        # 检查是否发布权威回应
        if self.step_count >= self.response_delay and not self.responded:
            self._release_authority_response()
            # v3: 添加辟谣干预
            if self.use_v3 and self.v3:
                self.v3.add_truth_intervention(
                    content="官方权威回应",
                    step=self.step_count,
                    credibility=self.response_credibility
                )

        if self.use_llm:
            # LLM 驱动模式
            await self._llm_step()
        else:
            # 数学模型模式
            self._math_step()

        # v3: 推演后处理
        if self.use_v3 and self.v3:
            self.v3.post_step([])  # Agent states already updated in belief_states

        # 计算新状态
        self.current_state = self._compute_state()
        self.history.append(self.current_state.to_dict())

        return self.current_state

    def step(self) -> SimulationState:
        """同步执行单步推演 (数学模型模式)"""
        if self.use_llm:
            raise RuntimeError("LLM 模式请使用 async_step()")

        if self.population is None:
            raise RuntimeError("请先调用 initialize()")

        self.step_count += 1

        # v3: 推演前处理
        if self.use_v3 and self.v3:
            self.v3.pre_step(self.step_count)

        # 检查是否发布权威回应
        if self.step_count >= self.response_delay and not self.responded:
            self._release_authority_response()
            # v3: 添加辟谣干预
            if self.use_v3 and self.v3:
                self.v3.add_truth_intervention(
                    content="官方权威回应",
                    step=self.step_count,
                    credibility=self.response_credibility
                )

        # 数学模型模式 - 直接调用同步方法
        self._math_step()

        # v3: 更新信念状态
        if self.use_v3 and self.v3 and self.population:
            for i in range(self.population.size):
                belief = self.v3.belief_states.get(i, BeliefState())
                belief.update_from_opinion(float(self.population.opinions[i]))
                self.v3.belief_states[i] = belief

        # v3: 推演后处理
        if self.use_v3 and self.v3:
            self.v3.post_step([])

        # 计算新状态
        self.current_state = self._compute_state()
        self.history.append(self.current_state.to_dict())

        return self.current_state

    async def _llm_step(self):
        """LLM 驱动的推演步骤"""
        pop = self.llm_population

        async with self.llm_client:
            # 批量异步决策（传入知识图谱）
            await pop.batch_decide(
                self.llm_client,
                response_released=self.responded,
                cocoon_strength=self.cocoon_strength,
                progress_callback=self.progress_callback,
                knowledge_graph=self.knowledge_graph  # 传入知识图谱
            )

        # 随机扰动
        for agent in pop.agents:
            noise = self._rng.normal(0, 0.01)
            agent.opinion = np.clip(agent.opinion + noise, -1, 1)

    def _math_step(self):
        """
        数学模型推演步骤 - 使用增强版数学模型

        整合的社会心理学机制：
        1. 增强版社交传播影响（观点相似度权重、权威效应、回音室效应）
        2. 算法茧房效应
        3. 沉默的螺旋
        4. 群体极化效应
        5. 权威回应与逆火效应
        6. 认知失调
        7. 知识图谱驱动演化（Phase 1 新增）
        """
        pop = self.population
        old_opinions = pop.opinions.copy()

        # 获取邻居列表
        neighbors_list = [pop.get_neighbors(i) for i in range(pop.size)]

        # 使用增强版数学模型计算一步
        new_opinions, new_belief, is_silent, metrics = self.math_model.compute_step(
            opinions=pop.opinions,
            belief_strength=pop.belief_strength,
            influence=pop.influence,
            susceptibility=pop.susceptibility,
            fear_of_isolation=pop.fear_of_isolation,
            neighbors=neighbors_list,
            influencer_ids=self._get_influencer_ids(),
            response_released=self.responded,
            step_count=self.step_count
        )
        
        # === Phase 1: 知识图谱驱动演化 ===
        if self.use_knowledge_evolution and self.knowledge_evolution:
            personas = self._get_personas()
            knowledge_influence = self.knowledge_evolution.compute_batch_influence(
                opinions=new_opinions,
                personas=personas,
                cocoon_strength=self.cocoon_strength,
                response_released=self.responded  # 已重命名参数
            )
            
            # 应用知识影响
            new_opinions = np.clip(new_opinions + knowledge_influence, -1, 1)
            
            avg_influence = np.mean(np.abs(knowledge_influence))
            if avg_influence > 0.001:
                logger.debug(f"知识驱动演化: 平均影响 {avg_influence:.4f}")

        # 更新状态
        pop.opinions = new_opinions
        pop.belief_strength = new_belief
        pop.is_silent = is_silent

        # 标记曝光正确认知（权威回应后）
        if self.responded:
            pop.exposed_to_positive = np.ones(pop.size, dtype=bool)

        # 记录指标到日志
        logger.debug(f"Math model metrics: {metrics}")

        # === 为每个 Agent 生成决策快照 ===
        self._generate_math_snapshots(old_opinions, new_opinions, is_silent, neighbors_list)

    def _get_influencer_ids(self, percentile: float = 95) -> List[int]:
        """
        获取意见领袖ID列表

        Args:
            percentile: 影响力百分位阈值，默认95表示前5%为意见领袖

        Returns:
            意见领袖Agent ID列表
        """
        if self.population is None:
            return []

        pop = self.population
        threshold = np.percentile(pop.influence, percentile)
        return list(np.where(pop.influence >= threshold)[0])
    
    def _get_personas(self) -> List[str]:
        """
        获取所有Agent的人设类型
        
        用于知识驱动演化的人设调节
        """
        if self.population is None:
            return []
        
        # 从population获取人设，如果没有则返回默认值
        personas = []
        for i in range(self.population.size):
            # 检查是否有personas属性
            if hasattr(self.population, 'personas') and self.population.personas is not None:
                personas.append(self.population.personas[i])
            else:
                # 基于影响力分配默认人设
                influence = self.population.influence[i]
                if influence > np.percentile(self.population.influence, 90):
                    personas.append("意见领袖")
                elif influence > np.percentile(self.population.influence, 70):
                    personas.append("媒体账号")
                else:
                    personas.append("普通用户")
        
        return personas

    def _generate_math_snapshots(
        self,
        old_opinions: np.ndarray,
        new_opinions: np.ndarray,
        is_silent: np.ndarray,
        neighbors_list: List[List[int]]
    ):
        """
        为数学模型模式生成决策快照

        基于数学模型的计算结果，为每个 Agent 生成决策理由
        """
        pop = self.population
        influencer_ids = set(self._get_influencer_ids())

        for i in range(pop.size):
            old_op = old_opinions[i]
            new_op = new_opinions[i]
            opinion_change = new_op - old_op
            neighbors = neighbors_list[i]

            # 生成决策理由
            reasons = []

            # 1. 社交影响分析
            if neighbors:
                # 过滤无效的邻居索引，防止越界
                valid_neighbors = [n for n in neighbors if 0 <= n < len(old_opinions)]
                if valid_neighbors:
                    neighbor_opinions = old_opinions[valid_neighbors]
                    avg_neighbor_op = np.mean(neighbor_opinions)
                    opinion_gap = avg_neighbor_op - old_op

                    if abs(opinion_gap) > 0.1:
                        direction = "正面信念" if opinion_gap > 0 else "负面信念"
                        reasons.append(f"邻居平均观点偏向{direction}(差距{abs(opinion_gap):.2f})")

                # 检查意见领袖影响
                influencer_neighbors = [n for n in neighbors if n in influencer_ids]
                if influencer_neighbors:
                    reasons.append(f"受{len(influencer_neighbors)}位意见领袖影响")

            # 2. 茧房效应
            cocoon_effect = self.cocoon_strength * old_op * 0.1
            if abs(cocoon_effect) > 0.01:
                direction = "强化" if old_op < 0 else "正面信念方向"
                reasons.append(f"算法推荐{direction}观点")

            # 3. 沉默状态
            if is_silent[i]:
                reasons.append(f"因孤立恐惧(恐惧值{pop.fear_of_isolation[i]:.2f})选择沉默")
            elif pop.fear_of_isolation[i] > 0.6:
                reasons.append("孤立恐惧较高但未沉默")

            # 4. 权威回应影响
            if self.responded and old_op < 0:
                if new_op > old_op:
                    reasons.append("收到权威回应信息，观点向正确认知偏移")
                elif new_op < old_op:
                    reasons.append("权威回应触发逆火效应，观点反加强")

            # 5. 观点变化总结
            if abs(opinion_change) < 0.01:
                reasons.append("观点基本稳定")
            elif opinion_change > 0:
                reasons.append(f"观点向正面信念偏移{abs(opinion_change):.3f}")
            else:
                reasons.append(f"观点向负面信念偏移{abs(opinion_change):.3f}")

            reasoning = "；".join(reasons) if reasons else "观点微调"

            # 构建快照
            snapshot = {
                "agent_id": i,
                "persona": {"type": "数学模型Agent", "desc": "基于增强版数学模型决策"},
                "persona_str": "数学模型Agent - 基于增强版数学模型决策",
                "belief_strength": float(pop.belief_strength[i]),
                "susceptibility": float(pop.susceptibility[i]),
                "influence": float(pop.influence[i]),
                "old_opinion": float(old_op),
                "new_opinion": float(new_op),
                "received_news": ["权威回应信息"] if self.responded else [],
                "llm_raw_response": None,  # 数学模型无LLM响应
                "emotion": "冷静",
                "action": "沉默" if is_silent[i] else "观望",
                "generated_comment": "",
                "reasoning": reasoning,
                "has_decided": True,
                # 沉默的螺旋相关
                "fear_of_isolation": float(pop.fear_of_isolation[i]),
                "conviction": float(pop.conviction[i]),
                "is_silent": bool(is_silent[i]),
                "perceived_climate": {
                    "neighbor_count": len(neighbors),
                    "avg_neighbor_opinion": float(np.mean(old_opinions[neighbors])) if neighbors else 0.0
                }
            }

            # 保存到全局存储
            AGENT_DECISION_SNAPSHOTS[i] = snapshot

    def _release_authority_response(self):
        """
        发布官方权威回应信息

        权威回应效果现在由增强版数学模型在 compute_step 中统一处理，
        包括逆火效应。这里只标记权威回应已发布。
        """
        self.responded = True
        logger.info(f"Step {self.step_count}: 发布权威回应")

    def _compute_state(self) -> SimulationState:
        """计算当前状态统计"""
        if self.use_llm:
            pop = self.llm_population
            opinion_dist = pop.get_opinion_histogram()
            stats = pop.get_statistics()
            agents = pop.to_agent_list()
            edges = pop.get_edges()
        else:
            pop = self.population
            opinion_dist = pop.get_opinion_histogram()
            # 基础统计：opinion 与新闻接受度直接对应
            opinions = pop.opinions
            belief_strengths = pop.belief_strength
            # 三个互斥类别：拒绝/中立/相信
            reject_mask = opinions < OPINION_THRESHOLD_NEGATIVE
            uncertain_mask = np.abs(opinions) <= min(abs(OPINION_THRESHOLD_NEGATIVE), OPINION_THRESHOLD_POSITIVE)
            believe_mask = opinions > OPINION_THRESHOLD_POSITIVE

            believe_rate = float(np.mean(believe_mask))
            reject_rate = float(np.mean(reject_mask))
            uncertain_rate = float(np.mean(uncertain_mask))

            stats = {
                # 基础统计（与 opinion 直接对应）
                "believe_rate": believe_rate,
                "reject_rate": reject_rate,
                "uncertain_rate": uncertain_rate,
                # 深度统计
                "deep_believe_rate": float(np.mean(believe_mask & (belief_strengths > 0.5))),
                "deep_reject_rate": float(np.mean(reject_mask & (belief_strengths > 0.5))),
                "weighted_believe_index": float(
                    np.mean(np.maximum(opinions, 0) * belief_strengths)
                    if np.any(believe_mask) else 0.0
                ),
                "avg_opinion": float(np.mean(opinions)),
                "polarization_index": float(min(1.0, EnhancedMathModel.compute_polarization_index(opinions))),
                "silence_rate": float(np.mean(pop.is_silent))
            }
            agents = pop.to_agent_list()
            edges = pop.get_edges()

        # 根据新闻可信度后验判定误信/正确认知
        credibility = self.news_credibility
        believe_rate = stats.get("believe_rate", stats.get("positive_belief_rate", 0.0))
        reject_rate = stats.get("reject_rate", stats.get("negative_belief_rate", 0.0))
        deep_believe_rate = stats.get("deep_believe_rate", stats.get("deep_positive_rate", 0.0))
        deep_reject_rate = stats.get("deep_reject_rate", stats.get("deep_negative_rate", 0.0))
        weighted_believe_index = stats.get("weighted_believe_index", stats.get("weighted_negative_index", 0.0))

        if credibility == "高可信":
            # 真实新闻：相信=正确认知，拒绝=误信
            mislead_rate = reject_rate
            correct_rate = believe_rate
            deep_mislead_rate = deep_reject_rate
            deep_correct_rate = deep_believe_rate
            weighted_mislead_index = stats.get("weighted_reject_index", 0.0)  # 暂无此字段
        elif credibility == "低可信":
            # 虚假新闻：相信=误信，拒绝=正确认知
            mislead_rate = believe_rate
            correct_rate = reject_rate
            deep_mislead_rate = deep_believe_rate
            deep_correct_rate = deep_reject_rate
            weighted_mislead_index = weighted_believe_index
        else:
            # 不确定：使用传统语义，拒绝=误信，相信=正确认知
            mislead_rate = reject_rate
            correct_rate = believe_rate
            deep_mislead_rate = deep_reject_rate
            deep_correct_rate = deep_believe_rate
            weighted_mislead_index = 1.0 - weighted_believe_index  # 反转

        # Phase 3: 计算实体影响摘要
        entity_impact_summary = None
        if self.mode == SimulationMode.NEWS and self.knowledge_evolution:
            entity_impact_summary = self.knowledge_evolution.entity_impacts

        # v3.0: 获取 v3 统计
        v3_stats = {}
        if self.use_v3 and self.v3:
            v3_stats = self.v3.get_statistics()
            
            # 为每个 Agent 添加 v3 字段（创建新字典避免修改原数据）
            agents = [
                {**agent_dict, **self.v3.get_agent_v3_fields(agent_dict.get('id', 0))}
                for agent_dict in agents
            ]

        return SimulationState(
            step=self.step_count,
            agents=agents,
            edges=edges,
            opinion_distribution=opinion_dist,
            # 基础统计
            believe_rate=believe_rate,
            reject_rate=reject_rate,
            uncertain_rate=stats.get("uncertain_rate", 0.0),
            deep_believe_rate=deep_believe_rate,
            deep_reject_rate=deep_reject_rate,
            weighted_believe_index=weighted_believe_index,
            # 后验判定
            news_credibility=credibility,
            mislead_rate=mislead_rate,
            correct_rate=correct_rate,
            # 兼容旧字段
            negative_belief_rate=mislead_rate,
            positive_belief_rate=correct_rate,
            deep_negative_rate=deep_mislead_rate,
            deep_positive_rate=deep_correct_rate,
            weighted_negative_index=weighted_mislead_index,
            avg_opinion=stats["avg_opinion"],
            polarization_index=stats["polarization_index"],
            silence_rate=stats.get("silence_rate", 0.0),
            mode=self.mode.value,
            entity_impact_summary=entity_impact_summary,
            # v3.0 统计
            avg_rumor_trust=v3_stats.get("avg_rumor_trust", 0.0),
            avg_truth_trust=v3_stats.get("avg_truth_trust", 0.0),
            need_distribution=v3_stats.get("need_distribution"),
            behavior_distribution=v3_stats.get("behavior_distribution"),
            total_exposures=v3_stats.get("total_exposures", 0),
            truth_intervention_active=v3_stats.get("truth_intervention_active", False)
        )

    def generate_report(self) -> str:
        """生成模拟报告并保存为MD文件"""
        if not self.history:
            return ""

        final_state = self.history[-1]
        initial_state = self.history[0]

        # 兼容新旧字段名
        negative_trend = [h.get('negative_belief_rate', h.get('rumor_spread_rate', 0)) for h in self.history]
        positive_trend = [h.get('positive_belief_rate', h.get('truth_acceptance_rate', 0)) for h in self.history]
        opinion_trend = [h['avg_opinion'] for h in self.history]
        polarization_trend = [h['polarization_index'] for h in self.history]

        final_result = self._analyze_result(final_state)
        cocoon_effect = self._analyze_cocoon_effect()
        response_effect = self._analyze_response_effect(negative_trend, positive_trend)

        mode_str = "LLM 驱动" if self.use_llm else "数学模型"

        report = f"""# 信息茧房推演报告

> 生成时间: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
> 推演模式: {mode_str}

## 模拟参数

| 参数 | 值 |
|------|-----|
| 群体规模 | {self.population_size} 人 |
| 算法茧房强度 | {self.cocoon_strength:.2f} |
| 官方权威回应延迟 | {self.response_delay} 步 |
| 初始误信率 | {self.initial_negative_spread:.0%} |
| 社交网络类型 | {self._network_type_name()} |
| 总推演步数 | {len(self.history) - 1} 步 |

## 模拟结果摘要

### 最终状态

| 指标 | 初始值 | 最终值 | 变化 |
|------|--------|--------|------|
| 误信率 | {initial_state.get('negative_belief_rate', initial_state.get('rumor_spread_rate', 0)):.1%} | {final_state.get('negative_belief_rate', final_state.get('rumor_spread_rate', 0)):.1%} | {self._change_arrow(initial_state.get('negative_belief_rate', initial_state.get('rumor_spread_rate', 0)), final_state.get('negative_belief_rate', final_state.get('rumor_spread_rate', 0)))} |
| 正面信念率 | {initial_state.get('positive_belief_rate', initial_state.get('truth_acceptance_rate', 0)):.1%} | {final_state.get('positive_belief_rate', final_state.get('truth_acceptance_rate', 0)):.1%} | {self._change_arrow(initial_state.get('positive_belief_rate', initial_state.get('truth_acceptance_rate', 0)), final_state.get('positive_belief_rate', final_state.get('truth_acceptance_rate', 0)))} |
| 平均观点 | {initial_state['avg_opinion']:.3f} | {final_state['avg_opinion']:.3f} | {self._change_arrow(initial_state['avg_opinion'], final_state['avg_opinion'], reverse=True)} |
| 极化指数 | {initial_state['polarization_index']:.3f} | {final_state['polarization_index']:.3f} | {self._change_arrow(initial_state['polarization_index'], final_state['polarization_index'], reverse=True)} |

### 结论: {final_result['title']}

{final_result['description']}

---

## 详细分析

### 1. 算法茧房效应分析

{cocoon_effect}

### 2. 权威回应效果分析

{response_effect}

### 3. 极化趋势分析

{self._analyze_polarization(polarization_trend)}

---

## 建议

{self._generate_recommendations(final_state)}

---

*本报告由信息茧房推演系统自动生成*
"""

        report_filename = f"report_{self.start_time}.md"
        report_path = self.report_dir / report_filename
        report_path.write_text(report, encoding='utf-8')

        return str(report_path)

    def _network_type_name(self) -> str:
        """获取网络类型中文名称"""
        names = {
            "small_world": "小世界网络",
            "scale_free": "无标度网络",
            "random": "随机网络"
        }
        return names.get(self.network_type, self.network_type)

    def _change_arrow(self, old: float, new: float, reverse: bool = False) -> str:
        """生成变化指示箭头"""
        diff = new - old
        if abs(diff) < 0.01:
            return "→ 稳定"
        if reverse:
            return "↓ 下降" if diff > 0 else "↑ 上升"
        return "↑ 上升" if diff > 0 else "↓ 下降"

    def _analyze_result(self, final_state: Dict) -> Dict:
        """分析最终结果"""
        rumor_rate = final_state.get('negative_belief_rate', final_state.get('rumor_spread_rate', 0))
        truth_rate = final_state.get('positive_belief_rate', final_state.get('truth_acceptance_rate', 0))
        polarization = final_state['polarization_index']

        if rumor_rate > 0.5:
            return {
                'title': '⚠️ 误信占主导',
                'description': f'最终有{rumor_rate:.0%}的人持有负面信念，仅{truth_rate:.0%}接受正面信念。'
            }
        elif truth_rate > 0.5:
            return {
                'title': '✅ 正面信念占主导',
                'description': f'最终有{truth_rate:.0%}的人接受正面信念，仅{rumor_rate:.0%}持有负面信念。'
            }
        elif polarization > 0.8:
            return {
                'title': '⚡ 社会严重撕裂',
                'description': f'极化指数达{polarization:.2f}，群体呈现两极分化。'
            }
        else:
            return {
                'title': '⚖️ 群体趋于中立',
                'description': f'多数人持中立态度，误信率{rumor_rate:.0%}，正面信念率{truth_rate:.0%}。'
            }

    def _analyze_cocoon_effect(self) -> str:
        """分析茧房效应"""
        if self.cocoon_strength < 0.3:
            return f"茧房强度较低({self.cocoon_strength:.2f})，算法推荐对观点强化作用有限。"
        elif self.cocoon_strength > 0.7:
            return f"茧房强度较高({self.cocoon_strength:.2f})，算法推荐显著强化既有观点。"
        else:
            return f"茧房强度中等({self.cocoon_strength:.2f})，存在一定程度的茧房效应。"

    def _analyze_response_effect(self, negative_trend: List, positive_trend: List) -> str:
        """分析权威回应效果"""
        if self.response_delay >= len(self.history):
            return "本次模拟未触发权威回应机制。"

        response_step = self.response_delay
        if response_step < len(negative_trend):
            before_negative = negative_trend[max(0, response_step-2)]
            after_negative = negative_trend[min(response_step+3, len(negative_trend)-1)]
            effect = before_negative - after_negative

            if effect > 0.1:
                return f"权威回应在第{self.response_delay}步发布后，误信率从{before_negative:.1%}下降至{after_negative:.1%}，**效果显著**。"
            elif effect > 0:
                return f"权威回应在第{self.response_delay}步发布后，误信率小幅下降{effect:.1%}。"
            else:
                return "权威回应后误信率未明显下降，可能回应时机过晚。"

        return "权威回应效果数据不足。"

    def _analyze_polarization(self, polarization_trend: List) -> str:
        """分析极化趋势"""
        if len(polarization_trend) < 2:
            return "数据不足以分析极化趋势。"

        initial = polarization_trend[0]
        final = polarization_trend[-1]

        if final > initial * 1.5:
            return f"极化指数从{initial:.3f}上升至{final:.3f}，**社会撕裂加剧**。"
        elif final < initial * 0.8:
            return f"极化指数从{initial:.3f}下降至{final:.3f}，**社会共识增强**。"
        else:
            return f"极化指数维持在{initial:.3f}~{final:.3f}区间，相对稳定。"

    def _generate_recommendations(self, final_state: Dict) -> str:
        """生成建议"""
        recommendations = []

        if final_state.get('negative_belief_rate', final_state.get('rumor_spread_rate', 0)) > 0.4:
            recommendations.append("- 建议提前权威回应时间，减少误信发酵期")

        if final_state['polarization_index'] > 0.7:
            recommendations.append("- 高极化风险，建议降低算法茧房强度")

        if self.cocoon_strength > 0.6 and final_state.get('negative_belief_rate', final_state.get('rumor_spread_rate', 0)) > 0.3:
            recommendations.append("- 茧房效应过强阻碍正面信念传播，建议优化推荐算法")

        if not recommendations:
            recommendations.append("- 当前参数配置下舆论状况良好")

        return "\n".join(recommendations)

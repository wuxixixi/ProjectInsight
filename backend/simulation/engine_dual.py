"""
推演引擎核心 - 双层模态信息场版本
支持公域/私域双层网络的信息传播模拟
"""
import numpy as np
from typing import Optional, Dict, List, Callable
from datetime import datetime
from pathlib import Path
import asyncio
import logging

from .agents import AgentPopulation
from .llm_agents import LLMAgentPopulation, AGENT_DECISION_SNAPSHOTS
from .llm_agents_dual import LLMAgentPopulationDual
from .dual_network import DualLayerNetwork
from .math_model_enhanced import EnhancedMathModel, EnhancedMathParams
from .knowledge_evolution import KnowledgeDrivenEvolution, KnowledgeEvolutionConfig
from .graph_parser_agent import GraphParserAgent, get_graph_parser
from ..models.schemas import SimulationState
from ..llm.client import LLMClient, LLMConfig

logger = logging.getLogger(__name__)


class SimulationEngineDual:
    """
    双层模态信息场推演引擎

    支持:
    1. 公域网络 (无标度网络): 模拟微博/抖音等公共平台
    2. 私域网络 (随机块模型): 模拟微信群/朋友圈等私密社群
    3. LLM 驱动的 Agent 决策
    4. 沉默的螺旋机制
    """

    def __init__(
        self,
        population_size: int = 200,
        cocoon_strength: float = 0.5,
        debunk_delay: int = 10,
        initial_rumor_spread: float = 0.3,
        use_llm: bool = True,
        llm_config: Optional[LLMConfig] = None,
        # 双层网络参数
        num_communities: int = 8,
        public_m: int = 3,
        intra_community_prob: float = 0.3,
        inter_community_prob: float = 0.01,
        # 增强版数学模型参数
        debunk_credibility: float = 0.7,
        authority_factor: float = 0.5,
        backfire_strength: float = 0.3,
        silence_threshold: float = 0.3,
        polarization_factor: float = 0.3,
        echo_chamber_factor: float = 0.2
    ):
        self.population_size = population_size
        self.cocoon_strength = cocoon_strength
        self.debunk_delay = debunk_delay
        self.initial_rumor_spread = initial_rumor_spread
        self.use_llm = use_llm
        self.llm_config = llm_config or LLMConfig()

        # 双层网络参数
        self.num_communities = num_communities
        self.public_m = public_m

        # 增强版数学模型参数
        self.debunk_credibility = debunk_credibility
        self.authority_factor = authority_factor
        self.backfire_strength = backfire_strength
        self.silence_threshold = silence_threshold
        self.polarization_factor = polarization_factor
        self.echo_chamber_factor = echo_chamber_factor

        self.step_count = 0
        self.debunked = False
        self.current_state: Optional[SimulationState] = None

        # 增强版数学模型实例
        math_params = EnhancedMathParams(
            cocoon_strength=cocoon_strength,
            debunk_delay=debunk_delay,
            debunk_credibility=debunk_credibility,
            authority_factor=authority_factor,
            backfire_strength=backfire_strength,
            silence_threshold=silence_threshold,
            polarization_factor=polarization_factor,
            echo_chamber_factor=echo_chamber_factor
        )
        self.math_model = EnhancedMathModel(math_params)

        # 历史记录
        self.history: List[Dict] = []

        # 报告相关
        self.report_dir = Path(__file__).parent.parent.parent / "reports"
        self.report_dir.mkdir(exist_ok=True)
        self.start_time: Optional[str] = None

        # Agent 群体
        self.population: Optional[AgentPopulation] = None
        self.llm_population: Optional[LLMAgentPopulationDual] = None
        self.llm_client: Optional[LLMClient] = None
        self.dual_network: Optional[DualLayerNetwork] = None  # 非 LLM 模式下的双层网络

        # 进度回调
        self.progress_callback: Optional[Callable] = None

        # 新闻内容（模拟热点事件）
        self.news_content = "某地发生重大事件，网络上流传各种说法..."
        self.news_source = "public"  # 默认公域信息
        self.knowledge_graph: Dict = {}  # 知识图谱数据
        self._graph_parser: Optional[GraphParserAgent] = None  # 图谱解析器
        
        # 知识驱动演化器（Phase 1 新增）
        self.knowledge_evolution: Optional[KnowledgeDrivenEvolution] = None
        self.use_knowledge_evolution: bool = False

        # === 事件注入池 ===
        self.event_pool: List[Dict] = []  # 存储所有注入的事件
        self.pending_events: List[Dict] = []  # 待处理的事件（将在下一步推演时应用）

    @property
    def graph_parser(self) -> GraphParserAgent:
        """获取图谱解析器（延迟初始化）"""
        if self._graph_parser is None:
            self._graph_parser = get_graph_parser(self.llm_config)
        return self._graph_parser

    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback

    async def set_news(self, content: str, source: str = "public", parse_graph: bool = True):
        """
        设置新闻内容和来源，并解析知识图谱

        Args:
            content: 新闻内容
            source: 来源 (public/private)
            parse_graph: 是否解析知识图谱
        """
        self.news_content = content
        self.news_source = source
        
        if parse_graph:
            # 解析知识图谱
            logger.info("正在解析新闻知识图谱...")
            self.knowledge_graph = await self.graph_parser.parse(content)
            logger.info(f"知识图谱解析完成: {len(self.knowledge_graph.get('entities', []))} 个实体")

    def set_knowledge_graph(
        self,
        entities: List[Dict],
        relations: List[Dict],
        config: KnowledgeEvolutionConfig = None
    ):
        """
        设置知识图谱，启用知识驱动演化
        
        Args:
            entities: 实体列表
            relations: 关系列表
            config: 知识演化配置
        """
        if not entities:
            logger.warning("实体列表为空，不启用知识驱动演化")
            return
        
        self.knowledge_evolution = KnowledgeDrivenEvolution(
            entities=entities,
            relations=relations,
            config=config
        )
        self.use_knowledge_evolution = True
        logger.info(f"知识图谱已设置，启用知识驱动演化: {len(entities)} 实体, {len(relations)} 关系")
        
        # 记录知识图谱
        self.knowledge_graph = {
            "entities": entities,
            "relations": relations
        }

    def broadcast_event(
        self,
        content: str,
        target_scope: str = "all"
    ) -> Dict:
        """
        向全网或特定圈层广播突发事件

        Args:
            content: 事件文本内容
            target_scope: 投放范围
                - "all": 全网广播
                - "public_only": 仅公域广场
                - "private_only": 仅私域茧房

        Returns:
            事件记录字典
        """
        event = {
            "step": self.step_count,
            "content": content,
            "target_scope": target_scope,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 添加到事件池
        self.event_pool.append(event)
        self.pending_events.append(event)

        logger.info(f"Step {self.step_count}: 注入突发事件 [{target_scope}] {content[:50]}...")

        return event

    def consume_pending_events(self) -> List[Dict]:
        """
        获取并清空待处理的事件列表

        Returns:
            待处理的事件列表
        """
        events = self.pending_events.copy()
        self.pending_events = []
        return events

    def get_event_timeline(self) -> List[Dict]:
        """
        获取事件时间线（用于前端 MarkLine 显示）

        Returns:
            事件列表，每个事件包含 step 和 content
        """
        return [
            {
                "step": e["step"],
                "content": e["content"],
                "scope": e["target_scope"]
            }
            for e in self.event_pool
        ]

    def initialize(self) -> SimulationState:
        """初始化模拟"""
        self.step_count = 0
        self.debunked = False
        self.history = []
        self.start_time = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.use_llm:
            # LLM 模式 - 双层网络版本
            self.llm_population = LLMAgentPopulationDual(
                size=self.population_size,
                initial_rumor_spread=self.initial_rumor_spread,
                llm_config=self.llm_config,
                num_communities=self.num_communities,
                public_m=self.public_m,
                intra_community_prob=0.3,
                inter_community_prob=0.01
            )
            self.llm_client = LLMClient(self.llm_config)
        else:
            # 数学模型模式 - 也创建双层网络用于统计
            self.population = AgentPopulation(
                size=self.population_size,
                initial_rumor_spread=self.initial_rumor_spread,
                network_type="scale_free"  # 使用无标度网络作为默认
            )
            # 创建双层网络用于统计
            self.dual_network = DualLayerNetwork(
                size=self.population_size,
                public_m=self.public_m,
                num_communities=self.num_communities,
                intra_community_prob=0.3,
                inter_community_prob=0.01
            )

        self.current_state = self._compute_state()
        self.history.append(self.current_state.to_dict())

        return self.current_state

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

        # 检查是否发布辟谣
        if self.step_count >= self.debunk_delay and not self.debunked:
            self._release_debunking()

        if self.use_llm:
            # LLM 驱动模式
            await self._llm_step_dual()
        else:
            # 数学模型模式
            self._math_step()

        # 计算新状态
        self.current_state = self._compute_state()
        self.history.append(self.current_state.to_dict())

        return self.current_state

    def step(self) -> SimulationState:
        """
        同步执行单步推演 (数学模型模式)
        
        注意：LLM 模式请使用 async_step()
        """
        if self.use_llm:
            raise RuntimeError("LLM 模式请使用 async_step()")

        if self.population is None:
            raise RuntimeError("请先调用 initialize()")

        self.step_count += 1

        # 检查是否发布辟谣
        if self.step_count >= self.debunk_delay and not self.debunked:
            self._release_debunking()

        # 数学模型模式 - 直接调用同步方法
        self._math_step()

        # 计算新状态
        self.current_state = self._compute_state()
        self.history.append(self.current_state.to_dict())

        return self.current_state

    async def _llm_step_dual(self):
        """LLM 驱动的双层网络推演步骤"""
        pop = self.llm_population

        async with self.llm_client:
            # 批量异步决策（包含知识图谱）
            await pop.batch_decide_dual(
                self.llm_client,
                news_content=self.news_content,
                news_source=self.news_source,
                knowledge_graph=self.knowledge_graph,
                debunk_released=self.debunked,
                cocoon_strength=self.cocoon_strength,
                progress_callback=self.progress_callback
            )

        # 随机扰动
        for agent in pop.agents:
            noise = np.random.normal(0, 0.01)
            agent.opinion = np.clip(agent.opinion + noise, -1, 1)

    def _math_step(self):
        """
        数学模型推演步骤 - 使用增强版数学模型

        整合的社会心理学机制：
        1. 增强版社交传播影响（观点相似度权重、权威效应、回音室效应）
        2. 算法茧房效应
        3. 沉默的螺旋
        4. 群体极化效应
        5. 辟谣与逆火效应
        6. 认知失调
        7. 知识图谱驱动演化（Phase 1 新增）
        """
        pop = self.population
        old_opinions = pop.opinions.copy()

        # 获取邻居列表
        neighbors_list = [pop.get_neighbors(i) for i in range(pop.size)]

        # 获取意见领袖ID（来自双层网络）
        influencer_ids = self._get_influencer_ids()

        # 使用增强版数学模型计算一步
        new_opinions, new_belief, is_silent, metrics = self.math_model.compute_step(
            opinions=pop.opinions,
            belief_strength=pop.belief_strength,
            influence=pop.influence,
            susceptibility=pop.susceptibility,
            fear_of_isolation=pop.fear_of_isolation,
            neighbors=neighbors_list,
            influencer_ids=influencer_ids,
            debunk_released=self.debunked,
            step_count=self.step_count
        )
        
        # === Phase 1: 知识图谱驱动演化 ===
        if self.use_knowledge_evolution and self.knowledge_evolution:
            personas = self._get_personas()
            knowledge_influence = self.knowledge_evolution.compute_batch_influence(
                opinions=new_opinions,
                personas=personas,
                cocoon_strength=self.cocoon_strength,
                debunk_released=self.debunked
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

        # 标记曝光真相（辟谣后）
        if self.debunked:
            pop.exposed_to_truth = np.ones(pop.size, dtype=bool)

        # 记录指标到日志
        logger.debug(f"Math model metrics: {metrics}")

        # === 为每个 Agent 生成决策快照 ===
        self._generate_math_snapshots(old_opinions, new_opinions, is_silent, neighbors_list)

    def _get_influencer_ids(self) -> List[int]:
        """获取意见领袖ID列表"""
        if self.dual_network:
            return list(self.dual_network.influencer_ids)
        elif self.population:
            threshold = np.percentile(self.population.influence, 95)
            return list(np.where(self.population.influence >= threshold)[0])
        return []
    
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
                neighbor_opinions = old_opinions[neighbors]
                avg_neighbor_op = np.mean(neighbor_opinions)
                opinion_gap = avg_neighbor_op - old_op

                if abs(opinion_gap) > 0.1:
                    direction = "真相" if opinion_gap > 0 else "谣言"
                    reasons.append(f"邻居平均观点偏向{direction}(差距{abs(opinion_gap):.2f})")

                # 检查意见领袖影响
                influencer_neighbors = [n for n in neighbors if n in influencer_ids]
                if influencer_neighbors:
                    reasons.append(f"受{len(influencer_neighbors)}位意见领袖影响")

            # 2. 茧房效应
            cocoon_effect = self.cocoon_strength * old_op * 0.1
            if abs(cocoon_effect) > 0.01:
                direction = "强化" if old_op < 0 else "真相方向"
                reasons.append(f"算法推荐{direction}观点")

            # 3. 沉默状态
            if is_silent[i]:
                reasons.append(f"因孤立恐惧(恐惧值{pop.fear_of_isolation[i]:.2f})选择沉默")
            elif pop.fear_of_isolation[i] > 0.6:
                reasons.append("孤立恐惧较高但未沉默")

            # 4. 辟谣影响
            if self.debunked and old_op < 0:
                if new_op > old_op:
                    reasons.append("收到辟谣信息，观点向真相偏移")
                elif new_op < old_op:
                    reasons.append("辟谣触发逆火效应，观点反加强")

            # 5. 观点变化总结
            if abs(opinion_change) < 0.01:
                reasons.append("观点基本稳定")
            elif opinion_change > 0:
                reasons.append(f"观点向真相偏移{abs(opinion_change):.3f}")
            else:
                reasons.append(f"观点向谣言偏移{abs(opinion_change):.3f}")

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
                "received_news": ["辟谣信息"] if self.debunked else [],
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

    def _release_debunking(self):
        """
        发布官方辟谣信息

        辟谣效果现在由增强版数学模型在 compute_step 中统一处理，
        包括逆火效应。这里只标记辟谣已发布。
        """
        self.debunked = True
        logger.info(f"Step {self.step_count}: 发布辟谣")

    def _compute_state(self) -> SimulationState:
        """计算当前状态统计"""
        if self.use_llm:
            pop = self.llm_population
            opinion_dist = pop.get_opinion_histogram()
            stats = pop.get_statistics()
            agents = pop.to_agent_list()
            public_edges = pop.get_public_edges()
            private_edges = pop.get_private_edges()
        else:
            pop = self.population
            opinion_dist = pop.get_opinion_histogram()
            stats = {
                "rumor_spread_rate": float(np.mean(pop.opinions < -0.2)),
                "truth_acceptance_rate": float(np.mean(pop.opinions > 0.2)),
                "avg_opinion": float(np.mean(pop.opinions)),
                "polarization_index": float(np.std(pop.opinions) * 2),
                "silence_rate": float(np.mean(pop.is_silent)),
            }
            agents = pop.to_agent_list()

            # 使用双层网络获取边和统计
            if self.dual_network:
                public_edges = self.dual_network.get_public_edges()
                private_edges = self.dual_network.get_private_edges()
                stats["public_rumor_rate"] = stats["rumor_spread_rate"]
                stats["public_truth_rate"] = stats["truth_acceptance_rate"]
                stats["private_rumor_rate"] = stats["rumor_spread_rate"]
                stats["private_truth_rate"] = stats["truth_acceptance_rate"]
                stats["num_communities"] = self.dual_network.num_communities
                stats["num_influencers"] = len(self.dual_network.influencer_ids)
            else:
                public_edges = pop.get_edges()
                private_edges = []
                stats["public_rumor_rate"] = stats["rumor_spread_rate"]
                stats["public_truth_rate"] = stats["truth_acceptance_rate"]
                stats["private_rumor_rate"] = stats["rumor_spread_rate"]
                stats["private_truth_rate"] = stats["truth_acceptance_rate"]
                stats["num_communities"] = 0
                stats["num_influencers"] = 0

        return SimulationState(
            step=self.step_count,
            agents=agents,
            public_edges=public_edges,
            private_edges=private_edges,
            edges=public_edges,  # 兼容旧版
            opinion_distribution=opinion_dist,
            rumor_spread_rate=stats["rumor_spread_rate"],
            truth_acceptance_rate=stats["truth_acceptance_rate"],
            avg_opinion=stats["avg_opinion"],
            polarization_index=stats["polarization_index"],
            silence_rate=stats.get("silence_rate", 0.0),
            public_rumor_rate=stats.get("public_rumor_rate", stats["rumor_spread_rate"]),
            public_truth_rate=stats.get("public_truth_rate", stats["truth_acceptance_rate"]),
            private_rumor_rate=stats.get("private_rumor_rate", stats["rumor_spread_rate"]),
            private_truth_rate=stats.get("private_truth_rate", stats["truth_acceptance_rate"]),
            num_communities=stats.get("num_communities", 0),
            num_influencers=stats.get("num_influencers", 0)
        )

    def get_network_info(self) -> Dict:
        """获取双层网络元信息"""
        if self.use_llm and self.llm_population:
            dn = self.llm_population.dual_network
            return {
                "num_nodes": self.population_size,
                "num_communities": dn.num_communities,
                "num_influencers": len(dn.influencer_ids),
                "public_edges": dn.public_graph.number_of_edges(),
                "private_edges": dn.private_graph.number_of_edges(),
                "influencer_ids": dn.influencer_ids
            }
        return {
            "num_nodes": self.population_size,
            "num_communities": 0,
            "num_influencers": 0,
            "public_edges": 0,
            "private_edges": 0,
            "influencer_ids": []
        }

    def generate_report(self) -> str:
        """生成模拟报告"""
        if not self.history:
            return ""

        final_state = self.history[-1]
        initial_state = self.history[0]

        mode_str = "LLM 驱动（双层网络）" if self.use_llm else "数学模型"

        report = f"""# 信息茧房推演报告（双层模态版本）

> 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 推演模式: {mode_str}

## 模拟参数

| 参数 | 值 |
|------|-----|
| 群体规模 | {self.population_size} 人 |
| 算法茧房强度 | {self.cocoon_strength:.2f} |
| 官方辟谣延迟 | {self.debunk_delay} 步 |
| 初始谣言传播率 | {self.initial_rumor_spread:.0%} |
| 社群数量 | {self.num_communities} |
| 总推演步数 | {len(self.history) - 1} 步 |

## 模拟结果摘要

### 整体状态

| 指标 | 初始值 | 最终值 |
|------|--------|--------|
| 谣言传播率 | {initial_state['rumor_spread_rate']:.1%} | {final_state['rumor_spread_rate']:.1%} |
| 真相接受率 | {initial_state['truth_acceptance_rate']:.1%} | {final_state['truth_acceptance_rate']:.1%} |
| 沉默率 | {initial_state.get('silence_rate', 0):.1%} | {final_state.get('silence_rate', 0):.1%} |

### 公域 vs 私域对比

| 渠道 | 谣言率 | 真相率 |
|------|--------|--------|
| 公域网络 | {final_state.get('public_rumor_rate', 0):.1%} | {final_state.get('public_truth_rate', 0):.1%} |
| 私域网络 | {final_state.get('private_rumor_rate', 0):.1%} | {final_state.get('private_truth_rate', 0):.1%} |

---

*本报告由信息茧房推演系统（双层模态版本）自动生成*
"""

        report_filename = f"report_dual_{self.start_time}.md"
        report_path = self.report_dir / report_filename
        report_path.write_text(report, encoding='utf-8')

        return str(report_path)

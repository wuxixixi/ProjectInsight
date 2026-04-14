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
from .llm_agents import LLMAgentPopulation
from .llm_agents_dual import LLMAgentPopulationDual
from .dual_network import DualLayerNetwork
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
        inter_community_prob: float = 0.01
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

        self.step_count = 0
        self.debunked = False
        self.current_state: Optional[SimulationState] = None

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

    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback

    def set_news(self, content: str, source: str = "public"):
        """设置新闻内容和来源"""
        self.news_content = content
        self.news_source = source

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
        """异步执行单步推演"""
        if self.use_llm and self.llm_population is None:
            raise RuntimeError("请先调用 initialize()")
        if not self.use_llm and self.population is None:
            raise RuntimeError("请先调用 initialize()")

        self.step_count += 1

        # 检查是否发布辟谣
        if self.step_count >= self.debunk_delay and not self.debunked:
            self._release_debunking()

        if self.use_llm:
            await self._llm_step_dual()
        else:
            self._math_step()

        # 计算新状态
        self.current_state = self._compute_state()
        self.history.append(self.current_state.to_dict())

        return self.current_state

    async def _llm_step_dual(self):
        """LLM 驱动的双层网络推演步骤"""
        pop = self.llm_population

        async with self.llm_client:
            # 批量异步决策
            await pop.batch_decide_dual(
                self.llm_client,
                news_content=self.news_content,
                news_source=self.news_source,
                debunk_released=self.debunked,
                cocoon_strength=self.cocoon_strength,
                progress_callback=self.progress_callback
            )

        # 随机扰动
        for agent in pop.agents:
            noise = np.random.normal(0, 0.01)
            agent.opinion = np.clip(agent.opinion + noise, -1, 1)

    def _math_step(self):
        """数学模型推演步骤"""
        pop = self.population

        # 社交传播影响
        self._social_influence()

        # 算法茧房效应
        self._algorithmic_cocoon()

        # 随机扰动
        self._random_noise()

    def _social_influence(self):
        """社交网络传播影响"""
        pop = self.population
        new_opinions = pop.opinions.copy()

        for i in range(pop.size):
            neighbors = pop.get_neighbors(i)
            if not neighbors:
                continue

            neighbor_opinions = pop.opinions[neighbors]
            neighbor_influence = pop.influence[neighbors]

            weights = neighbor_influence / neighbor_influence.sum()
            weighted_opinion = np.sum(neighbor_opinions * weights)

            change = (weighted_opinion - pop.opinions[i]) * pop.susceptibility[i]
            change *= (1 - pop.belief_strength[i] * 0.5)

            new_opinions[i] += change

        pop.opinions = np.clip(new_opinions, -1, 1)

    def _algorithmic_cocoon(self):
        """算法茧房效应"""
        pop = self.population

        for i in range(pop.size):
            current_opinion = pop.opinions[i]

            if current_opinion < 0:
                reinforcement = -self.cocoon_strength * 0.05 * (1 + abs(current_opinion))
            else:
                reinforcement = self.cocoon_strength * 0.05 * (1 + abs(current_opinion))

            pop.opinions[i] += reinforcement * pop.belief_strength[i]

        pop.opinions = np.clip(pop.opinions, -1, 1)

    def _release_debunking(self):
        """发布官方辟谣信息"""
        self.debunked = True
        logger.info(f"Step {self.step_count}: 发布辟谣")

        if self.use_llm:
            self.llm_population.apply_debunking()
        else:
            pop = self.population
            for i in range(pop.size):
                if pop.opinions[i] < 0:
                    impact = 0.3 * (1 - pop.belief_strength[i])
                    pop.opinions[i] += impact
                    pop.exposed_to_truth[i] = True
            pop.opinions = np.clip(pop.opinions, -1, 1)

    def _random_noise(self):
        """随机扰动"""
        pop = self.population
        noise = np.random.normal(0, 0.01, pop.size)
        pop.opinions += noise
        pop.opinions = np.clip(pop.opinions, -1, 1)

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
                "silence_rate": 0.0,
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

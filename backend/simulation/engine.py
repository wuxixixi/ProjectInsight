"""
推演引擎核心
支持 LLM 驱动和数学模型两种模式
"""
import numpy as np
from typing import Optional, Dict, List, Callable
from datetime import datetime
from pathlib import Path
import asyncio
import logging

from .agents import AgentPopulation
from .llm_agents import LLMAgentPopulation
from ..models.schemas import SimulationState
from ..llm.client import LLMClient, LLMConfig

logger = logging.getLogger(__name__)


class SimulationEngine:
    """
    信息茧房推演引擎

    支持两种模式:
    1. LLM 模式: Agent 通过大模型决策观点变化
    2. 数学模型模式: 使用数学公式计算观点变化

    核心机制:
    1. 算法茧房效应: 根据用户观点推荐相似内容, 强化既有观点
    2. 社交传播: 个体受邻居影响更新观点
    3. 官方辟谣: 延迟后发布真相, 影响观点
    """

    def __init__(
        self,
        population_size: int = 200,
        cocoon_strength: float = 0.5,
        debunk_delay: int = 10,
        initial_rumor_spread: float = 0.3,
        network_type: str = "small_world",
        use_llm: bool = True,
        llm_config: Optional[LLMConfig] = None
    ):
        self.population_size = population_size
        self.cocoon_strength = cocoon_strength
        self.debunk_delay = debunk_delay
        self.initial_rumor_spread = initial_rumor_spread
        self.network_type = network_type
        self.use_llm = use_llm
        self.llm_config = llm_config or LLMConfig()

        self.step_count = 0
        self.debunked = False
        self.current_state: Optional[SimulationState] = None

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

    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback

    def initialize(self) -> SimulationState:
        """初始化模拟"""
        self.step_count = 0
        self.debunked = False
        self.history = []
        self.start_time = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.use_llm:
            # LLM 模式
            self.llm_population = LLMAgentPopulation(
                size=self.population_size,
                initial_rumor_spread=self.initial_rumor_spread,
                network_type=self.network_type,
                llm_config=self.llm_config
            )
            self.llm_client = LLMClient(self.llm_config)
        else:
            # 数学模型模式
            self.population = AgentPopulation(
                size=self.population_size,
                initial_rumor_spread=self.initial_rumor_spread,
                network_type=self.network_type
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
            await self._llm_step()
        else:
            # 数学模型模式
            self._math_step()

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

        # 检查是否发布辟谣
        if self.step_count >= self.debunk_delay and not self.debunked:
            self._release_debunking()

        # 数学模型模式 - 直接调用同步方法
        self._math_step()

        # 计算新状态
        self.current_state = self._compute_state()
        self.history.append(self.current_state.to_dict())

        return self.current_state

    async def _llm_step(self):
        """LLM 驱动的推演步骤"""
        pop = self.llm_population

        async with self.llm_client:
            # 批量异步决策
            await pop.batch_decide(
                self.llm_client,
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
            edges = pop.get_edges()
        else:
            pop = self.population
            opinion_dist = pop.get_opinion_histogram()
            stats = {
                "rumor_spread_rate": float(np.mean(pop.opinions < -0.2)),
                "truth_acceptance_rate": float(np.mean(pop.opinions > 0.2)),
                "avg_opinion": float(np.mean(pop.opinions)),
                "polarization_index": float(np.std(pop.opinions) * 2)
            }
            agents = pop.to_agent_list()
            edges = pop.get_edges()

        return SimulationState(
            step=self.step_count,
            agents=agents,
            edges=edges,
            opinion_distribution=opinion_dist,
            rumor_spread_rate=stats["rumor_spread_rate"],
            truth_acceptance_rate=stats["truth_acceptance_rate"],
            avg_opinion=stats["avg_opinion"],
            polarization_index=stats["polarization_index"]
        )

    def generate_report(self) -> str:
        """生成模拟报告并保存为MD文件"""
        if not self.history:
            return ""

        final_state = self.history[-1]
        initial_state = self.history[0]

        rumor_trend = [h['rumor_spread_rate'] for h in self.history]
        truth_trend = [h['truth_acceptance_rate'] for h in self.history]
        opinion_trend = [h['avg_opinion'] for h in self.history]
        polarization_trend = [h['polarization_index'] for h in self.history]

        final_result = self._analyze_result(final_state)
        cocoon_effect = self._analyze_cocoon_effect()
        debunk_effect = self._analyze_debunk_effect(rumor_trend, truth_trend)

        mode_str = "LLM 驱动" if self.use_llm else "数学模型"

        report = f"""# 信息茧房推演报告

> 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 推演模式: {mode_str}

## 模拟参数

| 参数 | 值 |
|------|-----|
| 群体规模 | {self.population_size} 人 |
| 算法茧房强度 | {self.cocoon_strength:.2f} |
| 官方辟谣延迟 | {self.debunk_delay} 步 |
| 初始谣言传播率 | {self.initial_rumor_spread:.0%} |
| 社交网络类型 | {self._network_type_name()} |
| 总推演步数 | {len(self.history) - 1} 步 |

## 模拟结果摘要

### 最终状态

| 指标 | 初始值 | 最终值 | 变化 |
|------|--------|--------|------|
| 谣言传播率 | {initial_state['rumor_spread_rate']:.1%} | {final_state['rumor_spread_rate']:.1%} | {self._change_arrow(initial_state['rumor_spread_rate'], final_state['rumor_spread_rate'])} |
| 真相接受率 | {initial_state['truth_acceptance_rate']:.1%} | {final_state['truth_acceptance_rate']:.1%} | {self._change_arrow(initial_state['truth_acceptance_rate'], final_state['truth_acceptance_rate'])} |
| 平均观点 | {initial_state['avg_opinion']:.3f} | {final_state['avg_opinion']:.3f} | {self._change_arrow(initial_state['avg_opinion'], final_state['avg_opinion'], reverse=True)} |
| 极化指数 | {initial_state['polarization_index']:.3f} | {final_state['polarization_index']:.3f} | {self._change_arrow(initial_state['polarization_index'], final_state['polarization_index'], reverse=True)} |

### 结论: {final_result['title']}

{final_result['description']}

---

## 详细分析

### 1. 算法茧房效应分析

{cocoon_effect}

### 2. 辟谣效果分析

{debunk_effect}

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
        rumor_rate = final_state['rumor_spread_rate']
        truth_rate = final_state['truth_acceptance_rate']
        polarization = final_state['polarization_index']

        if rumor_rate > 0.5:
            return {
                'title': '⚠️ 谣言占主导',
                'description': f'最终有{rumor_rate:.0%}的人相信谣言，仅{truth_rate:.0%}接受真相。'
            }
        elif truth_rate > 0.5:
            return {
                'title': '✅ 真相占主导',
                'description': f'最终有{truth_rate:.0%}的人接受真相，仅{rumor_rate:.0%}相信谣言。'
            }
        elif polarization > 0.8:
            return {
                'title': '⚡ 社会严重撕裂',
                'description': f'极化指数达{polarization:.2f}，群体呈现两极分化。'
            }
        else:
            return {
                'title': '⚖️ 群体趋于中立',
                'description': f'多数人持中立态度，谣言率{rumor_rate:.0%}，真相率{truth_rate:.0%}。'
            }

    def _analyze_cocoon_effect(self) -> str:
        """分析茧房效应"""
        if self.cocoon_strength < 0.3:
            return f"茧房强度较低({self.cocoon_strength:.2f})，算法推荐对观点强化作用有限。"
        elif self.cocoon_strength > 0.7:
            return f"茧房强度较高({self.cocoon_strength:.2f})，算法推荐显著强化既有观点。"
        else:
            return f"茧房强度中等({self.cocoon_strength:.2f})，存在一定程度的茧房效应。"

    def _analyze_debunk_effect(self, rumor_trend: List, truth_trend: List) -> str:
        """分析辟谣效果"""
        if self.debunk_delay >= len(self.history):
            return "本次模拟未触发辟谣机制。"

        debunk_step = self.debunk_delay
        if debunk_step < len(rumor_trend):
            before_rumor = rumor_trend[max(0, debunk_step-2)]
            after_rumor = rumor_trend[min(debunk_step+3, len(rumor_trend)-1)]
            effect = before_rumor - after_rumor

            if effect > 0.1:
                return f"辟谣在第{self.debunk_delay}步发布后，谣言传播率从{before_rumor:.1%}下降至{after_rumor:.1%}，**效果显著**。"
            elif effect > 0:
                return f"辟谣在第{self.debunk_delay}步发布后，谣言传播率小幅下降{effect:.1%}。"
            else:
                return "辟谣后谣言传播率未明显下降，可能辟谣时机过晚。"

        return "辟谣效果数据不足。"

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

        if final_state['rumor_spread_rate'] > 0.4:
            recommendations.append("- 建议提前辟谣时间，减少谣言发酵期")

        if final_state['polarization_index'] > 0.7:
            recommendations.append("- 高极化风险，建议降低算法茧房强度")

        if self.cocoon_strength > 0.6 and final_state['rumor_spread_rate'] > 0.3:
            recommendations.append("- 茧房效应过强阻碍真相传播，建议优化推荐算法")

        if not recommendations:
            recommendations.append("- 当前参数配置下舆论状况良好")

        return "\n".join(recommendations)

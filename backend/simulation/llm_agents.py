"""
LLM 驱动的智能体
每个 Agent 通过 LLM 决策观点变化
"""
import asyncio
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
import networkx as nx
import logging
import json
import copy

from ..llm.client import LLMClient, LLMConfig

logger = logging.getLogger(__name__)

# 全局决策快照存储 (agent_id -> 上下文快照)
AGENT_DECISION_SNAPSHOTS: Dict[int, Dict[str, Any]] = {}


# 人设模板
PERSONA_TEMPLATES = [
    {"type": "低媒介素养", "desc": "对网络信息缺乏辨别能力，容易被情绪化内容影响"},
    {"type": "理性分析型", "desc": "习惯多方求证，对信息持审慎态度"},
    {"type": "易恐慌型", "desc": "对负面信息敏感，容易产生焦虑情绪"},
    {"type": "从众型", "desc": "容易受周围人影响，倾向于跟随主流观点"},
    {"type": "怀疑论者", "desc": "对官方信息持怀疑态度，不容易被说服"},
    {"type": "意见领袖", "desc": "有较强影响力，观点容易影响他人"},
    {"type": "信息茧房受害者", "desc": "长期接触单一观点信息，固守既有立场"},
]


def get_persona(agent_id: int, opinion: float, susceptibility: float) -> Dict:
    """根据属性生成人设"""
    np.random.seed(agent_id)  # 确保同一agent每次生成相同人设
    if susceptibility > 0.5:
        pool = [PERSONA_TEMPLATES[0], PERSONA_TEMPLATES[2], PERSONA_TEMPLATES[3]]
    elif opinion < -0.3:
        pool = [PERSONA_TEMPLATES[4], PERSONA_TEMPLATES[6]]
    else:
        pool = PERSONA_TEMPLATES
    return np.random.choice(pool)


# Agent 决策 Prompt 模板 (含沉默的螺旋和观点变化限制说明)
AGENT_PROMPT_TEMPLATE = """你是一个社交媒体用户，正在关注一个热点事件的讨论。
观点范围: -1(完全相信谣言) 到 1(完全相信真相)，0 表示中立。

## 你的个人特征
- 当前观点: {opinion:.2f}
- 信念强度: {belief_strength:.2f} (越强越难改变观点)
- 易感性: {susceptibility:.2f} (越强越容易受他人影响)
- 孤立恐惧感: {fear_of_isolation:.2f} (越高越害怕被社交孤立)
- 初始信念强度: {conviction:.2f} (形成观点时的坚定程度)

## 观点变化限制规则（重要）
- 你的信念强度为 {belief_strength:.2f}，因此你本轮观点最大变化幅度为 {max_change:.2f}
- 如果你选择沉默(is_silent=true)，观点变化幅度会进一步降低到 {max_change_silent:.2f}
- 请在限制范围内选择合理的新观点值

## 沉默的螺旋机制说明
- 如果你的观点与周围大多数人相反，且你的孤立恐惧感较高，你可能会选择沉默
- 沉默意味着你保持原有观点，但不在公开场合表达
- 选择沉默的代价：观点变化幅度受限，但可以避免社交冲突

## 你收到的信息
{info_section}

## 社交压力感知
{social_pressure_section}

## 任务
基于你的特征、收到的信息和社交压力，决定你的行为和观点变化。

请直接返回 JSON 格式（不要其他文字）:
{{"new_opinion": 数值在-1到1之间(注意变化幅度限制), "reasoning": "简短理由(20字内)", "emotion": "情绪状态(冷静/愤怒/焦虑/怀疑/释然)", "action": "行动选择(转发/评论/观望/辟谣/沉默)", "is_silent": boolean(是否选择沉默), "generated_comment": "如果选择评论，生成的评论内容(30字内)"}}
"""


class LLMAgent:
    """
    LLM 驱动的单个智能体

    属性:
    - opinion: 观点值 [-1, 1]
    - belief_strength: 信念强度
    - influence: 影响力
    - susceptibility: 易感性
    - persona: 人设背景
    - fear_of_isolation: 孤立恐惧感 [0, 1] (沉默的螺旋)
    - conviction: 初始信念强度 [0, 1] (沉默的螺旋)
    - is_silent: 是否选择沉默
    - perceived_climate: 感知到的舆论气候
    """

    def __init__(
        self,
        agent_id: int,
        opinion: float,
        belief_strength: float,
        influence: float,
        susceptibility: float
    ):
        self.id = agent_id
        self.opinion = opinion
        self.belief_strength = belief_strength
        self.influence = influence
        self.susceptibility = susceptibility
        self.exposed_to_rumor = opinion < -0.2
        self.exposed_to_truth = False

        # 人设背景
        self.persona = get_persona(agent_id, opinion, susceptibility)

        # 决策历史
        self.decision_history: List[Dict] = []

        # 最新决策上下文快照
        self.last_decision_snapshot: Optional[Dict] = None

        # === 沉默的螺旋：新增属性 ===
        np.random.seed(agent_id + 1000)  # 使用不同种子确保独立性
        self.fear_of_isolation = float(np.random.beta(2, 2))  # 孤立恐惧感 [0, 1]
        self.conviction = float(np.random.beta(2, 2))  # 初始信念强度 [0, 1]
        self.is_silent = False  # 是否选择沉默
        self.perceived_climate: Optional[Dict] = None  # 感知到的舆论气候

    def scan_neighbor_climate(
        self,
        neighbors: List['LLMAgent'],
        opinion_snapshot: Optional[Dict[int, float]] = None
    ) -> Dict:
        """
        扫描邻居状态，计算感知到的舆论气候
        
        Args:
            neighbors: 邻居 Agent 列表
            opinion_snapshot: 观点快照 {agent_id: opinion}，用于并发一致性
            
        Returns:
            包含邻居统计信息的字典
        """
        if not neighbors:
            return {
                "total": 0,
                "pro_rumor_ratio": 0.0,
                "pro_truth_ratio": 0.0,
                "neutral_ratio": 1.0,
                "silent_ratio": 0.0,
                "avg_opinion": 0.0
            }

        total = len(neighbors)
        
        # 使用快照中的观点（如果提供），否则使用实时观点
        if opinion_snapshot:
            opinions = [opinion_snapshot.get(n.id, n.opinion) for n in neighbors]
            silent_count = sum(
                1 for n in neighbors 
                if opinion_snapshot.get(f"{n.id}_is_silent", n.is_silent)
            )
        else:
            opinions = [n.opinion for n in neighbors]
            silent_count = sum(1 for n in neighbors if n.is_silent)
        
        pro_rumor = sum(1 for o in opinions if o < -0.2)
        pro_truth = sum(1 for o in opinions if o > 0.2)
        neutral = total - pro_rumor - pro_truth
        avg_opinion = sum(opinions) / total

        climate = {
            "total": total,
            "pro_rumor_ratio": pro_rumor / total,
            "pro_truth_ratio": pro_truth / total,
            "neutral_ratio": neutral / total,
            "silent_ratio": silent_count / total,
            "avg_opinion": avg_opinion
        }

        self.perceived_climate = climate
        return climate

    def build_prompt(
        self,
        neighbor_agents: List['LLMAgent'],
        debunk_released: bool,
        cocoon_strength: float,
        opinion_snapshot: Optional[Dict[int, float]] = None
    ) -> Tuple[str, List[str]]:
        """
        构建决策 Prompt

        Args:
            neighbor_agents: 邻居 Agent 列表 (用于扫描舆论气候)
            debunk_released: 是否已发布辟谣
            cocoon_strength: 茧房强度
            opinion_snapshot: 观点快照，用于并发一致性

        Returns:
            (prompt, info_lines) - Prompt文本和信息行列表
        """
        # 扫描邻居舆论气候（使用快照）
        climate = self.scan_neighbor_climate(neighbor_agents, opinion_snapshot)
        
        # 计算观点变化限制
        max_change = 0.3 * (1 - self.belief_strength * 0.5)
        max_change_silent = 0.1 * (1 - self.belief_strength * 0.5)

        # 构建信息部分
        info_lines = []

        # 邻居观点统计
        if climate["total"] > 0:
            info_lines.append(f"- 邻居数量: {climate['total']}")
            info_lines.append(f"- 邻居平均观点: {climate['avg_opinion']:.2f}")
            info_lines.append(f"- 邻居分布: {climate['pro_rumor_ratio']*100:.0f}%信谣言, {climate['neutral_ratio']*100:.0f}%中立, {climate['pro_truth_ratio']*100:.0f}%信真相")
            if climate['silent_ratio'] > 0:
                info_lines.append(f"- 沉默的邻居: {climate['silent_ratio']*100:.0f}%")

        # 辟谣状态
        if debunk_released:
            info_lines.append("- **官方已发布辟谣信息**: 指出谣言不实")

        # 算法推荐模拟 (茧房效应)
        if cocoon_strength > 0.3:
            if self.opinion < 0:
                info_lines.append("- 算法推荐: 更多支持谣言的内容")
            else:
                info_lines.append("- 算法推荐: 更多支持真相的内容")

        info_section = "\n".join(info_lines) if info_lines else "- 暂无新信息"

        # 构建社交压力部分
        social_pressure_lines = []

        if climate["total"] > 0:
            # 判断自己的观点是否与主流相反
            my_stance = "信谣言" if self.opinion < -0.2 else ("信真相" if self.opinion > 0.2 else "中立")
            majority_stance = "信谣言" if climate['pro_rumor_ratio'] > climate['pro_truth_ratio'] else "信真相" if climate['pro_truth_ratio'] > climate['pro_rumor_ratio'] else "中立"

            # 计算主流观点比例
            majority_ratio = max(climate['pro_rumor_ratio'], climate['pro_truth_ratio'])

            social_pressure_lines.append(f"- 你的观点: {my_stance} ({self.opinion:.2f})")
            social_pressure_lines.append(f"- 周围主流观点: {majority_stance} (占比{majority_ratio*100:.0f}%)")

            # 判断是否处于少数派
            is_minority = False
            if self.opinion < -0.2 and climate['pro_truth_ratio'] > climate['pro_rumor_ratio']:
                is_minority = True
            elif self.opinion > 0.2 and climate['pro_rumor_ratio'] > climate['pro_truth_ratio']:
                is_minority = True

            if is_minority:
                social_pressure_lines.append(f"- ⚠️ 你是少数派！周围{majority_ratio*100:.0f}%的人持有相反观点")
                if self.fear_of_isolation > 0.6:
                    social_pressure_lines.append(f"- 你的孤立恐惧感较高({self.fear_of_isolation:.2f})，可能会感到社交压力")
                    social_pressure_lines.append(f"- 建议：考虑是否应该公开表达你的观点，还是选择沉默以避免冲突")
            else:
                social_pressure_lines.append(f"- 你与周围大多数人观点一致，社交压力较小")
        else:
            social_pressure_lines.append("- 暂无邻居信息，无法判断社交压力")

        social_pressure_section = "\n".join(social_pressure_lines)

        prompt = AGENT_PROMPT_TEMPLATE.format(
            opinion=self.opinion,
            belief_strength=self.belief_strength,
            susceptibility=self.susceptibility,
            fear_of_isolation=self.fear_of_isolation,
            conviction=self.conviction,
            max_change=max_change,
            max_change_silent=max_change_silent,
            info_section=info_section,
            social_pressure_section=social_pressure_section
        )

        return prompt, info_lines

    async def decide_opinion(
        self,
        llm_client: LLMClient,
        neighbor_agents: List['LLMAgent'],
        debunk_released: bool,
        cocoon_strength: float,
        opinion_snapshot: Optional[Dict[int, float]] = None
    ) -> Dict:
        """
        通过 LLM 决定新观点

        Args:
            llm_client: LLM 客户端
            neighbor_agents: 邻居 Agent 列表 (用于扫描舆论气候)
            debunk_released: 是否已发布辟谣
            cocoon_strength: 茧房强度
            opinion_snapshot: 观点快照，用于并发一致性

        Returns:
            {"new_opinion": float, "reasoning": str, "is_silent": bool}
        """
        prompt, received_news = self.build_prompt(
            neighbor_agents, debunk_released, cocoon_strength, opinion_snapshot
        )

        messages = [{"role": "user", "content": prompt}]

        try:
            result = await llm_client.chat_json(
                messages,
                temperature=0.7,
                max_tokens=150
            )

            new_opinion = result.get("new_opinion", self.opinion)
            reasoning = result.get("reasoning", "")
            emotion = result.get("emotion", "冷静")
            action = result.get("action", "观望")
            generated_comment = result.get("generated_comment", "")
            is_silent = result.get("is_silent", False)

            # 确保在有效范围内
            new_opinion = np.clip(new_opinion, -1, 1)

            # 如果选择沉默，观点变化应该更小（保持原有观点）
            if is_silent:
                # 沉默时观点变化幅度降低到原来的30%
                max_change = 0.1 * (1 - self.belief_strength * 0.5)
                change = new_opinion - self.opinion
                if abs(change) > max_change:
                    new_opinion = self.opinion + np.sign(change) * max_change
                    new_opinion = np.clip(new_opinion, -1, 1)
            else:
                # 信念强度约束：观点变化幅度受信念强度限制
                max_change = 0.3 * (1 - self.belief_strength * 0.5)
                change = new_opinion - self.opinion
                if abs(change) > max_change:
                    new_opinion = self.opinion + np.sign(change) * max_change
                    new_opinion = np.clip(new_opinion, -1, 1)

            # 更新沉默状态
            self.is_silent = bool(is_silent)

            decision = {
                "old_opinion": self.opinion,
                "new_opinion": float(new_opinion),
                "reasoning": reasoning,
                "is_silent": bool(is_silent)
            }

            # === 保存决策上下文快照 ===
            snapshot = {
                "agent_id": self.id,
                "persona": self.persona,
                "persona_str": f"{self.persona['type']} - {self.persona['desc']}",
                "belief_strength": float(self.belief_strength),
                "susceptibility": float(self.susceptibility),
                "influence": float(self.influence),
                "old_opinion": float(self.opinion),
                "new_opinion": float(new_opinion),
                "received_news": received_news,
                "llm_raw_response": result,
                "emotion": emotion,
                "action": action,
                "generated_comment": generated_comment,
                "reasoning": reasoning,
                "has_decided": True,
                # 沉默的螺旋相关
                "fear_of_isolation": float(self.fear_of_isolation),
                "conviction": float(self.conviction),
                "is_silent": bool(is_silent),
                "perceived_climate": self.perceived_climate
            }

            # 保存到Agent实例
            self.last_decision_snapshot = snapshot

            # 保存到全局存储
            AGENT_DECISION_SNAPSHOTS[self.id] = snapshot

            self.decision_history.append(decision)
            self.opinion = float(new_opinion)

            return decision

        except Exception as e:
            logger.warning(f"Agent {self.id} LLM 决策失败: {e}，保持原观点")

            # 保存失败快照
            snapshot = {
                "agent_id": self.id,
                "persona": self.persona,
                "persona_str": f"{self.persona['type']} - {self.persona['desc']}",
                "belief_strength": float(self.belief_strength),
                "susceptibility": float(self.susceptibility),
                "influence": float(self.influence),
                "old_opinion": float(self.opinion),
                "new_opinion": float(self.opinion),
                "received_news": [],
                "llm_raw_response": {"error": str(e)},
                "emotion": "未知",
                "action": "观望",
                "generated_comment": "",
                "reasoning": "决策失败，保持原观点",
                "has_decided": False,
                "error": str(e),
                # 沉默的螺旋相关
                "fear_of_isolation": float(self.fear_of_isolation),
                "conviction": float(self.conviction),
                "is_silent": False,
                "perceived_climate": self.perceived_climate
            }
            self.last_decision_snapshot = snapshot
            AGENT_DECISION_SNAPSHOTS[self.id] = snapshot

            return {
                "old_opinion": self.opinion,
                "new_opinion": self.opinion,
                "reasoning": "决策失败，保持原观点",
                "is_silent": False
            }

    def to_dict(self) -> Dict:
        """转换为可序列化字典"""
        return {
            "id": self.id,
            "opinion": float(self.opinion),
            "belief_strength": float(self.belief_strength),
            "influence": float(self.influence),
            "susceptibility": float(self.susceptibility),
            "exposed_to_rumor": bool(self.exposed_to_rumor),
            "exposed_to_truth": bool(self.exposed_to_truth),
            "persona": self.persona,
            # 沉默的螺旋相关
            "fear_of_isolation": float(self.fear_of_isolation),
            "conviction": float(self.conviction),
            "is_silent": bool(self.is_silent),
            "opacity": 0.3 if self.is_silent else 1.0  # 前端透明度标记
        }


class LLMAgentPopulation:
    """
    LLM 驱动的智能体群体

    管理 Agent 群体，处理并发决策
    """

    def __init__(
        self,
        size: int = 200,
        initial_rumor_spread: float = 0.3,
        network_type: str = "small_world",
        llm_config: Optional[LLMConfig] = None
    ):
        self.size = size
        self.network_type = network_type
        self.llm_config = llm_config or LLMConfig()

        # 初始化观点分布
        opinions = np.zeros(size)
        rumor_believers = int(size * initial_rumor_spread)
        opinions[:rumor_believers] = np.random.uniform(-0.8, -0.3, rumor_believers)
        opinions[rumor_believers:] = np.random.uniform(-0.2, 0.3, size - rumor_believers)

        # 初始化属性
        belief_strengths = np.random.beta(2, 2, size)
        influences = np.clip(np.random.exponential(0.5, size), 0.1, 1.0)
        susceptibilities = np.random.beta(2, 5, size)

        # 创建 Agent 实例
        self.agents: List[LLMAgent] = [
            LLMAgent(
                agent_id=i,
                opinion=opinions[i],
                belief_strength=belief_strengths[i],
                influence=influences[i],
                susceptibility=susceptibilities[i]
            )
            for i in range(size)
        ]

        # 构建社交网络
        self.network = self._build_network(network_type)

        # 暴露状态
        self.exposed_to_truth = np.zeros(size, dtype=bool)

    def _build_network(self, network_type: str) -> nx.Graph:
        """构建社交网络"""
        if network_type == "small_world":
            G = nx.watts_strogatz_graph(self.size, k=6, p=0.3, seed=42)
        elif network_type == "scale_free":
            G = nx.barabasi_albert_graph(self.size, m=3, seed=42)
        else:
            G = nx.watts_strogatz_graph(self.size, k=6, p=0.3, seed=42)
        return G

    def get_neighbors(self, agent_id: int) -> List[int]:
        """获取邻居ID列表"""
        return list(self.network.neighbors(agent_id))

    def get_neighbor_opinions(self, agent_id: int) -> List[float]:
        """获取邻居观点列表"""
        neighbor_ids = self.get_neighbors(agent_id)
        return [self.agents[nid].opinion for nid in neighbor_ids]

    def get_neighbor_agents(self, agent_id: int) -> List[LLMAgent]:
        """获取邻居 Agent 对象列表"""
        neighbor_ids = self.get_neighbors(agent_id)
        return [self.agents[nid] for nid in neighbor_ids]

    def get_edges(self) -> List[Tuple[int, int]]:
        """获取所有边"""
        return list(self.network.edges())

    async def batch_decide(
        self,
        llm_client: LLMClient,
        debunk_released: bool,
        cocoon_strength: float,
        progress_callback=None
    ) -> List[Dict]:
        """
        批量异步决策（使用观点快照保证并发一致性）

        使用 asyncio.gather 并行调用 LLM，
        但受 LLMClient 内部的 Semaphore 限制并发数

        Args:
            llm_client: LLM 客户端
            debunk_released: 是否已辟谣
            cocoon_strength: 茧房强度
            progress_callback: 进度回调函数

        Returns:
            所有 Agent 的决策结果
        """
        # === 关键修复：在决策前保存所有 Agent 的观点快照 ===
        # 这确保所有 Agent 感知到的是同一时刻的邻居状态
        opinion_snapshot = {}
        for agent in self.agents:
            opinion_snapshot[agent.id] = float(agent.opinion)
            opinion_snapshot[f"{agent.id}_is_silent"] = agent.is_silent

        async def decide_one(agent: LLMAgent, index: int):
            neighbor_agents = self.get_neighbor_agents(agent.id)
            result = await agent.decide_opinion(
                llm_client,
                neighbor_agents,
                debunk_released,
                cocoon_strength,
                opinion_snapshot  # 传入快照
            )
            if progress_callback:
                await progress_callback(index, self.size)
            return result

        tasks = [
            decide_one(agent, i)
            for i, agent in enumerate(self.agents)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Agent {i} 决策异常: {result}")
                processed.append({
                    "old_opinion": self.agents[i].opinion,
                    "new_opinion": self.agents[i].opinion,
                    "reasoning": "决策异常",
                    "is_silent": False
                })
            else:
                processed.append(result)

        return processed

    def apply_debunking(self, effectiveness: float = 0.2):
        """
        应用辟谣效果（动态版本）
        
        Args:
            effectiveness: 基础辟谣效果系数（由引擎根据延迟和茧房强度计算）
        """
        self.exposed_to_truth[:] = True
        for agent in self.agents:
            agent.exposed_to_truth = True
            # 辟谣对相信谣言的人有一定影响
            if agent.opinion < 0:
                # 动态计算：考虑信念强度和易感性
                impact = effectiveness * (1 - agent.belief_strength * 0.5) * (0.5 + agent.susceptibility * 0.5)
                agent.opinion = min(agent.opinion + impact, 1.0)

    def get_opinion_histogram(self, bins: int = 20) -> Dict[str, List]:
        """计算观点分布直方图"""
        opinions = [a.opinion for a in self.agents]
        hist, edges = np.histogram(opinions, bins=bins, range=(-1, 1))
        centers = [(edges[i] + edges[i+1]) / 2 for i in range(len(edges)-1)]
        return {
            "counts": hist.tolist(),
            "centers": centers
        }

    def to_agent_list(self) -> List[Dict]:
        """转换为可序列化的 Agent 列表"""
        return [agent.to_dict() for agent in self.agents]

    def get_statistics(self) -> Dict:
        """计算群体统计"""
        opinions = [a.opinion for a in self.agents]

        return {
            "rumor_spread_rate": np.mean([o < -0.2 for o in opinions]),
            "truth_acceptance_rate": np.mean([o > 0.2 for o in opinions]),
            "avg_opinion": float(np.mean(opinions)),
            "polarization_index": float(np.std(opinions) * 2),
            "silence_rate": np.mean([a.is_silent for a in self.agents])  # 沉默率
        }

    def get_agent_snapshot(self, agent_id: int) -> Optional[Dict]:
        """获取指定Agent的决策快照"""
        if 0 <= agent_id < len(self.agents):
            agent = self.agents[agent_id]
            # 优先返回快照，否则返回基础信息
            if agent.last_decision_snapshot:
                return agent.last_decision_snapshot
            else:
                # 未参与决策的Agent，返回基础信息
                return {
                    "agent_id": agent_id,
                    "persona": agent.persona,
                    "persona_str": f"{agent.persona['type']} - {agent.persona['desc']}",
                    "belief_strength": float(agent.belief_strength),
                    "susceptibility": float(agent.susceptibility),
                    "influence": float(agent.influence),
                    "old_opinion": float(agent.opinion),
                    "new_opinion": float(agent.opinion),
                    "received_news": [],
                    "llm_raw_response": None,
                    "emotion": "未激活",
                    "action": "未参与",
                    "generated_comment": "",
                    "reasoning": "该Agent尚未参与本轮推演",
                    "has_decided": False,
                    # 沉默的螺旋相关
                    "fear_of_isolation": float(agent.fear_of_isolation),
                    "conviction": float(agent.conviction),
                    "is_silent": bool(agent.is_silent),
                    "perceived_climate": agent.perceived_climate
                }
        return None


def get_agent_snapshot_global(agent_id: int) -> Optional[Dict]:
    """从全局存储获取Agent决策快照"""
    return AGENT_DECISION_SNAPSHOTS.get(agent_id)

"""
LLM 驱动的智能体 - 双层模态信息场版本
每个 Agent 通过 LLM 决策观点变化，支持公域/私域双模态信息传播
"""
import asyncio
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
import logging
import json

from ..llm.client import LLMClient, LLMConfig
from .dual_network import DualLayerNetwork, MessageRouter

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
    np.random.seed(agent_id)
    if susceptibility > 0.5:
        pool = [PERSONA_TEMPLATES[0], PERSONA_TEMPLATES[2], PERSONA_TEMPLATES[3]]
    elif opinion < -0.3:
        pool = [PERSONA_TEMPLATES[4], PERSONA_TEMPLATES[6]]
    else:
        pool = PERSONA_TEMPLATES
    return np.random.choice(pool)


# ==================== 双模态 Prompt 模板 ====================

# 公域信息情境
PUBLIC_CONTEXT_TEMPLATE = """你在微博公共时间线上看到一个{sender_type}发布了以下消息：
「{news_content}」
下方评论区有很多陌生人情绪激动，观点两极分化。
"""

# 私域信息情境
PRIVATE_CONTEXT_TEMPLATE = """你最信任的亲友在家族微信群里专门@你，并转发了以下消息：
「{news_content}」
TA说这事关你们的切身利益，让你务必注意。
"""


# Agent 决策 Prompt 模板 (双层模态版本)
AGENT_PROMPT_TEMPLATE_DUAL = """你是一个社交媒体用户，正在关注一个热点事件的讨论。
观点范围: -1(完全相信谣言) 到 1(完全相信真相)，0 表示中立。

## 你的个人特征
- 当前观点: {opinion:.2f}
- 信念强度: {belief_strength:.2f} (越强越难改变观点)
- 易感性: {susceptibility:.2f} (越强越容易受他人影响)
- 孤立恐惧感: {fear_of_isolation:.2f} (越高越害怕被社交孤立)
- 是否为大V: {is_influencer}

## 你收到的信息
{info_section}

## 信息来源分析
{source_section}

## 公域舆论环境
{public_climate_section}

## 私域朋友圈环境
{private_climate_section}

## 任务
基于你的特征、收到的信息和不同渠道的信任度，决定你的行为和观点变化。

**信息渠道说明**:
- 公域信息(微博/抖音): 来自陌生人，可信度一般，但传播范围广
- 私域信息(微信群/朋友圈): 来自亲友，可信度高，但只在圈内传播

**发布渠道选项**:
- public: 只发布到公域（如发微博）
- private: 只转发给私域好友（如转发到微信群）
- both: 双发（同时发布到公域和私域）
- none: 不转发，保持沉默

请直接返回 JSON 格式（不要其他文字）:
{{"new_opinion": 数值在-1到1之间, "reasoning": "简短理由(20字内)", "emotion": "情绪状态(冷静/愤怒/焦虑/怀疑/释然)", "action": "行动选择(转发/评论/观望/辟谣/沉默)", "is_silent": boolean, "publish_channel": "public/private/both/none", "generated_comment": "评论内容(30字内)"}}
"""


class LLMAgent:
    """
    LLM 驱动的单个智能体 - 双层模态版本

    属性:
    - opinion: 观点值 [-1, 1]
    - belief_strength: 信念强度
    - influence: 影响力
    - susceptibility: 易感性
    - persona: 人设背景
    - fear_of_isolation: 孤立恐惧感 [0, 1]
    - conviction: 初始信念强度 [0, 1]
    - is_silent: 是否选择沉默
    - is_influencer: 是否为大V（公域超级节点）
    - community_id: 所属私域社群ID
    - publish_channel: 发布渠道选择
    """

    def __init__(
        self,
        agent_id: int,
        opinion: float,
        belief_strength: float,
        influence: float,
        susceptibility: float,
        is_influencer: bool = False,
        community_id: int = 0
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
        self.last_decision_snapshot: Optional[Dict] = None

        # === 沉默的螺旋属性 ===
        np.random.seed(agent_id + 1000)
        self.fear_of_isolation = float(np.random.beta(2, 2))
        self.conviction = float(np.random.beta(2, 2))
        self.is_silent = False
        self.perceived_climate: Optional[Dict] = None

        # === 双层网络属性 ===
        self.is_influencer = is_influencer
        self.community_id = community_id
        self.publish_channel = "none"  # 默认不发布

        # 信息接收记录
        self.received_public_info: List[Dict] = []
        self.received_private_info: List[Dict] = []

    def scan_public_climate(self, public_neighbors: List['LLMAgent']) -> Dict:
        """扫描公域舆论气候"""
        if not public_neighbors:
            return {"total": 0, "pro_rumor_ratio": 0.0, "pro_truth_ratio": 0.0, "avg_opinion": 0.0}

        total = len(public_neighbors)
        pro_rumor = sum(1 for n in public_neighbors if n.opinion < -0.2)
        pro_truth = sum(1 for n in public_neighbors if n.opinion > 0.2)
        avg_opinion = sum(n.opinion for n in public_neighbors) / total

        return {
            "total": total,
            "pro_rumor_ratio": pro_rumor / total,
            "pro_truth_ratio": pro_truth / total,
            "avg_opinion": avg_opinion
        }

    def scan_private_climate(self, private_neighbors: List['LLMAgent']) -> Dict:
        """扫描私域舆论气候"""
        if not private_neighbors:
            return {"total": 0, "pro_rumor_ratio": 0.0, "pro_truth_ratio": 0.0, "avg_opinion": 0.0}

        total = len(private_neighbors)
        pro_rumor = sum(1 for n in private_neighbors if n.opinion < -0.2)
        pro_truth = sum(1 for n in private_neighbors if n.opinion > 0.2)
        avg_opinion = sum(n.opinion for n in private_neighbors) / total

        return {
            "total": total,
            "pro_rumor_ratio": pro_rumor / total,
            "pro_truth_ratio": pro_truth / total,
            "avg_opinion": avg_opinion
        }

    def build_prompt_dual(
        self,
        public_neighbors: List['LLMAgent'],
        private_neighbors: List['LLMAgent'],
        news_content: str,
        news_source: str,
        debunk_released: bool,
        cocoon_strength: float
    ) -> Tuple[str, List[str]]:
        """
        构建双模态决策 Prompt
        """
        info_lines = []

        # 构建信息来源情境
        if news_source == "public":
            sender_type = "大V" if self.is_influencer else "博主"
            source_section = PUBLIC_CONTEXT_TEMPLATE.format(
                sender_type=sender_type,
                news_content=news_content
            )
            info_lines.append(f"[公域信息] 来源: 微博公共时间线")
        else:
            source_section = PRIVATE_CONTEXT_TEMPLATE.format(
                news_content=news_content
            )
            info_lines.append(f"[私域信息] 来源: 微信群好友")

        # 信息内容
        info_lines.append(f"内容: {news_content}")

        # 辟谣状态
        if debunk_released:
            info_lines.append("【官方辟谣】已发布，指出谣言不实")

        # 算法茧房效应
        if cocoon_strength > 0.3:
            if self.opinion < 0:
                info_lines.append("算法推荐: 更多支持谣言的内容")
            else:
                info_lines.append("算法推荐: 更多支持真相的内容")

        info_section = "\n".join(f"- {line}" for line in info_lines)

        # 公域舆论环境
        public_climate = self.scan_public_climate(public_neighbors)
        if public_climate["total"] > 0:
            public_climate_section = f"""- 公域粉丝数: {public_climate['total']}
- 公域平均观点: {public_climate['avg_opinion']:.2f}
- 公域谣言率: {public_climate['pro_rumor_ratio']*100:.0f}%
- 公域真相率: {public_climate['pro_truth_ratio']*100:.0f}%"""
        else:
            public_climate_section = "- 暂无公域粉丝"

        # 私域舆论环境
        private_climate = self.scan_private_climate(private_neighbors)
        if private_climate["total"] > 0:
            private_climate_section = f"""- 私域好友数: {private_climate['total']}
- 私域平均观点: {private_climate['avg_opinion']:.2f}
- 私域谣言率: {private_climate['pro_rumor_ratio']*100:.0f}%
- 私域真相率: {private_climate['pro_truth_ratio']*100:.0f}%"""
        else:
            private_climate_section = "- 暂无私域好友"

        # 保存气候数据
        self.perceived_climate = {
            "public": public_climate,
            "private": private_climate
        }

        prompt = AGENT_PROMPT_TEMPLATE_DUAL.format(
            opinion=self.opinion,
            belief_strength=self.belief_strength,
            susceptibility=self.susceptibility,
            fear_of_isolation=self.fear_of_isolation,
            conviction=self.conviction,
            is_influencer="是（大V）" if self.is_influencer else "否",
            info_section=info_section,
            source_section=source_section,
            public_climate_section=public_climate_section,
            private_climate_section=private_climate_section
        )

        return prompt, info_lines

    async def decide_opinion_dual(
        self,
        llm_client: LLMClient,
        public_neighbors: List['LLMAgent'],
        private_neighbors: List['LLMAgent'],
        news_content: str,
        news_source: str,
        debunk_released: bool,
        cocoon_strength: float
    ) -> Dict:
        """双模态决策"""
        prompt, received_news = self.build_prompt_dual(
            public_neighbors, private_neighbors, news_content, news_source,
            debunk_released, cocoon_strength
        )

        messages = [{"role": "user", "content": prompt}]

        try:
            result = await llm_client.chat_json(
                messages,
                temperature=0.7,
                max_tokens=200
            )

            new_opinion = result.get("new_opinion", self.opinion)
            reasoning = result.get("reasoning", "")
            emotion = result.get("emotion", "冷静")
            action = result.get("action", "观望")
            generated_comment = result.get("generated_comment", "")
            is_silent = result.get("is_silent", False)
            publish_channel = result.get("publish_channel", "none")

            # 确保在有效范围内
            new_opinion = np.clip(new_opinion, -1, 1)

            # 观点变化约束
            max_change = 0.1 if is_silent else 0.3 * (1 - self.belief_strength * 0.5)
            change = new_opinion - self.opinion
            if abs(change) > max_change:
                new_opinion = self.opinion + np.sign(change) * max_change
                new_opinion = np.clip(new_opinion, -1, 1)

            # 更新状态
            self.is_silent = bool(is_silent)
            self.publish_channel = publish_channel

            decision = {
                "old_opinion": self.opinion,
                "new_opinion": float(new_opinion),
                "reasoning": reasoning,
                "is_silent": bool(is_silent),
                "publish_channel": publish_channel
            }

            # 保存快照
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
                "fear_of_isolation": float(self.fear_of_isolation),
                "conviction": float(self.conviction),
                "is_silent": bool(is_silent),
                "perceived_climate": self.perceived_climate,
                "is_influencer": self.is_influencer,
                "community_id": self.community_id,
                "publish_channel": publish_channel
            }

            self.last_decision_snapshot = snapshot
            AGENT_DECISION_SNAPSHOTS[self.id] = snapshot
            self.decision_history.append(decision)
            self.opinion = float(new_opinion)

            return decision

        except Exception as e:
            logger.warning(f"Agent {self.id} LLM 决策失败: {e}")
            return {
                "old_opinion": self.opinion,
                "new_opinion": self.opinion,
                "reasoning": "决策失败",
                "is_silent": False,
                "publish_channel": "none"
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
            "fear_of_isolation": float(self.fear_of_isolation),
            "conviction": float(self.conviction),
            "is_silent": bool(self.is_silent),
            "opacity": 0.3 if self.is_silent else 1.0,
            # 双层网络属性
            "is_influencer": self.is_influencer,
            "community_id": self.community_id,
            "publish_channel": self.publish_channel
        }


class LLMAgentPopulationDual:
    """
    双层网络智能体群体
    """

    def __init__(
        self,
        size: int = 200,
        initial_rumor_spread: float = 0.3,
        llm_config: Optional[LLMConfig] = None,
        # 双层网络参数
        num_communities: int = 8,
        public_m: int = 3,
        intra_community_prob: float = 0.3,
        inter_community_prob: float = 0.01
    ):
        self.size = size
        self.llm_config = llm_config or LLMConfig()

        # 构建双层网络
        self.dual_network = DualLayerNetwork(
            size=size,
            public_m=public_m,
            num_communities=num_communities,
            intra_community_prob=intra_community_prob,
            inter_community_prob=inter_community_prob
        )

        # 消息路由器
        self.message_router = MessageRouter(self.dual_network)

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
        self.agents: List[LLMAgent] = []
        for i in range(size):
            agent = LLMAgent(
                agent_id=i,
                opinion=opinions[i],
                belief_strength=belief_strengths[i],
                influence=influences[i],
                susceptibility=susceptibilities[i],
                is_influencer=self.dual_network.is_influencer(i),
                community_id=self.dual_network.get_community(i)
            )
            self.agents.append(agent)

        self.exposed_to_truth = np.zeros(size, dtype=bool)

    def get_public_neighbors(self, agent_id: int) -> List[int]:
        """获取公域邻居ID"""
        return self.dual_network.get_public_neighbors(agent_id)

    def get_private_neighbors(self, agent_id: int) -> List[int]:
        """获取私域邻居ID"""
        return self.dual_network.get_private_neighbors(agent_id)

    def get_public_neighbor_agents(self, agent_id: int) -> List[LLMAgent]:
        """获取公域邻居 Agent 列表"""
        neighbor_ids = self.get_public_neighbors(agent_id)
        return [self.agents[nid] for nid in neighbor_ids]

    def get_private_neighbor_agents(self, agent_id: int) -> List[LLMAgent]:
        """获取私域邻居 Agent 列表"""
        neighbor_ids = self.get_private_neighbors(agent_id)
        return [self.agents[nid] for nid in neighbor_ids]

    def get_public_edges(self) -> List[Tuple[int, int]]:
        """获取公域网络所有边"""
        return self.dual_network.get_public_edges()

    def get_private_edges(self) -> List[Tuple[int, int]]:
        """获取私域网络所有边"""
        return self.dual_network.get_private_edges()

    async def batch_decide_dual(
        self,
        llm_client: LLMClient,
        news_content: str,
        news_source: str,
        debunk_released: bool,
        cocoon_strength: float,
        progress_callback=None
    ) -> List[Dict]:
        """批量双模态决策"""
        async def decide_one(agent: LLMAgent, index: int):
            public_neighbors = self.get_public_neighbor_agents(agent.id)
            private_neighbors = self.get_private_neighbor_agents(agent.id)
            result = await agent.decide_opinion_dual(
                llm_client,
                public_neighbors,
                private_neighbors,
                news_content,
                news_source,
                debunk_released,
                cocoon_strength
            )
            if progress_callback:
                await progress_callback(index, self.size)
            return result

        tasks = [decide_one(agent, i) for i, agent in enumerate(self.agents)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Agent {i} 决策异常: {result}")
                processed.append({
                    "old_opinion": self.agents[i].opinion,
                    "new_opinion": self.agents[i].opinion,
                    "reasoning": "决策异常",
                    "is_silent": False,
                    "publish_channel": "none"
                })
            else:
                processed.append(result)

        return processed

    def apply_debunking(self):
        """应用辟谣效果"""
        self.exposed_to_truth[:] = True
        for agent in self.agents:
            agent.exposed_to_truth = True
            if agent.opinion < 0:
                impact = 0.2 * (1 - agent.belief_strength)
                agent.opinion = min(agent.opinion + impact, 1.0)

    def get_opinion_histogram(self, bins: int = 20) -> Dict[str, List]:
        """计算观点分布直方图"""
        opinions = [a.opinion for a in self.agents]
        hist, edges = np.histogram(opinions, bins=bins, range=(-1, 1))
        centers = [(edges[i] + edges[i+1]) / 2 for i in range(len(edges)-1)]
        return {"counts": hist.tolist(), "centers": centers}

    def to_agent_list(self) -> List[Dict]:
        """转换为可序列化的 Agent 列表"""
        return [agent.to_dict() for agent in self.agents]

    def get_statistics(self) -> Dict:
        """计算群体统计（分别统计公域和私域）"""
        opinions = [a.opinion for a in self.agents]

        # 整体统计
        overall_stats = {
            "rumor_spread_rate": np.mean([o < -0.2 for o in opinions]),
            "truth_acceptance_rate": np.mean([o > 0.2 for o in opinions]),
            "avg_opinion": float(np.mean(opinions)),
            "polarization_index": float(np.std(opinions) * 2),
            "silence_rate": np.mean([a.is_silent for a in self.agents])
        }

        # 公域统计（大V和其粉丝的观点）
        public_agent_ids = set()
        for influencer_id in self.dual_network.influencer_ids:
            public_agent_ids.add(influencer_id)
            public_agent_ids.update(self.get_public_neighbors(influencer_id))

        if public_agent_ids:
            public_opinions = [self.agents[aid].opinion for aid in public_agent_ids if aid < len(self.agents)]
            public_rumor_rate = np.mean([o < -0.2 for o in public_opinions]) if public_opinions else 0
            public_truth_rate = np.mean([o > 0.2 for o in public_opinions]) if public_opinions else 0
        else:
            public_rumor_rate = overall_stats["rumor_spread_rate"]
            public_truth_rate = overall_stats["truth_acceptance_rate"]

        # 私域统计（按社群聚合）
        community_stats = {}
        for comm_id in range(self.dual_network.num_communities):
            members = self.dual_network.get_community_members(comm_id)
            if members:
                comm_opinions = [self.agents[mid].opinion for mid in members if mid < len(self.agents)]
                community_stats[f"community_{comm_id}"] = {
                    "size": len(comm_opinions),
                    "avg_opinion": float(np.mean(comm_opinions)) if comm_opinions else 0,
                    "rumor_rate": np.mean([o < -0.2 for o in comm_opinions]) if comm_opinions else 0
                }

        # 私域整体谣言率（社群内部的平均）
        private_rumor_rate = np.mean([s["rumor_rate"] for s in community_stats.values()]) if community_stats else 0
        private_truth_rate = np.mean([s.get("truth_rate", 0) for s in community_stats.values()]) if community_stats else 0

        return {
            **overall_stats,
            "public_rumor_rate": float(public_rumor_rate),
            "public_truth_rate": float(public_truth_rate),
            "private_rumor_rate": float(private_rumor_rate),
            "private_truth_rate": float(private_truth_rate),
            "num_communities": self.dual_network.num_communities,
            "num_influencers": len(self.dual_network.influencer_ids),
            "community_stats": community_stats
        }

    def get_agent_snapshot(self, agent_id: int) -> Optional[Dict]:
        """获取指定 Agent 的决策快照"""
        if 0 <= agent_id < len(self.agents):
            agent = self.agents[agent_id]
            if agent.last_decision_snapshot:
                return agent.last_decision_snapshot
            else:
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
                    "fear_of_isolation": float(agent.fear_of_isolation),
                    "conviction": float(agent.conviction),
                    "is_silent": bool(agent.is_silent),
                    "perceived_climate": agent.perceived_climate,
                    "is_influencer": agent.is_influencer,
                    "community_id": agent.community_id,
                    "publish_channel": agent.publish_channel
                }
        return None


def get_agent_snapshot_global(agent_id: int) -> Optional[Dict]:
    """从全局存储获取 Agent 决策快照"""
    return AGENT_DECISION_SNAPSHOTS.get(agent_id)

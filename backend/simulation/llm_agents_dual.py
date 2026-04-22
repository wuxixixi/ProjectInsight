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


# Agent 决策 Prompt 模板 (双层模态版本 + 观点变化限制 + 知识图谱)
AGENT_PROMPT_TEMPLATE_DUAL = """你是一个社交媒体用户，正在关注一个热点事件的讨论。
观点范围: -1(完全误信) 到 1(完全正确认知)，0 表示中立。

## 你的个人特征
- 当前观点: {opinion:.2f}
- 信念强度: {belief_strength:.2f} (越强越难改变观点)
- 易感性: {susceptibility:.2f} (越强越容易受他人影响)
- 孤立恐惧感: {fear_of_isolation:.2f} (越高越害怕被社交孤立)
- 是否为大V: {is_influencer}

## 观点变化限制规则（重要）
- 你的信念强度为 {belief_strength:.2f}，因此你本轮观点最大变化幅度为 {max_change:.2f}
- 如果你选择沉默(is_silent=true)，观点变化幅度会进一步降低到 {max_change_silent:.2f}
- 请在限制范围内选择合理的新观点值

## 知识图谱上下文（事件结构化分析）
{graph_section}

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
{{"new_opinion": 数值在-1到1之间(注意变化幅度限制), "reasoning": "简短理由(20字内)", "emotion": "情绪状态(冷静/愤怒/焦虑/怀疑/释然)", "action": "行动选择(转发/评论/观望/权威回应/沉默)", "is_silent": boolean, "publish_channel": "public/private/both/none", "generated_comment": "评论内容(30字内)"}}
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
        self.exposed_to_negative = opinion < 0
        self.exposed_to_positive = False

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

    # ==================== 兼容属性访问器 ====================
    @property
    def exposed_to_rumor(self) -> bool:
        """兼容旧属性名: exposed_to_rumor → exposed_to_negative"""
        return self.exposed_to_negative

    @exposed_to_rumor.setter
    def exposed_to_rumor(self, value: bool):
        self.exposed_to_negative = value

    @property
    def exposed_to_truth(self) -> bool:
        """兼容旧属性名: exposed_to_truth → exposed_to_positive"""
        return self.exposed_to_positive

    @exposed_to_truth.setter
    def exposed_to_truth(self, value: bool):
        self.exposed_to_positive = value

    def _build_graph_section(self, knowledge_graph: Dict) -> str:
        """
        构建知识图谱上下文段落（含注意力过滤指令）

        Args:
            knowledge_graph: 知识图谱数据

        Returns:
            格式化的图谱上下文文本
        """
        lines = []

        # 事件摘要
        summary = knowledge_graph.get("summary", "")
        if summary:
            lines.append(f"- 事件摘要: {summary}")

        # 关键词
        keywords = knowledge_graph.get("keywords", [])
        if keywords:
            lines.append(f"- 关键词: {', '.join(keywords[:5])}")

        # 情感倾向和可信度
        sentiment = knowledge_graph.get("sentiment", "")
        credibility = knowledge_graph.get("credibility_hint", "")
        if sentiment:
            lines.append(f"- 情感倾向: {sentiment}")
        if credibility:
            lines.append(f"- 可信度: {credibility}")

        # 实体列表
        entities = knowledge_graph.get("entities", [])
        if entities:
            lines.append(f"\n**涉及实体 ({len(entities)}个):**")
            # 根据人设选择最相关的实体
            relevant_entities = self._select_relevant_entities(entities)
            for i, entity in enumerate(relevant_entities[:5]):  # 显示最多5个相关实体
                entity_type = entity.get("type", "其他")
                entity_name = entity.get("name", "未知")
                entity_desc = entity.get("description", "")
                importance = entity.get("importance", 3)
                importance_marker = "⭐" * min(importance, 5)
                lines.append(f"  {i+1}. [{entity_type}] {entity_name} - {entity_desc} {importance_marker}")

        # 关键关系
        relations = knowledge_graph.get("relations", [])
        if relations:
            lines.append(f"\n**实体关系 ({len(relations)}条):**")
            for rel in relations[:4]:
                source = rel.get("source", "?")
                target = rel.get("target", "?")
                action = rel.get("action", rel.get("type", "关联"))
                lines.append(f"  • {source} --[{action}]--> {target}")

        # ==================== 注意力过滤指令 ====================
        lines.append("")
        lines.append("---")
        lines.append("⚠️ **注意力过滤指令（重要）**:")
        lines.append(f"你的【人设类型】是「{self.persona.get('type', '普通用户')}」: {self.persona.get('desc', '')}")
        lines.append("请严格根据你的人设特征，从上述图谱中挑选出你最关心的 2-3 个实体节点及其关系，忽略其他你不在乎的节点。")
        lines.append("基于这部分残缺的局部信息，做出你的立场判断和评论。")
        lines.append("")
        lines.append("例如：")
        lines.append("- 「易恐慌型」用户应更关注负面信息和风险相关实体")
        lines.append("- 「理性分析型」用户应关注事实性信息和权威来源")
        lines.append("- 「从众型」用户应关注大多数人关注的实体")
        lines.append("- 「怀疑论者」应关注矛盾和可疑之处")

        return "\n".join(lines)

    def _select_relevant_entities(self, entities: List[Dict]) -> List[Dict]:
        """
        根据人设选择最相关的实体

        Args:
            entities: 实体列表

        Returns:
            筛选后的实体列表
        """
        # 根据人设类型筛选相关实体
        persona_type = self.persona.get("type", "")

        priority_types = []
        if "低媒介素养" in persona_type or "从众" in persona_type:
            # 关注人物和情绪化内容
            priority_types = ["人物", "事件", "其他"]
        elif "理性" in persona_type:
            # 关注组织和时间
            priority_types = ["组织", "地点", "时间"]
        elif "意见领袖" in persona_type:
            # 关注影响力和传播
            priority_types = ["人物", "组织", "概念"]
        else:
            priority_types = ["人物", "事件", "组织"]

        # 按优先级排序
        prioritized = []
        for entity in entities:
            entity_type = entity.get("type", "其他")
            if entity_type in priority_types:
                prioritized.append(entity)

        # 如果筛选后的数量不足，返回原列表的前几个
        if len(prioritized) < 2:
            return entities[:3]

        return prioritized[:3]

    def scan_public_climate(
        self,
        public_neighbors: List['LLMAgent'],
        opinion_snapshot: Optional[Dict] = None
    ) -> Dict:
        """扫描公域舆论气候（支持快照一致性）"""
        if not public_neighbors:
            return {"total": 0, "pro_negative_ratio": 0.0, "pro_positive_ratio": 0.0,
                    "neutral_ratio": 1.0, "silent_ratio": 0.0, "avg_opinion": 0.0,
                    # 兼容旧键名
                    "pro_rumor_ratio": 0.0, "pro_truth_ratio": 0.0}

        total = len(public_neighbors)

        # 使用快照中的观点（如果提供）
        if opinion_snapshot:
            opinions = [opinion_snapshot.get(n.id, n.opinion) for n in public_neighbors]
        else:
            opinions = [n.opinion for n in public_neighbors]

        pro_negative = sum(1 for o in opinions if o < 0)
        pro_positive = sum(1 for o in opinions if o > 0)
        neutral = total - pro_negative - pro_positive
        avg_opinion = sum(opinions) / total

        pro_negative_ratio = pro_negative / total
        pro_positive_ratio = pro_positive / total

        return {
            "total": total,
            "pro_negative_ratio": pro_negative_ratio,
            "pro_positive_ratio": pro_positive_ratio,
            "neutral_ratio": neutral / total,
            "silent_ratio": 0.0,  # 公域网络不追踪沉默
            "avg_opinion": avg_opinion,
            # 兼容旧键名
            "pro_rumor_ratio": pro_negative_ratio,
            "pro_truth_ratio": pro_positive_ratio,
        }

    def scan_private_climate(
        self,
        private_neighbors: List['LLMAgent'],
        opinion_snapshot: Optional[Dict] = None
    ) -> Dict:
        """扫描私域舆论气候（支持快照一致性）"""
        if not private_neighbors:
            return {"total": 0, "pro_negative_ratio": 0.0, "pro_positive_ratio": 0.0,
                    "neutral_ratio": 1.0, "silent_ratio": 0.0, "avg_opinion": 0.0,
                    # 兼容旧键名
                    "pro_rumor_ratio": 0.0, "pro_truth_ratio": 0.0}

        total = len(private_neighbors)

        # 使用快照中的观点（如果提供）
        if opinion_snapshot:
            opinions = [opinion_snapshot.get(n.id, n.opinion) for n in private_neighbors]
        else:
            opinions = [n.opinion for n in private_neighbors]

        pro_negative = sum(1 for o in opinions if o < 0)
        pro_positive = sum(1 for o in opinions if o > 0)
        neutral = total - pro_negative - pro_positive
        avg_opinion = sum(opinions) / total

        pro_negative_ratio = pro_negative / total
        pro_positive_ratio = pro_positive / total

        return {
            "total": total,
            "pro_negative_ratio": pro_negative_ratio,
            "pro_positive_ratio": pro_positive_ratio,
            "neutral_ratio": neutral / total,
            "silent_ratio": 0.0,
            "avg_opinion": avg_opinion,
            # 兼容旧键名
            "pro_rumor_ratio": pro_negative_ratio,
            "pro_truth_ratio": pro_positive_ratio,
        }

    def build_prompt_dual(
        self,
        public_neighbors: List['LLMAgent'],
        private_neighbors: List['LLMAgent'],
        news_content: str,
        news_source: str,
        response_released: bool,
        cocoon_strength: float,
        opinion_snapshot: Optional[Dict] = None,
        knowledge_graph: Optional[Dict] = None
    ) -> Tuple[str, List[str]]:
        """
        构建双模态决策 Prompt

        Args:
            public_neighbors: 公域邻居列表
            private_neighbors: 私域邻居列表
            news_content: 新闻内容
            news_source: 新闻来源
            response_released: 是否已发布权威回应
            cocoon_strength: 茧房强度
            opinion_snapshot: 观点快照，用于并发一致性
            knowledge_graph: 知识图谱数据（可选）
        """
        # 计算观点变化限制
        max_change = 0.3 * (1 - self.belief_strength * 0.5)
        max_change_silent = 0.1 * (1 - self.belief_strength * 0.5)

        # 构建知识图谱上下文
        if knowledge_graph:
            graph_section = self._build_graph_section(knowledge_graph)
        else:
            graph_section = "- 暂无结构化分析"

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

        # 权威回应状态
        if response_released:
            info_lines.append("【权威回应】已发布，指出信息不实")

        # 算法茧房效应
        if cocoon_strength > 0.3:
            if self.opinion < 0:
                info_lines.append("算法推荐: 更多支持负面信念的内容")
            else:
                info_lines.append("算法推荐: 更多支持正确认知的内容")

        info_section = "\n".join(f"- {line}" for line in info_lines)

        # 公域舆论环境（使用快照）
        public_climate = self.scan_public_climate(public_neighbors, opinion_snapshot)
        if public_climate["total"] > 0:
            public_climate_section = f"""- 公域粉丝数: {public_climate['total']}
- 公域平均观点: {public_climate['avg_opinion']:.2f}
- 公域负面信念率: {public_climate['pro_negative_ratio']*100:.0f}%
- 公域正确认知率: {public_climate['pro_positive_ratio']*100:.0f}%"""
        else:
            public_climate_section = "- 暂无公域粉丝"

        # 私域舆论环境（使用快照）
        private_climate = self.scan_private_climate(private_neighbors, opinion_snapshot)
        if private_climate["total"] > 0:
            private_climate_section = f"""- 私域好友数: {private_climate['total']}
- 私域平均观点: {private_climate['avg_opinion']:.2f}
- 私域负面信念率: {private_climate['pro_negative_ratio']*100:.0f}%
- 私域正确认知率: {private_climate['pro_positive_ratio']*100:.0f}%"""
        else:
            private_climate_section = "- 暂无私域好友"

        # 保存气候数据（双层结构 + 扁平汇总）
        # 计算扁平汇总结构（用于前端透视面板兼容）
        all_neighbors = public_neighbors + private_neighbors
        if all_neighbors:
            all_opinions = [opinion_snapshot.get(n.id, n.opinion) for n in all_neighbors] if opinion_snapshot else [n.opinion for n in all_neighbors]
            total_all = len(all_neighbors)
            pro_negative_all = sum(1 for o in all_opinions if o < 0)
            pro_positive_all = sum(1 for o in all_opinions if o > 0)
            neutral_all = total_all - pro_negative_all - pro_positive_all
            avg_opinion_all = sum(all_opinions) / total_all
        else:
            total_all = 0
            pro_negative_all = 0
            pro_positive_all = 0
            neutral_all = 1
            avg_opinion_all = 0

        pro_negative_ratio_all = pro_negative_all / total_all if total_all > 0 else 0.0
        pro_positive_ratio_all = pro_positive_all / total_all if total_all > 0 else 0.0

        self.perceived_climate = {
            # 双层结构（保留用于内部分析）
            "public": public_climate,
            "private": private_climate,
            # 扁平结构（用于前端透视面板兼容）
            "total": total_all,
            "pro_negative_ratio": pro_negative_ratio_all,
            "pro_positive_ratio": pro_positive_ratio_all,
            "neutral_ratio": neutral_all / total_all if total_all > 0 else 1.0,
            "silent_ratio": 0.0,
            "avg_opinion": avg_opinion_all,
            # 兼容旧键名
            "pro_rumor_ratio": pro_negative_ratio_all,
            "pro_truth_ratio": pro_positive_ratio_all,
        }

        prompt = AGENT_PROMPT_TEMPLATE_DUAL.format(
            opinion=self.opinion,
            belief_strength=self.belief_strength,
            susceptibility=self.susceptibility,
            fear_of_isolation=self.fear_of_isolation,
            conviction=self.conviction,
            max_change=max_change,
            max_change_silent=max_change_silent,
            is_influencer="是（大V）" if self.is_influencer else "否",
            graph_section=graph_section,
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
        knowledge_graph: Optional[Dict] = None,
        response_released: bool = False,
        cocoon_strength: float = 0.5,
        opinion_snapshot: Optional[Dict] = None
    ) -> Dict:
        """双模态决策（支持快照一致性）"""
        prompt, received_news = self.build_prompt_dual(
            public_neighbors, private_neighbors, news_content, news_source,
            response_released, cocoon_strength, opinion_snapshot, knowledge_graph
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
                "llm_raw_response": result.get("_raw_response", result),  # 保存原始响应
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
            "exposed_to_negative": bool(self.exposed_to_negative),
            "exposed_to_positive": bool(self.exposed_to_positive),
            # 兼容旧键名
            "exposed_to_rumor": bool(self.exposed_to_negative),
            "exposed_to_truth": bool(self.exposed_to_positive),
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
        initial_negative_spread: float = 0.3,
        initial_rumor_spread: float = None,  # 兼容旧参数名
        llm_config: Optional[LLMConfig] = None,
        # 双层网络参数
        num_communities: int = 8,
        public_m: int = 3,
        intra_community_prob: float = 0.3,
        inter_community_prob: float = 0.01
    ):
        self.size = size
        self.llm_config = llm_config or LLMConfig()

        # 兼容旧参数名
        if initial_rumor_spread is not None:
            initial_negative_spread = initial_rumor_spread

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

        # 初始化观点分布：负面信念 / 中立 / 正面信念 三段
        opinions = np.zeros(size)
        negative_believers = int(size * initial_negative_spread)
        neutral_count = int(size * np.random.uniform(0.15, 0.25))
        neutral_count = min(neutral_count, size - negative_believers)
        positive_believers = size - negative_believers - neutral_count

        opinions[:negative_believers] = np.random.uniform(-0.8, -0.2, negative_believers)
        opinions[negative_believers:negative_believers + neutral_count] = np.random.uniform(-0.05, 0.05, neutral_count)
        opinions[negative_believers + neutral_count:] = np.random.uniform(0.1, 0.5, positive_believers)

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

        self.exposed_to_positive = np.zeros(size, dtype=bool)

    # ==================== 兼容属性访问器 ====================
    @property
    def exposed_to_truth(self) -> np.ndarray:
        """兼容旧属性名: exposed_to_truth → exposed_to_positive"""
        return self.exposed_to_positive

    @exposed_to_truth.setter
    def exposed_to_truth(self, value: np.ndarray):
        self.exposed_to_positive = value

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
        knowledge_graph: Optional[Dict] = None,
        response_released: bool = False,
        cocoon_strength: float = 0.5,
        progress_callback=None
    ) -> List[Dict]:
        """批量双模态决策（使用观点快照保证并发一致性）"""
        # === 关键修复：在决策前保存所有 Agent 的观点快照 ===
        opinion_snapshot = {}
        for agent in self.agents:
            opinion_snapshot[agent.id] = float(agent.opinion)
            opinion_snapshot[f"{agent.id}_is_silent"] = agent.is_silent

        # 使用计数器跟踪已完成的agent数量
        completed_count = 0
        completed_lock = asyncio.Lock()

        async def decide_one(agent: LLMAgent):
            nonlocal completed_count
            public_neighbors = self.get_public_neighbor_agents(agent.id)
            private_neighbors = self.get_private_neighbor_agents(agent.id)
            result = await agent.decide_opinion_dual(
                llm_client,
                public_neighbors,
                private_neighbors,
                news_content,
                news_source,
                knowledge_graph,
                response_released,
                cocoon_strength,
                opinion_snapshot  # 传入快照
            )
            # 原子递增完成计数
            async with completed_lock:
                completed_count += 1
                current_count = completed_count
            if progress_callback:
                # 传递实际完成数量：completed, total, agent_id, agent_opinion
                await progress_callback(current_count, self.size, agent.id, agent.opinion)
            return result

        tasks = [decide_one(agent) for agent in self.agents]
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

    def apply_authoritative_response(self, effectiveness: float = 0.2):
        """
        应用权威回应效果（动态版本）

        Args:
            effectiveness: 基础权威回应效果系数（由引擎根据延迟和茧房强度计算）
        """
        self.exposed_to_positive[:] = True
        for agent in self.agents:
            agent.exposed_to_positive = True
            if agent.opinion < 0:
                # 动态计算：考虑信念强度和易感性
                impact = effectiveness * (1 - agent.belief_strength * 0.5) * (0.5 + agent.susceptibility * 0.5)
                agent.opinion = min(agent.opinion + impact, 1.0)

    def apply_debunking(self, effectiveness: float = 0.2):
        """兼容旧方法名: apply_debunking → apply_authoritative_response"""
        return self.apply_authoritative_response(effectiveness)

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
        opinions = np.array([a.opinion for a in self.agents])
        belief_strengths = np.array([a.belief_strength for a in self.agents])
        # 三个互斥类别：拒绝/中立/相信
        reject_mask = opinions < -0.1
        uncertain_mask = np.abs(opinions) <= 0.1
        believe_mask = opinions > 0.1

        believe_rate = float(np.mean(believe_mask))
        reject_rate = float(np.mean(reject_mask))
        uncertain_rate = float(np.mean(uncertain_mask))

        # 整体统计（与 opinion 直接对应）
        overall_stats = {
            # 基础统计
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
            "polarization_index": float(np.std(opinions) * 2),
            "silence_rate": float(np.mean([a.is_silent for a in self.agents])),
            # 兼容旧键名
            "negative_belief_rate": reject_rate,
            "positive_belief_rate": believe_rate,
            "negative_spread_rate": reject_rate,
            "positive_acceptance_rate": believe_rate,
            "rumor_spread_rate": reject_rate,
            "truth_acceptance_rate": believe_rate,
            "deep_negative_rate": float(np.mean(reject_mask & (belief_strengths > 0.5))),
            "weighted_negative_index": float(
                np.mean(np.abs(np.minimum(opinions, 0)) * belief_strengths)
                if np.any(reject_mask) else 0.0
            ),
            "deep_positive_rate": float(np.mean(believe_mask & (belief_strengths > 0.5))),
        }

        # 公域统计（大V和其粉丝的观点）
        public_agent_ids = set()
        for influencer_id in self.dual_network.influencer_ids:
            public_agent_ids.add(influencer_id)
            public_agent_ids.update(self.get_public_neighbors(influencer_id))

        if public_agent_ids:
            public_opinions = np.array([self.agents[aid].opinion for aid in public_agent_ids if aid < len(self.agents)])
            public_reject_rate = float(np.mean(public_opinions < 0)) if len(public_opinions) > 0 else 0
            public_believe_rate = float(np.mean(public_opinions > 0)) if len(public_opinions) > 0 else 0
        else:
            public_reject_rate = overall_stats["reject_rate"]
            public_believe_rate = overall_stats["believe_rate"]

        # 私域统计（按社群聚合）
        community_stats = {}
        for comm_id in range(self.dual_network.num_communities):
            members = self.dual_network.get_community_members(comm_id)
            if members:
                comm_opinions = np.array([self.agents[mid].opinion for mid in members if mid < len(self.agents)])
                comm_reject_rate = float(np.mean(comm_opinions < 0)) if len(comm_opinions) > 0 else 0
                comm_believe_rate = float(np.mean(comm_opinions > 0)) if len(comm_opinions) > 0 else 0
                community_stats[f"community_{comm_id}"] = {
                    "size": len(comm_opinions),
                    "avg_opinion": float(np.mean(comm_opinions)) if len(comm_opinions) > 0 else 0,
                    "reject_rate": comm_reject_rate,
                    "believe_rate": comm_believe_rate,
                    # 兼容旧键名
                    "negative_rate": comm_reject_rate,
                    "positive_rate": comm_believe_rate,
                    "rumor_rate": comm_reject_rate,
                }

        # 私域整体拒绝率（社群内部的平均）
        private_reject_rate = np.mean([s["reject_rate"] for s in community_stats.values()]) if community_stats else 0
        private_believe_rate = np.mean([s.get("believe_rate", 0) for s in community_stats.values()]) if community_stats else 0

        return {
            **overall_stats,
            "public_negative_rate": float(public_reject_rate),
            "public_positive_rate": float(public_believe_rate),
            "private_negative_rate": float(private_reject_rate),
            "private_positive_rate": float(private_believe_rate),
            # 兼容旧键名
            "public_rumor_rate": float(public_reject_rate),
            "public_truth_rate": float(public_believe_rate),
            "private_rumor_rate": float(private_reject_rate),
            "private_truth_rate": float(private_believe_rate),
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

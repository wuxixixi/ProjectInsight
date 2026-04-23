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
from .math_model_enhanced import EnhancedMathModel
from .persona import (
    PERSONA_TEMPLATES, get_persona, AGENT_DECISION_SNAPSHOTS,
    get_agent_snapshot, set_agent_snapshot, clear_agent_snapshots
)

logger = logging.getLogger(__name__)


# Agent 决策 Prompt 模板 (含沉默的螺旋、观点变化限制、知识图谱注意力过滤)
AGENT_PROMPT_TEMPLATE = """你是一个社交媒体用户，正在关注一个热点事件的讨论。
观点范围: -1(完全误信负面信息) 到 1(完全相信正确认知)，0 表示中立。

## 你的个人特征
- 当前观点: {opinion:.2f}
- 信念强度: {belief_strength:.2f} (越强越难改变观点)
- 易感性: {susceptibility:.2f} (越强越容易受他人影响)
- 孤立恐惧感: {fear_of_isolation:.2f} (越高越害怕被社交孤立)
- 初始信念强度: {conviction:.2f} (形成观点时的坚定程度)
- 人设类型: {persona_type} ({persona_desc})

## 观点变化限制规则（重要）
- 你的信念强度为 {belief_strength:.2f}，因此你本轮观点最大变化幅度为 {max_change:.2f}
- 如果你选择沉默(is_silent=true)，观点变化幅度会进一步降低到 {max_change_silent:.2f}
- 请在限制范围内选择合理的新观点值

{graph_section}

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
{{"new_opinion": 数值在-1到1之间(注意变化幅度限制), "reasoning": "简短理由(20字内)", "emotion": "情绪状态(冷静/愤怒/焦虑/怀疑/释然)", "action": "行动选择(转发/评论/观望/权威回应/沉默)", "is_silent": boolean(是否选择沉默), "generated_comment": "如果选择评论，生成的评论内容(30字内)", "focused_entities": ["你关注的实体名称列表"]}}
"""


# ==================== 知识图谱上下文模板 ====================

GRAPH_SECTION_TEMPLATE = """## 知识图谱上下文（事件结构化分析）
你收到了一份关于最新事件的结构化信息图谱。

**事件摘要**: {summary}
**关键词**: {keywords}
**情感倾向**: {sentiment}
**可信度提示**: {credibility_hint}

**实体列表**:
{entities_text}

**实体关系**:
{relations_text}

---

⚠️ **注意力过滤指令（重要）**:
请严格根据你的【人设类型】和【核心关注点】，从上述图谱中挑选出你最关心的 2-3 个实体节点及其关系，并忽略其他你不在乎的节点。
基于这部分残缺的局部信息，做出你的立场判断和评论。

例如：
- 如果你是"易恐慌型"，你应该更关注负面信息和风险相关的实体
- 如果你是"理性分析型"，你应该关注事实性信息和权威来源
- 如果你是"从众型"，你应该关注大多数人关注的实体
- 如果你是"怀疑论者"，你应该关注矛盾和可疑之处
"""

GRAPH_SECTION_EMPTY = """## 知识图谱上下文
（暂无结构化事件信息）"""


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
        susceptibility: float,
        belief_reduction_on_authority: float = 0.1,
        silence_opinion_change_factor: float = 0.1
    ):
        self.id = agent_id
        self.opinion = opinion
        self.belief_strength = belief_strength
        self.influence = influence
        self.susceptibility = susceptibility
        self.belief_reduction_on_authority = belief_reduction_on_authority
        self.silence_opinion_change_factor = silence_opinion_change_factor
        self.exposed_to_negative = opinion < 0
        self.exposed_to_positive = False

        # 人设背景
        self.persona = get_persona(agent_id, opinion, susceptibility, influence)

        # 决策历史
        self.decision_history: List[Dict] = []

        # 最新决策上下文快照
        self.last_decision_snapshot: Optional[Dict] = None

        # === 沉默的螺旋：新增属性 ===
        _rng = np.random.RandomState(agent_id + 1000)
        self.fear_of_isolation = float(_rng.beta(2, 2))  # 孤立恐惧感 [0, 1]
        self.conviction = float(_rng.beta(2, 2))  # 初始信念强度 [0, 1]
        self.is_silent = False  # 是否选择沉默
        self.perceived_climate: Optional[Dict] = None  # 感知到的舆论气候

    # ==================== 兼容属性访问器 ====================
    @property
    def exposed_to_rumor(self) -> bool:
        """兼容旧属性名: exposed_to_rumor -> exposed_to_negative"""
        return self.exposed_to_negative

    @exposed_to_rumor.setter
    def exposed_to_rumor(self, value: bool):
        self.exposed_to_negative = value

    @property
    def exposed_to_truth(self) -> bool:
        """兼容旧属性名: exposed_to_truth -> exposed_to_positive"""
        return self.exposed_to_positive

    @exposed_to_truth.setter
    def exposed_to_truth(self, value: bool):
        self.exposed_to_positive = value

    def scan_neighbor_climate(
        self,
        neighbors: List['LLMAgent'],
        opinion_snapshot: Optional[Dict[int, float]] = None
    ) -> Dict:
        """
        扫描邻居状态，计算感知到的舆论气候

        重要：根据沉默的螺旋理论，沉默者的观点不应影响他人的决策过程。
        因此，在计算邻居平均观点和观点分布时，自动忽略 is_silent=true 的节点。

        Args:
            neighbors: 邻居 Agent 列表
            opinion_snapshot: 观点快照 {agent_id: opinion}，用于并发一致性

        Returns:
            包含邻居统计信息的字典
        """
        if not neighbors:
            return {
                "total": 0,
                "pro_negative_ratio": 0.0,
                "pro_positive_ratio": 0.0,
                "neutral_ratio": 1.0,
                "silent_ratio": 0.0,
                "avg_opinion": 0.0,
                "active_total": 0
            }

        # 使用快照或实时状态判断邻居是否沉默
        if opinion_snapshot:
            is_silent_map = {
                n.id: opinion_snapshot.get(f"{n.id}_is_silent", n.is_silent)
                for n in neighbors
            }
            opinions = [opinion_snapshot.get(n.id, n.opinion) for n in neighbors]
        else:
            is_silent_map = {n.id: n.is_silent for n in neighbors}
            opinions = [n.opinion for n in neighbors]

        # 根据沉默的螺旋理论：忽略沉默节点，只计算活跃邻居
        active_neighbors = [
            (n, op) for n, op in zip(neighbors, opinions)
            if not is_silent_map.get(n.id, False)
        ]

        if not active_neighbors:
            # 所有邻居都沉默
            return {
                "total": len(neighbors),
                "pro_negative_ratio": 0.0,
                "pro_positive_ratio": 0.0,
                "neutral_ratio": 1.0,
                "silent_ratio": 1.0,
                "avg_opinion": 0.0,
                "active_total": 0
            }

        active_count = len(active_neighbors)
        active_opinions = [op for _, op in active_neighbors]

        # 计算活跃邻居的统计
        total = len(neighbors)
        silent_count = total - active_count

        pro_negative = sum(1 for o in active_opinions if o < 0)
        pro_positive = sum(1 for o in active_opinions if o > 0)
        neutral = active_count - pro_negative - pro_positive
        avg_opinion = sum(active_opinions) / active_count

        climate = {
            "total": total,
            "active_total": active_count,  # 新增：活跃邻居数量
            "pro_negative_ratio": pro_negative / active_count if active_count > 0 else 0.0,
            "pro_positive_ratio": pro_positive / active_count if active_count > 0 else 0.0,
            "neutral_ratio": neutral / active_count if active_count > 0 else 0.0,
            "silent_ratio": silent_count / total,
            "avg_opinion": avg_opinion
        }

        self.perceived_climate = climate
        return climate

    def build_prompt(
        self,
        neighbor_agents: List['LLMAgent'],
        response_released: bool,
        cocoon_strength: float,
        opinion_snapshot: Optional[Dict[int, float]] = None,
        knowledge_graph: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[str]]:
        """
        构建决策 Prompt

        Args:
            neighbor_agents: 邻居 Agent 列表 (用于扫描舆论气候)
            response_released: 是否已发布权威回应
            cocoon_strength: 茧房强度
            opinion_snapshot: 观点快照，用于并发一致性
            knowledge_graph: 知识图谱数据（包含entities, relations, summary等）

        Returns:
            (prompt, info_lines) - Prompt文本和信息行列表
        """
        # 扫描邻居舆论气候（使用快照）
        climate = self.scan_neighbor_climate(neighbor_agents, opinion_snapshot)

        # 计算观点变化限制
        max_change = 0.3 * (1 - self.belief_strength * 0.5)
        max_change_silent = 0.1 * (1 - self.belief_strength * 0.5)

        # ==================== 构建知识图谱上下文 ====================
        graph_section = self._build_graph_section(knowledge_graph)

        # 构建信息部分
        info_lines = []

        # 邻居观点统计
        if climate["total"] > 0:
            info_lines.append(f"- 邻居数量: {climate['total']}")
            info_lines.append(f"- 邻居平均观点: {climate['avg_opinion']:.2f}")
            info_lines.append(f"- 邻居分布: {climate['pro_negative_ratio']*100:.0f}%误信, {climate['neutral_ratio']*100:.0f}%中立, {climate['pro_positive_ratio']*100:.0f}%正确认知")
            if climate['silent_ratio'] > 0:
                info_lines.append(f"- 沉默的邻居: {climate['silent_ratio']*100:.0f}%")

        # 权威回应状态
        if response_released:
            info_lines.append("- **官方已发布权威回应信息**: 澄清事实、还原真相")

        # 算法推荐模拟 (茧房效应)
        if cocoon_strength > 0.3:
            if self.opinion < 0:
                info_lines.append("- 算法推荐: 更多支持负面信念的内容")
            else:
                info_lines.append("- 算法推荐: 更多支持正确认知的内容")

        info_section = "\n".join(info_lines) if info_lines else "- 暂无新信息"

        # 构建社交压力部分
        social_pressure_lines = []

        if climate["total"] > 0:
            # 判断自己的观点是否与主流相反
            my_stance = "误信" if self.opinion < 0 else ("正确认知" if self.opinion > 0 else "不确定")
            majority_stance = "误信" if climate['pro_negative_ratio'] > climate['pro_positive_ratio'] else "正确认知" if climate['pro_positive_ratio'] > climate['pro_negative_ratio'] else "不确定"

            # 计算主流观点比例
            majority_ratio = max(climate['pro_negative_ratio'], climate['pro_positive_ratio'])

            social_pressure_lines.append(f"- 你的观点: {my_stance} ({self.opinion:.2f})")
            social_pressure_lines.append(f"- 周围主流观点: {majority_stance} (占比{majority_ratio*100:.0f}%)")

            # 判断是否处于少数派
            is_minority = False
            if self.opinion < 0 and climate['pro_positive_ratio'] > climate['pro_negative_ratio']:
                is_minority = True
            elif self.opinion > 0 and climate['pro_negative_ratio'] > climate['pro_positive_ratio']:
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
            persona_type=self.persona.get("type", "普通用户"),
            persona_desc=self.persona.get("desc", ""),
            graph_section=graph_section,
            info_section=info_section,
            social_pressure_section=social_pressure_section
        )

        return prompt, info_lines

    def _build_graph_section(self, knowledge_graph: Optional[Dict[str, Any]]) -> str:
        """
        构建知识图谱上下文部分

        Args:
            knowledge_graph: 知识图谱数据

        Returns:
            格式化的图谱上下文字符串
        """
        if not knowledge_graph or not knowledge_graph.get("entities"):
            return GRAPH_SECTION_EMPTY

        # 提取图谱信息
        summary = knowledge_graph.get("summary", "暂无摘要")
        keywords = knowledge_graph.get("keywords", [])
        sentiment = knowledge_graph.get("sentiment", "中性")
        credibility_hint = knowledge_graph.get("credibility_hint", "不确定")
        entities = knowledge_graph.get("entities", [])
        relations = knowledge_graph.get("relations", [])

        # 构建实体列表文本（限制显示数量）
        entities_text = ""
        for i, entity in enumerate(entities[:8]):  # 最多显示8个实体
            importance_marker = "⭐" * min(entity.get("importance", 3), 5)
            entities_text += f"{i+1}. [{entity.get('type', '未知')}] {entity.get('name', '未知')} - {entity.get('description', '')} {importance_marker}\n"
        if len(entities) > 8:
            entities_text += f"... 共 {len(entities)} 个实体\n"

        # 构建关系列表文本（限制显示数量）
        relations_text = ""
        if relations:
            # 创建实体ID到名称的映射
            entity_map = {e.get("id"): e.get("name") for e in entities}
            for i, relation in enumerate(relations[:6]):  # 最多显示6个关系
                source_name = entity_map.get(relation.get("source"), relation.get("source", "?"))
                target_name = entity_map.get(relation.get("target"), relation.get("target", "?"))
                action = relation.get("action", relation.get("type", "关联"))
                relations_text += f"{i+1}. {source_name} --[{action}]--> {target_name}\n"
            if len(relations) > 6:
                relations_text += f"... 共 {len(relations)} 个关系\n"
        else:
            relations_text = "（暂无明确关系）\n"

        # 格式化关键词
        keywords_text = "、".join(keywords[:5]) if keywords else "无"

        return GRAPH_SECTION_TEMPLATE.format(
            summary=summary,
            keywords=keywords_text,
            sentiment=sentiment,
            credibility_hint=credibility_hint,
            entities_text=entities_text,
            relations_text=relations_text
        )

    async def decide_opinion(
        self,
        llm_client: LLMClient,
        neighbor_agents: List['LLMAgent'],
        response_released: bool,
        cocoon_strength: float,
        opinion_snapshot: Optional[Dict[int, float]] = None,
        knowledge_graph: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        通过 LLM 决定新观点

        Args:
            llm_client: LLM 客户端
            neighbor_agents: 邻居 Agent 列表 (用于扫描舆论气候)
            response_released: 是否已发布权威回应
            cocoon_strength: 茧房强度
            opinion_snapshot: 观点快照，用于并发一致性
            knowledge_graph: 知识图谱数据

        Returns:
            {"new_opinion": float, "reasoning": str, "is_silent": bool, ...}
        """
        prompt, received_news = self.build_prompt(
            neighbor_agents, response_released, cocoon_strength, opinion_snapshot, knowledge_graph
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

            # 判断 action 类型
            action_normalized = action.strip().lower() if action else ""
            is_responding = "权威回应" in action  # 主动参与权威回应
            is_reversing = "立场反转" in action or "反转" in action  # 立场反转

            # 记录观点变化幅度
            change = new_opinion - self.opinion
            abs_change = abs(change)

            # 如果选择沉默，观点变化应该更小（保持原有观点）
            if is_silent:
                # 沉默时观点变化幅度降低
                max_change = self.silence_opinion_change_factor * (1 - self.belief_strength * 0.5)
                if abs_change > max_change:
                    new_opinion = self.opinion + np.sign(change) * max_change
                    new_opinion = np.clip(new_opinion, -1, 1)
                    change = new_opinion - self.opinion
            else:
                # 信念强度约束：观点变化幅度受信念强度限制
                max_change = 0.3 * (1 - self.belief_strength * 0.5)

                # === 关键修改：权威回应/立场反转 action 应允许突破限制 ===
                if is_responding or is_reversing:
                    # 权威回应或立场反转时，允许更大的观点变化（放宽到1.5倍）
                    # 同时需要调整 belief_strength 以保持逻辑一致
                    relaxed_max_change = min(0.5, max_change * 1.5)
                    if abs_change > relaxed_max_change:
                        new_opinion = self.opinion + np.sign(change) * relaxed_max_change
                        new_opinion = np.clip(new_opinion, -1, 1)
                        change = new_opinion - self.opinion

                    # 权威回应/反转后，降低信念强度（因为行动与原观点不一致）
                    self.belief_strength = max(0.1, self.belief_strength - self.belief_reduction_on_authority)
                else:
                    # 普通情况：严格限制观点变化幅度
                    if abs_change > max_change:
                        new_opinion = self.opinion + np.sign(change) * max_change
                        new_opinion = np.clip(new_opinion, -1, 1)
                        change = new_opinion - self.opinion

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
                "llm_raw_response": result.get("_raw_response", result),  # 保存原始响应
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
            "exposed_to_negative": bool(self.exposed_to_negative),
            "exposed_to_positive": bool(self.exposed_to_positive),
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
        initial_negative_spread: float = 0.3,
        initial_rumor_spread: float = None,  # 兼容旧参数名
        network_type: str = "small_world",
        llm_config: Optional[LLMConfig] = None,
        belief_reduction_on_authority: float = 0.1,
        silence_opinion_change_factor: float = 0.1
    ):
        # 兼容旧参数名
        if initial_rumor_spread is not None:
            initial_negative_spread = initial_rumor_spread

        self.size = size
        self.network_type = network_type
        self.llm_config = llm_config or LLMConfig()

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
        self.agents: List[LLMAgent] = [
            LLMAgent(
                agent_id=i,
                opinion=opinions[i],
                belief_strength=belief_strengths[i],
                influence=influences[i],
                susceptibility=susceptibilities[i],
                belief_reduction_on_authority=belief_reduction_on_authority,
                silence_opinion_change_factor=silence_opinion_change_factor
            )
            for i in range(size)
        ]

        # 构建社交网络
        self.network = self._build_network(network_type)

        # 暴露状态
        self.exposed_to_positive = np.zeros(size, dtype=bool)

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
        response_released: bool,
        cocoon_strength: float,
        progress_callback=None,
        knowledge_graph: Optional[Dict[str, Any]] = None
    ) -> List[Dict]:
        """
        批量异步决策（使用观点快照保证并发一致性）

        使用 asyncio.gather 并行调用 LLM，
        但受 LLMClient 内部的 Semaphore 限制并发数

        Args:
            llm_client: LLM 客户端
            response_released: 是否已发布权威回应
            cocoon_strength: 茧房强度
            progress_callback: 进度回调函数
            knowledge_graph: 知识图谱数据（事件结构化信息）

        Returns:
            所有 Agent 的决策结果
        """
        # === 关键修复：在决策前保存所有 Agent 的观点快照 ===
        # 这确保所有 Agent 感知到的是同一时刻的邻居状态
        opinion_snapshot = {}
        for agent in self.agents:
            opinion_snapshot[agent.id] = float(agent.opinion)
            opinion_snapshot[f"{agent.id}_is_silent"] = agent.is_silent

        # 使用计数器跟踪已完成的agent数量
        completed_count = 0
        completed_lock = asyncio.Lock()

        async def decide_one(agent: LLMAgent):
            nonlocal completed_count
            neighbor_agents = self.get_neighbor_agents(agent.id)
            result = await agent.decide_opinion(
                llm_client,
                neighbor_agents,
                response_released,
                cocoon_strength,
                opinion_snapshot,  # 传入快照
                knowledge_graph    # 传入知识图谱
            )
            # 原子递增完成计数
            async with completed_lock:
                completed_count += 1
                current_count = completed_count
            if progress_callback:
                # 传递实际完成数量：completed, total, agent_id, agent_opinion
                await progress_callback(current_count, self.size, agent.id, agent.opinion)
            return result

        tasks = [
            decide_one(agent)
            for agent in self.agents
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

    def apply_authoritative_response(self, effectiveness: float = 0.2):
        """
        应用权威回应效果（动态版本）

        Args:
            effectiveness: 基础权威回应效果系数（由引擎根据延迟和茧房强度计算）
        """
        self.exposed_to_positive[:] = True
        for agent in self.agents:
            agent.exposed_to_positive = True
            # 权威回应对持有负面信念的人有一定影响
            if agent.opinion < 0:
                # 动态计算：考虑信念强度和易感性
                impact = effectiveness * (1 - agent.belief_strength * 0.5) * (0.5 + agent.susceptibility * 0.5)
                agent.opinion = min(agent.opinion + impact, 1.0)

    # ==================== 兼容方法 ====================
    def apply_debunking(self, effectiveness: float = 0.2):
        """兼容旧方法名: apply_debunking -> apply_authoritative_response"""
        return self.apply_authoritative_response(effectiveness)

    @property
    def exposed_to_truth(self) -> np.ndarray:
        """兼容旧属性名: exposed_to_truth -> exposed_to_positive"""
        return self.exposed_to_positive

    @exposed_to_truth.setter
    def exposed_to_truth(self, value: np.ndarray):
        self.exposed_to_positive = value

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
        opinions = np.array([a.opinion for a in self.agents])
        belief_strengths = np.array([a.belief_strength for a in self.agents])
        # 三个互斥类别：拒绝/中立/相信
        reject_mask = opinions < -0.1
        uncertain_mask = np.abs(opinions) <= 0.1
        believe_mask = opinions > 0.1

        believe_rate = float(np.mean(believe_mask))
        reject_rate = float(np.mean(reject_mask))
        uncertain_rate = float(np.mean(uncertain_mask))

        return {
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
            "silence_rate": float(np.mean([a.is_silent for a in self.agents])),
            # 兼容旧字段名
            "negative_spread_rate": reject_rate,
            "positive_acceptance_rate": believe_rate,
            "negative_belief_rate": reject_rate,
            "positive_belief_rate": believe_rate,
            "deep_negative_rate": float(np.mean(reject_mask & (belief_strengths > 0.5))),
            "weighted_negative_index": float(
                np.mean(np.abs(np.minimum(opinions, 0)) * belief_strengths)
                if np.any(reject_mask) else 0.0
            ),
            "deep_positive_rate": float(np.mean(believe_mask & (belief_strengths > 0.5))),
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
    return get_agent_snapshot(agent_id)

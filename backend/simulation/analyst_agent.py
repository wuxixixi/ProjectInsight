"""
智库专报生成 Agent
AnalystAgent - 国家高端智库舆情分析专家
"""
import asyncio
import numpy as np
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import logging

from ..llm.client import LLMClient, LLMConfig, create_llm_config_from_env
from .report_utils import (
    credibility_rule_text,
    event_pool_summary,
    extract_sample_profile,
    format_count_distribution,
    response_effect_summary,
)

logger = logging.getLogger(__name__)


class DataSampler:
    """
    数据抽样器
    从推演历史中提取宏观数据和典型个体样本
    """
    _rng = np.random.default_rng(42)

    @staticmethod
    def extract_macro_data(engine) -> Dict[str, Any]:
        """
        提取宏观统计数据

        Args:
            engine: SimulationEngine 实例

        Returns:
            宏观数据字典
        """
        if not engine.history:
            return {}

        initial_state = engine.history[0]
        final_state = engine.history[-1]

        # 计算趋势（issue #1048: 使用get()提供fallback）
        rumor_trend = [h.get('negative_belief_rate', h.get('rumor_spread_rate', 0)) for h in engine.history]
        truth_trend = [h.get('positive_belief_rate', h.get('truth_acceptance_rate', 0)) for h in engine.history]
        believe_trend = [h.get('believe_rate', 0) for h in engine.history]
        reject_trend = [h.get('reject_rate', 0) for h in engine.history]
        opinion_trend = [h.get('avg_opinion', 0) for h in engine.history]
        polarization_trend = [h.get('polarization_index', 0) for h in engine.history]
        silence_trend = [h.get('silence_rate', 0) for h in engine.history]

        # 兼容单层/双层引擎的网络类型字段
        network_type = getattr(engine, "network_type", None)
        if network_type is None:
            if hasattr(engine, "num_communities"):
                network_type = f"dual_layer({getattr(engine, 'num_communities', 0)} communities)"
            else:
                network_type = "unknown"

        # 兼容新旧属性名
        debunk_delay = getattr(engine, 'response_delay', None) or getattr(engine, 'debunk_delay', 10)
        initial_rumor_spread = getattr(engine, 'initial_negative_spread', None) or getattr(engine, 'initial_rumor_spread', 0.3)

        # 提取事件信息
        news_content = getattr(engine, 'news_content', '')  # 最后一个事件（兼容）
        news_source = getattr(engine, 'news_source', 'public')
        knowledge_graph = getattr(engine, 'knowledge_graph', {})
        event_pool = getattr(engine, 'event_pool', [])

        # 构建所有事件的摘要文本
        events_summary = event_pool_summary(event_pool) if event_pool else (news_content if news_content else "未注入任何新闻事件")

        return {
            # 初始参数
            "parameters": {
                "population_size": engine.population_size,
                "cocoon_strength": engine.cocoon_strength,
                "debunk_delay": debunk_delay,
                "initial_rumor_spread": initial_rumor_spread,
                "network_type": network_type,
                "use_llm": engine.use_llm,
                "total_steps": len(engine.history) - 1,
                "response_credibility": getattr(engine, "response_credibility", getattr(engine, "debunk_credibility", 0.7)),
                "authority_factor": getattr(engine, "authority_factor", 0.5),
                "backfire_strength": getattr(engine, "backfire_strength", 0.3),
                "silence_threshold": getattr(engine, "silence_threshold", 0.3),
            },
            # 初始状态
            "initial_state": {
                "rumor_spread_rate": initial_state.get('mislead_rate', initial_state.get('rumor_spread_rate', initial_state.get('negative_belief_rate', 0))),
                "truth_acceptance_rate": initial_state.get('correct_rate', initial_state.get('truth_acceptance_rate', initial_state.get('positive_belief_rate', 0))),
                "believe_rate": initial_state.get('believe_rate', 0),
                "reject_rate": initial_state.get('reject_rate', 0),
                "news_credibility": initial_state.get('news_credibility', '不确定'),
                "deep_mislead_rate": initial_state.get('deep_negative_rate', 0),
                "deep_correct_rate": initial_state.get('deep_positive_rate', 0),
                "silence_rate": initial_state.get('silence_rate', 0),
                "avg_opinion": initial_state['avg_opinion'],
                "polarization_index": initial_state['polarization_index']
            },
            # 最终状态
            "final_state": {
                "rumor_spread_rate": final_state.get('mislead_rate', final_state.get('rumor_spread_rate', final_state.get('negative_belief_rate', 0))),
                "truth_acceptance_rate": final_state.get('correct_rate', final_state.get('truth_acceptance_rate', final_state.get('positive_belief_rate', 0))),
                "believe_rate": final_state.get('believe_rate', 0),
                "reject_rate": final_state.get('reject_rate', 0),
                "news_credibility": final_state.get('news_credibility', '不确定'),
                "deep_mislead_rate": final_state.get('deep_negative_rate', 0),
                "deep_correct_rate": final_state.get('deep_positive_rate', 0),
                "silence_rate": final_state.get('silence_rate', 0),
                "avg_rumor_trust": final_state.get("avg_rumor_trust", 0),
                "avg_truth_trust": final_state.get("avg_truth_trust", 0),
                "need_distribution": final_state.get("need_distribution") or {},
                "behavior_distribution": final_state.get("behavior_distribution") or {},
                "entity_impact_summary": final_state.get("entity_impact_summary") or {},
                "avg_opinion": final_state['avg_opinion'],
                "polarization_index": final_state['polarization_index']
            },
            # 变化趋势
            "trends": {
                "believe": {
                    "start": believe_trend[0] if believe_trend else 0,
                    "end": believe_trend[-1] if believe_trend else 0,
                    "max": max(believe_trend) if believe_trend else 0,
                    "min": min(believe_trend) if believe_trend else 0
                },
                "reject": {
                    "start": reject_trend[0] if reject_trend else 0,
                    "end": reject_trend[-1] if reject_trend else 0,
                    "max": max(reject_trend) if reject_trend else 0,
                    "min": min(reject_trend) if reject_trend else 0
                },
                "rumor_spread": {
                    "start": rumor_trend[0] if rumor_trend else 0,
                    "end": rumor_trend[-1] if rumor_trend else 0,
                    "max": max(rumor_trend) if rumor_trend else 0,
                    "min": min(rumor_trend) if rumor_trend else 0
                },
                "truth_acceptance": {
                    "start": truth_trend[0] if truth_trend else 0,
                    "end": truth_trend[-1] if truth_trend else 0,
                    "max": max(truth_trend) if truth_trend else 0
                },
                "avg_opinion": {
                    "start": opinion_trend[0] if opinion_trend else 0,
                    "end": opinion_trend[-1] if opinion_trend else 0
                },
                "polarization": {
                    "start": polarization_trend[0] if polarization_trend else 0,
                    "end": polarization_trend[-1] if polarization_trend else 0,
                    "max": max(polarization_trend) if polarization_trend else 0
                },
                "silence": {
                    "start": silence_trend[0] if silence_trend else 0,
                    "end": silence_trend[-1] if silence_trend else 0,
                    "max": max(silence_trend) if silence_trend else 0
                }
            },
            # 关键节点
            "response_released": engine.responded,
            "debunk_released": engine.responded,  # 兼容旧名
            "response_step": engine.response_delay,
            "debunk_step": engine.response_delay,  # 兼容旧名
            "response_effect": response_effect_summary(engine.history, engine.response_delay, engine.responded),
            # 事件信息
            "news_content": news_content,
            "news_source": news_source,
            "credibility_rule": credibility_rule_text(final_state.get('news_credibility', getattr(engine, 'news_credibility', '不确定'))),
            "knowledge_graph": knowledge_graph,
            "event_count": len(event_pool),
            "events_summary": events_summary,  # 所有事件的摘要文本
            "population_profile_id": getattr(engine, "population_profile_id", None) or "theory"
        }

    @staticmethod
    def _sample_payload(agent, snapshot: Dict[str, Any], old_op: float, new_op: float) -> Dict[str, Any]:
        realistic_profile = getattr(agent, "realistic_profile", None) or snapshot.get("realistic_profile") or {}
        return {
            "agent_id": agent.id,
            "name": realistic_profile.get("name", ""),
            "realistic_profile": realistic_profile,
            "persona": agent.persona,
            "persona_str": snapshot.get('persona_str', ''),
            "profile_label": extract_sample_profile({
                "agent_id": agent.id,
                "name": realistic_profile.get("name", ""),
                "realistic_profile": realistic_profile,
            }),
            "belief_strength": float(agent.belief_strength),
            "susceptibility": float(agent.susceptibility),
            "influence": float(agent.influence),
            "old_opinion": old_op,
            "new_opinion": new_op,
            "opinion_change": abs(new_op - old_op),
            "emotion": snapshot.get('emotion', ''),
            "action": snapshot.get('action', ''),
            "generated_comment": snapshot.get('generated_comment', ''),
            "reasoning": snapshot.get('reasoning', ''),
            "fear_of_isolation": float(getattr(agent, "fear_of_isolation", 0)),
            "is_silent": bool(getattr(agent, "is_silent", False)),
        }

    @classmethod
    def sample_agents(cls, population, n: int = 3, news_credibility: str = "不确定") -> Dict[str, List[Dict]]:
        """
        抽取典型 Agent 样本

        Args:
            population: LLMAgentPopulation 实例
            n: 每类样本数量
            news_credibility: 新闻可信度，用于判定"误信"方向

        Returns:
            {"converted": [...], "stubborn": [...]}
        """
        converted_agents = []  # 绿点: 从误信转向正确认知
        stubborn_agents = []   # 红点: 顽固坚持误信

        for agent in population.agents:
            if agent.last_decision_snapshot is None:
                continue

            snapshot = agent.last_decision_snapshot
            old_op = snapshot.get('old_opinion', 0)
            new_op = snapshot.get('new_opinion', 0)

            # 根据新闻可信度判定"误信"和"正确认知"的方向
            if news_credibility == "低可信":
                # 低可信新闻：相信(op>0)=误信，拒绝(op<0)=正确认知
                # 转化：从相信转向拒绝（op正→负或零）
                is_converted = old_op > 0 and new_op <= 0
                # 顽固：持续相信（op持续正）且信念坚定
                is_stubborn = old_op > 0 and new_op > 0 and agent.belief_strength > 0.5
            elif news_credibility == "高可信":
                # 高可信新闻：相信(op>0)=正确认知，拒绝(op<0)=误信
                # 转化：从拒绝转向相信（op负→正或零）
                is_converted = old_op < 0 and new_op >= 0
                # 顽固：持续拒绝（op持续负）且信念坚定
                is_stubborn = old_op < 0 and new_op < 0 and agent.belief_strength > 0.5
            else:
                # 不确定：无法明确判定误信/正确认知方向，
                # 使用观点变化幅度替代方向性判断（issue #861）
                is_converted = False
                is_stubborn = False

            # 转化样本
            if is_converted:
                converted_agents.append(cls._sample_payload(agent, snapshot, old_op, new_op))

            # 顽固坚持误信
            elif is_stubborn:
                stubborn_agents.append(cls._sample_payload(agent, snapshot, old_op, new_op))

        # 随机抽样（使用类级 RNG 确保可重现性）
        rng = cls._rng
        def safe_sample(lst, count):
            if len(lst) <= count:
                return lst
            indices = rng.choice(len(lst), size=count, replace=False)
            return [lst[i] for i in indices]

        return {
            "converted": safe_sample(converted_agents, n),
            "stubborn": safe_sample(stubborn_agents, n)
        }

    @staticmethod
    def sample_extreme_changes(population, n: int = 5) -> List[Dict]:
        """
        抽取观点变化最剧烈的样本，供 AnalystAgent 深度解剖

        根据用户需求，专门挑选出观点变化（|new_opinion - old_opinion|）最剧烈的
        N 个样本，这些样本代表了舆论演化中的"关键转折点"。

        Args:
            population: LLMAgentPopulation 实例
            n: 抽取样本数量，默认 5 个

        Returns:
            按观点变化幅度降序排列的样本列表
        """
        all_changes = []

        for agent in population.agents:
            if agent.last_decision_snapshot is None:
                continue

            snapshot = agent.last_decision_snapshot
            old_op = snapshot.get('old_opinion', 0)
            new_op = snapshot.get('new_opinion', 0)
            opinion_change = abs(new_op - old_op)

            # 记录完整信息
            payload = DataSampler._sample_payload(agent, snapshot, old_op, new_op)
            payload["change_direction"] = "positive" if new_op > old_op else ("negative" if new_op < old_op else "neutral")
            all_changes.append(payload)

        # 按观点变化幅度降序排序
        all_changes.sort(key=lambda x: x['opinion_change'], reverse=True)

        # 返回前 n 个最剧烈的变化
        return all_changes[:n]

    @classmethod
    def build_context(cls, engine, population, extreme_change_n: int = 5) -> Dict[str, Any]:
        """
        构建完整上下文

        Args:
            engine: SimulationEngine 实例
            population: LLMAgentPopulation 实例
            extreme_change_n: 极端观点变化样本数量，默认 5 个

        Returns:
            完整上下文字典
        """
        macro_data = cls.extract_macro_data(engine)
        news_credibility = getattr(engine, 'news_credibility', '不确定')
        agent_samples = cls.sample_agents(population, news_credibility=news_credibility)
        # 新增：观点变化最剧烈的样本
        extreme_samples = cls.sample_extreme_changes(population, extreme_change_n)

        return {
            "macro": macro_data,
            "agents": agent_samples,
            "extreme_changes": extreme_samples,  # 新增：极端变化样本
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }


# AnalystAgent System Prompt
ANALYST_SYSTEM_PROMPT = """你是一位上海社会科学院（国家高端智库）觉测团队的资深舆情分析专家，拥有丰富的网络舆论研究和危机应对经验。你的任务是针对信息茧房推演系统的模拟结果，撰写一份结构严谨、语气专业的内参报告。

你的专业背景:
- 深谙网络舆论传播规律，对算法推荐机制有深入研究
- 熟悉社交心理学和群体行为学理论
- 具备丰富的舆情危机应对和政策建议经验
- 文风严谨、客观，使用学术化、专业化的表述

核心要求 - 事件结合分析:
你收到的数据来源于一个具体的新闻事件推演。你必须：
1. 深入理解该新闻事件的核心矛盾、涉及主体和利益冲突
2. 将所有数据指标（误信率、极化指数等）与事件本身关联解读，而非泛泛而谈
3. 分析个体样本时，结合其人设特征和事件的具体内容，解释其反应的深层原因
4. 政策建议必须针对该事件暴露的具体问题，具有场景针对性

误信与正确认知的判定标准:
- opinion值表示对新闻内容的接受程度：opinion>0为相信新闻，opinion<0为拒绝新闻
- "误信"与"正确认知"需根据新闻可信度判定：
  - 若新闻可信度为"高可信"（真实新闻）：相信=正确认知，拒绝=误信（错过真相）
  - 若新闻可信度为"低可信"（虚假信息）：相信=误信（被误导），拒绝=正确认知（识破谣言）
  - 若新闻可信度为"不确定"：无法明确判定误信/正确认知，应保守分析

报告撰写要求:
1. 直接输出报告正文，不要使用代码块包裹
2. 使用 Markdown 标题格式（## 一、核心摘要 等）
3. 语言风格要正式、专业，避免口语化
4. 数据引用要准确，分析要有理有据
5. 政策建议要切实可行，具有操作性
6. 报告末尾注明：本分析基于上海社会科学院觉测团队【洞见】多智能体舆论认知干预沙盘仿真数据
7. 不得编造系统未提供的外部事实；如果事件材料不足，必须明确写成“依据当前注入材料判断”
"""

ANALYST_REPORT_TEMPLATE = """基于以下舆情推演数据，撰写专业智库专报。必须紧扣新闻事件本身进行分析。

## 事件信息
新闻内容：{news_content}
信息来源：{news_source_label}
事件摘要：{event_summary}
关键词：{event_keywords}
情感倾向：{event_sentiment}
可信度提示：{event_credibility}

## 关键语义说明
- 新闻可信度为"{event_credibility}"
- {credibility_rule}
- 若为"高可信"新闻：相信者=正确认知，拒绝者=误信
- 若为"低可信"新闻：相信者=误信（被误导），拒绝者=正确认知（识破谣言）
- opinion值含义：>0表示相信新闻，<0表示拒绝新闻

核心实体：
{event_entities}

实体关系：
{event_relations}

## 推演参数
{use_llm_mode}模式，{population_size}人，样本画像{population_profile_id}，茧房强度{cocoon_strength:.1f}，权威回应延迟{debunk_delay}步，回应可信度{response_credibility:.1f}，权威因子{authority_factor:.1f}，逆火强度{backfire_strength:.1f}

## 推演结果趋势
相信新闻比例 {initial_believe_rate:.0%}→{final_believe_rate:.0%}，拒绝新闻比例 {initial_reject_rate:.0%}→{final_reject_rate:.0%}
误信率 {initial_rumor_rate:.0%}→{final_rumor_rate:.0%}，正确认知率 {initial_truth_rate:.0%}→{final_truth_rate:.0%}
深度误信 {initial_deep_mislead_rate:.0%}→{final_deep_mislead_rate:.0%}，深度正确认知 {initial_deep_correct_rate:.0%}→{final_deep_correct_rate:.0%}
极化指数 {initial_polarization:.2f}→{final_polarization:.2f}，沉默率 {initial_silence_rate:.0%}→{final_silence_rate:.0%}
权威回应：{response_status}（第{debunk_delay}步介入）；回应效果：{response_effect}
趋势摘要：误信峰值{rumor_peak:.0%}，正确认知峰值{truth_peak:.0%}，极化峰值{polarization_peak:.2f}，沉默峰值{silence_peak:.0%}

## 行为与心理分布
需求分布：{need_distribution}
行为分布：{behavior_distribution}
平均负面信念信任度：{avg_rumor_trust:.2f}
平均正面信念信任度：{avg_truth_trust:.2f}

## 个体样本
转化样本（从误信转向正确认知）:
{converted_samples}

顽固样本（深度误信坚持）:
{stubborn_samples}

极端观点变化样本（关键转折点）:
{extreme_samples}

## 报告结构（共5节，每节150-250字）
一、事件背景与核心摘要 - 概述新闻事件的核心矛盾，提炼推演关键发现
二、舆情演化与风险研判 - 同时解释相信/拒绝、误信/正确认知、极化、沉默的变化
三、参数与机制分析 - 茧房强度、权威回应时机、逆火风险如何影响该事件舆论走向
四、关键个体深度剖析 - 结合事件内容和样本人设/现实画像，分析典型个体的认知转变或固化的心理机制
五、针对性政策建议 - 3条针对该事件类型的具体干预建议

请直接输出报告内容，使用中文撰写。必须紧密结合新闻事件本身进行分析，避免脱离事件语境的泛泛而谈。"""


class AnalystAgent:
    """
    智库分析专家 Agent

    基于 LLM 生成专业的舆情分析报告
    """

    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        temperature: float = 0.5,
        max_tokens: int = 2000,
        max_display_entities: int = 10,
        max_display_relations: int = 15
    ):
        if llm_config is None:
            llm_config = create_llm_config_from_env("REPORT_LLM")
        llm_config.timeout = llm_config.timeout or 120
        llm_config.max_tokens = max_tokens if llm_config.max_tokens == 150 else llm_config.max_tokens
        llm_config.temperature = temperature if llm_config.temperature == 0.7 else llm_config.temperature
        self.llm_config = llm_config
        self.llm_client: Optional[LLMClient] = None
        self.max_display_entities = max_display_entities
        self.max_display_relations = max_display_relations

    async def __aenter__(self):
        self.llm_client = LLMClient(self.llm_config)
        await self.llm_client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.llm_client:
            await self.llm_client.__aexit__(exc_type, exc_val, exc_tb)

    def _format_agent_samples(self, samples: List[Dict], label: str) -> str:
        """格式化 Agent 样本为可读文本"""
        if not samples:
            return f"（无{label}样本）"

        lines = []
        for i, s in enumerate(samples, 1):
            comment_part = f"，评论：「{s['generated_comment']}」" if s.get('generated_comment') else ""
            profile = s.get("profile_label") or extract_sample_profile(s)
            lines.append(
                f"样本{i}: {profile}，人设「{s['persona_str']}」，"
                f"信念{ s['belief_strength']:.0%}，易感{s['susceptibility']:.0%}，"
                f"影响力{s.get('influence', 0):.0%}，孤立恐惧{s.get('fear_of_isolation', 0):.0%}，"
                f"观点{ s['old_opinion']:.2f}→{s['new_opinion']:.2f}，"
                f"情绪「{s['emotion']}」，行动「{s['action']}」，是否沉默：{'是' if s.get('is_silent') else '否'}，"
                f"理由：{s['reasoning']}{comment_part}"
            )

        return "\n".join(lines)

    def _format_named_agent_samples(self, samples: List[Dict], label: str) -> str:
        if not samples:
            return f"（无{label}样本）"
        lines = []
        for i, s in enumerate(samples, 1):
            profile = s.get("profile_label") or extract_sample_profile(s)
            comment_part = f"，评论：「{s['generated_comment']}」" if s.get('generated_comment') else ""
            lines.append(
                f"{i}. {profile}，{s.get('persona_str', '未提供人设')}，"
                f"信念{s.get('belief_strength', 0):.0%}，易感{s.get('susceptibility', 0):.0%}，影响力{s.get('influence', 0):.0%}，"
                f"观点{s.get('old_opinion', 0):.2f}→{s.get('new_opinion', 0):.2f}，"
                f"情绪「{s.get('emotion', '')}」，行动「{s.get('action', '')}」，"
                f"理由：{s.get('reasoning', '')}{comment_part}"
            )
        return "\n".join(lines)

    def _format_extreme_samples(self, samples: List[Dict]) -> str:
        """
        格式化极端观点变化样本为可读文本

        这些样本代表舆论演化中的"关键转折点"
        """
        if not samples:
            return "（无极端变化样本）"

        lines = []
        for i, s in enumerate(samples, 1):
            direction = "观点上移（更接受新闻）" if s.get('change_direction') == 'positive' else (
                "观点下移（更拒绝新闻）" if s.get('change_direction') == 'negative' else "观点基本不变"
            )
            comment_part = f"，评论：「{s['generated_comment']}」" if s.get('generated_comment') else ""
            profile = s.get("profile_label") or extract_sample_profile(s)
            lines.append(
                f"转折点{i}: {profile}，人设「{s['persona_str']}」，"
                f"信念{s['belief_strength']:.0%}，易感{s['susceptibility']:.0%}，"
                f"影响力{s['influence']:.0%}，"
                f"观点变化{s['old_opinion']:.2f}→{s['new_opinion']:.2f}（变化{s['opinion_change']:.2f}，{direction}），"
                f"情绪「{s['emotion']}」，行动「{s['action']}」，"
                f"理由：{s['reasoning']}{comment_part}"
            )

        return "\n".join(lines)

    def _format_knowledge_graph(self, knowledge_graph: Dict) -> Dict[str, str]:
        """
        格式化知识图谱为可读文本

        Args:
            knowledge_graph: 知识图谱数据（包含entities, relations等）

        Returns:
            包含格式化文本的字典
        """
        if not knowledge_graph:
            return {
                "summary": "暂无事件摘要",
                "keywords": "暂无",
                "sentiment": "未知",
                "credibility": "未知",
                "entities": "暂无实体信息",
                "relations": "暂无关系信息"
            }

        # 摘要
        summary = knowledge_graph.get('summary', '暂无事件摘要')

        # 关键词
        keywords = knowledge_graph.get('keywords', [])
        keywords_str = "、".join(keywords) if keywords else "暂无"

        # 情感倾向
        sentiment = knowledge_graph.get('sentiment', '未知')

        # 可信度
        credibility = knowledge_graph.get('credibility_hint', '未知')

        # 实体列表（按重要度排序后截取，issue #862）
        entities = knowledge_graph.get('entities', [])
        if entities:
            # 按重要度降序排列，确保重要实体不被截断
            sorted_entities = sorted(entities, key=lambda e: e.get('importance', 3), reverse=True)
            entity_lines = []
            for e in sorted_entities[:self.max_display_entities]:
                name = e.get('name', '未知')
                etype = e.get('type', '未知')
                desc = e.get('description', '')
                importance = e.get('importance', 3)
                entity_lines.append(f"- {name}（{etype}，重要度{importance}/5）{desc}")
            entities_str = "\n".join(entity_lines)
        else:
            entities_str = "暂无实体信息"

        # 关系列表
        relations = knowledge_graph.get('relations', [])
        if relations:
            # issue #1049: 构建实体ID到名称的映射，避免O(n)线性扫描
            entity_map = {e.get('id'): e.get('name', e.get('id')) for e in entities}
            relation_lines = []
            for r in relations[:self.max_display_relations]:
                source = r.get('source', '')
                target = r.get('target', '')
                action = r.get('action', '关联')
                rtype = r.get('type', '')
                desc = r.get('description', '')
                # 使用映射查找名称
                source_name = entity_map.get(source, source)
                target_name = entity_map.get(target, target)
                relation_lines.append(f"- {source_name} → {action} → {target_name}（{rtype}）{desc}")
            relations_str = "\n".join(relation_lines)
        else:
            relations_str = "暂无关系信息"

        return {
            "summary": summary,
            "keywords": keywords_str,
            "sentiment": sentiment,
            "credibility": credibility,
            "entities": entities_str,
            "relations": relations_str
        }

    @staticmethod
    def _compress_context(text: str, limit: int = 1800) -> str:
        if not text:
            return ""
        if len(text) <= limit:
            return text
        return text[:limit] + "\n...（已截断，保留前文）"

    async def generate_report(self, context: Dict[str, Any]) -> str:
        """
        生成智库专报

        复用 generate_report_stream 的逻辑，收集所有片段后返回完整文本。

        Args:
            context: DataSampler.build_context() 返回的上下文

        Returns:
            Markdown 格式的报告文本
        """
        chunks = []
        async for chunk in self.generate_report_stream(context):
            chunks.append(chunk)
        return "".join(chunks)

    async def generate_report_stream(self, context: Dict[str, Any]):
        """
        流式生成智库专报

        Args:
            context: DataSampler.build_context() 返回的上下文

        Yields:
            str: 报告内容片段
        """
        if not self.llm_client:
            raise RuntimeError("请使用 async with 上下文管理器")

        # 格式化样本
        converted_samples = self._format_named_agent_samples(
            context['agents']['converted'],
            "被辟谣转化"
        )
        stubborn_samples = self._format_named_agent_samples(
            context['agents']['stubborn'],
            "顽固坚持误信"
        )
        # 格式化极端变化样本（新增）
        extreme_samples = self._format_extreme_samples(
            context.get('extreme_changes', [])
        )

        # 提取参数
        params = context['macro']['parameters']
        initial = context['macro']['initial_state']
        final = context['macro']['final_state']

        # 提取并格式化事件信息
        news_content = context['macro'].get('news_content', '未提供新闻事件内容')
        events_summary = context['macro'].get('events_summary', news_content)  # 所有事件摘要
        events_summary = self._compress_context(events_summary, 2200)
        news_source = context['macro'].get('news_source', 'public')
        news_source_label = "公共媒体（公域信息）" if news_source == "public" else "私密渠道（私域信息）"
        knowledge_graph = context['macro'].get('knowledge_graph', {})
        kg_formatted = self._format_knowledge_graph(knowledge_graph)

        # 权威回应状态
        response_released = context['macro'].get('response_released', False)
        response_status = "已发布" if response_released else "未发布"
        trends = context['macro'].get('trends', {})

        # 构建 Prompt
        user_prompt = ANALYST_REPORT_TEMPLATE.format(
            use_llm_mode="LLM驱动" if params['use_llm'] else "数学模型",
            population_size=params['population_size'],
            population_profile_id=context['macro'].get('population_profile_id', 'theory'),
            cocoon_strength=params['cocoon_strength'],
            debunk_delay=params['debunk_delay'],
            initial_rumor_spread=params['initial_rumor_spread'],
            network_type=params['network_type'],
            total_steps=params['total_steps'],
            response_credibility=params.get('response_credibility', 0.7),
            authority_factor=params.get('authority_factor', 0.5),
            backfire_strength=params.get('backfire_strength', 0.3),
            initial_believe_rate=initial.get('believe_rate', 0),
            final_believe_rate=final.get('believe_rate', 0),
            initial_reject_rate=initial.get('reject_rate', 0),
            final_reject_rate=final.get('reject_rate', 0),
            final_rumor_rate=final['rumor_spread_rate'],
            initial_rumor_rate=initial['rumor_spread_rate'],
            final_truth_rate=final['truth_acceptance_rate'],
            initial_truth_rate=initial['truth_acceptance_rate'],
            initial_deep_mislead_rate=initial.get('deep_mislead_rate', 0),
            final_deep_mislead_rate=final.get('deep_mislead_rate', 0),
            initial_deep_correct_rate=initial.get('deep_correct_rate', 0),
            final_deep_correct_rate=final.get('deep_correct_rate', 0),
            final_avg_opinion=final['avg_opinion'],
            initial_avg_opinion=initial['avg_opinion'],
            final_polarization=final['polarization_index'],
            initial_polarization=initial['polarization_index'],
            initial_silence_rate=initial.get('silence_rate', 0),
            final_silence_rate=final.get('silence_rate', 0),
            rumor_peak=trends.get('rumor_spread', {}).get('max', 0),
            truth_peak=trends.get('truth_acceptance', {}).get('max', 0),
            polarization_peak=trends.get('polarization', {}).get('max', 0),
            silence_peak=trends.get('silence', {}).get('max', 0),
            need_distribution=format_count_distribution(final.get('need_distribution')),
            behavior_distribution=format_count_distribution(final.get('behavior_distribution')),
            avg_rumor_trust=final.get('avg_rumor_trust', 0),
            avg_truth_trust=final.get('avg_truth_trust', 0),
            converted_samples=converted_samples,
            stubborn_samples=stubborn_samples,
            extreme_samples=extreme_samples,
            news_content=self._compress_context(news_content or events_summary, 1200),
            news_source_label=news_source_label,
            event_summary=self._compress_context(kg_formatted['summary'], 800),
            event_keywords=kg_formatted['keywords'],
            event_sentiment=kg_formatted['sentiment'],
            event_credibility=kg_formatted['credibility'],
            event_entities=self._compress_context(kg_formatted['entities'], 1200),
            event_relations=self._compress_context(kg_formatted['relations'], 1200),
            credibility_rule=context['macro'].get('credibility_rule', ''),
            response_effect=context['macro'].get('response_effect', ''),
            response_status=response_status
        )

        messages = [
            {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        try:
            # 先输出报告头部
            header = f"""# 信息茧房推演智库专报

> 生成时间: {context['generated_at']}
> 分析工具: AI分析师智能体

---

"""
            yield header

            # 流式调用 LLM
            async for chunk in self.llm_client.chat_stream(
                messages,
                temperature=self.llm_config.temperature
            ):
                yield chunk

        except Exception as e:
            logger.error(f"分析师 Agent 流式报告生成失败: {e}")
            raise


async def generate_intelligence_report(engine, population) -> str:
    """
    生成智库专报的便捷函数

    Args:
        engine: SimulationEngine 实例
        population: LLMAgentPopulation 实例

    Returns:
        Markdown 格式的报告文本
    """
    # 构建上下文
    context = DataSampler.build_context(engine, population)

    # 生成报告
    async with AnalystAgent(create_llm_config_from_env("REPORT_LLM")) as agent:
        report = await agent.generate_report(context)

    return report

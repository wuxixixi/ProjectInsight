"""
智库专报生成 Agent
AnalystAgent - 国家高端智库舆情分析专家
"""
import asyncio
import random
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from ..llm.client import LLMClient, LLMConfig

logger = logging.getLogger(__name__)


class DataSampler:
    """
    数据抽样器
    从推演历史中提取宏观数据和典型个体样本
    """

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

        # 计算趋势
        rumor_trend = [h['rumor_spread_rate'] for h in engine.history]
        truth_trend = [h['truth_acceptance_rate'] for h in engine.history]
        opinion_trend = [h['avg_opinion'] for h in engine.history]
        polarization_trend = [h['polarization_index'] for h in engine.history]

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
        if event_pool:
            events_summary = "\n".join([
                f"【事件{i+1}】Step {e.get('step', 0)} | 可信度: {e.get('credibility', '不确定')} | 内容: {e.get('content', '')[:100]}..."
                for i, e in enumerate(event_pool)
            ])
        else:
            events_summary = news_content if news_content else "未注入任何新闻事件"

        return {
            # 初始参数
            "parameters": {
                "population_size": engine.population_size,
                "cocoon_strength": engine.cocoon_strength,
                "debunk_delay": debunk_delay,
                "initial_rumor_spread": initial_rumor_spread,
                "network_type": network_type,
                "use_llm": engine.use_llm,
                "total_steps": len(engine.history) - 1
            },
            # 初始状态
            "initial_state": {
                "rumor_spread_rate": initial_state.get('mislead_rate', initial_state.get('rumor_spread_rate', initial_state.get('negative_belief_rate', 0))),
                "truth_acceptance_rate": initial_state.get('correct_rate', initial_state.get('truth_acceptance_rate', initial_state.get('positive_belief_rate', 0))),
                "believe_rate": initial_state.get('believe_rate', 0),
                "reject_rate": initial_state.get('reject_rate', 0),
                "news_credibility": initial_state.get('news_credibility', '不确定'),
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
                "avg_opinion": final_state['avg_opinion'],
                "polarization_index": final_state['polarization_index']
            },
            # 变化趋势
            "trends": {
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
                }
            },
            # 关键节点
            "response_released": engine.responded,
            "debunk_released": engine.responded,  # 兼容旧名
            "response_step": engine.response_delay,
            "debunk_step": engine.response_delay,  # 兼容旧名
            # 事件信息
            "news_content": news_content,
            "news_source": news_source,
            "knowledge_graph": knowledge_graph,
            "event_count": len(event_pool),
            "events_summary": events_summary  # 所有事件的摘要文本
        }

    @staticmethod
    def sample_agents(population, n: int = 3, news_credibility: str = "不确定") -> Dict[str, List[Dict]]:
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
                # 不确定：保守估计，保持原有逻辑
                is_converted = old_op < 0 and new_op >= 0
                is_stubborn = old_op < 0 and new_op < 0 and agent.belief_strength > 0.5

            # 转化样本
            if is_converted:
                converted_agents.append({
                    "agent_id": agent.id,
                    "persona": agent.persona,
                    "persona_str": snapshot.get('persona_str', ''),
                    "belief_strength": float(agent.belief_strength),
                    "susceptibility": float(agent.susceptibility),
                    "old_opinion": old_op,
                    "new_opinion": new_op,
                    "opinion_change": abs(new_op - old_op),
                    "emotion": snapshot.get('emotion', ''),
                    "action": snapshot.get('action', ''),
                    "generated_comment": snapshot.get('generated_comment', ''),
                    "reasoning": snapshot.get('reasoning', '')
                })

            # 顽固坚持误信
            elif is_stubborn:
                stubborn_agents.append({
                    "agent_id": agent.id,
                    "persona": agent.persona,
                    "persona_str": snapshot.get('persona_str', ''),
                    "belief_strength": float(agent.belief_strength),
                    "susceptibility": float(agent.susceptibility),
                    "old_opinion": old_op,
                    "new_opinion": new_op,
                    "opinion_change": abs(new_op - old_op),
                    "emotion": snapshot.get('emotion', ''),
                    "action": snapshot.get('action', ''),
                    "generated_comment": snapshot.get('generated_comment', ''),
                    "reasoning": snapshot.get('reasoning', '')
                })

        # 随机抽样
        def safe_sample(lst, count):
            if len(lst) <= count:
                return lst
            return random.sample(lst, count)

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
            all_changes.append({
                "agent_id": agent.id,
                "persona": agent.persona,
                "persona_str": snapshot.get('persona_str', ''),
                "belief_strength": float(agent.belief_strength),
                "susceptibility": float(agent.susceptibility),
                "influence": float(agent.influence),
                "old_opinion": old_op,
                "new_opinion": new_op,
                "opinion_change": opinion_change,
                "change_direction": "positive" if new_op > old_op else ("negative" if new_op < old_op else "neutral"),
                "emotion": snapshot.get('emotion', ''),
                "action": snapshot.get('action', ''),
                "generated_comment": snapshot.get('generated_comment', ''),
                "reasoning": snapshot.get('reasoning', ''),
                "fear_of_isolation": float(agent.fear_of_isolation),
                "is_silent": bool(agent.is_silent)
            })

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
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
- 若为"高可信"新闻：相信者=正确认知，拒绝者=误信
- 若为"低可信"新闻：相信者=误信（被误导），拒绝者=正确认知（识破谣言）
- opinion值含义：>0表示相信新闻，<0表示拒绝新闻

核心实体：
{event_entities}

实体关系：
{event_relations}

## 推演参数
{use_llm_mode}模式，{population_size}人，茧房强度{cocoon_strength:.1f}，权威回应延迟{debunk_delay}步

## 推演结果趋势
误信率 {initial_rumor_rate:.0%}→{final_rumor_rate:.0%}，正确认知率 {initial_truth_rate:.0%}→{final_truth_rate:.0%}
极化指数 {initial_polarization:.2f}→{final_polarization:.2f}
权威回应：{response_status}（第{debunk_delay}步介入）

## 个体样本
转化样本（从误信转向正确认知）:
{converted_samples}

顽固样本（深度误信坚持）:
{stubborn_samples}

极端观点变化样本（关键转折点）:
{extreme_samples}

## 报告结构（共5节，每节150-250字）
一、事件背景与核心摘要 - 概述新闻事件的核心矛盾，提炼推演关键发现
二、事件舆情演化分析 - 结合事件具体内容，分析误信传播路径和正确认知扩散过程
三、参数与机制分析 - 茧房强度、权威回应时机如何影响该事件舆论走向
四、关键个体深度剖析 - 结合事件内容和样本人设，分析典型个体的认知转变或固化的心理机制
五、针对性政策建议 - 3条针对该事件类型的具体干预建议

请直接输出报告内容，使用中文撰写。必须紧密结合新闻事件本身进行分析，避免脱离事件语境的泛泛而谈。"""


class AnalystAgent:
    """
    智库分析专家 Agent

    基于 LLM 生成专业的舆情分析报告
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        # 优化生成速度：减少token数量，降低温度
        if llm_config is None:
            llm_config = LLMConfig()
            llm_config.timeout = 120  # 2分钟超时
            llm_config.max_tokens = 2000  # 减少输出长度
            llm_config.temperature = 0.5  # 降低随机性加速生成
        self.llm_config = llm_config
        self.llm_client: Optional[LLMClient] = None

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
            lines.append(
                f"样本{i}: Agent #{s['agent_id']}，人设「{s['persona_str']}」，"
                f"信念{ s['belief_strength']:.0%}，易感{s['susceptibility']:.0%}，"
                f"观点{ s['old_opinion']:.2f}→{s['new_opinion']:.2f}，"
                f"情绪「{s['emotion']}」，行动「{s['action']}」，"
                f"理由：{s['reasoning']}{comment_part}"
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
            direction = "↑转向正确认知" if s.get('change_direction') == 'positive' else (
                "↓陷入误信" if s.get('change_direction') == 'negative' else "→维持不确定"
            )
            comment_part = f"，评论：「{s['generated_comment']}」" if s.get('generated_comment') else ""
            lines.append(
                f"转折点{i}: Agent #{s['agent_id']}，人设「{s['persona_str']}」，"
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

        # 实体列表
        entities = knowledge_graph.get('entities', [])
        if entities:
            entity_lines = []
            for e in entities[:10]:  # 最多显示10个
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
            relation_lines = []
            for r in relations[:15]:  # 最多显示15个
                source = r.get('source', '')
                target = r.get('target', '')
                action = r.get('action', '关联')
                rtype = r.get('type', '')
                desc = r.get('description', '')
                # 找到源和目标实体名称
                source_name = next((e['name'] for e in entities if e.get('id') == source), source)
                target_name = next((e['name'] for e in entities if e.get('id') == target), target)
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

    async def generate_report(self, context: Dict[str, Any]) -> str:
        """
        生成智库专报

        Args:
            context: DataSampler.build_context() 返回的上下文

        Returns:
            Markdown 格式的报告文本
        """
        if not self.llm_client:
            raise RuntimeError("请使用 async with 上下文管理器")

        # 格式化样本
        converted_samples = self._format_agent_samples(
            context['agents']['converted'],
            "被辟谣转化"
        )
        stubborn_samples = self._format_agent_samples(
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
        news_source = context['macro'].get('news_source', 'public')
        news_source_label = "公共媒体（公域信息）" if news_source == "public" else "私密渠道（私域信息）"
        knowledge_graph = context['macro'].get('knowledge_graph', {})
        kg_formatted = self._format_knowledge_graph(knowledge_graph)

        # 权威回应状态
        response_released = context['macro'].get('response_released', False)
        response_status = "已发布" if response_released else "未发布"

        # 构建 Prompt
        user_prompt = ANALYST_REPORT_TEMPLATE.format(
            use_llm_mode="LLM驱动" if params['use_llm'] else "数学模型",
            population_size=params['population_size'],
            cocoon_strength=params['cocoon_strength'],
            debunk_delay=params['debunk_delay'],
            initial_rumor_spread=params['initial_rumor_spread'],
            network_type=params['network_type'],
            total_steps=params['total_steps'],
            final_rumor_rate=final['rumor_spread_rate'],
            initial_rumor_rate=initial['rumor_spread_rate'],
            final_truth_rate=final['truth_acceptance_rate'],
            initial_truth_rate=initial['truth_acceptance_rate'],
            final_avg_opinion=final['avg_opinion'],
            initial_avg_opinion=initial['avg_opinion'],
            final_polarization=final['polarization_index'],
            initial_polarization=initial['polarization_index'],
            converted_samples=converted_samples,
            stubborn_samples=stubborn_samples,
            extreme_samples=extreme_samples,
            news_content=news_content,
            news_source_label=news_source_label,
            event_summary=kg_formatted['summary'],
            event_keywords=kg_formatted['keywords'],
            event_sentiment=kg_formatted['sentiment'],
            event_credibility=kg_formatted['credibility'],
            event_entities=kg_formatted['entities'],
            event_relations=kg_formatted['relations'],
            response_status=response_status
        )

        messages = [
            {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        try:
            # 调用 LLM，使用配置的温度参数加速生成
            response = await self.llm_client.chat(
                messages,
                temperature=self.llm_config.temperature
            )

            content = response["choices"][0]["message"]["content"]

            # 添加报告头部
            header = f"""# 信息茧房推演智库专报

> 生成时间: {context['generated_at']}
> 分析工具: AI分析师智能体

---

"""
            return header + content

        except Exception as e:
            logger.error(f"分析师 Agent 报告生成失败: {e}")
            raise

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
        converted_samples = self._format_agent_samples(
            context['agents']['converted'],
            "被辟谣转化"
        )
        stubborn_samples = self._format_agent_samples(
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
        news_source = context['macro'].get('news_source', 'public')
        news_source_label = "公共媒体（公域信息）" if news_source == "public" else "私密渠道（私域信息）"
        knowledge_graph = context['macro'].get('knowledge_graph', {})
        kg_formatted = self._format_knowledge_graph(knowledge_graph)

        # 权威回应状态
        response_released = context['macro'].get('response_released', False)
        response_status = "已发布" if response_released else "未发布"

        # 构建 Prompt
        user_prompt = ANALYST_REPORT_TEMPLATE.format(
            use_llm_mode="LLM驱动" if params['use_llm'] else "数学模型",
            population_size=params['population_size'],
            cocoon_strength=params['cocoon_strength'],
            debunk_delay=params['debunk_delay'],
            initial_rumor_spread=params['initial_rumor_spread'],
            network_type=params['network_type'],
            total_steps=params['total_steps'],
            final_rumor_rate=final['rumor_spread_rate'],
            initial_rumor_rate=initial['rumor_spread_rate'],
            final_truth_rate=final['truth_acceptance_rate'],
            initial_truth_rate=initial['truth_acceptance_rate'],
            final_avg_opinion=final['avg_opinion'],
            initial_avg_opinion=initial['avg_opinion'],
            final_polarization=final['polarization_index'],
            initial_polarization=initial['polarization_index'],
            converted_samples=converted_samples,
            stubborn_samples=stubborn_samples,
            extreme_samples=extreme_samples,
            news_content=news_content,
            news_source_label=news_source_label,
            event_summary=kg_formatted['summary'],
            event_keywords=kg_formatted['keywords'],
            event_sentiment=kg_formatted['sentiment'],
            event_credibility=kg_formatted['credibility'],
            event_entities=kg_formatted['entities'],
            event_relations=kg_formatted['relations'],
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
    async with AnalystAgent() as agent:
        report = await agent.generate_report(context)

    return report

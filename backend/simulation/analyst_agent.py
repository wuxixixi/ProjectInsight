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

        return {
            # 初始参数
            "parameters": {
                "population_size": engine.population_size,
                "cocoon_strength": engine.cocoon_strength,
                "debunk_delay": engine.debunk_delay,
                "initial_rumor_spread": engine.initial_rumor_spread,
                "network_type": engine.network_type,
                "use_llm": engine.use_llm,
                "total_steps": len(engine.history) - 1
            },
            # 初始状态
            "initial_state": {
                "rumor_spread_rate": initial_state['rumor_spread_rate'],
                "truth_acceptance_rate": initial_state['truth_acceptance_rate'],
                "avg_opinion": initial_state['avg_opinion'],
                "polarization_index": initial_state['polarization_index']
            },
            # 最终状态
            "final_state": {
                "rumor_spread_rate": final_state['rumor_spread_rate'],
                "truth_acceptance_rate": final_state['truth_acceptance_rate'],
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
            "debunk_released": engine.debunked,
            "debunk_step": engine.debunk_delay
        }

    @staticmethod
    def sample_agents(population, n: int = 3) -> Dict[str, List[Dict]]:
        """
        抽取典型 Agent 样本

        Args:
            population: LLMAgentPopulation 实例
            n: 每类样本数量

        Returns:
            {"converted": [...], "stubborn": [...]}
        """
        converted_agents = []  # 绿点: 被辟谣转化
        stubborn_agents = []   # 红点: 顽固坚持谣言

        for agent in population.agents:
            if agent.last_decision_snapshot is None:
                continue

            snapshot = agent.last_decision_snapshot
            old_op = snapshot.get('old_opinion', 0)
            new_op = snapshot.get('new_opinion', 0)

            # 被辟谣转化: 观点从负转正
            if old_op < -0.2 and new_op > 0:
                converted_agents.append({
                    "agent_id": agent.id,
                    "persona": agent.persona,
                    "persona_str": snapshot.get('persona_str', ''),
                    "belief_strength": float(agent.belief_strength),
                    "susceptibility": float(agent.susceptibility),
                    "old_opinion": old_op,
                    "new_opinion": new_op,
                    "emotion": snapshot.get('emotion', ''),
                    "action": snapshot.get('action', ''),
                    "generated_comment": snapshot.get('generated_comment', ''),
                    "reasoning": snapshot.get('reasoning', '')
                })

            # 顽固坚持: 观点持续为负
            elif old_op < -0.3 and new_op < -0.3:
                stubborn_agents.append({
                    "agent_id": agent.id,
                    "persona": agent.persona,
                    "persona_str": snapshot.get('persona_str', ''),
                    "belief_strength": float(agent.belief_strength),
                    "susceptibility": float(agent.susceptibility),
                    "old_opinion": old_op,
                    "new_opinion": new_op,
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

    @classmethod
    def build_context(cls, engine, population) -> Dict[str, Any]:
        """
        构建完整上下文

        Args:
            engine: SimulationEngine 实例
            population: LLMAgentPopulation 实例

        Returns:
            完整上下文字典
        """
        macro_data = cls.extract_macro_data(engine)
        agent_samples = cls.sample_agents(population)

        return {
            "macro": macro_data,
            "agents": agent_samples,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


# AnalystAgent System Prompt
ANALYST_SYSTEM_PROMPT = """你是一位上海社会科学院（国家高端智库）觉测团队的资深舆情分析专家，拥有丰富的网络舆论研究和危机应对经验。你的任务是针对信息茧房推演系统的模拟结果，撰写一份结构严谨、语气专业的内参报告。

你的专业背景:
- 深谙网络舆论传播规律，对算法推荐机制有深入研究
- 熟悉社交心理学和群体行为学理论
- 具备丰富的舆情危机应对和政策建议经验
- 文风严谨、客观，使用学术化、专业化的表述

报告撰写要求:
1. 直接输出报告正文，不要使用代码块包裹
2. 使用 Markdown 标题格式（## 一、核心摘要 等）
3. 语言风格要正式、专业，避免口语化
4. 数据引用要准确，分析要有理有据
5. 政策建议要切实可行，具有操作性
6. 报告末尾注明：本分析基于上海社会科学院觉测团队【洞见】多智能体舆论认知干预沙盘仿真数据
"""

ANALYST_REPORT_TEMPLATE = """基于以下舆情推演数据，撰写专业智库专报。

参数: {use_llm_mode}模式，{population_size}人，茧房强度{cocoon_strength:.1f}，辟谣延迟{debunk_delay}步
趋势: 谣言率 {initial_rumor_rate:.0%}→{final_rumor_rate:.0%}，真相率 {initial_truth_rate:.0%}→{final_truth_rate:.0%}
极化: {initial_polarization:.2f}→{final_polarization:.2f}

转化样本:
{converted_samples}

顽固样本:
{stubborn_samples}

报告结构（共4节，每节150-200字）:
一、核心摘要 - 关键发现与结论
二、参数影响分析 - 茧房强度、辟谣时机对舆论的影响
三、个体认知分析 - 分析上述样本的心理机制
四、政策建议 - 3条可行的干预建议

请直接输出报告内容，使用中文撰写。"""


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
            "顽固坚持谣言"
        )

        # 提取参数
        params = context['macro']['parameters']
        initial = context['macro']['initial_state']
        final = context['macro']['final_state']

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
            stubborn_samples=stubborn_samples
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
            "顽固坚持谣言"
        )

        # 提取参数
        params = context['macro']['parameters']
        initial = context['macro']['initial_state']
        final = context['macro']['final_state']

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
            stubborn_samples=stubborn_samples
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

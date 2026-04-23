"""
PersonAgent - LLM 驱动的智能体实现

基于 AgentSociety PersonAgent 模式:
- 三层记忆系统
- Skill Pipeline 懒加载
- 环境感知与交互
"""
import asyncio
import json
import logging
import random
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import AgentBase, AgentProfile
from .belief_state import BeliefState, ExposureEvent, ExposureSource
from .memory import AgentMemory
from ...llm.client import LLMClient, LLMConfig

logger = logging.getLogger(__name__)


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


# Agent 决策 Prompt 模板
PERSON_AGENT_PROMPT = """你是一个社交媒体用户，正在关注一个热点事件的讨论。

## 你的个人特征
- 当前观点: {opinion:.2f} (-1完全误信负面信息, 0中立, 1完全相信正确认知)
- 谣言信任度: {rumor_trust:.2f}
- 真相信任度: {truth_trust:.2f}
- 信念强度: {belief_strength:.2f} (越强越难改变观点)
- 易感性: {susceptibility:.2f} (越强越容易受他人影响)
- 孤立恐惧感: {fear_of_isolation:.2f} (越高越害怕被社交孤立)
- 人设类型: {persona_type} ({persona_desc})

## 观点变化限制规则（重要）
- 你的信念强度为 {belief_strength:.2f}，因此本轮观点最大变化幅度为 {max_change:.2f}
- 如果你选择沉默，观点变化幅度会进一步降低到 {max_change_silent:.2f}

## 你收到的信息
{info_section}

## 社交压力感知
- 邻居平均观点: {avg_peer_opinion:.2f}
- 与主流观点差异: {opinion_gap:.2f}
- 社交压力指数: {social_pressure:.2f}

## 最近记忆
{recent_memory}

## 任务
基于你的特征、收到的信息和社交压力，决定你的行为和观点变化。

请直接返回 JSON 格式（不要其他文字）:
{{
  "new_opinion": 数值在-1到1之间(注意变化幅度限制),
  "rumor_trust": 谣言信任度(-1到1),
  "truth_trust": 真相信任度(-1到1),
  "reasoning": "简短理由(20字内)",
  "emotion": "情绪状态(冷静/愤怒/焦虑/怀疑/释然)",
  "action": "行动选择(转发/评论/观望/权威回应/沉默)",
  "is_silent": boolean(是否选择沉默),
  "generated_comment": "如果选择评论，生成的评论内容(30字内)"
}}
"""


class PersonAgent(AgentBase):
    """
    LLM 驱动的智能体
    
    使用大模型进行决策，支持:
    - 细粒度信念状态
    - 三层记忆系统
    - Skill Pipeline (懒加载)
    """
    
    # 观点变化约束因子（issue #837: 参数化硬编码值）
    opinion_max_change_factor: float = 0.3
    # 社会影响系数（issue #838: 与 opinion_max_change_factor 分离）
    social_influence_coeff: float = 0.3

    def __init__(
        self,
        profile: AgentProfile,
        initial_belief: Optional[BeliefState] = None,
        llm_config: Optional[LLMConfig] = None,
        shared_llm_client: Optional[LLMClient] = None
    ):
        super().__init__(profile, initial_belief)

        # LLM 客户端（优先使用共享实例，避免资源浪费，issue #839）
        self.llm_config = llm_config or LLMConfig()
        self._llm_client = shared_llm_client
        self._owns_llm_client = shared_llm_client is None
    
    async def _get_llm_client(self) -> LLMClient:
        """获取 LLM 客户端（懒加载，仅在未共享时创建新实例）"""
        if self._llm_client is None:
            self._llm_client = LLMClient(self.llm_config)
        return self._llm_client
    
    async def step(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """LLM 驱动的推演步骤"""
        self.step_count = context.get("step", self.step_count + 1)

        # 执行技能管道
        observation = await self.observe(context)
        decision = await self.decide(observation)
        result = await self.act(decision)
        
        # Flush 认知缓冲
        self.memory.flush_cognition(self.step_count)
        
        return result
    
    async def observe(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """感知环境"""
        exposures = []
        
        # 算法推荐内容
        if "algorithm_content" in context:
            exposures.append(ExposureEvent(
                step=self.step_count,
                source=ExposureSource.ALGORITHM,
                content=context["algorithm_content"],
                alignment=context.get("algorithm_alignment", 0.0),
                credibility=context.get("algorithm_credibility", 0.5)
            ))
        
        # 社交影响
        peer_opinions = context.get("peer_opinions", [])
        for i, peer_op in enumerate(peer_opinions):
            if i < 3:  # 最多记录3个邻居
                exposures.append(ExposureEvent(
                    step=self.step_count,
                    source=ExposureSource.SOCIAL,
                    content=f"邻居{i+1}观点: {peer_op:.2f}",
                    alignment=peer_op,
                    sender_id=context.get("peer_ids", [])[i] if "peer_ids" in context else None
                ))
        
        # 官方辟谣
        if context.get("truth_content"):
            exposures.append(ExposureEvent(
                step=self.step_count,
                source=ExposureSource.TRUTH,
                content=context["truth_content"],
                alignment=1.0,
                credibility=context.get("truth_credibility", 0.7)
            ))
        
        # 注入事件
        if context.get("injected_event"):
            exposures.append(ExposureEvent(
                step=self.step_count,
                source=ExposureSource.INJECTED,
                content=context["injected_event"],
                alignment=context.get("injected_alignment", 0.0),
                credibility=context.get("injected_credibility", 0.5)
            ))
        
        # 添加到记忆
        for exposure in exposures:
            self.add_exposure(exposure)
        
        # 记录认知
        self.memory.add_cognition(
            skill_name="observation",
            step=self.step_count,
            input_data={"context_keys": list(context.keys())},
            output_data={"exposure_count": len(exposures)}
        )
        
        return {
            "exposures": exposures,
            "peer_opinions": peer_opinions,
            "social_pressure": self._compute_social_pressure(peer_opinions)
        }
    
    async def decide(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """LLM 决策"""
        try:
            # 构建 Prompt
            prompt = self._build_prompt(observation)
            
            # 调用 LLM
            client = await self._get_llm_client()
            async with client:
                response = await client.chat([{"role": "user", "content": prompt}])
            
            # 解析响应
            content = self._extract_content(response)
            decision = self._parse_decision(content)
            
            # 记录认知
            self.memory.add_cognition(
                skill_name="cognition",
                step=self.step_count,
                input_data={"prompt_length": len(prompt)},
                output_data=decision,
                reasoning=decision.get("reasoning")
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Agent {self.id} LLM 决策失败: {e}")
            # 回退到数学模型
            return await self._fallback_decision(observation)
    
    def _build_prompt(self, observation: Dict[str, Any]) -> str:
        """构建决策 Prompt"""
        # 获取上下文信息
        exposures = observation.get("exposures", [])
        peer_opinions = observation.get("peer_opinions", [])
        
        # 信息部分
        info_lines = []
        for exp in exposures[-5:]:  # 最近5条
            info_lines.append(f"- [{exp.source.value}] {exp.content}")
        info_section = "\n".join(info_lines) if info_lines else "无新信息"
        
        # 社交压力
        avg_peer = sum(peer_opinions) / len(peer_opinions) if peer_opinions else 0.0
        opinion_gap = abs(self.get_opinion() - avg_peer)
        social_pressure = observation.get("social_pressure", 0.0)
        
        # 最近记忆
        recent_memory = self._format_recent_memory()
        
        # 最大变化
        max_change = self.opinion_max_change_factor * (1 - self.belief_state.belief_strength)
        max_change_silent = max_change * 0.5

        return PERSON_AGENT_PROMPT.format(
            opinion=self.get_opinion(),
            rumor_trust=self.belief_state.rumor_trust,
            truth_trust=self.belief_state.truth_trust,
            belief_strength=self.belief_state.belief_strength,
            susceptibility=self.profile.susceptibility,
            fear_of_isolation=self.profile.fear_of_isolation,
            persona_type=self.profile.persona_type,
            persona_desc=self.profile.persona_desc,
            max_change=max_change,
            max_change_silent=max_change_silent,
            info_section=info_section,
            avg_peer_opinion=avg_peer,
            opinion_gap=opinion_gap,
            social_pressure=social_pressure,
            recent_memory=recent_memory
        )
    
    def _format_recent_memory(self) -> str:
        """格式化最近记忆"""
        recent = self.memory.get_recent_interactions(3)
        if not recent:
            return "暂无近期交互记录"
        
        lines = []
        for exp in recent:
            lines.append(f"- {exp.source.value}: {exp.content[:30]}...")
        return "\n".join(lines)
    
    def _extract_content(self, response: Any) -> str:
        """提取 LLM 响应内容"""
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "")
        return str(response)
    
    def _parse_decision(self, content: str) -> Dict[str, Any]:
        """解析 LLM 决策，复用 LLMClient._parse_json_content"""
        try:
            # 复用 LLMClient 的 JSON 解析方法
            temp_client = LLMClient()
            decision = temp_client._parse_json_content(content)

            # 检查解析是否成功（失败时返回 {"raw_content": ...}）
            if "raw_content" in decision and len(decision) == 1:
                logger.warning(f"Agent {self.id} LLM 响应解析失败: {content[:100]}")
                return {"new_opinion": self.get_opinion(), "is_silent": False}

            # 验证必要字段
            if "new_opinion" not in decision:
                decision["new_opinion"] = self.get_opinion()

            # 限制观点范围
            decision["new_opinion"] = max(-1.0, min(1.0, decision["new_opinion"]))

            # 应用变化限制
            max_change = self.opinion_max_change_factor * (1 - self.belief_state.belief_strength)
            delta = decision["new_opinion"] - self.get_opinion()
            if abs(delta) > max_change:
                decision["new_opinion"] = self.get_opinion() + (max_change if delta > 0 else -max_change)

            return decision

        except json.JSONDecodeError:
            logger.warning(f"Agent {self.id} LLM 响应解析失败: {content[:100]}")
            return {"new_opinion": self.get_opinion(), "is_silent": False}
    
    async def _fallback_decision(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """回退决策（数学模型）"""
        current = self.get_opinion()
        peer_opinions = observation.get("peer_opinions", [])
        
        # 简单的社交影响模型
        if peer_opinions:
            avg_peer = sum(peer_opinions) / len(peer_opinions)
            delta = (avg_peer - current) * self.profile.susceptibility * self.social_influence_coeff
            max_change = self.opinion_max_change_factor * (1 - self.belief_state.belief_strength)
            delta = max(-max_change, min(max_change, delta))
            new_opinion = current + delta
        else:
            new_opinion = current
        
        return {
            "new_opinion": new_opinion,
            "is_silent": False,
            "reasoning": "LLM 回退到数学模型",
            "action": "观望"
        }
    
    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """执行决策"""
        new_opinion = decision["new_opinion"]
        self.set_opinion(new_opinion)
        
        # 更新细粒度信念
        if "rumor_trust" in decision:
            self.belief_state.rumor_trust = max(-1, min(1, decision["rumor_trust"]))
        if "truth_trust" in decision:
            self.belief_state.truth_trust = max(-1, min(1, decision["truth_trust"]))
        
        self.is_silent = decision.get("is_silent", False)
        
        # 存储到记忆
        self.memory.store_belief(self.belief_state, self.step_count)
        
        return {
            "agent_id": self.id,
            "new_opinion": new_opinion,
            "rumor_trust": self.belief_state.rumor_trust,
            "truth_trust": self.belief_state.truth_trust,
            "is_silent": self.is_silent,
            "action": decision.get("action", "观望"),
            "reasoning": decision.get("reasoning"),
            "emotion": decision.get("emotion", "冷静")
        }
    
    def _compute_social_pressure(self, peer_opinions: List[float]) -> float:
        """计算社交压力"""
        if not peer_opinions:
            return 0.0
        
        current = self.get_opinion()
        avg_peer = sum(peer_opinions) / len(peer_opinions)
        
        # 观点差异 × 孤立恐惧
        pressure = abs(current - avg_peer) * self.profile.fear_of_isolation
        return min(1.0, pressure)
    
    def close(self):
        """关闭资源"""
        if self._owns_llm_client and self._llm_client is not None:
            self.memory.close()


def create_person_agent(
    agent_id: int,
    opinion: float,
    belief_strength: float,
    susceptibility: float,
    influence: float,
    fear_of_isolation: float,
    persona_type: str = None,
    llm_config: LLMConfig = None,
    shared_llm_client: Optional[LLMClient] = None,
    seed: Optional[int] = None
) -> PersonAgent:
    """
    工厂函数: 创建 PersonAgent

    兼容旧版参数接口
    """
    # 选择人设（issue #836: 使用确定性 RNG）
    rng = random.Random(seed if seed is not None else agent_id * 10007)
    if persona_type is None:
        if susceptibility > 0.5:
            pool = [PERSONA_TEMPLATES[0], PERSONA_TEMPLATES[2], PERSONA_TEMPLATES[3]]
        elif opinion < -0.3:
            pool = [PERSONA_TEMPLATES[4], PERSONA_TEMPLATES[6]]
        else:
            pool = PERSONA_TEMPLATES
        template = rng.choice(pool)
        persona_type = template["type"]
        persona_desc = template["desc"]
    else:
        persona_desc = next(
            (t["desc"] for t in PERSONA_TEMPLATES if t["type"] == persona_type),
            "普通用户"
        )
    
    # 创建 Profile
    profile = AgentProfile(
        agent_id=agent_id,
        persona_type=persona_type,
        persona_desc=persona_desc,
        susceptibility=susceptibility,
        influence=influence,
        fear_of_isolation=fear_of_isolation,
        cognitive_closed_need=rng.uniform(0.3, 0.7)
    )
    
    # 创建初始信念
    initial_belief = BeliefState.from_legacy_opinion(
        opinion=opinion,
        strength=belief_strength
    )
    
    return PersonAgent(
        profile=profile,
        initial_belief=initial_belief,
        llm_config=llm_config,
        shared_llm_client=shared_llm_client
    )

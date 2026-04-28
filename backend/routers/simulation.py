"""
推演相关路由
"""
import inspect
import logging
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import state
from ..helpers import (
    StartRequest, calculate_max_concurrent, _state_to_dict,
    _build_perceived_climate_summary, _normalize_snapshot_climate,
    _get_v3_agent_fields,
)
from ..simulation.engine import SimulationEngine
from ..simulation.engine_dual import SimulationEngineDual
from ..simulation.llm_agents import get_agent_snapshot_global
from ..simulation.llm_agents_dual import get_agent_snapshot_global as get_agent_snapshot_global_dual
from ..llm.client import LLMConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["simulation"])


async def _maybe_set_news(engine, content: str, source: str) -> None:
    """Support both sync and async engine.set_news implementations."""
    if not hasattr(engine, "set_news"):
        return
    result = engine.set_news(content, source, parse_graph=False)
    if inspect.isawaitable(result):
        await result


@router.post("/simulation/start")
async def start_simulation(params: StartRequest):
    """
    启动新的推演模拟
    如果有待注入的事件/知识图谱，会自动注入到引擎中
    返回初始状态
    """
    # 如果有待注入事件，根据事件内容设置初始分布
    if state.pending_knowledge_graph and state.pending_event_content:
        sentiment = state.pending_knowledge_graph.get("sentiment", "中性")
        credibility = state.pending_knowledge_graph.get("credibility_hint", "不确定")
        entity_count = len(state.pending_knowledge_graph.get('entities', []))
        logger.info(f"检测到待注入事件，情感={sentiment}, 可信度={credibility}, 实体数={entity_count}")

    # 自动计算并发数（如果未指定）
    max_concurrent = params.max_concurrent or calculate_max_concurrent(params.population_size)
    logger.info(f"LLM并发数设置: {max_concurrent} (Agent数量: {params.population_size})")

    # 使用环境变量中的LLM配置，仅覆盖并发数和超时参数
    llm_config = LLMConfig(
        max_concurrent=max_concurrent,
        timeout=params.timeout,
        max_retries=params.max_retries,
        connection_pool_size=params.connection_pool_size
    )

    # 参数兼容解析：新参数名优先，旧参数名兜底
    effective_initial_spread = params.initial_negative_spread if params.initial_negative_spread is not None else params.initial_rumor_spread
    effective_debunk_delay = params.response_delay if params.response_delay is not None else params.debunk_delay
    effective_credibility = params.response_credibility if params.response_credibility is not None else params.debunk_credibility

    # 根据是否启用双层网络选择引擎
    if params.use_dual_network:
        logger.info(f"使用双层网络引擎, 社群数: {params.num_communities}, LLM模式: {params.use_llm}")
        state.engine = SimulationEngineDual(
            population_size=params.population_size,
            cocoon_strength=params.cocoon_strength,
            debunk_delay=effective_debunk_delay,
            initial_rumor_spread=effective_initial_spread,
            use_llm=params.use_llm,
            llm_config=llm_config,
            num_communities=params.num_communities,
            public_m=params.public_m,
            # 增强版数学模型参数
            debunk_credibility=effective_credibility,
            authority_factor=params.authority_factor,
            backfire_strength=params.backfire_strength,
            silence_threshold=params.silence_threshold,
            polarization_factor=params.polarization_factor,
            echo_chamber_factor=params.echo_chamber_factor
        )
    else:
        state.engine = SimulationEngine(
            population_size=params.population_size,
            cocoon_strength=params.cocoon_strength,
            debunk_delay=effective_debunk_delay,
            initial_rumor_spread=effective_initial_spread,
            network_type=params.network_type,
            use_llm=params.use_llm,
            llm_config=llm_config,
            # 增强版数学模型参数
            debunk_credibility=effective_credibility,
            authority_factor=params.authority_factor,
            backfire_strength=params.backfire_strength,
            silence_threshold=params.silence_threshold,
            polarization_factor=params.polarization_factor,
            echo_chamber_factor=params.echo_chamber_factor,
            # Phase 3: 运行模式参数
            mode=params.mode,
            init_distribution=params.init_distribution,
            time_acceleration=params.time_acceleration
        )

    # 如果有待注入事件，根据事件内容设置初始分布
    if state.pending_knowledge_graph and state.pending_event_content:
        sentiment = state.pending_knowledge_graph.get("sentiment", "中性")
        credibility = state.pending_knowledge_graph.get("credibility_hint", "不确定")
        entity_count = len(state.pending_knowledge_graph.get('entities', []))
        if hasattr(state.engine, 'set_initial_distribution_from_news'):
            state.engine.set_initial_distribution_from_news(sentiment, credibility, entity_count)
            logger.info(f"已根据新闻内容设置初始分布")

    initial_state = state.engine.initialize()

    # ==================== 自动注入待处理的事件 ====================
    if state.pending_knowledge_graph and state.pending_event_content:
        logger.info(f"检测到待注入事件，自动注入到引擎: {state.pending_event_content[:50]}...")

        # === Phase 1: 设置知识图谱，启用知识驱动演化（初始化时不融合）===
        entities = state.pending_knowledge_graph.get('entities', [])
        relations = state.pending_knowledge_graph.get('relations', [])
        if entities and hasattr(state.engine, 'set_knowledge_graph'):
            state.engine.set_knowledge_graph(entities, relations, merge=False)
            logger.info(f"知识驱动演化已启用")

        # 如果引擎支持设置新闻
        await _maybe_set_news(
            state.engine,
            state.pending_event_content,
            state.pending_event_source or "public",
        )

        # 广播事件（触发事件冲击）
        target_scope = "all"
        if state.pending_event_source == "public":
            target_scope = "public_only"
        elif state.pending_event_source == "private":
            target_scope = "private_only"

        sentiment = state.pending_knowledge_graph.get("sentiment", "中性")
        credibility = state.pending_knowledge_graph.get("credibility_hint", "不确定")
        state.engine.broadcast_event(state.pending_event_content, target_scope, sentiment=sentiment, credibility=credibility)

        logger.info(f"待注入事件已成功注入，图谱包含 {len(state.pending_knowledge_graph.get('entities', []))} 个实体")

        # 清空待注入数据
        state.pending_knowledge_graph = None
        state.pending_event_content = None
        state.pending_event_source = None

    return JSONResponse(content=initial_state.to_dict())


@router.get("/simulation/step")
async def step_simulation():
    """执行单步推演并返回新状态 (仅数学模型模式)"""
    if state.engine is None:
        return JSONResponse(
            content={"error": "请先启动模拟"},
            status_code=400
        )

    if state.engine.use_llm:
        # LLM 模式需要通过 WebSocket
        return JSONResponse(
            content={"error": "LLM 模式请使用 WebSocket"},
            status_code=400
        )

    try:
        s = state.engine.step()
        return JSONResponse(content=s.to_dict())
    except Exception as e:
        logger.error(f"推演步骤错误: {e}")
        return JSONResponse(
            content={"error": f"推演步骤失败: {str(e)}"},
            status_code=500
        )


@router.get("/simulation/state")
async def get_state():
    """获取当前状态"""
    if state.engine is None:
        return JSONResponse(content={"error": "未初始化"}, status_code=400)

    state_dict = state.engine.current_state.to_dict()
    # 附加引擎级别数据（限制 event_pool 大小，issue #834）
    event_pool = getattr(state.engine, "event_pool", [])
    state_dict["event_pool"] = event_pool[-50:] if len(event_pool) > 50 else event_pool
    return JSONResponse(content=state_dict)


@router.get("/math-model/explanation")
async def get_math_model_explanation():
    """
    获取增强版数学模型的理论解释

    返回：
    - theories: 各社会心理学机制的理论说明
    - parameters: 各参数的含义和影响
    """
    from ..simulation.math_model_enhanced import EnhancedMathModel

    model = EnhancedMathModel()

    return JSONResponse(content={
        "theories": model.get_theory_explanation(),
        "parameters": model.get_parameter_explanation()
    })


@router.get("/agent/{agent_id}/inspect")
async def inspect_agent(agent_id: int):
    """
    微观行为透视接口
    获取指定Agent的决策上下文快照
    """
    engine = state.engine

    # 检查引擎是否初始化
    if engine is None:
        return JSONResponse(
            content={"error": "模拟未启动，请先开始推演", "has_decided": False},
            status_code=400
        )

    # 检查agent_id是否有效（优先使用实际Agent数量）
    if engine.use_llm and hasattr(engine, 'llm_population') and engine.llm_population:
        max_agents = len(engine.llm_population.agents)
    else:
        max_agents = engine.population_size

    if agent_id < 0 or agent_id >= max_agents:
        return JSONResponse(
            content={"error": f"无效的Agent ID: {agent_id}", "has_decided": False},
            status_code=404
        )

    # 优先从全局存储获取快照（同时检查单层和双层）
    snapshot = get_agent_snapshot_global(agent_id) or get_agent_snapshot_global_dual(agent_id)

    if snapshot:
        result = _normalize_snapshot_climate(snapshot)
        # 附加 v3.0 字段
        result.update(_get_v3_agent_fields(agent_id))
        return JSONResponse(content=result)

    # 如果全局存储没有，尝试从引擎获取（支持双层网络）
    if engine.use_llm and hasattr(engine, 'llm_population') and engine.llm_population:
        snapshot = engine.llm_population.get_agent_snapshot(agent_id)
        if snapshot:
            result = _normalize_snapshot_climate(snapshot)
            result.update(_get_v3_agent_fields(agent_id))
            return JSONResponse(content=result)

    # 获取基础Agent信息（未参与决策）
    if engine.use_llm and engine.llm_population:
        agent = engine.llm_population.agents[agent_id]
        return JSONResponse(content={
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
            "reasoning": "该Agent尚未参与本轮推演，处于初始状态",
            "has_decided": False,
            # 沉默的螺旋相关
            "fear_of_isolation": float(agent.fear_of_isolation),
            "conviction": float(agent.conviction),
            "is_silent": bool(agent.is_silent),
            "perceived_climate": _build_perceived_climate_summary(agent_id),
            # v3.0 字段
            **_get_v3_agent_fields(agent_id)
        })

    return JSONResponse(
        content={"error": "Agent信息不可用", "has_decided": False},
        status_code=500
    )


@router.post("/simulation/finish")
async def finish_simulation():
    """结束模拟并生成报告"""
    if state.engine is None:
        return JSONResponse(content={"error": "未初始化"}, status_code=400)

    try:
        report_path = state.engine.generate_report()
    except Exception as e:
        logger.error(f"报告生成失败: {e}")
        # issue #1156: 不重置引擎，允许重试
        return JSONResponse(
            content={"success": False, "error": f"报告生成失败: {e}"},
            status_code=500
        )

    # 使用正斜杠，避免JSON转义问题
    report_path_safe = report_path.replace("\\", "/") if report_path else None
    report_filename = os.path.basename(report_path) if report_path else None

    # 重置引擎状态，以便下次启动 (issue #2241: 先清理资源)
    if state.engine:
        state.engine.close()
    state.engine = None

    return JSONResponse(content={
        "success": True,
        "report_path": report_path_safe,
        "report_filename": report_filename
    })

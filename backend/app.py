"""
信息茧房推演系统 - 后端主入口
Ascend 环境运行提示:
  1. conda activate info-cocoon  # 激活环境
  2. uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
"""
import asyncio
import json
import logging
import os
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import state
from .helpers import calculate_max_concurrent, _state_to_dict
from .routers import simulation as sim_router
from .routers import report as report_router
from .routers import event as event_router
from .routers import prediction as pred_router
from .llm.client import LLMConfig
from .simulation.engine import SimulationEngine
from .simulation.engine_dual import SimulationEngineDual

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="信息茧房推演系统",
    description="模拟算法推荐与权威回应对群体观点的影响",
    version="3.0.0"
)

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(sim_router.router)
app.include_router(report_router.router)
app.include_router(event_router.router)
app.include_router(pred_router.router)


@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "service": "信息茧房推演系统", "version": "3.0.0"}


# ==================== WebSocket ====================

@app.websocket("/ws/simulation")
async def websocket_simulation(websocket: WebSocket):
    """
    WebSocket 实时推送推演过程

    协议:
    - 客户端 -> 服务端:
        {"action": "start", "params": {...}}
        {"action": "step"}
        {"action": "auto", "interval": 2000}  # 自动推演
        {"action": "stop"}
    - 服务端 -> 客户端:
        {"type": "state", "data": {...}}
        {"type": "progress", "step": 1, "total": 200, "message": "Agent 1/200"}
        {"type": "error", "message": "..."}
    """
    await websocket.accept()
    logger.info("WebSocket 连接已建立")

    auto_mode = False
    auto_task: Optional[asyncio.Task] = None
    max_steps = 50  # 默认值，会在start action中被更新

    async def send_progress(step: int, total: int, agent_id: int = None, agent_opinion: float = None):
        """发送进度更新"""
        try:
            # 构建进度消息
            progress_data = {
                "type": "progress",
                "step": step,
                "total": total,
                "percentage": round(step / total * 100, 1) if total > 0 else 0,
                "current_step": state.engine.step_count if state.engine else 0,
                "max_steps": max_steps
            }

            # 添加 Agent 详细信息
            if agent_id is not None:
                progress_data["agent_id"] = agent_id
                progress_data["agent_opinion"] = round(agent_opinion, 2) if agent_opinion is not None else 0

                # 根据观点值判断立场
                if agent_opinion is not None:
                    if agent_opinion < -0.3:
                        stance = "误信"
                    elif agent_opinion > 0.3:
                        stance = "正确认知"
                    else:
                        stance = "中立"
                    progress_data["agent_stance"] = stance

            progress_data["message"] = f"正在推演 Agent {step}/{total}" + (f" (ID:{agent_id})" if agent_id is not None else "")

            await websocket.send_json(progress_data)
        except Exception as e:
            logger.debug(f"发送进度失败: {e}")

    async def auto_step_loop(interval: int):
        """自动推演循环"""
        nonlocal max_steps
        while auto_mode and state.engine and state.engine.step_count < max_steps:
            try:
                # 如果事件注入正在进行，等待注入完成
                if state.injection_in_progress:
                    logger.debug("事件注入进行中，推演等待...")
                    await websocket.send_json({
                        "type": "progress",
                        "message": "事件注入解析中，推演暂停等待..."
                    })
                    # 等待注入完成（最多等待60秒）
                    for _ in range(60):
                        if not state.injection_in_progress:
                            break
                        await asyncio.sleep(1)
                    if state.injection_in_progress:
                        logger.warning("事件注入超时，恢复推演")
                    else:
                        logger.info("事件注入完成，恢复推演")
                        await websocket.send_json({
                            "type": "progress",
                            "message": "事件注入完成，恢复推演"
                        })

                s = await state.engine.async_step()
                await websocket.send_json({
                    "type": "state",
                    "data": _state_to_dict(s)
                })
                await asyncio.sleep(interval / 1000)
            except asyncio.CancelledError:
                logger.info("自动推演任务已取消")
                break
            except Exception as e:
                logger.error(f"自动推演错误: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                break

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            action = msg.get("action")

            if action == "start":
                # 启动新模拟
                params = msg.get("params", {})
                use_llm = params.get("use_llm", True)
                population_size = params.get("population_size", 200)
                use_dual_network = params.get("use_dual_network", True)
                max_steps = params.get("max_steps", 50)  # 从前端获取最大步数

                # 自动计算并发数（如果未指定）
                max_concurrent = params.get("max_concurrent")
                if max_concurrent is None:
                    max_concurrent = calculate_max_concurrent(population_size)
                logger.info(f"LLM并发数设置: {max_concurrent} (Agent数量: {population_size})")

                # 从前端获取LLM并发参数
                # 使用环境变量中的LLM配置，仅覆盖并发数和超时参数
                llm_config = LLMConfig(
                    max_concurrent=max_concurrent,
                    timeout=params.get("timeout", 60),
                    max_retries=params.get("max_retries", 5),
                    connection_pool_size=params.get("connection_pool_size", 600)
                )

                # 参数兼容解析：新参数名优先，旧参数名兜底
                effective_initial_spread = params.get("initial_negative_spread", params.get("initial_rumor_spread", 0.3))
                effective_debunk_delay = params.get("response_delay", params.get("debunk_delay", 10))
                effective_credibility = params.get("response_credibility", params.get("debunk_credibility", 0.7))

                # 根据是否启用双层网络选择引擎
                if use_dual_network:
                    logger.info(f"使用双层网络引擎, 社群数: {params.get('num_communities', 8)}, LLM模式: {use_llm}")
                    state.engine = SimulationEngineDual(
                        population_size=population_size,
                        cocoon_strength=params.get("cocoon_strength", 0.5),
                        debunk_delay=effective_debunk_delay,
                        initial_rumor_spread=effective_initial_spread,
                        use_llm=use_llm,
                        llm_config=llm_config,
                        num_communities=params.get("num_communities", 8),
                        public_m=params.get("public_m", 3),
                        # 增强版数学模型参数
                        debunk_credibility=effective_credibility,
                        authority_factor=params.get("authority_factor", 0.5),
                        backfire_strength=params.get("backfire_strength", 0.3),
                        silence_threshold=params.get("silence_threshold", 0.3),
                        polarization_factor=params.get("polarization_factor", 0.3),
                        echo_chamber_factor=params.get("echo_chamber_factor", 0.2)
                    )
                else:
                    state.engine = SimulationEngine(
                        population_size=population_size,
                        cocoon_strength=params.get("cocoon_strength", 0.5),
                        debunk_delay=effective_debunk_delay,
                        initial_rumor_spread=effective_initial_spread,
                        network_type=params.get("network_type", "small_world"),
                        use_llm=use_llm,
                        llm_config=llm_config,
                        # 增强版数学模型参数
                        debunk_credibility=effective_credibility,
                        authority_factor=params.get("authority_factor", 0.5),
                        backfire_strength=params.get("backfire_strength", 0.3),
                        silence_threshold=params.get("silence_threshold", 0.3),
                        polarization_factor=params.get("polarization_factor", 0.3),
                        echo_chamber_factor=params.get("echo_chamber_factor", 0.2)
                    )

                # 设置进度回调
                state.engine.set_progress_callback(send_progress)

                initial_state = state.engine.initialize()
                await websocket.send_json({
                    "type": "state",
                    "data": _state_to_dict(initial_state)
                })
                logger.info(f"模拟已启动, LLM模式: {use_llm}, 双层网络: {use_dual_network}")

            elif action == "step":
                # 单步推演
                if state.engine is None:
                    await websocket.send_json({
                        "type": "error",
                        "message": "请先启动模拟"
                    })
                    continue

                try:
                    s = await state.engine.async_step()
                    await websocket.send_json({
                        "type": "state",
                        "data": _state_to_dict(s)
                    })
                except Exception as e:
                    logger.error(f"推演错误: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })

            elif action == "auto":
                # 自动推演
                if state.engine is None:
                    await websocket.send_json({
                        "type": "error",
                        "message": "请先启动模拟"
                    })
                    continue

                interval = msg.get("interval", 2000)
                auto_mode = True
                auto_task = asyncio.create_task(auto_step_loop(interval))
                logger.info(f"自动推演已启动, 间隔 {interval}ms")

            elif action == "pause":
                # 暂停自动推演（保留引擎状态，可恢复）
                auto_mode = False
                if auto_task:
                    auto_task.cancel()
                    auto_task = None
                logger.info("自动推演已暂停")

            elif action == "resume":
                # 恢复自动推演
                if state.engine is None:
                    await websocket.send_json({
                        "type": "error",
                        "message": "请先启动模拟"
                    })
                    continue
                if state.engine.step_count >= max_steps:
                    await websocket.send_json({
                        "type": "error",
                        "message": "推演已完成，无法恢复"
                    })
                    continue
                interval = msg.get("interval", 2000)
                auto_mode = True
                auto_task = asyncio.create_task(auto_step_loop(interval))
                logger.info(f"自动推演已恢复, 间隔 {interval}ms")

            elif action == "stop":
                # 停止自动推演（终止推演）
                auto_mode = False
                if auto_task:
                    auto_task.cancel()
                    auto_task = None
                logger.info("自动推演已停止")

            elif action == "finish":
                # 生成报告
                if state.engine is None:
                    await websocket.send_json({
                        "type": "error",
                        "message": "请先启动模拟"
                    })
                    continue

                report_path = state.engine.generate_report()
                report_path_safe = report_path.replace("\\", "/") if report_path else None
                await websocket.send_json({
                    "type": "report",
                    "data": {
                        "success": True,
                        "report_path": report_path_safe,
                        "report_filename": os.path.basename(report_path) if report_path else None
                    }
                })

    except WebSocketDisconnect:
        logger.info("WebSocket 断开")
        auto_mode = False
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")

"""
信息茧房推演系统 - 后端主入口
Ascend 环境运行提示:
  1. conda activate info-cocoon  # 激活环境
  2. uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import json
import os
import subprocess
import platform
import logging

from .simulation.engine import SimulationEngine
from .simulation.agents import AgentPopulation
from .simulation.llm_agents import get_agent_snapshot_global
from .models.schemas import SimulationParams, SimulationState
from .llm.client import LLMConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="信息茧房推演系统",
    description="模拟算法推荐与官方辟谣对群体观点的影响",
    version="2.0.0"
)

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局模拟引擎实例
engine: Optional[SimulationEngine] = None


class StartRequest(BaseModel):
    """推演启动请求参数"""
    # 基础参数
    cocoon_strength: float = 0.5
    debunk_delay: int = 10
    population_size: int = 200
    initial_rumor_spread: float = 0.3
    network_type: str = "small_world"
    use_llm: bool = True

    # LLM并发参数
    max_concurrent: int = 400
    connection_pool_size: int = 600
    timeout: int = 60
    max_retries: int = 5


@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "service": "信息茧房推演系统", "version": "2.0.0"}


@app.post("/api/simulation/start")
async def start_simulation(params: StartRequest):
    """
    启动新的推演模拟
    返回初始状态
    """
    global engine

    # 从请求参数获取LLM配置
    llm_config = LLMConfig(
        base_url="http://10.17.2.29:31277/v1",
        api_key="R61XwviRggmoTdDGHmH3tA0BQN7TToYwdPk61m9Y8Gs",
        model="DeepSeek-V3",
        max_concurrent=params.max_concurrent,
        timeout=params.timeout,
        max_retries=params.max_retries,
        connection_pool_size=params.connection_pool_size
    )

    engine = SimulationEngine(
        population_size=params.population_size,
        cocoon_strength=params.cocoon_strength,
        debunk_delay=params.debunk_delay,
        initial_rumor_spread=params.initial_rumor_spread,
        network_type=params.network_type,
        use_llm=params.use_llm,
        llm_config=llm_config
    )

    initial_state = engine.initialize()
    return JSONResponse(content=initial_state.to_dict())


@app.get("/api/simulation/step")
async def step_simulation():
    """执行单步推演并返回新状态 (仅数学模型模式)"""
    global engine
    if engine is None:
        return JSONResponse(
            content={"error": "请先启动模拟"},
            status_code=400
        )

    if engine.use_llm:
        # LLM 模式需要通过 WebSocket
        return JSONResponse(
            content={"error": "LLM 模式请使用 WebSocket"},
            status_code=400
        )

    state = engine.step()
    return JSONResponse(content=state.to_dict())


@app.get("/api/simulation/state")
async def get_state():
    """获取当前状态"""
    global engine
    if engine is None:
        return JSONResponse(content={"error": "未初始化"}, status_code=400)

    return JSONResponse(content=engine.current_state.to_dict())


@app.get("/api/agent/{agent_id}/inspect")
async def inspect_agent(agent_id: int):
    """
    微观行为透视接口
    获取指定Agent的决策上下文快照
    """
    global engine

    # 检查引擎是否初始化
    if engine is None:
        return JSONResponse(
            content={"error": "模拟未启动，请先开始推演", "has_decided": False},
            status_code=400
        )

    # 检查agent_id是否有效
    if agent_id < 0 or agent_id >= engine.population_size:
        return JSONResponse(
            content={"error": f"无效的Agent ID: {agent_id}", "has_decided": False},
            status_code=404
        )

    # 优先从全局存储获取快照
    snapshot = get_agent_snapshot_global(agent_id)

    if snapshot:
        return JSONResponse(content=snapshot)

    # 如果全局存储没有，尝试从引擎获取
    if engine.use_llm and engine.llm_population:
        snapshot = engine.llm_population.get_agent_snapshot(agent_id)
        if snapshot:
            return JSONResponse(content=snapshot)

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
            "has_decided": False
        })

    return JSONResponse(
        content={"error": "Agent信息不可用", "has_decided": False},
        status_code=500
    )


@app.post("/api/simulation/finish")
async def finish_simulation():
    """结束模拟并生成报告"""
    global engine
    if engine is None:
        return JSONResponse(content={"error": "未初始化"}, status_code=400)

    report_path = engine.generate_report()
    # 使用正斜杠，避免JSON转义问题
    report_path_safe = report_path.replace("\\", "/") if report_path else None
    report_filename = report_path.split("\\")[-1] if report_path else None

    return JSONResponse(content={
        "success": True,
        "report_path": report_path_safe,
        "report_filename": report_filename
    })


@app.post("/api/report/open")
async def open_report(data: dict):
    """使用系统默认应用打开报告文件"""
    report_path = data.get("path", "").replace("/", os.sep).replace("\\", os.sep)

    if not report_path or not os.path.exists(report_path):
        return JSONResponse(content={"success": False, "error": f"报告文件不存在: {report_path}"}, status_code=404)

    try:
        system = platform.system()
        if system == "Windows":
            subprocess.run(["cmd", "/c", "start", "", report_path], check=True)
        elif system == "Darwin":
            subprocess.run(["open", report_path], check=True)
        else:
            subprocess.run(["xdg-open", report_path], check=True)

        return JSONResponse(content={"success": True, "message": "已打开报告"})
    except Exception as e:
        logger.error(f"打开报告失败: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.get("/api/report/content")
async def get_report_content(filename: str):
    """获取报告内容"""
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    reports_dir = os.path.abspath(reports_dir)
    report_path = os.path.join(reports_dir, filename)

    if not os.path.exists(report_path):
        return JSONResponse(content={"error": f"报告不存在: {filename}"}, status_code=404)

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        return JSONResponse(content={"success": True, "content": content, "filename": filename})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/report/download")
async def download_report(filename: str):
    """下载报告文件"""
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    reports_dir = os.path.abspath(reports_dir)
    report_path = os.path.join(reports_dir, filename)

    if not os.path.exists(report_path):
        return JSONResponse(content={"error": "报告不存在"}, status_code=404)

    return FileResponse(
        path=report_path,
        filename=filename,
        media_type="text/markdown"
    )


@app.get("/api/report/list")
async def list_reports():
    """列出所有报告文件"""
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    reports_dir = os.path.abspath(reports_dir)

    if not os.path.exists(reports_dir):
        return JSONResponse(content={"reports": []})

    reports = []
    for f in sorted(os.listdir(reports_dir), reverse=True):
        if f.endswith(".md"):
            filepath = os.path.join(reports_dir, f)
            stat = os.stat(filepath)
            reports.append({
                "filename": f,
                "path": filepath,
                "size": stat.st_size,
                "modified": stat.st_mtime
            })

    return JSONResponse(content={"reports": reports})


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
    global engine
    await websocket.accept()
    logger.info("WebSocket 连接已建立")

    auto_mode = False
    auto_task: Optional[asyncio.Task] = None

    async def send_progress(step: int, total: int):
        """发送进度更新"""
        try:
            await websocket.send_json({
                "type": "progress",
                "step": step,
                "total": total,
                "message": f"Agent {step}/{total}"
            })
        except:
            pass

    async def auto_step_loop(interval: int):
        """自动推演循环"""
        global engine
        max_steps = 50
        while auto_mode and engine and engine.step_count < max_steps:
            try:
                state = await engine.async_step()
                await websocket.send_json({
                    "type": "state",
                    "data": state.to_dict()
                })
                await asyncio.sleep(interval / 1000)
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

                # 从前端获取LLM并发参数
                llm_config = LLMConfig(
                    base_url="http://10.17.2.29:31277/v1",
                    api_key="R61XwviRggmoTdDGHmH3tA0BQN7TToYwdPk61m9Y8Gs",
                    model="DeepSeek-V3",
                    max_concurrent=params.get("max_concurrent", 400),
                    timeout=params.get("timeout", 60),
                    max_retries=params.get("max_retries", 5),
                    connection_pool_size=params.get("connection_pool_size", 600)
                )

                engine = SimulationEngine(
                    population_size=params.get("population_size", 200),
                    cocoon_strength=params.get("cocoon_strength", 0.5),
                    debunk_delay=params.get("debunk_delay", 10),
                    initial_rumor_spread=params.get("initial_rumor_spread", 0.3),
                    network_type=params.get("network_type", "small_world"),
                    use_llm=use_llm,
                    llm_config=llm_config
                )

                # 设置进度回调
                engine.set_progress_callback(send_progress)

                initial_state = engine.initialize()
                await websocket.send_json({
                    "type": "state",
                    "data": initial_state.to_dict()
                })
                logger.info(f"模拟已启动, LLM模式: {use_llm}")

            elif action == "step":
                # 单步推演
                if engine is None:
                    await websocket.send_json({
                        "type": "error",
                        "message": "请先启动模拟"
                    })
                    continue

                try:
                    state = await engine.async_step()
                    await websocket.send_json({
                        "type": "state",
                        "data": state.to_dict()
                    })
                except Exception as e:
                    logger.error(f"推演错误: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })

            elif action == "auto":
                # 自动推演
                if engine is None:
                    await websocket.send_json({
                        "type": "error",
                        "message": "请先启动模拟"
                    })
                    continue

                interval = msg.get("interval", 2000)
                auto_mode = True
                auto_task = asyncio.create_task(auto_step_loop(interval))
                logger.info(f"自动推演已启动, 间隔 {interval}ms")

            elif action == "stop":
                # 停止自动推演
                auto_mode = False
                if auto_task:
                    auto_task.cancel()
                    auto_task = None
                logger.info("自动推演已停止")

            elif action == "finish":
                # 生成报告
                if engine is None:
                    await websocket.send_json({
                        "type": "error",
                        "message": "请先启动模拟"
                    })
                    continue

                report_path = engine.generate_report()
                await websocket.send_json({
                    "type": "report",
                    "data": {
                        "success": True,
                        "report_path": report_path,
                        "report_filename": report_path.split("\\")[-1] if report_path else None
                    }
                })

    except WebSocketDisconnect:
        logger.info("WebSocket 断开")
        auto_mode = False
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")

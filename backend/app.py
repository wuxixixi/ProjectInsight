"""
信息茧房推演系统 - 后端主入口
Ascend 环境运行提示:
  1. conda activate info-cocoon  # 激活环境
  2. uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import json
import os
import subprocess
import platform
import logging

from .simulation.engine import SimulationEngine
from .simulation.engine_dual import SimulationEngineDual
from .simulation.agents import AgentPopulation
from .simulation.llm_agents import get_agent_snapshot_global
from .simulation.llm_agents_dual import get_agent_snapshot_global as get_agent_snapshot_global_dual
from .simulation.analyst_agent import generate_intelligence_report, AnalystAgent, DataSampler
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

# 待注入的事件/知识图谱（推演开始前可预先准备）
pending_knowledge_graph: Optional[dict] = None
pending_event_content: Optional[str] = None
pending_event_source: Optional[str] = None


class StartRequest(BaseModel):
    """推演启动请求参数"""
    # 基础参数
    cocoon_strength: float = 0.5
    debunk_delay: int = 10
    population_size: int = 200
    initial_rumor_spread: float = 0.3
    network_type: str = "small_world"
    use_llm: bool = True

    # LLM并发参数（留空则自动计算）
    max_concurrent: Optional[int] = None  # None 表示根据 population_size 自动计算
    connection_pool_size: int = 600
    timeout: int = 60
    max_retries: int = 5

    # 双层网络参数
    use_dual_network: bool = True     # 是否使用双层网络模式
    num_communities: int = 8          # 私域社群数量
    public_m: int = 3                 # 公域网络 BA 模型参数

    # 增强版数学模型参数
    debunk_credibility: float = 0.7      # 辟谣来源可信度 [0, 1]
    authority_factor: float = 0.5        # 权威影响力系数 [0, 1]
    backfire_strength: float = 0.3       # 逆火效应强度 [0, 1]
    silence_threshold: float = 0.3       # 沉默阈值 [0, 1]
    polarization_factor: float = 0.3     # 群体极化系数 [0, 1]
    echo_chamber_factor: float = 0.2     # 回音室效应系数 [0, 1]


class ParseRequest(BaseModel):
    """知识图谱解析请求参数"""
    content: str  # 新闻文本内容


class AirdropRequest(BaseModel):
    """事件注入请求参数"""
    content: str  # 事件文本内容
    source: str = "public"  # 来源 (public/private)


def _is_local_llm_runtime(llm_config: LLMConfig) -> bool:
    """根据 LLM 配置判断是否本地推理环境（如 Ollama）。"""
    base_url = (llm_config.base_url or "").lower()
    local_hosts = ("localhost", "127.0.0.1", "::1")
    return any(host in base_url for host in local_hosts) or "11434" in base_url


def _infer_ollama_model_size_b(model_name: str) -> int:
    """
    从模型名推断参数规模（如 gemma4:31b -> 31）。
    解析失败返回 0。
    """
    if not model_name:
        return 0
    model_name = model_name.lower()
    if "b" not in model_name or ":" not in model_name:
        return 0
    try:
        suffix = model_name.split(":")[-1]
        if suffix.endswith("b"):
            return int(suffix[:-1])
    except ValueError:
        return 0
    return 0


def calculate_max_concurrent(population_size: int) -> int:
    """
    根据 Agent 数量自动计算合理的并发数

    默认 auto 策略会按运行环境自适应：
    - local: 本地推理（如 Ollama），更保守，避免超时重试风暴
    - remote: 远程推理服务，允许更高并发

    可通过环境变量覆盖：
    - LLM_CONCURRENCY_PROFILE=local|remote|auto
    """
    profile = os.getenv("LLM_CONCURRENCY_PROFILE", "auto").strip().lower()
    llm_config = LLMConfig()
    is_local = _is_local_llm_runtime(llm_config)
    model_size_b = _infer_ollama_model_size_b(llm_config.model)

    if profile == "local" or (profile == "auto" and is_local):
        # 本地推理：默认保守；超大模型（>=20B）更保守
        max_cap = 16 if model_size_b >= 20 else 20
        return max(4, min(int(population_size * 0.2), max_cap))

    # remote / auto(remote)
    return max(10, min(int(population_size * 0.5), 100))


def _build_perceived_climate_summary(agent_id: int) -> dict:
    """
    统一构建 Agent 邻居舆论气候（兼容单层/双层网络）。
    返回前端透视面板所需的扁平字段。
    """
    global engine

    default_climate = {
        "total": 0,
        "pro_rumor_ratio": 0.0,
        "pro_truth_ratio": 0.0,
        "neutral_ratio": 1.0,
        "silent_ratio": 0.0,
        "avg_opinion": 0.0
    }

    if engine is None or not getattr(engine, "use_llm", False) or not getattr(engine, "llm_population", None):
        return default_climate

    population = engine.llm_population
    if agent_id < 0 or agent_id >= len(population.agents):
        return default_climate

    try:
        # 双层网络模式：合并公域+私域邻居去重后统计
        if hasattr(population, "get_public_neighbor_agents") and hasattr(population, "get_private_neighbor_agents"):
            public_neighbors = population.get_public_neighbor_agents(agent_id)
            private_neighbors = population.get_private_neighbor_agents(agent_id)
            neighbor_map = {n.id: n for n in (public_neighbors + private_neighbors)}
            neighbors = list(neighbor_map.values())
        # 单层网络模式
        elif hasattr(population, "get_neighbor_agents"):
            neighbors = population.get_neighbor_agents(agent_id)
        else:
            neighbors = []
    except Exception:
        neighbors = []

    if not neighbors:
        return default_climate

    total = len(neighbors)
    pro_rumor = sum(1 for n in neighbors if n.opinion < -0.2)
    pro_truth = sum(1 for n in neighbors if n.opinion > 0.2)
    neutral = total - pro_rumor - pro_truth
    silent = sum(1 for n in neighbors if getattr(n, "is_silent", False))
    avg_opinion = sum(float(n.opinion) for n in neighbors) / total

    return {
        "total": total,
        "pro_rumor_ratio": pro_rumor / total,
        "pro_truth_ratio": pro_truth / total,
        "neutral_ratio": neutral / total,
        "silent_ratio": silent / total,
        "avg_opinion": avg_opinion
    }


def _normalize_snapshot_climate(snapshot: dict) -> dict:
    """
    规范化快照中的 perceived_climate，保证前端字段可用。
    """
    agent_id = int(snapshot.get("agent_id", -1))
    climate = snapshot.get("perceived_climate")

    # 1) 已是前端需要的扁平结构，补默认值后直接返回
    if isinstance(climate, dict) and "total" in climate:
        climate.setdefault("pro_rumor_ratio", 0.0)
        climate.setdefault("pro_truth_ratio", 0.0)
        climate.setdefault("neutral_ratio", 1.0)
        climate.setdefault("silent_ratio", 0.0)
        climate.setdefault("avg_opinion", 0.0)
        snapshot["perceived_climate"] = climate
        return snapshot

    # 2) 双层结构（public/private）或缺失时，统一重算扁平结构
    snapshot["perceived_climate"] = _build_perceived_climate_summary(agent_id)
    return snapshot


@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "service": "信息茧房推演系统", "version": "2.0.0"}


@app.post("/api/simulation/start")
async def start_simulation(params: StartRequest):
    """
    启动新的推演模拟
    如果有待注入的事件/知识图谱，会自动注入到引擎中
    返回初始状态
    """
    global engine, pending_knowledge_graph, pending_event_content, pending_event_source

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

    # 根据是否启用双层网络选择引擎
    if params.use_dual_network:
        logger.info(f"使用双层网络引擎, 社群数: {params.num_communities}, LLM模式: {params.use_llm}")
        engine = SimulationEngineDual(
            population_size=params.population_size,
            cocoon_strength=params.cocoon_strength,
            debunk_delay=params.debunk_delay,
            initial_rumor_spread=params.initial_rumor_spread,
            use_llm=params.use_llm,
            llm_config=llm_config,
            num_communities=params.num_communities,
            public_m=params.public_m,
            # 增强版数学模型参数
            debunk_credibility=params.debunk_credibility,
            authority_factor=params.authority_factor,
            backfire_strength=params.backfire_strength,
            silence_threshold=params.silence_threshold,
            polarization_factor=params.polarization_factor,
            echo_chamber_factor=params.echo_chamber_factor
        )
    else:
        engine = SimulationEngine(
            population_size=params.population_size,
            cocoon_strength=params.cocoon_strength,
            debunk_delay=params.debunk_delay,
            initial_rumor_spread=params.initial_rumor_spread,
            network_type=params.network_type,
            use_llm=params.use_llm,
            llm_config=llm_config,
            # 增强版数学模型参数
            debunk_credibility=params.debunk_credibility,
            authority_factor=params.authority_factor,
            backfire_strength=params.backfire_strength,
            silence_threshold=params.silence_threshold,
            polarization_factor=params.polarization_factor,
            echo_chamber_factor=params.echo_chamber_factor
        )

    initial_state = engine.initialize()
    
    # ==================== 自动注入待处理的事件 ====================
    if pending_knowledge_graph and pending_event_content:
        logger.info(f"检测到待注入事件，自动注入到引擎: {pending_event_content[:50]}...")
        engine.knowledge_graph = pending_knowledge_graph
        
        # 如果引擎支持设置新闻
        if hasattr(engine, 'set_news'):
            import inspect
            if inspect.iscoroutinefunction(engine.set_news):
                await engine.set_news(pending_event_content, pending_event_source or "public", parse_graph=False)
            else:
                engine.set_news(pending_event_content, pending_event_source or "public", parse_graph=False)
        
        # 广播事件
        target_scope = "all"
        if pending_event_source == "public":
            target_scope = "public_only"
        elif pending_event_source == "private":
            target_scope = "private_only"
        engine.broadcast_event(pending_event_content, target_scope)
        
        logger.info(f"待注入事件已成功注入，图谱包含 {len(pending_knowledge_graph.get('entities', []))} 个实体")
        
        # 清空待注入数据
        pending_knowledge_graph = None
        pending_event_content = None
        pending_event_source = None
    
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


@app.get("/api/math-model/explanation")
async def get_math_model_explanation():
    """
    获取增强版数学模型的理论解释
    
    返回：
    - theories: 各社会心理学机制的理论说明
    - parameters: 各参数的含义和影响
    """
    from .simulation.math_model_enhanced import EnhancedMathModel
    
    model = EnhancedMathModel()
    
    return JSONResponse(content={
        "theories": model.get_theory_explanation(),
        "parameters": model.get_parameter_explanation()
    })


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

    # 优先从全局存储获取快照（同时检查单层和双层）
    snapshot = get_agent_snapshot_global(agent_id) or get_agent_snapshot_global_dual(agent_id)

    if snapshot:
        return JSONResponse(content=_normalize_snapshot_climate(snapshot))

    # 如果全局存储没有，尝试从引擎获取（支持双层网络）
    if engine.use_llm and hasattr(engine, 'llm_population') and engine.llm_population:
        snapshot = engine.llm_population.get_agent_snapshot(agent_id)
        if snapshot:
            return JSONResponse(content=_normalize_snapshot_climate(snapshot))

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
            "perceived_climate": _build_perceived_climate_summary(agent_id)
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
    report_filename = os.path.basename(report_path) if report_path else None

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


@app.post("/api/report/generate")
async def generate_intelligence_report_endpoint():
    """
    生成智库专报 (异步，耗时较长)

    调用 AnalystAgent 基于 LLM 生成专业的舆情分析报告
    """
    global engine
    if engine is None:
        return JSONResponse(
            content={"success": False, "error": "推演引擎未初始化，请先运行推演"},
            status_code=400
        )

    if not engine.use_llm:
        return JSONResponse(
            content={"success": False, "error": "智库专报仅支持LLM驱动模式"},
            status_code=400
        )

    if not engine.history:
        return JSONResponse(
            content={"success": False, "error": "推演尚未运行，请先执行推演"},
            status_code=400
        )

    if not engine.llm_population:
        return JSONResponse(
            content={"success": False, "error": "Agent群体未初始化"},
            status_code=400
        )

    try:
        # 生成智库专报
        report_content = await generate_intelligence_report(
            engine,
            engine.llm_population
        )

        # 保存报告
        reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
        reports_dir = os.path.abspath(reports_dir)
        os.makedirs(reports_dir, exist_ok=True)

        import time
        report_filename = f"intelligence_report_{int(time.time())}.md"
        report_path = os.path.join(reports_dir, report_filename)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        return JSONResponse(content={
            "success": True,
            "content": report_content,
            "filename": report_filename,
            "path": report_path.replace("\\", "/")
        })

    except Exception as e:
        logger.error(f"智库专报生成失败: {e}")
        return JSONResponse(
            content={"success": False, "error": f"报告生成失败: {str(e)}"},
            status_code=500
        )


@app.get("/api/report/stream")
async def stream_intelligence_report():
    """
    流式生成智库专报 (SSE)

    使用 Server-Sent Events 实时推送报告内容
    """
    global engine
    if engine is None:
        return JSONResponse(
            content={"error": "推演引擎未初始化，请先运行推演"},
            status_code=400
        )

    if not engine.use_llm:
        return JSONResponse(
            content={"error": "智库专报仅支持LLM驱动模式"},
            status_code=400
        )

    if not engine.history:
        return JSONResponse(
            content={"error": "推演尚未运行，请先执行推演"},
            status_code=400
        )

    if not engine.llm_population:
        return JSONResponse(
            content={"error": "Agent群体未初始化"},
            status_code=400
        )

    async def event_generator():
        """SSE 事件生成器"""
        try:
            # 构建上下文
            context = DataSampler.build_context(engine, engine.llm_population)

            # 创建 AnalystAgent 实例
            llm_config = LLMConfig()
            llm_config.timeout = 120
            llm_config.max_tokens = 2000
            llm_config.temperature = 0.5

            async with AnalystAgent(llm_config) as agent:
                async for chunk in agent.generate_report_stream(context):
                    # SSE 格式: data: {content}\n\n
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            # 发送结束信号
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"流式报告生成失败: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/event/parse")
async def parse_news_event(req: ParseRequest):
    """
    解析新闻文本为知识图谱

    Request Body:
        content: 新闻文本内容
    """
    from .simulation.graph_parser_agent import get_graph_parser

    try:
        graph_parser = get_graph_parser()
        knowledge_graph = await graph_parser.parse(req.content)

        return {
            "success": True,
            "data": knowledge_graph
        }
    except Exception as e:
        logger.error(f"知识图谱解析失败: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


@app.post("/api/event/airdrop")
async def airdrop_event(req: AirdropRequest):
    """
    注入突发事件 - "解析-注入-推演"三段式管线
    
    第一阶段（解析）：调用 GraphParserAgent 提取结构化知识图谱
    第二阶段（封装）：将图谱+原始文本封装成结构化的 EventMsg
    第三阶段（广播）：将 EventMsg 发送给网络中的节点
    
    Request Body:
        content: 事件文本内容
        source: 来源 (public/private)

    Response:
        success: 是否成功
        knowledge_graph: 解析后的知识图谱 JSON
        event: 事件记录
    """
    global engine, pending_knowledge_graph, pending_event_content, pending_event_source

    # ==================== 第一阶段：解析（挂起并调用大模型）====================
    logger.info(f"[管线阶段1] 开始解析突发事件: {req.content[:50]}...")

    try:
        from .simulation.graph_parser_agent import get_graph_parser
        graph_parser = get_graph_parser()
        knowledge_graph = await graph_parser.parse(req.content)

        entity_count = len(knowledge_graph.get('entities', []))
        relation_count = len(knowledge_graph.get('relations', []))
        logger.info(f"[管线阶段1] 知识图谱解析完成: {entity_count} 个实体, {relation_count} 个关系")

    except Exception as e:
        logger.error(f"[管线阶段1] 知识图谱解析失败: {e}")
        # 即使解析失败，也继续流程，使用空图谱
        knowledge_graph = {
            "entities": [],
            "relations": [],
            "summary": req.content[:100],
            "parse_error": True,
            "error_message": str(e)
        }

    # ==================== 第二阶段：封装（构建结构化 EventMsg）====================
    logger.info(f"[管线阶段2] 封装结构化事件消息...")

    # 构建结构化事件消息
    event_msg = {
        "type": "breaking_news",
        "content": req.content,  # 原始文本
        "source": req.source,    # 来源
        "knowledge_graph": knowledge_graph,  # 解析后的图谱
        "summary": knowledge_graph.get("summary", ""),
        "keywords": knowledge_graph.get("keywords", []),
        "sentiment": knowledge_graph.get("sentiment", "中性"),
        "credibility_hint": knowledge_graph.get("credibility_hint", "不确定"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # 确定广播范围
    target_scope = "all"
    if req.source == "public":
        target_scope = "public_only"
    elif req.source == "private":
        target_scope = "private_only"

    # ==================== 处理推演未开始的情况 ====================
    if engine is None:
        logger.info("[管线阶段3] 推演引擎未初始化，存储待注入事件供后续使用")
        # 存储待注入的事件
        pending_knowledge_graph = knowledge_graph
        pending_event_content = req.content
        pending_event_source = req.source
        
        return {
            "success": True,
            "data": {
                "event": {"step": 0, "content": req.content, "scope": target_scope, "pending": True},
                "knowledge_graph": knowledge_graph,
                "event_msg": event_msg,
                "message": "事件已解析并存储，将在推演开始时自动注入"
            }
        }

    # ==================== 第三阶段：广播（发送给推演引擎）====================
    logger.info(f"[管线阶段3] 广播事件到推演引擎, 范围: {target_scope}")
    
    try:
        # 更新引擎的新闻和图谱
        if hasattr(engine, 'set_news'):
            import inspect
            if inspect.iscoroutinefunction(engine.set_news):
                await engine.set_news(req.content, req.source, parse_graph=False)
            else:
                engine.set_news(req.content, req.source, parse_graph=False)
        
        # 更新引擎的知识图谱
        engine.knowledge_graph = knowledge_graph

        # 广播事件（包含图谱信息）
        event = engine.broadcast_event(req.content, target_scope)
        event["knowledge_graph"] = knowledge_graph
        event["event_msg"] = event_msg
        
        logger.info(f"[管线完成] 事件注入成功，已广播给所有Agent")

        return {
            "success": True,
            "data": {
                "event": event,
                "knowledge_graph": knowledge_graph,
                "event_msg": event_msg
            }
        }
        
    except Exception as e:
        logger.error(f"[管线阶段3] 事件广播失败: {e}")
        return JSONResponse(
            content={"success": False, "error": f"事件广播失败: {str(e)}"},
            status_code=500
        )


@app.get("/api/event/knowledge-graph")
async def get_current_knowledge_graph():
    """
    获取当前推演的知识图谱
    """
    global engine
    
    if engine is None:
        return JSONResponse(
            content={"success": False, "error": "推演引擎未初始化"},
            status_code=400
        )
    
    return {
        "success": True,
        "data": engine.knowledge_graph
    }


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

    async def send_progress(step: int, total: int, agent_id: int = None, agent_opinion: float = None):
        """发送进度更新"""
        try:
            # 构建进度消息
            progress_data = {
                "type": "progress",
                "step": step,
                "total": total,
                "percentage": round(step / total * 100, 1) if total > 0 else 0,
                "current_step": engine.step_count if engine else 0,
                "max_steps": max_steps if 'max_steps' in dir() else 50
            }

            # 添加 Agent 详细信息
            if agent_id is not None:
                progress_data["agent_id"] = agent_id
                progress_data["agent_opinion"] = round(agent_opinion, 2) if agent_opinion is not None else 0

                # 根据观点值判断立场
                if agent_opinion is not None:
                    if agent_opinion < -0.3:
                        stance = "信谣言"
                    elif agent_opinion > 0.3:
                        stance = "信真相"
                    else:
                        stance = "中立"
                    progress_data["agent_stance"] = stance

            progress_data["message"] = f"正在推演 Agent {step}/{total}" + (f" (ID:{agent_id})" if agent_id is not None else "")

            await websocket.send_json(progress_data)
        except Exception as e:
            logger.debug(f"发送进度失败: {e}")

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
                population_size = params.get("population_size", 200)
                use_dual_network = params.get("use_dual_network", True)

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

                # 根据是否启用双层网络选择引擎
                if use_dual_network:
                    logger.info(f"使用双层网络引擎, 社群数: {params.get('num_communities', 8)}, LLM模式: {use_llm}")
                    engine = SimulationEngineDual(
                        population_size=population_size,
                        cocoon_strength=params.get("cocoon_strength", 0.5),
                        debunk_delay=params.get("debunk_delay", 10),
                        initial_rumor_spread=params.get("initial_rumor_spread", 0.3),
                        use_llm=use_llm,
                        llm_config=llm_config,
                        num_communities=params.get("num_communities", 8),
                        public_m=params.get("public_m", 3),
                        # 增强版数学模型参数
                        debunk_credibility=params.get("debunk_credibility", 0.7),
                        authority_factor=params.get("authority_factor", 0.5),
                        backfire_strength=params.get("backfire_strength", 0.3),
                        silence_threshold=params.get("silence_threshold", 0.3),
                        polarization_factor=params.get("polarization_factor", 0.3),
                        echo_chamber_factor=params.get("echo_chamber_factor", 0.2)
                    )
                else:
                    engine = SimulationEngine(
                        population_size=population_size,
                        cocoon_strength=params.get("cocoon_strength", 0.5),
                        debunk_delay=params.get("debunk_delay", 10),
                        initial_rumor_spread=params.get("initial_rumor_spread", 0.3),
                        network_type=params.get("network_type", "small_world"),
                        use_llm=use_llm,
                        llm_config=llm_config,
                        # 增强版数学模型参数
                        debunk_credibility=params.get("debunk_credibility", 0.7),
                        authority_factor=params.get("authority_factor", 0.5),
                        backfire_strength=params.get("backfire_strength", 0.3),
                        silence_threshold=params.get("silence_threshold", 0.3),
                        polarization_factor=params.get("polarization_factor", 0.3),
                        echo_chamber_factor=params.get("echo_chamber_factor", 0.2)
                    )

                # 设置进度回调
                engine.set_progress_callback(send_progress)

                initial_state = engine.initialize()
                await websocket.send_json({
                    "type": "state",
                    "data": initial_state.to_dict()
                })
                logger.info(f"模拟已启动, LLM模式: {use_llm}, 双层网络: {use_dual_network}")

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

"""
报告相关路由
"""
import os
import logging
import platform
import subprocess

from fastapi import APIRouter
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from typing import Optional

from .. import state
from ..simulation.analyst_agent import generate_intelligence_report, AnalystAgent, DataSampler
from ..llm.client import LLMConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/report", tags=["report"])


@router.post("/open")
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


@router.get("/content")
async def get_report_content(filename: str):
    """获取报告内容"""
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
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


@router.get("/download")
async def download_report(filename: str):
    """下载报告文件"""
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
    reports_dir = os.path.abspath(reports_dir)
    report_path = os.path.join(reports_dir, filename)

    if not os.path.exists(report_path):
        return JSONResponse(content={"error": "报告不存在"}, status_code=404)

    return FileResponse(
        path=report_path,
        filename=filename,
        media_type="text/markdown"
    )


@router.get("/list")
async def list_reports(
    type: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = "modified",
    order: Optional[str] = "desc"
):
    """
    列出所有报告文件，支持分类、搜索、排序

    Args:
        type: 报告类型筛选 (simulation/intelligence/all)，默认 all
        search: 文件名搜索关键词
        sort: 排序字段 (modified/size/name)，默认 modified
        order: 排序方向 (desc/asc)，默认 desc

    Returns:
        reports: 所有报告列表
        simulation_reports: 推演报告列表
        intelligence_reports: 智库专报列表
        counts: 各类型数量统计
    """
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
    reports_dir = os.path.abspath(reports_dir)

    if not os.path.exists(reports_dir):
        return JSONResponse(content={
            "reports": [],
            "simulation_reports": [],
            "intelligence_reports": [],
            "counts": {"total": 0, "simulation": 0, "intelligence": 0}
        })

    all_reports = []
    simulation_reports = []
    intelligence_reports = []

    for f in os.listdir(reports_dir):
        if not f.endswith(".md"):
            continue

        filepath = os.path.join(reports_dir, f)
        stat = os.stat(filepath)

        # 根据文件名判断类型
        if f.startswith("intelligence_report_"):
            report_type = "intelligence"
        elif f.startswith("report_") or f.startswith("report_dual_"):
            report_type = "simulation"
        else:
            report_type = "other"

        report_item = {
            "filename": f,
            "path": filepath,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "type": report_type
        }

        all_reports.append(report_item)

        if report_type == "simulation":
            simulation_reports.append(report_item)
        elif report_type == "intelligence":
            intelligence_reports.append(report_item)

    # 搜索过滤
    if search:
        search_lower = search.lower()
        all_reports = [r for r in all_reports if search_lower in r["filename"].lower()]
        simulation_reports = [r for r in simulation_reports if search_lower in r["filename"].lower()]
        intelligence_reports = [r for r in intelligence_reports if search_lower in r["filename"].lower()]

    # 类型筛选
    if type == "simulation":
        filtered_reports = simulation_reports
    elif type == "intelligence":
        filtered_reports = intelligence_reports
    else:
        filtered_reports = all_reports

    # 排序
    reverse = (order == "desc")
    if sort == "size":
        filtered_reports.sort(key=lambda r: r["size"], reverse=reverse)
        simulation_reports.sort(key=lambda r: r["size"], reverse=reverse)
        intelligence_reports.sort(key=lambda r: r["size"], reverse=reverse)
    elif sort == "name":
        filtered_reports.sort(key=lambda r: r["filename"], reverse=reverse)
        simulation_reports.sort(key=lambda r: r["filename"], reverse=reverse)
        intelligence_reports.sort(key=lambda r: r["filename"], reverse=reverse)
    else:  # modified
        filtered_reports.sort(key=lambda r: r["modified"], reverse=reverse)
        simulation_reports.sort(key=lambda r: r["modified"], reverse=reverse)
        intelligence_reports.sort(key=lambda r: r["modified"], reverse=reverse)

    return JSONResponse(content={
        "reports": filtered_reports,
        "simulation_reports": simulation_reports,
        "intelligence_reports": intelligence_reports,
        "counts": {
            "total": len(all_reports),
            "simulation": len(simulation_reports),
            "intelligence": len(intelligence_reports)
        }
    })


@router.post("/generate")
async def generate_intelligence_report_endpoint():
    """
    生成智库专报 (异步，耗时较长)

    调用 AnalystAgent 基于 LLM 生成专业的舆情分析报告
    """
    import json
    import time

    if state.engine is None:
        return JSONResponse(
            content={"success": False, "error": "推演引擎未初始化，请先运行推演"},
            status_code=400
        )

    if not state.engine.use_llm:
        return JSONResponse(
            content={"success": False, "error": "智库专报仅支持LLM驱动模式"},
            status_code=400
        )

    if not state.engine.history:
        return JSONResponse(
            content={"success": False, "error": "推演尚未运行，请先执行推演"},
            status_code=400
        )

    if not state.engine.llm_population:
        return JSONResponse(
            content={"success": False, "error": "Agent群体未初始化"},
            status_code=400
        )

    try:
        # 生成智库专报
        report_content = await generate_intelligence_report(
            state.engine,
            state.engine.llm_population
        )

        # 保存报告
        reports_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
        reports_dir = os.path.abspath(reports_dir)
        os.makedirs(reports_dir, exist_ok=True)

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


@router.get("/stream")
async def stream_intelligence_report():
    """
    流式生成智库专报 (SSE)

    使用 Server-Sent Events 实时推送报告内容
    """
    import json

    if state.engine is None:
        return JSONResponse(
            content={"error": "推演引擎未初始化，请先运行推演"},
            status_code=400
        )

    if not state.engine.use_llm:
        return JSONResponse(
            content={"error": "智库专报仅支持LLM驱动模式"},
            status_code=400
        )

    if not state.engine.history:
        return JSONResponse(
            content={"error": "推演尚未运行，请先执行推演"},
            status_code=400
        )

    if not state.engine.llm_population:
        return JSONResponse(
            content={"error": "Agent群体未初始化"},
            status_code=400
        )

    async def event_generator():
        """SSE 事件生成器"""
        try:
            # 构建上下文
            context = DataSampler.build_context(state.engine, state.engine.llm_population)

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

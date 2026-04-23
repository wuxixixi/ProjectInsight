"""
事件注入路由
"""
import inspect
import logging
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import state
from ..helpers import AirdropRequest, ParseRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/event", tags=["event"])


@router.post("/parse")
async def parse_news_event(req: ParseRequest):
    """
    解析新闻文本为知识图谱

    Request Body:
        content: 新闻文本内容
    """
    from ..simulation.graph_parser_agent import get_graph_parser

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


@router.post("/airdrop")
async def airdrop_event(req: AirdropRequest):
    """
    注入突发事件 - "解析-注入-推演"三段式管线

    第一阶段（解析）：调用 GraphParserAgent 提取结构化知识图谱（可选跳过）
    第二阶段（封装）：将图谱+原始文本封装成结构化的 EventMsg
    第三阶段（广播）：将 EventMsg 发送给网络中的节点

    Request Body:
        content: 事件文本内容
        source: 来源 (public/private)
        skip_parse: 跳过知识图谱解析（快速注入模式）

    Response:
        success: 是否成功
        knowledge_graph: 解析后的知识图谱 JSON
        event: 事件记录
    """
    # ==================== 标记注入进行中（暂停推演）====================
    state.injection_in_progress = True
    logger.info(f"[管线] 事件注入开始，推演暂停等待")

    try:
        # ==================== 第一阶段：解析（可选跳过）====================
        if req.skip_parse:
            # 快速注入模式：跳过 LLM 解析，使用简单图谱
            logger.info(f"[快速注入] 跳过知识图谱解析: {req.content[:50]}...")
            knowledge_graph = {
                "entities": [{"id": "e1", "name": "事件主体", "type": "事件", "description": req.content[:50]}],
                "relations": [],
                "summary": req.content[:100],
                "keywords": [],
                "sentiment": "中性",
                "credibility_hint": "不确定",
                "skip_parse": True
            }
        else:
            # 完整解析模式：调用 LLM 解析知识图谱
            logger.info(f"[管线阶段1] 开始解析突发事件: {req.content[:50]}...")

            try:
                from ..simulation.graph_parser_agent import get_graph_parser
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

        # 用户选择的可信度优先于自动解析的
        final_credibility = req.credibility if req.credibility != "不确定" else knowledge_graph.get("credibility_hint", "不确定")
        # 同步到 knowledge_graph 供后续待注入使用
        knowledge_graph["credibility_hint"] = final_credibility
        event_msg = {
            "type": "breaking_news",
            "content": req.content,  # 原始文本
            "source": req.source,    # 来源
            "knowledge_graph": knowledge_graph,  # 解析后的图谱
            "summary": knowledge_graph.get("summary", ""),
            "keywords": knowledge_graph.get("keywords", []),
            "sentiment": knowledge_graph.get("sentiment", "中性"),
            "credibility_hint": final_credibility,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 确定广播范围
        target_scope = "all"
        if req.source == "public":
            target_scope = "public_only"
        elif req.source == "private":
            target_scope = "private_only"

        # ==================== 处理推演未开始的情况 ====================
        if state.engine is None:
            logger.info("[管线阶段3] 推演引擎未初始化，存储待注入事件供后续使用")
            # 存储待注入的事件
            state.pending_knowledge_graph = knowledge_graph
            state.pending_event_content = req.content
            state.pending_event_source = req.source

            return {
                "success": True,
                "data": {
                    "event": {"step": 0, "content": req.content, "scope": target_scope, "pending": True, "credibility": final_credibility},
                    "knowledge_graph": knowledge_graph,
                    "event_msg": event_msg,
                    "message": "事件已解析并存储，将在推演开始时自动注入"
                }
            }

        # ==================== 第三阶段：广播（发送给推演引擎）====================
        logger.info(f"[管线阶段3] 广播事件到推演引擎, 范围: {target_scope}")

        # 获取情感和可信度
        sentiment = knowledge_graph.get("sentiment", "中性")
        # 使用前面计算的 final_credibility
        credibility = final_credibility
        entity_count = len(knowledge_graph.get('entities', []))

        # 更新引擎的新闻和图谱
        if hasattr(state.engine, 'set_news'):
            if inspect.iscoroutinefunction(state.engine.set_news):
                await state.engine.set_news(req.content, req.source, parse_graph=False)
            else:
                state.engine.set_news(req.content, req.source, parse_graph=False)

        # 更新引擎的知识图谱（融合模式）
        entities = knowledge_graph.get('entities', [])
        relations = knowledge_graph.get('relations', [])
        if entities and hasattr(state.engine, 'set_knowledge_graph'):
            state.engine.set_knowledge_graph(entities, relations, merge=True)
            logger.info(f"知识图谱已融合，知识驱动演化已启用")
        else:
            # 没有实体时仍然更新图谱数据
            state.engine.knowledge_graph = knowledge_graph

        # 广播事件（包含图谱信息，触发事件冲击）
        event = state.engine.broadcast_event(
            content=req.content,
            target_scope=target_scope,
            sentiment=sentiment,
            credibility=credibility
        )
        # 返回融合后的知识图谱
        merged_graph = state.engine.knowledge_graph
        event["knowledge_graph"] = merged_graph
        event["event_msg"] = event_msg

        logger.info(f"[管线完成] 事件注入成功，已广播给所有Agent，图谱包含 {len(merged_graph.get('entities', []))} 个实体")

        return {
            "success": True,
            "data": {
                "event": event,
                "knowledge_graph": merged_graph,
                "event_msg": event_msg
            }
        }

    except Exception as e:
        logger.error(f"[管线] 事件注入失败: {e}")
        return JSONResponse(
            content={"success": False, "error": f"事件注入失败: {str(e)}"},
            status_code=500
        )
    finally:
        # 无论成功失败，都解除推演暂停
        state.injection_in_progress = False
        logger.info(f"[管线] 事件注入结束，推演可恢复")


@router.get("/knowledge-graph")
async def get_current_knowledge_graph():
    """
    获取当前推演的知识图谱
    """
    if state.engine is None:
        return JSONResponse(
            content={"success": False, "error": "推演引擎未初始化"},
            status_code=400
        )

    return {
        "success": True,
        "data": state.engine.knowledge_graph
    }

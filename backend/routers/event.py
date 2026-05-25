"""
浜嬩欢娉ㄥ叆璺敱
"""
import inspect
import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import state
from ..helpers import AirdropRequest, ParseRequest
from ..llm.client import create_llm_config_from_env

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/event", tags=["event"])


async def _maybe_set_news(engine, content: str, source: str) -> None:
    """Support both sync and async engine.set_news implementations."""
    if not hasattr(engine, "set_news"):
        return
    result = engine.set_news(content, source, parse_graph=False)
    if inspect.isawaitable(result):
        await result


@router.post("/parse")
async def parse_news_event(req: ParseRequest):
    """
    瑙ｆ瀽鏂伴椈鏂囨湰涓虹煡璇嗗浘璋?

    Request Body:
        content: 鏂伴椈鏂囨湰鍐呭
    """
    from ..simulation.graph_parser_agent import get_graph_parser

    try:
        graph_parser = get_graph_parser(create_llm_config_from_env("LLM"))
        knowledge_graph = await graph_parser.parse(req.content)

        return {
            "success": True,
            "data": knowledge_graph
        }
    except Exception as e:
        logger.error(f"鐭ヨ瘑鍥捐氨瑙ｆ瀽澶辫触: {e}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/airdrop")
async def airdrop_event(req: AirdropRequest):
    """
    娉ㄥ叆绐佸彂浜嬩欢 - "瑙ｆ瀽-娉ㄥ叆-鎺ㄦ紨"涓夋寮忕绾?

    绗竴闃舵锛堣В鏋愶級锛氳皟鐢?GraphParserAgent 鎻愬彇缁撴瀯鍖栫煡璇嗗浘璋憋紙鍙€夎烦杩囷級
    绗簩闃舵锛堝皝瑁咃級锛氬皢鍥捐氨+鍘熷鏂囨湰灏佽鎴愮粨鏋勫寲鐨?EventMsg
    绗笁闃舵锛堝箍鎾級锛氬皢 EventMsg 鍙戦€佺粰缃戠粶涓殑鑺傜偣

    Request Body:
        content: 浜嬩欢鏂囨湰鍐呭
        source: 鏉ユ簮 (public/private)
        skip_parse: 璺宠繃鐭ヨ瘑鍥捐氨瑙ｆ瀽锛堝揩閫熸敞鍏ユā寮忥級

    Response:
        success: 鏄惁鎴愬姛
        knowledge_graph: 瑙ｆ瀽鍚庣殑鐭ヨ瘑鍥捐氨 JSON
        event: 浜嬩欢璁板綍
    """
    # ==================== 鏍囪娉ㄥ叆杩涜涓紙鏆傚仠鎺ㄦ紨锛?===================
    state.injection_in_progress = True
    logger.info(f"[绠＄嚎] 浜嬩欢娉ㄥ叆寮€濮嬶紝鎺ㄦ紨鏆傚仠绛夊緟")

    try:
        # ==================== 绗竴闃舵锛氳В鏋愶紙鍙€夎烦杩囷級====================
        if req.skip_parse:
            # 蹇€熸敞鍏ユā寮忥細璺宠繃 LLM 瑙ｆ瀽锛屼娇鐢ㄧ畝鍗曞浘璋?
            logger.info(f"[蹇€熸敞鍏 璺宠繃鐭ヨ瘑鍥捐氨瑙ｆ瀽: {req.content[:50]}...")
            knowledge_graph = {
                "entities": [{"id": "e1", "name": "浜嬩欢涓讳綋", "type": "浜嬩欢", "description": req.content[:50]}],
                "relations": [],
                "summary": req.content[:100],
                "keywords": [],
                "sentiment": "中性",
                "credibility_hint": "不确定",
                "skip_parse": True
            }
        else:
            # 瀹屾暣瑙ｆ瀽妯″紡锛氳皟鐢?LLM 瑙ｆ瀽鐭ヨ瘑鍥捐氨
            logger.info(f"[绠＄嚎闃舵1] 寮€濮嬭В鏋愮獊鍙戜簨浠? {req.content[:50]}...")

            try:
                from ..simulation.graph_parser_agent import get_graph_parser
                graph_parser = get_graph_parser(create_llm_config_from_env("LLM"))
                knowledge_graph = await graph_parser.parse(req.content)

                entity_count = len(knowledge_graph.get('entities', []))
                relation_count = len(knowledge_graph.get('relations', []))
                logger.info(f"[事件注入-解析] 知识图谱解析完成: {entity_count} 个实体, {relation_count} 个关系")

            except Exception as e:
                logger.error(f"[绠＄嚎闃舵1] 鐭ヨ瘑鍥捐氨瑙ｆ瀽澶辫触: {e}")
                # 鍗充娇瑙ｆ瀽澶辫触锛屼篃缁х画娴佺▼锛屼娇鐢ㄧ┖鍥捐氨
                knowledge_graph = {
                    "entities": [],
                    "relations": [],
                    "summary": req.content[:100],
                    "parse_error": True,
                    "error_message": str(e)
                }

        # ==================== 绗簩闃舵锛氬皝瑁咃紙鏋勫缓缁撴瀯鍖?EventMsg锛?===================
        logger.info(f"[绠＄嚎闃舵2] 灏佽缁撴瀯鍖栦簨浠舵秷鎭?..")

        # 鐢ㄦ埛閫夋嫨鐨勫彲淇″害浼樺厛浜庤嚜鍔ㄨВ鏋愮殑
        final_credibility = req.credibility if req.credibility != "不确定" else knowledge_graph.get("credibility_hint", "不确定")
        # 鍚屾鍒?knowledge_graph 渚涘悗缁緟娉ㄥ叆浣跨敤
        knowledge_graph["credibility_hint"] = final_credibility
        event_msg = {
            "type": "breaking_news",
            "content": req.content,  # 鍘熷鏂囨湰
            "source": req.source,    # 鏉ユ簮
            "knowledge_graph": knowledge_graph,  # 瑙ｆ瀽鍚庣殑鍥捐氨
            "summary": knowledge_graph.get("summary", ""),
            "keywords": knowledge_graph.get("keywords", []),
            "sentiment": knowledge_graph.get("sentiment", "中性"),
            "credibility_hint": final_credibility,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }

        # 纭畾骞挎挱鑼冨洿
        target_scope = "all"
        if req.source == "public":
            target_scope = "public_only"
        elif req.source == "private":
            target_scope = "private_only"

        # ==================== 澶勭悊鎺ㄦ紨鏈紑濮嬬殑鎯呭喌 ====================
        if state.engine is None:
            logger.info("[事件注入-广播] 推演引擎未初始化，暂存待注入事件供后续使用")
            # 瀛樺偍寰呮敞鍏ョ殑浜嬩欢
            state.pending_knowledge_graph = knowledge_graph
            state.pending_event_content = req.content
            state.pending_event_source = req.source

            return {
                "success": True,
                "data": {
                    "event": {"step": 0, "content": req.content, "scope": target_scope, "pending": True, "credibility": final_credibility},
                    "knowledge_graph": knowledge_graph,
                    "event_msg": event_msg,
                    "message": "浜嬩欢宸茶В鏋愬苟瀛樺偍锛屽皢鍦ㄦ帹婕斿紑濮嬫椂鑷姩娉ㄥ叆"
                }
            }

        # ==================== 绗笁闃舵锛氬箍鎾紙鍙戦€佺粰鎺ㄦ紨寮曟搸锛?===================
        logger.info(f"[绠＄嚎闃舵3] 骞挎挱浜嬩欢鍒版帹婕斿紩鎿? 鑼冨洿: {target_scope}")

        # 鑾峰彇鎯呮劅鍜屽彲淇″害
        sentiment = knowledge_graph.get("sentiment", "中性")
        # 浣跨敤鍓嶉潰璁＄畻鐨?final_credibility
        credibility = final_credibility
        entity_count = len(knowledge_graph.get('entities', []))

        # 鏇存柊寮曟搸鐨勬柊闂诲拰鍥捐氨
        await _maybe_set_news(state.engine, req.content, req.source)

        # 鏇存柊寮曟搸鐨勭煡璇嗗浘璋憋紙铻嶅悎妯″紡锛?
        entities = knowledge_graph.get('entities', [])
        relations = knowledge_graph.get('relations', [])

        if hasattr(state.engine, 'set_knowledge_graph'):
            if entities:
                state.engine.set_knowledge_graph(entities, relations, merge=True)
                logger.info("知识图谱已融合，知识驱动演化已启用")
            else:
                # 绌哄疄浣撴椂浠嶆洿鏂板浘璋卞厓鏁版嵁锛堝 sentiment銆乧redibility_hint锛?
                if state.engine.knowledge_graph:
                    state.engine.knowledge_graph.update(knowledge_graph)
                else:
                    state.engine.knowledge_graph = knowledge_graph
                logger.info("知识图谱元数据已更新（无实体）")
        else:
            # 闄嶇骇锛氱洿鎺ヨ祴鍊?
            state.engine.knowledge_graph = knowledge_graph

        # 骞挎挱浜嬩欢锛堝寘鍚浘璋变俊鎭紝瑙﹀彂浜嬩欢鍐插嚮锛?
        event = state.engine.broadcast_event(
            content=req.content,
            target_scope=target_scope,
            sentiment=sentiment,
            credibility=credibility
        )
        # 杩斿洖铻嶅悎鍚庣殑鐭ヨ瘑鍥捐氨
        merged_graph = state.engine.knowledge_graph
        event["knowledge_graph"] = merged_graph
        event["event_msg"] = event_msg

        logger.info(f"[事件注入-完成] 事件注入成功，已广播给所有 Agent，图谱包含 {len(merged_graph.get('entities', []))} 个实体")

        return {
            "success": True,
            "data": {
                "event": event,
                "knowledge_graph": merged_graph,
                "event_msg": event_msg
            }
        }

    except Exception as e:
        logger.error(f"[绠＄嚎] 浜嬩欢娉ㄥ叆澶辫触: {e}")
        return JSONResponse(
            content={"success": False, "error": f"浜嬩欢娉ㄥ叆澶辫触: {str(e)}"},
            status_code=500
        )
    finally:
        # 鏃犺鎴愬姛澶辫触锛岄兘瑙ｉ櫎鎺ㄦ紨鏆傚仠
        state.injection_in_progress = False
        logger.info(f"[绠＄嚎] 浜嬩欢娉ㄥ叆缁撴潫锛屾帹婕斿彲鎭㈠")


@router.get("/knowledge-graph")
async def get_current_knowledge_graph():
    """
    鑾峰彇褰撳墠鎺ㄦ紨鐨勭煡璇嗗浘璋?
    """
    if state.engine is None:
        return JSONResponse(
            content={"success": False, "error": "鎺ㄦ紨寮曟搸鏈垵濮嬪寲"},
            status_code=400
        )

    return {
        "success": True,
        "data": state.engine.knowledge_graph
    }


@router.get("/hot-news")
async def get_hot_news():
    """使用 Tavily 抓取当天热点新闻，返回 10 条供前端一键注入。"""
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    from ..services.public_search import TavilySearchClient

    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

    def _clean_text(value: str) -> str:
        text = (value or "").strip()
        if not text:
            return ""
        text = text.replace("\r", " ").replace("\n", " ")
        text = " ".join(text.split())
        suspicious = ("â", "ä¸", "ï")
        if any(token in text for token in suspicious):
            try:
                repaired = text.encode("latin1", errors="ignore").decode("utf-8", errors="ignore").strip()
                if repaired:
                    text = repaired
            except Exception:
                pass
        return text

    api_key = os.getenv("TAVILY_API_KEY", "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").strip()
    client = TavilySearchClient(api_key=api_key, timeout=30)

    categories = [
        {
            "label": "政治",
            "queries": ["中国政治 政策 最新新闻", "China politics latest news"],
        },
        {
            "label": "经济",
            "queries": ["中国经济 产业 金融 最新新闻", "China economy finance latest news"],
        },
        {
            "label": "文化",
            "queries": ["中国文化 社会 教育 最新新闻", "China society education latest news"],
        },
        {
            "label": "国际",
            "queries": ["国际政治 经济 最新新闻", "world politics economy latest news"],
        },
    ]
    all_results = []

    for category in categories:
        try:
            results = await client.search_with_fallbacks(category["queries"], max_results=5)
            for r in results:
                title = _clean_text(r.title)
                content = _clean_text(r.content)[:500]
                if not title or not content:
                    continue
                all_results.append({
                    "title": title,
                    "content": content,
                    "url": r.url,
                    "source": _clean_text(getattr(r, "source", "") or "Tavily"),
                    "category": category["label"],
                })
        except Exception as e:
            logger.warning(f"Tavily search failed for '{category['label']}': {e}")

    seen = set()
    unique = []
    for item in all_results:
        title = item["title"]
        if title and title not in seen:
            seen.add(title)
            unique.append(item)

    return {"items": unique[:10]}


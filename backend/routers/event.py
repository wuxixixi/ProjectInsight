"""
浜嬩欢娉ㄥ叆璺敱
"""
import inspect
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .. import state
from ..helpers import AirdropRequest, ParseRequest
from ..llm.client import create_llm_config_from_env
from ..models.schemas import HotNewsResponse, NewsItem
from ..services.news_sources import (
    MAINSTREAM_DOMAINS,
    filter_mainstream,
)
from ..services.public_search import (
    TavilySearchClient,
    _aggregate_hot_news,
)

# Load .env once at import time so test code can monkey-patch ``load_dotenv``
# for the empty-API-key path. ``override=False`` ensures OS env vars win over
# the .env file.
load_dotenv(
    Path(__file__).resolve().parents[2] / ".env",
    override=False,
)


# ==================== AI 增强提示模型 ====================
class PromptEnhanceRequest(BaseModel):
    """AI 增强提示请求"""
    prompt: str  # 用户输入的原始提示词

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


@router.get("/hot-news", response_model=HotNewsResponse)
async def get_hot_news():
    """抓取当天**主流媒体**热点新闻，按跨 query 累加的相关度排序，返回 Top 8。

    来源治理（解决"来源不正"问题）：
    - 检索阶段通过 Tavily ``include_domains`` 把域名限定在主流媒体白名单
      （中央主要新闻单位 / 全国性权威媒体 / 国际主流通讯社），从源头排除
      采集站、山寨新闻站、百科词条、门户自媒体号与站点演示页。
    - ``topic=news`` + ``time_range=day`` + ``include_published_date`` 保证
      结果是有发布日期的当日新闻报道，而非旧文章或栏目索引页。
    - 结果阶段再做一次白名单校验（防御性兜底），并剔除站点首页。
    - 若 ``TAVILY_API_KEY`` 未配置或白名单内无结果，返回空 ``items`` +
      ``warning``，不抛 5xx，**也不降级到不可信来源**。
    - 应急开关：``HOT_NEWS_STRICT_SOURCES=0`` 可临时关闭限定（不建议生产使用）。
    """
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        logger.warning("[hot-news] TAVILY_API_KEY is not configured; returning empty items")
        return HotNewsResponse(
            items=[],
            total=0,
            generated_at=datetime.now(timezone.utc).isoformat(),
            warning="TAVILY_API_KEY 未配置，无法抓取热点新闻。请在 .env 中配置后重试。",
        )

    # 严格模式（默认）：检索与结果两层都锁定主流媒体白名单。
    strict = os.getenv("HOT_NEWS_STRICT_SOURCES", "1").strip().lower() not in (
        "0", "false", "no",
    )
    client = TavilySearchClient(
        api_key=api_key,
        timeout=30,
        include_domains=list(MAINSTREAM_DOMAINS) if strict else None,
        topic="news",
        time_range="day",
        include_published_date=True,
    )

    # 查询词聚焦"今日要闻/具体报道"，避免召回百科词条与新闻栏目索引页。
    # 每个分类保留中英双语 fallback（Tavily 偶发拒绝 CJK 密集查询）。
    categories = [
        {
            "label": "政治",
            "queries": ["今日时政要闻 政策发布 报道", "China politics policy news today"],
        },
        {
            "label": "经济",
            "queries": ["今日经济财经要闻 宏观 产业 报道", "China economy finance news today"],
        },
        {
            "label": "文化",
            "queries": ["今日社会 文化 教育 要闻 报道", "China society culture education news today"],
        },
        {
            "label": "国际",
            "queries": ["今日国际要闻 全球政治经济 报道", "world news today politics economy Reuters"],
        },
    ]

    per_category: list = []
    dropped = 0
    for category in categories:
        try:
            results = await client.search_with_fallbacks(
                category["queries"],
                max_results=5,
                search_depth="advanced",
                include_raw_content=True,
            )
            if results:
                # 二次校验：即使 API 返回越界域名，也不让非主流来源进入推演。
                trusted = filter_mainstream(results) if strict else list(results)
                dropped += len(results) - len(trusted)
                if trusted:
                    per_category.append((category["label"], trusted))
        except Exception as e:
            logger.warning(f"[hot-news] Tavily search failed for '{category['label']}': {e}")

    if dropped:
        logger.info(f"[hot-news] filtered out {dropped} non-mainstream / index-page results")

    if not per_category:
        # 全部失败或白名单内无结果：返回友好提示而不是 5xx，也绝不回退到
        # 不限定来源的搜索结果（那正是"来源不正"的根因）。
        return HotNewsResponse(
            items=[],
            total=0,
            generated_at=datetime.now(timezone.utc).isoformat(),
            warning=(
                "今日未检索到主流媒体来源的热点新闻，请稍后重试。"
                "系统仅收录新华社、人民日报、央视、澎湃、路透社等主流媒体当日报道。"
            ),
        )

    ranked_dicts = _aggregate_hot_news(per_category, top_n=8)
    items = [NewsItem(**d) for d in ranked_dicts]
    return HotNewsResponse(
        items=items,
        total=len(items),
        generated_at=datetime.now(timezone.utc).isoformat(),
        warning=None,
    )


@router.post("/enhance-prompt")
async def enhance_prompt_api(request: PromptEnhanceRequest):
    """
    AI 增强提示词
    
    使用大模型将用户简短的提示词扩写成详细、结构化的事件描述
    
    Request Body:
        prompt: 用户输入的原始提示词
    
    Response:
        enhanced_prompt: 增强后的详细提示词
        original_prompt: 原始提示词
    """
    if not request.prompt or not request.prompt.strip():
        return JSONResponse(
            content={"success": False, "error": "提示词不能为空"},
            status_code=400
        )
    
    try:
        logger.info(f"[AI 增强提示] 原始提示：{request.prompt[:100]}")
        
        # 构建增强提示的系统提示词
        system_prompt = """你是一位专业的信息场模拟事件策划助手。用户会输入一个简短的事件关键词或短语，
        你需要将其扩写成一段详细、具体、适合注入到信息场推演系统中的事件描述。
        
        扩写要求：
        1. 保持事件的核心主题不变
        2. 添加具体的时间、地点、涉及人物/组织
        3. 描述事件的发展过程和关键细节
        4. 包含可能产生的社会影响和争议点
        5. 语气客观中立，适合模拟推演
        6. 长度控制在 200-400 字之间
        
        示例：
        用户输入："AI 失业"
        你的输出："2026 年 3 月，某大型互联网公司宣布将裁减 30% 的客服人员，全面替换为 AI 聊天机器人。
        该决定引发社会广泛关注，支持者认为这是技术进步必然，反对者担忧大规模失业将冲击社会稳定。
        工会组织呼吁政府介入，要求制定 AI 替代人类的补偿机制。社交媒体上#AI 失业#话题热度飙升，
        形成支持与反对两大阵营的激烈辩论。"
        
        现在，请扩写以下用户输入："""
        
        # 调用 LLM 生成增强提示词
        from ..llm.client import LLMClient
        
        # 构建 OpenAI 格式的消息列表
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.prompt}
        ]
        
        # 使用 LLMClient 直接生成文本
        async with LLMClient() as client:
            response = await client.chat(
                messages=messages, max_tokens=800, temperature=0.7
            )
        
        # 从响应中提取内容（OpenAI 格式）
        enhanced_prompt = response["choices"][0]["message"]["content"].strip()
        
        # 如果生成内容过短，尝试重新生成
        if len(enhanced_prompt) < 50:
            system_prompt += "\n\n请确保输出足够详细，至少 200 字以上。"
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.prompt}
            ]
            async with LLMClient() as client:
                response = await client.chat(
                    messages=messages, max_tokens=800, temperature=0.7
                )
            enhanced_prompt = response["choices"][0]["message"]["content"].strip()
        
        logger.info(f"[AI 增强提示 v2] 增强成功，长度：{len(enhanced_prompt)} 字符")
        
        return {
            "success": True,
            "data": {
                "enhanced_prompt": enhanced_prompt,
                "original_prompt": request.prompt
            }
        }
        
    except Exception as e:
        logger.error(f"[AI 增强提示] 生成失败：{e}")
        return JSONResponse(
            content={"success": False, "error": f"AI 增强失败：{str(e)}"},
            status_code=500
        )


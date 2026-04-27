"""
知识图谱解析引擎
将长篇新闻文本解析为结构化的实体关系图谱
实现"解析-注入-推演"三段式管线的第一阶段
"""
import asyncio
import json
import logging
import os
import re
import threading
import urllib.request
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional
from ..llm.client import LLMClient, LLMConfig

logger = logging.getLogger(__name__)


# ==================== 知识图谱解析 Prompt 模板 ====================

GRAPH_PARSER_PROMPT = """你是一个专业的信息抽取专家，负责从突发事件文本中提取结构化知识图谱。
这个图谱将用于智能体的认知决策，因此需要准确、清晰、可操作。

## 任务目标
从新闻文本中提取：
1. 实体（entities）：参与事件的关键对象
2. 关系（relations）：实体之间的互动关系
3. 事件摘要（summary）：核心信息的精炼概括

## 实体类型规范
- 人物：事件的参与者（主角、受害者、发言人等）
- 组织：涉及的机构、公司、政府部门等
- 地点：事件发生的地理位置
- 事件：核心事件本身作为抽象实体
- 概念：关键议题（如"食品安全"、"财务造假"等）
- 时间：事件发生的时间节点（如"昨天"、"2024年1月"）

## 关系类型规范
- 参与：A参与了B事件
- 导致：A导致了B结果
- 对立：A与B立场对立
- 支持：A支持B的观点/行为
- 指控：A指控B做了某事
- 否认：A否认B的说法
- 影响：A影响B的状态/决策
- 关联：A与B有某种联系

## 输出格式（严格JSON）
请直接返回以下格式的JSON，不要添加任何其他文字：

```json
{{
  "entities": [
    {{"id": "e1", "name": "实体名称", "type": "人物|组织|地点|事件|概念|时间", "description": "简要描述", "importance": 1-5}}
  ],
  "relations": [
    {{"source": "e1", "target": "e2", "action": "关系动词", "type": "参与|导致|对立|支持|指控|否认|影响|关联", "description": "详细描述"}}
  ],
  "summary": "一句话概括核心内容（30字以内）",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "sentiment": "正面|负面|中性|争议",
  "credibility_hint": "高可信|低可信|不确定"
}}
```

## 新闻文本
{news_content}

请提取知识图谱："""


# ==================== GraphParserAgent 类 ====================

class GraphParserAgent:
    """
    知识图谱解析 Agent
    
    作为"解析-注入-推演"管线的第一阶段，
    专门调用 DeepSeek-V3 接口将突发事件文本解析为结构化图谱
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        """
        初始化图谱解析 Agent

        Args:
            llm_config: LLM 配置，如果为 None 则使用优先级客户端
        """
        if llm_config is None:
            # 使用高优先级客户端，不受推演并发池影响
            from ..llm.client import create_priority_llm_client
            self._priority_client = create_priority_llm_client()
            self.llm_config = self._priority_client.config
        else:
            self._priority_client = None
            self.llm_config = llm_config
        self.llm_config.max_tokens = 2000
        self.llm_config.temperature = 0.2  # 更低温度以获得稳定JSON输出

    async def parse(self, news_content: str) -> Dict[str, Any]:
        """
        解析新闻文本为知识图谱

        这是管线的核心步骤，输入长文本，输出结构化JSON图谱

        Args:
            news_content: 新闻文本内容

        Returns:
            包含 entities, relations, summary, keywords, sentiment 的字典
        """
        if not news_content or not news_content.strip():
            return self._get_empty_graph()

        if not self._llm_is_available():
            logger.warning("LLM config unavailable for graph parsing, fallback to default graph")
            return self._get_enhanced_default_graph(news_content)

        prompt = GRAPH_PARSER_PROMPT.format(news_content=news_content.strip())

        try:
            # 使用优先级客户端（如有）或创建临时客户端
            if self._priority_client:
                llm_client = self._priority_client
                async with llm_client:
                    response = await llm_client.chat([{"role": "user", "content": prompt}])
            else:
                llm_client = LLMClient(self.llm_config)
                async with llm_client:
                    response = await llm_client.chat([{"role": "user", "content": prompt}])

            # 从 API 响应中提取内容
            content = self._extract_response_content(response)

            if not content:
                logger.warning("LLM 响应内容为空，返回默认图谱")
                return self._get_enhanced_default_graph(news_content)

            # 尝试解析 JSON
            graph_data = self._extract_json(content)

            if graph_data and self._validate_graph(graph_data):
                # 规范化图谱数据
                graph_data = self._normalize_graph(graph_data)
                logger.info(f"知识图谱解析成功: {len(graph_data.get('entities', []))} 个实体, {len(graph_data.get('relations', []))} 个关系")
                return graph_data
            else:
                logger.warning(f"知识图谱解析失败或数据不完整，LLM响应前200字符: {content[:200] if content else 'None'}")
                return self._get_enhanced_default_graph(news_content)

        except asyncio.TimeoutError:
            logger.error(f"知识图谱解析超时（{self.llm_config.timeout}秒），新闻前50字: {news_content[:50]}")
            return {
                "entities": [{"id": "e1", "name": "解析超时", "type": "其他", "description": f"LLM调用超时{self.llm_config.timeout}秒", "importance": 1}],
                "relations": [],
                "summary": news_content[:100] if len(news_content) > 100 else news_content,
                "keywords": [],
                "sentiment": "不确定",
                "credibility_hint": "不确定",
                "parse_error": True,
                "error_message": f"LLM调用超时{self.llm_config.timeout}秒"
            }
        except Exception as e:
            # LLM 客户端会将 asyncio.TimeoutError 转为普通 Exception
            error_msg = str(e)
            if "超时" in error_msg or "timeout" in error_msg.lower():
                logger.error(f"知识图谱解析超时: {error_msg}")
                return {
                    "entities": [{"id": "e1", "name": "解析超时", "type": "其他", "description": f"LLM调用超时", "importance": 1}],
                    "relations": [],
                    "summary": news_content[:100] if len(news_content) > 100 else news_content,
                    "keywords": [],
                    "sentiment": "不确定",
                    "credibility_hint": "不确定",
                    "parse_error": True,
                    "error_message": error_msg
                }
            else:
                logger.error(f"知识图谱解析错误: {type(e).__name__}: {e}")
                return {
                    "entities": [{"id": "e1", "name": "解析异常", "type": "其他", "description": str(e)[:100], "importance": 1}],
                    "relations": [],
                    "summary": news_content[:100] if len(news_content) > 100 else news_content,
                    "keywords": [],
                    "sentiment": "不确定",
                    "credibility_hint": "不确定",
                    "parse_error": True,
                    "error_type": type(e).__name__
                }

    def _llm_is_available(self) -> bool:
        """Avoid long parser waits when no LLM endpoint is configured locally."""
        base_url = (self.llm_config.base_url or "").strip()
        api_key = (self.llm_config.api_key or "").strip()
        if not base_url:
            return False
        if "localhost" in base_url or "127.0.0.1" in base_url or "::1" in base_url:
            return True
        if not (api_key or os.getenv("OPENAI_API_KEY", "").strip()):
            return False
        return self._probe_base_url(base_url)

    def _probe_base_url(self, base_url: str) -> bool:
        """Use a tiny blocking probe to avoid waiting a full request timeout on dead endpoints."""
        try:
            parsed = urlparse(base_url)
            if not parsed.scheme or not parsed.netloc:
                return False
            probe_url = f"{parsed.scheme}://{parsed.netloc}"
            request = urllib.request.Request(probe_url, method="HEAD")
            with urllib.request.urlopen(request, timeout=1.5) as response:
                return response.status < 500
        except Exception:
            return False

    def _extract_response_content(self, response: Any) -> str:
        """
        从 LLM API 响应中提取文本内容
        """
        content = ""
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "")
        elif isinstance(response, str):
            content = response
        return content

    def _validate_graph(self, graph_data: Dict[str, Any]) -> bool:
        """
        验证图谱数据结构是否完整
        """
        if not isinstance(graph_data, dict):
            return False
        if "entities" not in graph_data or "relations" not in graph_data:
            return False
        if not isinstance(graph_data["entities"], list):
            return False
        # 至少需要有一个实体
        if len(graph_data["entities"]) == 0:
            return False
        return True

    def _normalize_graph(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        规范化图谱数据，确保所有字段存在且格式正确
        """
        # 确保实体有id
        for i, entity in enumerate(graph_data.get("entities", [])):
            if "id" not in entity:
                entity["id"] = f"e{i+1}"
            if "importance" not in entity:
                entity["importance"] = 3
            if "type" not in entity:
                entity["type"] = "其他"
            if "description" not in entity:
                entity["description"] = entity.get("name", "未知实体")

        # 确保关系引用有效实体
        valid_entity_ids = {e["id"] for e in graph_data.get("entities", [])}
        valid_relations = []
        for relation in graph_data.get("relations", []):
            # 如果source/target不是实体id而是实体名称，尝试匹配
            if relation.get("source") not in valid_entity_ids:
                for entity in graph_data.get("entities", []):
                    if entity.get("name") == relation.get("source"):
                        relation["source"] = entity["id"]
                        break
            if relation.get("target") not in valid_entity_ids:
                for entity in graph_data.get("entities", []):
                    if entity.get("name") == relation.get("target"):
                        relation["target"] = entity["id"]
                        break
            # 只保留有效的关系
            if relation.get("source") in valid_entity_ids and relation.get("target") in valid_entity_ids:
                valid_relations.append(relation)
        
        graph_data["relations"] = valid_relations

        # 确保其他字段存在
        if "summary" not in graph_data:
            graph_data["summary"] = "事件信息待分析"
        if "keywords" not in graph_data:
            graph_data["keywords"] = [e.get("name", "") for e in graph_data.get("entities", [])[:3]]
        if "sentiment" not in graph_data:
            graph_data["sentiment"] = "中性"
        if "credibility_hint" not in graph_data:
            graph_data["credibility_hint"] = "不确定"

        return graph_data

    def _extract_json(self, response: str) -> Optional[Dict[str, Any]]:
        """
        从 LLM 响应中提取 JSON

        复用 LLMClient._parse_json_content 方法

        Args:
            response: LLM 响应文本

        Returns:
            解析后的字典，或 None
        """
        if not response:
            return None

        # 创建临时 LLMClient 实例以复用其 _parse_json_content 方法
        temp_client = LLMClient()
        result = temp_client._parse_json_content(response)

        # 检查是否解析成功（失败时返回 {"raw_content": ...}）
        if "raw_content" in result and len(result) == 1:
            return None
        return result

    def _get_empty_graph(self) -> Dict[str, Any]:
        """
        返回空图谱结构（输入为空时使用）
        """
        return {
            "entities": [],
            "relations": [],
            "summary": "",
            "keywords": [],
            "sentiment": "中性",
            "credibility_hint": "不确定"
        }

    def _get_enhanced_default_graph(self, news_content: str) -> Dict[str, Any]:
        """
        获取增强版默认图谱结构（解析失败时使用）
        尝试从文本中提取一些基本信息

        Args:
            news_content: 新闻文本

        Returns:
            默认图谱结构
        """
        # 提取摘要
        sentences = news_content.replace('\n', ' ').split('。')
        summary = sentences[0][:50] + '...' if sentences and len(sentences[0]) > 50 else (sentences[0] if sentences else news_content[:50])

        # 尝试提取一些关键词（简单规则）
        keywords = []
        # 提取引号内容
        quotes = re.findall(r'["「『]([^"」』]+)["」』]', news_content)
        keywords.extend(quotes[:3])
        # 提取可能的组织名
        orgs = re.findall(r'[\u4e00-\u9fa5]{2,6}(?:公司|集团|银行|政府|部门|机构)', news_content)
        keywords.extend(orgs[:2])
        
        # 构建默认实体
        entities = [{"id": "e1", "name": "未知事件", "type": "事件", "description": summary, "importance": 5}]
        if keywords:
            for i, kw in enumerate(keywords[:3]):
                entities.append({"id": f"e{i+2}", "name": kw, "type": "概念", "description": f"关键词：{kw}", "importance": 3})

        return {
            "entities": entities,
            "relations": [],
            "summary": summary,
            "keywords": keywords[:5],
            "sentiment": "争议",
            "credibility_hint": "不确定",
            "parse_error": True
        }

    def _get_default_graph(self, news_content: str) -> Dict[str, Any]:
        """向后兼容的旧方法"""
        return self._get_enhanced_default_graph(news_content)


# ==================== 全局单例 ====================

_graph_parser_instance: Optional[GraphParserAgent] = None
_graph_parser_lock = threading.Lock()


def get_graph_parser(llm_config: Optional[LLMConfig] = None) -> GraphParserAgent:
    """
    获取全局 GraphParserAgent 实例（线程安全）

    Args:
        llm_config: LLM 配置

    Returns:
        GraphParserAgent 实例
    """
    global _graph_parser_instance
    if _graph_parser_instance is None:
        with _graph_parser_lock:
            if _graph_parser_instance is None:
                _graph_parser_instance = GraphParserAgent(llm_config)
    return _graph_parser_instance


def reset_graph_parser():
    """重置全局单例（用于测试）"""
    global _graph_parser_instance
    with _graph_parser_lock:
        _graph_parser_instance = None

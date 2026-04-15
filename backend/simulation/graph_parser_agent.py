"""
知识图谱解析引擎
将长篇新闻文本解析为结构化的实体关系图谱
"""
import json
import logging
from typing import Dict, List, Any, Optional
from ..llm.client import LLMClient, LLMConfig

logger = logging.getLogger(__name__)


# 知识图谱解析 Prompt 模板
GRAPH_PARSER_PROMPT = """你是一个信息抽取专家。请从以下新闻文本中提取结构化的知识图谱。

要求：
1. 提取所有关键实体（人物、组织、地点、事件、概念等）
2. 提取实体之间的关系（source: 主体, target: 客体, action: 关系描述）
3. 识别事件的参与者、时间、地点等要素
4. 如果信息不明确，使用"未知"或"不确定"

请直接返回 JSON 格式（不要其他文字）：
{{
  "entities": [
    {{"name": "实体名称", "type": "人物/组织/地点/事件/概念/其他", "description": "简要描述"}}
  ],
  "relations": [
    {{"source": "实体1", "target": "实体2", "action": "关系描述", "type": "关联/对立/影响/参与"}}
  ],
  "summary": "用一句话概括这篇新闻的核心内容"
}}

新闻文本：
{news_content}

请提取知识图谱："""


class GraphParserAgent:
    """
    知识图谱解析 Agent
    用于将长篇新闻文本解析为结构化的实体关系图谱
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        """
        初始化图谱解析 Agent

        Args:
            llm_config: LLM 配置，如果为 None 则使用默认配置
        """
        self.llm_config = llm_config or LLMConfig()
        self.llm_config.max_tokens = 2000
        self.llm_config.temperature = 0.3  # 较低温度以获得更稳定的JSON输出

    async def parse(self, news_content: str) -> Dict[str, Any]:
        """
        解析新闻文本为知识图谱

        Args:
            news_content: 新闻文本内容

        Returns:
            包含 entities, relations, summary 的字典
        """
        prompt = GRAPH_PARSER_PROMPT.format(news_content=news_content)
        
        try:
            llm_client = LLMClient(self.llm_config)
            async with llm_client:
                response = await llm_client.chat([{"role": "user", "content": prompt}])
            
            # 从 API 响应中提取内容
            content = ""
            if isinstance(response, dict):
                choices = response.get("choices", [])
                if choices:
                    message_content = choices[0].get("message", {}).get("content", "")
                    # 处理可能的嵌套 JSON 字符串
                    if isinstance(message_content, str):
                        # 尝试解析嵌套的 JSON
                        try:
                            nested = json.loads(message_content)
                            if isinstance(nested, dict) and "entities" in nested:
                                # 返回嵌套的 JSON
                                return nested
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.debug(f"嵌套JSON解析失败: {e}")
                    content = message_content
            else:
                content = str(response)
            
            # 尝试解析 JSON
            graph_data = self._extract_json(content)
            
            if graph_data:
                logger.info(f"知识图谱解析成功: {len(graph_data.get('entities', []))} 个实体, {len(graph_data.get('relations', []))} 个关系")
                return graph_data
            else:
                logger.warning("知识图谱解析失败，返回默认结构")
                return self._get_default_graph(news_content)
                
        except Exception as e:
            logger.error(f"知识图谱解析错误: {e}")
            # 返回一个简单的摘要而不是空
            return {
                "entities": [{"name": "解析失败", "type": "其他", "description": str(e)}],
                "relations": [],
                "summary": news_content[:200] if len(news_content) > 200 else news_content,
                "parse_error": True
            }

    def _extract_json(self, response: str) -> Optional[Dict[str, Any]]:
        """
        从 LLM 响应中提取 JSON

        Args:
            response: LLM 响应文本

        Returns:
            解析后的字典，或 None
        """
        # 尝试找到 JSON 块
        import re

        # 方法1: 尝试直接解析整个响应
        if response:
            try:
                return json.loads(response)
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"JSON直接解析失败: {e}")

        # 方法2: 尝试找到 ```json ... ``` 块
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response or "")
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"json代码块解析失败: {e}")

        # 方法3: 尝试找到 ``` ... ``` 块（不带json标签）
        json_match = re.search(r'```\s*([\s\S]*?)\s*```', response or "")
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                if isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"代码块解析失败: {e}")

        # 方法4: 尝试找到 { ... } 块
        brace_match = re.search(r'\{[\s\S]*\}', response or "")
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"花括号块解析失败: {e}")

        # 方法5: 尝试找到 "content": "..." 中的 JSON 字符串
        content_match = re.search(r'"content"\s*:\s*"([\s\S]*?)"', response or "")
        if content_match:
            try:
                # 解码转义字符
                content = content_match.group(1).replace('\\n', '\n').replace('\\"', '"')
                return json.loads(content)
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"content字段解析失败: {e}")

        return None

    def _get_default_graph(self, news_content: str) -> Dict[str, Any]:
        """
        获取默认图谱结构（解析失败时使用）

        Args:
            news_content: 新闻文本

        Returns:
            默认图谱结构
        """
        # 简单提取前几个句子作为摘要
        sentences = news_content.split('。')
        summary = sentences[0] + '。' if sentences else news_content[:100]
        
        return {
            "entities": [
                {"name": "新闻事件", "type": "事件", "description": summary}
            ],
            "relations": [],
            "summary": summary,
            "parse_error": True
        }


# 全局单例
_graph_parser_instance: Optional[GraphParserAgent] = None


def get_graph_parser(llm_config: Optional[LLMConfig] = None) -> GraphParserAgent:
    """
    获取全局 GraphParserAgent 实例

    Args:
        llm_config: LLM 配置

    Returns:
        GraphParserAgent 实例
    """
    global _graph_parser_instance
    if _graph_parser_instance is None:
        _graph_parser_instance = GraphParserAgent(llm_config)
    return _graph_parser_instance

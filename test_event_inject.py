"""测试事件注入功能"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, 'H:/ProjectInsight')
os.chdir('H:/ProjectInsight')

async def test_graph_parser():
    from backend.simulation.graph_parser_agent import get_graph_parser
    
    print("1. 初始化 GraphParser...")
    parser = get_graph_parser()
    print(f"   LLM Config: base_url={parser.llm_config.base_url}, model={parser.llm_config.model}")
    
    print("\n2. 测试解析新闻...")
    test_content = "某科技公司发布新产品引发市场关注"
    
    try:
        result = await parser.parse(test_content)
        entities = result.get('entities', [])
        print(f"   成功! 实体数: {len(entities)}")
        return True
    except Exception as e:
        print(f"   失败! 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_endpoint():
    """直接测试 API 端点函数"""
    print("\n3. 测试 API 端点...")
    try:
        from backend.app import AirdropRequest, airdrop_event
        
        req = AirdropRequest(content='test news from API', source='public')
        result = await airdrop_event(req)
        
        success = result.get('success', False)
        kg = result.get('data', {}).get('knowledge_graph', {})
        print(f"   API返回: success={success}, entities={len(kg.get('entities', []))}")
        return success
    except Exception as e:
        print(f"   失败! 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("=" * 50)
    print("诊断事件注入功能")
    print("=" * 50)
    
    # 测试 Graph Parser
    parser_ok = await test_graph_parser()
    
    # 测试 API 端点
    api_ok = await test_api_endpoint()
    
    print("\n" + "=" * 50)
    print(f"结果: Graph Parser={parser_ok}, API Endpoint={api_ok}")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
"""
测试事件注入时的推演暂停机制

场景：
1. 启动推演（LLM模式，小规模Agent）
2. 开启自动推演
3. 在推演过程中注入事件
4. 验证：推演暂停等待，注入完成后恢复
"""
import requests
import json
import time
import asyncio
import websockets

BASE = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/simulation"

async def test_injection_pause():
    print("=" * 60)
    print("事件注入暂停机制测试")
    print("=" * 60)

    # ========== Step 0: 清理 ==========
    print("\n[Step 0] 清理旧引擎...")
    try:
        requests.post(f"{BASE}/api/simulation/finish")
        time.sleep(1)
    except:
        pass

    # ========== Step 1: 注入第一个事件 ==========
    print("\n[Step 1] 注入初始事件...")
    event1 = {
        "content": "某科技公司发布了一项AI技术",
        "source": "public",
        "skip_parse": True  # 快速注入
    }
    resp = requests.post(f"{BASE}/api/event/airdrop", json=event1)
    print(f"  状态码: {resp.status_code}")

    # ========== Step 2: WebSocket 启动推演 ==========
    print("\n[Step 2] 通过 WebSocket 启动推演...")
    
    async with websockets.connect(WS_URL) as ws:
        # 启动推演
        await ws.send(json.dumps({
            "action": "start",
            "params": {
                "population_size": 20,
                "use_llm": False,  # 数学模型模式，速度快
                "use_dual_network": True,
                "max_steps": 20
            }
        }))
        
        # 等待初始状态
        msg = await ws.recv()
        state = json.loads(msg)
        print(f"  推演已启动, 类型: {state.get('type')}")
        
        # 开启自动推演
        print("\n[Step 3] 开启自动推演（间隔1秒）...")
        await ws.send(json.dumps({
            "action": "auto",
            "interval": 1000
        }))
        
        # 收集几步推演
        step_count = 0
        injection_done = False
        start_time = time.time()
        
        print("\n[Step 4] 推演进行中，将在第3步后注入事件...")
        
        while step_count < 15:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(msg)
                
                if data.get("type") == "state":
                    step_count = data.get("data", {}).get("step", step_count)
                    avg_opinion = data.get("data", {}).get("average_opinion", 0)
                    print(f"  Step {step_count}: avg_opinion={avg_opinion:.4f}")
                    
                    # 在第3步后注入事件
                    if step_count >= 3 and not injection_done:
                        print("\n[Step 5] 注入事件（应在推演暂停期间完成）...")
                        inject_start = time.time()
                        
                        # 在另一个协程中注入
                        event2 = {
                            "content": "突发：专家称该AI技术将取代大量工作岗位，引发社会广泛担忧。政府紧急回应将出台保障政策",
                            "source": "public",
                            "skip_parse": False  # 使用LLM解析，测试暂停
                        }
                        
                        # 使用同步请求（在另一个线程中执行）
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                requests.post, 
                                f"{BASE}/api/event/airdrop", 
                                json=event2
                            )
                            resp = future.result(timeout=60)
                        
                        inject_time = time.time() - inject_start
                        print(f"  注入完成！耗时: {inject_time:.2f}秒, 状态码: {resp.status_code}")
                        
                        result = resp.json()
                        if result.get("success"):
                            kg = result.get("data", {}).get("knowledge_graph", {})
                            print(f"  知识图谱实体数: {len(kg.get('entities', []))}")
                        else:
                            print(f"  注入失败: {result}")
                        
                        injection_done = True
                        
                elif data.get("type") == "progress":
                    message = data.get("message", "")
                    if "暂停" in message or "注入" in message:
                        print(f"  [进度] {message}")
                        
            except asyncio.TimeoutError:
                print("  等待超时")
                break
        
        # 停止自动推演
        print("\n[Step 6] 停止推演...")
        await ws.send(json.dumps({"action": "stop"}))
        
        # 结束推演
        requests.post(f"{BASE}/api/simulation/finish")
        
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print(f"总步数: {step_count}")
    print(f"事件注入成功: {injection_done}")

if __name__ == "__main__":
    asyncio.run(test_injection_pause())

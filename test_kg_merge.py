"""
测试知识图谱融合功能

场景：
1. 启动推演（注入第一个事件）
2. 获取知识图谱
3. 推演几步
4. 注入第二个事件（触发融合）
5. 验证融合结果
"""
import requests
import json
import time

BASE = "http://localhost:8000"

def test_merge():
    print("=" * 60)
    print("知识图谱融合功能测试")
    print("=" * 60)

    # ========== Step 0: 清理 ==========
    print("\n[Step 0] 清理旧引擎...")
    try:
        requests.post(f"{BASE}/api/simulation/finish")
        time.sleep(1)
    except:
        pass

    # ========== Step 1: 先注入第一个事件（会设为pending）==========
    print("\n[Step 1] 注入第一个事件...")
    # 使用 LLM 解析，获取真实的知识图谱
    event1 = {
        "content": "权威专家张教授发表声明，认为某AI技术将在3年内取代50%的白领工作，引发社会广泛担忧。张教授是人工智能领域的知名学者。",
        "source": "public",
        "skip_parse": False  # 使用LLM解析
    }
    resp = requests.post(f"{BASE}/api/event/airdrop", json=event1)
    print(f"  状态码: {resp.status_code}")
    if resp.status_code != 200:
        print(f"  错误: {resp.text[:500]}")
        return

    result1 = resp.json()
    data1 = result1.get("data", {})
    kg1 = data1.get("knowledge_graph", {})
    entities1_pending = kg1.get("entities", [])
    relations1_pending = kg1.get("relations", [])
    print(f"  事件已暂存（pending）")
    print(f"  解析出实体数: {len(entities1_pending)}")
    print(f"  解析出关系数: {len(relations1_pending)}")

    # ========== Step 2: 启动推演（会自动注入pending事件）==========
    print("\n[Step 2] 启动推演...")
    resp = requests.post(f"{BASE}/api/simulation/start", json={
        "population_size": 30,
        "network_type": "small_world",
        "use_llm": False,  # 数学模型模式，速度快
        "use_dual_network": True
    })
    print(f"  状态码: {resp.status_code}")
    if resp.status_code != 200:
        print(f"  错误: {resp.text[:300]}")
        return
    init_data = resp.json()
    print(f"  推演启动成功, Agent数: {init_data.get('population_size', 'N/A')}")

    # ========== Step 3: 获取第一个知识图谱 ==========
    print("\n[Step 3] 获取当前知识图谱...")
    resp = requests.get(f"{BASE}/api/event/knowledge-graph")
    if resp.status_code == 200:
        kg_data = resp.json()
        kg = kg_data.get("data", kg_data)
        entities = kg.get("entities", [])
        relations = kg.get("relations", [])
        print(f"  实体数: {len(entities)}")
        for e in entities:
            print(f"    - {e.get('id')} {e.get('name')} ({e.get('type')}, importance={e.get('importance')})")
        print(f"  关系数: {len(relations)}")
        for r in relations:
            print(f"    - {r.get('source')} --[{r.get('action')}]--> {r.get('target')}")
    else:
        print(f"  获取图谱失败 (状态码: {resp.status_code})")
        entities = []
        relations = []

    entity_names_1 = {e.get("name") for e in entities}
    relation_count_1 = len(relations)
    entity_count_1 = len(entities)

    # ========== Step 4: 推演几步 ==========
    print("\n[Step 4] 推演3步...")
    for i in range(3):
        resp = requests.get(f"{BASE}/api/simulation/step")
        if resp.status_code == 200:
            state = resp.json()
            avg = state.get('average_opinion', 0)
            print(f"  Step {i+1}: avg_opinion={avg:.4f}" if isinstance(avg, (int, float)) else f"  Step {i+1}: done")
        time.sleep(0.2)

    # ========== Step 5: 注入第二个事件（应触发融合）==========
    print("\n[Step 5] 注入第二个事件（应与第一个图谱融合）...")
    # 使用LLM解析，确保有足够的实体和关系
    event2 = {
        "content": "科技公司CEO李明回应称，AI技术将创造更多新岗位，不会大规模取代人类工作。李明表示公司已投入10亿元用于员工转型培训。同时政府宣布将出台AI就业保障政策，保护劳动者权益。张教授对此回应称需要更多时间观察。",
        "source": "public",
        "skip_parse": False  # 使用LLM解析
    }
    resp = requests.post(f"{BASE}/api/event/airdrop", json=event2)
    print(f"  状态码: {resp.status_code}")
    if resp.status_code != 200:
        print(f"  错误: {resp.text[:500]}")
        return

    result2 = resp.json()
    data2 = result2.get("data", {})
    kg2_injected = data2.get("knowledge_graph", {})
    print(f"  第二事件注入成功")

    # ========== Step 6: 获取融合后的知识图谱 ==========
    print("\n[Step 6] 获取融合后的知识图谱...")
    resp = requests.get(f"{BASE}/api/event/knowledge-graph")
    if resp.status_code == 200:
        kg_data = resp.json()
        kg2 = kg_data.get("data", kg_data)
        entities2 = kg2.get("entities", [])
        relations2 = kg2.get("relations", [])
        print(f"  融合后实体数: {len(entities2)}")
        for e in entities2:
            print(f"    - {e.get('id')} {e.get('name')} ({e.get('type')}, importance={e.get('importance')})")
        print(f"  融合后关系数: {len(relations2)}")
        for r in relations2:
            print(f"    - {r.get('source')} --[{r.get('action')}]--> {r.get('target')}")
    else:
        print(f"  获取失败 (状态码: {resp.status_code})")
        entities2 = []
        relations2 = []

    # ========== Step 7: 验证融合结果 ==========
    print("\n" + "=" * 60)
    print("验证融合结果")
    print("=" * 60)

    entity_names_2 = {e.get("name") for e in entities2}

    # 检查1: 融合后实体数 >= 第一次
    if len(entities2) >= entity_count_1:
        print(f"  ✅ 融合后实体数 ({len(entities2)}) >= 第一次 ({entity_count_1})")
    else:
        print(f"  ❌ 融合后实体数 ({len(entities2)}) < 第一次 ({entity_count_1})，融合可能失败！")

    # 检查2: 第一次的实体应该保留
    lost = entity_names_1 - entity_names_2
    if not lost:
        print(f"  ✅ 第一个图谱的所有实体都已保留")
    else:
        print(f"  ❌ 丢失实体: {lost}")

    # 检查3: 第二个事件应该带来新实体
    new_entities = entity_names_2 - entity_names_1
    if new_entities:
        print(f"  ✅ 第二个事件带来 {len(new_entities)} 个新实体: {new_entities}")
    else:
        print(f"  ⚠️ 没有新实体（可能事件实体完全重叠）")

    # 检查4: 关系数应该增长或持平
    if len(relations2) >= relation_count_1:
        print(f"  ✅ 融合后关系数 ({len(relations2)}) >= 第一次 ({relation_count_1})")
    else:
        print(f"  ❌ 融合后关系数 ({len(relations2)}) < 第一次 ({relation_count_1})，关系可能丢失！")

    # 检查5: 关系中的 source/target 应该是名称而非纯 ID
    id_pattern_count = 0
    for r in relations2:
        src = r.get("source", "")
        tgt = r.get("target", "")
        if src.startswith("e") and src[1:].isdigit():
            id_pattern_count += 1
        if tgt.startswith("e") and tgt[1:].isdigit():
            id_pattern_count += 1
    if id_pattern_count == 0:
        print(f"  ✅ 所有关系的 source/target 都是名称格式")
    else:
        print(f"  ⚠️ 有 {id_pattern_count} 个关系字段仍然是 ID 格式")

    # 检查6: 实体ID连续且无冲突
    ids = [e.get("id", "") for e in entities2]
    id_nums = []
    for eid in ids:
        if eid.startswith("e") and eid[1:].isdigit():
            id_nums.append(int(eid[1:]))
    if id_nums and max(id_nums) == len(id_nums) and len(set(id_nums)) == len(id_nums):
        print(f"  ✅ 实体ID编号连续且无冲突 (e1~e{max(id_nums)})")
    else:
        print(f"  ⚠️ 实体ID可能存在问题: {ids}")

    # 检查7: 同名实体描述合并（如果张教授出现在两个事件中）
    merged_desc_found = False
    for e in entities2:
        name = e.get("name", "")
        desc = e.get("description", "")
        if "张教授" in name and "；" in desc:
            print(f"  ✅ 实体 [{name}] 的描述已合并: {desc[:100]}...")
            merged_desc_found = True
            break
    if not merged_desc_found:
        print(f"  ℹ️ 没有同名实体的描述需要合并（或张教授未同时出现在两个事件中）")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

    # 清理
    try:
        requests.post(f"{BASE}/api/simulation/finish")
    except:
        pass

if __name__ == "__main__":
    test_merge()

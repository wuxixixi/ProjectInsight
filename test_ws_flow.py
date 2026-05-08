"""Test the full simulation flow via WebSocket (mimicking the frontend)."""
import asyncio
import json
import websockets
import httpx

API = "http://localhost:8000"
WS = "ws://localhost:8000/ws/simulation"

async def main():
    # Step 1: Inject a pending event via REST
    print("=== Step 1: Inject event via REST ===")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{API}/api/event/airdrop", json={
            "content": "某研究所发生数据泄露事件，涉及大量敏感信息",
            "source": "public",
            "skip_parse": True,
            "credibility": "低可信"
        })
        print(f"  Status: {resp.status_code}")
        print(f"  Body: {resp.text[:500]}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  success={data.get('success')}")

    # Step 2: Connect WebSocket and start simulation
    print("\n=== Step 2: WebSocket start simulation ===")
    async with websockets.connect(WS) as ws:
        start_msg = {
            "action": "start",
            "params": {
                "mode": "news",
                "cocoon_strength": 0.5,
                "debunk_delay": 10,
                "initial_rumor_spread": 0.3,
                "use_llm": True,
                "population_size": 27,
                "population_profile_id": "shass_news_institute",
                "refresh_realistic_profile": False,
                "network_type": "small_world",
                "max_steps": 5,
                "max_concurrent": 13,
                "connection_pool_size": 600,
                "timeout": 60,
                "max_retries": 5,
                "use_dual_network": True,
                "num_communities": 8,
                "public_m": 3,
                "init_distribution": {
                    "believe_rumor": 0.25,
                    "believe_truth": 0.15,
                    "neutral": 0.6
                }
            }
        }
        print(f"  Sending start message...")
        await ws.send(json.dumps(start_msg))

        try:
            response = await asyncio.wait_for(ws.recv(), timeout=30)
            msg = json.loads(response)
            print(f"  Response type: {msg.get('type')}")
            if msg.get('type') == 'state':
                data = msg['data']
                print(f"  Step: {data.get('step')}, Agents: {len(data.get('agents', []))}")
                print(f"  opinion_distribution keys: {list(data.get('opinion_distribution', {}).keys()) if data.get('opinion_distribution') else 'MISSING'}")
                print(f"  mislead_rate: {data.get('mislead_rate')}")
                print(f"  news_credibility: {data.get('news_credibility')}")
            elif msg.get('type') == 'error':
                print(f"  ERROR: {msg.get('message')}")
        except asyncio.TimeoutError:
            print("  TIMEOUT waiting for response!")

        # Step 3: Send auto step
        print("\n=== Step 3: Auto step ===")
        await ws.send(json.dumps({"action": "auto", "interval": 2000}))

        for i in range(8):
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=15)
                msg = json.loads(response)
                t = msg.get('type')
                if t == 'state':
                    d = msg['data']
                    od = d.get('opinion_distribution', {})
                    print(f"  [{i}] state: step={d.get('step')}, agents={len(d.get('agents',[]))}, od_counts={len(od.get('counts',[])) if od else 'NULL'}")
                elif t == 'progress':
                    print(f"  [{i}] progress: {msg.get('step')}/{msg.get('total')}")
                elif t == 'error':
                    print(f"  [{i}] ERROR: {msg.get('message')}")
                else:
                    print(f"  [{i}] {t}")
            except asyncio.TimeoutError:
                print(f"  [{i}] TIMEOUT")
                break

        await ws.send(json.dumps({"action": "stop"}))
        print("\n=== Done ===")

asyncio.run(main())

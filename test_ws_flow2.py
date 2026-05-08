"""Test: inject event then start via WebSocket."""
import asyncio
import json
import httpx
import websockets

API = "http://localhost:8000"
WS = "ws://localhost:8000/ws/simulation"

async def main():
    # 1. Inject event via REST (before simulation starts)
    print("=== 1. Inject event (engine should be None) ===")
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{API}/api/event/airdrop", json={
                "content": "某研究所数据泄露",
                "source": "public",
                "skip_parse": True,
                "credibility": "低可信"
            })
            data = resp.json()
            pending = data.get("data", {}).get("event", {}).get("pending", False)
            print(f"  Status: {resp.status_code}, success: {data.get('success')}, pending: {pending}")
        except Exception as e:
            print(f"  REST Error: {e}")
            return

    # 2. Start via WebSocket
    print("\n=== 2. Start simulation via WebSocket ===")
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
                "max_steps": 3,
                "max_concurrent": 13,
                "connection_pool_size": 600,
                "timeout": 60,
                "max_retries": 5,
                "use_dual_network": True,
                "num_communities": 8,
                "public_m": 3,
                "init_distribution": None
            }
        }
        await ws.send(json.dumps(start_msg))

        # Wait for initial state
        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=30)
            msg = json.loads(resp)
            if msg.get('type') == 'state':
                d = msg['data']
                nc = d.get('news_credibility', '?')
                print(f"  State: step={d.get('step')}, agents={len(d.get('agents',[]))}, credibility={nc}")
                print(f"  opinionDist: {d.get('opinion_distribution') is not None}")
                print(f"  mislead_rate: {d.get('mislead_rate')}")
            elif msg.get('type') == 'error':
                print(f"  ERROR: {msg.get('message')}")
        except asyncio.TimeoutError:
            print("  TIMEOUT")

        # 3. Run auto steps
        print("\n=== 3. Auto step ===")
        await ws.send(json.dumps({"action": "auto", "interval": 1500}))

        got_state = False
        for i in range(20):
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=15)
                msg = json.loads(resp)
                t = msg.get('type')
                if t == 'state':
                    d = msg['data']
                    print(f"  state: step={d.get('step')}, od={d.get('opinion_distribution') is not None}")
                    got_state = True
                    if d.get('step', 0) >= 3:
                        break
                elif t == 'progress':
                    pass  # skip progress
                elif t == 'error':
                    print(f"  ERROR: {msg.get('message')}")
                    break
            except asyncio.TimeoutError:
                print(f"  TIMEOUT at msg {i}")
                break

        await ws.send(json.dumps({"action": "stop"}))
        print(f"\n=== Done. Got state: {got_state} ===")

asyncio.run(main())

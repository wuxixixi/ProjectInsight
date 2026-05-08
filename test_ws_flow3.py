"""Test: inject event then start via WebSocket - verbose."""
import asyncio
import json
import httpx
import websockets

API = "http://localhost:8000"
WS = "ws://localhost:8000/ws/simulation"

async def main():
    # 1. Inject event
    print("=== 1. Inject event ===")
    async with httpx.AsyncClient(timeout=30, proxy=None) as client:
        resp = await client.post(f"{API}/api/event/airdrop", json={
            "content": "某研究所数据泄露",
            "source": "public",
            "skip_parse": True,
            "credibility": "低可信"
        })
        data = resp.json()
        print(f"  pending: {data.get('data', {}).get('event', {}).get('pending')}")

    # 2. Start via WebSocket
    print("\n=== 2. Start simulation ===")
    async with websockets.connect(WS) as ws:
        await ws.send(json.dumps({
            "action": "start",
            "params": {
                "mode": "news",
                "use_llm": True,
                "population_size": 27,
                "population_profile_id": "shass_news_institute",
                "refresh_realistic_profile": False,
                "max_steps": 3,
                "use_dual_network": True,
                "cocoon_strength": 0.5,
                "debunk_delay": 10,
                "initial_rumor_spread": 0.3,
                "max_concurrent": 13,
                "timeout": 60,
                "max_retries": 5,
                "connection_pool_size": 600
            }
        }))

        # Read ALL messages for 60 seconds
        print("\n=== 3. Reading messages ===")
        try:
            while True:
                resp = await asyncio.wait_for(ws.recv(), timeout=60)
                msg = json.loads(resp)
                t = msg.get('type')
                if t == 'state':
                    d = msg['data']
                    print(f"  STATE: step={d.get('step')}, agents={len(d.get('agents',[]))}, od={d.get('opinion_distribution') is not None}")
                    if d.get('step', 0) >= 3:
                        break
                elif t == 'progress':
                    # Only print first progress of each step
                    pass
                elif t == 'error':
                    print(f"  ERROR: {msg.get('message')}")
                    break
                else:
                    print(f"  UNKNOWN: {t}")
        except asyncio.TimeoutError:
            print("  TIMEOUT - no more messages")
        except Exception as e:
            print(f"  Exception: {e}")

        await ws.send(json.dumps({"action": "stop"}))
        print("\n=== Done ===")

asyncio.run(main())

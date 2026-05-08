import asyncio, json, websockets

async def main():
    async with websockets.connect('ws://localhost:8000/ws/simulation') as ws:
        await ws.send(json.dumps({'action':'start','params':{
            'use_llm':True,'population_size':27,'population_profile_id':'shass_news_institute',
            'refresh_realistic_profile':False,'max_steps':3,'use_dual_network':True,
            'cocoon_strength':0.5,'debunk_delay':10,'initial_rumor_spread':0.3,
            'max_concurrent':13,'timeout':30,'max_retries':2,'connection_pool_size':600
        }}))
        r = await asyncio.wait_for(ws.recv(), timeout=30)
        m = json.loads(r)
        print(f'Start: type={m["type"]}, agents={len(m.get("data",{}).get("agents",[]))}')

        await ws.send(json.dumps({'action':'auto','interval':3000}))
        
        for i in range(30):
            try:
                r = await asyncio.wait_for(ws.recv(), timeout=60)
                m = json.loads(r)
                tp = m['type']
                if tp == 'state':
                    d = m['data']
                    print(f'[{i}] STATE step={d.get("step")} agents={len(d.get("agents",[]))} od={d.get("opinion_distribution") is not None}')
                    if d.get('step',0) >= 3:
                        break
                elif tp == 'progress':
                    if i < 5:
                        print(f'[{i}] progress: {m.get("step")}/{m.get("total")}')
                elif tp == 'error':
                    print(f'[{i}] ERROR: {m.get("message")}')
                    break
                else:
                    print(f'[{i}] {tp}')
            except asyncio.TimeoutError:
                print(f'[{i}] TIMEOUT')
                break

        await ws.send(json.dumps({'action':'stop'}))
        print('Done')

asyncio.run(main())

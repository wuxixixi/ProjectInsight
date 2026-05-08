import asyncio, json, websockets

async def main():
    async with websockets.connect('ws://localhost:8000/ws/simulation') as ws:
        await ws.send(json.dumps({'action':'start','params':{
            'use_llm':False,'population_size':27,'population_profile_id':'shass_news_institute',
            'refresh_realistic_profile':False,'max_steps':3,'use_dual_network':True,
            'cocoon_strength':0.5,'debunk_delay':10,'initial_rumor_spread':0.3,
            'max_concurrent':13,'timeout':60,'max_retries':5,'connection_pool_size':600
        }}))
        r = await asyncio.wait_for(ws.recv(), timeout=15)
        m = json.loads(r)
        t = m['type']
        n = len(m.get('data',{}).get('agents',[]))
        print(f'Start: type={t}, agents={n}')

        await ws.send(json.dumps({'action':'auto','interval':500}))
        
        for i in range(20):
            try:
                r = await asyncio.wait_for(ws.recv(), timeout=15)
                m = json.loads(r)
                tp = m['type']
                if tp == 'state':
                    d = m['data']
                    s = d.get('step',0)
                    a = len(d.get('agents',[]))
                    od = d.get('opinion_distribution') is not None
                    print(f'[{i}] STATE step={s} agents={a} od={od}')
                    if s >= 3:
                        break
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

#!/usr/bin/env python3
"""Check available models from the campus LLM API."""
import paramiko
import json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.16.128.44', username='dev', password='dev@sass.', timeout=10)

API_KEY = 'R61XwviRggmoTdDGHmH3tA0BQN7TToYwdPk61m9Y8Gs'
BASE = 'http://10.17.2.29:31277'

# 1. Try /v1/models and variants
print("=== 查询模型列表端点 ===")
for ep in ['/v1/models', '/models', '/v1/engines']:
    cmd = f"curl -s --connect-timeout 5 '{BASE}{ep}' -H 'Authorization: Bearer {API_KEY}'"
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    status = "有数据" if out and '404' not in out and len(out) > 5 else "无数据"
    print(f"  {ep}: {status}")
    if status == "有数据":
        print(f"    {out[:500]}")

# 2. Probe common model names
print("\n=== 探测可用模型 ===")
test_models = [
    'DeepSeek-V3.2', 'deepseek-v3', 'deepseek-chat', 'deepseek-coder',
    'deepseek-reasoner', 'deepseek-v2', 'deepseek-v2.5',
    'qwen2.5-72b-instruct', 'qwen-plus', 'qwen-turbo', 'qwen-max',
    'llama-3.1-70b', 'llama-3.1-8b', 'llama3', 'llama2',
    'mistral-large', 'mistral-7b', 'mixtral',
    'gpt-4', 'gpt-4o', 'gpt-3.5-turbo',
    'chatglm3', 'chatglm4', 'glm-4',
    'yi-large', 'yi-34b',
    'baichuan2', 'internlm2',
    'default',
]

available = []
for model in test_models:
    payload = json.dumps({"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1})
    cmd = f"curl -s --connect-timeout 5 '{BASE}/v1/chat/completions' -H 'Authorization: Bearer {API_KEY}' -H 'Content-Type: application/json' -d '{payload}'"
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    try:
        resp = json.loads(out)
        if 'choices' in resp:
            actual_model = resp.get('model', model)
            print(f"  {model}: OK (返回模型名: {actual_model})")
            available.append((model, actual_model))
        elif 'error' in resp:
            msg = resp['error'].get('message', '')[:80]
            print(f"  {model}: {msg}")
        else:
            print(f"  {model}: 未知响应 {str(resp)[:80]}")
    except:
        print(f"  {model}: 无法解析")

print(f"\n=== 共发现 {len(available)} 个可用模型 ===")
for m, actual in available:
    print(f"  {m} -> {actual}")

client.close()

#!/usr/bin/env python3
"""Deep-probe LLM models: verify if different model names return different responses."""
import paramiko
import os
import json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
# Issue #1249: 使用环境变量
client.connect('172.16.128.44', username='dev', password=os.environ.get("YANYUAN_PASSWORD", ""), timeout=10)

API_KEY = os.environ.get("LLM_API_KEY", "")
BASE = 'http://10.17.2.29:31277'

# 1. 验证 DeepSeek-V3.2 vs qwen2.5-72b-instruct 是否真是不同模型
print("=== 验证两个模型是否不同 ===")
for model in ['DeepSeek-V3.2', 'qwen2.5-72b-instruct']:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "你是什么模型？请说出你的模型名称和版本"}],
        "max_tokens": 100
    })
    cmd = f"curl -s --connect-timeout 15 '{BASE}/v1/chat/completions' -H 'Authorization: Bearer {API_KEY}' -H 'Content-Type: application/json' -d '{payload}'"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    out = stdout.read().decode('utf-8', errors='replace')
    try:
        resp = json.loads(out)
        content = resp['choices'][0]['message']['content']
        usage = resp.get('usage', {})
        print(f"  [{model}] 回复: {content[:120]}")
        print(f"  usage: {usage}")
    except:
        print(f"  [{model}] 解析失败: {out[:100]}")

# 2. 扩大探测范围 - 更多可能的模型名
print("\n=== 扩大探测范围 ===")
more_models = [
    # DeepSeek 系列
    'deepseek-v3-0324', 'deepseek-v3.2', 'deepseek-r1', 'deepseek-r1-distill',
    'DeepSeek-V3', 'DeepSeek-R1', 'deepseek-v2.5-1210',
    'deepseek-coder-v2', 'deepseek-math',
    # Qwen 系列
    'Qwen2.5-72B-Instruct', 'Qwen2.5-7B-Instruct', 'Qwen2.5-32B',
    'qwen2-72b', 'Qwen1.5-72B', 'qwen2.5-coder-32b',
    'Qwen2-72B-Instruct', 'QwQ-32B',
    # 其他国产
    'Yi-1.5-34B', 'internlm2-20b', 'internlm2.5',
    'Baichuan2-53B', 'chatglm4-9b',
    # Llama
    'Llama-3.1-70B-Instruct', 'Llama-3.1-8B-Instruct',
    'Meta-Llama-3.1-70B', 'llama-3.3-70b',
    # Mistral
    'Mistral-7B-Instruct', 'Mixtral-8x7B', 'Mixtral-8x22B',
    # 其他
    'solar', 'gemma-2-27b', 'command-r',
]

found = []
for model in more_models:
    payload = json.dumps({"model": model, "messages": [{"role": "user", "content": "1+1="}], "max_tokens": 3})
    cmd = f"curl -s --connect-timeout 5 '{BASE}/v1/chat/completions' -H 'Authorization: Bearer {API_KEY}' -H 'Content-Type: application/json' -d '{payload}'"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
    out = stdout.read().decode('utf-8', errors='replace')
    try:
        resp = json.loads(out)
        if 'choices' in resp:
            content = resp['choices'][0]['message']['content'][:30]
            actual = resp.get('model', '?')
            print(f"  {model}: OK -> {content} (model={actual})")
            found.append(model)
        elif 'error' in resp:
            pass  # skip
    except:
        pass

# 3. 检查是否有 served_models 端点或其他管理接口
print(f"\n=== 总计发现 {len(found)} + 2 = {len(found)+2} 个可用模型名 ===")
print(f"  DeepSeek-V3.2")
print(f"  qwen2.5-72b-instruct")
for m in found:
    print(f"  {m}")

# 4. 检查 /v1/models 各种变体和健康检查
print("\n=== 其他端点探测 ===")
for ep in ['/v1/models', '/models', '/v1/engines', '/health', '/v1/health',
           '/info', '/v1/info', '/status', '/v1/status',
           '/api/v1/models', '/openai/v1/models']:
    cmd = f"curl -s --connect-timeout 3 '{BASE}{ep}'"
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    code = len(out) > 10 and '404' not in out[:50]
    if code:
        print(f"  {ep}: {out[:200]}")

client.close()

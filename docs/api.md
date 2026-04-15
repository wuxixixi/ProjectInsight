# API 接口文档

## 基础信息

| 项目 | 说明 |
|------|------|
| 基础 URL | http://localhost:8000 |
| WebSocket | ws://localhost:8000/ws/simulation |
| 数据格式 | JSON |

## REST API

### 健康检查

#### GET /

检查服务是否正常运行

**响应示例:**
```json
{
  "status": "ok",
  "service": "信息茧房推演系统",
  "version": "2.0.0"
}
```

---

### 推演管理

#### POST /api/simulation/start

启动新的推演模拟

**请求体:**
```json
{
  "cocoon_strength": 0.5,
  "debunk_delay": 10,
  "population_size": 200,
  "initial_rumor_spread": 0.3,
  "network_type": "small_world",
  "use_llm": true,
  "use_dual_network": true,
  "num_communities": 8,
  "public_m": 3,
  "max_concurrent": 50,
  "connection_pool_size": 600,
  "timeout": 60,
  "max_retries": 5,
  "debunk_credibility": 0.7,
  "authority_factor": 0.5,
  "backfire_strength": 0.3,
  "silence_threshold": 0.3,
  "polarization_factor": 0.3,
  "echo_chamber_factor": 0.2
}
```

**响应示例:**
```json
{
  "step": 0,
  "agents": [...],
  "edges": [...],
  "rumor_spread_rate": 0.3,
  "truth_acceptance_rate": 0.0,
  "avg_opinion": -0.85,
  "polarization_index": 0.42
}
```

---

#### GET /api/simulation/step

执行单步推演（仅数学模型模式）

**响应示例:**
```json
{
  "step": 1,
  "agents": [...],
  "edges": [...],
  "rumor_spread_rate": 0.35,
  "truth_acceptance_rate": 0.05,
  "avg_opinion": -0.72,
  "polarization_index": 0.48
}
```

---

#### GET /api/simulation/state

获取当前推演状态

**响应示例:**
```json
{
  "step": 5,
  "agents": [...],
  "public_edges": [...],
  "private_edges": [...],
  "rumor_spread_rate": 0.45,
  "truth_acceptance_rate": 0.15,
  "avg_opinion": -0.35,
  "polarization_index": 0.62,
  "silence_rate": 0.12,
  "public_rumor_rate": 0.48,
  "private_rumor_rate": 0.42,
  "num_communities": 8,
  "num_influencers": 5
}
```

---

#### POST /api/simulation/finish

结束推演并生成基础报告

**响应示例:**
```json
{
  "success": true,
  "report_path": "reports/report_1234567890.md",
  "report_filename": "report_1234567890.md"
}
```

---

### 智能体透视

#### GET /api/agent/{agent_id}/inspect

获取指定 Agent 的详细信息

**路径参数:**
- `agent_id`: Agent ID

**响应示例:**
```json
{
  "agent_id": 42,
  "persona": {
    "type": "理性分析者",
    "desc": "注重逻辑和数据"
  },
  "belief_strength": 0.75,
  "susceptibility": 0.3,
  "influence": 0.8,
  "old_opinion": -0.6,
  "new_opinion": -0.35,
  "received_news": [
    "官方发布辟谣公告"
  ],
  "llm_raw_response": "...",
  "emotion": "理性",
  "action": "评论",
  "generated_comment": "仔细看了官方公告，发现之前的消息确实有误...",
  "reasoning": "考虑到邻居观点和官方证据，我选择相信真相",
  "has_decided": true,
  "fear_of_isolation": 0.4,
  "conviction": 0.6,
  "is_silent": false,
  "perceived_climate": {
    "total": 15,
    "pro_rumor_ratio": 0.4,
    "pro_truth_ratio": 0.33,
    "neutral_ratio": 0.27,
    "silent_ratio": 0.1,
    "avg_opinion": -0.15
  }
}
```

---

### 报告管理

#### POST /api/report/generate

生成智库专报（LLM 模式）

**响应示例:**
```json
{
  "success": true,
  "content": "# 智库专报\n\n## 演练核心摘要\n\n...",
  "filename": "intelligence_report_1234567890.md",
  "path": "reports/intelligence_report_1234567890.md"
}
```

---

#### GET /api/report/stream

流式生成智库专报（SSE）

**响应类型:** text/event-stream

**消息格式:**
```json
{"content": "## 演练核心摘要\n"}
{"content": "本次推演..."}
{"done": true}
```

---

#### GET /api/report/list

列出所有报告

**响应示例:**
```json
{
  "reports": [
    {
      "filename": "intelligence_report_1234567890.md",
      "path": "reports/intelligence_report_1234567890.md",
      "size": 15420,
      "modified": 1234567890.0
    }
  ]
}
```

---

#### GET /api/report/content

获取报告内容

**查询参数:**
- `filename`: 报告文件名

**响应示例:**
```json
{
  "success": true,
  "content": "# 智库专报\n\n...",
  "filename": "intelligence_report_1234567890.md"
}
```

---

#### GET /api/report/download

下载报告文件

**查询参数:**
- `filename`: 报告文件名

**响应:** 文件下载

---

### 知识图谱

#### POST /api/event/parse

解析新闻文本为知识图谱

**查询参数:**
- `content`: 新闻文本内容

**响应示例:**
```json
{
  "success": true,
  "data": {
    "entities": [
      {"name": "王某杞", "type": "人物", "description": "某科技公司CEO"},
      {"name": "某科技公司", "type": "组织", "description": "新闻中提及的科技公司"},
      {"name": "北京", "type": "地点", "description": "发布会举办地点"},
      {"name": "100亿元", "type": "概念", "description": "公司计划投资的金额"}
    ],
    "relations": [
      {"source": "王某杞", "target": "某科技公司", "action": "担任CEO", "type": "关联"},
      {"source": "某科技公司", "target": "100亿元", "action": "计划投资", "type": "影响"}
    ],
    "summary": "某科技公司CEO王某杞在北京发布会上宣布公司将投资100亿元。"
  }
}
```

---

#### POST /api/event/airdrop

注入突发事件，触发知识图谱解析并在推演中使用

**查询参数:**
- `content`: 事件文本内容
- `source`: 来源 (public/private)，默认 "public"

**响应示例:**
```json
{
  "success": true,
  "data": {
    "event": {
      "content": "某科技公司CEO王某杞在北京发帨会上宣希公司将投资100亿元",
      "step": 0,
      "knowledge_graph": {...}
    },
    "knowledge_graph": {
      "entities": [...],
      "relations": [...],
      "summary": "..."
    }
  }
}
```

---

#### GET /api/event/knowledge-graph

获取当前推演的知识图谱

**响应示例:**
```json
{
  "success": true,
  "data": {
    "entities": [...],
    "relations": [...],
    "summary": "..."
  }
}
```

---

### 数学模型

#### GET /api/math-model/explanation

获取增强版数学模型的理论解释

**响应示例:**
```json
{
  "theories": {
    "echo_chamber": "算法推荐形成信息茧房的机制...",
    "spiral_of_silence": "沉默的螺旋理论...",
    "group_polarization": "群体极化理论..."
  },
  "parameters": {
    "cocoon_strength": {
      "name": "算法茧房强度",
      "description": "推荐算法强化既有观点的程度"
    }
  }
}
```

---

## WebSocket API

### 连接地址

```
ws://localhost:8000/ws/simulation
```

### 客户端 → 服务端

#### 启动推演
```json
{
  "action": "start",
  "params": {
    "cocoon_strength": 0.5,
    "debunk_delay": 10,
    "population_size": 200,
    "initial_rumor_spread": 0.3,
    "use_llm": true,
    "use_dual_network": true,
    "num_communities": 8,
    "max_concurrent": 50
  }
}
```

#### 执行单步
```json
{"action": "step"}
```

#### 自动推演
```json
{"action": "auto", "interval": 2000}
```

#### 停止推演
```json
{"action": "stop"}
```

#### 结束推演
```json
{"action": "finish"}
```

---

### 服务端 → 客户端

#### 状态推送
```json
{
  "type": "state",
  "data": {
    "step": 5,
    "agents": [...],
    "edges": [...],
    "rumor_spread_rate": 0.45,
    "truth_acceptance_rate": 0.15,
    "avg_opinion": -0.35,
    "polarization_index": 0.62,
    "silence_rate": 0.12,
    "public_rumor_rate": 0.48,
    "private_rumor_rate": 0.42,
    "public_truth_rate": 0.18,
    "private_truth_rate": 0.12,
    "num_communities": 8,
    "num_influencers": 5
  }
}
```

#### 进度推送
```json
{
  "type": "progress",
  "step": 50,
  "total": 200,
  "message": "Agent 50/200"
}
```

#### 错误推送
```json
{
  "type": "error",
  "message": "推演引擎未初始化"
}
```

#### 报告生成完成
```json
{
  "type": "report",
  "data": {
    "report_path": "reports/intelligence_report_1234567890.md",
    "report_filename": "intelligence_report_1234567890.md"
  }
}
```

---

## 错误响应

所有 API 错误响应格式：

```json
{
  "error": "错误描述信息"
}
```

**常见错误码:**

| 错误信息 | 说明 |
|----------|------|
| 请先启动模拟 | 未调用 start 接口 |
| LLM 模式请使用 WebSocket | LLM 模式不支持 REST step |
| 推演引擎未初始化 | engine 对象为 None |
| 智库专报仅支持LLM驱动模式 | 数学模型模式无法生成专报 |
| 报告不存在 | 指定的报告文件不存在 |

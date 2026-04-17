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

## 推演模式

### 模式参数说明

推演模式通过 `/api/simulation/start` 接口的 `mode` 参数指定，无需单独调用模式设置接口。

**模式类型**:
| 值 | 说明 |
|------|------|
| `sandbox` | 沙盘推演模式（默认），参数驱动，研究传播机制 |
| `news` | 新闻推演模式，真实分布锚定，预测现实演进 |

**启动参数示例（新闻模式）**:
```json
{
  "mode": "news",
  "init_distribution": {
    "believe_rumor": 0.30,
    "believe_truth": 0.15,
    "neutral": 0.55
  },
  "cocoon_strength": 0.5,
  "population_size": 200,
  "use_llm": true
}
```

**启动参数示例（沙盘模式）**:
```json
{
  "mode": "sandbox",
  "initial_rumor_spread": 0.3,
  "cocoon_strength": 0.5,
  "population_size": 200,
  "use_llm": true
}
```

---

## 推演管理

### POST /api/simulation/start

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

## 预测接口

### GET /api/prediction

获取当前预测结果（新闻模式）

**响应示例:**
```json
{
  "success": true,
  "data": {
    "current_state": {
      "rumor_spread_rate": 0.45,
      "truth_acceptance_rate": 0.15,
      "polarization_index": 0.62
    },
    "prediction": {
      "rumor_spread_rate": {
        "expected": 0.52,
        "optimistic": 0.38,
        "pessimistic": 0.66,
        "confidence": 0.95
      },
      "truth_acceptance_rate": {
        "expected": 0.22,
        "optimistic": 0.35,
        "pessimistic": 0.09
      }
    },
    "risk_level": "high",
    "intervention_window": {
      "current_step": 5,
      "recommended_intervention_step": 8,
      "window_closing": false
    },
    "strategies": [
      {
        "type": "debunk",
        "priority": 1,
        "description": "官方权威辟谣",
        "expected_effect": "预计降低谣言传播率15-25%"
      },
      {
        "type": "amplify",
        "priority": 2,
        "description": "放大真相传播",
        "expected_effect": "预计提升真相接受率10-20%"
      }
    ],
    "reasoning": "当前谣言传播率已达45%，预测将持续上升..."
  }
}
```

---

### GET /api/prediction/trajectory

获取预测轨迹数据

**查询参数:**
- `steps`: 预测步数（默认10）

**响应示例:**
```json
{
  "success": true,
  "data": {
    "steps": [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    "rumor_spread_rate": {
      "expected": [0.45, 0.48, 0.51, 0.54, 0.56, 0.58, 0.60, 0.61, 0.62, 0.63, 0.64],
      "optimistic": [0.45, 0.42, 0.39, 0.36, 0.33, 0.30, 0.28, 0.26, 0.24, 0.23, 0.22],
      "pessimistic": [0.45, 0.54, 0.63, 0.72, 0.79, 0.85, 0.88, 0.90, 0.92, 0.93, 0.94]
    },
    "truth_acceptance_rate": {
      "expected": [0.15, 0.16, 0.17, 0.18, 0.19, 0.20, 0.21, 0.22, 0.23, 0.24, 0.25],
      "optimistic": [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.44, 0.48, 0.51, 0.54, 0.56],
      "pessimistic": [0.15, 0.12, 0.09, 0.07, 0.05, 0.04, 0.03, 0.02, 0.02, 0.01, 0.01]
    }
  }
}
```

---

## 智能体透视

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

## 报告管理

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

## 知识图谱

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

**请求体:**
```json
{
  "content": "某科技公司CEO王某杞在北京发布会上宣布公司将投资100亿元",
  "source": "public",
  "skip_parse": false
}
```

**参数说明:**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| content | string | 必填 | 事件文本内容 |
| source | string | "public" | 来源 (public/private) |
| skip_parse | boolean | false | 是否跳过图谱解析（快速模式） |

**响应示例:**
```json
{
  "success": true,
  "data": {
    "event": {
      "content": "某科技公司CEO王某杞在北京发布会上宣布公司将投资100亿元",
      "step": 5,
      "skip_parse": false
    },
    "knowledge_graph": {
      "entities": [...],
      "relations": [...],
      "summary": "..."
    },
    "parse_time": 15.3
  }
}
```

**快速模式响应（skip_parse=true）:**
```json
{
  "success": true,
  "data": {
    "event": {
      "content": "...",
      "step": 5,
      "skip_parse": true
    },
    "knowledge_graph": null,
    "parse_time": 0.1
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

## 文档接口

#### GET /api/docs/usage

获取使用说明文档内容

**响应示例:**
```json
{
  "success": true,
  "content": "# 使用说明\n\n## 1. 选择推演模式\n...",
  "filename": "README.md"
}
```

---

## 数学模型

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
    "mode": "news",
    "cocoon_strength": 0.5,
    "debunk_delay": 10,
    "population_size": 200,
    "initial_rumor_spread": 0.3,
    "use_llm": true,
    "use_dual_network": true,
    "num_communities": 8,
    "max_concurrent": 50,
    "init_distribution": {
      "believe_rumor": 0.30,
      "believe_truth": 0.15,
      "neutral": 0.55
    }
  }
}
```

**参数说明**:
| 参数 | 必填 | 说明 |
|------|------|------|
| mode | 否 | 推演模式，默认 sandbox |
| init_distribution | 否 | 新闻模式专用，真实分布锚定 |
| 其他参数 | 否 | 详见上文 REST API 说明 |

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

#### 预测推送（新闻模式）
```json
{
  "type": "prediction",
  "data": {
    "prediction": {...},
    "risk_level": "high",
    "strategies": [...],
    "reasoning": "..."
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
| 知识图谱解析超时 | LLM 响应超时，建议使用快速注入 |

---

## 响应时间参考

| 接口 | 数学模型模式 | LLM模式 |
|------|-------------|---------|
| /api/simulation/start | 100-500ms | 5-30s（初始化Agent） |
| /api/simulation/step | 10-50ms | 通过WebSocket |
| /api/event/parse | N/A | 10-60s |
| /api/event/airdrop | N/A | 10-60s（完整解析） |
| /api/event/airdrop (skip_parse) | N/A | 0.1-2s（快速注入） |
| /api/prediction | 10-100ms | 10-100ms |
| /api/report/generate | N/A | 30-120s |

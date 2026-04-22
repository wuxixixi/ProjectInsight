# API 接口文档

## 基础信息

| 项目 | 说明 |
|------|------|
| 基础 URL | http://localhost:8000 |
| WebSocket | ws://localhost:8000/ws |
| 数据格式 | JSON |
| API 版本 | v2.0.0 |

## 接口概览

### 健康检查
- `GET /` - 服务健康状态检查

### 推演管理
- `POST /api/simulation/start` - 启动推演模拟
- `GET /api/simulation/step` - 执行单步推演（数学模型模式）
- `GET /api/simulation/state` - 获取当前推演状态
- `POST /api/simulation/finish` - 结束推演并生成基础报告

### 智能体透视
- `GET /api/agent/{agent_id}/inspect` - 获取指定智能体详细信息

### 报告管理
- `POST /api/report/generate` - 生成智库专报（LLM模式）
- `GET /api/report/stream` - 流式生成智库专报
- `GET /api/report/list` - 列出所有报告
- `GET /api/report/content` - 获取报告内容
- `GET /api/report/download` - 下载报告文件

### 知识图谱
- `POST /api/event/parse` - 解析新闻文本为知识图谱
- `POST /api/event/inject` - 注入事件（支持快速注入）

### 预测接口（新闻模式）
- `GET /api/prediction/update` - 获取当前预测结果
- `GET /api/prediction/timeline` - 获取预测轨迹数据

### 风险预警
- `GET /api/risk/check` - 检查当前风险状态

---

## REST API 详解

### 健康检查

#### GET /

**描述**: 检查服务是否正常运行

**响应**:
```json
{
  "status": "ok",
  "service": "觉测·洞鉴信息茧房推演系统",
  "version": "2.0.0"
}
```

---

## 推演管理

### POST /api/simulation/start

**描述**: 启动新的推演模拟

**请求体**:
```json
{
  "mode": "sandbox",
  "cocoon_strength": 0.5,
  "response_delay": 10,
  "population_size": 200,
  "initial_negative_spread": 0.3,
  "network_type": "small_world",
  "use_llm": true,
  "use_dual_network": true,
  "num_communities": 8,
  "response_credibility": 0.7,
  "authority_factor": 0.5,
  "backfire_strength": 0.3,
  "silence_threshold": 0.3,
  "polarization_factor": 0.3,
  "echo_chamber_factor": 0.2,
  "init_distribution": {
    "believe_negative": 0.30,
    "believe_positive": 0.15,
    "neutral": 0.55
  }
}
```

**参数说明**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| mode | string | "sandbox" | 推演模式（sandbox/news） |
| cocoon_strength | float | 0.5 | 算法茧房强度 [0-1] |
| response_delay | int | 10 | 权威回应延迟步数 |
| population_size | int | 200 | Agent数量 |
| initial_negative_spread | float | 0.3 | 初始误信率（沙盘模式） |
| network_type | string | "barabasi_albert" | 网络类型 |
| use_llm | bool | true | 是否使用LLM模式 |
| use_dual_network | bool | true | 是否使用双层网络 |
| num_communities | int | 8 | 私域社群数量 |
| response_credibility | float | 0.7 | 权威回应可信度 |
| init_distribution | object | null | 真实分布锚定（新闻模式） |

**兼容性说明**: 系统同时支持新旧参数名，如 `debunk_delay` → `response_delay`

**响应**:
```json
{
  "step": 0,
  "agents": [...],
  "edges": [...],
  "negative_belief_rate": 0.3,
  "positive_belief_rate": 0.0,
  "avg_opinion": -0.85,
  "polarization_index": 0.42
}
```

---

### GET /api/simulation/step

**描述**: 执行单步推演（仅数学模型模式）

**响应**:
```json
{
  "step": 1,
  "agents": [...],
  "edges": [...],
  "negative_belief_rate": 0.35,
  "positive_belief_rate": 0.05,
  "avg_opinion": -0.72,
  "polarization_index": 0.48
}
```

---

### GET /api/simulation/state

**描述**: 获取当前推演状态

**响应**:
```json
{
  "step": 5,
  "agents": [...],
  "public_edges": [...],
  "private_edges": [...],
  "negative_belief_rate": 0.45,
  "positive_belief_rate": 0.15,
  "avg_opinion": -0.35,
  "polarization_index": 0.62,
  "silence_rate": 0.12,
  "public_negative_rate": 0.48,
  "private_negative_rate": 0.42,
  "num_communities": 8,
  "num_influencers": 5
}
```

---

### POST /api/simulation/finish

**描述**: 结束推演并生成基础报告

**响应**:
```json
{
  "success": true,
  "report_path": "reports/report_1234567890.md",
  "report_filename": "report_1234567890.md"
}
```

---

## 预测接口

### GET /api/prediction/update

**描述**: 获取当前预测结果（新闻模式）

**响应**:
```json
{
  "success": true,
  "data": {
    "current_state": {
      "negative_belief_rate": 0.45,
      "positive_belief_rate": 0.15,
      "polarization_index": 0.62
    },
    "prediction": {
      "negative_belief_rate": {
        "expected": 0.52,
        "optimistic": 0.38,
        "pessimistic": 0.66,
        "confidence": 0.95
      },
      "positive_belief_rate": {
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
        "type": "response",
        "priority": 1,
        "description": "官方权威回应",
        "expected_effect": "预计降低误信率15-25%"
      }
    ],
    "reasoning": "当前误信率已达45%，预测将持续上升..."
  }
}
```

---

## 智能体透视

### GET /api/agent/{agent_id}/inspect

**路径参数**:
- `agent_id`: Agent ID

**响应**:
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
    "官方发布权威回应公告"
  ],
  "llm_raw_response": "...",
  "emotion": "理性",
  "action": "评论",
  "generated_comment": "仔细看了官方公告，发现之前的消息确实有误...",
  "reasoning": "考虑到邻居观点和官方证据，我选择正确认知"
}
```

---

## 报告管理

### POST /api/report/generate

**描述**: 生成智库专报（LLM 模式）

**响应**:
```json
{
  "success": true,
  "content": "# 智库专报\n\n## 演练核心摘要\n\n...",
  "filename": "intelligence_report_1234567890.md",
  "path": "reports/intelligence_report_1234567890.md"
}
```

---

## 知识图谱

### POST /api/event/parse

**描述**: 解析新闻文本为知识图谱

**请求体**:
```json
{
  "content": "某科技公司CEO在北京发布会宣布将投资100亿元"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "entities": [
      {"name": "王某杞", "type": "人物", "description": "某科技公司CEO", "importance": 1},
      {"name": "某科技公司", "type": "组织", "description": "科技公司", "importance": 2}
    ],
    "relations": [
      {"source": "王某杞", "target": "某科技公司", "action": "担任CEO", "type": "关联"}
    ],
    "summary": "某科技公司CEO王某杞在北京发布会宣布投资100亿元。",
    "sentiment": "正面",
    "credibility_hint": "高可信"
  }
}
```

---

### POST /api/event/inject

**描述**: 注入事件（支持快速注入）

**请求体**:
```json
{
  "content": "事件内容",
  "source": "public",
  "skip_parse": false
}
```

**快速模式响应**（skip_parse=true）:
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

## WebSocket API

### 连接地址
```
ws://localhost:8000/ws
```

### 客户端 → 服务端消息

#### 启动推演
```json
{
  "action": "start",
  "params": {
    "mode": "news",
    "cocoon_strength": 0.5,
    "response_delay": 10,
    "population_size": 200
  }
}
```

#### 执行单步
```json
{"action": "step"}
```

#### 停止推演
```json
{"action": "stop"}
```

### 服务端 → 客户端消息

#### 状态推送
```json
{
  "type": "state",
  "data": {
    "step": 5,
    "agents": [...],
    "edges": [...],
    "negative_belief_rate": 0.45,
    "positive_belief_rate": 0.15,
    "avg_opinion": -0.35,
    "polarization_index": 0.62
  }
}
```

#### 错误推送
```json
{
  "type": "error",
  "message": "推演引擎未初始化"
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

**常见错误**:

| 错误信息 | HTTP状态码 | 说明 |
|----------|------------|------|
| 请先启动模拟 | 400 | 未调用start接口 |
| LLM模式请使用WebSocket | 400 | LLM模式不支持REST step |
| 推演引擎未初始化 | 500 | engine对象为None |
| 报告不存在 | 404 | 指定的报告文件不存在 |

---

## 响应时间参考

| 接口 | 数学模型模式 | LLM模式 |
|------|-------------|---------|
| /api/simulation/start | 100-500ms | 5-30s |
| /api/simulation/step | 10-50ms | 通过WebSocket |
| /api/event/parse | N/A | 10-60s |
| /api/event/inject | N/A | 0.1-2s（快速模式） |

---

## 版本信息

- **v2.0.0** (当前): 支持语义抽象、双模式推演、知识图谱
- **v1.0.0**: 基础谣言传播模拟
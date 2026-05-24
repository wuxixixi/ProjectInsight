# API 接口文档

更新时间：2026-05-24

## 基础信息

| 项目 | 当前值 |
| --- | --- |
| 后端地址 | `http://localhost:8000` |
| WebSocket | `ws://localhost:8000/ws/simulation` |
| 前端开发地址 | `http://localhost:3000` |
| 数据格式 | JSON；报告流使用 SSE |
| 主要前缀 | `/api`、`/api/event`、`/api/report` |

前端开发环境下，`frontend/src/App.vue` 会直接访问同主机 `8000` 端口；`vite.config.js` 仍保留 `/api` 和 `/ws` 代理，便于兼容同源开发方式。

## 接口概览

| 模块 | 方法与路径 | 说明 |
| --- | --- | --- |
| 健康检查 | `GET /` | 服务状态 |
| 推演 | `POST /api/simulation/start` | REST 启动推演 |
| 推演 | `GET /api/simulation/step` | 数学模型单步推演；LLM 模式请用 WebSocket |
| 推演 | `GET /api/simulation/state` | 当前推演状态 |
| 推演 | `POST /api/simulation/finish` | 结束推演并生成基础报告 |
| 模型解释 | `GET /api/math-model/explanation` | 数学模型理论与参数解释 |
| 智能体透视 | `GET /api/agent/{agent_id}/inspect` | 微观行为、决策链路、现实画像与数值来源 |
| 事件 | `POST /api/event/parse` | 将新闻文本解析为知识图谱 |
| 事件 | `POST /api/event/airdrop` | 注入事件，支持快速注入 |
| 事件 | `GET /api/event/knowledge-graph` | 当前知识图谱 |
| 预测 | `GET /api/prediction` | 趋势预测与干预建议 |
| 预测 | `GET /api/prediction/trajectory?steps=10` | 预测轨迹 |
| 风险 | `GET /api/risk-alerts` | 风险预警 |
| 风险 | `POST /api/risk-alerts/clear` | 清空预警历史 |
| 画像资料库 | `GET /api/profiles` | 列出内置画像、用户资料画像和已构建缓存 |
| 画像资料库 | `POST /api/profiles/upload` | 上传用户自定义画像资料 |
| 画像资料库 | `POST /api/profiles/build` | 从本地资料离线构建可复用画像缓存 |
| 报告 | `POST /api/report/generate` | 一次性生成智库专报 |
| 报告 | `GET /api/report/stream` | SSE 流式生成智库专报，并在完成后保存 |
| 报告 | `GET /api/report/list` | 报告列表 |
| 报告 | `GET /api/report/content?filename=...` | 读取报告内容 |
| 报告 | `GET /api/report/download?filename=...` | 下载报告 |
| 报告 | `POST /api/report/open` | 使用系统默认应用打开报告 |
| 设置 | `GET /api/settings/llm` | 获取当前 LLM 与并发配置 |
| 设置 | `POST /api/settings/llm` | 保存 LLM 与并发配置 |
| 健康检查 | `GET /api/health/llm` | LLM 连通性检测 |
| 热点新闻 | `GET /api/event/hot-news` | 获取今日热点新闻列表 |
| 文档 | `GET /api/docs/usage` | 读取 `docs/README.md` |

旧文档中的 `/api/event/inject`、`/api/prediction/update`、`/api/prediction/timeline`、`/api/risk/check`、`/ws` 已不是当前实现入口。

## 推演启动

### `POST /api/simulation/start`

REST 启动适合数学模型或初始化状态。LLM 连续推演通常通过 WebSocket 的 `start`、`step`、`auto` 消息完成。

```json
{
  "mode": "news",
  "cocoon_strength": 0.5,
  "response_delay": 10,
  "population_size": 200,
  "initial_negative_spread": 0.3,
  "network_type": "small_world",
  "use_llm": true,
  "use_dual_network": true,
  "num_communities": 8,
  "public_m": 3,
  "response_credibility": 0.7,
  "authority_factor": 0.5,
  "backfire_strength": 0.3,
  "silence_threshold": 0.3,
  "polarization_factor": 0.3,
  "echo_chamber_factor": 0.2,
  "population_profile_id": "shass_news_institute",
  "refresh_realistic_profile": false,
  "include_public_enrichment": false,
  "init_distribution": {
    "believe_negative": 0.3,
    "believe_positive": 0.15,
    "neutral": 0.55
  }
}
```

关键参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `mode` | `sandbox` | `sandbox` 为沙盘模式；`news` 为新闻推演模式 |
| `use_llm` | `true` | 是否让 Agent 通过 LLM 决策 |
| `use_dual_network` | `true` | 是否使用公域 + 私域双层网络 |
| `population_size` | `200` | 理论人设人数；使用现实画像时会被画像人数覆盖 |
| `population_profile_id` | `null` | 画像 ID。内置支持 `shass_news_institute`、`上海社科院新闻所`、`news_institute`；也可传用户自定义 `profile_id` |
| `realistic_profile_source_path` | `null` | 人员工作簿路径；不传时使用环境变量或默认路径 |
| `refresh_realistic_profile` | `false` | 是否强制从工作簿刷新缓存 |
| `include_public_enrichment` | `false` | 是否生成公开证据候选队列，仍需人工审核 |
| `max_concurrent` | 自动 | LLM 并发数；留空时按人数和运行环境自动计算 |

兼容字段仍可使用：`debunk_delay`、`initial_rumor_spread`、`debunk_credibility`、`believe_rumor`、`believe_truth`。新字段优先。

现实画像说明：

- `shass_news_institute` 当前按上海社科院新闻所 27 人组织画像运行。
- 用户自定义画像传入自定义 `profile_id`，运行时优先读取 `data/realistic_profiles/<profile_id>.sanitized.json` 缓存；没有缓存时从 `data/user_profiles/<profile_id>/sources/` 离线构建。
- 前端和 API 会返回姓名，用于演示验证微观行为；身份证号、手机、地址、健康、婚姻、出生日期等敏感列不会进入缓存和接口。
- 找不到工作簿且没有缓存时，系统会生成匿名合成画像用于兜底演示。

## 画像资料库

### `GET /api/profiles`

列出前端“样本画像”可选择的画像。返回内置新闻所画像、用户资料库画像，以及只有缓存但没有元数据的画像。

```json
{
  "success": true,
  "profiles": [
    {
      "profile_id": "shass_news_institute",
      "display_name": "上海社会科学院新闻研究所现实组织画像",
      "kind": "built_in",
      "size": 27,
      "ready": true,
      "source_count": null,
      "updated_at": "2026-05-11T10:00:00Z"
    },
    {
      "profile_id": "media_research_team",
      "display_name": "媒体研究团队",
      "kind": "user",
      "size": 12,
      "ready": true,
      "source_count": 3,
      "updated_at": "2026-05-11T10:20:00Z"
    }
  ]
}
```

### `POST /api/profiles/upload`

`multipart/form-data` 上传资料到本地资料库。

| 表单字段 | 必填 | 说明 |
| --- | --- | --- |
| `profile_id` | 是 | 用户自定义画像 ID，例如 `media_research_team` |
| `display_name` | 否 | 前端显示名称 |
| `files` | 是 | 一个或多个资料文件 |

支持文件：`csv`、`tsv`、`json`、`jsonl`、`txt`、`md`、`markdown`；安装 `pandas/openpyxl` 时支持 `xlsx/xls`。

上传后的文件路径：

```text
data/user_profiles/<profile_id>/sources/
```

### `POST /api/profiles/build`

从已上传资料离线构建画像缓存。

```json
{
  "profile_id": "media_research_team",
  "display_name": "媒体研究团队"
}
```

成功后写入：

```text
data/realistic_profiles/<profile_id>.sanitized.json
data/user_profiles/<profile_id>/profile.meta.json
```

返回的 `profile` 包含可用于推演的人数、公开画像字段和 `generation_trace`。后续启动推演时不需要重新上传或重新解析资料，除非再次调用 build 刷新缓存。

## 状态字段

`SimulationState` 当前同时保留“相信/拒绝新闻”和“误信/正确认知”两套口径：

| 字段 | 含义 |
| --- | --- |
| `believe_rate` | 相信当前新闻内容的比例 |
| `reject_rate` | 拒绝当前新闻内容的比例 |
| `news_credibility` | 新闻可信度：`高可信`、`低可信`、`不确定` |
| `mislead_rate` | 根据新闻可信度后验判定的误信率 |
| `correct_rate` | 根据新闻可信度后验判定的正确认知率 |
| `negative_belief_rate` | 兼容字段，当前与误信口径对齐 |
| `positive_belief_rate` | 兼容字段，当前与正确认知口径对齐 |
| `avg_opinion` | 平均观点，范围 `[-1, 1]` |
| `polarization_index` | 极化指数 |
| `silence_rate` | 沉默率 |
| `public_negative_rate` / `private_negative_rate` | 公域/私域误信口径比例 |
| `public_edges` / `private_edges` | 双层网络边 |
| `event_pool` | 最近事件池，`/state` 最多返回最近 50 条 |

## 智能体透视

### `GET /api/agent/{agent_id}/inspect`

该接口用于前端“微观行为透视”。LLM Agent 已决策时优先返回快照；没有快照时返回当前基础状态。

```json
{
  "agent_id": 3,
  "persona": {
    "type": "现实组织画像",
    "desc": "资深研究员 / 舆情治理..."
  },
  "belief_strength": 0.71,
  "susceptibility": 0.32,
  "influence": 0.79,
  "old_opinion": 0.04,
  "new_opinion": 0.12,
  "emotion": "理性",
  "action": "评论",
  "generated_comment": "...",
  "reasoning": "...",
  "perceived_climate": {
    "total": 8,
    "pro_rumor_ratio": 0.25,
    "pro_truth_ratio": 0.38,
    "neutral_ratio": 0.37,
    "silent_ratio": 0.12,
    "avg_opinion": 0.08
  },
  "realistic_profile": {
    "name": "张三",
    "role_label": "资深研究员 / 舆情治理",
    "department": "上海社会科学院新闻研究所",
    "specialty": "舆情治理",
    "seniority_label": "资深",
    "community_id": 1,
    "is_influencer": true,
    "generation_trace": {
      "source": "workbook",
      "inputs": {
        "age_band": "45-54岁",
        "work_years_band": "20-30年",
        "title": "研究员"
      },
      "derived": {
        "seniority_score": 0.855,
        "community_id": 1,
        "is_influencer": true
      },
      "metrics": {
        "opinion": 0.0819,
        "belief_strength": 0.7144,
        "influence": 0.8275,
        "susceptibility": 0.255
      },
      "formulas": {
        "influence": "资历分和行政职务共同影响影响力，最后限制在0.1到1.0之间"
      }
    }
  }
}
```

`generation_trace` 是前端“数值来源”的数据来源。UI 应将 `seniority_score` 展示为“资历分”，将 `clip` 解释为“把结果限制在合理范围内”。

## 事件注入

### `POST /api/event/parse`

```json
{
  "content": "新闻事件全文"
}
```

返回知识图谱：`entities`、`relations`、`summary`、`keywords`、`sentiment`、`credibility_hint`。

### `POST /api/event/airdrop`

```json
{
  "content": "新闻事件全文",
  "source": "public",
  "skip_parse": false,
  "credibility": "不确定"
}
```

说明：

- `source` 可取 `public` 或 `private`，分别对应公域或私域注入。
- `skip_parse=true` 时跳过 LLM 图谱解析，快速构造简化事件。
- 推演未启动时，事件会暂存，下一次启动推演时自动注入。
- 推演进行中注入事件时，WebSocket 自动推演会等待注入完成；超时由 `INJECTION_TIMEOUT` 控制。

## 预测与风险

### `GET /api/prediction`

至少需要 3 条历史状态。返回 `available=false` 时表示历史不足。

```json
{
  "success": true,
  "data": {
    "available": true,
    "current_step": 5,
    "prediction": {},
    "trajectory": [],
    "recommendation": {}
  }
}
```

### `GET /api/risk-alerts`

返回当前风险摘要、触发的预警规则和最近预警历史。

## 报告

### 基础推演报告

`POST /api/simulation/finish` 调用 `engine.generate_report()`，生成 `reports/report_*.md` 或 `reports/report_dual_*.md`，然后重置当前引擎状态。

### 智库专报

`POST /api/report/generate` 一次性生成并保存 `reports/intelligence_report_*.md`。

`GET /api/report/stream` 使用 SSE 流式返回：

```text
data: {"content":"# 智库专报..."}

data: {"done":true,"filename":"intelligence_report_1234567890.md","path":"H:/ProjectInsight/reports/intelligence_report_1234567890.md"}
```

智库专报要求：

- 当前引擎已初始化；
- 使用 LLM 模式；
- 已至少运行过一步；
- `llm_population` 已初始化。

## 设置

### `GET /api/settings/llm`

返回当前 LLM 和并发配置（模型名称、Base URL、API Key、并发数、超时等）。

### `POST /api/settings/llm`

保存 LLM 和并发配置。请求体示例：

```json
{
  "simulation_llm": { "model": "DeepSeek-V3", "base_url": "http://...", "api_key": "sk-..." },
  "report_llm": { "model": "DeepSeek-R1", "base_url": "http://...", "api_key": "sk-..." },
  "max_concurrent": 200,
  "connection_pool_size": 400,
  "timeout": 60,
  "max_retries": 3,
  "auto_interval": 3000
}
```

### `GET /api/health/llm`

检测 LLM 连通性。返回 `{ "ok": true/false, "detail": "..." }`。

## 热点新闻

### `GET /api/event/hot-news`

获取今日热点新闻列表，供事件注入弹窗快速选择。

## WebSocket

### 地址

```text
ws://localhost:8000/ws/simulation
```

### 客户端消息

```json
{"action": "start", "params": {"use_llm": true, "use_dual_network": true}}
```

```json
{"action": "step"}
```

```json
{"action": "auto", "interval": 3000}
```

```json
{"action": "pause"}
```

```json
{"action": "resume", "interval": 3000}
```

```json
{"action": "stop"}
```

```json
{"action": "finish"}
```

### 服务端消息

| `type` | 说明 |
| --- | --- |
| `state` | 当前推演状态 |
| `progress` | LLM Agent 推演进度 |
| `report` | WebSocket `finish` 后返回报告路径 |
| `error` | 错误信息 |

同一客户端主机只保留一个活动 WebSocket，新连接会关闭旧连接。消息速率限制由 `WS_RATE_LIMIT` 控制，默认每分钟 60 条。

## 常见错误

| 场景 | 响应 |
| --- | --- |
| 未启动推演 | `{"error":"未初始化"}` 或 `{"success":false,"error":"推演引擎未初始化"}` |
| LLM 模式调用 REST step | `{"error":"LLM 模式请使用 WebSocket"}` |
| 智库专报条件不足 | `{"success":false,"error":"..."}` |
| 报告文件越权或不存在 | HTTP 403/404 |

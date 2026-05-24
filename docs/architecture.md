# 系统架构

更新时间：2026-05-24

## 总览

ProjectInsight 采用 Vue 3 前端 + FastAPI 后端。后端通过 REST API、WebSocket 和 SSE 提供推演、事件注入、Agent 透视、预测风险和报告生成能力。

```text
Vue 3 App
  ├─ 控制面板：模式、参数、人设来源、事件注入
  ├─ 可视化：观点分布、传播网络、趋势曲线、预测轨迹
  ├─ 微观行为透视：Agent 决策链路、现实画像、数值来源
  └─ 报告：基础报告、智库专报、历史报告

FastAPI
  ├─ /api/simulation/*：启动、单步、状态、结束、Agent inspect
  ├─ /api/event/*：新闻解析、事件注入、知识图谱
  ├─ /api/prediction、/api/risk-alerts：预测与风险
  ├─ /api/profiles/*：用户自定义资料画像的上传、构建和列表
  ├─ /api/report/*：报告生成、流式生成、读取、下载、打开
  └─ /ws/simulation：LLM 推演和实时状态推送

Simulation Layer
  ├─ SimulationEngine：单层网络，数学模型 + LLM 模式
  ├─ SimulationEngineDual：双层网络，公域 + 私域
  ├─ RealisticPopulation：内置现实画像、用户资料画像加载、缓存、数值来源
  ├─ LLM Agents：微观决策与快照
  ├─ Knowledge Graph：事件实体关系解析与演化影响
  └─ Report Utils / Analyst Agent：报告口径、样本抽取、LLM 专报
```

## 后端入口

### `backend/app.py`

职责：

- 创建 FastAPI 应用；
- 注册 `simulation`、`event`、`prediction`、`profiles`、`report` 路由；
- 提供健康检查 `GET /`；
- 提供 WebSocket `/ws/simulation`；
- 控制同一客户端主机只保留一个活动 WebSocket；
- 在自动推演中处理事件注入暂停、LLM 进度推送和断连清理。

WebSocket 支持动作：

| action | 说明 |
| --- | --- |
| `start` | 启动推演，可传完整启动参数 |
| `step` | 执行一步 |
| `auto` | 自动推演 |
| `pause` | 暂停自动推演，保留引擎状态 |
| `resume` | 恢复自动推演 |
| `stop` | 停止自动推演 |
| `finish` | 生成基础报告 |

### `backend/state.py`

全局状态使用自定义 `_StateModule` 替换模块对象并通过 `RLock` 保护访问。主要状态包括：

- `state.engine`
- `state.injection_in_progress`
- `state.pending_knowledge_graph`
- `state.pending_event_content`
- `state.prediction_model`

测试必须使用 `reset_global_state` fixture，避免引擎、LLM 单例、图谱解析器和 Agent 快照泄漏。

## 推演引擎

### `SimulationEngine`

文件：`backend/simulation/engine.py`

- 单层社交网络；
- 支持数学模型和 LLM 模式；
- `use_llm=False` 时可用同步 `step()`；
- `use_llm=True` 时应使用 `async_step()`；
- 支持事件注入、知识图谱、基础报告生成和现实画像初始化。

### `SimulationEngineDual`

文件：`backend/simulation/engine_dual.py`

- 默认引擎；
- 公域使用无标度网络，用于模拟微博式传播；
- 私域使用社群网络，用于模拟微信式群组传播；
- 返回 `public_edges`、`private_edges`、`public_negative_rate`、`private_negative_rate` 等双层指标；
- 支持现实画像和 LLM Agent 快照。

## Agent 层

### 理论人设

理论人设由 Agent 类根据内置参数生成，适合机制演示和参数实验。常见属性：

- `opinion`
- `belief_strength`
- `susceptibility`
- `influence`
- `fear_of_isolation`
- `conviction`
- `persona`

### LLM Agent

文件：

- `backend/simulation/llm_agents.py`
- `backend/simulation/llm_agents_dual.py`

LLM Agent 决策后会保存快照，供 `/api/agent/{id}/inspect` 读取。快照包含：

- 旧观点、新观点；
- 接收到的新闻和邻居观点；
- 情绪、行动、评论、推理；
- 邻居舆论气候；
- 现实画像 `realistic_profile`。

## 现实组织画像与资料库画像

文件：`backend/simulation/realistic_population.py`

当前支持画像：

```text
shass_news_institute
上海社科院新闻所
news_institute
```

内置现实组织画像加载流程：

```text
启动参数 population_profile_id
  ├─ 解析工作簿路径：realistic_profile_source_path
  │                  SHASS_NEWS_INSTITUTE_XLSX
  │                  默认本地路径
  ├─ 如果缓存存在且未 refresh，则读取 data/realistic_profiles/*.sanitized.json
  ├─ 如果工作簿存在，则从工作簿构造并刷新缓存
  └─ 如果工作簿和缓存都不存在，则生成匿名合成画像兜底
```

用户自定义资料画像使用同一个 `RealisticPopulationProfile` 数据结构，但来源改为本地资料库：

```text
前端上传资料
  ├─ POST /api/profiles/upload
  ├─ 写入 data/user_profiles/<profile_id>/sources/
  ├─ POST /api/profiles/build
  ├─ 解析 CSV/TSV/JSON/JSONL/TXT/MD/Markdown/Excel
  ├─ 生成 data/realistic_profiles/<profile_id>.sanitized.json
  └─ 启动推演时 population_profile_id=<profile_id> 直接复用缓存
```

资料库元数据保存在：

```text
data/user_profiles/<profile_id>/profile.meta.json
```

现实画像应用位置：

- `apply_realistic_profile_to_llm_population()`：覆盖 LLM Agent 的初始参数与 `persona`；
- `apply_realistic_profile_to_math_population()`：覆盖数学人口数组；
- `/api/agent/{id}/inspect`：无论快照是否存在，都会尝试附加 `realistic_profile`。

现实画像公开字段：

- `name`
- `role_label`
- `department`
- `specialty`
- `title`
- `seniority_label`
- `community_id`
- `is_influencer`
- `generation_trace`
- `public_evidence`
- `search_queries`

敏感字段不会进入缓存和接口：身份证号、手机、邮箱、联系地址、健康、婚姻、血型、户口所在地、出生日期等。

用户自定义资料画像会优先识别这些字段：

- `姓名/name`
- `部门/单位/机构/department`
- `职称/职务/岗位/title`
- `研究方向/专业/领域/specialty`
- `年龄/age`
- `工龄/工作年限/work_years`
- `本单位工龄/本单位年限/org_years`
- `简介/摘要/内容/报道/文章/notes`

识别不到姓名时，系统会生成稳定的“资料成员”编号；识别不到研究方向时，会从正文关键词中推断。

## 数值来源

现实画像中的 `generation_trace` 是前端“数值来源”的数据根：

```json
{
  "source": "workbook",
  "inputs": {
    "age_band": "45-54岁",
    "work_years_band": "20-30年",
    "title": "研究员",
    "education": "研究生",
    "degree": "博士",
    "specialty": "舆情治理"
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
```

前端应将内部变量解释为中文：

| 内部字段 | 前端建议文案 |
| --- | --- |
| `seniority_score` | 资历分 |
| `clip` | 把结果限制在合理范围内 |
| `opinion` | 初始态度 |
| `belief_strength` | 信念强度 |
| `influence` | 影响力 |
| `susceptibility` | 易感性 |
| `fear_of_isolation` | 孤立担忧 |
| `conviction` | 立场坚定度 |

## 事件与知识图谱

文件：

- `backend/routers/event.py`
- `backend/simulation/graph_parser_agent.py`
- `backend/simulation/knowledge_evolution.py`

事件注入分三段：

1. 解析：完整模式调用 LLM 提取知识图谱；快速模式构造简化图谱。
2. 封装：写入事件内容、来源、可信度、情感和图谱。
3. 广播：根据 `source` 注入公域、私域或全部网络。

如果推演尚未启动，事件会进入 `state.pending_*`，下一次启动时自动注入。

## 预测与风险

文件：

- `backend/simulation/prediction.py`
- `backend/simulation/risk_alert.py`
- `backend/routers/prediction.py`

预测依赖历史状态，少于 3 条历史时返回 `available=false`。当前预测输出包括：

- 当前步数；
- 指标预测区间；
- 未来轨迹；
- 干预建议；
- 风险预警。

## 报告链路

### 基础报告

由 `engine.generate_report()` 生成，保存到 `reports/report_*.md` 或 `reports/report_dual_*.md`。报告会使用 `report_utils.py` 中的统一口径：

- 新闻可信度决定“误信/正确认知”语义；
- 汇总事件池、知识图谱、趋势、风险、权威回应效果；
- 现实画像样本会显示姓名、角色和研究方向。

### 智库专报

文件：

- `backend/simulation/analyst_agent.py`
- `backend/routers/report.py`

`POST /api/report/generate` 一次性生成，`GET /api/report/stream` 流式生成。流式生成完成后会保存完整 Markdown 并发送：

```json
{"done": true, "filename": "...", "path": "..."}
```

报告生成条件：

- 引擎已初始化；
- LLM 模式；
- 已至少推演一步；
- `llm_population` 可用。

## 前端结构

当前前端是单文件 Vue SPA：

```text
frontend/src/
  App.vue
  main.js
  assets/
```

主要交互：

- 通过 WebSocket `/ws/simulation` 启动和推进 LLM 推演；
- 通过 REST 获取 Agent 透视、预测、风险和报告；
- ECharts 绘制观点分布、传播网络和趋势；
- 点击网络节点触发 `/api/agent/{id}/inspect`；
- 现实画像模式在节点、弹窗和微观透视中显示姓名。

## 配置与环境变量

| 变量 | 说明 |
| --- | --- |
| `LLM_BASE_URL` | OpenAI 兼容 LLM 服务地址 |
| `LLM_API_KEY` | LLM API Key |
| `LLM_MODEL` | 模型名 |
| `LLM_CONCURRENCY_PROFILE` | `auto`、`local`、`remote` |
| `LLM_MAX_CONCURRENT` | LLM 最大并发，留空自动计算 |
| `LLM_TIMEOUT` | LLM 请求超时 |
| `SHASS_NEWS_INSTITUTE_XLSX` | 上海社科院新闻所人员工作簿路径 |
| `REALISTIC_PROFILE_CACHE_DIR` | 现实画像和自定义资料画像缓存目录，默认 `data/realistic_profiles` |
| `USER_PROFILE_LIBRARY_DIR` | 用户资料库目录，默认 `data/user_profiles` |
| `PUBLIC_EVIDENCE_QUEUE_DIR` | 公开证据候选队列目录 |
| `REPORT_LLM_TIMEOUT` | 智库专报 LLM 超时 |
| `REPORT_LLM_MAX_TOKENS` | 智库专报单次输出长度 |
| `REPORT_LLM_TEMPERATURE` | 智库专报温度 |
| `INJECTION_TIMEOUT` | 推演中事件注入等待超时 |
| `WS_RATE_LIMIT` | WebSocket 每分钟消息限制 |

## 架构注意事项

- 后端重启会清空内存态推演。
- `SimulationEngineDual` 是默认路径，测试单层网络需显式 `use_dual_network=false`。
- LLM 模式必须用异步推演，不能调用同步 `step()`。
- 报告打开接口只允许打开 `reports/` 下的 `.md` 文件。
- 现实画像和自定义资料画像中的姓名当前按演示验证需求展示；新增画像时仍应最小化采集和输出字段。
- `data/user_profiles/` 和用户自定义缓存默认视为本地资料，不应提交到公开仓库。

# 觉测·洞鉴 - 信息茧房推演系统

更新时间：2026-05-11

本系统是一个多智能体舆论认知推演平台，用于观察新闻事件、信息源可信度、算法茧房、社交网络结构和权威回应对群体态度的影响。当前系统同时支持“理论人设”“内置现实组织画像”和“用户自定义资料画像”三类 Agent 群体。

## 当前能力

| 能力 | 当前实现 |
| --- | --- |
| 推演引擎 | 数学模型 `SimulationEngine`；LLM 驱动 `SimulationEngine` / `SimulationEngineDual` |
| 网络结构 | 单层网络；双层网络（公域无标度网络 + 私域社群网络，默认启用） |
| Agent 来源 | 理论人设；内置现实画像 `shass_news_institute`；用户自定义资料画像 |
| 事件处理 | 新闻文本解析为知识图谱；支持快速注入和推演中注入 |
| 微观透视 | 点击节点查看 Agent 决策链路、姓名、角色、当前态度、邻居舆论气候和数值来源 |
| 报告 | 基础推演报告；LLM 智库专报；流式生成后自动保存 Markdown |
| 预测与风险 | 预测区间、轨迹外推、风险预警和干预建议 |

## 三类人设

### 理论人设

理论人设由系统内置的认知类型生成，适合解释模型机制、做参数敏感性分析和快速演示。它强调可控性和泛化性。

### 现实组织画像

当前现实画像 ID：

```text
shass_news_institute
```

该画像对应上海社科院新闻所 27 人组织样本。启动推演时传入 `population_profile_id: "shass_news_institute"` 后，系统会：

- 将 Agent 数量固定为画像人数；
- 用工作簿或缓存中的姓名、职务、研究方向、资历分组等生成初始参数；
- 在前端微观透视中显示姓名，便于演示时验证具体节点行为；
- 保留“数值来源”，解释初始观点、信念强度、影响力、易感性、沉默压力等数值如何得到；
- 排除身份证号、手机、联系地址、健康、婚姻、出生日期等敏感字段。

如果找不到原始工作簿且没有缓存，系统会生成匿名合成画像作为兜底，此时不代表真实人员态度。

### 用户自定义资料画像

用户可以在前端“样本画像 -> 自定义资料画像 -> 资料库构建”上传表格、文章、报道或 Markdown 文档，系统会把资料保存在本地资料库：

```text
data/user_profiles/<profile_id>/sources/
```

点击“离线构建画像”后，后端会解析资料、抽取姓名/部门/职称/研究方向/简介等字段，并生成可复用缓存：

```text
data/realistic_profiles/<profile_id>.sanitized.json
```

之后启动推演只读取缓存，不需要每次重新解析原始资料。支持的来源包括 `CSV`、`TSV`、`JSON`、`JSONL`、`TXT`、`MD`、`Markdown`；安装 `pandas/openpyxl` 后也支持 Excel。

## 运行方式

### 后端

```bash
pip install -r requirements.txt
uvicorn backend.app:app --reload --port 8000
```

LLM 模式需要 `.env`：

```bash
LLM_BASE_URL=http://your-llm-server:port/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
LLM_CONCURRENCY_PROFILE=auto
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

默认访问：

```text
http://localhost:3000
```

前端开发环境会访问 `http://localhost:8000` 和 `ws://localhost:8000/ws/simulation`。

## 常用流程

1. 可选：先注入新闻事件，让系统解析知识图谱。
2. 选择理论人设、新闻所现实画像或自定义资料画像。
3. 启动推演。LLM 模式通过 WebSocket 推进，数学模式也可用 REST 单步推进。
4. 观察观点分布、信息传播网络、趋势曲线、风险预警和预测轨迹。
5. 点击网络节点，查看微观行为透视、真实姓名、决策链路和数值来源。
6. 生成基础报告或智库专报。

## 文档导航

| 文档 | 内容 |
| --- | --- |
| [API 接口文档](api.md) | 当前 REST、WebSocket、SSE 接口和字段 |
| [系统架构](architecture.md) | 后端、前端、状态、现实画像和报告链路 |
| [推演机制](simulation.md) | 理论人设、现实画像、数学模型、LLM 和双层网络 |
| [指标解释](metrics.md) | 前端指标、微观数值、数值来源和可信度口径 |
| [部署指南](deployment.md) | 本地、生产、环境变量、现实画像和排障 |
| [v3.0 设计方案](design.md) | 心理学、记忆、环境与技能系统设计背景 |
| [语义重构映射](refactor_mapping.md) | 新旧字段命名映射与兼容策略 |

## 核心目录

```text
backend/
  app.py                         FastAPI 入口与 WebSocket
  state.py                       线程安全全局状态
  routers/
    simulation.py                推演、状态、Agent 透视
    event.py                     新闻解析与事件注入
    prediction.py                预测与风险
    report.py                    报告生成、读取、下载、打开
  simulation/
    engine.py                    单层网络引擎，数学 + LLM
    engine_dual.py               双层网络引擎
    realistic_population.py      现实组织画像、自定义资料画像加载与数值来源
    llm_agents.py                单层 LLM Agent
    llm_agents_dual.py           双层 LLM Agent
    report_utils.py              报告共享口径与格式化工具
frontend/
  src/App.vue                    Vue 3 单文件前端
data/
  realistic_profiles/            现实画像缓存
  user_profiles/                 用户上传资料库，默认不提交 Git
  public_evidence_queue/         公开证据候选队列
reports/                         生成的 Markdown 报告
tests/                           测试套件
```

## 当前注意事项

- 后端重启会清空当前内存中的推演状态。
- LLM 模式应使用 `async_step()` 或 WebSocket；同步 `step()` 仅适用于数学模型。
- 智库专报需要 LLM 模式且至少完成一步推演。
- 现实画像和自定义资料画像展示姓名是为了演示验证；生成和缓存仍应避免写入不必要的敏感字段。
- `data/user_profiles/` 和自定义 `data/realistic_profiles/*.sanitized.json` 默认只作为本地资料库和缓存使用。
- `docs/design.md` 是设计背景文档，实际接口以 `docs/api.md` 和当前代码为准。

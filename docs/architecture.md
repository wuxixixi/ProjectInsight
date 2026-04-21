# 系统架构说明

## 整体架构

觉测·洞鉴采用前后端分离架构，支持双模式推演（沙盘/新闻），通过 WebSocket 实现实时推演状态同步：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Vue 3 Frontend                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐  │
│  │ 控制面板    │  │ 可视化面板  │  │ 预测面板    │  │ 智能体透视面板    │  │
│  │ (沙盘/新闻) │  │ (观点分布)  │  │ (轨迹展示)  │  │ (决策过程)        │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────────┬─────────┘  │
│         │                │                │                   │            │
│         └────────────────┴────────────────┴───────────────────┘            │
│                                   │                                         │
│                     WebSocket + REST API                                    │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────────────┐
│                          FastAPI Backend                                    │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                         API Layer                                   │   │
│  │  /api/simulation/*  /api/agent/*  /api/report/*  /api/prediction/* │   │
│  │  /api/event/*       /api/docs/*                                    │   │
│  └────────────────────────────────┬───────────────────────────────────┘   │
│                                   │                                        │
│  ┌────────────────────────────────┼────────────────────────────────────┐  │
│  │                  Simulation Engine Layer                            │  │
│  │                                                                     │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │                 双模式引擎架构                                │  │  │
│  │  │                                                              │  │  │
│  │  │   ┌─────────────────┐       ┌─────────────────────────────┐ │  │  │
│  │  │   │   沙盘模式       │       │       新闻模式              │ │  │  │
│  │  │   │ (Sandbox Mode)  │       │    (News Mode)              │ │  │  │
│  │  │   │                 │       │                             │ │  │  │
│  │  │   │ • 参数驱动      │       │ • 真实分布锚定              │ │  │  │
│  │  │   │ • 快速探索      │       │ • 预测区间                  │ │  │  │
│  │  │   │ • 机制研究      │       │ • 风险预警                  │ │  │  │
│  │  │   │                 │       │ • 干预建议                  │ │  │  │
│  │  │   └─────────────────┘       └─────────────────────────────┘ │  │  │
│  │  │                                                              │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐   │  │
│  │  │ Engine (数学)  │  │ EngineDual     │  │ KnowledgeDriven    │   │  │
│  │  │               │  │ (双层网络)     │  │ Evolution          │   │  │
│  │  └───────┬───────┘  └───────┬────────┘  └──────────┬─────────┘   │  │
│  │          │                  │                       │             │  │
│  │  ┌───────┴──────────────────┴───────────────────────┴────────┐   │  │
│  │  │                    Agent Population                        │   │  │
│  │  │  ┌─────────────┐  ┌───────────────┐  ┌─────────────────┐  │   │  │
│  │  │  │  agents.py  │  │ llm_agents.py │  │ llm_agents_     │  │   │  │
│  │  │  │  (数学模型) │  │ (LLM驱动)     │  │ dual.py(双层)   │  │   │  │
│  │  │  └─────────────┘  └───────────────┘  └─────────────────┘  │   │  │
│  │  └────────────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                       LLM Layer                                    │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────┐  │  │
│  │  │  LLM Client     │  │ GraphParser     │  │ Analyst Agent     │  │  │
│  │  │  (DeepSeek)     │  │ (知识图谱解析)  │  │ (智库专报生成)    │  │  │
│  │  └─────────────────┘  └─────────────────┘  └───────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    Prediction Layer                                │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────┐  │  │
│  │  │ TrajectoryModel │  │ RiskAlertSystem │  │ InterventionPlanner│  │  │
│  │  │ (轨迹预测)      │  │ (风险预警)      │  │ (干预建议)        │  │  │
│  │  └─────────────────┘  └─────────────────┘  └───────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 后端组件

#### 1. API Layer (`backend/app.py`)

- **FastAPI 应用**：提供 REST API 和 WebSocket 接口
- **路由处理**：simulation、agent、report、prediction、event、docs 六大模块
- **CORS 中间件**：支持前端跨域访问
- **双模式管理**：沙盘/新闻模式切换和状态管理
- **向后兼容层**：API同时接受新旧参数名（如 `response_delay` / `debunk_delay`）

#### 2. Simulation Engine

| 组件 | 文件 | 说明 |
|------|------|------|
| SimulationEngine | `simulation/engine.py` | 单层网络引擎（数学模型/LLM） |
| SimulationEngineDual | `simulation/engine_dual.py` | 双层网络引擎（公域+私域） |
| AgentPopulation | `simulation/agents.py` | 数学模型智能体群体 |
| LLMAgentPopulation | `simulation/llm_agents.py` | LLM 驱动智能体 |
| LLMAgentPopulationDual | `simulation/llm_agents_dual.py` | LLM 驱动智能体（双层网络） |
| KnowledgeDrivenEvolution | `simulation/knowledge_evolution.py` | 知识图谱驱动演化器 |
| GraphParserAgent | `simulation/graph_parser_agent.py` | 知识图谱解析器 |
| AnalystAgent | `simulation/analyst_agent.py` | 智库专报生成 |

#### 3. LLM Layer

| 组件 | 文件 | 说明 |
|------|------|------|
| LLM Client | `llm/client.py` | DeepSeek API 封装，支持并发控制 |
| GraphParserAgent | `simulation/graph_parser_agent.py` | 知识图谱解析（实体/关系抽取） |

#### 4. Prediction Layer（新闻模式专用）

| 组件 | 文件 | 说明 |
|------|------|------|
| TrajectoryModel | `simulation/prediction.py` | 轨迹预测，输出置信区间 |
| RiskAlertSystem | `simulation/risk_alert.py` | 风险预警系统 |
| InterventionPlanner | `simulation/prediction.py` | 干预时机和策略建议 |

#### 5. Knowledge Graph Pipeline

```
   新闻文本输入
         │
         ▼
┌─────────────────┐
│ GraphParserAgent│
│   (LLM Prompt)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LLM API 调用 (10-60秒)                                              │
│  • 实体提取: 人物、组织、地点、事件、概念                             │
│  • 关系抽取: 动作类型、关系类型                                       │
│  • 语义摘要: 事件核心内容                                            │
│  • 情感分析: 正面/负面/中性/争议                                      │
│  • 可信度评估: 高可信/低可信/不确定                                   │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  知识图谱 JSON                                                      │
│  {                                                                  │
│    "entities": [{"name": "", "type": "", "importance": 1-5}],       │
│    "relations": [{"source": "", "target": "", "action": ""}],       │
│    "summary": "...",                                                │
│    "sentiment": "中性",                                              │
│    "credibility_hint": "不确定"                                      │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Agent 决策上下文 + 知识驱动演化                                     │
│  • 实体影响力计算                                                   │
│  • 关系立场映射                                                     │
│  • 观点增量计算                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 前端组件

```
frontend/src/
├── App.vue              # 主应用组件（含双模式控制、预测面板）
├── main.js             # 入口文件
├── assets/
│   └── main.css        # 全局样式
├── components/
│   ├── ControlPanel.vue    # 参数控制面板（沙盘/新闻配置）
│   ├── OpinionChart.vue    # 观点分布图
│   ├── NetworkGraph.vue    # 网络拓扑图
│   ├── TrendChart.vue      # 趋势曲线图
│   ├── PredictionChart.vue # 预测轨迹图
│   └── AgentDetail.vue     # 智能体透视面板
├── utils/
│   ├── websocket.js    # WebSocket 客户端
│   └── api.js          # REST API 封装
└── public/
    └── sass-logo.png   # 上海社会科学院Logo
```

## 数据模型

### 核心语义抽象

系统采用语义抽象设计，将特定领域术语映射为通用概念：

| UI文案 | 内部命名 | 英文标识 | 说明 |
|--------|----------|----------|------|
| 误信 | 负面信念 | `negative_belief` | 用户相信的错误/有害信息 |
| 正确认知 | 正面信念 | `positive_belief` | 官方正确/有益信息 |
| 权威回应 | 权威回应 | `authority_response` | 官方发布的纠正信息 |

### SimulationParams 核心字段

| 字段名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `mode` | str | "sandbox" | 推演模式 |
| `cocoon_strength` | float | 0.5 | 算法茧房强度 |
| `response_delay` | int | 10 | 权威回应延迟步数 |
| `initial_negative_spread` | float | 0.3 | 初始负面信念传播率 |
| `response_credibility` | float | 0.7 | 权威回应可信度 |
| `population_size` | int | 200 | Agent 数量 |
| `use_llm` | bool | true | 是否使用 LLM |
| `use_dual_network` | bool | true | 是否使用双层网络 |

> **向后兼容**：旧参数名（如 `debunk_delay`、`initial_rumor_spread`）仍然有效，API会自动映射到新参数名。

### SimulationState 核心字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `negative_belief_rate` | float | 负面信念率（API同时返回 `rumor_spread_rate`） |
| `positive_belief_rate` | float | 正面信念率（API同时返回 `truth_acceptance_rate`） |
| `avg_opinion` | float | 平均观点值 |
| `polarization_index` | float | 极化指数 |
| `silence_rate` | float | 沉默率 |
| `public_negative_rate` | float | 公域负面信念率 |
| `private_negative_rate` | float | 私域负面信念率 |

## 双层网络模型

系统支持模拟公域与私域信息传播的差异：

```
┌─────────────────────────────────────────────┐
│              Public Domain (公域)           │
│   ┌─────────────────────────────────────┐   │
│   │  微博式信息传播                       │   │
│   │  • 无标度网络 (Scale-Free)           │   │
│   │  • 存在超级节点 (大V/官媒)           │   │
│   │  • 信息传播速度快、范围广            │   │
│   └─────────────────────────────────────┘   │
└──────────────────┬──────────────────────────┘
                   │ 跨域传播
┌──────────────────┴──────────────────────────┐
│             Private Domain (私域)           │
│   ┌─────────────────────────────────────┐   │
│   │  微信式社群传播                       │   │
│   │  • 多个独立社群 (Community)          │   │
│   │  • 社群内部连接紧密                  │   │
│   │  • 跨社群传播较难                    │   │
│   └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## 配置管理

### 环境变量

在 `.env` 文件中配置：

```bash
# DeepSeek API 配置
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# LLM 并发配置
LLM_CONCURRENCY_PROFILE=auto  # local/remote/auto

# 服务器配置
HOST=0.0.0.0
PORT=8000
```

### 推演参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| mode | sandbox | 推演模式（sandbox/news） |
| cocoon_strength | 0.5 | 算法茧房强度 |
| response_delay | 10 | 权威回应延迟步数 |
| population_size | 200 | Agent 数量 |
| initial_negative_spread | 0.3 | 初始误信率（沙盘模式） |
| init_distribution | null | 真实分布锚定（新闻模式） |
| use_llm | true | 是否使用 LLM 模式 |
| use_dual_network | true | 是否使用双层网络 |
| num_communities | 8 | 私域社群数量 |

## 扩展开发

### 添加新的推演模式

1. 在 `simulation/` 目录创建新的引擎类，继承基础接口
2. 实现 `initialize()`, `step()`, `current_state` 方法
3. 在 `app.py` 添加新的路由或扩展现有路由
4. 在前端 `ControlPanel.vue` 添加模式切换选项

### 添加新的 LLM Provider

1. 修改 `llm/client.py`，添加新的 provider 支持
2. 在 `LLMConfig` 中添加配置选项
3. 更新 Agent 类的 prompt 模板以适配新 provider

### 添加新的可视化图表

1. 在 `frontend/src/components/` 创建新的 Vue 组件
2. 在 `App.vue` 中引入并布局
3. 实现 WebSocket 状态监听和数据绑定

### 添加新的预测模型

1. 在 `simulation/prediction.py` 中扩展 `TrajectoryModel`
2. 添加新的预测算法（如时间序列、蒙特卡洛等）
3. 在 API 层暴露新的预测接口

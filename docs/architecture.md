# 系统架构说明

## 整体架构

觉测·洞鉴采用前后端分离架构，通过 WebSocket 实现实时推演状态同步：

```
┌─────────────────────────────────────────────────────────────────┐
│                        Vue 3 Frontend                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ 控制面板    │  │ 可视化面板  │  │ 智能体透视面板          │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                     │               │
│         └────────────────┼─────────────────────┘               │
│                          │ WebSocket + REST API                │
└──────────────────────────┼──────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                    FastAPI Backend                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API Layer                              │  │
│  │  /api/simulation/*  /api/agent/*  /api/report/*         │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────┼───────────────────────────────┐  │
│  │              Simulation Engine Layer                      │  │
│  │  ┌────────────────┐  ┌────────────────────────────┐     │  │
│  │  │ Engine (数学模型)│  │ EngineDual (双层网络)     │     │  │
│  │  └───────┬────────┘  └─────────────┬──────────────┘     │  │
│  │          │                         │                     │  │
│  │  ┌───────┴─────────────────────────┴───────────────┐    │  │
│  │  │              Agent Population                    │    │  │
│  │  │  ┌─────────────┐  ┌────────────────────────┐   │    │  │
│  │  │  │  agents.py  │  │   llm_agents.py       │   │    │  │
│  │  │  │  (数学模型)  │  │   (LLM驱动)           │   │    │  │
│  │  │  └─────────────┘  └────────────────────────┘   │    │  │
│  │  └─────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    LLM Layer                             │  │
│  │  ┌─────────────────┐  ┌─────────────────────────────┐    │  │
│  │  │  LLM Client     │  │  Analyst Agent              │    │  │
│  │  │  (DeepSeek)     │  │  (智库专报生成)            │    │  │
│  │  └─────────────────┘  └─────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 后端组件

#### 1. API Layer (`backend/app.py`)

- **FastAPI 应用**：提供 REST API 和 WebSocket 接口
- **路由处理**：simulation、agent、report 三大模块
- **CORS 中间件**：支持前端跨域访问

#### 2. Simulation Engine

| 组件 | 文件 | 说明 |
|------|------|------|
| SimulationEngine | `simulation/engine.py` | 单层网络数学模型引擎 |
| SimulationEngineDual | `simulation/engine_dual.py` | 双层网络引擎（公域+私域） |
| AgentPopulation | `simulation/agents.py` | 数学模型智能体群体 |
| LLM Agents | `simulation/llm_agents.py` | LLM 驱动智能体 |
| Analyst Agent | `simulation/analyst_agent.py` | 智库专报生成 |

#### 3. LLM Layer

| 组件 | 文件 | 说明 |
|------|------|------|
| LLM Client | `llm/client.py` | DeepSeek API 封装，支持并发控制 |

### 前端组件

```
frontend/src/
├── App.vue              # 主应用组件
├── main.js             # 入口文件
├── assets/
│   └── main.css        # 全局样式
├── components/
│   ├── ControlPanel.vue    # 参数控制面板
│   ├── OpinionChart.vue    # 观点分布图
│   ├── NetworkGraph.vue    # 网络拓扑图
│   ├── TrendChart.vue      # 趋势曲线图
│   └── AgentDetail.vue     # 智能体透视面板
└── utils/
    ├── websocket.js    # WebSocket 客户端
    └── api.js          # REST API 封装
```

## 数据流

### 推演流程

```
1. 前端发送参数
      ↓
2. 后端创建 SimulationEngine
      ↓
3. 初始化 Agent 群体 + 构建社交网络
      ↓
4. WebSocket 循环:
   - 执行单步推演
   - 计算统计指标
   - 推送状态到前端
      ↓
5. 推演结束 → 生成报告
```

### WebSocket 消息协议

**客户端 → 服务端：**
```json
{"action": "start", "params": {...}}
{"action": "step"}
{"action": "auto", "interval": 2000}
{"action": "stop"}
{"action": "finish"}
```

**服务端 → 客户端：**
```json
{"type": "state", "data": {...}}
{"type": "progress", "step": 1, "total": 200}
{"type": "error", "message": "..."}
```

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
| cocoon_strength | 0.5 | 算法茧房强度 |
| debunk_delay | 10 | 辟谣延迟步数 |
| population_size | 200 | Agent 数量 |
| initial_rumor_spread | 0.3 | 初始谣言传播率 |
| use_llm | true | 是否使用 LLM 模式 |
| use_dual_network | true | 是否使用双层网络 |
| num_communities | 8 | 私域社群数量 |

## 扩展开发

### 添加新的推演模式

1. 在 `simulation/` 目录创建新的引擎类，继承基础接口
2. 实现 `initialize()`, `step()`, `current_state` 方法
3. 在 `app.py` 添加新的路由或扩展现有路由

### 添加新的 LLM Provider

1. 修改 `llm/client.py`，添加新的 provider 支持
2. 在 `LLMConfig` 中添加配置选项
3. 更新 Agent 类的 prompt 模板以适配新 provider

### 添加新的可视化图表

1. 在 `frontend/src/components/` 创建新的 Vue 组件
2. 在 `App.vue` 中引入并布局
3. 实现 WebSocket 状态监听和数据绑定

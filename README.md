# 觉测·洞鉴 - 信息茧房推演系统

> 多智能体舆论认知干预沙盘 v3.0

**在线演示**: http://101.34.62.149

可视化模拟算法推荐与官方辟谣对群体观点的影响，支持 LLM 驱动的智能体决策和智库专报自动生成。

## v3.0 新特性

### 🧠 心理学驱动模型
- **马斯洛需求层次**：五层需求影响信息接受度
  - 生理/安全/社交/尊重/认知需求动态主导
  - 需求-内容匹配矩阵计算 receptivity
- **计划行为理论 (TPB)**：预测传播行为
  - 态度 + 主观规范 + 知觉行为控制 → 行为意向
  - 六种行为预测：SHARE/COMMENT/VERIFY/OBSERVE/SILENCE/REJECT

### 📊 双维度信念系统
- **rumor_trust**：负面信念信任度 [-1, 1]
- **truth_trust**：正面信念信任度 [-1, 1]
- 兼容旧版 `opinion = truth_trust - rumor_trust`

### 🌐 分层环境架构
- **AlgorithmEnv**：算法茧房效应、推荐曝光
- **SocialEnv**：网络拓扑、意见领袖、社交压力
- **TruthEnv**：辟谣干预、可信度衰减

### 💾 三层记忆系统
- **短期记忆**：最近 10 条交互 (deque)
- **长期记忆**：SQLite 持久化存储
- **认知缓冲**：待处理的决策线索

## 核心功能

### 推演模式
- **数学模型模式**：基于数学公式的快速推演，适合参数探索
- **LLM 驱动模式**：基于大语言模型的智能体决策，模拟真实人类认知行为

### 主要特性
- **算法茧房效应模拟**：可调节的推荐算法强化程度，观察观点极化过程
- **社交网络传播**：基于小世界/无标度网络的个体交互模型
- **官方辟谣机制**：可设置延迟时间，研究辟谣时机对舆论的影响
- **智能体透视**：点击网络节点查看 Agent 的完整决策过程和人设信息
- **智库专报生成**：基于 LLM 自动生成专业的舆情分析报告

### 实时可视化
- 群体观点分布直方图
- 信息传播网络拓扑（可交互）
- 舆论演化趋势曲线

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+, FastAPI, NumPy, NetworkX, DeepSeek-V3 |
| 前端 | Vue 3, Vite, ECharts, D3.js, Marked |
| 测试 | pytest, pytest-asyncio |
| v3新增 | Pydantic v2, SQLite (memory), AsyncIO |

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境 (推荐)
conda create -n info-cocoon python=3.10
conda activate info-cocoon

# 或使用 venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

### 2. 安装依赖

```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

### 3. 启动服务

**终端 1 - 后端服务：**
```bash
uvicorn backend.app:app --reload --port 8000
```

**终端 2 - 前端开发服务器：**
```bash
cd frontend
npm run dev
```

访问 http://localhost:3000 打开界面。

## 使用说明

### 参数说明

| 参数 | 范围 | 说明 |
|------|------|------|
| 推演模式 | LLM驱动/数学模型 | LLM模式模拟真实人类决策，数学模型快速推演 |
| 算法茧房强度 | 0 ~ 1 | 越高越容易强化用户既有观点 |
| 权威回应延迟 | 0 ~ 30 步 | 负面信息传播多久后发布权威回应 |
| 初始负面信念率 | 10% ~ 60% | 初始误信负面信息的人群比例 |
| Agent数量 | 50 ~ 500 | 模拟群体规模 |
| 社交网络类型 | 小世界/无标度/随机 | 网络拓扑结构 |

### 操作流程

1. 选择推演模式（LLM驱动或数学模型）
2. 调整左侧控制面板的参数
3. 点击「开始推演」启动模拟
4. 观察右侧三个可视化面板的变化
5. 可随时停止并重新调整参数
6. 推演结束后生成报告或智库专报

### 可视化解读

- **观点分布图**：红色=相信谣言，橙色=中立，绿色=相信真相
- **传播网络图**：节点颜色代表观点，大小代表影响力，**点击节点查看 Agent 详情**
- **趋势曲线图**：追踪谣言传播率、真相接受率、极化指数等指标

## 智库专报功能

在 LLM 驱动模式下，推演结束后可生成专业的智库分析专报。

### 专报特点
- 由 AI 分析师智能体撰写
- 包含宏观趋势分析和微观个体切片
- 引用典型 Agent 的决策过程和评论
- 提供专业的政策建议

### 专报结构
1. **演练核心摘要**：关键发现和结论
2. **参数设定与宏观趋势分析**：数据驱动的趋势解读
3. **典型个体认知切片分析**：6个代表性 Agent 深度分析
4. **舆论干预政策建议**：切实可行的建议

### 使用方式
1. 选择「LLM驱动」模式运行推演
2. 推演结束后点击「智库专报」按钮
3. 等待 10-20 秒生成报告
4. 可导出 Markdown 文件

## 项目结构

```
ProjectInsight/
├── backend/                 # Python 后端
│   ├── app.py              # FastAPI 主入口
│   ├── simulation/         # 推演核心逻辑
│   │   ├── engine.py       # 模拟引擎
│   │   ├── agents.py       # 数学模型智能体
│   │   ├── llm_agents.py   # LLM 驱动智能体
│   │   └── analyst_agent.py # 智库分析师 Agent
│   ├── llm/                # LLM 客户端
│   │   └── client.py       # DeepSeek API 封装
│   └── models/             # 数据模型
│       └── schemas.py      # Pydantic 模型定义
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── App.vue         # 主界面组件
│   │   ├── main.js         # 应用入口
│   │   └── assets/
│   │       └── main.css    # 样式文件
│   ├── index.html
│   ├── package.json
│   └── vite.config.js      # Vite 配置 (含代理)
├── reports/                # 生成的报告
├── tests/                  # 测试套件
│   ├── unit/               # 单元测试
│   └── integration/        # 集成测试
└── requirements.txt        # Python 依赖
```

## API 接口

### REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 健康检查 |
| POST | `/api/simulation/start` | 启动模拟 |
| GET | `/api/simulation/step` | 执行单步推演 |
| GET | `/api/simulation/state` | 获取当前状态 |
| POST | `/api/simulation/finish` | 结束并生成基础报告 |
| GET | `/api/agent/{id}/inspect` | 获取 Agent 决策详情 |
| POST | `/api/report/generate` | 生成智库专报 (LLM模式) |
| GET | `/api/report/list` | 获取历史报告列表 |
| GET | `/api/report/content` | 获取报告内容 |
| GET | `/api/report/download` | 下载报告文件 |

### WebSocket

| 路径 | 说明 |
|------|------|
| `/ws/simulation` | 实时推送推演状态 |

**消息格式：**
```json
// 请求
{"action": "start", "params": {...}}  // 启动推演
{"action": "step"}                     // 执行下一步
{"action": "stop"}                     // 停止推演
{"action": "finish"}                   // 结束并生成报告

// 响应
{
  "type": "state",
  "data": {
    "step": 1,
    "agents": [...],
    "edges": [[0, 1], ...],
    "negative_belief_rate": 0.25,
    "positive_belief_rate": 0.15,
    "avg_opinion": -0.12,
    "polarization_index": 0.45
  }
}

// Agent 进度
{
  "type": "progress",
  "data": {"current": 50, "total": 200}
}

// 报告生成完成
{
  "type": "report",
  "data": {
    "report_path": "/path/to/report.md",
    "report_filename": "report_xxx.md"
  }
}
```

## 核心模型

### LLM Agent 决策机制

每个 Agent 具有以下属性：
- **观点 (opinion)**: -1(相信谣言) 到 1(相信真相)
- **信念强度 (belief_strength)**: 越高越难改变观点
- **易感性 (susceptibility)**: 越高越容易受他人影响
- **人设 (persona)**: 7种人设类型，影响决策风格

Agent 通过 LLM 接收邻居观点和辟谣信息，生成：
- 新观点值
- 情绪状态
- 行动选择（转发/评论/观望/辟谣）
- 生成的评论内容

### 观点演化机制

1. **社交影响**：个体受邻居加权平均观点影响
2. **算法茧房**：推荐内容强化既有观点倾向
3. **官方辟谣**：延迟发布真相，影响相信谣言者
4. **LLM 决策**：模拟真实人类的认知决策过程

### 网络类型

- **small_world**：小世界网络（Watts-Strogatz），模拟真实社交网络
- **scale_free**：无标度网络（Barabási-Albert），存在意见领袖
- **random**：随机网络（Erdős-Rényi），基准对照

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 仅运行单元测试
pytest tests/unit/ -v

# 仅运行集成测试
pytest tests/integration/ -v

# 带覆盖率报告
pytest tests/ --cov=backend --cov-report=html
```

## 开发说明

### 后端开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 启动开发服务器（热重载）
uvicorn backend.app:app --reload --port 8000

# 代码格式化
black backend/ tests/

# 类型检查
mypy backend/
```

### 前端开发

```bash
cd frontend

# 开发模式
npm run dev

# 生产构建
npm run build

# 预览构建结果
npm run preview
```

## 环境要求

- Python >= 3.10
- Node.js >= 18.0
- npm >= 9.0

## License

MIT License

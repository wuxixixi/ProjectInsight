# 信息茧房推演系统

可视化模拟算法推荐与官方辟谣对群体观点的影响。

## 功能特性

- **算法茧房效应模拟**：可调节的推荐算法强化程度，观察观点极化过程
- **社交网络传播**：基于小世界/无标度网络的个体交互模型
- **官方辟谣机制**：可设置延迟时间，研究辟谣时机对舆论的影响
- **实时可视化**：
  - 群体观点分布直方图
  - 信息传播网络拓扑
  - 舆论演化趋势曲线

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+, FastAPI, NumPy, NetworkX |
| 前端 | Vue 3, Vite, ECharts, D3.js |
| 测试 | pytest, pytest-asyncio |

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
uvicorn backend.app:app --reload --port 8001
```

**终端 2 - 前端开发服务器：**
```bash
cd frontend
npm run dev
```

访问 http://localhost:3000 打开界面。

> **注意**: 后端默认使用 8001 端口，前端通过 Vite 代理自动转发 API 请求。

## 使用说明

### 参数说明

| 参数 | 范围 | 说明 |
|------|------|------|
| 算法茧房强度 | 0 ~ 1 | 越高越容易强化用户既有观点 |
| 官方辟谣延迟 | 0 ~ 30 步 | 谣言传播多久后发布辟谣信息 |
| 初始谣言传播率 | 10% ~ 60% | 初始相信谣言的人群比例 |

### 操作流程

1. 调整左侧控制面板的参数
2. 点击「开始推演」启动模拟
3. 观察右侧三个可视化面板的变化
4. 可随时停止并重新调整参数

### 可视化解读

- **观点分布图**：红色=相信谣言，橙色=中立，绿色=相信真相
- **传播网络图**：节点颜色代表观点，大小代表影响力
- **趋势曲线图**：追踪谣言传播率、真相接受率、极化指数等指标

## 项目结构

```
ProjectInsight/
├── backend/                 # Python 后端
│   ├── app.py              # FastAPI 主入口
│   ├── simulation/         # 推演核心逻辑
│   │   ├── engine.py       # 模拟引擎
│   │   └── agents.py       # 智能体群体模型
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
├── tests/                  # 测试套件
│   ├── unit/               # 单元测试
│   │   ├── test_engine.py
│   │   ├── test_agents.py
│   │   └── test_schemas.py
│   └── integration/        # 集成测试
│       ├── test_api.py
│       ├── test_websocket.py
│       └── test_e2e.py
└── requirements.txt        # Python 依赖
```

## API 接口

### REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 健康检查 |
| POST | `/api/simulation/start` | 启动模拟，返回初始状态 |
| GET | `/api/simulation/step` | 执行单步推演 |
| GET | `/api/simulation/state` | 获取当前状态 |

### WebSocket

| 路径 | 说明 |
|------|------|
| `/ws/simulation` | 实时推送推演状态 |

**消息格式：**
```json
// 请求
{"action": "step"}      // 执行下一步
{"action": "reset", "params": {...}}  // 重置模拟

// 响应
{
  "step": 1,
  "agents": [...],
  "edges": [[0, 1], ...],
  "opinion_distribution": {"counts": [...], "centers": [...]},
  "rumor_spread_rate": 0.25,
  "truth_acceptance_rate": 0.15,
  "avg_opinion": -0.12,
  "polarization_index": 0.45
}
```

## 模拟报告

每次模拟结束后，系统可生成详细的分析报告，保存在 `reports/` 目录下。

### 报告内容包括：

- **模拟参数**：记录所有输入参数
- **结果摘要**：谣言传播率、真相接受率、极化指数等核心指标
- **详细分析**：茧房效应、辟谣效果、极化趋势分析
- **关键节点**：重要事件时间线
- **建议**：基于结果的改进建议

### 使用方式：

1. 运行模拟后点击「生成分析报告」按钮
2. 报告自动保存为 Markdown 格式
3. 可使用任意 Markdown 阅读器查看

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

## 核心模型

### 观点演化机制

1. **社交影响**：个体受邻居加权平均观点影响
2. **算法茧房**：推荐内容强化既有观点倾向
3. **官方辟谣**：延迟发布真相，影响相信谣言者
4. **随机扰动**：模拟信息环境的不确定性

### 网络类型

- **small_world**：小世界网络（Watts-Strogatz），模拟真实社交网络
- **scale_free**：无标度网络（Barabási-Albert），存在意见领袖
- **random**：随机网络（Erdős-Rényi），基准对照

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

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

信息茧房推演系统 - 可视化模拟算法推荐、官方辟谣对群体观点的影响。支持“数学模型”与“LLM驱动”两种推演模式。

## 技术栈

- **后端**: Python 3.10+, FastAPI, NumPy, NetworkX, DeepSeek-V3 (via API)
- **前端**: Vue 3, Vite, ECharts, D3.js, Marked
- **测试**: pytest, pytest-asyncio

## 常用命令

### 后端
```bash
# 安装依赖
pip install -r requirements.txt

# 启动后端服务
uvicorn backend.app:app --reload --port 8000

# 运行所有测试
pytest tests/ -v

# 运行特定测试集
pytest tests/unit/ -v        # 单元测试
pytest tests/integration/ -v  # 集成测试

# 运行测试并生成覆盖率报告
pytest tests/ --cov=backend --cov-report=html

# 代码格式化与检查
black backend/ tests/
mypy backend/
```

### 前端
```bash
cd frontend
npm install
npm run dev      # 开发服务器 (http://localhost:3000)
npm run build    # 生产构建
```

## 架构与核心逻辑

### 1. 整体结构
- `backend/`: 包含 FastAPI 接口、推演引擎、LLM 客户端及数据模型。
- `frontend/`: Vue 3 单页应用，通过 WebSocket (`/ws/simulation`) 和 REST API 与后端交互。
- `tests/`: 分为 `unit` (核心算法/逻辑) 和 `integration` (API/端到端流)。

### 2. 推演引擎 (`backend/simulation/`)
系统支持两种互斥的模拟模式：
- **数学模型模式**: 基于公式的快速演化，逻辑主要在 `agents.py` 和 `engine.py`。
- **LLM 驱动模式**: 模拟真实人类认知，由 `llm_agents.py` 和 `engine_dual.py` 实现。每个 Agent 根据人设 (Persona) 通过 LLM 决定观点演化。
- **分析报告**: `analyst_agent.py` 负责在推演结束后分析数据并生成智库专报。

### 3. 核心机制
- **观点演化**: 观点值 $\in [-1, 1]$ (相信谣言 $\leftrightarrow$ 相信真相)。受社交影响、算法茧房强化、官方辟谣三个维度驱动。
- **网络拓扑**: 支持 `small_world` (小世界), `scale_free` (无标度), `random` (随机) 三种社交网络结构。
- **LLM 交互**: 通过 `backend/llm/client.py` 封装 DeepSeek API。

## 运行环境

- Python 3.10+
- Node.js 18+
- 推荐使用 conda 或 venv 隔离环境

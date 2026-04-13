# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

信息茧房推演系统 - 可视化模拟算法推荐、官方辟谣对群体观点的影响。

## 技术栈

- **后端**: Python 3.10+ (FastAPI, NumPy, NetworkX)
- **前端**: Vue 3 + Vite + D3.js/ECharts

## 常用命令

### 后端
```bash
# 安装依赖
pip install -r requirements.txt

# 启动后端服务
uvicorn backend.app:app --reload --port 8000

# 运行测试
pytest tests/
```

### 前端
```bash
cd frontend
npm install
npm run dev      # 开发服务器
npm run build    # 生产构建
```

## 架构

```
├── backend/           # Python 后端
│   ├── app.py         # FastAPI 主入口
│   ├── simulation/    # 推演核心逻辑
│   └── models/        # 数据模型
├── frontend/          # Vue 3 前端
│   ├── src/components/  # Vue 组件
│   └── src/views/       # 页面视图
└── data/              # 模拟数据
```

## 运行环境

- Python 3.10+
- Node.js 18+
- 推荐: conda/virtualenv 隔离环境

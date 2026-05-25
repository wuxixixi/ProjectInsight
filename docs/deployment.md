# 部署指南

更新时间：2026-05-24

## 环境要求

| 组件 | 最低版本 | 建议版本 |
| --- | --- | --- |
| Python | 3.10 | 3.11+ |
| Node.js | 18 | 20+ |
| npm | 9 | 10+ |

LLM 模式需要可访问的 OpenAI 兼容接口。数学模型模式可以不配置 LLM。

## 本地开发

### 后端

```bash
cd H:\ProjectInsight
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://localhost:8000/
```

### 前端

```bash
cd H:\ProjectInsight\frontend
npm install
npm run dev
```

访问：

```text
http://localhost:3000
```

当前前端开发环境会直接连接：

```text
REST: http://localhost:8000
WS:   ws://localhost:8000/ws/simulation
```

`vite.config.js` 仍保留 `/api` 和 `/ws` 代理，便于兼容同源访问。

## LLM 配置

复制 `.env.example` 为 `.env`：

```bash
LLM_BASE_URL=http://your-llm-server:port/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name

LLM_CONCURRENCY_PROFILE=auto
LLM_MAX_CONCURRENT=
LLM_TIMEOUT=60
LLM_MAX_RETRIES=5
```

说明：

| 变量 | 说明 |
| --- | --- |
| `LLM_BASE_URL` | OpenAI 兼容服务地址，例如 `http://localhost:11434/v1` |
| `LLM_API_KEY` | API Key，本地模型可填占位值 |
| `LLM_MODEL` | 模型名 |
| `LLM_CONCURRENCY_PROFILE` | `auto`、`local`、`remote` |
| `LLM_MAX_CONCURRENT` | 留空时按人口规模自动计算 |
| `LLM_TIMEOUT` | 单次请求超时 |
| `LLM_MAX_RETRIES` | 重试次数 |

本地 Ollama 示例：

```bash
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen:7b
LLM_CONCURRENCY_PROFILE=local
```

不要再使用旧文档中的 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL` 作为主配置名；当前代码读取的是 `LLM_*`。

## 现实画像配置

当前支持上海社科院新闻所现实画像：

```text
population_profile_id = shass_news_institute
```

环境变量：

```bash
SHASS_NEWS_INSTITUTE_XLSX=E:\wuxi_xws\名单\251231 新闻所在职人员名单.xlsx
REALISTIC_PROFILE_CACHE_DIR=data/realistic_profiles
PUBLIC_EVIDENCE_QUEUE_DIR=data/public_evidence_queue
USER_PROFILE_LIBRARY_DIR=data/user_profiles
```

加载规则：

1. 启动参数传入 `population_profile_id`。
2. 如果 `data/realistic_profiles/shass_news_institute.sanitized.json` 存在且未要求刷新，直接读取缓存。
3. 如果要求刷新或缓存不存在，读取 `SHASS_NEWS_INSTITUTE_XLSX` 或 `realistic_profile_source_path`。
4. 如果工作簿和缓存都不存在，生成匿名合成画像兜底。

刷新缓存的启动参数：

```json
{
  "population_profile_id": "shass_news_institute",
  "refresh_realistic_profile": true,
  "realistic_profile_source_path": "E:\\wuxi_xws\\名单\\251231 新闻所在职人员名单.xlsx"
}
```

安全边界：

- 姓名当前会显示在前端和 API 中，用于演示验证；
- 身份证号、手机、邮箱、联系地址、健康、婚姻、出生日期等敏感字段会被排除；
- `include_public_enrichment=true` 只生成候选队列，需人工审核后再使用；
- 新增现实画像时，应默认最小化字段采集和缓存。

## 用户资料画像配置

用户资料画像用于在本地离线构建客户自定义群体。前端入口位于“样本画像 -> 自定义资料画像 -> 资料库构建”。

默认目录：

```text
data/user_profiles/<profile_id>/sources/          原始资料
data/user_profiles/<profile_id>/profile.meta.json 资料库元数据
data/realistic_profiles/<profile_id>.sanitized.json 可复用画像缓存
```

支持来源：

- `CSV`、`TSV`
- `JSON`、`JSONL`
- `TXT`、`MD`、`Markdown`
- `XLSX/XLS`：需要安装 `pandas` 和 `openpyxl`

构建方式：

1. 上传资料：`POST /api/profiles/upload`
2. 离线构建缓存：`POST /api/profiles/build`
3. 启动推演：`population_profile_id=<profile_id>`，`refresh_realistic_profile=false`

前端启动自定义画像时默认不刷新缓存，避免每次推演重新解析原始资料。需要更新画像时，重新上传资料并点击“离线构建画像”。

Git 策略：

- `data/user_profiles/` 默认忽略；
- 用户自定义 `data/realistic_profiles/*.sanitized.json` 默认忽略；
- 内置 `shass_news_institute.sanitized.json` 目前保留为项目既有缓存。

## 报告配置

报告默认保存在：

```text
reports/
```

智库专报相关变量：

```bash
REPORT_LLM_TIMEOUT=120
REPORT_LLM_MAX_TOKENS=2000
REPORT_LLM_TEMPERATURE=0.5
```

接口：

- `POST /api/simulation/finish`：生成基础推演报告，并重置当前引擎；
- `POST /api/report/generate`：一次性生成智库专报；
- `GET /api/report/stream`：SSE 流式生成智库专报，完成后自动保存；
- `GET /api/report/list`：查看报告列表；
- `POST /api/report/open`：打开 `reports/` 下的 `.md` 文件。

## WebSocket 配置

WebSocket 地址：

```text
ws://localhost:8000/ws/simulation
```

相关环境变量：

```bash
WS_RATE_LIMIT=60
INJECTION_TIMEOUT=120
```

说明：

- `WS_RATE_LIMIT` 控制每分钟最多接收多少条客户端消息；
- `INJECTION_TIMEOUT` 控制推演中事件注入时自动推演等待多久；
- 同一客户端主机只保留一个活动 WebSocket，新连接会关闭旧连接。

## 生产部署

### 构建前端

```bash
cd frontend
npm run build
```

构建产物：

```text
frontend/dist
```

### 后端服务

简单部署：

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

### Windows Server 服务守护

Windows Server 生产环境建议使用真正的 Windows Service，不要再用计划任务长期守护。

仓库内提供 `NSSM` 安装脚本：

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\install_windows_service.ps1 -ProjectRoot C:\ProjectInsight
```

该脚本会：

- 清理旧的 `ProjectInsight` 计划任务及残留 `ProjectInsight-Backend` / `ProjectInsight-Now`
- 清理残留 `uvicorn` 进程
- 用 `nssm` 注册 `ProjectInsight` Windows Service
- 配置自动启动、异常退出自动重启、标准输出和错误日志

常用运维命令：

```powershell
Get-Service ProjectInsight
Restart-Service ProjectInsight
Stop-Service ProjectInsight
Start-Service ProjectInsight
```

Gunicorn 示例：

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.app:app --bind 0.0.0.0:8000
```

### Nginx 示例

```nginx
upstream projectinsight_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /opt/ProjectInsight/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://projectinsight_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300;
    }

    location /ws/ {
        proxy_pass http://projectinsight_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
        proxy_buffering off;
    }
}
```

## Docker 参考

后端 Dockerfile：

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY .env.example .env
EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

前端 Dockerfile：

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Compose 示例：

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./reports:/app/reports
      - ./data:/app/data

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
```

如果需要现实画像工作簿，还应挂载工作簿所在目录并设置 `SHASS_NEWS_INSTITUTE_XLSX`。

## 验证命令

后端语法与关键集成：

```bash
python -m py_compile backend/app.py backend/routers/simulation.py backend/routers/report.py
pytest tests/integration/test_api.py tests/integration/test_websocket.py -q
```

前端构建：

```bash
cd frontend
npm run build
```

现实画像单元测试：

```bash
pytest tests/unit/test_realistic_population.py -q
```

该测试也覆盖用户资料画像的离线构建、缓存复用和小样本推演初始化。

## 排障

| 问题 | 常见原因 | 处理 |
| --- | --- | --- |
| 前端无法连接后端 | 后端未启动或端口不是 8000 | 检查 `uvicorn` 和浏览器控制台 |
| WebSocket 连接失败 | 路径仍使用旧 `/ws` | 改为 `/ws/simulation` |
| LLM 推演失败 | `.env` 缺少 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` | 补齐配置并重启后端 |
| 智库专报失败 | 未使用 LLM、未推演、无 `llm_population` | 先启动 LLM 推演并至少运行一步 |
| 现实画像人数不对 | 工作簿列名或过滤结果变化 | 刷新缓存并检查 warnings |
| 前端看不到姓名 | 未启用 `population_profile_id` 或缓存为匿名合成画像 | 检查启动参数和 `data/realistic_profiles` |
| 自定义画像不出现在前端 | 未构建缓存或资料库元数据损坏 | 先调用 `/api/profiles`，再重新上传并离线构建 |
| 自定义画像人数为 0 | 资料文件格式不受支持或没有可识别记录 | 使用 CSV/JSON/Markdown，至少提供姓名或简介 |
| 数值来源为空 | 旧缓存缺少 `generation_trace` | 使用 `refresh_realistic_profile=true` 刷新 |
| 推演中事件注入卡住 | LLM 图谱解析耗时或接口超时 | 使用快速注入或调大 `INJECTION_TIMEOUT` |

## 运维注意

- 后端重启会清空当前内存推演状态。
- `reports/` 和 `data/` 应持久化。
- 生产环境应限制 CORS、启用 HTTPS、保护 `.env`。
- 报告打开接口只允许打开 `reports/` 下的 `.md` 文件。
- 演示环境可显示姓名；公开部署前应重新评估现实画像和用户资料画像展示策略。

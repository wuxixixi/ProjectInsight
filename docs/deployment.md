# 部署指南

## 环境要求

| 组件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Python | 3.10 | 3.11+ |
| Node.js | 18.0 | 20.0+ |
| npm | 9.0 | 10.0+ |

## 开发环境部署

### 1. 克隆项目

```bash
git clone <repository-url>
cd ProjectInsight
```

### 2. 后端部署

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 DeepSeek API Key
```

### 3. 前端部署

```bash
cd frontend
npm install
```

### 4. 启动服务

**终端 1 - 后端:**
```bash
uvicorn backend.app:app --reload --port 8000
```

**终端 2 - 前端:**
```bash
cd frontend
npm run dev
```

访问 http://localhost:3000

---

## 生产环境部署

### 方案一：手动部署

#### 后端配置

1. 安装生产依赖
```bash
pip install gunicorn uvicorn[standard]
```

2. 创建 systemd 服务（Linux）

```ini
# /etc/systemd/system/info-cocoon.service
[Unit]
Description=信息茧房推演系统
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/ProjectInsight
Environment="PATH=/opt/ProjectInsight/venv/bin"
ExecStart=/opt/ProjectInsight/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.app:app --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

3. 启动服务
```bash
sudo systemctl daemon-reload
sudo systemctl enable info-cocoon
sudo systemctl start info-cocoon
```

#### 前端构建

```bash
cd frontend
npm run build
```

构建产物在 `frontend/dist` 目录

#### Nginx 配置

```nginx
upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /opt/ProjectInsight/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket 代理
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

### 方案二：Docker 部署

#### Dockerfile (后端)

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

#### Dockerfile (前端)

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./reports:/app/reports

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
```

---

### 方案三：云平台部署

#### 阿里云 ECS

1. 创建 ECS 实例（推荐 2核4G）
2. 安装 Docker
3. 使用方案二部署

#### 腾讯云 CloudBase

```bash
# 安装 cloudbase CLI
npm install -g @cloudbase/cli

# 部署前端
cloudbase init
cloudbase hosting deploy frontend/dist -e your-env-id
```

---

## LLM 配置

### DeepSeek API

1. 注册 DeepSeek 账号
2. 获取 API Key
3. 在 `.env` 中配置：

```bash
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

### 本地 LLM (Ollama)

如需使用本地模型：

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 拉取模型
ollama pull qwen:7b

# 配置环境变量
DEEPSEEK_BASE_URL=http://localhost:11434/v1
DEEPSEEK_MODEL=qwen:7b
DEEPSEEK_API_KEY=ollama

# 设置并发模式
LLM_CONCURRENCY_PROFILE=local
```

---

## 性能优化

### LLM 并发控制

| Agent 数量 | 推荐并发数 (远程) | 推荐并发数 (本地) |
|------------|------------------|-------------------|
| 50         | 25              | 10                |
| 100        | 50              | 15                |
| 200        | 100             | 20                |
| 500        | 100             | 16                |

### 数据库优化

报告文件存储在 `reports/` 目录，建议：
- 定期清理旧报告
- 使用对象存储（如 OSS）存储报告

### 前端优化

```javascript
// vite.config.js 配置
export default defineConfig({
  build: {
    target: 'es2015',
    minify: 'terser',
    rollupOptions: {
      output: {
        manualChunks: {
          'echarts': ['echarts'],
          'd3': ['d3']
        }
      }
    }
  }
})
```

---

## 监控与日志

### 日志配置

```python
# backend/app.py
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
```

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/

# 检查 WebSocket
wscat -c ws://localhost:8000/ws/simulation
```

---

## 安全配置

### 生产环境建议

1. **修改 API Key**：使用强密钥，定期轮换
2. **限制 CORS**：生产环境指定具体域名
3. **启用 HTTPS**：使用 Let's Encrypt
4. **限制请求频率**：添加速率限制中间件

```python
# CORS 配置示例
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 故障排查

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| WebSocket 连接失败 | 端口被占用或未启动 | 检查后端是否运行 |
| LLM API 调用失败 | API Key 错误 | 检查 .env 配置 |
| 前端页面空白 | 构建失败 | 检查 npm install |
| 推演速度慢 | 并发设置过高 | 降低 max_concurrent |

### 查看日志

```bash
# 后端日志
tail -f app.log

# Docker 日志
docker logs -f info-cocoon-backend
```

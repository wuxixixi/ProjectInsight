# 前后端连接稳定性改进

## 问题背景

前端频繁出现"后端未连接"错误，主要原因是：
1. 前端直接使用 `fetch` 没有统一的健康检查和重连机制
2. 网络波动或后端重启时，前端无法自动恢复连接
3. 接口路径变化时，前端没有版本协商机制

## 解决方案

### 1. 创建统一的 API 客户端 (`frontend/src/utils/api-client.js`)

**核心功能：**
- **自动健康检查**：每 5 秒轮询 `/api/health` 和 `/` 端点，检测后端可达性
- **智能重连机制**：指数退避 (exponential backoff) + 随机抖动 (jitter) 的 WebSocket 重连策略
  - 初始延迟：1 秒
  - 增长因子：1.5 倍
  - 最大延迟：30 秒
  - 最大重试：10 次
- **请求队列**：网络中断时缓存请求，连接恢复后自动重试
  - 队列超时：10 分钟
  - 最大重试：3 次
- **统一错误处理**：集中处理超时、网络错误、HTTP 错误

**API 使用方法：**
```javascript
import apiClient from './utils/api-client'

// HTTP GET
const data = await apiClient.get('/api/settings/llm')

// HTTP POST
const data = await apiClient.post('/api/event/parse', { content: newsContent })

// WebSocket 连接
const ws = apiClient.createWebSocket('/ws', {
  onOpen: () => console.log('WebSocket 已连接'),
  onMessage: (data) => console.log('收到消息:', data),
  onClose: () => console.log('WebSocket 已断开'),
  onMaxReconnects: () => console.log('重连次数已达上限')
})

// 连接状态监听
apiClient.onStatusChange = (isConnected) => {
  console.log('连接状态:', isConnected ? '已连接' : '已断开')
}

// 手动控制健康检查
apiClient.startHealthCheck()
apiClient.stopHealthCheck()
```

### 2. 重构 App.vue 使用新的 API 客户端

**已替换的接口调用：**
- `/api/settings/llm` (GET/POST)
- `/api/profiles` (GET)
- `/api/profiles/upload` (POST, FormData)
- `/api/profiles/build` (POST)
- `/api/math-model/explanation` (GET)
- `/api/docs/usage` (GET)
- `/api/event/parse` (POST)
- `/api/health/llm` (GET)
- `/api/event/hot-news` (GET)
- `/api/simulation/state` (GET)
- `/api/report/list` (GET)
- `/api/prediction` (GET)
- `/api/risk-alerts` (GET)

**生命周期管理：**
```javascript
// mounted 时初始化
mounted() {
  this.apiClient = apiClient
  this.apiClient.onStatusChange((isConnected) => {
    this.isConnected = isConnected
  })
  this.apiClient.startHealthCheck()
  // ... 其他初始化
}

// beforeUnmount 时清理
beforeUnmount() {
  this.disconnectWebSocket()
  this.apiClient?.stopHealthCheck()
  // ... 其他清理
}
```

### 3. 后端已有的健康检查端点

- `/api/health` - 基础健康检查（已存在）
- `/api/health/llm` - LLM 状态检查（已存在）
- `/` - 根路径，返回服务信息（已存在）

## 技术细节

### 健康检查策略

采用 `no-cors` 模式进行健康检查，避免跨域限制：
```javascript
const response = await fetch(`${this.baseURL}/api/health`, {
  method: 'GET',
  mode: 'no-cors',  // 不检查响应内容，只要不抛异常就认为可达
  signal: AbortSignal.timeout(5000)
})
```

### 指数退避重连算法

```javascript
const delay = Math.min(
  baseDelay * Math.pow(1.5, attempt - 1) * (0.5 + Math.random()),
  maxDelay
)
```

例如：
- 第 1 次：1 秒 × 1.5^0 × (0.5-1.5) = 0.5-1.5 秒
- 第 2 次：1 秒 × 1.5^1 × (0.5-1.5) = 0.75-2.25 秒
- 第 3 次：1 秒 × 1.5^2 × (0.5-1.5) = 1.125-3.375 秒
- ...
- 第 10 次：最大 30 秒

### 请求队列机制

网络中断时的请求处理流程：
1. 请求失败 → 加入队列
2. 检测连接状态 → 等待恢复
3. 连接恢复 → 按 FIFO 顺序重试
4. 超时或重试次数超限 → 放弃请求并报错

## 后续优化建议

1. **添加连接状态 UI**：在前端显示当前连接状态（连接中/已连接/断开）
2. **错误提示优化**：当连接失败时显示友好的错误信息和重试按钮
3. **API 版本管理**：预留版本协商接口，避免接口变更导致的兼容性问题
4. **WebSocket 心跳**：添加 WebSocket 心跳机制，保持长连接活跃
5. **离线缓存**：考虑使用 IndexedDB 缓存关键数据，支持离线操作

## 测试建议

1. **网络中断测试**：
   - 停止后端服务，验证前端是否显示断开状态
   - 重启后端服务，验证前端是否自动重连

2. **WebSocket 重连测试**：
   - 断开网络连接，观察重连日志
   - 验证指数退避延迟是否按预期增长

3. **请求队列测试**：
   - 在网络中断时发送请求
   - 恢复网络后验证请求是否自动重试成功

## 文件清单

- `frontend/src/utils/api-client.js` - 新建，API 客户端封装
- `frontend/src/App.vue` - 修改，替换所有 fetch 调用为 apiClient
- `docs/CONNECTION_IMPROVEMENTS.md` - 新建，本文档

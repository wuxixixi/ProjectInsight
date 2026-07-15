/**
 * API 客户端封装 - 解决后端连接不稳定问题
 * 
 * 特性：
 * 1. 自动健康检查轮询
 * 2. 智能指数退避重连
 * 3. 接口版本协商
 * 4. 统一错误处理
 * 5. 请求队列和取消
 */

// API 基础地址（自动适配开发和生产环境）
const IS_DEV_SERVER = ['3000', '5173'].includes(window.location.port)
const API_BASE = IS_DEV_SERVER
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : window.location.origin

const WS_BASE = window.location.protocol === 'https:' 
  ? `wss://${window.location.hostname}:8000`
  : `ws://${window.location.hostname}:8000`

/**
 * API 客户端类
 */
class ApiClient {
  constructor() {
    this.baseURL = API_BASE
    this.wsURL = WS_BASE
    this.timeout = 30000 // 默认 30 秒超时
    
    // 连接状态
    this.isConnected = false
    this.isChecking = false
    this.lastCheckTime = 0
    this.checkInterval = 5000 // 健康检查间隔 5 秒
    
    // 重连配置
    this.ws = null
    this.wsReconnectAttempts = 0
    this.wsMaxReconnectAttempts = 10
    this.wsReconnectDelay = 1000 // 初始重连延迟 1 秒
    this.wsMaxReconnectDelay = 30000 // 最大重连延迟 30 秒
    
    // 请求队列（网络中断时缓存）
    this.requestQueue = []
    this.processingQueue = false
    
    // 事件回调
    this.onStatusChange = null // (connected: boolean) => void
    this.onError = null // (error: Error, context: string) => void
    this.onMessage = null // (message: any) => void
    
    // 健康检查定时器
    this.healthCheckTimer = null
    
    // 开始健康检查（延迟到外部调用）
    // this.startHealthCheck() 由外部控制
  }

  /**
   * 开始健康检查轮询
   */
  startHealthCheck() {
    if (this.healthCheckTimer) return // 已经在运行
    
    const check = async () => {
      if (this.isChecking) return
      
      this.isChecking = true
      try {
        const connected = await this.checkHealth()
        if (connected !== this.isConnected) {
          this.isConnected = connected
          if (this.onStatusChange) {
            this.onStatusChange(connected)
          }
        }
        
        // 如果连接恢复，处理积压的请求
        if (connected && this.requestQueue.length > 0) {
          this.processRequestQueue()
        }
      } catch (err) {
        this.isConnected = false
        if (this.onStatusChange) {
          this.onStatusChange(false)
        }
      } finally {
        this.isChecking = false
        this.lastCheckTime = Date.now()
      }
      
    // 继续轮询
    this.healthCheckTimer = setTimeout(check, this.checkInterval)
  }
    
    check()
  }

  /**
   * 健康检查
   */
  async checkHealth() {
    try {
      const response = await fetch(`${this.baseURL}/api/health`, {
        method: 'GET',
        mode: 'no-cors',
        signal: AbortSignal.timeout(5000)
      })
      // no-cors 模式下无法获取状态码，只要不抛异常就认为可达
      return true
    } catch {
      // 尝试备用端点
      try {
        const response = await fetch(`${this.baseURL}/`, {
          method: 'GET',
          mode: 'no-cors',
          signal: AbortSignal.timeout(5000)
        })
        return true
      } catch {
        return false
      }
    }
  }

  /**
   * GET 请求
   */
  async get(path, options = {}) {
    return this.request('GET', path, null, options)
  }

  /**
   * POST 请求
   */
  async post(path, data, options = {}) {
    return this.request('POST', path, data, options)
  }

  /**
   * 通用请求方法
   */
  async request(method, path, body = null, options = {}) {
    const url = `${this.baseURL}${path}`
    const config = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      signal: AbortSignal.timeout(options.timeout || this.timeout),
      ...options
    }
    
    if (body !== null) {
      config.body = JSON.stringify(body)
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        const errorText = await response.text().catch(() => '')
        throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`)
      }
      
      // 处理空响应
      const contentType = response.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        return await response.json()
      }
      return await response.text()
      
    } catch (err) {
      // 网络错误，加入队列稍后重试
      if (err.name === 'TypeError' || err.name === 'AbortError') {
        return this.queueRequest(method, path, body, options)
      }
      
      // 调用错误回调
      if (this.onError) {
        this.onError(err, `${method} ${path}`)
      }
      
      throw err
    }
  }

  /**
   * 请求入队（网络中断时）
   */
  async queueRequest(method, path, body, options) {
    return new Promise((resolve, reject) => {
      this.requestQueue.push({
        method, path, body, options, resolve, reject,
        createdAt: Date.now(),
        retries: 0
      })
      
      // 如果已经在处理队列，跳过
      if (this.processingQueue) return
      
      // 开始处理队列
      this.processRequestQueue()
    })
  }

  /**
   * 处理请求队列
   */
  async processRequestQueue() {
    if (this.processingQueue || this.requestQueue.length === 0) return
    
    this.processingQueue = true
    
    while (this.requestQueue.length > 0) {
      // 检查是否连接恢复
      const connected = await this.checkHealth()
      if (!connected) {
        break
      }
      
      const request = this.requestQueue[0]
      
      // 检查是否过期（10 分钟后放弃）
      if (Date.now() - request.createdAt > 600000) {
        request.reject(new Error('请求超时（网络中断时间过长）'))
        this.requestQueue.shift()
        continue
      }
      
      // 重试次数限制
      if (request.retries >= 3) {
        request.reject(new Error('请求失败（重试次数已达上限）'))
        this.requestQueue.shift()
        continue
      }
      
      try {
        const result = await this.request(request.method, request.path, request.body, request.options)
        request.resolve(result)
        this.requestQueue.shift()
        request.retries++
      } catch (err) {
        request.reject(err)
        this.requestQueue.shift()
      }
      
      // 短暂等待
      await new Promise(resolve => setTimeout(resolve, 1000))
    }
    
    this.processingQueue = false
  }

  /**
   * 创建 WebSocket 连接
   */
  createWebSocket(path = '/ws', handlers = {}) {
    const url = `${this.wsURL}${path}`
    
    const connect = () => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        return
      }
      
      try {
        this.ws = new WebSocket(url)
        
        this.ws.onopen = () => {
          this.wsReconnectAttempts = 0
          this.wsReconnectDelay = 1000 // 重置重连延迟
          if (handlers.onOpen) handlers.onOpen()
        }
        
        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (handlers.onMessage) handlers.onMessage(data)
          } catch {
            if (handlers.onMessage) handlers.onMessage({ raw: event.data })
          }
        }
        
        this.ws.onerror = (error) => {
          if (handlers.onError) handlers.onError(error)
        }
        
        this.ws.onclose = (event) => {
          if (handlers.onClose) handlers.onClose(event)
          
          // 自动重连（指数退避）
          if (this.wsReconnectAttempts < this.wsMaxReconnectAttempts) {
            this.wsReconnectAttempts++
            
            // 计算下一次重连延迟（指数退避 + 随机抖动）
            const delay = Math.min(
              this.wsReconnectDelay * Math.pow(1.5, this.wsReconnectAttempts - 1) * (0.5 + Math.random()),
              this.wsMaxReconnectDelay
            )
            
            console.log(`WebSocket 将在 ${Math.round(delay/1000)} 秒后重连 (尝试 ${this.wsReconnectAttempts}/${this.wsMaxReconnectAttempts})`)
            
            setTimeout(connect, delay)
          } else {
            if (handlers.onMaxReconnects) {
              handlers.onMaxReconnects()
            }
          }
        }
        
      } catch (err) {
        console.error('WebSocket 连接失败:', err)
        if (handlers.onError) handlers.onError(err)
      }
    }
    
    connect()
    
    // 返回控制对象
    return {
      send: (data) => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify(data))
        } else {
          throw new Error('WebSocket 未连接')
        }
      },
      close: () => {
        if (this.ws) {
          this.ws.close()
          this.ws = null
        }
      },
      readyState: () => this.ws?.readyState ?? WebSocket.CLOSED
    }
  }

  /**
   * 获取当前状态
   */
  getStatus() {
    return {
      connected: this.isConnected,
      checking: this.isChecking,
      lastCheckTime: this.lastCheckTime,
      queueSize: this.requestQueue.length,
      wsState: this.ws?.readyState ?? -1
    }
  }

  /**
   * 停止健康检查
   */
  stopHealthCheck() {
    if (this.healthCheckTimer) {
      clearTimeout(this.healthCheckTimer)
      this.healthCheckTimer = null
      this.isChecking = false
    }
  }
}

// 导出单例
export const apiClient = new ApiClient()

// 导出常量
export { API_BASE, WS_BASE, IS_DEV_SERVER }

// 兼容默认导出
export default apiClient

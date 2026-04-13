<template>
  <div class="dashboard-container">
    <!-- 左侧控制面板 -->
    <aside class="control-panel">
      <!-- 标题 -->
      <div class="panel-header">
        <h1>觉测·洞鉴</h1>
        <p class="subtitle">多智能体舆论认知干预沙盘</p>
      </div>

      <!-- 连接状态 -->
      <div class="connection-status" :class="connectionClass">
        <span class="status-dot"></span>
        {{ connectionStatus }}
      </div>

      <!-- 推演模式 -->
      <div class="control-section">
        <label class="section-label">推演模式</label>
        <div class="mode-toggle">
          <button :class="['mode-btn', { active: useLLM }]" @click="useLLM = true" :disabled="isRunning">
            <span class="mode-icon">🤖</span>
            LLM驱动
          </button>
          <button :class="['mode-btn', { active: !useLLM }]" @click="useLLM = false" :disabled="isRunning">
            <span class="mode-icon">📊</span>
            数学模型
          </button>
        </div>
      </div>

      <!-- 核心参数 -->
      <div class="control-section">
        <div class="param-item">
          <div class="param-header">
            <span class="param-label">算法茧房强度</span>
            <span class="param-value">{{ cocoonStrength.toFixed(2) }}</span>
          </div>
          <input type="range" v-model.number="cocoonStrength" min="0" max="1" step="0.05" :disabled="isRunning" />
          <p class="param-desc">越高越容易强化既有观点</p>
        </div>

        <div class="param-item">
          <div class="param-header">
            <span class="param-label">官方辟谣延迟</span>
            <span class="param-value">{{ debunkDelay }} 步</span>
          </div>
          <input type="range" v-model.number="debunkDelay" min="0" max="30" step="1" :disabled="isRunning" />
          <p class="param-desc">谣言传播多久后发布辟谣</p>
        </div>

        <div class="param-item">
          <div class="param-header">
            <span class="param-label">初始谣言传播率</span>
            <span class="param-value">{{ (initialRumorSpread * 100).toFixed(0) }}%</span>
          </div>
          <input type="range" v-model.number="initialRumorSpread" min="0.1" max="0.6" step="0.05" :disabled="isRunning" />
        </div>

        <div class="param-item">
          <div class="param-header">
            <span class="param-label">Agent数量</span>
            <span class="param-value">{{ populationSize }}</span>
          </div>
          <input type="range" v-model.number="populationSize" min="50" max="500" step="50" :disabled="isRunning" />
        </div>

        <div class="param-item">
          <div class="param-header">
            <span class="param-label">社交网络类型</span>
          </div>
          <select v-model="networkType" :disabled="isRunning" class="network-select">
            <option value="small_world">小世界网络</option>
            <option value="scale_free">无标度网络</option>
            <option value="random">随机网络</option>
          </select>
          <p class="param-desc">{{ networkTypeDesc }}</p>
        </div>

        <div class="param-item">
          <div class="param-header">
            <span class="param-label">最大推演步数</span>
            <span class="param-value">{{ maxSteps }} 步</span>
          </div>
          <input type="range" v-model.number="maxSteps" min="10" max="100" step="10" :disabled="isRunning" />
        </div>
      </div>

      <!-- 推演控制 -->
      <div class="control-actions">
        <button v-if="!isRunning" class="btn-start" @click="startSimulation" :disabled="!isConnected">
          <span class="btn-icon">▶</span>
          开始推演
        </button>
        <button v-else class="btn-stop" @click="stopSimulation">
          <span class="btn-icon">■</span>
          停止推演
        </button>

        <!-- 进度显示 -->
        <div v-if="isRunning && agentProgress" class="progress-notice">
          <div class="progress-spinner"></div>
          <span>{{ agentProgress }}</span>
        </div>
      </div>

      <!-- 底部操作 -->
      <div class="panel-footer">
        <button v-if="currentStep > 0 && !isRunning" class="btn-report" @click="generateReport">
          <span>📄</span> 生成报告
        </button>
        <button class="btn-settings" @click="showSettingsDrawer = true">
          <span>⚙️</span> 高级设置
        </button>
      </div>
    </aside>

    <!-- 右侧主内容区 -->
    <main class="main-content">
      <!-- 顶部核心指标卡 -->
      <div class="kpi-cards">
        <div class="kpi-card">
          <div class="kpi-icon">⏱️</div>
          <div class="kpi-content">
            <span class="kpi-label">当前步数</span>
            <span class="kpi-value">{{ animatedStep }}</span>
          </div>
        </div>
        <div class="kpi-card danger">
          <div class="kpi-icon">📢</div>
          <div class="kpi-content">
            <span class="kpi-label">谣言传播率</span>
            <span class="kpi-value">{{ (rumorSpreadRate * 100).toFixed(1) }}<small>%</small></span>
          </div>
        </div>
        <div class="kpi-card success">
          <div class="kpi-icon">✓</div>
          <div class="kpi-content">
            <span class="kpi-label">真相接受率</span>
            <span class="kpi-value">{{ (truthAcceptanceRate * 100).toFixed(1) }}<small>%</small></span>
          </div>
        </div>
        <div class="kpi-card info">
          <div class="kpi-icon">⚖️</div>
          <div class="kpi-content">
            <span class="kpi-label">平均观点</span>
            <span class="kpi-value">{{ avgOpinion.toFixed(3) }}</span>
          </div>
        </div>
        <div class="kpi-card warning">
          <div class="kpi-icon">⚡</div>
          <div class="kpi-content">
            <span class="kpi-label">极化指数</span>
            <span class="kpi-value">{{ polarizationIndex.toFixed(3) }}</span>
          </div>
        </div>
      </div>

      <!-- 图表区域 -->
      <div class="charts-grid">
        <!-- 上排：观点分布 + 网络图 -->
        <div class="chart-row top-row">
          <div class="chart-card opinion-chart">
            <div class="chart-header">
              <h3>群体观点分布</h3>
              <div class="chart-legend">
                <span class="legend-item rumor">谣言</span>
                <span class="legend-item neutral">中立</span>
                <span class="legend-item truth">真相</span>
              </div>
            </div>
            <div class="chart-body" ref="opinionChart"></div>
          </div>
          <div class="chart-card network-chart">
            <div class="chart-header">
              <h3>信息传播网络</h3>
              <span class="chart-tip">点击节点查看Agent详情</span>
            </div>
            <div class="chart-body" ref="networkChart"></div>
          </div>
        </div>

        <!-- 下排：趋势图 -->
        <div class="chart-row bottom-row">
          <div class="chart-card trend-chart">
            <div class="chart-header">
              <h3>舆论演化趋势</h3>
              <span v-if="debunked" class="debunk-badge">辟谣已发布</span>
            </div>
            <div class="chart-body" ref="trendChart"></div>
          </div>
        </div>
      </div>
    </main>

    <!-- 高级设置抽屉 -->
    <div v-if="showSettingsDrawer" class="drawer-overlay" @click.self="showSettingsDrawer = false">
      <div class="settings-drawer">
        <div class="drawer-header">
          <h3>⚙️ 高级设置</h3>
          <button class="drawer-close" @click="showSettingsDrawer = false">✕</button>
        </div>
        <div class="drawer-body">
          <h4 class="drawer-section-title">LLM 并发配置</h4>

          <div class="setting-item">
            <div class="setting-header">
              <span class="setting-label">并发数上限</span>
              <span class="setting-value">{{ maxConcurrent }}</span>
            </div>
            <input type="range" v-model.number="maxConcurrent" min="50" max="500" step="50" :disabled="isRunning" />
            <p class="setting-desc">同时请求LLM的Agent数量</p>
          </div>

          <div class="setting-item">
            <div class="setting-header">
              <span class="setting-label">连接池大小</span>
              <span class="setting-value">{{ connectionPoolSize }}</span>
            </div>
            <input type="range" v-model.number="connectionPoolSize" min="100" max="800" step="100" :disabled="isRunning" />
            <p class="setting-desc">应大于并发数上限</p>
          </div>

          <div class="setting-item">
            <div class="setting-header">
              <span class="setting-label">请求超时</span>
              <span class="setting-value">{{ timeout }} 秒</span>
            </div>
            <input type="range" v-model.number="timeout" min="30" max="120" step="10" :disabled="isRunning" />
            <p class="setting-desc">单个请求最长等待时间</p>
          </div>

          <div class="setting-item">
            <div class="setting-header">
              <span class="setting-label">最大重试次数</span>
              <span class="setting-value">{{ maxRetries }} 次</span>
            </div>
            <input type="range" v-model.number="maxRetries" min="1" max="10" step="1" :disabled="isRunning" />
            <p class="setting-desc">失败后自动重试</p>
          </div>

          <div class="setting-item">
            <div class="setting-header">
              <span class="setting-label">推演间隔</span>
              <span class="setting-value">{{ autoInterval / 1000 }} 秒</span>
            </div>
            <input type="range" v-model.number="autoInterval" min="1000" max="10000" step="1000" :disabled="isRunning" />
            <p class="setting-desc">LLM模式建议3秒以上</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Agent透视弹窗 -->
    <div v-if="showAgentModal" class="agent-modal-overlay" @click.self="closeAgentModal">
      <div class="agent-modal">
        <div class="modal-header">
          <h3><span class="icon">🔍</span> Agent #{{ inspectAgentId }} 微观行为透视</h3>
          <button class="close-btn" @click="closeAgentModal">✕</button>
        </div>

        <div v-if="agentLoading" class="modal-loading">
          <div class="loading-spinner"></div>
          <p>正在获取决策链路...</p>
        </div>

        <div v-else-if="agentSnapshot && agentSnapshot.error" class="modal-error">
          <p>{{ agentSnapshot.error }}</p>
        </div>

        <div v-else-if="agentSnapshot" class="modal-content">
          <!-- 区块A: Agent基础人设 -->
          <div class="info-block persona-block">
            <div class="block-title"><span class="block-icon">👤</span> 基础人设</div>
            <div class="block-content">
              <div class="info-grid">
                <div class="info-item">
                  <span class="label">Agent ID</span>
                  <span class="value">#{{ agentSnapshot.agent_id }}</span>
                </div>
                <div class="info-item">
                  <span class="label">人设类型</span>
                  <span class="value highlight">{{ agentSnapshot.persona?.type || '未知' }}</span>
                </div>
                <div class="info-item">
                  <span class="label">人设描述</span>
                  <span class="value desc">{{ agentSnapshot.persona?.desc || '-' }}</span>
                </div>
                <div class="info-item">
                  <span class="label">信念强度</span>
                  <span class="value">{{ (agentSnapshot.belief_strength * 100).toFixed(0) }}%</span>
                </div>
                <div class="info-item">
                  <span class="label">易感性</span>
                  <span class="value">{{ (agentSnapshot.susceptibility * 100).toFixed(0) }}%</span>
                </div>
                <div class="info-item">
                  <span class="label">当前立场</span>
                  <span :class="['value', 'status-badge', agentOpinionClass]">{{ agentOpinionLabel }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 区块B: 信息刺激 -->
          <div class="info-block stimulus-block">
            <div class="block-title"><span class="block-icon">📡</span> 信息刺激</div>
            <div class="block-content">
              <div v-if="agentSnapshot.received_news?.length" class="news-list">
                <div v-for="(news, idx) in agentSnapshot.received_news" :key="idx" class="news-item">{{ news }}</div>
              </div>
              <div v-else class="empty-state">暂无新信息刺激</div>
            </div>
          </div>

          <!-- 区块C: LLM决策输出 -->
          <div class="info-block decision-block">
            <div class="block-title"><span class="block-icon">🧠</span> LLM 决策引擎输出</div>
            <div class="block-content">
              <div v-if="agentSnapshot.has_decided" class="decision-output">
                <div class="decision-summary">
                  <div class="summary-item">
                    <span class="label">情绪状态</span>
                    <span class="value emotion">{{ agentSnapshot.emotion || '-' }}</span>
                  </div>
                  <div class="summary-item">
                    <span class="label">行动选择</span>
                    <span class="value action">{{ agentSnapshot.action || '-' }}</span>
                  </div>
                  <div class="summary-item">
                    <span class="label">观点变化</span>
                    <span class="value opinion-change">{{ agentSnapshot.old_opinion?.toFixed(3) }} → {{ agentSnapshot.new_opinion?.toFixed(3) }}</span>
                  </div>
                </div>
                <div v-if="agentSnapshot.generated_comment" class="generated-comment">
                  <span class="label">生成评论</span>
                  <p class="comment-text">"{{ agentSnapshot.generated_comment }}"</p>
                </div>
                <div class="reasoning">
                  <span class="label">决策理由</span>
                  <p class="reasoning-text">{{ agentSnapshot.reasoning || '-' }}</p>
                </div>
                <div class="raw-response">
                  <span class="label">LLM 原始响应 (JSON)</span>
                  <pre class="json-code">{{ formatJson(agentSnapshot.llm_raw_response) }}</pre>
                </div>
              </div>
              <div v-else class="empty-state">
                <span class="icon">⏳</span>
                <p>{{ agentSnapshot.reasoning || '该Agent尚未参与本轮推演' }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 报告成功提示 -->
    <div v-if="reportGenerated" class="report-toast">
      <p>📄 报告已生成</p>
      <button class="btn-open-report" @click="openReport">打开报告</button>
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts'

export default {
  name: 'App',

  data() {
    return {
      // 连接状态
      isConnected: false,
      ws: null,

      // 基础参数
      cocoonStrength: 0.5,
      debunkDelay: 10,
      initialRumorSpread: 0.3,
      useLLM: true,

      // Agent参数
      populationSize: 200,
      networkType: 'small_world',

      // LLM并发参数
      maxConcurrent: 400,
      connectionPoolSize: 600,
      timeout: 60,
      maxRetries: 5,

      // 推演参数
      maxSteps: 50,
      autoInterval: 3000,

      // 状态
      isRunning: false,
      currentStep: 0,
      debunked: false,
      agentProgress: '',

      // 统计数据
      rumorSpreadRate: 0,
      truthAcceptanceRate: 0,
      avgOpinion: 0,
      polarizationIndex: 0,

      // 动画数值
      animatedStep: 0,

      // 图表数据
      agents: [],
      edges: [],
      opinionDist: { counts: [], centers: [] },
      trendHistory: {
        steps: [],
        rumorRates: [],
        truthRates: [],
        avgOpinions: [],
        polarization: []
      },

      // 图表实例
      opinionChartInstance: null,
      networkChartInstance: null,
      trendChartInstance: null,

      // 报告相关
      reportGenerated: false,
      reportFilename: '',
      reportPath: '',

      // Agent透视弹窗
      showAgentModal: false,
      inspectAgentId: null,
      agentSnapshot: null,
      agentLoading: false,

      // 高级设置抽屉
      showSettingsDrawer: false
    }
  },

  computed: {
    connectionClass() {
      return this.isConnected ? 'connected' : 'disconnected'
    },
    connectionStatus() {
      return this.isConnected ? '已连接' : '未连接'
    },
    networkTypeDesc() {
      const descs = {
        'small_world': '真实社交网络模拟',
        'scale_free': '存在意见领袖',
        'random': '随机连接'
      }
      return descs[this.networkType] || ''
    },
    agentOpinionClass() {
      if (!this.agentSnapshot) return 'neutral'
      const opinion = this.agentSnapshot.new_opinion
      if (opinion > 0.2) return 'positive'
      if (opinion < -0.2) return 'negative'
      return 'neutral'
    },
    agentOpinionLabel() {
      if (!this.agentSnapshot) return ''
      const opinion = this.agentSnapshot.new_opinion
      if (opinion > 0.2) return '相信真相'
      if (opinion < -0.2) return '相信谣言'
      return '中立'
    }
  },

  watch: {
    currentStep(newVal) {
      // 数字翻滚动画
      const target = newVal
      const duration = 300
      const start = this.animatedStep
      const startTime = performance.now()

      const animate = (currentTime) => {
        const elapsed = currentTime - startTime
        const progress = Math.min(elapsed / duration, 1)
        this.animatedStep = Math.round(start + (target - start) * progress)
        if (progress < 1) {
          requestAnimationFrame(animate)
        }
      }
      requestAnimationFrame(animate)
    }
  },

  mounted() {
    this.initCharts()
    this.connectWebSocket()
    window.addEventListener('resize', this.handleResize)
  },

  beforeUnmount() {
    this.disconnectWebSocket()
    window.removeEventListener('resize', this.handleResize)
    this.opinionChartInstance?.dispose()
    this.networkChartInstance?.dispose()
    this.trendChartInstance?.dispose()
  },

  methods: {
    // ==================== WebSocket 连接 ====================

    connectWebSocket() {
      const wsUrl = 'ws://localhost:8000/ws/simulation'
      console.log('连接 WebSocket:', wsUrl)

      try {
        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          this.isConnected = true
          console.log('WebSocket 已连接')
        }

        this.ws.onclose = (event) => {
          this.isConnected = false
          console.log('WebSocket 已断开', event.code, event.reason)
          setTimeout(() => {
            if (!this.isConnected) {
              this.connectWebSocket()
            }
          }, 3000)
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket 错误:', error)
          this.isConnected = false
        }

        this.ws.onmessage = (event) => {
          const msg = JSON.parse(event.data)
          this.handleMessage(msg)
        }
      } catch (e) {
        console.error('WebSocket 创建失败:', e)
        this.isConnected = false
      }
    },

    disconnectWebSocket() {
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
    },

    handleMessage(msg) {
      switch (msg.type) {
        case 'state':
          this.updateState(msg.data)
          break
        case 'progress':
          this.agentProgress = msg.message
          break
        case 'error':
          console.error('服务端错误:', msg.message)
          alert('错误: ' + msg.message)
          this.isRunning = false
          break
        case 'report':
          if (msg.data.success) {
            this.reportGenerated = true
            this.reportFilename = msg.data.report_filename
            this.reportPath = msg.data.report_path
          }
          break
      }
    },

    sendAction(action, params = {}) {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ action, ...params }))
      }
    },

    // ==================== 模拟控制 ====================

    startSimulation() {
      this.isRunning = true
      this.currentStep = 0
      this.animatedStep = 0
      this.debunked = false
      this.agentProgress = ''
      this.trendHistory = {
        steps: [],
        rumorRates: [],
        truthRates: [],
        avgOpinions: [],
        polarization: []
      }

      this.sendAction('start', {
        params: {
          cocoon_strength: this.cocoonStrength,
          debunk_delay: this.debunkDelay,
          initial_rumor_spread: this.initialRumorSpread,
          use_llm: this.useLLM,
          population_size: this.populationSize,
          network_type: this.networkType,
          max_concurrent: this.maxConcurrent,
          connection_pool_size: this.connectionPoolSize,
          timeout: this.timeout,
          max_retries: this.maxRetries
        }
      })

      setTimeout(() => {
        if (this.isRunning) {
          const interval = this.useLLM ? this.autoInterval : 500
          this.sendAction('auto', { interval })
        }
      }, 500)
    },

    stopSimulation() {
      this.isRunning = false
      this.agentProgress = ''
      this.sendAction('stop')
    },

    generateReport() {
      this.sendAction('finish')
    },

    async openReport() {
      try {
        const response = await fetch('/api/report/open', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: this.reportPath })
        })
        const data = await response.json()
        if (!data.success) {
          alert('打开报告失败: ' + (data.error || '未知错误'))
        }
      } catch (error) {
        console.error('打开报告失败:', error)
      }
    },

    // ==================== Agent透视功能 ====================

    async inspectAgent(agentId) {
      this.inspectAgentId = agentId
      this.showAgentModal = true
      this.agentLoading = true
      this.agentSnapshot = null

      try {
        const response = await fetch(`http://localhost:8000/api/agent/${agentId}/inspect`)
        const data = await response.json()
        this.agentSnapshot = data
      } catch (error) {
        console.error('获取Agent信息失败:', error)
        this.agentSnapshot = { error: '获取Agent信息失败' }
      } finally {
        this.agentLoading = false
      }
    },

    closeAgentModal() {
      this.showAgentModal = false
      this.inspectAgentId = null
      this.agentSnapshot = null
    },

    formatJson(obj) {
      if (!obj) return ''
      return JSON.stringify(obj, null, 2)
    },

    // ==================== 状态更新 ====================

    updateState(data) {
      this.currentStep = data.step
      this.agents = data.agents
      this.edges = data.edges
      this.opinionDist = data.opinion_distribution
      this.rumorSpreadRate = data.rumor_spread_rate
      this.truthAcceptanceRate = data.truth_acceptance_rate
      this.avgOpinion = data.avg_opinion
      this.polarizationIndex = data.polarization_index
      this.debunked = data.step >= this.debunkDelay

      this.trendHistory.steps.push(data.step)
      this.trendHistory.rumorRates.push(data.rumor_spread_rate)
      this.trendHistory.truthRates.push(data.truth_acceptance_rate)
      this.trendHistory.avgOpinions.push(data.avg_opinion)
      this.trendHistory.polarization.push(data.polarization_index)

      this.agentProgress = ''

      if (data.step >= this.maxSteps) {
        this.isRunning = false
        this.sendAction('stop')
      }

      this.renderOpinionChart()
      this.renderNetworkChart()
      this.renderTrendChart()
    },

    // ==================== 图表渲染 ====================

    initCharts() {
      this.opinionChartInstance = echarts.init(this.$refs.opinionChart)
      this.renderOpinionChart()

      this.networkChartInstance = echarts.init(this.$refs.networkChart)
      this.renderNetworkChart()

      this.trendChartInstance = echarts.init(this.$refs.trendChart)
      this.renderTrendChart()
    },

    handleResize() {
      this.opinionChartInstance?.resize()
      this.networkChartInstance?.resize()
      this.trendChartInstance?.resize()
    },

    renderOpinionChart() {
      const data = this.opinionDist.counts.map((count, i) => ({
        value: count,
        center: this.opinionDist.centers?.[i] || i
      }))

      const option = {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(20, 25, 40, 0.95)',
          borderColor: 'rgba(100, 181, 246, 0.3)',
          textStyle: { color: '#e0e0e0' }
        },
        grid: {
          left: '8%',
          right: '4%',
          top: '10%',
          bottom: '12%'
        },
        xAxis: {
          type: 'category',
          data: this.opinionDist.centers?.map(c => c.toFixed(2)) || [],
          axisLabel: { color: '#6b7280', fontSize: 10 },
          axisLine: { lineStyle: { color: 'rgba(100, 181, 246, 0.2)' } },
          name: '观点值',
          nameTextStyle: { color: '#6b7280', fontSize: 11 }
        },
        yAxis: {
          type: 'value',
          axisLabel: { color: '#6b7280' },
          splitLine: { lineStyle: { color: 'rgba(100, 181, 246, 0.1)' } },
          axisLine: { show: false }
        },
        series: [{
          type: 'bar',
          data: data.map((d, i) => {
            const center = d.center
            let color
            if (center < -0.2) color = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#ef4444' },
              { offset: 1, color: '#dc2626' }
            ])
            else if (center > 0.2) color = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#22c55e' },
              { offset: 1, color: '#16a34a' }
            ])
            else color = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#f59e0b' },
              { offset: 1, color: '#d97706' }
            ])
            return {
              value: d.value,
              itemStyle: { color, borderRadius: [4, 4, 0, 0] }
            }
          }),
          barWidth: '70%'
        }]
      }

      this.opinionChartInstance?.setOption(option)
    },

    renderNetworkChart() {
      if (!this.agents.length) return

      const nodes = this.agents.map(agent => {
        let color
        if (agent.opinion < -0.2) color = '#ef4444'
        else if (agent.opinion > 0.2) color = '#22c55e'
        else color = '#f59e0b'

        return {
          id: agent.id.toString(),
          symbolSize: 4 + agent.influence * 8,
          itemStyle: { color },
          x: Math.random() * 800,
          y: Math.random() * 500
        }
      })

      const sampledEdges = this.edges
        .filter(() => Math.random() < 0.25)
        .slice(0, 400)
        .map(([source, target]) => ({
          source: source.toString(),
          target: target.toString(),
          lineStyle: { color: 'rgba(100, 181, 246, 0.15)', width: 0.5 }
        }))

      const option = {
        backgroundColor: 'transparent',
        tooltip: {
          formatter: (params) => {
            if (params.dataType === 'node') {
              const agent = this.agents.find(a => a.id.toString() === params.data.id)
              if (agent) {
                return `<div style="padding: 8px;">
                  <div style="font-weight: bold; margin-bottom: 4px;">Agent ${agent.id}</div>
                  <div>观点: ${agent.opinion.toFixed(3)}</div>
                  <div style="color: #64b5f6; margin-top: 4px;">点击查看详情</div>
                </div>`
              }
            }
            return ''
          },
          backgroundColor: 'rgba(20, 25, 40, 0.95)',
          borderColor: 'rgba(100, 181, 246, 0.3)',
          textStyle: { color: '#e0e0e0' }
        },
        series: [{
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: sampledEdges,
          roam: true,
          draggable: true,
          force: {
            repulsion: 80,
            edgeLength: 40,
            gravity: 0.1
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: { width: 2, color: '#64b5f6' },
            itemStyle: { shadowBlur: 20, shadowColor: 'rgba(100, 181, 246, 0.5)' }
          },
          lineStyle: { opacity: 0.2 }
        }]
      }

      this.networkChartInstance?.setOption(option)

      this.networkChartInstance?.off('click')
      this.networkChartInstance?.on('click', (params) => {
        if (params.dataType === 'node') {
          const agentId = parseInt(params.data.id)
          this.inspectAgent(agentId)
        }
      })
    },

    renderTrendChart() {
      const option = {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(20, 25, 40, 0.95)',
          borderColor: 'rgba(100, 181, 246, 0.3)',
          textStyle: { color: '#e0e0e0' }
        },
        legend: {
          data: ['谣言传播率', '真相接受率', '平均观点', '极化指数'],
          textStyle: { color: '#6b7280', fontSize: 11 },
          top: 5,
          itemWidth: 16,
          itemHeight: 8
        },
        grid: {
          left: '6%',
          right: '6%',
          top: '22%',
          bottom: '10%'
        },
        xAxis: {
          type: 'category',
          data: this.trendHistory.steps,
          axisLabel: { color: '#6b7280', fontSize: 10 },
          axisLine: { lineStyle: { color: 'rgba(100, 181, 246, 0.2)' } },
          name: '步数',
          nameTextStyle: { color: '#6b7280', fontSize: 11 }
        },
        yAxis: [
          {
            type: 'value',
            position: 'left',
            axisLabel: { color: '#6b7280', fontSize: 10 },
            splitLine: { lineStyle: { color: 'rgba(100, 181, 246, 0.1)' } },
            axisLine: { show: false },
            min: -1,
            max: 1
          },
          {
            type: 'value',
            position: 'right',
            axisLabel: { color: '#6b7280', fontSize: 10 },
            splitLine: { show: false },
            axisLine: { show: false },
            min: 0,
            max: 1
          }
        ],
        series: [
          {
            name: '谣言传播率',
            type: 'line',
            yAxisIndex: 1,
            data: this.trendHistory.rumorRates,
            lineStyle: { color: '#ef4444', width: 2 },
            itemStyle: { color: '#ef4444' },
            smooth: true,
            symbol: 'none',
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(239, 68, 68, 0.3)' },
                { offset: 1, color: 'rgba(239, 68, 68, 0.05)' }
              ])
            }
          },
          {
            name: '真相接受率',
            type: 'line',
            yAxisIndex: 1,
            data: this.trendHistory.truthRates,
            lineStyle: { color: '#22c55e', width: 2 },
            itemStyle: { color: '#22c55e' },
            smooth: true,
            symbol: 'none',
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(34, 197, 94, 0.3)' },
                { offset: 1, color: 'rgba(34, 197, 94, 0.05)' }
              ])
            }
          },
          {
            name: '平均观点',
            type: 'line',
            yAxisIndex: 0,
            data: this.trendHistory.avgOpinions,
            lineStyle: { color: '#3b82f6', width: 2 },
            itemStyle: { color: '#3b82f6' },
            smooth: true,
            symbol: 'none'
          },
          {
            name: '极化指数',
            type: 'line',
            yAxisIndex: 1,
            data: this.trendHistory.polarization,
            lineStyle: { color: '#f59e0b', width: 2, type: 'dashed' },
            itemStyle: { color: '#f59e0b' },
            smooth: true,
            symbol: 'none'
          }
        ]
      }

      this.trendChartInstance?.setOption(option)
    }
  }
}
</script>

<style scoped>
/* ==================== 全局布局 ==================== */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.dashboard-container {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #0a0f1a 0%, #0f172a 50%, #1e1b4b 100%);
  font-family: 'Inter', 'PingFang SC', -apple-system, sans-serif;
}

/* ==================== 左侧控制面板 ==================== */
.control-panel {
  width: 320px;
  min-width: 320px;
  background: rgba(15, 23, 42, 0.95);
  border-right: 1px solid rgba(100, 181, 246, 0.15);
  display: flex;
  flex-direction: column;
  padding: 20px 16px;
  gap: 16px;
  overflow-y: auto;
}

.panel-header {
  text-align: center;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
}

.panel-header h1 {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 4px;
}

.panel-header .subtitle {
  font-size: 12px;
  color: #6b7280;
}

/* 连接状态 */
.connection-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
}

.connection-status.connected {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.connection-status.disconnected {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.9); }
}

/* 控制区块 */
.control-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* 模式切换 */
.mode-toggle {
  display: flex;
  gap: 8px;
}

.mode-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 10px;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.mode-btn:hover:not(:disabled) {
  background: rgba(100, 181, 246, 0.1);
  border-color: rgba(100, 181, 246, 0.4);
}

.mode-btn.active {
  background: linear-gradient(135deg, rgba(96, 165, 250, 0.2) 0%, rgba(167, 139, 250, 0.2) 100%);
  border-color: #60a5fa;
  color: #60a5fa;
  box-shadow: 0 0 20px rgba(96, 165, 250, 0.2);
}

.mode-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mode-icon {
  font-size: 16px;
}

/* 参数项 */
.param-item {
  background: rgba(30, 41, 59, 0.3);
  border-radius: 10px;
  padding: 12px;
  border: 1px solid rgba(100, 181, 246, 0.08);
}

.param-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.param-label {
  font-size: 13px;
  color: #cbd5e1;
  font-weight: 500;
}

.param-value {
  font-size: 14px;
  font-weight: 600;
  color: #60a5fa;
}

.param-item input[type="range"] {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  background: rgba(100, 181, 246, 0.2);
  border-radius: 3px;
  outline: none;
}

.param-item input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 0 10px rgba(96, 165, 250, 0.5);
}

.param-item input[type="range"]:disabled {
  opacity: 0.5;
}

.param-desc {
  font-size: 11px;
  color: #6b7280;
  margin-top: 6px;
}

.network-select {
  width: 100%;
  padding: 10px 12px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 13px;
  cursor: pointer;
}

.network-select:disabled {
  opacity: 0.5;
}

/* 操作按钮 */
.control-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid rgba(100, 181, 246, 0.1);
}

.btn-start, .btn-stop {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-start {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: white;
  box-shadow: 0 4px 20px rgba(34, 197, 94, 0.3);
}

.btn-start:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 30px rgba(34, 197, 94, 0.4);
}

.btn-start:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-stop {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  box-shadow: 0 4px 20px rgba(239, 68, 68, 0.3);
}

.btn-icon {
  font-size: 14px;
}

.progress-notice {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px;
  background: rgba(96, 165, 250, 0.1);
  border: 1px solid rgba(96, 165, 250, 0.3);
  border-radius: 10px;
  color: #60a5fa;
  font-size: 13px;
}

.progress-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(96, 165, 250, 0.2);
  border-top-color: #60a5fa;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 面板底部 */
.panel-footer {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid rgba(100, 181, 246, 0.1);
}

.btn-report, .btn-settings {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 8px;
  color: #94a3b8;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-report:hover, .btn-settings:hover {
  background: rgba(100, 181, 246, 0.1);
  color: #60a5fa;
}

/* ==================== 右侧主内容区 ==================== */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  gap: 16px;
  overflow: hidden;
}

/* KPI指标卡 */
.kpi-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(100, 181, 246, 0.15);
  border-radius: 12px;
  transition: all 0.3s ease;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
  border-color: rgba(100, 181, 246, 0.3);
}

.kpi-card.danger {
  border-color: rgba(239, 68, 68, 0.3);
}

.kpi-card.danger .kpi-icon {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.kpi-card.danger .kpi-value {
  color: #ef4444;
}

.kpi-card.success {
  border-color: rgba(34, 197, 94, 0.3);
}

.kpi-card.success .kpi-icon {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.kpi-card.success .kpi-value {
  color: #22c55e;
}

.kpi-card.info {
  border-color: rgba(59, 130, 246, 0.3);
}

.kpi-card.info .kpi-icon {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.kpi-card.info .kpi-value {
  color: #3b82f6;
}

.kpi-card.warning {
  border-color: rgba(245, 158, 11, 0.3);
}

.kpi-card.warning .kpi-icon {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.kpi-card.warning .kpi-value {
  color: #f59e0b;
}

.kpi-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(100, 181, 246, 0.15);
  border-radius: 10px;
  font-size: 20px;
  color: #60a5fa;
}

.kpi-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-label {
  font-size: 12px;
  color: #6b7280;
}

.kpi-value {
  font-size: 24px;
  font-weight: 700;
  color: #e2e8f0;
  font-variant-numeric: tabular-nums;
}

.kpi-value small {
  font-size: 14px;
  font-weight: 500;
  margin-left: 2px;
}

/* 图表区域 */
.charts-grid {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.chart-row {
  display: flex;
  gap: 16px;
}

.top-row {
  flex: 1.4;
  min-height: 0;
}

.bottom-row {
  height: 180px;
  flex-shrink: 0;
}

.chart-card {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(100, 181, 246, 0.15);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.opinion-chart {
  flex: 4;
}

.network-chart {
  flex: 6;
}

.trend-chart {
  flex: 1;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
}

.chart-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.chart-legend {
  display: flex;
  gap: 16px;
}

.legend-item {
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-item::before {
  content: '';
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.legend-item.rumor::before { background: #ef4444; }
.legend-item.neutral::before { background: #f59e0b; }
.legend-item.truth::before { background: #22c55e; }

.chart-tip {
  font-size: 11px;
  color: #6b7280;
}

.debunk-badge {
  font-size: 11px;
  padding: 4px 10px;
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border-radius: 12px;
  font-weight: 500;
}

.chart-body {
  flex: 1;
  min-height: 0;
}

/* ==================== 高级设置抽屉 ==================== */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  z-index: 100;
  display: flex;
  justify-content: flex-end;
}

.settings-drawer {
  width: 380px;
  height: 100%;
  background: rgba(15, 23, 42, 0.98);
  border-left: 1px solid rgba(100, 181, 246, 0.2);
  display: flex;
  flex-direction: column;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
}

.drawer-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #e2e8f0;
}

.drawer-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(100, 181, 246, 0.1);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 8px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s;
}

.drawer-close:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
  color: #ef4444;
}

.drawer-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.drawer-section-title {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 16px;
}

.setting-item {
  background: rgba(30, 41, 59, 0.3);
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 12px;
  border: 1px solid rgba(100, 181, 246, 0.08);
}

.setting-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.setting-label {
  font-size: 13px;
  color: #cbd5e1;
  font-weight: 500;
}

.setting-value {
  font-size: 14px;
  font-weight: 600;
  color: #60a5fa;
}

.setting-item input[type="range"] {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  background: rgba(100, 181, 246, 0.2);
  border-radius: 3px;
  outline: none;
}

.setting-item input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 0 10px rgba(96, 165, 250, 0.5);
}

.setting-desc {
  font-size: 11px;
  color: #6b7280;
  margin-top: 8px;
}

/* ==================== Agent透视弹窗 ==================== */
.agent-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
}

.agent-modal {
  width: 520px;
  max-height: 85vh;
  background: linear-gradient(145deg, #0f172a 0%, #1e1b4b 100%);
  border: 1px solid rgba(100, 181, 246, 0.25);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 0 60px rgba(100, 181, 246, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(100, 181, 246, 0.1);
  border-bottom: 1px solid rgba(100, 181, 246, 0.15);
}

.modal-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: #60a5fa;
  display: flex;
  align-items: center;
  gap: 8px;
}

.close-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: #94a3b8;
  cursor: pointer;
  font-size: 14px;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
  color: #ef4444;
}

.modal-loading {
  padding: 60px 20px;
  text-align: center;
  color: #6b7280;
}

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(100, 181, 246, 0.2);
  border-top-color: #60a5fa;
  border-radius: 50%;
  margin: 0 auto 16px;
  animation: spin 1s linear infinite;
}

.modal-error {
  padding: 40px 20px;
  text-align: center;
  color: #ef4444;
}

.modal-content {
  padding: 16px;
  max-height: calc(85vh - 60px);
  overflow-y: auto;
}

.info-block {
  margin-bottom: 14px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(100, 181, 246, 0.1);
  overflow: hidden;
}

.block-title {
  padding: 10px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  background: rgba(100, 181, 246, 0.05);
  display: flex;
  align-items: center;
  gap: 8px;
}

.block-content {
  padding: 14px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 10px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-item .value {
  font-size: 13px;
  color: #e2e8f0;
}

.info-item .value.highlight {
  color: #60a5fa;
  font-weight: 600;
}

.info-item .value.desc {
  font-size: 12px;
  color: #94a3b8;
}

.status-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.status-badge.positive {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.status-badge.negative {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.status-badge.neutral {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}

.decision-block {
  border-color: rgba(100, 181, 246, 0.25);
  background: linear-gradient(145deg, rgba(100, 181, 246, 0.05) 0%, rgba(0, 0, 0, 0.3) 100%);
}

.decision-block .block-title {
  background: rgba(100, 181, 246, 0.1);
  color: #60a5fa;
}

.news-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.news-item {
  padding: 8px 12px;
  background: rgba(100, 181, 246, 0.08);
  border-radius: 6px;
  font-size: 12px;
  color: #cbd5e1;
  border-left: 3px solid #60a5fa;
}

.empty-state {
  text-align: center;
  padding: 20px;
  color: #4b5563;
}

.empty-state .icon {
  font-size: 20px;
  display: block;
  margin-bottom: 6px;
}

.decision-output {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.decision-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.summary-item {
  text-align: center;
  padding: 12px;
  background: rgba(100, 181, 246, 0.05);
  border-radius: 8px;
}

.summary-item .label {
  display: block;
  font-size: 10px;
  color: #6b7280;
  margin-bottom: 4px;
}

.summary-item .value {
  font-size: 14px;
  font-weight: 600;
}

.summary-item .value.emotion { color: #c084fc; }
.summary-item .value.action { color: #38bdf8; }
.summary-item .value.opinion-change { color: #fbbf24; font-size: 12px; }

.generated-comment {
  padding: 12px;
  background: rgba(251, 191, 36, 0.08);
  border-radius: 8px;
  border: 1px solid rgba(251, 191, 36, 0.2);
}

.generated-comment .label {
  display: block;
  font-size: 10px;
  color: #6b7280;
  margin-bottom: 6px;
}

.comment-text {
  margin: 0;
  font-size: 13px;
  color: #fcd34d;
  font-style: italic;
}

.reasoning {
  padding: 12px;
  background: rgba(100, 181, 246, 0.05);
  border-radius: 8px;
}

.reasoning .label {
  display: block;
  font-size: 10px;
  color: #6b7280;
  margin-bottom: 6px;
}

.reasoning-text {
  margin: 0;
  font-size: 12px;
  color: #cbd5e1;
  line-height: 1.5;
}

.raw-response {
  padding: 12px;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 8px;
  border: 1px solid rgba(100, 181, 246, 0.1);
}

.raw-response .label {
  display: block;
  font-size: 10px;
  color: #6b7280;
  margin-bottom: 8px;
}

.json-code {
  margin: 0;
  padding: 10px;
  background: #0a0f1a;
  border-radius: 6px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 10px;
  color: #86efac;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 150px;
  overflow-y: auto;
}

/* ==================== 报告提示 ==================== */
.report-toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  background: rgba(34, 197, 94, 0.15);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 12px;
  color: #4ade80;
  font-size: 14px;
  animation: slideIn 0.3s ease;
  z-index: 50;
}

@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

.btn-open-report {
  padding: 6px 14px;
  background: rgba(34, 197, 94, 0.2);
  border: 1px solid rgba(34, 197, 94, 0.4);
  border-radius: 6px;
  color: #4ade80;
  font-size: 12px;
  cursor: pointer;
}

.btn-open-report:hover {
  background: rgba(34, 197, 94, 0.3);
}

/* ==================== 响应式适配 ==================== */
@media (max-width: 1600px) {
  .kpi-cards {
    grid-template-columns: repeat(5, 1fr);
  }

  .kpi-value {
    font-size: 20px;
  }
}

@media (max-width: 1400px) {
  .control-panel {
    width: 280px;
    min-width: 280px;
  }

  .kpi-cards {
    grid-template-columns: repeat(5, 1fr);
  }

  .kpi-icon {
    width: 36px;
    height: 36px;
    font-size: 16px;
  }
}
</style>

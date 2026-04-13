<template>
  <!--
    信息茧房推演系统主界面
    左侧: 控制面板
    右侧: 可视化面板 (观点分布、传播网络、舆论趋势)
  -->
  <div class="app-container">
    <!-- 左侧控制面板 -->
    <aside class="control-panel">
      <h1>信息茧房推演</h1>

      <!-- 连接状态 -->
      <div class="connection-status" :class="connectionClass">
        {{ connectionStatus }}
      </div>

      <!-- 模式选择 -->
      <div class="control-group">
        <label>推演模式</label>
        <div class="mode-toggle">
          <button
            :class="['mode-btn', { active: useLLM }]"
            @click="useLLM = true"
            :disabled="isRunning"
          >
            LLM 驱动
          </button>
          <button
            :class="['mode-btn', { active: !useLLM }]"
            @click="useLLM = false"
            :disabled="isRunning"
          >
            数学模型
          </button>
        </div>
        <small style="color: #888">{{ useLLM ? 'Agent 通过大模型决策' : '使用数学公式计算' }}</small>
      </div>

      <!-- 参数控制 -->
      <div class="control-group">
        <label>
          算法茧房强度
          <span class="value">{{ cocoonStrength.toFixed(2) }}</span>
        </label>
        <div class="slider-container">
          <input
            type="range"
            v-model.number="cocoonStrength"
            min="0"
            max="1"
            step="0.05"
            :disabled="isRunning"
          />
        </div>
        <small style="color: #888">越高越容易强化既有观点</small>
      </div>

      <div class="control-group">
        <label>
          官方辟谣延迟
          <span class="value">{{ debunkDelay }} 步</span>
        </label>
        <div class="slider-container">
          <input
            type="range"
            v-model.number="debunkDelay"
            min="0"
            max="30"
            step="1"
            :disabled="isRunning"
          />
        </div>
        <small style="color: #888">谣言传播多久后发布辟谣</small>
      </div>

      <div class="control-group">
        <label>
          初始谣言传播率
          <span class="value">{{ (initialRumorSpread * 100).toFixed(0) }}%</span>
        </label>
        <div class="slider-container">
          <input
            type="range"
            v-model.number="initialRumorSpread"
            min="0.1"
            max="0.6"
            step="0.05"
            :disabled="isRunning"
          />
        </div>
      </div>

      <!-- 操作按钮 -->
      <button
        class="btn-start"
        @click="startSimulation"
        :disabled="isRunning || !isConnected"
      >
        {{ isRunning ? `推演中... (${currentStep}/${maxSteps})` : '开始推演' }}
      </button>

      <button
        v-if="isRunning"
        class="btn-start"
        style="background: linear-gradient(135deg, #d32f2f, #c62828); margin-top: 8px;"
        @click="stopSimulation"
      >
        停止推演
      </button>

      <!-- 进度显示 -->
      <div v-if="isRunning && useLLM && agentProgress" class="progress-notice">
        <p>{{ agentProgress }}</p>
      </div>

      <!-- 报告生成按钮 -->
      <button
        v-if="currentStep > 0 && !isRunning"
        class="btn-report"
        @click="generateReport"
      >
        生成分析报告
      </button>

      <!-- 报告成功提示 -->
      <div v-if="reportGenerated" class="report-notice">
        <p>报告已生成</p>
        <p class="report-path">{{ reportFilename }}</p>
        <button class="btn-open-report" @click="openReport">
          打开报告文件
        </button>
      </div>

      <!-- 统计面板 -->
      <div class="stats-panel">
        <h3>实时统计</h3>
        <div class="stat-item">
          <span>当前步数</span>
          <span class="stat-value">{{ currentStep }}</span>
        </div>
        <div class="stat-item">
          <span>谣言传播率</span>
          <span class="stat-value negative">
            {{ (rumorSpreadRate * 100).toFixed(1) }}%
          </span>
        </div>
        <div class="stat-item">
          <span>真相接受率</span>
          <span class="stat-value positive">
            {{ (truthAcceptanceRate * 100).toFixed(1) }}%
          </span>
        </div>
        <div class="stat-item">
          <span>平均观点</span>
          <span :class="['stat-value', avgOpinionClass]">
            {{ avgOpinion.toFixed(3) }}
          </span>
        </div>
        <div class="stat-item">
          <span>极化指数</span>
          <span class="stat-value neutral">
            {{ polarizationIndex.toFixed(3) }}
          </span>
        </div>
        <div class="stat-item" v-if="debunked">
          <span>辟谣状态</span>
          <span class="stat-value positive">已发布</span>
        </div>
      </div>
    </aside>

    <!-- 右侧可视化面板 -->
    <main class="visualization-panel">
      <!-- 观点分布图 -->
      <div class="viz-card">
        <h2>群体观点分布</h2>
        <div class="viz-content" ref="opinionChart"></div>
        <div class="legend">
          <div class="legend-item">
            <div class="legend-color" style="background: #f44336;"></div>
            <span>相信谣言</span>
          </div>
          <div class="legend-item">
            <div class="legend-color" style="background: #ff9800;"></div>
            <span>中立</span>
          </div>
          <div class="legend-item">
            <div class="legend-color" style="background: #4caf50;"></div>
            <span>相信真相</span>
          </div>
        </div>
      </div>

      <!-- 信息传播网络 -->
      <div class="viz-card">
        <h2>信息传播网络</h2>
        <div class="viz-content" ref="networkChart"></div>
      </div>

      <!-- 舆论趋势图 -->
      <div class="viz-card" style="grid-column: span 2;">
        <h2>舆论演化趋势</h2>
        <div class="viz-content" ref="trendChart"></div>
      </div>
    </main>
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

      // 参数
      cocoonStrength: 0.5,
      debunkDelay: 10,
      initialRumorSpread: 0.3,
      useLLM: true,

      // 状态
      isRunning: false,
      currentStep: 0,
      maxSteps: 50,
      debunked: false,

      // Agent 进度
      agentProgress: '',

      // 统计数据
      rumorSpreadRate: 0,
      truthAcceptanceRate: 0,
      avgOpinion: 0,
      polarizationIndex: 0,

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
      reportPath: ''
    }
  },

  computed: {
    connectionClass() {
      return this.isConnected ? 'connected' : 'disconnected'
    },
    connectionStatus() {
      return this.isConnected ? '已连接' : '未连接'
    },
    avgOpinionClass() {
      if (this.avgOpinion > 0.1) return 'positive'
      if (this.avgOpinion < -0.1) return 'negative'
      return 'neutral'
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
      // 直接连接后端 WebSocket (绕过 vite 代理)
      const wsUrl = 'ws://localhost:8003/ws/simulation'
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
          // 自动重连
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
      this.debunked = false
      this.agentProgress = ''
      this.trendHistory = {
        steps: [],
        rumorRates: [],
        truthRates: [],
        avgOpinions: [],
        polarization: []
      }

      // 发送启动命令
      this.sendAction('start', {
        params: {
          cocoon_strength: this.cocoonStrength,
          debunk_delay: this.debunkDelay,
          population_size: 200,
          initial_rumor_spread: this.initialRumorSpread,
          network_type: 'small_world',
          use_llm: this.useLLM
        }
      })

      // 启动自动推演
      setTimeout(() => {
        if (this.isRunning) {
          const interval = this.useLLM ? 5000 : 500  // LLM 模式间隔更长
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
        if (data.success) {
          console.log('报告已用系统默认应用打开')
        } else {
          alert('打开报告失败: ' + (data.error || '未知错误'))
        }
      } catch (error) {
        console.error('打开报告失败:', error)
        alert('打开报告失败，请手动打开: ' + this.reportPath)
      }
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

      // 更新趋势历史
      this.trendHistory.steps.push(data.step)
      this.trendHistory.rumorRates.push(data.rumor_spread_rate)
      this.trendHistory.truthRates.push(data.truth_acceptance_rate)
      this.trendHistory.avgOpinions.push(data.avg_opinion)
      this.trendHistory.polarization.push(data.polarization_index)

      // 清除进度显示
      this.agentProgress = ''

      // 检查是否完成
      if (data.step >= this.maxSteps) {
        this.isRunning = false
        this.sendAction('stop')
      }

      // 更新图表
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
        tooltip: { trigger: 'axis' },
        xAxis: {
          type: 'category',
          data: this.opinionDist.centers?.map(c => c.toFixed(2)) || [],
          axisLabel: { color: '#aaa', fontSize: 10 },
          name: '观点值',
          nameTextStyle: { color: '#888' }
        },
        yAxis: {
          type: 'value',
          axisLabel: { color: '#aaa' },
          splitLine: { lineStyle: { color: 'rgba(100,100,150,0.2)' } }
        },
        series: [{
          type: 'bar',
          data: data.map((d, i) => {
            const center = d.center
            let color
            if (center < -0.2) color = '#f44336'
            else if (center > 0.2) color = '#4caf50'
            else color = '#ff9800'
            return {
              value: d.value,
              itemStyle: { color }
            }
          }),
          barWidth: '80%'
        }]
      }

      this.opinionChartInstance?.setOption(option)
    },

    renderNetworkChart() {
      if (!this.agents.length) return

      const nodes = this.agents.map(agent => {
        let color
        if (agent.opinion < -0.2) color = '#f44336'
        else if (agent.opinion > 0.2) color = '#4caf50'
        else color = '#ff9800'

        return {
          id: agent.id.toString(),
          symbolSize: 4 + agent.influence * 8,
          itemStyle: { color },
          x: Math.random() * 600,
          y: Math.random() * 400
        }
      })

      const sampledEdges = this.edges
        .filter(() => Math.random() < 0.3)
        .slice(0, 300)
        .map(([source, target]) => ({
          source: source.toString(),
          target: target.toString(),
          lineStyle: { color: 'rgba(100,100,150,0.2)', width: 0.5 }
        }))

      const option = {
        tooltip: {},
        series: [{
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: sampledEdges,
          roam: true,
          draggable: true,
          force: {
            repulsion: 50,
            edgeLength: 30
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: { width: 2 }
          },
          lineStyle: { opacity: 0.3 }
        }]
      }

      this.networkChartInstance?.setOption(option)
    },

    renderTrendChart() {
      const option = {
        tooltip: { trigger: 'axis' },
        legend: {
          data: ['谣言传播率', '真相接受率', '平均观点', '极化指数'],
          textStyle: { color: '#aaa' },
          top: 0
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: this.trendHistory.steps,
          axisLabel: { color: '#aaa' },
          name: '步数',
          nameTextStyle: { color: '#888' }
        },
        yAxis: [
          {
            type: 'value',
            position: 'left',
            axisLabel: { color: '#aaa' },
            splitLine: { lineStyle: { color: 'rgba(100,100,150,0.2)' } },
            min: -1,
            max: 1
          },
          {
            type: 'value',
            position: 'right',
            axisLabel: { color: '#aaa' },
            splitLine: { show: false },
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
            lineStyle: { color: '#f44336' },
            itemStyle: { color: '#f44336' },
            smooth: true
          },
          {
            name: '真相接受率',
            type: 'line',
            yAxisIndex: 1,
            data: this.trendHistory.truthRates,
            lineStyle: { color: '#4caf50' },
            itemStyle: { color: '#4caf50' },
            smooth: true
          },
          {
            name: '平均观点',
            type: 'line',
            yAxisIndex: 0,
            data: this.trendHistory.avgOpinions,
            lineStyle: { color: '#64b5f6' },
            itemStyle: { color: '#64b5f6' },
            smooth: true
          },
          {
            name: '极化指数',
            type: 'line',
            yAxisIndex: 1,
            data: this.trendHistory.polarization,
            lineStyle: { color: '#ff9800', type: 'dashed' },
            itemStyle: { color: '#ff9800' },
            smooth: true
          }
        ]
      }

      this.trendChartInstance?.setOption(option)
    }
  }
}
</script>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
  width: 100vw;
}

.connection-status {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  margin-bottom: 12px;
  text-align: center;
}

.connection-status.connected {
  background: rgba(76, 175, 80, 0.2);
  color: #81c784;
  border: 1px solid rgba(76, 175, 80, 0.4);
}

.connection-status.disconnected {
  background: rgba(244, 67, 54, 0.2);
  color: #e57373;
  border: 1px solid rgba(244, 67, 54, 0.4);
}

.mode-toggle {
  display: flex;
  gap: 8px;
}

.mode-btn {
  flex: 1;
  padding: 8px;
  border: 1px solid #444;
  background: transparent;
  color: #aaa;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-btn.active {
  background: rgba(100, 181, 246, 0.2);
  border-color: #64b5f6;
  color: #64b5f6;
}

.mode-btn:hover:not(:disabled) {
  background: rgba(100, 181, 246, 0.1);
}

.mode-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.progress-notice {
  background: rgba(100, 181, 246, 0.15);
  border: 1px solid rgba(100, 181, 246, 0.4);
  border-radius: 8px;
  padding: 12px;
  margin-top: 12px;
  text-align: center;
}

.progress-notice p {
  margin: 0;
  font-size: 13px;
  color: #64b5f6;
}
</style>

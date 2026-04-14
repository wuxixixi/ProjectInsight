# 前端双层网络可视化修改指南

## 1. 在 data() 中添加新属性

```javascript
// 双层网络相关
useDualNetwork: false,       // 是否使用双层网络模式
publicEdges: [],             // 公域网络边
privateEdges: [],            // 私域网络边
activeNetworkTab: 'public',  // 当前显示的网络 Tab
publicRumorRate: 0,          // 公域谣言率
privateRumorRate: 0,         // 私域谣言率
numCommunities: 0,           // 社群数量
numInfluencers: 0,           // 大V数量

// 趋势历史（双层版本）
trendHistoryDual: {
  steps: [],
  rumorRates: [],
  truthRates: [],
  avgOpinions: [],
  polarization: [],
  silenceRates: [],
  publicRumorRates: [],      // 公域谣言率历史
  privateRumorRates: []      // 私域谣言率历史
}
```

## 2. 添加网络 Tab 切换组件（替换原来的网络图区域）

```html
<!-- 网络图区域 - Tab 切换 -->
<div class="chart-card network-chart">
  <div class="chart-header">
    <h3>信息传播网络</h3>
    <div class="network-tabs">
      <button 
        :class="['tab-btn', { active: activeNetworkTab === 'public' }]"
        @click="activeNetworkTab = 'public'"
      >
        🏛️ 公域广场
      </button>
      <button 
        :class="['tab-btn', { active: activeNetworkTab === 'private' }]"
        @click="activeNetworkTab = 'private'"
      >
        🏠 私域茧房
      </button>
    </div>
  </div>
  <div class="chart-body" ref="networkChart"></div>
  <div class="network-info">
    <span v-if="activeNetworkTab === 'public'">
      大V数量: {{ numInfluencers }} | 节点按影响力大小显示
    </span>
    <span v-else>
      社群数量: {{ numCommunities }} | 节点按社群颜色区分
    </span>
  </div>
</div>
```

## 3. 更新 renderNetworkChart 方法（支持双层网络）

```javascript
renderNetworkChart() {
  if (!this.agents.length) return

  // 根据当前 Tab 选择边数据
  const edges = this.activeNetworkTab === 'public' 
    ? this.publicEdges 
    : this.privateEdges
  
  // 如果没有双层网络数据，使用旧版 edges
  const actualEdges = edges.length > 0 ? edges : this.edges

  const nodes = this.agents.map(agent => {
    let color
    if (agent.opinion < -0.2) color = '#ef4444'
    else if (agent.opinion > 0.2) color = '#22c55e'
    else color = '#f59e0b'

    // 沉默节点透明度降低
    const opacity = agent.is_silent ? 0.3 : 1.0
    
    // 公域网络：按影响力大小，大V节点更大
    // 私域网络：按社群颜色区分
    let symbolSize
    if (this.activeNetworkTab === 'public') {
      symbolSize = agent.is_influencer 
        ? 12 + agent.influence * 15  // 大V节点更大
        : 4 + agent.influence * 6
    } else {
      // 私域网络：使用社群颜色
      const communityColors = [
        '#60a5fa', '#a78bfa', '#f472b6', '#fb923c',
        '#4ade80', '#22d3ee', '#facc15', '#e879f9'
      ]
      color = communityColors[agent.community_id % 8] || color
      symbolSize = agent.is_silent ? 3 : 5
    }

    return {
      id: agent.id.toString(),
      symbolSize: symbolSize,
      itemStyle: {
        color: color,
        opacity: opacity,
        // 大V节点特殊样式
        borderColor: agent.is_influencer ? '#fcd34d' : null,
        borderWidth: agent.is_influencer ? 2 : 0
      },
      label: agent.is_influencer ? {
        show: true,
        text: 'V',
        fontSize: 10,
        color: '#fcd34d'
      } : null,
      x: Math.random() * 800,
      y: Math.random() * 500
    }
  })

  const sampledEdges = actualEdges
    .filter(() => Math.random() < 0.3)
    .slice(0, 500)
    .map(([source, target]) => ({
      source: source.toString(),
      target: target.toString(),
      lineStyle: { 
        color: this.activeNetworkTab === 'public' 
          ? 'rgba(100, 181, 246, 0.2)' 
          : 'rgba(167, 139, 250, 0.15)', 
        width: 0.5 
      }
    }))

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (params) => {
        if (params.dataType === 'node') {
          const agent = this.agents.find(a => a.id.toString() === params.data.id)
          if (agent) {
            const influencerTag = agent.is_influencer ? ' [大V]' : ''
            const communityTag = ` [社群${agent.community_id + 1}]`
            const tag = this.activeNetworkTab === 'public' ? influencerTag : communityTag
            return `<div style="padding: 8px;">
              <div style="font-weight: bold;">Agent ${agent.id}${tag}</div>
              <div>观点: ${agent.opinion.toFixed(3)}</div>
              <div>发布渠道: ${agent.publish_channel || 'none'}</div>
              <div style="color: #64b5f6;">点击查看详情</div>
            </div>`
          }
        }
        return ''
      }
    },
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes,
      links: sampledEdges,
      roam: true,
      draggable: true,
      force: {
        repulsion: this.activeNetworkTab === 'public' ? 100 : 50,
        edgeLength: this.activeNetworkTab === 'public' ? 60 : 30,
        gravity: 0.1
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 2 }
      }
    }]
  }

  this.networkChartInstance?.setOption(option)

  // 点击事件
  this.networkChartInstance?.off('click')
  this.networkChartInstance?.on('click', (params) => {
    if (params.dataType === 'node') {
      const agentId = parseInt(params.data.id)
      this.inspectAgent(agentId)
    }
  })
}
```

## 4. 更新趋势图（拆分公域/私域谣言率）

```javascript
renderTrendChart() {
  const hasDualData = this.trendHistory.publicRumorRates.length > 0
  
  const series = [
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
      symbol: 'none'
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
      name: '沉默率',
      type: 'line',
      yAxisIndex: 1,
      data: this.trendHistory.silenceRates,
      lineStyle: { color: '#8b5cf6', width: 2, type: 'dotted' },
      itemStyle: { color: '#8b5cf6' },
      smooth: true,
      symbol: 'none'
    }
  ]

  // 双层网络：添加公域/私域谣言率曲线
  if (hasDualData) {
    series.push({
      name: '公域谣言率',
      type: 'line',
      yAxisIndex: 1,
      data: this.trendHistory.publicRumorRates,
      lineStyle: { color: '#f97316', width: 2, type: 'dashed' },
      itemStyle: { color: '#f97316' },
      smooth: true,
      symbol: 'circle',
      symbolSize: 4
    })
    series.push({
      name: '私域谣言率',
      type: 'line',
      yAxisIndex: 1,
      data: this.trendHistory.privateRumorRates,
      lineStyle: { color: '#dc2626', width: 2, type: 'solid' },
      itemStyle: { color: '#dc2626' },
      smooth: true,
      symbol: 'diamond',
      symbolSize: 4
    })
  }

  const legendData = hasDualData 
    ? ['谣言传播率', '真相接受率', '平均观点', '沉默率', '公域谣言率', '私域谣言率']
    : ['谣言传播率', '真相接受率', '平均观点', '沉默率']

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: {
      data: legendData,
      textStyle: { color: '#6b7280', fontSize: 11 },
      top: 5
    },
    grid: { left: '6%', right: '6%', top: '22%', bottom: '10%' },
    xAxis: {
      type: 'category',
      data: this.trendHistory.steps,
      name: '步数'
    },
    yAxis: [
      { type: 'value', position: 'left', min: -1, max: 1 },
      { type: 'value', position: 'right', min: 0, max: 1 }
    ],
    series: series
  }

  this.trendChartInstance?.setOption(option)
}
```

## 5. 更新 updateState 方法处理双层数据

```javascript
updateState(data) {
  this.currentStep = data.step
  this.agents = data.agents
  
  // 双层网络边数据
  this.publicEdges = data.public_edges || data.edges || []
  this.privateEdges = data.private_edges || []
  
  this.edges = data.edges
  
  // 双层统计数据
  this.publicRumorRate = data.public_rumor_rate || data.rumor_spread_rate
  this.privateRumorRate = data.private_rumor_rate || data.rumor_spread_rate
  this.numCommunities = data.num_communities || 0
  this.numInfluencers = data.num_influencers || 0
  
  // 其他统计
  this.opinionDist = data.opinion_distribution
  this.rumorSpreadRate = data.rumor_spread_rate
  this.truthAcceptanceRate = data.truth_acceptance_rate
  this.avgOpinion = data.avg_opinion
  this.polarizationIndex = data.polarization_index
  this.silenceRate = data.silence_rate || 0
  this.debunked = data.step >= this.debunkDelay

  // 更新趋势历史
  this.trendHistory.steps.push(data.step)
  this.trendHistory.rumorRates.push(data.rumor_spread_rate)
  this.trendHistory.truthRates.push(data.truth_acceptance_rate)
  this.trendHistory.avgOpinions.push(data.avg_opinion)
  this.trendHistory.polarization.push(data.polarization_index)
  this.trendHistory.silenceRates.push(data.silence_rate || 0)
  
  // 双层网络趋势
  this.trendHistory.publicRumorRates.push(data.public_rumor_rate || data.rumor_spread_rate)
  this.trendHistory.privateRumorRates.push(data.private_rumor_rate || data.rumor_spread_rate)

  this.agentProgress = ''

  if (data.step >= this.maxSteps) {
    this.isRunning = false
    this.sendAction('stop')
  }

  this.renderOpinionChart()
  this.renderNetworkChart()
  this.renderTrendChart()
}
```

## 6. CSS 样式

```css
/* 网络 Tab 切换 */
.network-tabs {
  display: flex;
  gap: 8px;
}

.tab-btn {
  padding: 6px 12px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 6px;
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: rgba(100, 181, 246, 0.1);
}

.tab-btn.active {
  background: rgba(100, 181, 246, 0.2);
  border-color: #60a5fa;
  color: #60a5fa;
}

.network-info {
  padding: 8px 12px;
  background: rgba(30, 41, 59, 0.3);
  border-radius: 6px;
  font-size: 11px;
  color: #6b7280;
  margin-top: 8px;
}
```
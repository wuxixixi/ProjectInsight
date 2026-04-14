<template>
  <div class="dashboard-container">
    <!-- 左侧控制面板 -->
    <aside class="control-panel">
      <!-- 标题 -->
      <div class="panel-header">
        <h1>觉测·洞鉴</h1>
        <p class="subtitle">多智能体舆论认知干预沙盘</p>
        <a href="https://github.com/wuxixixi/ProjectInsight" target="_blank" class="project-link">
          <span>📖 项目文档</span>
        </a>
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
        <button v-if="currentStep > 0 && !isRunning && useLLM" class="btn-intelligence" @click="generateIntelligenceReport" :disabled="reportGenerating">
          <span>🧠</span> {{ reportGenerating ? '撰写中...' : '智库专报' }}
        </button>
        <button v-if="!useLLM" class="btn-theory" @click="showMathModelDrawer = true">
          <span>📚</span> 模型说明
        </button>
        <button class="btn-history" @click="fetchReportList">
          <span>📚</span> 历史报告
        </button>
        <button class="btn-settings" @click="showSettingsDrawer = true">
          <span>⚙️</span> 设置
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
        <div class="kpi-card purple">
          <div class="kpi-icon">🤫</div>
          <div class="kpi-content">
            <span class="kpi-label">沉默率</span>
            <span class="kpi-value">{{ (silenceRate * 100).toFixed(1) }}<small>%</small></span>
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
              <div class="network-tabs">
                <button :class="['tab-btn', { active: activeNetworkTab === 'public' }]" @click="activeNetworkTab = 'public'">
                  🏛️ 公域广场
                </button>
                <button :class="['tab-btn', { active: activeNetworkTab === 'private' }]" @click="activeNetworkTab = 'private'">
                  🏠 私域茧房
                </button>
              </div>
            </div>
            <div class="chart-body" ref="networkChart"></div>
            <div class="network-info">
              <span v-if="activeNetworkTab === 'public'">大V数量: {{ numInfluencers }} | 节点大小表示影响力</span>
              <span v-else>社群数量: {{ numCommunities }} | 不同颜色代表不同社群</span>
            </div>
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

    <!-- 数学模型说明抽屉 -->
    <div v-if="showMathModelDrawer" class="drawer-overlay" @click.self="showMathModelDrawer = false">
      <div class="math-model-drawer">
        <div class="drawer-header">
          <h3>📐 数学模型说明</h3>
          <button class="drawer-close" @click="showMathModelDrawer = false">✕</button>
        </div>
        <div class="drawer-body">
          <div v-if="mathModelLoading" class="loading-container">
            <div class="loading-spinner"></div>
            <p>加载模型说明...</p>
          </div>
          <div v-else-if="mathModelExplanation" class="math-model-content">
            <!-- 理论机制 -->
            <h4 class="section-title">🔬 社会心理学机制</h4>
            <div v-for="(theory, key) in mathModelExplanation.theories" :key="key" class="theory-card">
              <div class="theory-header">
                <span class="theory-name">{{ theory.name }}</span>
                <span class="theory-source">{{ theory.theory }}</span>
              </div>
              <div class="theory-formula">
                <code>{{ theory.formula }}</code>
              </div>
              <p class="theory-explanation" v-if="theory.explanation">{{ theory.explanation }}</p>
              <ul v-if="theory.enhancements" class="theory-enhancements">
                <li v-for="(enh, idx) in theory.enhancements" :key="idx">{{ enh }}</li>
              </ul>
            </div>

            <!-- 参数说明 -->
            <h4 class="section-title">🎛️ 参数说明</h4>
            <div class="params-table">
              <div v-for="(param, key) in mathModelExplanation.parameters" :key="key" class="param-row">
                <div class="param-name">{{ param.name }}</div>
                <div class="param-meta">
                  <span class="param-range">{{ param.range }}</span>
                  <span class="param-default">默认: {{ param.default }}</span>
                </div>
                <div class="param-effect">{{ param.effect }}</div>
              </div>
            </div>
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
                <!-- 沉默的螺旋：新增属性 -->
                <div class="info-item">
                  <span class="label">孤立恐惧感</span>
                  <span :class="['value', agentSnapshot.fear_of_isolation > 0.6 ? 'warning' : '']">{{ (agentSnapshot.fear_of_isolation * 100).toFixed(0) }}%</span>
                </div>
                <div class="info-item">
                  <span class="label">沉默状态</span>
                  <span :class="['value', 'status-badge', agentSnapshot.is_silent ? 'silent' : 'active']">{{ agentSnapshot.is_silent ? '🤫 沉默' : '🔊 发声' }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 区块B: 心理博弈过程 (沉默的螺旋) -->
          <div v-if="agentSnapshot.perceived_climate" class="info-block psychology-block">
            <div class="block-title"><span class="block-icon">🌀</span> 心理博弈过程</div>
            <div class="block-content">
              <div class="psychology-analysis">
                <div class="climate-info">
                  <div class="climate-item">
                    <span class="label">邻居数量</span>
                    <span class="value">{{ agentSnapshot.perceived_climate.total }}</span>
                  </div>
                  <div class="climate-item">
                    <span class="label">信谣言比例</span>
                    <span class="value rumor">{{ (agentSnapshot.perceived_climate.pro_rumor_ratio * 100).toFixed(0) }}%</span>
                  </div>
                  <div class="climate-item">
                    <span class="label">信真相比例</span>
                    <span class="value truth">{{ (agentSnapshot.perceived_climate.pro_truth_ratio * 100).toFixed(0) }}%</span>
                  </div>
                  <div class="climate-item">
                    <span class="label">沉默比例</span>
                    <span class="value silent">{{ (agentSnapshot.perceived_climate.silent_ratio * 100).toFixed(0) }}%</span>
                  </div>
                </div>
                <!-- 心理博弈结论 -->
                <div v-if="agentSnapshot.is_silent" class="psychology-conclusion silent">
                  <div class="conclusion-icon">🤫</div>
                  <div class="conclusion-text">
                    <strong>选择沉默</strong>
                    <p>"虽然我不完全认同周围人的观点，但大家都这样想，我怕被孤立/被骂/被攻击，所以选择保持沉默。"</p>
                  </div>
                </div>
                <div v-else class="psychology-conclusion active">
                  <div class="conclusion-icon">🔊</div>
                  <div class="conclusion-text">
                    <strong>选择发声</strong>
                    <p v-if="agentSnapshot.perceived_climate.pro_rumor_ratio > agentSnapshot.perceived_climate.pro_truth_ratio && agentSnapshot.new_opinion > 0.2">
                      "虽然周围信谣言的人更多，但我有足够的勇气和信念表达我的观点。"
                    </p>
                    <p v-else-if="agentSnapshot.perceived_climate.pro_truth_ratio > agentSnapshot.perceived_climate.pro_rumor_ratio && agentSnapshot.new_opinion < -0.2">
                      "虽然周围信真相的人更多，但我坚持自己的判断，不会轻易改变。"
                    </p>
                    <p v-else>
                      "舆论环境相对宽松，我可以自由表达我的观点。"
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 区块C: 信息刺激 -->
          <div class="info-block stimulus-block">
            <div class="block-title"><span class="block-icon">📡</span> 信息刺激</div>
            <div class="block-content">
              <div v-if="agentSnapshot.received_news?.length" class="news-list">
                <div v-for="(news, idx) in agentSnapshot.received_news" :key="idx" class="news-item">{{ news }}</div>
              </div>
              <div v-else class="empty-state">暂无新信息刺激</div>
            </div>
          </div>

          <!-- 区块D: LLM决策输出 -->
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
                    <span class="label">沉默决策</span>
                    <span :class="['value', agentSnapshot.is_silent ? 'silent-status' : 'active-status']">{{ agentSnapshot.is_silent ? '是' : '否' }}</span>
                  </div>
                </div>
                <div class="summary-row">
                  <span class="label">观点变化</span>
                  <span class="value opinion-change">{{ agentSnapshot.old_opinion?.toFixed(3) }} → {{ agentSnapshot.new_opinion?.toFixed(3) }}</span>
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

    <!-- 报告弹窗 -->
    <div v-if="reportGenerated" class="report-modal-overlay" @click.self="closeReport">
      <div class="report-modal">
        <div class="report-modal-header">
          <h3>📄 推演报告</h3>
          <button class="report-close-btn" @click="closeReport">✕</button>
        </div>
        <div class="report-modal-body">
          <div v-if="reportLoading" class="report-loading">
            <div class="loading-spinner"></div>
            <p>加载报告中...</p>
          </div>
          <div v-else-if="reportContent" class="report-content">
            <pre>{{ reportContent }}</pre>
          </div>
          <div v-else class="report-placeholder">
            <p>报告加载失败</p>
          </div>
        </div>
        <div class="report-modal-footer">
          <button class="btn-download" @click="downloadReport">⬇ 下载报告</button>
        </div>
      </div>
    </div>

    <!-- 历史报告列表弹窗 -->
    <div v-if="showReportList" class="report-modal-overlay" @click.self="showReportList = false">
      <div class="report-modal">
        <div class="report-modal-header">
          <h3>📚 历史报告</h3>
          <button class="report-close-btn" @click="showReportList = false">✕</button>
        </div>
        <div class="report-modal-body">
          <div v-if="reportListLoading" class="report-loading">
            <div class="loading-spinner"></div>
            <p>加载报告列表...</p>
          </div>
          <div v-else-if="reportList.length > 0" class="report-list">
            <div v-for="report in reportList" :key="report.filename" class="report-item" @click="viewHistoryReport(report)">
              <div class="report-item-icon">📄</div>
              <div class="report-item-info">
                <div class="report-item-name">{{ report.filename }}</div>
                <div class="report-item-meta">{{ formatFileSize(report.size) }} · {{ formatDate(report.modified) }}</div>
              </div>
              <div class="report-item-action">查看</div>
            </div>
          </div>
          <div v-else class="report-placeholder">
            <p>暂无历史报告</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 智库专报弹窗 -->
    <div v-if="showIntelligenceModal" class="intelligence-modal-overlay" @click.self="closeIntelligenceModal">
      <div class="intelligence-modal">
        <div class="intelligence-modal-header">
          <h3>🧠 智库专报</h3>
          <button class="report-close-btn" @click="closeIntelligenceModal">✕</button>
        </div>
        <div class="intelligence-modal-body">
          <!-- 流式输出时显示原始内容 -->
          <div v-if="reportGenerating && intelligenceContent" class="intelligence-content intelligence-streaming">
            <pre>{{ intelligenceContent }}</pre>
            <div class="streaming-cursor">▌</div>
          </div>
          <!-- 生成中但无内容 -->
          <div v-else-if="reportGenerating" class="intelligence-loading">
            <div class="loading-spinner"></div>
            <p>分析师智能体正在撰写专报，请稍候...</p>
            <p class="loading-tip">预计需要10-20秒</p>
          </div>
          <!-- 生成完成后渲染Markdown -->
          <div v-else-if="intelligenceContent" class="intelligence-content markdown-body" v-html="renderedIntelligence"></div>
          <div v-else class="report-placeholder">
            <p>专报生成失败</p>
          </div>
        </div>
        <div class="intelligence-modal-footer">
          <button class="btn-download-intelligence" @click="downloadIntelligenceReport">📥 导出 Markdown</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import { marked } from 'marked'

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

      // LLM并发参数（留空则自动计算）
      maxConcurrent: null,
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
      silenceRate: 0,  // 沉默率

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
        polarization: [],
        silenceRates: [],  // 沉默率历史
        publicRumorRates: [],   // 公域谣言率历史
        privateRumorRates: []   // 私域谣言率历史
      },

      // 双层网络相关
      useDualNetwork: false,
      publicEdges: [],
      privateEdges: [],
      activeNetworkTab: 'public',
      publicRumorRate: 0,
      privateRumorRate: 0,
      numCommunities: 0,
      numInfluencers: 0,

      // 图表实例
      opinionChartInstance: null,
      networkChartInstance: null,
      trendChartInstance: null,

      // 报告相关
      reportGenerated: false,
      reportFilename: '',
      reportPath: '',
      reportContent: '',
      reportLoading: false,

      // 历史报告列表
      showReportList: false,
      reportList: [],
      reportListLoading: false,

      // 智库专报
      showIntelligenceModal: false,
      reportGenerating: false,
      intelligenceContent: '',
      intelligenceFilename: '',

      // Agent透视弹窗
      showAgentModal: false,
      inspectAgentId: null,
      agentSnapshot: null,
      agentLoading: false,

      // 高级设置抽屉
      showSettingsDrawer: false,

      // 数学模型说明抽屉
      showMathModelDrawer: false,
      mathModelLoading: false,
      mathModelExplanation: null
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
    },
    renderedIntelligence() {
      if (!this.intelligenceContent) return ''
      return marked(this.intelligenceContent)
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
    },
    showMathModelDrawer(newVal) {
      if (newVal) {
        this.fetchMathModelExplanation()
      }
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
      const wsUrl = (window.location.origin.replace('http', 'ws')) + '/ws/simulation'
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
            // 自动加载报告内容
            this.loadReportContent()
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
        polarization: [],
        silenceRates: [],
        publicRumorRates: [],
        privateRumorRates: []
      }

      // 重置双层网络数据
      this.publicEdges = []
      this.privateEdges = []
      this.publicRumorRate = 0
      this.privateRumorRate = 0
      this.numCommunities = 0
      this.numInfluencers = 0

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
          max_retries: this.maxRetries,
          use_dual_network: true,  // 启用双层网络模式
          num_communities: 8,      // 私域社群数量
          public_m: 3              // 公域网络参数
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

    async loadReportContent() {
      if (!this.reportFilename) return
      this.reportLoading = true
      this.reportContent = ''
      try {
        const response = await fetch(
          window.location.origin + '/api/report/content?filename=' + encodeURIComponent(this.reportFilename)
        )
        const data = await response.json()
        if (data.success) {
          this.reportContent = data.content
        } else {
          this.reportContent = '加载报告失败: ' + (data.error || '未知错误')
        }
      } catch (error) {
        console.error('加载报告失败:', error)
        this.reportContent = '加载报告失败: ' + error.message
      } finally {
        this.reportLoading = false
      }
    },

    closeReport() {
      this.reportGenerated = false
    },

    // ==================== 数学模型说明 ====================

    async fetchMathModelExplanation() {
      if (this.mathModelExplanation) return  // 已缓存

      this.mathModelLoading = true
      try {
        const response = await fetch(window.location.origin + '/api/math-model/explanation')
        const data = await response.json()
        this.mathModelExplanation = data
      } catch (error) {
        console.error('获取数学模型说明失败:', error)
        this.mathModelExplanation = {
          theories: {},
          parameters: {}
        }
      } finally {
        this.mathModelLoading = false
      }
    },

    // ==================== 历史报告功能 ====================

    async fetchReportList() {
      this.showReportList = true
      this.reportListLoading = true
      this.reportList = []
      try {
        const response = await fetch(window.location.origin + '/api/report/list')
        const data = await response.json()
        this.reportList = data.reports || []
      } catch (error) {
        console.error('获取报告列表失败:', error)
        this.reportList = []
      } finally {
        this.reportListLoading = false
      }
    },

    async viewHistoryReport(report) {
      this.showReportList = false
      this.reportFilename = report.filename
      this.reportPath = report.path
      this.reportGenerated = true
      await this.loadReportContent()
    },

    formatFileSize(bytes) {
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / 1024 / 1024).toFixed(1) + ' MB'
    },

    formatDate(timestamp) {
      const date = new Date(timestamp * 1000)
      return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    },

    downloadReport() {
      if (this.reportFilename) {
        const link = document.createElement('a')
        link.href = window.location.origin + '/api/report/download?filename=' + encodeURIComponent(this.reportFilename)
        link.download = this.reportFilename
        link.click()
      }
    },

    // ==================== 智库专报功能 ====================

    async generateIntelligenceReport() {
      this.showIntelligenceModal = true
      this.reportGenerating = true
      this.intelligenceContent = ''
      this.intelligenceFilename = `intelligence_report_${new Date().toISOString().slice(0,10)}.md`

      try {
        // 使用 EventSource 进行流式接收
        const eventSource = new EventSource(window.location.origin + '/api/report/stream')

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)

            if (data.done) {
              // 生成完成
              eventSource.close()
              this.reportGenerating = false
            } else if (data.error) {
              // 发生错误
              this.intelligenceContent = `# 生成失败\n\n${data.error}`
              eventSource.close()
              this.reportGenerating = false
            } else if (data.content) {
              // 追加内容
              this.intelligenceContent += data.content
              // 自动滚动到底部
              this.$nextTick(() => {
                const container = document.querySelector('.intelligence-modal-body')
                if (container) {
                  container.scrollTop = container.scrollHeight
                }
              })
            }
          } catch (e) {
            console.error('解析SSE数据失败:', e)
          }
        }

        eventSource.onerror = (error) => {
          console.error('EventSource错误:', error)
          if (this.intelligenceContent === '') {
            this.intelligenceContent = '# 生成失败\n\n连接中断，请重试'
          }
          eventSource.close()
          this.reportGenerating = false
        }

      } catch (error) {
        console.error('智库专报生成失败:', error)
        this.intelligenceContent = `# 生成失败\n\n网络错误: ${error.message}`
        this.reportGenerating = false
      }
    },

    closeIntelligenceModal() {
      this.showIntelligenceModal = false
    },

    downloadIntelligenceReport() {
      if (this.intelligenceContent && this.intelligenceFilename) {
        const blob = new Blob([this.intelligenceContent], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = this.intelligenceFilename
        link.click()
        URL.revokeObjectURL(url)
      } else if (this.intelligenceContent) {
        // 没有文件名时，生成一个默认的
        const blob = new Blob([this.intelligenceContent], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `intelligence_report_${new Date().toISOString().slice(0,10)}.md`
        link.click()
        URL.revokeObjectURL(url)
      }
    },

    async openReportInApp() {
      try {
        const response = await fetch(window.location.origin + '/api/report/open', {
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
        alert('打开报告失败: ' + error.message)
      }
    },

    // ==================== Agent透视功能 ====================

    async inspectAgent(agentId) {
      this.inspectAgentId = agentId
      this.showAgentModal = true
      this.agentLoading = true
      this.agentSnapshot = null

      try {
        const response = await fetch(`${window.location.origin}/api/agent/${agentId}/inspect`)
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

      // 双层网络边数据
      this.publicEdges = data.public_edges || data.edges || []
      this.privateEdges = data.private_edges || []

      // 双层统计数据
      this.publicRumorRate = data.public_rumor_rate || data.rumor_spread_rate
      this.privateRumorRate = data.private_rumor_rate || data.rumor_spread_rate
      this.numCommunities = data.num_communities || 0
      this.numInfluencers = data.num_influencers || 0

      this.opinionDist = data.opinion_distribution
      this.rumorSpreadRate = data.rumor_spread_rate
      this.truthAcceptanceRate = data.truth_acceptance_rate
      this.avgOpinion = data.avg_opinion
      this.polarizationIndex = data.polarization_index
      this.silenceRate = data.silence_rate || 0
      this.debunked = data.step >= this.debunkDelay

      this.trendHistory.steps.push(data.step)
      this.trendHistory.rumorRates.push(data.rumor_spread_rate)
      this.trendHistory.truthRates.push(data.truth_acceptance_rate)
      this.trendHistory.avgOpinions.push(data.avg_opinion)
      this.trendHistory.polarization.push(data.polarization_index)
      this.trendHistory.silenceRates.push(data.silence_rate || 0)
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

      // 根据当前 Tab 选择边数据
      const edges = this.activeNetworkTab === 'public' ? this.publicEdges : this.privateEdges
      const actualEdges = edges.length > 0 ? edges : this.edges

      // 社群颜色
      const communityColors = [
        '#60a5fa', '#a78bfa', '#f472b6', '#fb923c',
        '#4ade80', '#22d3ee', '#facc15', '#e879f9'
      ]

      const nodes = this.agents.map(agent => {
        let color
        if (agent.opinion < -0.2) color = '#ef4444'
        else if (agent.opinion > 0.2) color = '#22c55e'
        else color = '#f59e0b'

        // 沉默的节点透明度降低
        const opacity = agent.is_silent ? 0.3 : 1.0

        // 公域网络 vs 私域网络样式
        let symbolSize
        if (this.activeNetworkTab === 'public') {
          // 公域：按影响力大小，大V节点更大
          symbolSize = agent.is_influencer
            ? 12 + agent.influence * 15
            : 4 + agent.influence * 6
        } else {
          // 私域：按社群颜色区分
          color = communityColors[agent.community_id % 8] || color
          symbolSize = agent.is_silent ? 3 : 5
        }

        return {
          id: agent.id.toString(),
          symbolSize: symbolSize,
          itemStyle: {
            color: color,
            opacity: opacity,
            borderColor: agent.is_influencer ? '#fcd34d' : null,
            borderWidth: agent.is_influencer ? 2 : 0
          },
          label: agent.is_influencer && this.activeNetworkTab === 'public' ? {
            show: true,
            formatter: 'V',
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
                const communityTag = ` [社群${(agent.community_id || 0) + 1}]`
                const tag = this.activeNetworkTab === 'public' ? influencerTag : communityTag
                const silenceTag = agent.is_silent ? ' [沉默]' : ''
                return `<div style="padding: 8px;">
                  <div style="font-weight: bold;">Agent ${agent.id}${tag}${silenceTag}</div>
                  <div>观点: ${agent.opinion.toFixed(3)}</div>
                  <div>发布渠道: ${agent.publish_channel || 'none'}</div>
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
            repulsion: this.activeNetworkTab === 'public' ? 100 : 50,
            edgeLength: this.activeNetworkTab === 'public' ? 60 : 30,
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
      // 判断是否有双层数据
      const hasDualData = this.trendHistory.publicRumorRates.length > 0 &&
                          this.publicRumorRates !== this.trendHistory.rumorRates

      const option = {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(20, 25, 40, 0.95)',
          borderColor: 'rgba(100, 181, 246, 0.3)',
          textStyle: { color: '#e0e0e0' }
        },
        legend: {
          data: ['谣言传播率', '真相接受率', '平均观点', '极化指数', '沉默率', '公域谣言率', '私域谣言率'],
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
          },
          {
            name: '沉默率',
            type: 'line',
            yAxisIndex: 1,
            data: this.trendHistory.silenceRates,
            lineStyle: { color: '#8b5cf6', width: 2, type: 'dotted' },
            itemStyle: { color: '#8b5cf6' },
            smooth: true,
            symbol: 'none',
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(139, 92, 246, 0.2)' },
                { offset: 1, color: 'rgba(139, 92, 246, 0.02)' }
              ])
            }
          },
          // 双层网络：公域/私域谣言率曲线
          {
            name: '公域谣言率',
            type: 'line',
            yAxisIndex: 1,
            data: this.trendHistory.publicRumorRates,
            lineStyle: { color: '#f97316', width: 2, type: 'dashed' },
            itemStyle: { color: '#f97316' },
            smooth: true,
            symbol: 'circle',
            symbolSize: 4
          },
          {
            name: '私域谣言率',
            type: 'line',
            yAxisIndex: 1,
            data: this.trendHistory.privateRumorRates,
            lineStyle: { color: '#dc2626', width: 2, type: 'solid' },
            itemStyle: { color: '#dc2626' },
            smooth: true,
            symbol: 'diamond',
            symbolSize: 4
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

.project-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  padding: 4px 10px;
  background: rgba(100, 181, 246, 0.1);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 12px;
  font-size: 11px;
  color: #60a5fa;
  text-decoration: none;
  transition: all 0.2s;
}

.project-link:hover {
  background: rgba(100, 181, 246, 0.2);
  border-color: rgba(100, 181, 246, 0.4);
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

.kpi-card.purple {
  border-color: rgba(139, 92, 246, 0.3);
}

.kpi-card.purple .kpi-icon {
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
}

.kpi-card.purple .kpi-value {
  color: #a78bfa;
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
  margin: 8px 12px;
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

/* ==================== 数学模型说明抽屉 ==================== */
.math-model-drawer {
  width: 520px;
  height: 100%;
  background: rgba(15, 23, 42, 0.98);
  border-left: 1px solid rgba(100, 181, 246, 0.2);
  display: flex;
  flex-direction: column;
}

.math-model-content {
  padding: 0;
}

.math-model-content .section-title {
  font-size: 14px;
  font-weight: 600;
  color: #60a5fa;
  margin: 20px 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.15);
}

.math-model-content .section-title:first-child {
  margin-top: 0;
}

.theory-card {
  background: rgba(30, 41, 59, 0.5);
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 12px;
  border: 1px solid rgba(100, 181, 246, 0.1);
}

.theory-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.theory-name {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.theory-source {
  font-size: 11px;
  color: #6b7280;
  background: rgba(100, 181, 246, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.theory-formula {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 10px;
  overflow-x: auto;
}

.theory-formula code {
  font-family: 'Fira Code', 'Monaco', monospace;
  font-size: 12px;
  color: #a5b4fc;
  white-space: pre-wrap;
  word-break: break-all;
}

.theory-explanation {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.6;
  margin: 0;
}

.theory-enhancements {
  font-size: 11px;
  color: #78716c;
  margin: 8px 0 0 0;
  padding-left: 16px;
}

.theory-enhancements li {
  margin-bottom: 4px;
}

.params-table {
  background: rgba(30, 41, 59, 0.3);
  border-radius: 10px;
  overflow: hidden;
}

.param-row {
  padding: 12px 14px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.08);
}

.param-row:last-child {
  border-bottom: none;
}

.param-name {
  font-size: 13px;
  font-weight: 500;
  color: #e2e8f0;
  margin-bottom: 6px;
}

.param-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 6px;
}

.param-range {
  font-size: 11px;
  color: #60a5fa;
  background: rgba(96, 165, 250, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.param-default {
  font-size: 11px;
  color: #94a3b8;
}

.param-effect {
  font-size: 11px;
  color: #78716c;
  line-height: 1.5;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #94a3b8;
}

.btn-theory {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(59, 130, 246, 0.2) 100%);
  border: 1px solid rgba(139, 92, 246, 0.3);
  color: #c4b5fd;
  padding: 10px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.btn-theory:hover {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.3) 0%, rgba(59, 130, 246, 0.3) 100%);
  border-color: rgba(139, 92, 246, 0.5);
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

/* 沉默状态徽章 */
.status-badge.silent {
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
}

.status-badge.active {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

/* 心理博弈区块 */
.psychology-block {
  border-color: rgba(139, 92, 246, 0.25);
  background: linear-gradient(145deg, rgba(139, 92, 246, 0.05) 0%, rgba(0, 0, 0, 0.3) 100%);
}

.psychology-block .block-title {
  background: rgba(139, 92, 246, 0.1);
  color: #a78bfa;
}

.psychology-analysis {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.climate-info {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.climate-item {
  text-align: center;
  padding: 10px;
  background: rgba(139, 92, 246, 0.08);
  border-radius: 6px;
}

.climate-item .label {
  display: block;
  font-size: 10px;
  color: #6b7280;
  margin-bottom: 4px;
}

.climate-item .value {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.climate-item .value.rumor { color: #f87171; }
.climate-item .value.truth { color: #4ade80; }
.climate-item .value.silent { color: #a78bfa; }

.psychology-conclusion {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  align-items: flex-start;
}

.psychology-conclusion.silent {
  background: rgba(139, 92, 246, 0.1);
  border: 1px solid rgba(139, 92, 246, 0.3);
}

.psychology-conclusion.active {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.conclusion-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.conclusion-text strong {
  display: block;
  font-size: 13px;
  margin-bottom: 4px;
}

.psychology-conclusion.silent .conclusion-text strong { color: #a78bfa; }
.psychology-conclusion.active .conclusion-text strong { color: #4ade80; }

.conclusion-text p {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
  font-style: italic;
  line-height: 1.5;
}

/* 沉默决策状态 */
.value.warning { color: #fbbf24; }
.value.silent-status { color: #a78bfa; font-weight: 600; }
.value.active-status { color: #4ade80; font-weight: 600; }

.summary-row {
  margin-top: 10px;
  padding: 10px;
  background: rgba(100, 181, 246, 0.05);
  border-radius: 6px;
}

.summary-row .label {
  display: block;
  font-size: 10px;
  color: #6b7280;
  margin-bottom: 4px;
}

.summary-row .value {
  font-size: 13px;
  color: #e2e8f0;
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

/* ==================== 报告弹窗 ==================== */
.report-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
}

.report-modal {
  width: 700px;
  max-height: 85vh;
  background: linear-gradient(145deg, #0f172a, #1e1b4b);
  border: 1px solid rgba(100, 181, 246, 0.25);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 0 60px rgba(100, 181, 246, 0.2);
}

.report-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(100, 181, 246, 0.1);
  border-bottom: 1px solid rgba(100, 181, 246, 0.15);
}

.report-modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #60a5fa;
}

.report-close-btn {
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

.report-close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
  color: #ef4444;
}

.report-modal-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  min-height: 300px;
}

.report-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #6b7280;
}

.report-loading .loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(100, 181, 246, 0.2);
  border-top-color: #60a5fa;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}

.report-content {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid rgba(100, 181, 246, 0.1);
}

.report-content pre {
  margin: 0;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

.report-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #6b7280;
}

.report-modal-footer {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  background: rgba(100, 181, 246, 0.05);
  border-top: 1px solid rgba(100, 181, 246, 0.1);
}

.btn-download, .btn-view-file {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-download {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  border: none;
  color: white;
}

.btn-download:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3);
}

.btn-view-file {
  background: rgba(100, 181, 246, 0.15);
  border: 1px solid rgba(100, 181, 246, 0.3);
  color: #60a5fa;
}

.btn-view-file:hover {
  background: rgba(100, 181, 246, 0.25);
}

/* 历史报告列表样式 */
.report-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.report-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(100, 181, 246, 0.15);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.report-item:hover {
  background: rgba(100, 181, 246, 0.1);
  border-color: rgba(100, 181, 246, 0.3);
}

.report-item-icon {
  font-size: 24px;
}

.report-item-info {
  flex: 1;
}

.report-item-name {
  font-size: 13px;
  color: #e2e8f0;
  font-weight: 500;
}

.report-item-meta {
  font-size: 11px;
  color: #6b7280;
  margin-top: 2px;
}

.report-item-action {
  font-size: 12px;
  color: #60a5fa;
  padding: 4px 12px;
  background: rgba(100, 181, 246, 0.15);
  border-radius: 4px;
}

.btn-history {
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

.btn-history:hover {
  background: rgba(100, 181, 246, 0.1);
  color: #60a5fa;
}

/* 智库专报按钮 */
.btn-intelligence {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  background: linear-gradient(135deg, rgba(167, 139, 250, 0.2), rgba(139, 92, 246, 0.2));
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 8px;
  color: #c4b5fd;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-intelligence:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(167, 139, 250, 0.3), rgba(139, 92, 246, 0.3));
  border-color: rgba(167, 139, 250, 0.5);
  color: #ddd6fe;
}

.btn-intelligence:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 智库专报模态框 */
.intelligence-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  z-index: 400;
  display: flex;
  align-items: center;
  justify-content: center;
}

.intelligence-modal {
  width: 70%;
  max-width: 1000px;
  max-height: 90vh;
  background: linear-gradient(145deg, #0f172a, #1e1b4b);
  border: 1px solid rgba(167, 139, 250, 0.25);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 0 80px rgba(167, 139, 250, 0.15);
}

.intelligence-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: rgba(167, 139, 250, 0.1);
  border-bottom: 1px solid rgba(167, 139, 250, 0.15);
}

.intelligence-modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #c4b5fd;
}

.intelligence-modal-body {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  min-height: 300px;
}

.intelligence-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #94a3b8;
}

.intelligence-loading .loading-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid rgba(167, 139, 250, 0.2);
  border-top-color: #a78bfa;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

.loading-tip {
  font-size: 12px;
  color: #6b7280;
  margin-top: 8px;
}

.intelligence-content {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 24px;
  border: 1px solid rgba(100, 181, 246, 0.1);
  color: #e2e8f0;
  line-height: 1.8;
}

/* 流式输出样式 */
.intelligence-streaming {
  background: rgba(0, 0, 0, 0.5);
}

.intelligence-streaming pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  font-family: 'Inter', 'JetBrains Mono', monospace;
  font-size: 14px;
  line-height: 1.7;
  color: #a5b4fc;
}

.streaming-cursor {
  display: inline;
  animation: blink 1s infinite;
  color: #60a5fa;
  font-size: 16px;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* Markdown 样式 */
.intelligence-content h1 {
  font-size: 24px;
  font-weight: 700;
  color: #c4b5fd;
  margin: 0 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 2px solid rgba(167, 139, 250, 0.3);
}

.intelligence-content h2 {
  font-size: 20px;
  font-weight: 600;
  color: #a78bfa;
  margin: 28px 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(167, 139, 250, 0.2);
}

.intelligence-content h3 {
  font-size: 16px;
  font-weight: 600;
  color: #818cf8;
  margin: 20px 0 12px 0;
}

.intelligence-content h4 {
  font-size: 14px;
  font-weight: 600;
  color: #60a5fa;
  margin: 16px 0 8px 0;
}

.intelligence-content p {
  margin: 0 0 16px 0;
  line-height: 1.8;
}

.intelligence-content ul, .intelligence-content ol {
  margin: 0 0 16px 0;
  padding-left: 24px;
}

.intelligence-content li {
  margin-bottom: 8px;
  line-height: 1.6;
}

.intelligence-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}

.intelligence-content th, .intelligence-content td {
  padding: 10px 14px;
  border: 1px solid rgba(100, 181, 246, 0.2);
  text-align: left;
}

.intelligence-content th {
  background: rgba(100, 181, 246, 0.1);
  color: #60a5fa;
  font-weight: 600;
}

.intelligence-content tr:nth-child(even) td {
  background: rgba(0, 0, 0, 0.2);
}

.intelligence-content blockquote {
  border-left: 4px solid #a78bfa;
  padding-left: 16px;
  margin: 16px 0;
  color: #94a3b8;
  font-style: italic;
}

.intelligence-content code {
  background: rgba(0, 0, 0, 0.4);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  color: #86efac;
}

.intelligence-content pre {
  background: rgba(0, 0, 0, 0.4);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 16px 0;
}

.intelligence-content pre code {
  background: none;
  padding: 0;
}

.intelligence-content strong {
  color: #fcd34d;
}

.intelligence-content em {
  color: #a5b4fc;
}

.intelligence-content hr {
  border: none;
  border-top: 1px solid rgba(100, 181, 246, 0.2);
  margin: 24px 0;
}

.intelligence-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  background: rgba(167, 139, 250, 0.05);
  border-top: 1px solid rgba(167, 139, 250, 0.1);
}

.btn-download-intelligence {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-download-intelligence:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
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

<template>
  <div class="dashboard-container">
    <!-- 顶部流程引导 -->
    <div class="workflow-guide">
      <div class="workflow-steps">
        <div :class="['workflow-step', { active: !isRunning && currentStep === 0 && pendingEvents.length === 0, completed: pendingEvents.length > 0 || currentStep > 0 }]">
          <span class="step-number">1</span>
          <span class="step-text">配置参数</span>
        </div>
        <div class="step-connector" :class="{ active: pendingEvents.length > 0 || currentStep > 0 }"></div>
        <div :class="['workflow-step', { active: !isRunning && currentStep === 0 && pendingEvents.length > 0, completed: currentStep > 0 }]">
          <span class="step-number">2</span>
          <span class="step-text">注入事件</span>
        </div>
        <div class="step-connector" :class="{ active: currentStep > 0 }"></div>
        <div :class="['workflow-step', { active: isRunning, completed: currentStep > 0 && !isRunning }]">
          <span class="step-number">3</span>
          <span class="step-text">开始推演</span>
        </div>
        <div class="step-connector" :class="{ active: currentStep > 0 }"></div>
        <div :class="['workflow-step', { active: reportGenerated }]">
          <span class="step-number">4</span>
          <span class="step-text">生成报告</span>
        </div>
      </div>
    </div>

    <!-- 左侧控制面板 -->
    <aside class="control-panel">
      <!-- 标题 -->
      <div class="panel-header">
        <div class="header-row">
          <a href="https://www.sass.org.cn/" target="_blank" class="sass-logo-link">
            <img src="/sass-logo.png" alt="上海社会科学院" class="sass-logo" />
          </a>
          <h1>觉测·洞鉴</h1>
        </div>
        <p class="subtitle">多智能体舆论认知干预沙盘</p>
        <div class="header-links">
          <a href="https://github.com/wuxixixi/ProjectInsight" target="_blank" class="project-link">
            <span>📖 项目文档</span>
          </a>
          <a href="#" @click.prevent="showUsageDrawer = true" class="project-link">
            <span>📋 使用说明</span>
          </a>
        </div>
      </div>

      <!-- 事件注入区块（核心流程） -->
      <div class="event-inject-section">
        <div class="section-header">
          <span class="section-icon">📰</span>
          <span class="section-title">事件注入</span>
          <span v-if="pendingEvents.length > 0" class="event-count-badge">{{ pendingEvents.length }}</span>
        </div>
        
        <!-- 有待注入事件 -->
        <div v-if="pendingEvents.length > 0" class="pending-events-mini">
          <div class="pending-mini-item" v-for="(event, index) in pendingEvents.slice(0, 3)" :key="index">
            <span class="mini-index">#{{ index + 1 }}</span>
            <span class="mini-content">{{ event.content.substring(0, 35) }}{{ event.content.length > 35 ? '...' : '' }}</span>
            <span class="mini-entities" v-if="event.knowledgeGraph?.entities?.length">{{ event.knowledgeGraph.entities.length }}实体</span>
          </div>
          <div v-if="pendingEvents.length > 3" class="more-events">
            +{{ pendingEvents.length - 3 }} 更多事件
          </div>
          <div class="event-actions-row">
            <button class="btn-event-add" @click="showEventAirdrop = true">➕ 添加</button>
            <button v-if="!isRunning && !hasStopped" class="btn-event-start" @click="startSimulation">🚀 开始推演</button>
            <button v-if="!isRunning && hasStopped" class="btn-event-reset" @click="resetSimulation">↻ 重新推演</button>
          </div>
        </div>

        <!-- 无事件时引导 -->
        <div v-else class="no-event-hint">
          <div class="hint-text" v-if="!isPaused">⚠️ 必须先注入事件才能推演</div>
          <div class="hint-text" v-else>💡 暂停中可注入事件</div>
          <button class="btn-inject-primary" @click="showEventAirdrop = true">
            📝 注入新闻事件
          </button>
        </div>
      </div>

      <!-- 帮助说明（可折叠） -->
      <div class="help-section">
        <div class="help-header" @click="showHelp = !showHelp">
          <span>💡 使用说明</span>
          <span :class="['help-toggle', { expanded: showHelp }]">▼</span>
        </div>
        <div v-if="showHelp" class="help-content">
          <div class="help-item">
            <strong>推演模式：</strong>
            <p>• <b>LLM驱动</b>：Agent由大语言模型决策，行为更真实</p>
            <p>• <b>数学模型</b>：基于社会心理学公式快速计算</p>
          </div>
          <div class="help-item">
            <strong>六大机制：</strong>
            <p>• <b>社交传播</b>：受邻居观点影响</p>
            <p>• <b>算法茧房</b>：推荐强化既有立场</p>
            <p>• <b>沉默螺旋</b>：少数派因恐惧孤立</p>
            <p>• <b>群体极化</b>：讨论导致观点极端</p>
            <p>• <b>逆火效应</b>：权威回应反而强化误信</p>
            <p>• <b>认知失调</b>：矛盾信息强化信念</p>
          </div>
          <div class="help-item">
            <strong>核心参数：</strong>
            <p>• <b>茧房强度</b>：算法推荐强化观点的程度</p>
            <p>• <b>权威回应延迟</b>：负面信息传播多久后官方介入</p>
            <p>• <b>双层网络</b>：模拟公域（微博）+私域（微信群）</p>
          </div>
          <div class="help-item">
            <strong>操作流程：</strong>
            <p>1. 配置参数 → 2. 注入事件 → 3. 开始推演 → 4. 生成报告</p>
          </div>
          <div class="help-item">
            <strong>事件注入：</strong>
            <p>必须先注入新闻事件，系统将解析提取知识图谱，作为推演的基础</p>
          </div>
          <div class="help-item">
            <strong>观点范围：</strong>
            <p>-1（完全误信）→ 0（中立）→ +1（完全正确认知）</p>
          </div>
        </div>
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

      <!-- 运行模式（Phase 3） -->
      <div class="control-section">
        <label class="section-label">运行模式</label>
        <div class="mode-toggle">
          <button :class="['mode-btn', { active: simulationMode === 'sandbox' }]" @click="simulationMode = 'sandbox'" :disabled="isRunning">
            <span class="mode-icon">🎮</span>
            沙盘推演
          </button>
          <button :class="['mode-btn', { active: simulationMode === 'news' }]" @click="simulationMode = 'news'" :disabled="isRunning">
            <span class="mode-icon">📰</span>
            新闻推演
          </button>
        </div>
        <p class="param-desc" v-if="simulationMode === 'sandbox'">参数驱动，研究传播机制</p>
        <p class="param-desc" v-else>真实分布锚定，预测现实演进</p>
      </div>

      <!-- 真实分布锚定（新闻模式） -->
      <div class="control-section" v-if="simulationMode === 'news'">
        <label class="section-label">真实分布锚定</label>
        <div class="init-dist-config">
          <div class="param-item">
            <div class="param-header">
              <span class="param-label">误信比例</span>
              <span class="param-value">{{ (initDistRumor * 100).toFixed(0) }}%</span>
            </div>
            <input type="range" v-model.number="initDistRumor" min="0" max="0.8" step="0.05" :disabled="isRunning" />
          </div>
          <div class="param-item">
            <div class="param-header">
              <span class="param-label">正确认知比例</span>
              <span class="param-value">{{ (initDistTruth * 100).toFixed(0) }}%</span>
            </div>
            <input type="range" v-model.number="initDistTruth" min="0" max="0.8" step="0.05" :disabled="isRunning" />
          </div>
          <div class="init-dist-summary">
            <span>中立: {{ ((1 - initDistRumor - initDistTruth) * 100).toFixed(0) }}%</span>
            <span class="dist-bar">
              <span class="dist-rumor" :style="{ width: (initDistRumor * 100) + '%' }"></span>
              <span class="dist-neutral" :style="{ width: ((1 - initDistRumor - initDistTruth) * 100) + '%' }"></span>
              <span class="dist-truth" :style="{ width: (initDistTruth * 100) + '%' }"></span>
            </span>
          </div>
        </div>
      </div>

      <!-- 核心参数 -->
      <div class="control-section">
        <div class="param-item">
          <div class="param-header">
            <div class="param-label-with-help">
              <span class="param-label">算法茧房强度</span>
              <span class="param-help" title="模拟推荐算法强化既有观点的程度。0=无茧房，1=完全茧房（只看到同温层内容）。建议：探索权威回应效果时设0.3-0.5">❓</span>
            </div>
            <span class="param-value">{{ cocoonStrength.toFixed(2) }}</span>
          </div>
          <input type="range" v-model.number="cocoonStrength" min="0" max="1" step="0.05" :disabled="isRunning" />
          <p class="param-desc">越高越容易强化既有观点</p>
        </div>

        <div class="param-item">
          <div class="param-header">
            <div class="param-label-with-help">
              <span class="param-label">权威回应延迟</span>
              <span class="param-help" title="负面信息传播多少步后发布权威回应。延迟越长，误信传播范围越广，权威回应效果越差。建议：对比0步和10步的差异">❓</span>
            </div>
            <span class="param-value">{{ debunkDelay }} 步</span>
          </div>
          <input type="range" v-model.number="debunkDelay" min="0" max="30" step="1" :disabled="isRunning" />
          <p class="param-desc">负面信息传播多久后发布权威回应</p>
        </div>

        <div class="param-item">
          <div class="param-header">
            <div class="param-label-with-help">
              <span class="param-label">初始误信率</span>
              <span class="param-help" title="推演开始时已误信的人群比例">❓</span>
            </div>
            <span class="param-value">{{ (initialRumorSpread * 100).toFixed(0) }}%</span>
          </div>
          <input type="range" v-model.number="initialRumorSpread" min="0.1" max="0.6" step="0.05" :disabled="isRunning" />
        </div>

        <div class="param-item">
          <div class="param-header">
            <div class="param-label-with-help">
              <span class="param-label">Agent数量</span>
              <span class="param-help" title="模拟的智能体数量。LLM模式建议50-100以控制成本，数学模型模式可设200-500">❓</span>
            </div>
            <span class="param-value">{{ populationSize }}</span>
          </div>
          <input type="range" v-model.number="populationSize" min="50" max="500" step="50" :disabled="isRunning" />
        </div>

        <!-- 双层网络开关 -->
        <div class="param-item">
          <div class="param-header">
            <div class="param-label-with-help">
              <span class="param-label">双层网络模式</span>
              <span class="param-help" title="模拟公域（微博）+私域（微信）。公域存在大V，信息传播快；私域分成多个社群，跨社群传播难">❓</span>
            </div>
            <label class="switch">
              <input type="checkbox" v-model="useDualNetwork" :disabled="isRunning" />
              <span class="slider"></span>
            </label>
          </div>
          <p class="param-desc">{{ useDualNetwork ? '模拟公域+私域信息传播' : '单层社交网络' }}</p>
        </div>

        <!-- 私域网络类型（双层模式时显示） -->
        <div class="param-item" v-if="useDualNetwork">
          <div class="param-header">
            <span class="param-label">私域网络类型</span>
          </div>
          <select v-model="networkType" :disabled="isRunning" class="network-select">
            <option value="small_world">小世界网络</option>
            <option value="scale_free">无标度网络</option>
            <option value="random">随机网络</option>
          </select>
          <p class="param-desc">{{ networkTypeDesc }}</p>
          <p class="param-hint">注：公域广场固定为无标度模型以模拟大V效应</p>
        </div>

        <!-- 社交网络类型（单层模式时显示） -->
        <div class="param-item" v-if="!useDualNetwork">
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
        <button v-if="!isRunning && !hasStopped" class="btn-start" @click="startSimulation" :disabled="!isConnected || pendingEvents.length === 0">
          <span class="btn-icon">▶</span>
          开始推演
        </button>
        <button v-if="!isRunning && hasStopped" class="btn-reset" @click="resetSimulation">
          <span class="btn-icon">↻</span>
          重新推演
        </button>
        <template v-if="isRunning">
          <div class="btn-group-row">
            <button v-if="!isPaused" class="btn-pause" @click="pauseSimulation">
              <span class="btn-icon">⏸</span>
              暂停
            </button>
            <button v-else class="btn-resume" @click="resumeSimulation">
              <span class="btn-icon">▶</span>
              继续
            </button>
            <button class="btn-stop" @click="stopSimulation">
              <span class="btn-icon">■</span>
              停止
            </button>
          </div>
        </template>

        <!-- 进度显示 -->
        <div v-if="isRunning && !isPaused" class="progress-container">
          <div class="progress-header">
            <div class="progress-spinner"></div>
            <span class="progress-title">推演进行中...</span>
            <span class="progress-step">步骤 {{ currentStep }}/{{ maxSteps }}</span>
          </div>
          <div class="progress-bar-wrapper">
            <div class="progress-bar" :style="{ width: Math.round(currentStep / maxSteps * 100) + '%' }"></div>
          </div>
          <div class="progress-info">
            <span class="progress-agent" v-if="progressData.agentId !== null">
              <span class="agent-label">当前Agent:</span>
              <span class="agent-id">#{{ progressData.agentId }}</span>
              <span class="agent-opinion" :class="getOpinionClass(progressData.agentOpinion)">
                (观点: {{ progressData.agentOpinion > 0 ? '+' : '' }}{{ progressData.agentOpinion }})
              </span>
              <span class="agent-stance" :class="'stance-' + progressData.agentStance">
                {{ progressData.agentStance }}
              </span>
            </span>
            <span class="progress-count" v-if="progressData.total > 0">本步Agent: {{ progressData.step }}/{{ progressData.total }}</span>
          </div>
        </div>

        <!-- 暂停状态提示 -->
        <div v-if="isRunning && isPaused" class="pause-container">
          <div class="pause-header">
            <span class="pause-icon">⏸</span>
            <span class="pause-title">推演已暂停</span>
            <span class="pause-step">步骤 {{ currentStep }}/{{ maxSteps }}</span>
          </div>
          <div class="pause-hint">可注入事件后点击「继续」恢复推演</div>
        </div>
      </div>

      <!-- 底部功能面板（分组折叠） -->
      <div class="panel-footer-grouped">
        <!-- 知识图谱组 -->
        <div class="footer-group">
          <div class="group-header" @click="toggleGroup('kg')">
            <span>🕸️ 知识图谱</span>
            <span :class="['group-toggle', { expanded: expandedGroups.kg }]">▼</span>
          </div>
          <div v-if="expandedGroups.kg" class="group-buttons">
            <button class="btn-group" @click="showNewsParser = true">
              <span>📰</span> 解析新闻
            </button>
            <button v-if="knowledgeGraph.entities && knowledgeGraph.entities.length > 0" class="btn-group" @click="showKnowledgeGraph = true">
              <span>🔍</span> 查看图谱
            </button>
          </div>
        </div>

        <!-- 报告分析组 -->
        <div class="footer-group">
          <div class="group-header" @click="toggleGroup('report')">
            <span>📊 报告分析</span>
            <span :class="['group-toggle', { expanded: expandedGroups.report }]">▼</span>
          </div>
          <div v-if="expandedGroups.report" class="group-buttons">
            <button v-if="currentStep > 0 && !isRunning" class="btn-group" @click="generateReport">
              <span>📄</span> 生成报告
            </button>
            <button v-if="currentStep > 0 && !isRunning && useLLM" class="btn-group" @click="generateIntelligenceReport" :disabled="reportGenerating">
              <span>🧠</span> {{ reportGenerating ? '撰写中...' : '智库专报' }}
            </button>
            <button class="btn-group" @click="fetchReportList">
              <span>📚</span> 历史报告
            </button>
            <button v-if="!useLLM" class="btn-group" @click="showMathModelDrawer = true">
              <span>📖</span> 模型说明
            </button>
          </div>
        </div>

        <!-- 事件日志组（透明化展示） -->
        <div class="footer-group" v-if="eventLogs.length > 0">
          <div class="group-header" @click="toggleGroup('eventLog')">
            <span>📜 事件日志</span>
            <span class="event-log-count">{{ eventLogs.length }}</span>
            <span :class="['group-toggle', { expanded: expandedGroups.eventLog }]">▼</span>
          </div>
          <div v-if="expandedGroups.eventLog !== false" class="event-log-list">
            <div class="event-log-item" v-for="(log, index) in eventLogs" :key="index">
              <div class="event-log-header">
                <span class="event-log-time">{{ log.timestamp }}</span>
                <span class="event-log-status" :class="log.pending ? 'status-pending' : 'status-injected'">
                  {{ log.pending ? '⏳ 待注入' : '✅ 已注入' }}
                </span>
                <span class="event-log-source" :class="'source-' + log.source">
                  {{ log.source === 'public' ? '📢 公域' : '🏠 私域' }}
                </span>
              </div>
              <div class="event-log-content">{{ log.content.slice(0, 50) }}{{ log.content.length > 50 ? '...' : '' }}</div>
              <div class="event-log-graph" v-if="log.knowledgeGraph">
                <div class="graph-summary-line">
                  <span class="summary-icon">📝</span>
                  {{ log.knowledgeGraph.summary || '无摘要' }}
                </div>
                <div class="graph-entities-line">
                  <span class="entities-icon">🏷️</span>
                  {{ formatEntitiesForLog(log.knowledgeGraph.entities) }}
                </div>
                <div class="graph-stats-line">
                  <span>{{ log.knowledgeGraph.entities?.length || 0 }} 实体</span>
                  <span>·</span>
                  <span>{{ log.knowledgeGraph.relations?.length || 0 }} 关系</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 系统设置组 -->
        <div class="footer-group">
          <div class="group-header" @click="toggleGroup('settings')">
            <span>⚙️ 系统设置</span>
            <span :class="['group-toggle', { expanded: expandedGroups.settings }]">▼</span>
          </div>
          <div v-if="expandedGroups.settings" class="group-buttons">
            <button class="btn-group" @click="showSettingsDrawer = true">
              <span>🔧</span> 高级设置
            </button>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧主内容区（含图表区和说明栏） -->
    <main class="main-content">
      <!-- 图表区域 -->
      <div class="charts-area">
      <!-- 顶部核心指标卡 -->
      <div class="kpi-cards">
        <div class="kpi-card clickable" @click="showInfoPanelWithHighlight('step')">
          <div class="kpi-icon">⏱️</div>
          <div class="kpi-content">
            <span class="kpi-label">当前步数</span>
            <span class="kpi-value">{{ animatedStep }}</span>
          </div>
        </div>
        <!-- Phase 3: 运行模式状态显示 -->
        <div class="kpi-card mode-indicator" :class="simulationMode">
          <div class="kpi-icon">{{ simulationMode === 'news' ? '📰' : '🎮' }}</div>
          <div class="kpi-content">
            <span class="kpi-label">运行模式</span>
            <span class="kpi-value">{{ simulationMode === 'news' ? '新闻推演' : '沙盘推演' }}</span>
          </div>
        </div>
        <div class="kpi-card danger clickable" @click="showInfoPanelWithHighlight('rumor')">
          <div class="kpi-icon">📢</div>
          <div class="kpi-content">
            <span class="kpi-label">误信率</span>
            <span class="kpi-value">{{ (rumorSpreadRate * 100).toFixed(1) }}<small>%</small></span>
          </div>
        </div>
        <div class="kpi-card success clickable" @click="showInfoPanelWithHighlight('truth')">
          <div class="kpi-icon">✓</div>
          <div class="kpi-content">
            <span class="kpi-label">正确认知率</span>
            <span class="kpi-value">{{ (truthAcceptanceRate * 100).toFixed(1) }}<small>%</small></span>
          </div>
        </div>
        <div class="kpi-card info clickable" @click="showInfoPanelWithHighlight('avgOpinion')">
          <div class="kpi-icon">⚖️</div>
          <div class="kpi-content">
            <span class="kpi-label">平均观点</span>
            <span class="kpi-value">{{ avgOpinion.toFixed(3) }}</span>
          </div>
        </div>
        <div class="kpi-card purple clickable" @click="showInfoPanelWithHighlight('silence')">
          <div class="kpi-icon">🤫</div>
          <div class="kpi-content">
            <span class="kpi-label">沉默率</span>
            <span class="kpi-value">{{ (silenceRate * 100).toFixed(1) }}<small>%</small></span>
          </div>
        </div>
        <div class="kpi-card warning clickable" @click="showInfoPanelWithHighlight('polarization')">
          <div class="kpi-icon">⚡</div>
          <div class="kpi-content">
            <span class="kpi-label">极化指数</span>
            <span class="kpi-value">{{ polarizationIndex.toFixed(3) }}</span>
          </div>
        </div>
        <!-- v3.0 新增 KPI -->
        <div class="kpi-card danger clickable" @click="showInfoPanelWithHighlight('rumor_trust')">
          <div class="kpi-icon">📉</div>
          <div class="kpi-content">
            <span class="kpi-label">谣言信任度</span>
            <span class="kpi-value">{{ (avgRumorTrust * 100).toFixed(1) }}<small>%</small></span>
          </div>
        </div>
        <div class="kpi-card success clickable" @click="showInfoPanelWithHighlight('truth_trust')">
          <div class="kpi-icon">📈</div>
          <div class="kpi-content">
            <span class="kpi-label">真相信任度</span>
            <span class="kpi-value">{{ (avgTruthTrust * 100).toFixed(1) }}<small>%</small></span>
          </div>
        </div>
        <div class="kpi-card info clickable" @click="showInfoPanelWithHighlight('total_exposures')">
          <div class="kpi-icon">👁️</div>
          <div class="kpi-content">
            <span class="kpi-label">总曝光量</span>
            <span class="kpi-value">{{ totalExposures }}</span>
          </div>
        </div>
        <div class="kpi-card clickable" :class="truthInterventionActive ? 'success' : 'purple'" @click="showInfoPanelWithHighlight('truth_intervention')">
          <div class="kpi-icon">🛡️</div>
          <div class="kpi-content">
            <span class="kpi-label">辟谣干预</span>
            <span class="kpi-value">{{ truthInterventionActive ? '已启动' : '未启动' }}</span>
          </div>
        </div>
        <div class="kpi-card knowledge clickable" @click="showInfoPanelWithHighlight('knowledge')" v-if="knowledgeGraph.entities && knowledgeGraph.entities.length > 0">
          <div class="kpi-icon">🧠</div>
          <div class="kpi-content">
            <span class="kpi-label">知识驱动</span>
            <span class="kpi-value">{{ knowledgeGraph.entities.length }}<small> 实体</small></span>
          </div>
        </div>
      </div>

      <!-- 预测与风险预警区域 -->
      <!-- 推演中/暂停中：第3步后显示；推演停止后：有预测数据时显示 -->
      <div class="prediction-alerts-area" v-if="((isRunning || isPaused) && currentStep >= 3) || (!isRunning && !isPaused && prediction && prediction.available)">
        <!-- 预测区间展示 -->
        <div class="prediction-panel" v-if="prediction && prediction.available">
          <div class="prediction-header">
            <h4>📊 趋势预测</h4>
            <span class="prediction-step">基于步骤 {{ prediction.current_step }}</span>
          </div>
          <div class="prediction-intervals">
            <div class="prediction-item">
              <div class="prediction-label">误信率</div>
              <div class="prediction-bar">
                <div class="bar-range" :style="{
                  left: (getPredictionField('negative', 'optimistic') * 100) + '%',
                  right: (100 - getPredictionField('negative', 'pessimistic') * 100) + '%'
                }">
                  <div class="bar-expected" :style="{ left: getExpectedPosition('negative', 'optimistic', 'pessimistic') + '%' }"></div>
                </div>
              </div>
              <div class="prediction-values">
                <span class="optimistic">{{ (getPredictionField('negative', 'optimistic') * 100).toFixed(0) }}%</span>
                <span class="expected">{{ (getPredictionField('negative', 'expected') * 100).toFixed(0) }}%</span>
                <span class="pessimistic">{{ (getPredictionField('negative', 'pessimistic') * 100).toFixed(0) }}%</span>
              </div>
            </div>
            <div class="prediction-item">
              <div class="prediction-label">正确认知率</div>
              <div class="prediction-bar truth-bar">
                <div class="bar-range" :style="{
                  left: (getPredictionField('positive', 'pessimistic') * 100) + '%',
                  right: (100 - getPredictionField('positive', 'optimistic') * 100) + '%'
                }">
                  <div class="bar-expected" :style="{ left: getExpectedPosition('positive', 'pessimistic', 'optimistic') + '%' }"></div>
                </div>
              </div>
              <div class="prediction-values">
                <span class="pessimistic">{{ (getPredictionField('positive', 'pessimistic') * 100).toFixed(0) }}%</span>
                <span class="expected">{{ (getPredictionField('positive', 'expected') * 100).toFixed(0) }}%</span>
                <span class="optimistic">{{ (getPredictionField('positive', 'optimistic') * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
          <div class="prediction-recommendation" v-if="prediction.recommendation">
            <span :class="['risk-badge', prediction.recommendation.risk_level]">{{ prediction.recommendation.risk_level.toUpperCase() }}</span>
            <span class="recommendation-msg">{{ prediction.recommendation.message }}</span>
          </div>
          <!-- Phase 3: 增强干预策略展示 -->
          <div class="intervention-strategies" v-if="prediction.recommendation && prediction.recommendation.strategies">
            <div class="strategies-header">干预策略建议</div>
            <div class="strategies-list">
              <div class="strategy-item" v-for="strategy in prediction.recommendation.strategies" :key="strategy.type">
                <div class="strategy-icon">{{ getStrategyIcon(strategy.type) }}</div>
                <div class="strategy-content">
                  <div class="strategy-name">{{ strategy.name }}</div>
                  <div class="strategy-desc">{{ strategy.description }}</div>
                  <div class="strategy-meta">
                    <span class="effectiveness">效果: {{ (strategy.effectiveness * 100).toFixed(0) }}%</span>
                    <span :class="['cost', strategy.cost]">成本: {{ getCostLabel(strategy.cost) }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="intervention-timing" v-if="prediction.recommendation.best_timing">
              <span class="timing-label">最佳干预时机:</span>
              <span class="timing-value">{{ prediction.recommendation.best_timing }} 步内</span>
              <span class="window-status" :class="prediction.recommendation.window_status">
                窗口{{ prediction.recommendation.window_status }}
              </span>
            </div>
          </div>
        </div>

        <!-- 风险预警展示 -->
        <div class="alerts-panel" v-if="riskAlerts && riskAlerts.alerts && riskAlerts.alerts.length > 0">
          <div class="alerts-header">
            <h4>⚠️ 风险预警</h4>
            <span class="alerts-count">{{ riskAlerts.alerts.length }}</span>
          </div>
          <div class="alerts-list">
            <div v-for="(alert, idx) in riskAlerts.alerts.slice(0, 3)" :key="idx" :class="['alert-item', alert.level]">
              <span class="alert-icon">{{ alert.level === 'critical' ? '🚨' : alert.level === 'high' ? '⚠️' : '📢' }}</span>
              <div class="alert-content">
                <div class="alert-message">{{ alert.message }}</div>
                <div class="alert-suggestion">{{ alert.suggestion }}</div>
              </div>
            </div>
          </div>
          <div class="risk-summary" v-if="riskAlerts.risk_summary">
            <span class="risk-score">综合风险: {{ (riskAlerts.risk_summary.risk_score * 100).toFixed(0) }}%</span>
            <span :class="['risk-level', riskAlerts.risk_summary.overall_level]">{{ riskAlerts.risk_summary.overall_level.toUpperCase() }}</span>
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
              <span v-if="newsCredibility !== '不确定'" class="credibility-badge" :class="newsCredibility === '高可信' ? 'high' : 'low'">
                {{ newsCredibility === '高可信' ? '✅ 高可信新闻' : '⚠️ 低可信新闻' }}
              </span>
              <button class="chart-zoom-btn" @click="openChartModal('opinion')" title="放大">🔍</button>
              <div class="chart-legend">
                <span class="legend-item rumor">{{ misleadLegendLabel }}</span>
                <span class="legend-item neutral">中立</span>
                <span class="legend-item truth">{{ correctLegendLabel }}</span>
              </div>
            </div>
            <div class="chart-body" ref="opinionChart"></div>
          </div>
          <div class="chart-card network-chart">
            <div class="chart-header">
              <h3>信息传播网络</h3>
              <button class="chart-zoom-btn" @click="openChartModal('network')" title="放大">🔍</button>
              <div class="network-tabs" v-if="useDualNetwork">
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
              <span v-if="useDualNetwork && activeNetworkTab === 'public'">大V数量: {{ numInfluencers }} | 节点大小表示影响力</span>
              <span v-else-if="useDualNetwork">社群数量: {{ numCommunities }} | 不同颜色代表不同社群</span>
              <span v-else>单层网络 | 节点大小表示影响力</span>
            </div>
          </div>
        </div>

        <!-- 下排：趋势图 -->
        <div class="chart-row bottom-row">
          <div class="chart-card trend-chart">
            <div class="chart-header">
              <h3>舆论演化趋势</h3>
              <button class="chart-zoom-btn" @click="openChartModal('trend')" title="放大">🔍</button>
              <span v-if="debunked" class="debunk-badge">权威回应已发布</span>
            </div>
            <div class="chart-body" ref="trendChart"></div>
          </div>
          <!-- v3.0 新增图表面板（紧凑布局） -->
          <div class="chart-card v3-panel" v-if="Object.keys(needDistribution).length > 0 || Object.keys(behaviorDistribution).length > 0">
            <div class="chart-header clickable" @click="showV3Charts = !showV3Charts">
              <h3>🧠 心理分析</h3>
              <span class="toggle-icon">{{ showV3Charts ? '▼' : '▶' }}</span>
            </div>
            <div class="v3-charts-body" v-show="showV3Charts">
              <div class="v3-chart-item" ref="needDistChart" v-if="Object.keys(needDistribution).length > 0"></div>
              <div class="v3-chart-item" ref="behaviorDistChart" v-if="Object.keys(behaviorDistribution).length > 0"></div>
            </div>
          </div>
        </div>
      </div>
      <!-- 图表区域结束 -->
      </div>

      <!-- 右侧说明栏（可折叠） -->
      <aside class="info-panel" :class="{ collapsed: !showInfoPanel }">
        <div class="info-panel-toggle" @click="showInfoPanel = !showInfoPanel">
          <span v-if="showInfoPanel">收起 ▶</span>
          <span v-else>◀ 展开</span>
        </div>
        <div v-if="showInfoPanel" class="info-panel-content">
          <!-- 当前关注区域 -->
          <div class="info-section">
            <h4 class="info-section-title">📊 指标解读</h4>
            <div class="info-item" :class="{ highlighted: highlightedInfoItem === 'rumor' }">
              <div class="info-item-header">
                <span class="info-item-label">误信率</span>
                <span class="info-item-value danger">{{ (rumorSpreadRate * 100).toFixed(1) }}%</span>
              </div>
              <p class="info-item-desc">当前误信的人群比例（opinion &lt; 0）。权威回应后应逐渐下降。</p>
            </div>
            <div class="info-item" :class="{ highlighted: highlightedInfoItem === 'truth' }">
              <div class="info-item-header">
                <span class="info-item-label">正确认知率</span>
                <span class="info-item-value success">{{ (truthAcceptanceRate * 100).toFixed(1) }}%</span>
              </div>
              <p class="info-item-desc">当前持正确认知的人群比例（opinion &gt; 0）。权威回应后应逐渐上升。</p>
            </div>
            <div class="info-item" :class="{ highlighted: highlightedInfoItem === 'avgOpinion' }">
              <div class="info-item-header">
                <span class="info-item-label">平均观点</span>
                <span class="info-item-value info">{{ avgOpinion.toFixed(3) }}</span>
              </div>
              <p class="info-item-desc">群体观点平均值。负值=倾向负面信念，正值=倾向正确认知。范围：-1 ~ +1</p>
            </div>
            <div class="info-item" :class="{ highlighted: highlightedInfoItem === 'silence' }">
              <div class="info-item-header">
                <span class="info-item-label">沉默率</span>
                <span class="info-item-value purple">{{ (silenceRate * 100).toFixed(1) }}%</span>
              </div>
              <p class="info-item-desc">不敢表达观点的人群比例。反映"沉默的螺旋"效应，高值可能导致极端观点主导。</p>
            </div>
            <div class="info-item" :class="{ highlighted: highlightedInfoItem === 'polarization' }">
              <div class="info-item-header">
                <span class="info-item-label">极化指数</span>
                <span class="info-item-value warning">{{ polarizationIndex.toFixed(3) }}</span>
              </div>
              <p class="info-item-desc">群体观点分歧程度（0~1）。高值表示社会撕裂，双方互不信任。</p>
            </div>
            <!-- v3.0 新增指标解读 -->
            <div class="info-item" :class="{ highlighted: highlightedInfoItem === 'rumor_trust' }">
              <div class="info-item-header">
                <span class="info-item-label">谣言信任度</span>
                <span class="info-item-value danger">{{ (avgRumorTrust * 100).toFixed(1) }}%</span>
              </div>
              <p class="info-item-desc">群体对负面信息的平均信任程度。与"误信率"不同，反映信念强度而非立场比例。</p>
            </div>
            <div class="info-item" :class="{ highlighted: highlightedInfoItem === 'truth_trust' }">
              <div class="info-item-header">
                <span class="info-item-label">真相信任度</span>
                <span class="info-item-value success">{{ (avgTruthTrust * 100).toFixed(1) }}%</span>
              </div>
              <p class="info-item-desc">群体对正面信息的平均信任程度。权威回应后应逐渐上升。</p>
            </div>
            <div class="info-item" :class="{ highlighted: highlightedInfoItem === 'total_exposures' }">
              <div class="info-item-header">
                <span class="info-item-label">总曝光量</span>
                <span class="info-item-value info">{{ totalExposures }}</span>
              </div>
              <p class="info-item-desc">累计信息曝光次数。反映信息传播广度，高值表示信息触达更多人群。</p>
            </div>
            <div class="info-item" :class="{ highlighted: highlightedInfoItem === 'truth_intervention' }">
              <div class="info-item-header">
                <span class="info-item-label">辟谣干预</span>
                <span class="info-item-value" :class="truthInterventionActive ? 'success' : 'purple'">{{ truthInterventionActive ? '已启动' : '未启动' }}</span>
              </div>
              <p class="info-item-desc">权威辟谣信息发布状态。启动后 TruthEnv 将推送正面信息，影响群体信念。</p>
            </div>
          </div>

          <!-- v3.0 心理学模型说明 -->
          <div class="info-section" v-if="Object.keys(needDistribution).length > 0 || Object.keys(behaviorDistribution).length > 0">
            <h4 class="info-section-title">🧠 心理学模型 (v3.0)</h4>
            <div class="mechanism-list">
              <div class="mechanism-item">
                <span class="mechanism-icon">马斯洛</span>
                <div class="mechanism-content">
                  <strong>需求层次理论</strong>
                  <p>五层需求（生理→安全→社交→尊重→认知）决定信息接受度。主导需求=最低满足度层次。</p>
                </div>
              </div>
              <div class="mechanism-item">
                <span class="mechanism-icon">TPB</span>
                <div class="mechanism-content">
                  <strong>计划行为理论</strong>
                  <p>行为意向 = 态度×w1 + 主观规范×w2 + 知觉行为控制×w3。预测分享/评论/沉默/核查/拒绝等行为。</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 推演机制 -->
          <div class="info-section">
            <h4 class="info-section-title">🔬 推演机制</h4>
            <div class="mechanism-list">
              <div class="mechanism-item">
                <span class="mechanism-icon">👥</span>
                <div class="mechanism-content">
                  <strong>社交传播影响</strong>
                  <p>Agent受邻居观点影响，权重由邻居影响力决定</p>
                </div>
              </div>
              <div class="mechanism-item">
                <span class="mechanism-icon">📱</span>
                <div class="mechanism-content">
                  <strong>算法茧房效应</strong>
                  <p>推荐算法强化既有观点，形成回音室</p>
                </div>
              </div>
              <div class="mechanism-item">
                <span class="mechanism-icon">🤫</span>
                <div class="mechanism-content">
                  <strong>沉默的螺旋</strong>
                  <p>少数派因恐惧孤立而选择沉默</p>
                </div>
              </div>
              <div class="mechanism-item">
                <span class="mechanism-icon">⚡</span>
                <div class="mechanism-content">
                  <strong>群体极化</strong>
                  <p>群体讨论导致观点向极端方向移动</p>
                </div>
              </div>
              <div class="mechanism-item">
                <span class="mechanism-icon">🔥</span>
                <div class="mechanism-content">
                  <strong>逆火效应</strong>
                  <p>权威回应可能与强信念冲突，反而强化误信</p>
                </div>
              </div>
              <div class="mechanism-item">
                <span class="mechanism-icon">🧠</span>
                <div class="mechanism-content">
                  <strong>认知失调</strong>
                  <p>面对矛盾信息时可能强化原有信念</p>
                </div>
              </div>
              <div class="mechanism-item knowledge-mechanism" v-if="knowledgeGraph.entities && knowledgeGraph.entities.length > 0">
                <span class="mechanism-icon">🔗</span>
                <div class="mechanism-content">
                  <strong>知识驱动演化</strong>
                  <p>实体影响力参与观点演化，权威实体影响更大</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 知识图谱实体影响力 -->
          <div class="info-section" v-if="knowledgeGraph.entities && knowledgeGraph.entities.length > 0" :class="{ highlighted: highlightedInfoItem === 'knowledge' }">
            <h4 class="info-section-title">🧠 知识驱动演化</h4>
            <div class="info-item">
              <div class="info-item-header">
                <span class="info-item-label">实体数量</span>
                <span class="info-item-value knowledge">{{ knowledgeGraph.entities.length }}</span>
              </div>
              <p class="info-item-desc">知识图谱中的实体数量，实体影响力参与观点演化计算。</p>
            </div>
            <div class="info-item">
              <div class="info-item-header">
                <span class="info-item-label">关系数量</span>
                <span class="info-item-value knowledge">{{ knowledgeGraph.relations ? knowledgeGraph.relations.length : 0 }}</span>
              </div>
              <p class="info-item-desc">实体间的关系数量，支持立场传导计算。</p>
            </div>
            <!-- 高影响力实体展示 -->
            <div class="entity-impact-list" v-if="topEntities.length > 0">
              <div class="entity-impact-title">高影响力实体</div>
              <div class="entity-impact-items">
                <div v-for="entity in topEntities" :key="entity.name" class="entity-impact-item">
                  <span class="entity-name">{{ entity.name }}</span>
                  <span class="entity-type">{{ entity.type }}</span>
                  <div class="entity-impact-bar">
                    <div class="entity-impact-fill" :style="{ width: (entity.impact * 100) + '%' }"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 图表阅读指南 -->
          <div class="info-section">
            <h4 class="info-section-title">📖 图表阅读指南</h4>
            <div class="guide-item">
              <strong>观点分布图</strong>
              <ul>
                <li>红色柱子 = 误信人群</li>
                <li>橙色柱子 = 中立人群</li>
                <li>绿色柱子 = 正确认知人群</li>
                <li>观察分布如何随推演变化</li>
              </ul>
            </div>
            <div class="guide-item">
              <strong>网络拓扑图</strong>
              <ul>
                <li>节点颜色 = Agent观点（红=负面信念立场）</li>
                <li>节点大小 = 影响力（大=意见领袖）</li>
                <li>连线 = 信息传播路径</li>
                <li>点击节点查看Agent决策详情</li>
              </ul>
            </div>
            <div class="guide-item">
              <strong>趋势曲线图</strong>
              <ul>
                <li>观察误信率和正确认知率的此消彼长</li>
                <li>权威回应发布点会有标记</li>
                <li>极化指数上升=群体观点分化</li>
              </ul>
            </div>
          </div>

          <!-- 操作提示 -->
          <div class="info-section tips-section">
            <h4 class="info-section-title">💡 操作提示</h4>
            <div class="tip-item" v-if="currentStep === 0 && !isRunning">
              <span class="tip-icon">1️⃣</span>
              <span>调整左侧参数，然后点击"开始推演"</span>
            </div>
            <div class="tip-item" v-else-if="isRunning">
              <span class="tip-icon">2️⃣</span>
              <span>观察图表实时变化，可点击网络节点查看Agent决策</span>
            </div>
            <div class="tip-item" v-else-if="currentStep > 0 && !isRunning">
              <span class="tip-icon">3️⃣</span>
              <span>可注入事件或生成报告分析推演结果</span>
            </div>
          </div>
        </div>
      </aside>
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

    <!-- 使用说明抽屉 -->
    <div v-if="showUsageDrawer" class="drawer-overlay" @click.self="showUsageDrawer = false">
      <div class="usage-drawer">
        <div class="drawer-header">
          <h3>📋 使用说明</h3>
          <button class="drawer-close" @click="showUsageDrawer = false">✕</button>
        </div>
        <div class="drawer-body">
          <div v-if="usageLoading" class="loading-container">
            <div class="loading-spinner"></div>
            <p>加载使用说明...</p>
          </div>
          <div v-else class="usage-content" v-html="usageContent"></div>
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
                <!-- v3.0 新增字段 -->
                <div class="info-item" v-if="agentSnapshot.rumor_trust !== undefined">
                  <span class="label">谣言信任度</span>
                  <span :class="['value', agentSnapshot.rumor_trust > 0.5 ? 'warning' : '']">{{ (agentSnapshot.rumor_trust * 100).toFixed(1) }}%</span>
                </div>
                <div class="info-item" v-if="agentSnapshot.truth_trust !== undefined">
                  <span class="label">真相信任度</span>
                  <span :class="['value', agentSnapshot.truth_trust > 0.5 ? 'success' : '']">{{ (agentSnapshot.truth_trust * 100).toFixed(1) }}%</span>
                </div>
                <div class="info-item" v-if="agentSnapshot.dominant_need">
                  <span class="label">主导需求</span>
                  <span class="value highlight">{{ needLabel(agentSnapshot.dominant_need) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- v3.0 新增：行为预测区块 -->
          <div v-if="agentSnapshot.predicted_behavior" class="info-block behavior-block">
            <div class="block-title"><span class="block-icon">🎯</span> 行为预测 (TPB)</div>
            <div class="block-content">
              <div class="info-grid">
                <div class="info-item">
                  <span class="label">预测行为</span>
                  <span :class="['value', 'status-badge', behaviorClass(agentSnapshot.predicted_behavior)]">{{ behaviorLabel(agentSnapshot.predicted_behavior) }}</span>
                </div>
                <div class="info-item" v-if="agentSnapshot.behavior_confidence !== undefined">
                  <span class="label">行为意向强度</span>
                  <span class="value">{{ (agentSnapshot.behavior_confidence * 100).toFixed(0) }}%</span>
                </div>
                <div class="info-item" v-if="agentSnapshot.cognitive_closed_need">
                  <span class="label">认知闭合需求</span>
                  <span class="value">{{ (agentSnapshot.cognitive_closed_need * 100).toFixed(0) }}%</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 区块B: 心理博弈过程 (沉默的螺旋) -->
          <div v-if="normalizedClimate" class="info-block psychology-block">
            <div class="block-title"><span class="block-icon">🌀</span> 心理博弈过程</div>
            <div class="block-content">
              <div class="psychology-analysis">
                <div class="climate-info">
                  <div class="climate-item">
                    <span class="label">邻居数量</span>
                    <span class="value">{{ normalizedClimate.total }}</span>
                  </div>
                  <div class="climate-item">
                    <span class="label">误信比例</span>
                    <span class="value rumor">{{ (normalizedClimate.pro_rumor_ratio * 100).toFixed(0) }}%</span>
                  </div>
                  <div class="climate-item">
                    <span class="label">正确认知比例</span>
                    <span class="value truth">{{ (normalizedClimate.pro_truth_ratio * 100).toFixed(0) }}%</span>
                  </div>
                  <div class="climate-item">
                    <span class="label">沉默比例</span>
                    <span class="value silent">{{ (normalizedClimate.silent_ratio * 100).toFixed(0) }}%</span>
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
                    <p v-if="normalizedClimate.pro_rumor_ratio > normalizedClimate.pro_truth_ratio && agentSnapshot.new_opinion > 0">
                      "虽然周围误信的人更多，但我有足够的勇气和信念表达我的观点。"
                    </p>
                    <p v-else-if="normalizedClimate.pro_truth_ratio > normalizedClimate.pro_rumor_ratio && agentSnapshot.new_opinion < 0">
                      "虽然周围持正确认知的人更多，但我坚持自己的判断，不会轻易改变。"
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

    <!-- 图表放大弹窗 -->
    <div v-if="chartModalOpen" class="chart-modal-overlay" @click.self="closeChartModal">
      <div class="chart-modal">
        <div class="chart-modal-header">
          <h3>{{ chartModalTitle }}</h3>
          <button class="chart-modal-close" @click="closeChartModal">✕</button>
        </div>
        <div class="chart-modal-body" ref="chartModalBody"></div>
      </div>
    </div>

    <!-- 推演完成引导弹窗 -->
    <div v-if="showCompletionModal" class="completion-modal-overlay" @click.self="showCompletionModal = false">
      <div class="completion-modal">
        <div class="completion-icon">🎉</div>
        <h3 class="completion-title">推演完成</h3>
        <p class="completion-desc">已完成 {{ maxSteps }} 步推演，可以生成分析报告查看完整结果</p>
        <div class="completion-stats" v-if="prediction && prediction.recommendation">
          <div class="completion-stat-item">
            <span class="stat-label">风险等级</span>
            <span :class="['stat-value', 'risk-' + prediction.recommendation.risk_level]">{{ prediction.recommendation.risk_level.toUpperCase() }}</span>
          </div>
          <div class="completion-stat-item">
            <span class="stat-label">误信率</span>
            <span class="stat-value">{{ (rumorSpreadRate * 100).toFixed(1) }}%</span>
          </div>
          <div class="completion-stat-item">
            <span class="stat-label">正确认知率</span>
            <span class="stat-value truth">{{ (truthAcceptanceRate * 100).toFixed(1) }}%</span>
          </div>
        </div>
        <div class="completion-actions">
          <button class="btn-completion btn-report" @click="showCompletionModal = false; generateReport()">
            <span>📄</span> 生成推演报告
          </button>
          <button v-if="useLLM" class="btn-completion btn-intelligence" @click="showCompletionModal = false; generateIntelligenceReport()" :disabled="reportGenerating">
            <span>🧠</span> {{ reportGenerating ? '撰写中...' : '生成智库专报' }}
          </button>
          <button class="btn-completion btn-later" @click="showCompletionModal = false">
            稍后查看
          </button>
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
      <div class="report-modal report-modal-enhanced">
        <div class="report-modal-header">
          <h3>📚 历史报告</h3>
          <button class="report-close-btn" @click="showReportList = false">✕</button>
        </div>
        <div class="report-modal-body">
          <div v-if="reportListLoading" class="report-loading">
            <div class="loading-spinner"></div>
            <p>加载报告列表...</p>
          </div>
          <template v-else>
            <!-- 搜索和排序工具栏 -->
            <div class="report-toolbar">
              <div class="report-search-box">
                <input
                  type="text"
                  v-model="reportSearchKeyword"
                  @input="onReportSearchInput"
                  placeholder="搜索报告..."
                  class="report-search-input"
                />
                <span class="report-search-icon">🔍</span>
              </div>
              <div class="report-sort-btns">
                <button
                  :class="['sort-btn', { active: reportSortBy === 'modified' }]"
                  @click="changeReportSort('modified')"
                  title="按时间排序">
                  🕐 {{ reportSortBy === 'modified' ? (reportSortOrder === 'desc' ? '↓' : '↑') : '' }}
                </button>
                <button
                  :class="['sort-btn', { active: reportSortBy === 'size' }]"
                  @click="changeReportSort('size')"
                  title="按大小排序">
                  📊 {{ reportSortBy === 'size' ? (reportSortOrder === 'desc' ? '↓' : '↑') : '' }}
                </button>
                <button
                  :class="['sort-btn', { active: reportSortBy === 'name' }]"
                  @click="changeReportSort('name')"
                  title="按名称排序">
                  🔤 {{ reportSortBy === 'name' ? (reportSortOrder === 'desc' ? '↓' : '↑') : '' }}
                </button>
              </div>
            </div>

            <!-- 报告统计 -->
            <div class="report-stats">
              共 <strong>{{ reportCounts.total }}</strong> 份报告
              （推演 <strong>{{ reportCounts.simulation }}</strong> 份，
              智库专报 <strong>{{ reportCounts.intelligence }}</strong> 份）
            </div>

            <!-- 双栏布局 -->
            <div class="report-columns">
              <!-- 左栏：推演报告 -->
              <div class="report-column">
                <div class="column-header">
                  <span class="column-icon">📄</span>
                  <span class="column-title">推演报告</span>
                  <span class="column-count">{{ simulationReports.length }}</span>
                </div>
                <div class="column-body">
                  <div v-if="simulationReports.length > 0" class="report-list">
                    <div
                      v-for="report in simulationReports"
                      :key="report.filename"
                      class="report-item"
                      @click="viewHistoryReport(report)">
                      <div class="report-item-icon">📄</div>
                      <div class="report-item-info">
                        <div class="report-item-name">{{ report.filename }}</div>
                        <div class="report-item-meta">{{ formatFileSize(report.size) }} · {{ formatDate(report.modified) }}</div>
                      </div>
                      <div class="report-item-action">查看</div>
                    </div>
                  </div>
                  <div v-else class="report-placeholder">
                    <p>暂无推演报告</p>
                  </div>
                </div>
              </div>

              <!-- 右栏：智库专报 -->
              <div class="report-column">
                <div class="column-header">
                  <span class="column-icon">🧠</span>
                  <span class="column-title">智库专报</span>
                  <span class="column-count">{{ intelligenceReports.length }}</span>
                </div>
                <div class="column-body">
                  <div v-if="intelligenceReports.length > 0" class="report-list">
                    <div
                      v-for="report in intelligenceReports"
                      :key="report.filename"
                      class="report-item report-item-intelligence"
                      @click="viewHistoryReport(report)">
                      <div class="report-item-icon">🧠</div>
                      <div class="report-item-info">
                        <div class="report-item-name">{{ report.filename }}</div>
                        <div class="report-item-meta">{{ formatFileSize(report.size) }} · {{ formatDate(report.modified) }}</div>
                      </div>
                      <div class="report-item-action">查看</div>
                    </div>
                  </div>
                  <div v-else class="report-placeholder">
                    <p>暂无智库专报</p>
                  </div>
                </div>
              </div>
            </div>
          </template>
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

    <!-- 知识图谱弹窗 -->
    <div v-if="showKnowledgeGraph" class="kg-modal-overlay" @click.self="showKnowledgeGraph = false">
      <div class="kg-modal kg-modal-graph">
        <div class="kg-modal-header">
          <h3>🕸️ 知识图谱解析</h3>
          <button class="report-close-btn" @click="showKnowledgeGraph = false">✕</button>
        </div>
        <div class="kg-modal-body">
          <div v-if="knowledgeGraphLoading" class="kg-loading">
            <div class="loading-spinner"></div>
            <p>正在解析新闻结构...</p>
          </div>
          <div v-else class="kg-content">
            <!-- 动态图谱可视化区域 -->
            <div class="kg-graph-container" v-if="knowledgeGraph.entities && knowledgeGraph.entities.length">
              <div class="kg-graph-header">
                <span class="kg-stats">📊 {{ knowledgeGraph.entities.length }} 实体 · {{ knowledgeGraph.relations?.length || 0 }} 关系</span>
                <div class="kg-legend">
                  <span class="kg-legend-item"><span class="kg-legend-dot person"></span>人物</span>
                  <span class="kg-legend-item"><span class="kg-legend-dot org"></span>组织</span>
                  <span class="kg-legend-item"><span class="kg-legend-dot location"></span>地点</span>
                  <span class="kg-legend-item"><span class="kg-legend-dot event"></span>事件</span>
                  <span class="kg-legend-item"><span class="kg-legend-dot other"></span>其他</span>
                </div>
              </div>
              <div ref="knowledgeGraphChart" class="kg-graph-chart"></div>
            </div>

            <!-- 事件摘要 -->
            <div v-if="knowledgeGraph.summary" class="kg-section">
              <h4>📝 事件摘要</h4>
              <p class="kg-summary">{{ knowledgeGraph.summary }}</p>
            </div>
            <!-- 实体列表 -->
            <div v-if="knowledgeGraph.entities && knowledgeGraph.entities.length" class="kg-section">
              <h4>🔷 实体 ({{ knowledgeGraph.entities.length }})</h4>
              <div class="kg-entities">
                <span v-for="(entity, idx) in knowledgeGraph.entities" :key="idx" class="kg-entity-tag" :class="'kg-entity-' + (entity.type || 'other').toLowerCase()">
                  {{ entity.name }}
                  <span class="kg-entity-type">{{ entity.type || '其他' }}</span>
                </span>
              </div>
            </div>
            <!-- 关系列表 -->
            <div v-if="knowledgeGraph.relations && knowledgeGraph.relations.length" class="kg-section">
              <h4>🔗 关系 ({{ knowledgeGraph.relations.length }})</h4>
              <div class="kg-relations">
                <div v-for="(rel, idx) in knowledgeGraph.relations" :key="idx" class="kg-relation-item">
                  <span class="kg-relation-source">{{ resolveEntityName(rel.source) }}</span>
                  <span class="kg-relation-action">{{ rel.action }}</span>
                  <span class="kg-relation-target">{{ resolveEntityName(rel.target) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新闻解析弹窗 -->
    <div v-if="showNewsParser" class="kg-modal-overlay" @click.self="showNewsParser = false">
      <div class="kg-modal">
        <div class="kg-modal-header">
          <h3>🕸️ 新闻解析为知识图谱</h3>
          <button class="report-close-btn" @click="showNewsParser = false">✕</button>
        </div>
        <div class="kg-modal-body">
          <!-- 功能说明 -->
          <div class="kg-section kg-info-box">
            <p><strong>功能说明：</strong>输入新闻文本，系统将自动提取实体（人物、组织、地点等）和关系，生成结构化知识图谱。</p>
            <p class="kg-info-hint">💡 解析后的知识图谱可在推演中影响Agent的决策行为</p>
          </div>
          <div class="kg-section">
            <h4>📰 输入新闻内容</h4>
            <textarea 
              v-model="newsContent" 
              class="news-input" 
              placeholder="请输入要解析的新闻内容..."
              rows="5"
            ></textarea>
            <button class="btn-parse-news" @click="parseNews" :disabled="newsParsing || !newsContent.trim()">
              {{ newsParsing ? '解析中...' : '🔍 开始解析' }}
            </button>
          </div>
          <div v-if="newsParseError" class="kg-section">
            <p class="kg-error">{{ newsParseError }}</p>
          </div>
          <div v-if="parsedKnowledgeGraph && parsedKnowledgeGraph.entities && parsedKnowledgeGraph.entities.length" class="kg-section">
            <h4>✅ 解析成功！</h4>
            <button class="btn-view-graph" @click="viewParsedGraph">
              查看知识图谱 →
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 事件注入弹窗 -->
    <div v-if="showEventAirdrop" class="kg-modal-overlay" @click.self="showEventAirdrop = false">
      <div class="kg-modal kg-modal-event">
        <div class="kg-modal-header">
          <h3>📢 注入突发事件</h3>
          <button class="report-close-btn" @click="showEventAirdrop = false">✕</button>
        </div>
        <div class="kg-modal-body">
          <!-- 功能说明：根据注入时机显示不同内容 -->
          <div class="kg-section kg-info-box">
            <!-- 推演未开始：设置初始分布 -->
            <template v-if="currentStep === 0">
              <p><strong>🎯 注入时机：推演开始前</strong></p>
              <p class="impact-desc">事件将产生三层影响：</p>
              <ul class="impact-list">
                <li><b>初始分布：</b>误信率根据情感/可信度调整</li>
                <li><b>事件冲击：</b>推演开始时触发一次观点偏移</li>
                <li><b>知识演化：</b>每步推演中实体持续影响Agent</li>
              </ul>
              <p class="impact-desc" style="margin-top:8px">实体影响力权重：</p>
              <ul class="impact-list">
                <li>媒体(1.0) > 官方(0.95) > 专家(0.85) > 组织(0.7) > 人物(0.5)</li>
              </ul>
              <p class="kg-info-hint">💡 建议推演前注入初始事件，构建完整的知识驱动推演</p>
            </template>

            <!-- 推演进行中：触发观点冲击 -->
            <template v-else>
              <p><strong>🎯 注入时机：第 {{ currentStep }} 步</strong></p>
              <p class="impact-desc">事件将产生两层影响：</p>
              <ul class="impact-list">
                <li><b>即时冲击：</b>全网Agent观点一次性偏移</li>
                <li><b>持续演化：</b>知识图谱每步持续影响推演</li>
              </ul>
              <p class="impact-desc" style="margin-top:8px">冲击强度计算：</p>
              <ul class="impact-list">
                <li><span class="impact-tag negative">负面新闻</span> 向误信方向偏移（基础0.15）</li>
                <li><span class="impact-tag positive">正面新闻</span> 向正确认知方向偏移（基础0.10）</li>
                <li><span class="impact-tag high">高可信</span> 强度 ×1.3 | <span class="impact-tag low">低可信</span> ×0.7</li>
                <li>大V更敏感，影响力高的Agent受影响更大</li>
              </ul>
              <p class="kg-info-hint">⚡ 突发事件可改变推演化走向，观察舆论波动</p>
            </template>
          </div>
          
          <!-- 输入区域 -->
          <div class="kg-section" v-if="!airdropLoading">
            <h4>📰 事件内容</h4>
            <textarea
              v-model="airdropContent"
              class="news-input"
              placeholder="请输入要注入的事件内容，例如：'某科技公司被曝数据泄露，涉及百万用户隐私信息...'"
              rows="5"
            ></textarea>
          </div>
          
          <!-- 传播领域选择 -->
          <div class="kg-section" v-if="!airdropLoading">
            <h4>🌐 传播领域</h4>
            <div class="airdrop-source-options">
              <label class="source-option">
                <input type="radio" v-model="airdropSource" value="public" />
                <span>📢 公域 (微博热搜)</span>
              </label>
              <label class="source-option">
                <input type="radio" v-model="airdropSource" value="private" />
                <span>🏠 私域 (微信群)</span>
              </label>
            </div>
            <div class="airdrop-options-row" style="margin-top: 12px;">
              <label class="source-option" style="font-size: 12px; color: #888;">
                <input type="checkbox" v-model="airdropSkipParse" style="width: 14px; height: 14px;" />
                <span>⚡ 快速注入（跳过图谱解析，秒级响应）</span>
              </label>
            </div>
          </div>

          <!-- 新闻可信度选择 -->
          <div class="kg-section" v-if="!airdropLoading">
            <h4>🔍 新闻可信度</h4>
            <p class="impact-desc" style="margin-bottom:8px">可信度决定"误信/正确认知"的判定方向：</p>
            <div class="airdrop-source-options">
              <label class="source-option">
                <input type="radio" v-model="airdropCredibility" value="低可信" />
                <span class="credibility-tag low">⚠️ 低可信</span>
                <span class="credibility-hint">相信=误信，拒绝=正确认知</span>
              </label>
              <label class="source-option">
                <input type="radio" v-model="airdropCredibility" value="不确定" />
                <span class="credibility-tag uncertain">❓ 不确定</span>
                <span class="credibility-hint">系统自动判定</span>
              </label>
              <label class="source-option">
                <input type="radio" v-model="airdropCredibility" value="高可信" />
                <span class="credibility-tag high">✅ 高可信</span>
                <span class="credibility-hint">相信=正确认知，拒绝=误信</span>
              </label>
            </div>
          </div>
          
          <!-- Loading 状态显示 -->
          <div class="kg-section airdrop-loading-section" v-if="airdropLoading">
            <div class="airdrop-loading-animation">
              <div class="loading-spinner-large"></div>
              <div class="loading-text">{{ airdropLoadingStage }}</div>
            </div>
            <div class="loading-progress">
              <div class="progress-bar-loading"></div>
            </div>
            <p class="loading-hint">{{ airdropLoadingHint }}</p>
          </div>
          
          <!-- 解析成功后的图谱展示 -->
          <div class="kg-section parsed-graph-display" v-if="parsedGraphDisplay && !airdropLoading">
            <h4>📊 解析结果预览</h4>
            <div class="graph-preview">
              <div class="graph-summary">
                <span class="summary-label">事件摘要:</span>
                <span class="summary-text">{{ parsedGraphDisplay.summary }}</span>
              </div>
              <div class="graph-stats">
                <span class="stat-item">
                  <span class="stat-icon">🏷️</span>
                  <span class="stat-value">{{ parsedGraphDisplay.entities?.length || 0 }} 个实体</span>
                </span>
                <span class="stat-item">
                  <span class="stat-icon">🔗</span>
                  <span class="stat-value">{{ parsedGraphDisplay.relations?.length || 0 }} 个关系</span>
                </span>
                <span class="stat-item" v-if="parsedGraphDisplay.sentiment">
                  <span class="stat-icon">💭</span>
                  <span class="stat-value">{{ parsedGraphDisplay.sentiment }}</span>
                </span>
              </div>
              <div class="graph-entities-preview" v-if="parsedGraphDisplay.entities?.length">
                <div class="entity-tag" v-for="entity in parsedGraphDisplay.entities.slice(0, 5)" :key="entity.id">
                  <span class="entity-type">[{{ entity.type }}]</span>
                  <span class="entity-name">{{ entity.name }}</span>
                </div>
                <span class="entity-more" v-if="parsedGraphDisplay.entities.length > 5">
                  +{{ parsedGraphDisplay.entities.length - 5 }} 更多
                </span>
              </div>
            </div>
          </div>
          
          <!-- 错误显示 -->
          <div v-if="airdropError" class="kg-section">
            <p class="kg-error">❌ {{ airdropError }}</p>
          </div>
          
          <!-- 操作按钮 -->
          <div class="kg-section" v-if="!airdropLoading">
            <button class="btn-parse-news" @click="injectEvent" :disabled="!airdropContent.trim()">
              🚀 立即空投事件
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const API_BASE = window.location.origin
const WS_BASE = `ws${window.location.protocol === 'https:' ? 's' : ''}://${window.location.host}`

export default {
  name: 'App',

  data() {
    return {
      // 连接状态
      isConnected: false,
      ws: null,
      wsReconnectCount: 0,
      wsMaxReconnectAttempts: 5,

      // UI状态
      showHelp: true,  // 帮助说明默认展开
      showInfoPanel: false,  // 右侧说明栏默认收起
      highlightedInfoItem: null,  // 当前高亮的信息项
      expandedGroups: {
        kg: true,      // 知识图谱组默认展开
        report: false,
        settings: false,
        eventLog: true  // 事件日志默认展开
      },

      // 基础参数
      cocoonStrength: 0.5,
      debunkDelay: 10,
      initialRumorSpread: 0.3,
      useLLM: true,

      // Phase 3: 运行模式参数
      simulationMode: 'sandbox',  // sandbox / news
      initDistRumor: 0.25,         // 新闻模式：初始误信比例
      initDistTruth: 0.15,         // 新闻模式：初始正确认知比例

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
      isPaused: false,
      currentStep: 0,
      debunked: false,
      agentProgress: '',

      // 进度条详细数据
      progressData: {
        step: 0,           // 当前Agent序号
        total: 0,          // Agent总数
        percentage: 0,     // 百分比
        agentId: null,     // 当前Agent ID
        agentOpinion: 0,   // Agent观点
        agentStance: '',   // Agent立场
        currentStep: 0,    // 当前推演步数
        maxSteps: 50       // 最大步数
      },

      // 统计数据
      rumorSpreadRate: 0,
      truthAcceptanceRate: 0,
      believeRate: 0,          // 相信新闻比例
      rejectRate: 0,           // 拒绝新闻比例
      newsCredibility: '不确定', // 新闻可信度
      avgOpinion: 0,
      polarizationIndex: 0,
      silenceRate: 0,  // 沉默率

      // v3.0 新增统计
      avgRumorTrust: 0,
      avgTruthTrust: 0,
      needDistribution: {},
      behaviorDistribution: {},
      totalExposures: 0,
      truthInterventionActive: false,
      showV3Charts: true,  // v3 图表默认展开

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
        publicRumorRates: [],   // 公域误信率历史
        privateRumorRates: []   // 私域误信率历史
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

      // 预测与风险预警 (Phase 2)
      prediction: null,
      riskAlerts: null,

      // 图表实例
      opinionChartInstance: null,
      networkChartInstance: null,
      trendChartInstance: null,
      needDistChartInstance: null,
      behaviorDistChartInstance: null,

      // 图表放大模态框
      chartModalOpen: false,
      chartModalType: 'opinion',  // 'opinion' | 'network' | 'trend'
      chartModalTitle: '',
      chartModalInstance: null,

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
      reportTypeFilter: 'all',  // all / simulation / intelligence
      reportSearchKeyword: '',
      reportSortBy: 'modified',  // modified / size / name
      reportSortOrder: 'desc',   // desc / asc
      reportCounts: { total: 0, simulation: 0, intelligence: 0 },
      simulationReports: [],
      intelligenceReports: [],

      // 知识图谱解析
      showKnowledgeGraph: false,
      knowledgeGraph: { entities: [], relations: [], summary: '' },
      knowledgeGraphLoading: false,
      entityImpactSummary: null,  // Phase 3: 实体影响摘要

      // 新闻解析
      showNewsParser: false,
      newsContent: '',
      newsParsing: false,
      newsParseError: '',
      parsedKnowledgeGraph: null,
      
      // 事件注入
      showEventAirdrop: false,
      airdropContent: '',
      airdropSource: 'public',
      airdropCredibility: '不确定',  // 新闻可信度选择
      airdropSkipParse: false,  // 快速注入模式（跳过图谱解析）
      airdropLoading: false,
      airdropLoadingStage: '',  // Loading阶段提示
      airdropError: '',
      airdropSuccess: false,    // 是否成功
      parsedGraphDisplay: null, // 解析后的图谱数据（用于展示）
      
      // 事件日志（透明化展示）
      eventLogs: [],  // 存储所有注入事件的日志
      hasStopped: false,  // 是否已停止推演（用于显示"重新推演"按钮）

      // 智库专报
      showIntelligenceModal: false,
      reportGenerating: false,
      intelligenceContent: '',
      intelligenceFilename: '',

      // 推演完成弹窗
      showCompletionModal: false,

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
      mathModelExplanation: null,

      // 使用说明抽屉
      showUsageDrawer: false,
      usageContent: '',
      usageLoading: false
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
      if (opinion > 0) return 'positive'
      if (opinion < 0) return 'negative'
      return 'neutral'
    },
    agentOpinionLabel() {
      if (!this.agentSnapshot) return ''
      const opinion = this.agentSnapshot.new_opinion
      if (opinion > 0) return '正确认知'
      if (opinion < 0) return '误信'
      return '不确定'
    },
    needLabel() {
      const labels = {
        '生理': '🏠 生理需求',
        '安全': '🛡️ 安全需求',
        '社交': '❤️ 社交需求',
        '尊重': '⭐ 尊重需求',
        '认知': '📚 认知需求',
        physiological: '🏠 生理需求',
        safety: '🛡️ 安全需求',
        love: '❤️ 社交需求',
        esteem: '⭐ 尊重需求',
        cognitive: '📚 认知需求'
      }
      return (need) => labels[need] || need
    },
    behaviorLabel() {
      const labels = {
        '分享': '📢 分享传播',
        '评论': '💬 评论讨论',
        '观望': '👁️ 旁观',
        '沉默': '🤫 沉默',
        '核查': '🔍 核查验证',
        '拒绝': '✋ 拒绝',
        SHARE: '📢 分享传播',
        COMMENT: '💬 评论讨论',
        OBSERVE: '👁️ 旁观',
        SILENCE: '🤫 沉默',
        VERIFY: '🔍 核查验证',
        REJECT: '✋ 拒绝'
      }
      return (b) => labels[b] || b
    },
    behaviorClass() {
      const classes = {
        '分享': 'negative',
        '评论': 'negative',
        '观望': 'neutral',
        '沉默': 'silent',
        '核查': 'positive',
        '拒绝': 'positive',
        SHARE: 'negative',
        COMMENT: 'negative',
        OBSERVE: 'neutral',
        SILENCE: 'silent',
        VERIFY: 'positive',
        REJECT: 'positive'
      }
      return (b) => classes[b] || 'neutral'
    },
    renderedIntelligence() {
      if (!this.intelligenceContent) return ''
      return DOMPurify.sanitize(marked(this.intelligenceContent))
    },
    // 待注入事件（推演未开始时注入的事件）
    pendingEvents() {
      return this.eventLogs.filter(log => log.pending)
    },
    // 兼容单层和双层网络的 perceived_climate
    normalizedClimate() {
      if (!this.agentSnapshot || !this.agentSnapshot.perceived_climate) return null

      const pc = this.agentSnapshot.perceived_climate

      // 单层网络格式：直接有 total/pro_rumor_ratio 等字段
      if (pc.total !== undefined) {
        return pc
      }

      // 双层网络格式：{public: {...}, private: {...}}
      // 合并两个网络的统计数据
      if (pc.public && pc.private) {
        const total = (pc.public.total || 0) + (pc.private.total || 0)
        if (total === 0) return { total: 0, pro_rumor_ratio: 0, pro_truth_ratio: 0, silent_ratio: 0 }

        const rumorCount = (pc.public.pro_rumor_count || 0) + (pc.private.pro_rumor_count || 0)
        const truthCount = (pc.public.pro_truth_count || 0) + (pc.private.pro_truth_count || 0)
        const silentCount = (pc.public.silent_count || 0) + (pc.private.silent_count || 0)

        return {
          total: total,
          pro_rumor_ratio: total > 0 ? rumorCount / total : 0,
          pro_truth_ratio: total > 0 ? truthCount / total : 0,
          silent_ratio: total > 0 ? silentCount / total : 0
        }
      }

      return null
    },
    // 事件注入加载提示（根据阶段动态调整）
    airdropLoadingHint() {
      const stage = this.airdropLoadingStage || ''
      // 推演进行中的提示
      if (this.isRunning) {
        if (this.airdropSkipParse) {
          return '推演进行中，事件将在当前步骤结束后注入（预计 10-30 秒）...'
        }
        return '⚠️ 推演进行中，大模型资源紧张，解析可能较慢（预计 30-90 秒）...'
      }
      // 快速注入模式
      if (this.airdropSkipParse || stage.includes('快速')) {
        return '快速注入模式，预计 1-3 秒...'
      }
      if (stage.includes('阶段1') || stage.includes('解析')) {
        return '大模型正在解析事件图谱，通常需要 10-30 秒...'
      }
      if (stage.includes('阶段2') || stage.includes('完成')) {
        return '图谱解析完成，正在注入事件...'
      }
      if (stage.includes('阶段3') || stage.includes('处理完成')) {
        return '事件处理完成'
      }
      return '正在处理，请稍候...'
    },
    // 高影响力实体（用于知识驱动演化展示）
    topEntities() {
      // 优先使用后端返回的entity_impact_summary
      if (this.entityImpactSummary && Object.keys(this.entityImpactSummary).length > 0) {
        const entities = Object.entries(this.entityImpactSummary)
          .map(([name, impact]) => {
            // 从knowledgeGraph中找到实体类型
            const entityInfo = this.knowledgeGraph.entities?.find(e => e.name === name) || {}
            return {
              name: name,
              type: entityInfo.type || '未知',
              impact: impact
            }
          })
          .sort((a, b) => b.impact - a.impact)
          .slice(0, 5)
        return entities
      }

      // 回退：前端计算
      if (!this.knowledgeGraph.entities || this.knowledgeGraph.entities.length === 0) {
        return []
      }
      // 计算实体影响力并排序
      const typeWeights = {
        '媒体': 1.0,
        '官方': 0.95,
        '专家': 0.85,
        '组织': 0.7,
        '人物': 0.5,
        'organization': 0.7,
        'person': 0.5
      }
      const entitiesWithImpact = this.knowledgeGraph.entities.map(e => {
        const type = e.type || '人物'
        const importance = e.importance || 3
        const typeWeight = typeWeights[type] || 0.5
        const importanceWeight = (6 - importance) / 5
        const impact = typeWeight * 0.4 + importanceWeight * 0.4 + 0.2
        return {
          name: e.name,
          type: type,
          impact: Math.min(1.0, Math.max(0.0, impact))
        }
      })
      // 按影响力排序，取前5个
      return entitiesWithImpact.sort((a, b) => b.impact - a.impact).slice(0, 5)
    },
    // 图例标签：根据新闻可信度动态调整
    misleadLegendLabel() {
      if (this.newsCredibility === '低可信') return '误信(相信)'
      if (this.newsCredibility === '高可信') return '误信(拒绝)'
      return '拒绝'
    },
    correctLegendLabel() {
      if (this.newsCredibility === '低可信') return '正确认知(拒绝)'
      if (this.newsCredibility === '高可信') return '正确认知(相信)'
      return '相信'
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
    },
    showUsageDrawer(newVal) {
      if (newVal && !this.usageContent) {
        this.fetchUsageContent()
      }
    },
    showKnowledgeGraph(newVal) {
      if (newVal && this.knowledgeGraph.entities && this.knowledgeGraph.entities.length) {
        this.$nextTick(() => {
          this.renderKnowledgeGraphChart()
        })
      }
      if (!newVal) {
        // 清理 chart 实例和 resize 监听
        if (this._kgChartResizeHandler) {
          window.removeEventListener('resize', this._kgChartResizeHandler)
          this._kgChartResizeHandler = null
        }
        if (this._kgChartInstance) {
          this._kgChartInstance.dispose()
          this._kgChartInstance = null
        }
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
    this.needDistChartInstance?.dispose()
    this.behaviorDistChartInstance?.dispose()
  },

  methods: {
    // ==================== UI 辅助方法 ====================

    toggleGroup(group) {
      this.expandedGroups[group] = !this.expandedGroups[group]
    },

    // 预测字段名兼容：新名优先，旧名兜底
    getPredictionField(category, field) {
      if (!this.prediction || !this.prediction.prediction) return 0
      const p = this.prediction.prediction
      const nameMap = {
        negative: ['negative_belief_rate', 'rumor_spread_rate'],
        positive: ['positive_belief_rate', 'truth_acceptance_rate'],
        polarization: ['polarization_index']
      }
      const keys = nameMap[category] || []
      for (const key of keys) {
        if (p[key] && p[key][field] !== undefined) {
          return p[key][field]
        }
      }
      return 0
    },

    // 计算预测区间期望值位置百分比（带除零保护）
    getExpectedPosition(category, lowField, highField) {
      const expected = this.getPredictionField(category, 'expected')
      const low = this.getPredictionField(category, lowField)
      const high = this.getPredictionField(category, highField)
      const range = high - low
      return range > 0 ? ((expected - low) / range * 100) : 50
    },

    // 展开信息面板并高亮指定项
    showInfoPanelWithHighlight(itemKey) {
      this.showInfoPanel = true
      this.highlightedInfoItem = itemKey
      // 滚动到对应元素
      this.$nextTick(() => {
        const el = document.querySelector('.info-item.highlighted')
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
      })
      // 3秒后取消高亮
      setTimeout(() => {
        this.highlightedInfoItem = null
      }, 3000)
    },

    getOpinionClass(opinion) {
      if (opinion < 0) return 'opinion-rumor'
      if (opinion > 0) return 'opinion-truth'
      return 'opinion-neutral'
    },

    // Phase 3: 干预策略相关方法
    getStrategyIcon(type) {
      const icons = {
        'debunk': '📢',
        'prevent': '🛡️',
        'amplify': '📣',
        'depolarize': '🤝',
        'multi': '🎯'
      }
      return icons[type] || '📋'
    },

    getCostLabel(cost) {
      const labels = {
        'low': '低',
        'medium': '中',
        'high': '高',
        'very_high': '极高'
      }
      return labels[cost] || cost
    },

    // ==================== WebSocket 连接 ====================

    connectWebSocket() {
      // 使用动态地址（开发环境走代理，生产环境直接访问）
      const wsUrl = `${WS_BASE}/ws/simulation`
      console.log('连接 WebSocket:', wsUrl)

      try {
        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          this.isConnected = true
          this.wsReconnectCount = 0
          console.log('WebSocket 已连接')
        }

        this.ws.onclose = (event) => {
          this.isConnected = false
          console.log('WebSocket 已断开', event.code, event.reason)
          if (this.wsReconnectCount < this.wsMaxReconnectAttempts) {
            this.wsReconnectCount++
            console.log(`WebSocket 重连尝试 ${this.wsReconnectCount}/${this.wsMaxReconnectAttempts}`)
            setTimeout(() => {
              if (!this.isConnected) {
                this.connectWebSocket()
              }
            }, 3000)
          } else {
            console.error('WebSocket 重连次数已达上限，停止重连')
            alert('WebSocket 连接失败，请刷新页面重试')
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket 错误:', error)
          this.isConnected = false
        }

        this.ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data)
            this.handleMessage(msg)
          } catch (e) {
            console.error('WebSocket message parse error:', e, event.data)
          }
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
          // 更新进度数据
          this.agentProgress = msg.message
          this.progressData = {
            step: msg.step || 0,
            total: msg.total || 0,
            percentage: msg.percentage || 0,
            agentId: msg.agent_id,
            agentOpinion: msg.agent_opinion || 0,
            agentStance: msg.agent_stance || '',
            currentStep: msg.current_step || 0,
            maxSteps: msg.max_steps || 50
          }
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
      this.hasStopped = false
      this.currentStep = 0
      this.animatedStep = 0
      this.debunked = false
      this.agentProgress = ''

      // 重置预测和风险预警
      this.prediction = null
      this.riskAlerts = null

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

      // 更新事件日志中待注入事件的状态
      this.eventLogs.forEach(log => {
        if (log.pending) {
          log.pending = false
        }
      })

      this.sendAction('start', {
        params: {
          mode: this.simulationMode,  // Phase 3: 运行模式
          cocoon_strength: this.cocoonStrength,
          debunk_delay: this.debunkDelay,
          initial_rumor_spread: this.initialRumorSpread,
          use_llm: this.useLLM,
          population_size: this.populationSize,
          network_type: this.networkType,
          max_steps: this.maxSteps,
          max_concurrent: this.maxConcurrent,
          connection_pool_size: this.connectionPoolSize,
          timeout: this.timeout,
          max_retries: this.maxRetries,
          use_dual_network: this.useDualNetwork,  // 双层网络开关
          num_communities: 8,      // 私域社群数量
          public_m: 3,             // 公域网络参数
          // Phase 3: 真实分布锚定（新闻模式）
          init_distribution: this.simulationMode === 'news' ? {
            believe_rumor: this.initDistRumor,
            believe_truth: this.initDistTruth,
            neutral: 1 - this.initDistRumor - this.initDistTruth
          } : null
        }
      })

      setTimeout(() => {
        if (this.isRunning) {
          const interval = this.useLLM ? this.autoInterval : 500
          this.sendAction('auto', { interval })
        }
      }, 500)
    },

    pauseSimulation() {
      this.isPaused = true
      this.sendAction('pause')
      // 暂停时刷新一次预测和风险预警
      if (this.currentStep >= 3) {
        this.fetchPrediction()
        this.fetchRiskAlerts()
      }
    },

    resumeSimulation() {
      this.isPaused = false
      const interval = this.useLLM ? this.autoInterval : 500
      this.sendAction('resume', { interval })
    },

    stopSimulation() {
      this.isRunning = false
      this.isPaused = false
      this.hasStopped = true
      this.agentProgress = ''
      this.sendAction('stop')
      // 用户主动停止时也展开报告面板
      if (this.currentStep > 0) {
        this.expandedGroups.report = true
      }
    },

    resetSimulation() {
      // 重置推演状态，允许重新开始
      this.hasStopped = false
      this.currentStep = 0
      this.animatedStep = 0
      this.prediction = null
      this.riskAlerts = null
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
      this.publicEdges = []
      this.privateEdges = []
      this.publicRumorRate = 0
      this.privateRumorRate = 0
      this.numCommunities = 0
      this.numInfluencers = 0
      // 重新标记所有事件为待注入
      this.eventLogs.forEach(log => {
        log.pending = true
      })
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
          API_BASE + '/api/report/content?filename=' + encodeURIComponent(this.reportFilename)
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
        const response = await fetch(API_BASE + '/api/math-model/explanation')
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

    async fetchUsageContent() {
      this.usageLoading = true
      try {
        const response = await fetch(API_BASE + '/api/docs/usage')
        const data = await response.json()
        if (data.success && data.content) {
          this.usageContent = DOMPurify.sanitize(marked(data.content))
        }
      } catch (error) {
        console.error('获取使用说明失败:', error)
        this.usageContent = '<p style="color:#ef4444;">加载失败，请刷新重试</p>'
      } finally {
        this.usageLoading = false
      }
    },

    // ==================== 新闻解析功能 ====================

    async parseNews() {
      if (!this.newsContent.trim()) return
      
      this.newsParsing = true
      this.newsParseError = ''
      this.parsedKnowledgeGraph = null
      
      try {
        const response = await fetch(API_BASE + '/api/event/parse', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: this.newsContent })
        })
        const data = await response.json()
        
        if (data.success) {
          this.parsedKnowledgeGraph = data.data
          this.knowledgeGraph = data.data
        } else {
          this.newsParseError = data.error || '解析失败'
        }
      } catch (error) {
        console.error('解析新闻失败:', error)
        this.newsParseError = '网络错误: ' + error.message
      } finally {
        this.newsParsing = false
      }
    },

    viewParsedGraph() {
      this.showNewsParser = false
      this.showKnowledgeGraph = true
    },

    // ==================== 事件注入功能 ====================

    async injectEvent() {
      if (!this.airdropContent.trim()) return

      this.airdropLoading = true
      this.airdropLoadingStage = this.airdropSkipParse ? '正在快速注入事件...' : '正在调用大模型解析事件图谱...'
      this.airdropError = ''
      this.airdropSuccess = false
      this.parsedGraphDisplay = null

      try {
        // 第一阶段：解析（显示Loading状态）
        if (!this.airdropSkipParse) {
          this.airdropLoadingStage = '⏳ 阶段1/3: 大模型正在解析事件图谱...'
        } else {
          this.airdropLoadingStage = '⚡ 快速注入模式...'
        }

        // 创建带超时的 fetch 请求（快速模式5秒，完整解析180秒）
        const controller = new AbortController()
        const timeout = this.airdropSkipParse ? 5000 : 180000
        const timeoutId = setTimeout(() => controller.abort(), timeout)

        const response = await fetch(
          API_BASE + '/api/event/airdrop',
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              content: this.airdropContent,
              source: this.airdropSource,
              skip_parse: this.airdropSkipParse,
              credibility: this.airdropCredibility
            }),
            signal: controller.signal
          }
        )
        clearTimeout(timeoutId)
        const data = await response.json()

        if (data.success) {
          // 更新Loading状态
          this.airdropLoadingStage = '✅ 阶段2/3: 知识图谱解析完成'

          // 保存解析后的图谱数据用于展示
          if (data.data && data.data.knowledge_graph) {
            this.parsedGraphDisplay = data.data.knowledge_graph
            this.knowledgeGraph = data.data.knowledge_graph
          }

          // 更新Loading状态到第三阶段
          this.airdropLoadingStage = '✅ 阶段3/3: 事件处理完成'

          // 获取事件冲击信息
          const eventData = data.data?.event || {}
          const impactStrength = eventData.impact_strength || 0
          const affectedAgents = eventData.affected_agents || 0
          const avgShift = eventData.avg_opinion_shift || 0
          const sentiment = eventData.sentiment || '中性'
          const credibility = eventData.credibility || '不确定'

          // 更新可信度显示（用户选择的优先）
          this.newsCredibility = credibility

          // 添加到事件日志（透明化展示）
          this.addEventLog({
            content: this.airdropContent,
            source: this.airdropSource,
            knowledgeGraph: this.parsedGraphDisplay,
            timestamp: new Date().toLocaleString('zh-CN'),
            pending: this.currentStep === 0,  // 标记是否为待注入
            // 新增：事件冲击信息
            impact: {
              strength: impactStrength,
              affectedAgents: affectedAgents,
              avgShift: avgShift,
              sentiment: sentiment,
              credibility: credibility
            }
          })

          // 短暂延迟后关闭弹窗
          setTimeout(() => {
            this.showEventAirdrop = false
            this.airdropContent = ''
            this.airdropLoading = false
            this.airdropLoadingStage = ''
            this.airdropSuccess = true

            // 显示成功提示（包含图谱信息和冲击效果）
            const entityCount = this.parsedGraphDisplay?.entities?.length || 0
            const relationCount = this.parsedGraphDisplay?.relations?.length || 0

            if (this.currentStep === 0) {
              // 推演未开始，事件将被存储
              alert(`事件解析成功！\n\n📊 解析结果：${entityCount}个实体, ${relationCount}个关系\n📝 摘要：${this.parsedGraphDisplay?.summary || '无'}\n🎭 情感：${sentiment} | 可信度：${credibility}\n\n✅ 事件已存储，将在推演开始时自动注入`)
            } else {
              // 推演已开始，自动刷新界面显示冲击效果
              let impactMsg = ''
              if (impactStrength > 0) {
                impactMsg = `\n\n⚡ 事件冲击效果：\n  • 冲击强度：${(impactStrength * 100).toFixed(1)}%\n  • 影响Agent：${affectedAgents}个\n  • 平均观点偏移：${(avgShift * 100).toFixed(2)}%`
              }
              alert(`事件注入成功！\n\n📊 解析结果：${entityCount}个实体, ${relationCount}个关系\n📝 摘要：${this.parsedGraphDisplay?.summary || '无'}\n🎭 情感：${sentiment} | 可信度：${credibility}${impactMsg}`)

              // 自动获取最新状态刷新界面
              this.refreshSimulationState()
            }
          }, 500)
        } else {
          this.airdropError = data.error || '注入失败'
          this.airdropLoading = false
          this.airdropLoadingStage = ''
        }
      } catch (error) {
        console.error('注入事件失败:', error)
        if (error.name === 'AbortError') {
          this.airdropError = '请求超时（120秒），请检查后端服务是否正常'
        } else {
          this.airdropError = '网络错误: ' + error.message
        }
        this.airdropLoading = false
        this.airdropLoadingStage = ''
      }
    },
    
    // 添加事件日志
    addEventLog(eventData) {
      console.log('[addEventLog] 添加事件日志:', eventData)
      console.log('[addEventLog] 当前currentStep:', this.currentStep)
      console.log('[addEventLog] pending状态:', eventData.pending)
      this.eventLogs.unshift(eventData)  // 新事件放前面
      console.log('[addEventLog] eventLogs总数:', this.eventLogs.length)
      console.log('[addEventLog] pendingEvents:', this.eventLogs.filter(log => log.pending))
      // 最多保留10条日志
      if (this.eventLogs.length > 10) {
        this.eventLogs.pop()
      }
    },
    
    // 格式化实体列表用于日志显示
    formatEntitiesForLog(entities) {
      if (!entities || entities.length === 0) return '无'
      return entities.slice(0, 5).map(e => e.name).join(', ') + (entities.length > 5 ? ` +${entities.length - 5}` : '')
    },

    // 将实体ID解析为名称
    resolveEntityName(id) {
      if (!this.knowledgeGraph?.entities) return id
      const entity = this.knowledgeGraph.entities.find(e => e.id === id)
      return entity ? entity.name : id
    },

    // 刷新推演状态（事件注入后调用）
    async refreshSimulationState() {
      try {
        const response = await fetch(API_BASE + '/api/simulation/state')
        const data = await response.json()
        if (data.step !== undefined) {
          this.updateState(data)
          console.log('[refreshSimulationState] 状态已刷新，当前步骤:', data.step)
        }
      } catch (error) {
        console.error('[refreshSimulationState] 刷新状态失败:', error)
      }
    },

    // ==================== 历史报告功能 ====================

    async fetchReportList() {
      this.showReportList = true
      this.reportListLoading = true
      this.reportList = []
      this.simulationReports = []
      this.intelligenceReports = []
      try {
        // 构建查询参数
        const params = new URLSearchParams()
        if (this.reportSearchKeyword) {
          params.append('search', this.reportSearchKeyword)
        }
        params.append('sort', this.reportSortBy)
        params.append('order', this.reportSortOrder)

        const response = await fetch(API_BASE + '/api/report/list?' + params.toString())
        const data = await response.json()
        this.reportList = data.reports || []
        this.simulationReports = data.simulation_reports || []
        this.intelligenceReports = data.intelligence_reports || []
        this.reportCounts = data.counts || { total: 0, simulation: 0, intelligence: 0 }
      } catch (error) {
        console.error('获取报告列表失败:', error)
        this.reportList = []
        this.simulationReports = []
        this.intelligenceReports = []
        this.reportCounts = { total: 0, simulation: 0, intelligence: 0 }
      } finally {
        this.reportListLoading = false
      }
    },

    // 搜索框防抖处理（手动实现）
    onReportSearchInput() {
      if (this._searchTimer) {
        clearTimeout(this._searchTimer)
      }
      this._searchTimer = setTimeout(() => {
        this.fetchReportList()
      }, 300)
    },

    // 切换排序方式
    changeReportSort(sortBy) {
      if (this.reportSortBy === sortBy) {
        this.reportSortOrder = this.reportSortOrder === 'desc' ? 'asc' : 'desc'
      } else {
        this.reportSortBy = sortBy
        this.reportSortOrder = 'desc'
      }
      this.fetchReportList()
    },

    // 切换类型筛选
    changeReportTypeFilter(type) {
      this.reportTypeFilter = type
      this.fetchReportList()
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
        link.href = API_BASE + '/api/report/download?filename=' + encodeURIComponent(this.reportFilename)
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
        const eventSource = new EventSource(API_BASE + '/api/report/stream')

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
        const response = await fetch(API_BASE + '/api/report/open', {
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
        const response = await fetch(`${API_BASE}/api/agent/${agentId}/inspect`)
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
      this.rumorSpreadRate = data.mislead_rate || data.rumor_spread_rate
      this.truthAcceptanceRate = data.correct_rate || data.truth_acceptance_rate
      this.believeRate = data.believe_rate || 0
      this.rejectRate = data.reject_rate || 0
      this.newsCredibility = data.news_credibility || '不确定'
      this.avgOpinion = data.avg_opinion
      this.polarizationIndex = data.polarization_index
      this.silenceRate = data.silence_rate || 0
      this.debunked = data.step >= this.debunkDelay

      // v3.0 新增字段
      this.avgRumorTrust = data.avg_rumor_trust || 0
      this.avgTruthTrust = data.avg_truth_trust || 0
      this.needDistribution = data.need_distribution || {}
      this.behaviorDistribution = data.behavior_distribution || {}
      this.totalExposures = data.total_exposures || 0
      this.truthInterventionActive = data.truth_intervention_active || false

      // Phase 3: 实体影响摘要
      if (data.entity_impact_summary) {
        this.entityImpactSummary = data.entity_impact_summary
      }

      // 只在步骤变化时追加历史记录（避免事件注入刷新时重复）
      const lastStep = this.trendHistory.steps[this.trendHistory.steps.length - 1]
      if (lastStep !== data.step) {
        this.trendHistory.steps.push(data.step)
        this.trendHistory.rumorRates.push(data.rumor_spread_rate)
        this.trendHistory.truthRates.push(data.truth_acceptance_rate)
        this.trendHistory.avgOpinions.push(data.avg_opinion)
        this.trendHistory.polarization.push(data.polarization_index)
        this.trendHistory.silenceRates.push(data.silence_rate || 0)
        this.trendHistory.publicRumorRates.push(data.public_rumor_rate || data.rumor_spread_rate)
        this.trendHistory.privateRumorRates.push(data.private_rumor_rate || data.rumor_spread_rate)
      }

      this.agentProgress = ''

      if (data.step >= this.maxSteps) {
        this.isRunning = false
        this.hasStopped = true
        this.sendAction('stop')
        // 重置进度数据
        this.progressData = {
          step: 0, total: 0, percentage: 0, agentId: null,
          agentOpinion: 0, agentStance: '', currentStep: 0, maxSteps: this.maxSteps
        }
        // 推演完成，获取最终预测数据
        this.fetchPrediction()
        this.fetchRiskAlerts()
        // 推演完成，显示引导弹窗
        this.showCompletionModal = true
        // 自动展开报告面板
        this.expandedGroups.report = true
      }

      this.renderOpinionChart()
      this.renderNetworkChart()
      this.renderTrendChart()
      this.renderV3Charts()

      // 每3步获取一次预测和风险预警
      if (this.currentStep >= 3 && this.currentStep % 3 === 0) {
        this.fetchPrediction()
        this.fetchRiskAlerts()
      }
    },

    // ==================== 预测与风险预警 (Phase 2) ====================

    async fetchPrediction() {
      try {
        const response = await fetch(API_BASE + '/api/prediction')
        const data = await response.json()
        if (data.success) {
          this.prediction = data.data
        }
      } catch (e) {
        console.error('获取预测失败:', e)
      }
    },

    async fetchRiskAlerts() {
      try {
        const response = await fetch(API_BASE + '/api/risk-alerts')
        const data = await response.json()
        if (data.success) {
          this.riskAlerts = data.data
        }
      } catch (e) {
        console.error('获取风险预警失败:', e)
      }
    },

    // ==================== 图表渲染 ====================

    initCharts() {
      this.opinionChartInstance = echarts.init(this.$refs.opinionChart)
      this.renderOpinionChart()

      this.networkChartInstance = echarts.init(this.$refs.networkChart)
      this.renderNetworkChart()

      this.trendChartInstance = echarts.init(this.$refs.trendChart)
      this.renderTrendChart()

      this.renderV3Charts()
    },

    renderV3Charts() {
      this.$nextTick(() => {
        if (this.$refs.needDistChart && Object.keys(this.needDistribution).length > 0) {
          if (!this.needDistChartInstance) {
            this.needDistChartInstance = echarts.init(this.$refs.needDistChart)
          }
          this.renderNeedDistChart()
        }
        if (this.$refs.behaviorDistChart && Object.keys(this.behaviorDistribution).length > 0) {
          if (!this.behaviorDistChartInstance) {
            this.behaviorDistChartInstance = echarts.init(this.$refs.behaviorDistChart)
          }
          this.renderBehaviorDistChart()
        }
      })
    },

    handleResize() {
      this.opinionChartInstance?.resize()
      this.networkChartInstance?.resize()
      this.trendChartInstance?.resize()
      this.needDistChartInstance?.resize()
      this.behaviorDistChartInstance?.resize()
      if (this.chartModalInstance) {
        this.chartModalInstance.resize()
      }
    },

    openChartModal(type) {
      this.chartModalType = type
      const titles = {
        opinion: '群体观点分布',
        network: '信息传播网络',
        trend: '舆论演化趋势'
      }
      this.chartModalTitle = titles[type] || '图表'
      this.chartModalOpen = true

      this.$nextTick(() => {
        this.chartModalInstance = echarts.init(this.$refs.chartModalBody)
        this.renderModalChart()
      })
    },

    closeChartModal() {
      this.chartModalOpen = false
      if (this.chartModalInstance) {
        this.chartModalInstance.dispose()
        this.chartModalInstance = null
      }
    },

    renderModalChart() {
      if (!this.chartModalInstance) return

      let option = null

      if (this.chartModalType === 'opinion') {
        option = this.getOpinionChartOption()
      } else if (this.chartModalType === 'network') {
        option = this.getNetworkChartOption()
      } else if (this.chartModalType === 'trend') {
        option = this.getTrendChartOption()
      }

      if (option) {
        this.chartModalInstance.setOption(option)
      }

      // 为网络图添加点击事件（查看Agent详情）
      if (this.chartModalType === 'network') {
        this.chartModalInstance.off('click')
        this.chartModalInstance.on('click', (params) => {
          if (params.dataType === 'node') {
            const agentId = parseInt(params.data.id)
            this.inspectAgent(agentId)
          }
        })
      }

      // 为趋势图添加全选/反选功能
      if (this.chartModalType === 'trend') {
        this.chartModalInstance.off('legendselectchanged')
        this.chartModalInstance.on('legendselectchanged', (params) => {
          const selected = params.selected
          if (!selected) return
          
          const legendData = ['误信率', '正确认知率', '平均观点', '极化指数', '沉默率', '公域误信率', '私域误信率']
          const visibleCount = legendData.filter(name => selected[name]).length
          
          // 全选：使用延时确保图例状态已更新
          if (visibleCount === legendData.length) {
            setTimeout(() => {
              legendData.forEach(name => {
                this.chartModalInstance.dispatchAction({ type: 'legendSelect', name: name })
              })
            }, 50)
          }
          // 反选（全不选）
          else if (visibleCount === 0) {
            setTimeout(() => {
              legendData.forEach(name => {
                this.chartModalInstance.dispatchAction({ type: 'legendUnSelect', name: name })
              })
            }, 50)
          }
        })
      }
    },
    getOpinionChartOption() {
      const data = this.opinionDist.counts.map((count, i) => ({
        value: count,
        center: this.opinionDist.centers?.[i] || i
      }))

      return {
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
            // 根据新闻可信度动态调整颜色语义
            // center < 0 → 拒绝新闻, center > 0 → 相信新闻
            // 中立区间: |center| <= 0.05
            if (Math.abs(center) <= 0.05) color = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#f59e0b' },
              { offset: 1, color: '#d97706' }
            ])
            else {
              // 根据新闻可信度判定"误信/正确认知"
              const isBelieve = center > 0  // 相信新闻
              let isMislead
              if (this.newsCredibility === '低可信') {
                // 低可信新闻：相信=误信
                isMislead = isBelieve
              } else if (this.newsCredibility === '高可信') {
                // 高可信新闻：拒绝=误信
                isMislead = !isBelieve
              } else {
                // 不确定时：恢复传统语义，负值=误信(红色)，正值=正确认知(绿色)
                isMislead = !isBelieve
              }
              color = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: isMislead ? '#ef4444' : '#22c55e' },
                { offset: 1, color: isMislead ? '#dc2626' : '#16a34a' }
              ])
            }
            return {
              value: d.value,
              itemStyle: { color, borderRadius: [4, 4, 0, 0] }
            }
          }),
          barWidth: '70%'
        }]
      }
    },

    getNetworkChartOption() {
      if (!this.agents || !this.agents.length) {
        return { backgroundColor: 'transparent', title: { text: '暂无数据', style: { color: '#9ca3af' } } }
      }

      const edges = this.useDualNetwork
        ? (this.activeNetworkTab === 'public' ? this.publicEdges : this.privateEdges)
        : (this.edges || [])

      const communityColors = [
        '#60a5fa', '#a78bfa', '#f472b6', '#fb923c',
        '#4ade80', '#22d3ee', '#facc15', '#e879f9'
      ]

      const nodes = this.agents.map(agent => {
        let color
        if (agent.opinion < 0) color = '#ef4444'
        else if (agent.opinion > 0) color = '#22c55e'
        else color = '#f59e0b'

        const opacity = agent.is_silent ? 0.3 : 1.0

        let symbolSize
        if (this.useDualNetwork && this.activeNetworkTab === 'public') {
          symbolSize = agent.is_influencer
            ? 12 + (agent.influence || 0) * 15
            : 4 + (agent.influence || 0) * 6
        } else if (this.useDualNetwork) {
          color = communityColors[agent.community_id % 8] || color
          symbolSize = agent.is_silent ? 3 : 5
        } else {
          symbolSize = 5 + (agent.influence || 0) * 10
        }

        return {
          id: agent.id.toString(),
          name: `#${agent.id}`,
          symbolSize: symbolSize,
          itemStyle: {
            color: color,
            opacity: opacity,
            borderColor: agent.is_influencer ? '#fcd34d' : null,
            borderWidth: agent.is_influencer ? 2 : 0
          },
          x: Math.random() * 800,
          y: Math.random() * 500
        }
      })

      const sampledEdges = edges
        .filter(() => Math.random() < 0.3)
        .slice(0, 500)
        .map(([source, target]) => ({ source: source.toString(), target: target.toString() }))

      return {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(30, 41, 59, 0.9)',
          borderColor: 'rgba(100, 181, 246, 0.3)',
          textStyle: { color: '#e2e8f0' },
          formatter: (params) => {
            if (params.dataType === 'node') {
              const agent = this.agents.find(a => a.id.toString() === params.data.id)
              if (agent) {
                const influencerTag = agent.is_influencer ? ' [大V]' : ''
                const communityTag = ` [社群${(agent.community_id || 0) + 1}]`
                const tag = this.useDualNetwork && this.activeNetworkTab === 'public' ? influencerTag : communityTag
                const silenceTag = agent.is_silent ? ' [沉默]' : ''
                // v3.0 新增字段
                const rumorTrust = agent.rumor_trust !== undefined ? `<div style="color: #f87171;">谣言信任: ${(agent.rumor_trust * 100).toFixed(1)}%</div>` : ''
                const truthTrust = agent.truth_trust !== undefined ? `<div style="color: #4ade80;">真相信任: ${(agent.truth_trust * 100).toFixed(1)}%</div>` : ''
                const dominantNeed = agent.dominant_need ? `<div style="color: #a78bfa;">主导需求: ${this.needLabel(agent.dominant_need)}</div>` : ''
                const predictedBehavior = agent.predicted_behavior ? `<div style="color: #facc15;">预测行为: ${this.behaviorLabel(agent.predicted_behavior)}</div>` : ''
                // 发布渠道映射（仅双层网络模式有意义）
                const channelMap = { 'public': '📢 公域', 'private': '🔒 私域', 'both': '📤 双渠道', 'none': '🔇 未发布' }
                const publishChannel = agent.publish_channel && agent.publish_channel !== 'none'
                  ? `<div style="color: #94a3b8;">发布渠道: ${channelMap[agent.publish_channel] || agent.publish_channel}</div>`
                  : ''
                return `<div style="padding: 8px;">
                  <div style="font-weight: bold;">Agent ${agent.id}${tag}${silenceTag}</div>
                  <div>观点: ${agent.opinion.toFixed(3)}</div>
                  ${rumorTrust}${truthTrust}${dominantNeed}${predictedBehavior}${publishChannel}
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
          label: { show: false },
          force: {
            repulsion: 100,
            gravity: 0.1,
            edgeLength: 30
          },
          lineStyle: {
            color: 'rgba(100, 181, 246, 0.2)',
            width: 0.5,
            curveness: 0.1
          }
        }]
      }
    },

    getTrendChartOption() {
      const hasDualData = this.trendHistory.publicRumorRates.length > 0 &&
                          this.publicRumorRates !== this.trendHistory.rumorRates

      return {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(20, 25, 40, 0.95)',
          borderColor: 'rgba(100, 181, 246, 0.3)',
          textStyle: { color: '#e0e0e0' }
        },
        legend: {
          data: ['误信率', '正确认知率', '平均观点', '极化指数', '沉默率', '公域误信率', '私域误信率'],
          textStyle: { color: '#6b7280', fontSize: 11 },
          top: 5,
          itemWidth: 16,
          itemHeight: 8,
          selectedMode: 'multiple',
          selector: true,
          selectorPosition: 'end',
          triggerEvent: true
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
            name: '误信率',
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
            name: '正确认知率',
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
          // 双层网络：公域/私域误信率曲线
          ...(hasDualData ? [
            {
              name: '公域误信率',
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
              name: '私域误信率',
              type: 'line',
              yAxisIndex: 1,
              data: this.trendHistory.privateRumorRates,
              lineStyle: { color: '#dc2626', width: 2, type: 'solid' },
              itemStyle: { color: '#dc2626' },
              smooth: true,
              symbol: 'circle',
              symbolSize: 4
            }
          ] : [])
        ]
      }
    },

    getCommunityColor(community) {
      const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#14b8a6', '#3b82f6', '#8b5cf6', '#ec4899']
      return colors[community % colors.length]
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
            // 根据新闻可信度动态调整颜色语义
            // center < 0 → 拒绝新闻, center > 0 → 相信新闻
            // 中立区间: |center| <= 0.05
            if (Math.abs(center) <= 0.05) color = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#f59e0b' },
              { offset: 1, color: '#d97706' }
            ])
            else {
              // 根据新闻可信度判定"误信/正确认知"
              const isBelieve = center > 0  // 相信新闻
              let isMislead
              if (this.newsCredibility === '低可信') {
                // 低可信新闻：相信=误信
                isMislead = isBelieve
              } else if (this.newsCredibility === '高可信') {
                // 高可信新闻：拒绝=误信
                isMislead = !isBelieve
              } else {
                // 不确定时：恢复传统语义，负值=误信(红色)，正值=正确认知(绿色)
                isMislead = !isBelieve
              }
              color = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: isMislead ? '#ef4444' : '#22c55e' },
                { offset: 1, color: isMislead ? '#dc2626' : '#16a34a' }
              ])
            }
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

    renderKnowledgeGraphChart() {
      const chartDom = this.$refs.knowledgeGraphChart
      if (!chartDom) return

      const kg = this.knowledgeGraph
      if (!kg || !kg.entities || kg.entities.length === 0) return

      // 中文类型 → 颜色/图标映射
      const typeColorMap = {
        '人物': '#f472b6',
        '组织': '#60a5fa',
        '地点': '#34d399',
        '事件': '#fbbf24',
        '时间': '#a78bfa',
        '概念': '#fb923c',
        '其他': '#94a3b8'
      }

      const typeIconMap = {
        '人物': 'circle',
        '组织': 'rect',
        '地点': 'triangle',
        '事件': 'diamond',
        '时间': 'pin',
        '概念': 'rect',
        '其他': 'circle'
      }

      // 构建 ID → name 映射（关系的 source/target 可能是 ID）
      const idToName = {}
      kg.entities.forEach(e => {
        if (e.id) idToName[e.id] = e.name
      })

      // 构建节点（用 name 作为节点标识，ECharts 按 name 匹配边）
      const nodes = kg.entities.map(e => {
        const t = e.type || '其他'
        const color = typeColorMap[t] || '#94a3b8'
        return {
          name: e.name,
          symbolSize: Math.max(30, 20 + (e.importance || 3) * 6),
          symbol: typeIconMap[t] || 'circle',
          itemStyle: {
            color: color,
            borderColor: 'rgba(255,255,255,0.3)',
            borderWidth: 2,
            shadowBlur: 10,
            shadowColor: color + '80'
          },
          label: {
            show: true,
            color: '#e2e8f0',
            fontSize: 12,
            fontWeight: 500,
            position: 'bottom',
            distance: 5
          },
          category: t,
          _type: t
        }
      })

      // 构建边：将 ID 转换为 name
      const links = (kg.relations || []).map(r => {
        const sourceName = idToName[r.source] || r.source
        const targetName = idToName[r.target] || r.target
        return {
          source: sourceName,
          target: targetName,
          label: {
            show: true,
            formatter: r.action || r.relation || '',
            color: '#94a3b8',
            fontSize: 10,
            backgroundColor: 'rgba(15,23,42,0.8)',
            padding: [2, 4],
            borderRadius: 3
          },
          lineStyle: {
            color: '#475569',
            width: 1.5,
            curveness: 0.2
          }
        }
      })

      // 分类（中文）
      const categorySet = new Set(kg.entities.map(e => e.type || '其他'))
      const categories = [...categorySet].map(t => ({
        name: t,
        itemStyle: { color: typeColorMap[t] || '#94a3b8' }
      }))

      const chart = echarts.init(chartDom, null, { renderer: 'canvas' })

      const option = {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(15,23,42,0.95)',
          borderColor: 'rgba(139,92,246,0.3)',
          textStyle: { color: '#e2e8f0', fontSize: 12 },
          formatter: (params) => {
            if (params.dataType === 'node') {
              return `<b>${params.name}</b><br/>类型: ${params.data._type || '其他'}`
            }
            if (params.dataType === 'edge') {
              const label = typeof params.data.label?.formatter === 'function'
                ? '' : (params.data.label?.formatter || '')
              return `${params.data.source} → <b>${label}</b> → ${params.data.target}`
            }
            return ''
          }
        },
        legend: {
          data: categories.map(c => c.name),
          textStyle: { color: '#94a3b8', fontSize: 11 },
          top: 0,
          right: 10,
          orient: 'vertical'
        },
        animationDuration: 1500,
        animationEasingUpdate: 'quinticInOut',
        series: [{
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: links,
          categories: categories,
          roam: true,
          draggable: true,
          force: {
            repulsion: 350,
            gravity: 0.1,
            edgeLength: [80, 200],
            friction: 0.6
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: { width: 3 },
            itemStyle: { borderWidth: 4, borderColor: '#fff' },
            label: { fontSize: 14, fontWeight: 'bold' }
          },
          blur: {
            itemStyle: { opacity: 0.2 },
            lineStyle: { opacity: 0.1 }
          }
        }]
      }

      chart.setOption(option)

      // 窗口 resize 时自适应
      const resizeHandler = () => chart.resize()
      window.addEventListener('resize', resizeHandler)
      this._kgChartResizeHandler = resizeHandler
      this._kgChartInstance = chart
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
        if (agent.opinion < 0) color = '#ef4444'
        else if (agent.opinion > 0) color = '#22c55e'
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
                // v3.0 新增字段
                const rumorTrust = agent.rumor_trust !== undefined ? `<div style="color: #f87171;">谣言信任: ${(agent.rumor_trust * 100).toFixed(1)}%</div>` : ''
                const truthTrust = agent.truth_trust !== undefined ? `<div style="color: #4ade80;">真相信任: ${(agent.truth_trust * 100).toFixed(1)}%</div>` : ''
                const dominantNeed = agent.dominant_need ? `<div style="color: #a78bfa;">主导需求: ${this.needLabel(agent.dominant_need)}</div>` : ''
                const predictedBehavior = agent.predicted_behavior ? `<div style="color: #facc15;">预测行为: ${this.behaviorLabel(agent.predicted_behavior)}</div>` : ''
                // 发布渠道（仅双层网络模式有意义）
                const channelMap = { 'public': '📢 公域', 'private': '🔒 私域', 'both': '📤 双渠道', 'none': '🔇 未发布' }
                const publishChannel = agent.publish_channel && agent.publish_channel !== 'none'
                  ? `<div style="color: #94a3b8;">发布渠道: ${channelMap[agent.publish_channel] || agent.publish_channel}</div>`
                  : ''
                return `<div style="padding: 8px;">
                  <div style="font-weight: bold;">Agent ${agent.id}${tag}${silenceTag}</div>
                  <div>观点: ${agent.opinion.toFixed(3)}</div>
                  ${rumorTrust}${truthTrust}${dominantNeed}${predictedBehavior}${publishChannel}
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
          data: ['误信率', '正确认知率', '平均观点', '极化指数', '沉默率', '公域误信率', '私域误信率'],
          textStyle: { color: '#6b7280', fontSize: 11 },
          top: 5,
          itemWidth: 16,
          itemHeight: 8,
          selectedMode: 'multiple',
          selector: true,
          selectorPosition: 'end',
          triggerEvent: true
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
            name: '误信率',
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
            name: '正确认知率',
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
          // 双层网络：公域/私域误信率曲线
          {
            name: '公域误信率',
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
            name: '私域误信率',
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
    },

    // ==================== v3.0 图表渲染 ====================

    renderNeedDistChart() {
      if (!this.needDistChartInstance) return

      const needLabels = {
        '生理': '生理需求',
        '安全': '安全需求',
        '社交': '社交需求',
        '尊重': '尊重需求',
        '认知': '认知需求',
        physiological: '生理需求',
        safety: '安全需求',
        love: '社交需求',
        esteem: '尊重需求',
        cognitive: '认知需求'
      }
      const needColors = {
        '生理': '#ef4444',
        '安全': '#f97316',
        '社交': '#3b82f6',
        '尊重': '#a855f7',
        '认知': '#22c55e',
        physiological: '#ef4444',
        safety: '#f97316',
        love: '#3b82f6',
        esteem: '#a855f7',
        cognitive: '#22c55e'
      }

      const dist = this.needDistribution
      const data = Object.entries(dist).map(([key, value]) => ({
        name: needLabels[key] || key,
        value: value,
        itemStyle: { color: needColors[key] || '#9ca3af' }
      }))

      const option = {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'item',
          formatter: '{b}: {c} ({d}%)'
        },
        series: [{
          type: 'pie',
          radius: ['35%', '65%'],
          center: ['50%', '50%'],
          data: data,
          label: {
            color: '#d1d5db',
            fontSize: 11,
            formatter: '{b}\n{d}%'
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }]
      }

      this.needDistChartInstance.setOption(option)
    },

    renderBehaviorDistChart() {
      if (!this.behaviorDistChartInstance) return

      const behaviorLabels = {
        '分享': '📢 分享',
        '评论': '💬 评论',
        '观望': '👁️ 观望',
        '沉默': '🤫 沉默',
        '核查': '🔍 核查',
        '拒绝': '✋ 拒绝',
        SHARE: '📢 分享',
        COMMENT: '💬 评论',
        OBSERVE: '👁️ 观望',
        SILENCE: '🤫 沉默',
        VERIFY: '🔍 核查',
        REJECT: '✋ 拒绝'
      }
      const behaviorColors = {
        '分享': '#ef4444',
        '评论': '#f97316',
        '观望': '#60a5fa',
        '沉默': '#9ca3af',
        '核查': '#22c55e',
        '拒绝': '#8b5cf6',
        SHARE: '#ef4444',
        COMMENT: '#f97316',
        OBSERVE: '#60a5fa',
        SILENCE: '#9ca3af',
        VERIFY: '#22c55e',
        REJECT: '#8b5cf6'
      }

      const dist = this.behaviorDistribution
      const data = Object.entries(dist).map(([key, value]) => ({
        name: behaviorLabels[key] || key,
        value: value,
        itemStyle: { color: behaviorColors[key] || '#9ca3af' }
      }))

      const option = {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'item',
          formatter: '{b}: {c} ({d}%)'
        },
        series: [{
          type: 'pie',
          radius: ['35%', '65%'],
          center: ['50%', '50%'],
          data: data,
          label: {
            color: '#d1d5db',
            fontSize: 11,
            formatter: '{b}\n{d}%'
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }]
      }

      this.behaviorDistChartInstance.setOption(option)
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

/* ==================== 开关样式 ==================== */
.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #374151;
  transition: 0.3s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

.switch input:checked + .slider {
  background-color: #3b82f6;
}

.switch input:checked + .slider:before {
  transform: translateX(20px);
}

.switch input:disabled + .slider {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ==================== 顶部流程引导 ==================== */
.workflow-guide {
  position: fixed;
  top: 0;
  left: 320px;
  right: 0;
  height: 50px;
  background: rgba(15, 23, 42, 0.98);
  border-bottom: 1px solid rgba(100, 181, 246, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.workflow-steps {
  display: flex;
  align-items: center;
  gap: 8px;
}

.workflow-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 20px;
  background: rgba(51, 65, 85, 0.5);
  color: #94a3b8;
  font-size: 13px;
  transition: all 0.3s ease;
}

.workflow-step.active {
  background: rgba(59, 130, 246, 0.3);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.5);
}

.workflow-step.completed {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.4);
}

.step-number {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(51, 65, 85, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 12px;
}

.workflow-step.active .step-number {
  background: #3b82f6;
  color: white;
}

.workflow-step.completed .step-number {
  background: #22c55e;
  color: white;
}

.step-connector {
  width: 40px;
  height: 2px;
  background: rgba(51, 65, 85, 0.5);
  transition: background 0.3s ease;
}

.step-connector.active {
  background: linear-gradient(90deg, #22c55e, #3b82f6);
}

/* ==================== 事件注入区块（左侧面板） ==================== */
.event-inject-section {
  background: rgba(30, 41, 59, 0.8);
  border-radius: 10px;
  border: 1px solid rgba(245, 158, 11, 0.3);
  padding: 12px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.section-icon {
  font-size: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #fbbf24;
}

.event-count-badge {
  background: rgba(245, 158, 11, 0.3);
  color: #fbbf24;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
}

/* 待注入事件列表（紧凑版） */
.pending-events-mini {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pending-mini-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 6px;
  border: 1px solid rgba(100, 181, 246, 0.1);
}

.mini-index {
  font-size: 11px;
  color: #60a5fa;
  font-weight: 600;
}

.mini-content {
  flex: 1;
  font-size: 12px;
  color: #e2e8f0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mini-entities {
  font-size: 10px;
  color: #94a3b8;
  background: rgba(100, 181, 246, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.more-events {
  font-size: 11px;
  color: #94a3b8;
  text-align: center;
  padding: 4px;
}

.event-actions-row {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.btn-event-add {
  flex: 1;
  padding: 8px 12px;
  background: rgba(51, 65, 85, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 6px;
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-event-add:hover {
  background: rgba(51, 65, 85, 0.8);
  color: #e2e8f0;
}

.btn-event-start {
  flex: 2;
  padding: 8px 12px;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-event-start:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 12px rgba(245, 158, 11, 0.4);
}

.btn-event-reset {
  flex: 2;
  padding: 8px 12px;
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-event-reset:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 12px rgba(139, 92, 246, 0.4);
}

/* 无事件引导 */
.no-event-hint {
  text-align: center;
  padding: 12px;
}

.hint-text {
  font-size: 13px;
  color: #f59e0b;
  margin-bottom: 10px;
}

.btn-inject-primary {
  width: 100%;
  padding: 10px 16px;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-inject-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
}

/* ==================== 帮助说明面板 ==================== */
.help-section {
  background: rgba(30, 41, 59, 0.6);
  border-radius: 8px;
  border: 1px solid rgba(100, 181, 246, 0.1);
  overflow: hidden;
}

.help-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  cursor: pointer;
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.2s ease;
}

.help-header:hover {
  background: rgba(59, 130, 246, 0.1);
}

.help-toggle {
  font-size: 10px;
  transition: transform 0.3s ease;
}

.help-toggle.expanded {
  transform: rotate(180deg);
}

.help-content {
  padding: 12px;
  border-top: 1px solid rgba(100, 181, 246, 0.1);
  background: rgba(15, 23, 42, 0.4);
}

.help-item {
  margin-bottom: 10px;
}

.help-item:last-child {
  margin-bottom: 0;
}

.help-item strong {
  color: #60a5fa;
  font-size: 12px;
  display: block;
  margin-bottom: 4px;
}

.help-item p {
  color: #94a3b8;
  font-size: 11px;
  line-height: 1.5;
  margin: 2px 0;
}

/* ==================== 分组功能面板 ==================== */
.panel-footer-grouped {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.footer-group {
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  border: 1px solid rgba(100, 181, 246, 0.1);
  overflow: hidden;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  cursor: pointer;
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.2s ease;
}

.group-header:hover {
  background: rgba(59, 130, 246, 0.1);
}

.group-toggle {
  font-size: 10px;
  color: #64748b;
  transition: transform 0.3s ease;
}

.group-toggle.expanded {
  transform: rotate(180deg);
}

.group-buttons {
  padding: 8px;
  border-top: 1px solid rgba(100, 181, 246, 0.1);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.btn-group {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: rgba(51, 65, 85, 0.6);
  color: #e2e8f0;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.btn-group:hover {
  background: rgba(59, 130, 246, 0.3);
  transform: translateX(2px);
}

.btn-group:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

.panel-header .header-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 4px;
}

.sass-logo-link {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sass-logo {
  width: 36px;
  height: 36px;
  object-fit: contain;
  border-radius: 4px;
  transition: transform 0.2s ease;
}

.sass-logo:hover {
  transform: scale(1.1);
}

.panel-header h1 {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
}

.panel-header .subtitle {
  font-size: 12px;
  color: #6b7280;
}

.header-links {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 8px;
}

.header-links .project-link {
  margin-top: 0;
}

.project-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
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

/* 参数标签与帮助图标 */
.param-label-with-help {
  display: flex;
  align-items: center;
  gap: 4px;
}

.param-help {
  font-size: 12px;
  color: #6b7280;
  cursor: help;
  transition: color 0.2s;
}

.param-help:hover {
  color: #60a5fa;
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

/* ==================== Phase 3: 真实分布锚定样式 ==================== */
.init-dist-config {
  background: rgba(30, 41, 59, 0.3);
  border-radius: 8px;
  padding: 12px;
}

.init-dist-config .param-item {
  margin-bottom: 8px;
}

.init-dist-config .param-item:last-child {
  margin-bottom: 0;
}

.init-dist-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(100, 181, 246, 0.1);
  font-size: 12px;
  color: #94a3b8;
}

.dist-bar {
  display: inline-flex;
  width: 120px;
  height: 12px;
  border-radius: 6px;
  overflow: hidden;
  background: rgba(30, 41, 59, 0.5);
}

.dist-rumor {
  background: linear-gradient(90deg, #ef4444, #f87171);
}

.dist-neutral {
  background: #64748b;
}

.dist-truth {
  background: linear-gradient(90deg, #22c55e, #4ade80);
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

.param-hint {
  font-size: 11px;
  color: #f59e0b;
  margin-top: 4px;
  font-style: italic;
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

.btn-reset {
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
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  color: white;
  box-shadow: 0 4px 20px rgba(139, 92, 246, 0.3);
}

.btn-reset:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 30px rgba(139, 92, 246, 0.4);
}

.btn-pause {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  box-shadow: 0 4px 20px rgba(245, 158, 11, 0.3);
}

.btn-resume {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  box-shadow: 0 4px 20px rgba(16, 185, 129, 0.3);
}

.btn-group-row {
  display: flex;
  gap: 8px;
  width: 100%;
}

.btn-group-row > button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-group-row > button:hover {
  transform: translateY(-1px);
  filter: brightness(1.1);
}

.btn-icon {
  font-size: 14px;
}

.progress-container {
  width: 100%;
  padding: 14px 16px;
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
  border: 1px solid rgba(96, 165, 250, 0.3);
  border-radius: 12px;
  margin-top: 12px;
}

.pause-container {
  width: 100%;
  padding: 14px 16px;
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
  border: 1px solid rgba(245, 158, 11, 0.4);
  border-radius: 12px;
  margin-top: 12px;
}

.pause-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.pause-icon {
  font-size: 18px;
}

.pause-title {
  color: #fbbf24;
  font-size: 14px;
  font-weight: 600;
}

.pause-step {
  margin-left: auto;
  color: #94a3b8;
  font-size: 12px;
  background: rgba(245, 158, 11, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.pause-hint {
  color: #94a3b8;
  font-size: 12px;
  padding-left: 28px;
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.progress-title {
  color: #60a5fa;
  font-size: 14px;
  font-weight: 500;
}

.progress-step {
  margin-left: auto;
  color: #94a3b8;
  font-size: 12px;
  background: rgba(96, 165, 250, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.progress-bar-wrapper {
  width: 100%;
  height: 6px;
  background: rgba(100, 116, 139, 0.3);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6 0%, #60a5fa 50%, #93c5fd 100%);
  border-radius: 3px;
  transition: width 0.15s ease-out;
  box-shadow: 0 0 10px rgba(96, 165, 250, 0.5);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.progress-agent {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #e2e8f0;
}

.agent-label {
  color: #94a3b8;
}

.agent-id {
  color: #60a5fa;
  font-weight: 600;
}

.agent-opinion {
  font-family: monospace;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
}

.agent-opinion.opinion-rumor {
  color: #f87171;
  background: rgba(248, 113, 113, 0.15);
}

.agent-opinion.opinion-truth {
  color: #4ade80;
  background: rgba(74, 222, 128, 0.15);
}

.agent-opinion.opinion-neutral {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.15);
}

.agent-stance {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.agent-stance.stance-信谣言 {
  color: #f87171;
  background: rgba(248, 113, 113, 0.2);
}

.agent-stance.stance-信真相 {
  color: #4ade80;
  background: rgba(74, 222, 128, 0.2);
}

.agent-stance.stance-中立 {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.2);
}

.progress-count {
  color: #94a3b8;
  font-size: 12px;
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

/* 面板底部按钮样式（保留兼容） */
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
/* 注意：.main-content 样式已移至文件末尾，这里保留图表子区域样式 */

/* KPI指标卡 */
.kpi-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  flex-shrink: 0;
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

.kpi-card.clickable {
  cursor: pointer;
}

.kpi-card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
  border-color: rgba(100, 181, 246, 0.3);
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

.kpi-card.knowledge {
  border-color: rgba(16, 185, 129, 0.3);
}

.kpi-card.knowledge .kpi-icon {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.kpi-card.knowledge .kpi-value {
  color: #10b981;
}

/* Phase 3: 运行模式状态显示样式 */
.kpi-card.mode-indicator {
  border-color: rgba(139, 92, 246, 0.3);
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%);
}

.kpi-card.mode-indicator .kpi-icon {
  background: rgba(139, 92, 246, 0.15);
  color: #8b5cf6;
}

.kpi-card.mode-indicator .kpi-value {
  color: #8b5cf6;
  font-size: 14px;
}

.kpi-card.mode-indicator.news {
  border-color: rgba(245, 158, 11, 0.3);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.05) 0%, rgba(251, 191, 36, 0.05) 100%);
}

.kpi-card.mode-indicator.news .kpi-icon {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.kpi-card.mode-indicator.news .kpi-value {
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

/* ==================== 预测与风险预警样式 (Phase 2) ==================== */

.prediction-alerts-area {
  display: flex;
  gap: 16px;
  flex-shrink: 0;
  max-height: 140px;
  overflow: hidden;
}

.prediction-panel {
  flex: 1;
  min-width: 280px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.05));
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 10px;
  padding: 12px;
  overflow: hidden;
}

.prediction-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.prediction-header h4 {
  font-size: 14px;
  color: #60a5fa;
  margin: 0;
}

.prediction-step {
  font-size: 11px;
  color: #6b7280;
}

.prediction-intervals {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.prediction-item {
  flex: 1;
  min-width: 120px;
}

.prediction-label {
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 4px;
}

.prediction-bar {
  height: 12px;
  background: rgba(30, 41, 59, 0.8);
  border-radius: 6px;
  position: relative;
  margin-bottom: 4px;
}

.bar-range {
  position: absolute;
  top: 0;
  bottom: 0;
  background: rgba(59, 130, 246, 0.3);
  border-radius: 6px;
}

.prediction-bar.truth-bar .bar-range {
  background: rgba(34, 197, 94, 0.3);
}

.bar-expected {
  position: absolute;
  width: 4px;
  height: 100%;
  background: #f59e0b;
  border-radius: 2px;
}

.prediction-values {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
}

.prediction-values .optimistic {
  color: #22c55e;
}

.prediction-values .expected {
  color: #f59e0b;
  font-weight: 600;
}

.prediction-values .pessimistic {
  color: #ef4444;
}

.prediction-recommendation {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(59, 130, 246, 0.2);
  display: flex;
  gap: 6px;
  align-items: center;
}

.risk-badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.risk-badge.low {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.risk-badge.medium {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.risk-badge.high {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.recommendation-msg {
  font-size: 12px;
  color: #cbd5e1;
}

/* Phase 3: 增强干预策略样式 */
.intervention-strategies {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(59, 130, 246, 0.2);
}

.strategies-header {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  margin-bottom: 8px;
}

.strategies-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.strategy-item {
  display: flex;
  gap: 8px;
  padding: 8px;
  background: rgba(30, 41, 59, 0.4);
  border-radius: 8px;
  border: 1px solid rgba(100, 181, 246, 0.1);
}

.strategy-icon {
  font-size: 20px;
  line-height: 1;
}

.strategy-content {
  flex: 1;
}

.strategy-name {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
}

.strategy-desc {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.strategy-meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  font-size: 10px;
}

.effectiveness {
  color: #22c55e;
}

.cost {
  color: #94a3b8;
}

.cost.high {
  color: #f59e0b;
}

.cost.very_high {
  color: #ef4444;
}

.intervention-timing {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 8px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 6px;
  font-size: 12px;
}

.timing-label {
  color: #94a3b8;
}

.timing-value {
  font-weight: 600;
  color: #60a5fa;
}

.window-status {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
}

.window-status.充足 {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.window-status.收窄 {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.window-status.紧迫 {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.risk-badge.critical {
  background: rgba(239, 68, 68, 0.3);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.5);
}

.alerts-panel {
  flex: 1;
  min-width: 280px;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(220, 38, 38, 0.05));
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 10px;
  padding: 12px;
  overflow: hidden;
}

.alerts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.alerts-header h4 {
  font-size: 14px;
  color: #f87171;
  margin: 0;
}

.alerts-count {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  padding: 2px 6px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 90px;
  overflow-y: auto;
}

.alert-item {
  display: flex;
  gap: 6px;
  padding: 6px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 6px;
}

.alert-item.critical {
  border-left: 3px solid #ef4444;
}

.alert-item.high {
  border-left: 3px solid #f59e0b;
}

.alert-item.medium {
  border-left: 3px solid #3b82f6;
}

.alert-icon {
  font-size: 18px;
}

.alert-content {
  flex: 1;
}

.alert-message {
  font-size: 13px;
  color: #e2e8f0;
  margin-bottom: 2px;
}

.alert-suggestion {
  font-size: 11px;
  color: #9ca3af;
}

.risk-summary {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(239, 68, 68, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.risk-score {
  font-size: 11px;
  color: #cbd5e1;
}

.risk-level {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.risk-level.low {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.risk-level.medium {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.risk-level.high {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.risk-level.critical {
  background: rgba(220, 38, 38, 0.3);
  color: #fca5a5;
}

/* 图表区域 */
.charts-grid {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 460px;
  overflow: hidden;
}

.chart-row {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.top-row {
  flex: 1.6;
}

.bottom-row {
  flex: 1;
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

/* v3.0 心理分析面板 */
.v3-panel {
  flex: 0 0 320px;
  min-width: 280px;
}

.v3-panel .chart-header.clickable {
  cursor: pointer;
  user-select: none;
}

.v3-panel .toggle-icon {
  color: #94a3b8;
  font-size: 12px;
}

.v3-charts-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px;
  height: 100%;
}

.v3-chart-item {
  flex: 1;
  min-height: 0;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
  gap: 8px;
}

.chart-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  flex-shrink: 0;
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

/* ==================== 使用说明抽屉 ==================== */
.usage-drawer {
  width: 640px;
  height: 100%;
  background: rgba(15, 23, 42, 0.98);
  border-left: 1px solid rgba(100, 181, 246, 0.2);
  display: flex;
  flex-direction: column;
}

/* usage-content 样式已统一到 Markdown 统一样式部分 */

/* ==================== Agent透视弹窗 ==================== */
.agent-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  z-index: 500;
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

/* ==================== 图表放大弹窗 ==================== */
.chart-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.9);
  backdrop-filter: blur(8px);
  z-index: 400;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-modal {
  width: 90vw;
  height: 80vh;
  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(100, 181, 246, 0.3);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chart-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.2);
}

.chart-modal-header h3 {
  font-size: 18px;
  color: #e2e8f0;
  margin: 0;
}

.chart-modal-close {
  background: transparent;
  border: none;
  color: #9ca3af;
  font-size: 20px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.chart-modal-close:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.chart-modal-body {
  flex: 1;
  width: 100%;
  padding: 16px;
}

/* ==================== 图表放大按钮 ==================== */
.chart-zoom-btn {
  background: transparent;
  border: 1px solid rgba(100, 181, 246, 0.3);
  color: #9ca3af;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  margin-left: auto;
}

.chart-zoom-btn:hover {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.5);
  color: #60a5fa;
}

/* ==================== 报告弹窗 ==================== */
/* 推演完成引导弹窗 */
.completion-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  z-index: 350;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.3s ease;
}

.completion-modal {
  width: 420px;
  background: linear-gradient(145deg, #0f172a, #1e1b4b);
  border: 1px solid rgba(100, 181, 246, 0.3);
  border-radius: 16px;
  padding: 32px 28px;
  text-align: center;
  box-shadow: 0 0 60px rgba(100, 181, 246, 0.25);
  animation: slideUp 0.4s ease;
}

.completion-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.completion-title {
  font-size: 20px;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 8px;
}

.completion-desc {
  font-size: 14px;
  color: #94a3b8;
  margin: 0 0 20px;
  line-height: 1.5;
}

.completion-stats {
  display: flex;
  justify-content: center;
  gap: 20px;
  padding: 14px 0;
  margin-bottom: 20px;
  border-top: 1px solid rgba(100, 181, 246, 0.15);
  border-bottom: 1px solid rgba(100, 181, 246, 0.15);
}

.completion-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.completion-stat-item .stat-label {
  font-size: 11px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.completion-stat-item .stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #f97316;
}

.completion-stat-item .stat-value.truth {
  color: #34d399;
}

.completion-stat-item .stat-value.risk-low { color: #34d399; }
.completion-stat-item .stat-value.risk-medium { color: #fbbf24; }
.completion-stat-item .stat-value.risk-high { color: #f97316; }
.completion-stat-item .stat-value.risk-critical { color: #ef4444; }

.completion-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.btn-completion {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-completion:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-report {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #fff;
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
}

.btn-report:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
}

.btn-intelligence {
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  color: #fff;
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
}

.btn-intelligence:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5);
}

.btn-later {
  background: rgba(100, 116, 139, 0.15);
  color: #94a3b8;
  border: 1px solid rgba(100, 116, 139, 0.2);
}

.btn-later:hover:not(:disabled) {
  background: rgba(100, 116, 139, 0.25);
  color: #cbd5e1;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

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

/* 增强版历史报告弹窗 */
.report-modal-enhanced {
  width: 900px;
  max-height: 80vh;
}

.report-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 10px;
  margin-bottom: 16px;
}

.report-search-box {
  flex: 1;
  position: relative;
}

.report-search-input {
  width: 100%;
  padding: 8px 12px 8px 36px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 13px;
  outline: none;
  transition: all 0.2s;
}

.report-search-input:focus {
  border-color: rgba(100, 181, 246, 0.5);
  background: rgba(0, 0, 0, 0.4);
}

.report-search-input::placeholder {
  color: #6b7280;
}

.report-search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 14px;
  pointer-events: none;
}

.report-sort-btns {
  display: flex;
  gap: 6px;
}

.sort-btn {
  padding: 6px 10px;
  background: rgba(100, 181, 246, 0.1);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 6px;
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 36px;
}

.sort-btn:hover {
  background: rgba(100, 181, 246, 0.2);
  color: #e2e8f0;
}

.sort-btn.active {
  background: rgba(100, 181, 246, 0.25);
  border-color: rgba(100, 181, 246, 0.4);
  color: #60a5fa;
}

.report-stats {
  padding: 8px 12px;
  background: rgba(100, 181, 246, 0.08);
  border-radius: 6px;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 16px;
}

.report-stats strong {
  color: #60a5fa;
  font-weight: 600;
}

.report-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.report-column {
  display: flex;
  flex-direction: column;
  background: rgba(30, 41, 59, 0.3);
  border-radius: 10px;
  border: 1px solid rgba(100, 181, 246, 0.1);
  overflow: hidden;
}

.column-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(100, 181, 246, 0.1);
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
}

.column-icon {
  font-size: 16px;
}

.column-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  flex: 1;
}

.column-count {
  padding: 2px 8px;
  background: rgba(100, 181, 246, 0.2);
  border-radius: 10px;
  font-size: 11px;
  color: #60a5fa;
}

.column-body {
  flex: 1;
  padding: 12px;
  max-height: 350px;
  overflow-y: auto;
}

.column-body .report-list {
  max-height: none;
}

.column-body .report-placeholder {
  height: 150px;
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

.report-item-intelligence {
  border-color: rgba(168, 85, 247, 0.2);
}

.report-item-intelligence:hover {
  background: rgba(168, 85, 247, 0.1);
  border-color: rgba(168, 85, 247, 0.3);
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

/* ==================== Markdown 统一样式 ==================== */
/* 适用于 .intelligence-content 和 .usage-content */

.intelligence-content,
.usage-content {
  font-size: 14px;
  line-height: 1.8;
  color: #e2e8f0;
}

.intelligence-content h1,
.usage-content h1 {
  font-size: 22px;
  font-weight: 700;
  color: #f0abfc;
  margin: 24px 0 16px 0;
  padding-bottom: 10px;
  border-bottom: 2px solid rgba(240, 171, 252, 0.3);
  background: linear-gradient(90deg, rgba(240, 171, 252, 0.1), transparent);
  padding-left: 12px;
  border-radius: 4px 4px 0 0;
}

.intelligence-content h2,
.usage-content h2 {
  font-size: 18px;
  font-weight: 600;
  color: #c4b5fd;
  margin: 20px 0 12px 0;
  padding: 8px 12px;
  background: rgba(196, 181, 253, 0.08);
  border-left: 3px solid #c4b5fd;
  border-radius: 0 6px 6px 0;
}

.intelligence-content h3,
.usage-content h3 {
  font-size: 16px;
  font-weight: 600;
  color: #a78bfa;
  margin: 16px 0 10px 0;
  padding-left: 10px;
}

.intelligence-content h4,
.usage-content h4 {
  font-size: 14px;
  font-weight: 600;
  color: #818cf8;
  margin: 12px 0 8px 0;
}

.intelligence-content p,
.usage-content p {
  margin: 0 0 14px 0;
  line-height: 1.75;
  color: #cbd5e1;
}

.intelligence-content ul,
.usage-content ul,
.intelligence-content ol,
.usage-content ol {
  margin: 0 0 14px 0;
  padding-left: 20px;
}

.intelligence-content li,
.usage-content li {
  margin-bottom: 6px;
  line-height: 1.6;
  color: #e2e8f0;
}

.intelligence-content li::marker,
.usage-content li::marker {
  color: #a78bfa;
}

.intelligence-content table,
.usage-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 13px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 8px;
  overflow: hidden;
}

.intelligence-content th,
.usage-content th {
  background: linear-gradient(135deg, rgba(167, 139, 250, 0.2), rgba(139, 92, 246, 0.1));
  color: #f0abfc;
  font-weight: 600;
  padding: 12px 16px;
  text-align: left;
  border-bottom: 2px solid rgba(167, 139, 250, 0.3);
}

.intelligence-content td,
.usage-content td {
  padding: 10px 16px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
  color: #e2e8f0;
}

.intelligence-content tr:last-child td,
.usage-content tr:last-child td {
  border-bottom: none;
}

.intelligence-content tr:nth-child(even) td,
.usage-content tr:nth-child(even) td {
  background: rgba(0, 0, 0, 0.15);
}

.intelligence-content blockquote,
.usage-content blockquote {
  border-left: 4px solid #8b5cf6;
  margin: 16px 0;
  padding: 12px 16px;
  background: rgba(139, 92, 246, 0.08);
  border-radius: 0 8px 8px 0;
  color: #a5b4fc;
}

.intelligence-content blockquote p,
.usage-content blockquote p {
  margin: 0;
  color: #a5b4fc;
}

.intelligence-content code,
.usage-content code {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
}

.intelligence-content pre,
.usage-content pre {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(100, 181, 246, 0.15);
  border-radius: 8px;
  padding: 16px;
  margin: 16px 0;
  overflow-x: auto;
}

.intelligence-content pre code,
.usage-content pre code {
  background: none;
  padding: 0;
  color: #86efac;
  font-size: 13px;
  line-height: 1.5;
}

.intelligence-content strong,
.usage-content strong {
  color: #fcd34d;
  font-weight: 600;
}

.intelligence-content em,
.usage-content em {
  color: #a5b4fc;
}

.intelligence-content a,
.usage-content a {
  color: #60a5fa;
  text-decoration: none;
  border-bottom: 1px solid rgba(96, 165, 250, 0.3);
  transition: all 0.2s;
}

.intelligence-content a:hover,
.usage-content a:hover {
  color: #93c5fd;
  border-bottom-color: #93c5fd;
}

.intelligence-content hr,
.usage-content hr {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(167, 139, 250, 0.4), transparent);
  margin: 24px 0;
}

.intelligence-content img,
.usage-content img {
  max-width: 100%;
  border-radius: 8px;
  margin: 12px 0;
}

/* 删除旧的重复定义，保留 intelligence-modal-footer 和按钮样式 */

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

/* ==================== 知识图谱模态框 ==================== */
.kg-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.kg-modal {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 16px;
  width: 80%;
  max-width: 900px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(139, 92, 246, 0.3);
}

.kg-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(139, 92, 246, 0.2);
}

.kg-modal-header h3 {
  margin: 0;
  color: #e0e0e0;
  font-size: 18px;
}

.kg-modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.kg-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #a0a0a0;
}

.kg-content {
  color: #e0e0e0;
}

.kg-section {
  margin-bottom: 20px;
}

.kg-info-box {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
  padding: 12px;
}

.kg-info-box p {
  margin: 0 0 8px 0;
  color: #e2e8f0;
  font-size: 13px;
  line-height: 1.5;
}

.kg-info-box p:last-child {
  margin-bottom: 0;
}

.kg-info-hint {
  color: #94a3b8;
  font-size: 12px !important;
}

/* 注入时机说明样式 */
.impact-desc {
  color: #cbd5e1 !important;
  margin-top: 8px !important;
}

.impact-list {
  margin: 8px 0 0 0;
  padding-left: 20px;
  list-style: disc;
}

.impact-list li {
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.8;
}

.impact-tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  margin-right: 4px;
}

.impact-tag.negative {
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.impact-tag.positive {
  background: rgba(34, 197, 94, 0.2);
  color: #86efac;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.impact-tag.high {
  background: rgba(59, 130, 246, 0.2);
  color: #93c5fd;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.impact-tag.low {
  background: rgba(245, 158, 11, 0.2);
  color: #fcd34d;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

/* 可信度选择器样式 */
.credibility-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
}
.credibility-tag.high {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}
.credibility-tag.low {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}
.credibility-tag.uncertain {
  background: rgba(156, 163, 175, 0.15);
  color: #9ca3af;
  border: 1px solid rgba(156, 163, 175, 0.3);
}
.credibility-hint {
  font-size: 11px;
  color: #6b7280;
  margin-left: 4px;
}

/* 观点分布图标题旁的可信度徽章 */
.credibility-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  margin-left: 8px;
  white-space: nowrap;
}
.credibility-badge.high {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}
.credibility-badge.low {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

/* ==================== 知识图谱可视化 ==================== */
.kg-modal-graph {
  max-width: 1000px;
  width: 85%;
}

.kg-graph-container {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
}

.kg-graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.kg-stats {
  font-size: 13px;
  color: #94a3b8;
}

.kg-legend {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.kg-legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #94a3b8;
}

.kg-legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.kg-legend-dot.person { background: #f472b6; }
.kg-legend-dot.org { background: #60a5fa; }
.kg-legend-dot.location { background: #34d399; }
.kg-legend-dot.event { background: #fbbf24; }
.kg-legend-dot.other { background: #94a3b8; }

.kg-graph-chart {
  width: 100%;
  height: 400px;
  border-radius: 8px;
}

/* 实体标签按类型着色 */
.kg-entity-tag.kg-entity-person,
.kg-entity-tag.kg-entity-人物 { background: rgba(244, 114, 182, 0.2); border-color: rgba(244, 114, 182, 0.4); color: #f472b6; }
.kg-entity-tag.kg-entity-organization,
.kg-entity-tag.kg-entity-组织 { background: rgba(96, 165, 250, 0.2); border-color: rgba(96, 165, 250, 0.4); color: #60a5fa; }
.kg-entity-tag.kg-entity-location,
.kg-entity-tag.kg-entity-地点 { background: rgba(52, 211, 153, 0.2); border-color: rgba(52, 211, 153, 0.4); color: #34d399; }
.kg-entity-tag.kg-entity-event,
.kg-entity-tag.kg-entity-事件 { background: rgba(251, 191, 36, 0.2); border-color: rgba(251, 191, 36, 0.4); color: #fbbf24; }
.kg-entity-tag.kg-entity-time,
.kg-entity-tag.kg-entity-时间 { background: rgba(167, 139, 250, 0.2); border-color: rgba(167, 139, 250, 0.4); color: #a78bfa; }
.kg-entity-tag.kg-entity-concept,
.kg-entity-tag.kg-entity-概念 { background: rgba(251, 146, 60, 0.2); border-color: rgba(251, 146, 60, 0.4); color: #fb923c; }
.kg-entity-tag.kg-entity-other,
.kg-entity-tag.kg-entity-其他 { background: rgba(148, 163, 184, 0.2); border-color: rgba(148, 163, 184, 0.4); color: #94a3b8; }

.kg-section h4 {
  margin: 0 0 10px 0;
  color: #a78bfa;
  font-size: 14px;
}

.kg-summary {
  background: rgba(139, 92, 246, 0.1);
  padding: 12px;
  border-radius: 8px;
  border-left: 3px solid #8b5cf6;
  line-height: 1.6;
}

.kg-entities {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.kg-entity-tag {
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.4);
  border-radius: 16px;
  padding: 4px 12px;
  font-size: 13px;
  color: #60a5fa;
}

.kg-entity-type {
  color: #a0a0a0;
  font-size: 11px;
  margin-left: 4px;
}

.kg-relations {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kg-relation-item {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
}

.kg-relation-source {
  color: #ef4444;
  font-weight: 500;
}

.kg-relation-action {
  color: #a0a0a0;
  margin: 0 8px;
}

.kg-relation-target {
  color: #22c55e;
  font-weight: 500;
}

.kg-json {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
  color: #a0a0a0;
  overflow-x: auto;
  max-height: 200px;
  white-space: pre-wrap;
  word-break: break-all;
}

/* ==================== 新闻解析输入 ==================== */
.news-input {
  width: 100%;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 8px;
  padding: 12px;
  color: #e0e0e0;
  font-size: 14px;
  resize: vertical;
  font-family: inherit;
}

.news-input:focus {
  outline: none;
  border-color: rgba(139, 92, 246, 0.6);
}

.news-input::placeholder {
  color: #6b7280;
}

.btn-parse-news {
  margin-top: 12px;
  background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-parse-news:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
}

.btn-parse-news:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.kg-error {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
  padding: 12px;
  border-radius: 8px;
  border-left: 3px solid #ef4444;
}

/* ==================== 事件注入三段式管线样式 ==================== */
.kg-modal-event {
  max-width: 600px;
}

.pipeline-steps {
  margin: 10px 0;
  padding-left: 0;
  list-style: none;
}

.pipeline-steps li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  color: #cbd5e1;
  font-size: 13px;
}

.pipeline-steps .step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 50%;
  color: white;
  font-size: 11px;
  font-weight: 600;
}

.airdrop-loading-section {
  text-align: center;
  padding: 30px 20px;
}

.airdrop-loading-animation {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.loading-spinner-large {
  width: 48px;
  height: 48px;
  border: 3px solid rgba(139, 92, 246, 0.2);
  border-top-color: #8b5cf6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-text {
  color: #e2e8f0;
  font-size: 15px;
  font-weight: 500;
}

.loading-progress {
  width: 100%;
  max-width: 300px;
  height: 4px;
  background: rgba(139, 92, 246, 0.2);
  border-radius: 2px;
  overflow: hidden;
  margin: 16px auto;
}

.progress-bar-loading {
  height: 100%;
  width: 30%;
  background: linear-gradient(90deg, #8b5cf6, #a78bfa, #c4b5fd);
  border-radius: 2px;
  animation: loading-slide 1.5s ease-in-out infinite;
}

@keyframes loading-slide {
  0% { transform: translateX(-100%); }
  50% { transform: translateX(200%); }
  100% { transform: translateX(-100%); }
}

.loading-hint {
  color: #94a3b8;
  font-size: 13px;
  margin-top: 12px;
}

/* 解析结果预览样式 */
.parsed-graph-display {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 12px;
  padding: 16px;
}

.parsed-graph-display h4 {
  color: #4ade80;
  margin-bottom: 12px;
}

.graph-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.graph-summary {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.summary-label {
  color: #94a3b8;
  font-size: 13px;
  white-space: nowrap;
}

.summary-text {
  color: #e2e8f0;
  font-size: 13px;
  line-height: 1.5;
}

.graph-stats {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-icon {
  font-size: 14px;
}

.stat-value {
  color: #cbd5e1;
  font-size: 13px;
}

.graph-entities-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.entity-tag {
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 16px;
  padding: 4px 10px;
  font-size: 12px;
}

.entity-type {
  color: #60a5fa;
  margin-right: 4px;
}

.entity-name {
  color: #e2e8f0;
}

.entity-more {
  color: #94a3b8;
  font-size: 12px;
  display: flex;
  align-items: center;
}

/* ==================== 事件日志样式 ==================== */
.event-log-count {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
  color: #1f2937;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 8px;
}

.event-log-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 8px 0;
  max-height: 300px;
  overflow-y: auto;
}

.event-log-item {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 10px;
  padding: 12px;
  font-size: 13px;
}

.event-log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  gap: 8px;
}

.event-log-time {
  color: #94a3b8;
  font-size: 11px;
}

.event-log-status {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
}

.event-log-status.status-pending {
  background: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
}

.event-log-status.status-injected {
  background: rgba(16, 185, 129, 0.2);
  color: #4ade80;
}

.event-log-source {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
}

.event-log-source.source-public {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.event-log-source.source-private {
  background: rgba(16, 185, 129, 0.2);
  color: #4ade80;
}

.event-log-content {
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.4;
  margin-bottom: 8px;
}

.event-log-graph {
  background: rgba(139, 92, 246, 0.1);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.graph-summary-line,
.graph-entities-line,
.graph-stats-line {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}

.summary-icon,
.entities-icon {
  color: #a78bfa;
}

.graph-summary-line {
  color: #cbd5e1;
}

.graph-entities-line {
  color: #60a5fa;
}

.graph-stats-line {
  color: #94a3b8;
}

.btn-view-graph {
  margin-top: 12px;
  background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-view-graph:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
}

/* ==================== 事件注入 ==================== */
.btn-airdrop {
  background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
  color: #1f2937;
  border: none;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.btn-airdrop:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
}

.airdrop-source-options {
  display: flex;
  gap: 20px;
  margin: 12px 0;
}

.source-option {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #e0e0e0;
  font-size: 14px;
}

.source-option input {
  accent-color: #8b5cf6;
}

.airdrop-hint {
  color: #9ca3af;
  font-size: 13px;
  margin-bottom: 12px;
  line-height: 1.5;
}

.btn-knowledge-graph {
  background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%);
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.btn-knowledge-graph:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
}

/* ==================== 右侧说明栏 ==================== */
.info-panel {
  position: fixed;
  right: 0;
  top: 0;
  height: 100vh;
  width: 320px;
  background: rgba(15, 23, 42, 0.98);
  border-left: 1px solid rgba(100, 181, 246, 0.15);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;
  z-index: 1000;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.3);
}

.info-panel.collapsed {
  width: 40px;
  box-shadow: none;
}

.info-panel-toggle {
  flex-shrink: 0;
  padding: 15px 8px;
  text-align: center;
  background: rgba(59, 130, 246, 0.9);
  color: white;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

.info-panel-toggle:hover {
  background: rgba(59, 130, 246, 1);
}

.info-panel.collapsed .info-panel-toggle {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.info-panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #60a5fa;
  margin-bottom: 4px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
}

.info-item {
  padding: 10px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  border: 1px solid rgba(100, 181, 246, 0.08);
  transition: all 0.3s ease;
}

.info-item.highlighted {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 0 15px rgba(59, 130, 246, 0.3);
}

.info-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.info-item-label {
  font-size: 12px;
  color: #cbd5e1;
  font-weight: 500;
}

.info-item-value {
  font-size: 14px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.info-item-value.danger { color: #ef4444; }
.info-item-value.success { color: #22c55e; }
.info-item-value.info { color: #3b82f6; }
.info-item-value.purple { color: #a78bfa; }
.info-item-value.warning { color: #f59e0b; }
.info-item-value.knowledge { color: #10b981; }

.info-item-desc {
  font-size: 11px;
  color: #6b7280;
  line-height: 1.4;
}

/* 实体影响力展示 */
.entity-impact-list {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(100, 181, 246, 0.1);
}

.entity-impact-title {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 10px;
  font-weight: 500;
}

.entity-impact-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.entity-impact-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.entity-name {
  font-size: 12px;
  color: #e2e8f0;
  min-width: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entity-type {
  font-size: 10px;
  color: #64748b;
  background: rgba(100, 181, 246, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  min-width: 40px;
  text-align: center;
}

.entity-impact-bar {
  flex: 1;
  height: 6px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 3px;
  overflow: hidden;
}

.entity-impact-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  border-radius: 3px;
  transition: width 0.3s ease;
}

/* 知识驱动机制高亮 */
.mechanism-item.knowledge-mechanism {
  background: rgba(16, 185, 129, 0.1);
  border-radius: 8px;
  padding: 2px;
}

/* 推演机制列表 */
.mechanism-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mechanism-item {
  display: flex;
  gap: 10px;
  padding: 10px;
  background: rgba(30, 41, 59, 0.4);
  border-radius: 8px;
  border: 1px solid rgba(100, 181, 246, 0.06);
}

.mechanism-icon {
  font-size: 18px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(100, 181, 246, 0.1);
  border-radius: 6px;
}

.mechanism-content {
  flex: 1;
}

.mechanism-content strong {
  font-size: 12px;
  color: #e2e8f0;
  display: block;
  margin-bottom: 2px;
}

.mechanism-content p {
  font-size: 11px;
  color: #6b7280;
  line-height: 1.3;
}

/* 图表阅读指南 */
.guide-item {
  padding: 10px;
  background: rgba(30, 41, 59, 0.4);
  border-radius: 8px;
  border: 1px solid rgba(100, 181, 246, 0.06);
}

.guide-item strong {
  font-size: 12px;
  color: #e2e8f0;
  display: block;
  margin-bottom: 6px;
}

.guide-item ul {
  margin: 0;
  padding-left: 16px;
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.5;
}

.guide-item li {
  margin-bottom: 2px;
}

/* 操作提示 */
.tips-section {
  background: rgba(34, 197, 94, 0.08);
  border-radius: 10px;
  padding: 12px;
  border: 1px solid rgba(34, 197, 94, 0.15);
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #cbd5e1;
}

.tip-icon {
  font-size: 14px;
}

/* 图表区域容器调整 */
.charts-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  padding-top: 70px;
  gap: 16px;
  overflow-y: auto;
  min-width: 0;
  min-height: 600px;
}

/* 主内容区布局调整 */
.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 预测预警区：只保留上面的定义，此处不重复 */
</style>

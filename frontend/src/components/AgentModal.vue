<template>
  <div v-if="modelValue" class="agent-modal-overlay" @click.self="close">
    <div class="agent-modal">
      <div class="modal-header">
        <h3><span class="icon">🔍</span> {{ inspectedAgentTitle }}</h3>
        <button class="close-btn" @click="close">✕</button>
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
              <div class="info-item" v-if="agentSnapshot.realistic_profile?.name">
                <span class="label">姓名</span>
                <span class="value highlight">{{ agentSnapshot.realistic_profile.name }}</span>
              </div>
              <div class="info-item" v-if="agentSnapshot.realistic_profile?.role_label">
                <span class="label">现实角色</span>
                <span class="value">{{ agentSnapshot.realistic_profile.role_label }}</span>
              </div>
              <div class="info-item">
                <span class="label">人设类型</span>
                <span class="value highlight">{{ agentSnapshot.persona?.type || '未知' }}</span>
              </div>
              <div class="info-item">
                <span class="label">人设描述</span>
                <span class="value desc">{{ agentSnapshot.persona?.desc || '-' }}</span>
              </div>
              <!-- LLM 画像丰富字段 -->
              <template v-if="agentSnapshot.persona?.personality">
                <div class="info-item">
                  <span class="label">性格特点</span>
                  <span class="value">{{ agentSnapshot.persona.personality }}</span>
                </div>
                <div class="info-item">
                  <span class="label">信息习惯</span>
                  <span class="value">{{ agentSnapshot.persona.media_habit }}</span>
                </div>
                <div class="info-item">
                  <span class="label">社交风格</span>
                  <span class="value">{{ agentSnapshot.persona.social_style }}</span>
                </div>
                <div class="info-item">
                  <span class="label">权威态度</span>
                  <span class="value">{{ agentSnapshot.persona.authority_stance }}</span>
                </div>
              </template>
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

        <details v-if="generationTrace" class="info-block trace-block">
          <summary class="trace-toggle">
            <span class="trace-toggle-title"><span class="block-icon">🧩</span> 数值来源</span>
            <span class="trace-toggle-meta">
              <span class="trace-badge">{{ generationTraceSourceLabel }}</span>
              <span class="trace-badge" v-if="generationTrace?.derived?.seniority_score !== undefined">资历分 {{ generationTrace.derived.seniority_score }}</span>
              <span class="trace-badge" v-if="generationTrace?.derived?.is_influencer !== undefined">{{ generationTrace.derived.is_influencer ? '意见领袖' : '普通成员' }}</span>
              <span class="trace-chevron"></span>
            </span>
          </summary>
          <div class="block-content">
            <div class="trace-summary">{{ generationTraceSummary }}</div>

            <div v-if="generationTraceInputs.length" class="trace-section">
              <div class="trace-section-title">输入依据</div>
              <div class="trace-grid">
                <div v-for="item in generationTraceInputs" :key="item.key" class="trace-item">
                  <span class="label">{{ item.label }}</span>
                  <span class="value">{{ item.value }}<template v-if="item.suffix">{{ item.suffix }}</template></span>
                </div>
              </div>
            </div>

            <div v-if="generationTraceDerived.length" class="trace-section">
              <div class="trace-section-title">中间结果</div>
              <div class="trace-grid">
                <div v-for="item in generationTraceDerived" :key="item.key" class="trace-item" :title="item.tooltip">
                  <span class="label">{{ item.label }}</span>
                  <span class="value">{{ typeof item.value === 'boolean' ? (item.value ? '是' : '否') : item.value }}</span>
                </div>
              </div>
            </div>

            <div v-if="generationTraceMetrics.length" class="trace-section">
              <div class="trace-section-title">最终数值</div>
              <div class="trace-grid">
                <div v-for="item in generationTraceMetrics" :key="item.key" class="trace-item" :title="item.tooltip">
                  <span class="label">{{ item.label }}</span>
                  <span class="value">{{ typeof item.value === 'number' ? item.value.toFixed(3) : item.value }}</span>
                </div>
              </div>
            </div>
          </div>
        </details>

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
</template>

<script>
export default {
  name: 'AgentModal',

  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    agentLoading: {
      type: Boolean,
      default: false
    },
    agentSnapshot: {
      type: Object,
      default: null
    },
    normalizedClimate: {
      type: Object,
      default: null
    },
    generationTrace: {
      type: Object,
      default: null
    },
    generationTraceSourceLabel: {
      type: String,
      default: ''
    },
    generationTraceSummary: {
      type: String,
      default: ''
    },
    generationTraceInputs: {
      type: Array,
      default: () => []
    },
    generationTraceDerived: {
      type: Array,
      default: () => []
    },
    generationTraceMetrics: {
      type: Array,
      default: () => []
    }
  },

  emits: ['update:modelValue'],

  computed: {
    inspectedAgentTitle() {
      const name = this.agentSnapshot?.realistic_profile?.name
      const id = this.agentSnapshot?.agent_id
      return name ? `${name} (#${id}) 微观行为透视` : `Agent #${id} 微观行为透视`
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
    }
  },

  methods: {
    close() {
      this.$emit('update:modelValue', false)
    },

    needLabel(need) {
      const labels = {
        '生理': '🏠 生理需求',
        '安全': '🛡️ 安全需求',
        '社交': '❤️ 社交需求',
        '尊重': '⭐ 尊重需求',
        '自我实现': '🌟 自我实现',
        safety: '🛡️ 安全需求',
        belonging: '❤️ 社交需求',
        esteem: '⭐ 尊重需求',
        cognitive: '📚 认知需求'
      }
      return labels[need] || need
    },

    behaviorLabel(behavior) {
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
      return labels[behavior] || behavior
    },

    behaviorClass(behavior) {
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
      return classes[behavior] || 'neutral'
    },

    formatJson(data) {
      if (!data) return ''
      return JSON.stringify(data, null, 2)
    }
  }
}
</script>

<style scoped>
.agent-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  z-index: 10000;
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

@keyframes spin {
  to { transform: rotate(360deg); }
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

.trace-block {
  border-color: rgba(96, 165, 250, 0.22);
  background: rgba(15, 23, 42, 0.82);
}

.trace-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border: 0;
  background: rgba(100, 181, 246, 0.05);
  color: inherit;
  text-align: left;
  cursor: pointer;
  list-style: none;
  user-select: none;
}

.trace-toggle::-webkit-details-marker {
  display: none;
}

.trace-toggle::marker {
  content: "";
}

.trace-toggle-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #cbd5e1;
}

.trace-toggle-meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.trace-chevron {
  font-size: 11px;
  color: #93c5fd;
}

.trace-chevron::after {
  content: "展开";
}

.trace-block[open] .trace-chevron::after {
  content: "收起";
}

.trace-summary {
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.6;
  margin-bottom: 10px;
}

.trace-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(96, 165, 250, 0.16);
  color: #93c5fd;
  font-size: 11px;
}

.trace-section {
  margin-top: 12px;
}

.trace-section-title {
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 8px;
}

.trace-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
}

.trace-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 8px 10px;
  background: rgba(30, 41, 59, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 8px;
}

.trace-item .label {
  font-size: 10px;
  color: #94a3b8;
}

.trace-item .value {
  font-size: 12px;
  color: #e2e8f0;
  word-break: break-word;
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
.value.success { color: #4ade80; }
.value.silent-status { color: #a78bfa; font-weight: 600; }
.value.active-status { color: #4ade80; font-weight: 600; }

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

.decision-block {
  border-color: rgba(100, 181, 246, 0.25);
  background: linear-gradient(145deg, rgba(100, 181, 246, 0.05) 0%, rgba(0, 0, 0, 0.3) 100%);
}

.decision-block .block-title {
  background: rgba(100, 181, 246, 0.1);
  color: #60a5fa;
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

.summary-row .value.opinion-change {
  color: #fbbf24;
  font-size: 12px;
}

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
</style>

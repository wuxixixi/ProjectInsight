<template>
  <div v-if="modelValue" class="completion-modal-overlay" @click.self="$emit('update:modelValue', false)">
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
        <button class="btn-completion btn-report" @click="$emit('update:modelValue', false); $emit('generate-report')">
          <span>📄</span> 生成推演报告
        </button>
        <button v-if="useLLM" class="btn-completion btn-intelligence" @click="$emit('update:modelValue', false); $emit('generate-intelligence')" :disabled="reportGenerating">
          <span>🧠</span> {{ reportGenerating ? '撰写中...' : '生成智库专报' }}
        </button>
        <button class="btn-completion btn-later" @click="$emit('update:modelValue', false)">
          稍后查看
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CompletionModal',
  props: {
    modelValue: { type: Boolean, default: false },
    maxSteps: { type: Number, default: 50 },
    prediction: { type: Object, default: null },
    rumorSpreadRate: { type: Number, default: 0 },
    truthAcceptanceRate: { type: Number, default: 0 },
    useLLM: { type: Boolean, default: false },
    reportGenerating: { type: Boolean, default: false }
  },
  emits: ['update:modelValue', 'generate-report', 'generate-intelligence']
}
</script>

<style scoped>
.completion-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  z-index: 350;
  display: flex;
  align-items: center;
  justify-content: center;
}

.completion-modal {
  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 20px;
  padding: 40px;
  max-width: 500px;
  width: 90%;
  text-align: center;
}

.completion-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.completion-title {
  font-size: 24px;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 8px 0;
}

.completion-desc {
  font-size: 14px;
  color: #94a3b8;
  margin: 0 0 24px 0;
}

.completion-stats {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-bottom: 24px;
}

.completion-stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 11px;
  color: #6b7280;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #ef4444;
}

.stat-value.truth {
  color: #22c55e;
}

.risk-low { color: #22c55e; }
.risk-medium { color: #f59e0b; }
.risk-high { color: #ef4444; }
.risk-critical { color: #dc2626; }

.completion-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.btn-completion {
  padding: 12px 24px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-report {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
}

.btn-report:hover {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
}

.btn-intelligence {
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  color: white;
}

.btn-intelligence:hover:not(:disabled) {
  background: linear-gradient(135deg, #7c3aed, #6d28d9);
}

.btn-intelligence:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-later {
  background: transparent;
  color: #94a3b8;
  border-color: rgba(100, 181, 246, 0.2);
}

.btn-later:hover {
  background: rgba(100, 181, 246, 0.1);
}
</style>

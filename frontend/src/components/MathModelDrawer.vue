<template>
  <div v-if="modelValue" class="drawer-overlay" @click.self="close">
    <div class="math-model-drawer">
      <div class="drawer-header">
        <h3>📐 数学模型说明</h3>
        <button class="drawer-close" @click="close">✕</button>
      </div>
      <div class="drawer-body">
        <div v-if="loading" class="loading-container">
          <div class="loading-spinner"></div>
          <p>加载模型说明...</p>
        </div>
        <div v-else-if="explanation" class="math-model-content">
          <h4 class="section-title">🔬 社会心理学机制</h4>
          <div v-for="(theory, key) in explanation.theories" :key="key" class="theory-card">
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
          <h4 class="section-title">🎛️ 参数说明</h4>
          <div class="params-table">
            <div v-for="(param, key) in explanation.parameters" :key="key" class="param-row">
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
</template>

<script>
export default {
  name: 'MathModelDrawer',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    explanation: {
      type: Object,
      default: null
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:modelValue'],
  methods: {
    close() {
      this.$emit('update:modelValue', false);
    }
  }
};
</script>

<style scoped>
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ==================== Shared drawer styles ==================== */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  z-index: var(--z-drawer);
  display: flex;
  justify-content: flex-end;
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

/* ==================== Math model drawer ==================== */
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

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(100, 181, 246, 0.2);
  border-top-color: #60a5fa;
  border-radius: 50%;
  margin: 0 auto 16px;
  animation: spin 1s linear infinite;
}
</style>

<template>
  <div v-if="modelValue" class="intelligence-modal-overlay" @click.self="$emit('update:modelValue', false)">
    <div class="intelligence-modal">
      <div class="intelligence-modal-header">
        <h3>🧠 智库专报</h3>
        <button class="report-close-btn" @click="$emit('update:modelValue', false)">✕</button>
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
        <button class="btn-download-intelligence" @click="$emit('download-intelligence')">📥 导出 Markdown</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'IntelligenceModal',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    reportGenerating: {
      type: Boolean,
      default: false
    },
    intelligenceContent: {
      type: String,
      default: ''
    },
    renderedIntelligence: {
      type: String,
      default: ''
    }
  },
  emits: ['update:modelValue', 'download-intelligence']
}
</script>

<style scoped>
.intelligence-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
}

.intelligence-modal {
  width: 800px;
  max-height: 85vh;
  background: linear-gradient(145deg, #0f172a, #1e1b4b);
  border: 1px solid rgba(100, 181, 246, 0.25);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 0 60px rgba(100, 181, 246, 0.2);
}

.intelligence-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.15);
}

.intelligence-modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

.intelligence-modal-body {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.intelligence-content pre {
  font-family: 'Fira Code', 'Monaco', monospace;
  font-size: 13px;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

.intelligence-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
}

.loading-tip {
  font-size: 12px;
  color: #64748b;
}

.streaming-cursor {
  color: #60a5fa;
  animation: blink 0.8s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.intelligence-modal-footer {
  display: flex;
  justify-content: flex-end;
  padding: 16px 24px;
  border-top: 1px solid rgba(100, 181, 246, 0.15);
}

.btn-download-intelligence {
  padding: 10px 20px;
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-download-intelligence:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
}

.report-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6b7280;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(100, 181, 246, 0.2);
  border-top-color: #60a5fa;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

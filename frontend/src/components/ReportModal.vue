<template>
  <div v-if="modelValue" class="report-modal-overlay" @click.self="$emit('update:modelValue', false)">
    <div class="report-modal">
      <div class="report-modal-header">
        <h3>📄 推演报告</h3>
        <button class="report-close-btn" @click="$emit('update:modelValue', false)">✕</button>
      </div>
      <div class="report-modal-body">
        <div v-if="loading" class="report-loading">
          <div class="loading-spinner"></div>
          <p>加载报告中...</p>
        </div>
        <div v-else-if="content" class="report-content">
          <pre>{{ content }}</pre>
        </div>
        <div v-else class="report-placeholder">
          <p>报告加载失败</p>
        </div>
      </div>
      <div class="report-modal-footer">
        <button class="btn-download" @click="$emit('download')">⬇ 下载报告</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ReportModal',
  props: {
    modelValue: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
    content: { type: String, default: '' },
    filename: { type: String, default: '' }
  },
  emits: ['update:modelValue', 'download']
}
</script>

<style scoped>
.report-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  z-index: 400;
  display: flex;
  align-items: center;
  justify-content: center;
}

.report-modal {
  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 16px;
  width: 80vw;
  max-width: 900px;
  height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.report-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
}

.report-modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

.report-close-btn {
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

.report-close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
  color: #ef4444;
}

.report-modal-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.report-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
}

.report-content pre {
  font-family: 'Fira Code', 'Monaco', monospace;
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
  height: 100%;
  color: #6b7280;
}

.report-modal-footer {
  padding: 12px 20px;
  border-top: 1px solid rgba(100, 181, 246, 0.1);
  display: flex;
  justify-content: flex-end;
}

.btn-download {
  padding: 8px 16px;
  background: rgba(100, 181, 246, 0.15);
  border: 1px solid rgba(100, 181, 246, 0.3);
  border-radius: 8px;
  color: #60a5fa;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.btn-download:hover {
  background: rgba(100, 181, 246, 0.25);
}
</style>

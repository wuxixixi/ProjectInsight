<template>
  <div v-if="modelValue" class="drawer-overlay" @click.self="$emit('update:modelValue', false)">
    <div class="usage-drawer">
      <div class="drawer-header">
        <h3>📋 使用说明</h3>
        <button class="drawer-close" @click="$emit('update:modelValue', false)">✕</button>
      </div>
      <div class="drawer-body">
        <div v-if="loading" class="loading-container">
          <div class="loading-spinner"></div>
          <p>加载使用说明...</p>
        </div>
        <div v-else class="usage-content" v-html="content"></div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'UsageDrawer',
  props: {
    modelValue: { type: Boolean, default: false },
    content: { type: String, default: '' },
    loading: { type: Boolean, default: false }
  },
  emits: ['update:modelValue']
}
</script>

<style scoped>
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  z-index: 200;
  display: flex;
  justify-content: flex-end;
}

.usage-drawer {
  width: 640px;
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

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #94a3b8;
}

/* Markdown 排版 */
.usage-content {
  font-size: 14px;
  line-height: 1.8;
  color: #cbd5e1;
}

.usage-content h1 {
  font-size: 22px;
  font-weight: 700;
  color: #f0abfc;
  margin: 24px 0 16px 0;
  padding-bottom: 10px;
  border-bottom: 2px solid rgba(240, 171, 252, 0.3);
  padding-left: 12px;
  border-radius: 4px 4px 0 0;
}

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

.usage-content h3 {
  font-size: 16px;
  font-weight: 600;
  color: #a78bfa;
  margin: 16px 0 10px 0;
  padding-left: 10px;
}

.usage-content h4 {
  font-size: 14px;
  font-weight: 600;
  color: #818cf8;
  margin: 12px 0 8px 0;
}

.usage-content p {
  margin: 0 0 14px 0;
  line-height: 1.75;
}

.usage-content ul,
.usage-content ol {
  margin: 0 0 14px 0;
  padding-left: 24px;
}

.usage-content li {
  margin-bottom: 6px;
  line-height: 1.7;
}

.usage-content li::marker {
  color: #60a5fa;
}

.usage-content strong {
  color: #e2e8f0;
  font-weight: 600;
}

.usage-content a {
  color: #60a5fa;
  text-decoration: none;
  border-bottom: 1px solid rgba(96, 165, 250, 0.3);
  transition: all 0.2s;
}

.usage-content a:hover {
  color: #93c5fd;
  border-bottom-color: #93c5fd;
}

.usage-content code {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(100, 181, 246, 0.15);
  border-radius: 4px;
  padding: 2px 6px;
  font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
  font-size: 13px;
  color: #a5b4fc;
}

.usage-content pre {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(100, 181, 246, 0.15);
  border-radius: 8px;
  padding: 16px;
  margin: 0 0 16px 0;
  overflow-x: auto;
}

.usage-content pre code {
  background: none;
  border: none;
  padding: 0;
  font-size: 13px;
  color: #e2e8f0;
  line-height: 1.6;
}

.usage-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 16px 0;
  font-size: 13px;
}

.usage-content thead th {
  background: rgba(30, 41, 59, 0.6);
  color: #e2e8f0;
  font-weight: 600;
  text-align: left;
  padding: 10px 12px;
  border-bottom: 2px solid rgba(100, 181, 246, 0.2);
}

.usage-content tbody td {
  padding: 8px 12px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.08);
  color: #cbd5e1;
}

.usage-content tbody tr:hover {
  background: rgba(100, 181, 246, 0.05);
}

.usage-content blockquote {
  margin: 0 0 14px 0;
  padding: 12px 16px;
  border-left: 3px solid #60a5fa;
  background: rgba(96, 165, 250, 0.08);
  border-radius: 0 6px 6px 0;
  color: #94a3b8;
}

.usage-content hr {
  border: none;
  border-top: 1px solid rgba(100, 181, 246, 0.15);
  margin: 20px 0;
}

.usage-content img {
  max-width: 100%;
  border-radius: 8px;
}
</style>

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
</style>

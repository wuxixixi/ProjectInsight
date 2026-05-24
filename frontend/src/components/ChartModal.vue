<template>
  <div v-if="modelValue" class="chart-modal-overlay" @click.self="$emit('update:modelValue', false)">
    <div class="chart-modal">
      <div class="chart-modal-header">
        <h3>{{ title }}</h3>
        <button class="modal-close-btn" @click="$emit('update:modelValue', false)">✕</button>
      </div>
      <div ref="modalBody" class="chart-modal-body"></div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChartModal',
  props: {
    modelValue: {
      type: Boolean,
      required: true
    },
    title: {
      type: String,
      default: ''
    }
  },
  emits: ['update:modelValue'],
  expose: ['modalBody'],
  computed: {
    modalBody() {
      return this.$refs.modalBody
    }
  }
}
</script>

<style scoped>
.chart-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.9);
  backdrop-filter: blur(8px);
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-modal {
  width: 90vw;
  height: 85vh;
  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chart-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
}

.chart-modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
}

.modal-close-btn {
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

.modal-close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
  color: #ef4444;
}

.chart-modal-body {
  flex: 1;
  padding: 20px;
}
</style>

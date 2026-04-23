<template>
  <div :class="['kpi-card', cardClass, { clickable: clickable }]" @click="handleClick">
    <div class="kpi-icon">{{ icon }}</div>
    <div class="kpi-content">
      <span class="kpi-label">{{ label }}</span>
      <span class="kpi-value">
        {{ prefix }}{{ formattedValue }}{{ suffix }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  value: { type: [Number, String], required: true },
  suffix: { type: String, default: '' },
  prefix: { type: String, default: '' },
  type: { type: String, default: 'default' }, // default, danger, success, info, warning, purple, knowledge
  clickable: { type: Boolean, default: false }
})

const emit = defineEmits(['click'])

const formattedValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value.toFixed(props.value % 1 === 0 ? 0 : 1)
  }
  return props.value
})

const cardClass = computed(() => {
  if (props.type === 'danger') return 'danger'
  if (props.type === 'success') return 'success'
  if (props.type === 'info') return 'info'
  if (props.type === 'warning') return 'warning'
  if (props.type === 'purple') return 'purple'
  if (props.type === 'knowledge') return 'knowledge'
  return ''
})

const handleClick = () => {
  if (props.clickable) {
    emit('click')
  }
}
</script>

<style scoped>
.kpi-card {
  background: rgba(30, 30, 50, 0.8);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.3s;
  border: 1px solid rgba(100, 100, 150, 0.2);
}

.kpi-card.clickable {
  cursor: pointer;
}

.kpi-card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.kpi-icon {
  font-size: 20px;
}

.kpi-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-label {
  font-size: 11px;
  color: #90caf9;
}

.kpi-value {
  font-size: 18px;
  font-weight: bold;
  color: #fff;
}

.kpi-value small {
  font-size: 11px;
  color: #aaa;
}

/* 类型样式 */
.kpi-card.danger {
  border-color: rgba(244, 67, 54, 0.4);
}

.kpi-card.danger .kpi-value {
  color: #f44336;
}

.kpi-card.success {
  border-color: rgba(76, 175, 80, 0.4);
}

.kpi-card.success .kpi-value {
  color: #4caf50;
}

.kpi-card.info {
  border-color: rgba(33, 150, 243, 0.4);
}

.kpi-card.info .kpi-value {
  color: #2196f3;
}

.kpi-card.warning {
  border-color: rgba(255, 152, 0, 0.4);
}

.kpi-card.warning .kpi-value {
  color: #ff9800;
}

.kpi-card.purple {
  border-color: rgba(156, 39, 176, 0.4);
}

.kpi-card.purple .kpi-value {
  color: #9c27b0;
}

.kpi-card.knowledge {
  border-color: rgba(0, 188, 212, 0.4);
}

.kpi-card.knowledge .kpi-value {
  color: #00bcd4;
}

/* 响应式 */
@media screen and (max-width: 1024px) {
  .kpi-card {
    padding: 10px;
  }

  .kpi-value {
    font-size: 16px;
  }
}

@media screen and (max-width: 480px) {
  .kpi-card {
    padding: 6px;
    gap: 6px;
  }

  .kpi-icon {
    font-size: 16px;
  }

  .kpi-label {
    font-size: 10px;
  }

  .kpi-value {
    font-size: 14px;
  }
}
</style>
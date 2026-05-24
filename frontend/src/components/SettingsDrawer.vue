<template>
  <div v-if="modelValue" class="drawer-overlay" @click.self="$emit('update:modelValue', false)">
    <div class="settings-drawer">
      <div class="drawer-header">
        <h3>⚙️ 高级设置</h3>
        <button class="drawer-close" @click="$emit('update:modelValue', false)">✕</button>
      </div>
      <div class="drawer-body">
        <h4 class="drawer-section-title">推演 LLM</h4>

        <div class="setting-item">
          <div class="setting-header">
            <span class="setting-label">模型名称</span>
          </div>
          <input
            :value="simulationLlm.model"
            @input="updateSimulationLlm('model', $event.target.value)"
            class="settings-input"
            :disabled="isRunning || settingsSaving"
            placeholder="如 DeepSeek-V3.2"
          />
          <p class="setting-desc">用于推演决策与事件解析</p>
        </div>

        <div class="setting-item">
          <div class="setting-header">
            <span class="setting-label">Base URL</span>
          </div>
          <input
            :value="simulationLlm.base_url"
            @input="updateSimulationLlm('base_url', $event.target.value)"
            class="settings-input"
            :disabled="isRunning || settingsSaving"
            placeholder="http://host:port/v1"
          />
        </div>

        <div class="setting-item">
          <div class="setting-header">
            <span class="setting-label">API Key</span>
          </div>
          <input
            :value="simulationLlm.api_key"
            @input="updateSimulationLlm('api_key', $event.target.value)"
            class="settings-input"
            :disabled="isRunning || settingsSaving"
            placeholder="sk-..."
          />
        </div>

        <h4 class="drawer-section-title">专报 LLM</h4>

        <div class="setting-item">
          <div class="setting-header">
            <span class="setting-label">模型名称</span>
          </div>
          <input
            :value="reportLlm.model"
            @input="updateReportLlm('model', $event.target.value)"
            class="settings-input"
            :disabled="isRunning || settingsSaving"
            placeholder="如 DeepSeek-R1-0528-64k"
          />
          <p class="setting-desc">用于智库专报生成</p>
        </div>

        <div class="setting-item">
          <div class="setting-header">
            <span class="setting-label">Base URL</span>
          </div>
          <input
            :value="reportLlm.base_url"
            @input="updateReportLlm('base_url', $event.target.value)"
            class="settings-input"
            :disabled="isRunning || settingsSaving"
            placeholder="http://host:port/v1"
          />
        </div>

        <div class="setting-item">
          <div class="setting-header">
            <span class="setting-label">API Key</span>
          </div>
          <input
            :value="reportLlm.api_key"
            @input="updateReportLlm('api_key', $event.target.value)"
            class="settings-input"
            :disabled="isRunning || settingsSaving"
            placeholder="sk-..."
          />
        </div>

        <h4 class="drawer-section-title">LLM 并发配置</h4>

        <div class="setting-item">
          <div class="setting-header">
            <span class="setting-label">并发数上限</span>
            <span class="setting-value">{{ maxConcurrent }}</span>
          </div>
          <input type="range" :value="maxConcurrent" @input="$emit('update:maxConcurrent', Number($event.target.value))" min="50" max="500" step="50" :disabled="isRunning" />
          <p class="setting-desc">同时请求LLM的Agent数量</p>
        </div>

        <div class="setting-item">
          <div class="setting-header">
            <span class="setting-label">连接池大小</span>
            <span class="setting-value">{{ connectionPoolSize }}</span>
          </div>
          <input type="range" :value="connectionPoolSize" @input="$emit('update:connectionPoolSize', Number($event.target.value))" min="100" max="800" step="100" :disabled="isRunning" />
          <p class="setting-desc">应大于并发数上限</p>
        </div>

        <div class="setting-item">
          <div class="setting-header">
            <span class="setting-label">请求超时</span>
            <span class="setting-value">{{ timeout }} 秒</span>
          </div>
          <input type="range" :value="timeout" @input="$emit('update:timeout', Number($event.target.value))" min="30" max="120" step="10" :disabled="isRunning" />
          <p class="setting-desc">单个请求最长等待时间</p>
        </div>

        <div class="setting-item">
          <div class="setting-header">
            <span class="setting-label">最大重试次数</span>
            <span class="setting-value">{{ maxRetries }} 次</span>
          </div>
          <input type="range" :value="maxRetries" @input="$emit('update:maxRetries', Number($event.target.value))" min="1" max="10" step="1" :disabled="isRunning" />
          <p class="setting-desc">失败后自动重试</p>
        </div>

        <div class="setting-item">
          <div class="setting-header">
            <span class="setting-label">推演间隔</span>
            <span class="setting-value">{{ autoInterval / 1000 }} 秒</span>
          </div>
          <input type="range" :value="autoInterval" @input="$emit('update:autoInterval', Number($event.target.value))" min="1000" max="10000" step="1000" :disabled="isRunning" />
          <p class="setting-desc">LLM模式建议3秒以上</p>
        </div>

        <div class="settings-actions">
          <button class="btn-settings-secondary" @click="$emit('reload')" :disabled="settingsSaving">重新加载</button>
          <button class="btn-settings-primary" @click="$emit('save')" :disabled="isRunning || settingsSaving">保存设置</button>
        </div>
        <p v-if="settingsMessage" class="settings-message">{{ settingsMessage }}</p>
        <p v-if="settingsError" class="settings-error">{{ settingsError }}</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SettingsDrawer',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    simulationLlm: {
      type: Object,
      default: () => ({ model: '', base_url: '', api_key: '' })
    },
    reportLlm: {
      type: Object,
      default: () => ({ model: '', base_url: '', api_key: '' })
    },
    maxConcurrent: {
      type: Number,
      default: 100
    },
    connectionPoolSize: {
      type: Number,
      default: 200
    },
    timeout: {
      type: Number,
      default: 60
    },
    maxRetries: {
      type: Number,
      default: 3
    },
    autoInterval: {
      type: Number,
      default: 2000
    },
    isRunning: {
      type: Boolean,
      default: false
    },
    settingsSaving: {
      type: Boolean,
      default: false
    },
    settingsMessage: {
      type: String,
      default: ''
    },
    settingsError: {
      type: String,
      default: ''
    }
  },
  emits: [
    'update:modelValue',
    'update:simulationLlm',
    'update:reportLlm',
    'update:maxConcurrent',
    'update:connectionPoolSize',
    'update:timeout',
    'update:maxRetries',
    'update:autoInterval',
    'reload',
    'save'
  ],
  methods: {
    updateSimulationLlm(key, value) {
      const updated = { ...this.simulationLlm, [key]: value }
      this.$emit('update:simulationLlm', updated)
    },
    updateReportLlm(key, value) {
      const updated = { ...this.reportLlm, [key]: value }
      this.$emit('update:reportLlm', updated)
    }
  }
}
</script>

<style scoped>
.drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
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

.settings-input {
  width: 100%;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(100, 181, 246, 0.18);
  border-radius: 8px;
  padding: 10px 12px;
  color: #e2e8f0;
  font-size: 13px;
}

.settings-input:focus {
  outline: none;
  border-color: rgba(96, 165, 250, 0.5);
  box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.12);
}

.settings-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.setting-desc {
  font-size: 11px;
  color: #6b7280;
  margin-top: 8px;
}

.settings-actions {
  display: flex;
  gap: 12px;
  margin-top: 18px;
}

.btn-settings-primary,
.btn-settings-secondary {
  flex: 1;
  border: none;
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-settings-primary {
  background: linear-gradient(135deg, #2563eb 0%, #60a5fa 100%);
  color: #eff6ff;
}

.btn-settings-secondary {
  background: rgba(30, 41, 59, 0.9);
  color: #cbd5e1;
  border: 1px solid rgba(100, 181, 246, 0.18);
}

.btn-settings-primary:hover:not(:disabled),
.btn-settings-secondary:hover:not(:disabled) {
  transform: translateY(-1px);
}

.btn-settings-primary:disabled,
.btn-settings-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.settings-message,
.settings-error {
  margin-top: 12px;
  font-size: 12px;
  line-height: 1.5;
}

.settings-message {
  color: #86efac;
}

.settings-error {
  color: #fca5a5;
}
</style>

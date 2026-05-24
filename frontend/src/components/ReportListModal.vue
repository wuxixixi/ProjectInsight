<template>
  <div v-if="modelValue" class="report-modal-overlay" @click.self="$emit('update:modelValue', false)">
    <div class="report-modal report-modal-enhanced">
      <div class="report-modal-header">
        <h3>📚 历史报告</h3>
        <button class="report-close-btn" @click="$emit('update:modelValue', false)">✕</button>
      </div>
      <div class="report-modal-body">
        <div v-if="reportListLoading" class="report-loading">
          <div class="loading-spinner"></div>
          <p>加载报告列表...</p>
        </div>
        <template v-else>
          <!-- 搜索和排序工具栏 -->
          <div class="report-toolbar">
            <div class="report-search-box">
              <input
                type="text"
                :value="reportSearchKeyword"
                @input="$emit('update:reportSearchKeyword', $event.target.value); $emit('search-input')"
                placeholder="搜索报告..."
                class="report-search-input"
              />
              <span class="report-search-icon">🔍</span>
            </div>
            <div class="report-sort-btns">
              <button
                :class="['sort-btn', { active: reportSortBy === 'modified' }]"
                @click="$emit('change-sort', 'modified')"
                title="按时间排序">
                🕐 {{ reportSortBy === 'modified' ? (reportSortOrder === 'desc' ? '↓' : '↑') : '' }}
              </button>
              <button
                :class="['sort-btn', { active: reportSortBy === 'size' }]"
                @click="$emit('change-sort', 'size')"
                title="按大小排序">
                📊 {{ reportSortBy === 'size' ? (reportSortOrder === 'desc' ? '↓' : '↑') : '' }}
              </button>
              <button
                :class="['sort-btn', { active: reportSortBy === 'name' }]"
                @click="$emit('change-sort', 'name')"
                title="按名称排序">
                🔤 {{ reportSortBy === 'name' ? (reportSortOrder === 'desc' ? '↓' : '↑') : '' }}
              </button>
            </div>
          </div>

          <!-- 报告统计 -->
          <div class="report-stats">
            共 <strong>{{ reportCounts.total }}</strong> 份报告
            （推演 <strong>{{ reportCounts.simulation }}</strong> 份，
            智库专报 <strong>{{ reportCounts.intelligence }}</strong> 份）
          </div>

          <!-- 双栏布局 -->
          <div class="report-columns">
            <!-- 左栏：推演报告 -->
            <div class="report-column">
              <div class="column-header">
                <span class="column-icon">📄</span>
                <span class="column-title">推演报告</span>
                <span class="column-count">{{ simulationReports.length }}</span>
              </div>
              <div class="column-body">
                <div v-if="simulationReports.length > 0" class="report-list">
                  <div
                    v-for="report in simulationReports"
                    :key="report.filename"
                    class="report-item"
                    @click="$emit('view-report', report)">
                    <div class="report-item-icon">📄</div>
                    <div class="report-item-info">
                      <div class="report-item-name">{{ report.filename }}</div>
                      <div class="report-item-meta">{{ formatFileSize(report.size) }} · {{ formatDate(report.modified) }}</div>
                    </div>
                    <div class="report-item-action">查看</div>
                  </div>
                </div>
                <div v-else class="report-placeholder">
                  <p>暂无推演报告</p>
                </div>
              </div>
            </div>

            <!-- 右栏：智库专报 -->
            <div class="report-column">
              <div class="column-header">
                <span class="column-icon">🧠</span>
                <span class="column-title">智库专报</span>
                <span class="column-count">{{ intelligenceReports.length }}</span>
              </div>
              <div class="column-body">
                <div v-if="intelligenceReports.length > 0" class="report-list">
                  <div
                    v-for="report in intelligenceReports"
                    :key="report.filename"
                    class="report-item report-item-intelligence"
                    @click="$emit('view-report', report)">
                    <div class="report-item-icon">🧠</div>
                    <div class="report-item-info">
                      <div class="report-item-name">{{ report.filename }}</div>
                      <div class="report-item-meta">{{ formatFileSize(report.size) }} · {{ formatDate(report.modified) }}</div>
                    </div>
                    <div class="report-item-action">查看</div>
                  </div>
                </div>
                <div v-else class="report-placeholder">
                  <p>暂无智库专报</p>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ReportListModal',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    reportListLoading: {
      type: Boolean,
      default: false
    },
    reportSearchKeyword: {
      type: String,
      default: ''
    },
    reportSortBy: {
      type: String,
      default: 'modified'
    },
    reportSortOrder: {
      type: String,
      default: 'desc'
    },
    reportCounts: {
      type: Object,
      default: () => ({ total: 0, simulation: 0, intelligence: 0 })
    },
    simulationReports: {
      type: Array,
      default: () => []
    },
    intelligenceReports: {
      type: Array,
      default: () => []
    }
  },
  emits: [
    'update:modelValue',
    'update:reportSearchKeyword',
    'search-input',
    'change-sort',
    'view-report'
  ],
  methods: {
    formatFileSize(bytes) {
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / 1024 / 1024).toFixed(1) + ' MB'
    },
    formatDate(timestamp) {
      const date = new Date(timestamp * 1000)
      return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
  }
}
</script>

<style scoped>
.report-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  z-index: var(--z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
}

.report-modal {
  width: 700px;
  max-height: 85vh;
  background: linear-gradient(145deg, #0f172a, #1e1b4b);
  border: 1px solid rgba(100, 181, 246, 0.25);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 0 60px rgba(100, 181, 246, 0.2);
}

.report-modal-enhanced {
  width: 900px;
  max-height: 80vh;
}

.report-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(100, 181, 246, 0.1);
  border-bottom: 1px solid rgba(100, 181, 246, 0.15);
}

.report-modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #60a5fa;
}

.report-close-btn {
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

.report-close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
  color: #ef4444;
}

.report-modal-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  min-height: 300px;
}

.report-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #6b7280;
}

.report-loading .loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(100, 181, 246, 0.2);
  border-top-color: #60a5fa;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.report-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 10px;
  margin-bottom: 16px;
}

.report-search-box {
  flex: 1;
  position: relative;
}

.report-search-input {
  width: 100%;
  padding: 8px 12px 8px 36px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 13px;
  outline: none;
  transition: all 0.2s;
}

.report-search-input:focus {
  border-color: rgba(100, 181, 246, 0.5);
  background: rgba(0, 0, 0, 0.4);
}

.report-search-input::placeholder {
  color: #6b7280;
}

.report-search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 14px;
  pointer-events: none;
}

.report-sort-btns {
  display: flex;
  gap: 6px;
}

.sort-btn {
  padding: 6px 10px;
  background: rgba(100, 181, 246, 0.1);
  border: 1px solid rgba(100, 181, 246, 0.2);
  border-radius: 6px;
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 36px;
}

.sort-btn:hover {
  background: rgba(100, 181, 246, 0.2);
  color: #e2e8f0;
}

.sort-btn.active {
  background: rgba(100, 181, 246, 0.25);
  border-color: rgba(100, 181, 246, 0.4);
  color: #60a5fa;
}

.report-stats {
  padding: 8px 12px;
  background: rgba(100, 181, 246, 0.08);
  border-radius: 6px;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 16px;
}

.report-stats strong {
  color: #60a5fa;
  font-weight: 600;
}

.report-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.report-column {
  display: flex;
  flex-direction: column;
  background: rgba(30, 41, 59, 0.3);
  border-radius: 10px;
  border: 1px solid rgba(100, 181, 246, 0.1);
  overflow: hidden;
}

.column-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(100, 181, 246, 0.1);
  border-bottom: 1px solid rgba(100, 181, 246, 0.1);
}

.column-icon {
  font-size: 16px;
}

.column-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  flex: 1;
}

.column-count {
  padding: 2px 8px;
  background: rgba(100, 181, 246, 0.2);
  border-radius: 10px;
  font-size: 11px;
  color: #60a5fa;
}

.column-body {
  flex: 1;
  padding: 12px;
  max-height: 350px;
  overflow-y: auto;
}

.column-body .report-list {
  max-height: none;
}

.column-body .report-placeholder {
  height: 150px;
}

.report-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.report-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(100, 181, 246, 0.15);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.report-item:hover {
  background: rgba(100, 181, 246, 0.1);
  border-color: rgba(100, 181, 246, 0.3);
}

.report-item-intelligence {
  border-color: rgba(168, 85, 247, 0.2);
}

.report-item-intelligence:hover {
  background: rgba(168, 85, 247, 0.1);
  border-color: rgba(168, 85, 247, 0.3);
}

.report-item-icon {
  font-size: 24px;
}

.report-item-info {
  flex: 1;
}

.report-item-name {
  font-size: 13px;
  color: #e2e8f0;
  font-weight: 500;
}

.report-item-meta {
  font-size: 11px;
  color: #6b7280;
  margin-top: 2px;
}

.report-item-action {
  font-size: 12px;
  color: #60a5fa;
  padding: 4px 12px;
  background: rgba(100, 181, 246, 0.15);
  border-radius: 4px;
}

.report-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #6b7280;
}
</style>

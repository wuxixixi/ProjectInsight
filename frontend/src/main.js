/**
 * Vue 应用入口
 * Ascend 环境运行提示:
 *   1. cd frontend
 *   2. npm install
 *   3. npm run dev
 */
import { createApp } from 'vue'
import App from './App.vue'
import './assets/main.css'

createApp(App).mount('#app')

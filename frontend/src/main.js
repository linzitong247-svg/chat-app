import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'

// 定义路由配置数组
const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('./components/Chat.vue'),
    meta: { welcome: true }
  },
  {
    path: '/chat/:id',
    name: 'Chat',
    component: () => import('./components/Chat.vue'),
    props: (route) => ({ id: Number(route.params.id) })
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes
})

// 创建 Vue 应用实例
const app = createApp(App)

// 全局注册 Element Plus 所有图标组件
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 安装插件 (安装插件的本质：把路由实例 “注入” 到 Vue 应用中)
app.use(ElementPlus)
app.use(router)

// 挂载应用到DOM
app.mount('#app')
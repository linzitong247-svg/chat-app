<template>
  <div class="app-container">
    <!-- 展开按钮 (侧边栏收起时显示) -->
    <div v-if="sidebarCollapsed" class="expand-section">
      <button class="sidebar-expand-btn" @click="sidebarCollapsed = false" title="展开侧边栏">
        <el-icon size="18"><Expand /></el-icon>
      </button>
      <div class="expand-divider"></div>
    </div>

    <el-container>
      <!-- 侧边栏 -->
      <el-aside :width="sidebarCollapsed ? '0px' : '300px'" class="sidebar">
        <div class="logo" v-show="!sidebarCollapsed" @click="goHome" role="button" tabindex="0">
          <div class="logo-seal">智</div>
          <div class="logo-label">
            <span class="logo-text">智言 · 企业智库</span>
            <span class="logo-ver">V2.0</span>
          </div>
          <!-- 折叠按钮 -->
          <button class="logo-collapse-btn" @click.stop="sidebarCollapsed = true" title="收起侧边栏">
            <el-icon size="16"><Fold /></el-icon>
          </button>
        </div>

        <!-- 选项卡切换 -->
        <div class="sidebar-tabs" v-show="!sidebarCollapsed">
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'chat' }"
            @click="switchTab('chat')"
          >
            对话
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'knowledge' }"
            @click="switchTab('knowledge')"
          >
            知识库
          </button>
        </div>

        <!-- 组件切换 -->
        <History ref="historyRef" v-show="!sidebarCollapsed && activeTab === 'chat'" />
        <Knowledge v-show="!sidebarCollapsed && activeTab === 'knowledge'" />
      </el-aside>

      <!-- 主内容区 -->
      <el-main>
        <!-- 欢迎页 -->
        <div v-if="showWelcome" class="welcome-page">
          <div class="welcome-content">
            <div class="welcome-logo">
              <div class="welcome-seal">智</div>
              <h1 class="welcome-title">智言 · 企业智库</h1>
              <p class="welcome-subtitle">博观而约取，厚积而薄发</p>
            </div>

            <div class="suggestion-cards">
              <button
                v-for="(suggestion, index) in suggestions"
                :key="index"
                class="suggestion-card"
                :style="{ animationDelay: 0.6 + index * 0.1 + 's' }"
                @click="handleSuggestion(suggestion.text)"
              >
                <span class="suggestion-text">{{ suggestion.text }}</span>
                <el-icon class="suggestion-arrow" aria-hidden="true"><Right /></el-icon>
              </button>
            </div>
          </div>
        </div>

        <!-- 路由视图 -->
        <router-view v-else />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import History from './components/History.vue'
import Knowledge from './components/Knowledge.vue'

const route = useRoute()
const router = useRouter()
const historyRef = ref(null)
const sidebarCollapsed = ref(false)

// 选项卡状态
const activeTab = ref('chat') // 'chat' | 'knowledge'

const switchTab = (tab) => {
  activeTab.value = tab
}

const goHome = () => {
  // 如果当前在聊天页面，导航回欢迎页
  if (route.params.id) {
    router.push({ name: 'Home' })
    // 切换到对话选项卡
    activeTab.value = 'chat'
  }
}

const refreshHistory = () => {
  if (historyRef.value?.loadConversations) {
    historyRef.value.loadConversations()
  }
}
provide('refreshHistory', refreshHistory)

const showWelcome = computed(() => {
  return !route.params.id
})

const suggestions = [
  { text: '公司年假有几天？' },
  { text: '如何申请报销流程？' },
  { text: '新员工入职需要准备什么？' },
  { text: '公司有哪些福利政策？' }
]

const handleSuggestion = async (text) => {
  try {
    const axios = (await import('axios')).default
    const response = await axios.post('/api/conversations', { title: '新对话' })
    const conversationId = response.data.id
    router.push({ path: `/chat/${conversationId}`, query: { prefill: text } })
    if (historyRef.value?.loadConversations) {
      setTimeout(() => historyRef.value.loadConversations(), 300)
    }
  } catch (err) {
    console.error('创建对话失败:', err)
  }
}
</script>

<style scoped>
/* ===== Design Tokens ===== */
.app-container {
  --ink-900: #0f1419;
  --ink-800: #1a1f27;
  --ink-700: #2c333d;
  --ink-600: #3d4654;
  --ink-400: #6b7685;
  --ink-200: #a8b0bb;
  --gold-500: #c9a96e;
  --gold-400: #d4ba85;
  --gold-300: #e0cc9f;
  --gold-600: #a8893e;
  --jade-500: #6A8C9E;
  --jade-400: #84A3B3;
  --jade-600: #567A8A;
  --rust-500: #B5694D;
  --rust-400: #C8826A;
  --rust-600: #9A5540;
  --cream-50: #faf8f5;
  --cream-100: #f3efe8;
  --cream-200: #e8e2d8;
  --warm-white: #fdfcfa;
  --font-display: 'Noto Serif SC', 'Songti SC', serif;
  --font-body: 'DM Sans', 'PingFang SC', sans-serif;

  height: 100vh;
  font-family: var(--font-body);
}

.el-container {
  height: 100%;
}

/* ===== Sidebar ===== */
.sidebar {
  background: var(--ink-900);
  border-right: 1px solid rgba(201, 169, 110, 0.08);
  transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

/* Logo */
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 14px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  cursor: pointer;
  transition: background-color 0.2s;
  position: relative;
}

.logo:hover {
  background: rgba(255,255,255,0.04);
}

.logo:hover .logo-seal {
  box-shadow: 0 2px 12px rgba(201, 169, 110, 0.45);
}

/* Logo 右侧折叠按钮 */
.logo-collapse-btn {
  margin-left: auto;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.4);
  transition: all 0.2s;
  flex-shrink: 0;
}

.logo-collapse-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.7);
}

.logo-seal {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  background: var(--gold-500);
  color: var(--ink-900);
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(201, 169, 110, 0.3);
}

.logo-label {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.logo-text {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  color: var(--cream-100);
  letter-spacing: 1.5px;
  white-space: nowrap;
}

.logo-ver {
  font-size: 10px;
  color: var(--jade-500);
  letter-spacing: 2px;
  text-transform: uppercase;
}

/* ===== 选项卡切换 ===== */
.sidebar-tabs {
  display: flex;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding: 0 12px;
}

.tab-btn {
  flex: 1;
  padding: 10px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.45);
  font-size: 14px;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
}

.tab-btn:hover {
  color: rgba(255, 255, 255, 0.7);
}

.tab-btn.active {
  color: var(--gold-500);
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 20%;
  right: 20%;
  height: 2px;
  background: var(--gold-500);
}

/* ===== Main Area ===== */
.el-main {
  padding: 0;
  background: var(--cream-50);
  position: relative;
}

/* 展开按钮 (侧边栏收起时显示) */
.expand-section {
  position: fixed;
  top: 16px;
  left: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 1000;
  height: 32px;
  pointer-events: none;
}

.sidebar-expand-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-400);
  transition: all 0.2s;
  flex-shrink: 0;
  pointer-events: auto;
}

.sidebar-expand-btn:hover {
  background: rgba(0, 0, 0, 0.04);
  color: var(--ink-700);
  border-color: var(--gold-400);
}

.expand-divider {
  width: 1px;
  height: 32px;
  background: rgba(0, 0, 0, 0.08);
  pointer-events: none;
}

/* ===== Welcome Page ===== */
.welcome-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  /* 亚麻纹理底 */
  background-color: #EDE8DD;
  background-image:
    /* 不规则透明度渐变 */
    radial-gradient(ellipse at 12% 20%, rgba(201,169,110,0.10) 0%, transparent 50%),
    radial-gradient(ellipse at 85% 65%, rgba(201,169,110,0.08) 0%, transparent 45%),
    radial-gradient(ellipse at 50% 90%, rgba(180,160,120,0.07) 0%, transparent 40%),
    radial-gradient(ellipse at 70% 10%, rgba(160,140,100,0.06) 0%, transparent 35%),
    /* 亚麻十字交织纹理 */
    repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(120,100,65,0.08) 2px, rgba(120,100,65,0.08) 3px),
    repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(120,100,65,0.06) 2px, rgba(120,100,65,0.06) 3px);
}

.welcome-content {
  text-align: center;
  max-width: 580px;
  padding: 40px 20px;
  position: relative;
  z-index: 1;
}

.welcome-logo {
  margin-bottom: 56px;
  animation: welcomeFadeUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.welcome-seal {
  width: 72px;
  height: 72px;
  border-radius: 16px;
  background: var(--ink-900);
  color: var(--gold-500);
  font-family: var(--font-display);
  font-size: 36px;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 28px;
  box-shadow:
    0 4px 24px rgba(15, 20, 25, 0.15),
    inset 0 1px 0 rgba(201, 169, 110, 0.1);
}

.welcome-title {
  font-family: var(--font-display);
  font-size: 34px;
  font-weight: 900;
  color: var(--ink-900);
  margin: 0 0 14px;
  letter-spacing: 3px;
}

.welcome-subtitle {
  font-family: var(--font-display);
  font-size: 15px;
  color: var(--jade-500);
  margin: 0;
  letter-spacing: 4px;
  font-weight: 400;
}

/* Suggestion cards */
.suggestion-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.suggestion-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 22px;
  background: var(--warm-white);
  border-radius: 10px;
  border: 1px solid var(--cream-200);
  cursor: pointer;
  transition: border-color 0.25s, background-color 0.25s, box-shadow 0.25s, transform 0.25s;
  font-size: 14px;
  color: var(--ink-700);
  opacity: 0;
  animation: cardSlideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.suggestion-card:hover {
  border-color: var(--gold-400);
  background: white;
  box-shadow: 0 4px 20px rgba(201, 169, 110, 0.1);
  transform: translateX(4px);
}

.suggestion-card:hover .suggestion-arrow {
  color: var(--gold-500);
  transform: translateX(3px);
}

.suggestion-text {
  font-family: var(--font-body);
}

.suggestion-arrow {
  color: var(--ink-200);
  transition: color 0.25s, transform 0.25s;
  flex-shrink: 0;
}

@keyframes welcomeFadeUp {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes cardSlideUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Respect motion preferences */
@media (prefers-reduced-motion: reduce) {
  .sidebar { transition: none; }
  .suggestion-card { animation: none; opacity: 1; transition: none; }
  .welcome-logo { animation: none; }
}
</style>

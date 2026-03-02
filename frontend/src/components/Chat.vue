<template>
  <div class="chat-container">
    <!-- 对话信息头 -->
    <div class="chat-header">
      <h1 class="chat-title">{{ conversationTitle }}</h1>
      <span class="chat-time">{{ formatCreatedAt(conversationCreatedAt) }}</span>
    </div>

    <!-- 聊天区域 -->
    <div class="chat-messages" ref="messageContainer" @scroll="handleScroll">
      <div
        v-for="(msg, index) in messages"
        :key="msg.timestamp + '-' + index"
        :class="['message', msg.role, { 'slide-in-right': msg.role === 'user', 'slide-in-left': msg.role === 'assistant' }]"
        :style="{ animationDelay: index * 0.05 + 's' }"
      >
        <div class="message-avatar">
          <div :class="msg.role === 'user' ? 'avatar-user' : 'avatar-ai'">
            {{ msg.role === 'user' ? '我' : '智' }}
          </div>
        </div>
        <div class="message-content" @mouseenter="hoveredMsg = index" @mouseleave="hoveredMsg = -1">
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="message-text user-bubble">{{ msg.content }}</div>
          <!-- AI 消息 -->
          <div v-else class="message-text ai-bubble">
            <div class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
          </div>
          <!-- 复制按钮 (AI 消息) -->
          <Transition name="fade">
            <button
              v-show="hoveredMsg === index && msg.role === 'assistant'"
              class="copy-msg-btn"
              @click="copyText(msg.content, $event)"
            >
              {{ copiedIndex === index ? '已复制' : '复制' }}
            </button>
          </Transition>
          <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="isLoading" class="message assistant slide-in-left">
        <div class="message-avatar">
          <div class="avatar-ai">智</div>
        </div>
        <div class="message-content">
          <div class="message-text ai-bubble">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 回到最新按钮 -->
    <Transition name="bounce">
      <button v-show="showScrollBtn" class="scroll-bottom-btn" @click="scrollToBottom">
        <el-icon><ArrowDown /></el-icon>
      </button>
    </Transition>

    <!-- 输入区域 -->
    <div class="chat-input">
      <div class="input-container">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="2"
          placeholder="有什么想问的..."
          @keydown.enter.exact.prevent="sendMessage"
          :disabled="isLoading"
          resize="none"
        />
        <div class="input-actions">
          <div class="knowledge-toggle">
            <el-switch
              v-model="useKnowledge"
              active-text="知识库"
              inactive-text="自由"
              size="small"
              :active-color="'#c9a96e'"
            />
          </div>
          <el-button class="send-btn" @click="sendMessage" :loading="isLoading">
            <el-icon v-if="!isLoading"><Promotion /></el-icon>
            发送
          </el-button>
        </div>
      </div>
    </div>

    <!-- 错误提示 -->
    <el-alert
      v-if="error"
      title="发送失败"
      :description="error"
      type="error"
      show-icon
      closable
      @close="error = ''"
      class="error-alert"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import MarkdownIt from 'markdown-it'

const refreshHistory = inject('refreshHistory', () => {})

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })

md.renderer.rules.fence = function(tokens, idx) {
  const token = tokens[idx]
  const code = token.content
  const escapedCode = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  const lang = token.info ? token.info.trim() : ''

  return `<div class="code-block-wrapper">
    <div class="code-block-header">
      <span class="code-lang">${lang}</span>
      <button class="copy-code-btn" onclick="(function(btn){
        var code = decodeURIComponent('${encodeURIComponent(code)}');
        navigator.clipboard.writeText(code).then(function(){
          btn.textContent='已复制';
          setTimeout(function(){btn.textContent='复制代码'},1500);
        });
      })(this)">复制代码</button>
    </div>
    <pre><code class="language-${lang}">${escapedCode}</code></pre>
  </div>`
}

const renderMarkdown = (content) => {
  if (!content) return ''
  return md.render(content)
}

const props = defineProps({
  id: { type: Number, default: 0 }
})

const route = useRoute()
const router = useRouter()
const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const error = ref('')
const useKnowledge = ref(true)
const messageContainer = ref(null)
const hoveredMsg = ref(-1)
const copiedIndex = ref(-1)
const showScrollBtn = ref(false)
const conversationTitle = ref('新对话')
const conversationCreatedAt = ref('')

const scrollToBottom = () => {
  nextTick(() => {
    if (messageContainer.value) {
      messageContainer.value.scrollTo({
        top: messageContainer.value.scrollHeight,
        behavior: 'smooth'
      })
    }
  })
}

const handleScroll = () => {
  if (!messageContainer.value) return
  const { scrollTop, scrollHeight, clientHeight } = messageContainer.value
  showScrollBtn.value = scrollHeight - scrollTop - clientHeight > 200
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const formatCreatedAt = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const copyText = (text) => {
  const index = hoveredMsg.value
  navigator.clipboard.writeText(text).then(() => {
    copiedIndex.value = index
    setTimeout(() => { copiedIndex.value = -1 }, 1500)
  })
}

const loadMessages = async () => {
  if (!props.id) return
  try {
    const response = await axios.get(`/api/conversations/${props.id}/messages`)
    messages.value = response.data || []
    scrollToBottom()
  } catch (err) {
    console.error('加载消息失败:', err)
  }
}

const loadConversationInfo = async () => {
  if (!props.id) return
  try {
    const response = await axios.get(`/api/conversations/${props.id}`)
    conversationTitle.value = response.data.title || '新对话'
    conversationCreatedAt.value = response.data.created_at || ''
  } catch (err) {
    console.error('加载对话信息失败:', err)
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return
  if (!props.id) return

  const userMsg = {
    role: 'user',
    content: inputMessage.value,
    timestamp: new Date().toISOString()
  }
  messages.value.push(userMsg)

  const message = inputMessage.value
  inputMessage.value = ''
  isLoading.value = true
  error.value = ''
  scrollToBottom()

  try {
    const endpoint = useKnowledge.value ? '/api/chat/rag' : '/api/chat'
    const response = await axios.post(endpoint, {
      conversation_id: props.id,
      message: message,
      use_knowledge: useKnowledge.value
    })

    let aiContent
    if (useKnowledge.value) {
      aiContent = response.data.response
    } else {
      aiContent = response.data.message.content
    }

    messages.value.push({
      role: 'assistant',
      content: aiContent,
      timestamp: new Date().toISOString()
    })
    scrollToBottom()
    // 延迟刷新，等待后台异步生成标题
    setTimeout(() => {
      refreshHistory()
      loadConversationInfo()  // 刷新当前对话标题
    }, 3000)
  } catch (err) {
    console.error('发送消息失败:', err)
    error.value = err.response?.data?.detail || '发送失败，请重试'
    const userIdx = messages.value.findIndex(m => m === userMsg)
    if (userIdx !== -1) messages.value.splice(userIdx, 1)
  } finally {
    isLoading.value = false
  }
}

const checkPrefill = async () => {
  const prefill = route.query?.prefill
  if (prefill && props.id) {
    // 清除 URL 中的 prefill 参数，避免重复发送
    router.replace({ query: {} })
    inputMessage.value = prefill
    await nextTick()
    await sendMessage()
  }
}

watch(() => props.id, async () => {
  if (!props.id) return
  messages.value = []
  await loadMessages()
  await loadConversationInfo()
  await nextTick()
  await checkPrefill()
})

onMounted(async () => {
  if (props.id) {
    await loadMessages()
    await loadConversationInfo()
    await nextTick()
    await checkPrefill()
  }
})
</script>

<style scoped>
.chat-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  --ink-900: #0f1419;
  --ink-700: #2c333d;
  --ink-400: #6b7685;
  --ink-200: #a8b0bb;
  --gold-500: #c9a96e;
  --gold-400: #d4ba85;
  --cream-50: #faf8f5;
  --cream-100: #f3efe8;
  --cream-200: #e8e2d8;
  --warm-white: #fdfcfa;
  --font-display: 'Noto Serif SC', 'Songti SC', serif;
  --font-body: 'DM Sans', 'PingFang SC', sans-serif;
  font-family: var(--font-body);
}

/* Chat Header */
.chat-header {
  padding: 12px 24px 12px 70px;
  background: var(--warm-white);
  border-bottom: 1px solid var(--cream-200);
  display: flex;
  align-items: center;
  gap: 12px;
}

.chat-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  color: var(--ink-900);
  margin: 0;
}

.chat-time {
  font-size: 12px;
  color: var(--ink-200);
}

/* Messages Area */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px;
  background: linear-gradient(180deg, var(--cream-50) 0%, #f5f2ec 100%);
  position: relative;
}

/* 宣纸纹理背景 */
.chat-messages::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  opacity: 0.04;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='paper'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.04' numOctaves='5' result='noise'/%3E%3CfeDiffuseLighting in='noise' lighting-color='%23c9a96e' surfaceScale='2'%3E%3CfeDistantLight azimuth='45' elevation='60'/%3E%3C/feDiffuseLighting%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23paper)'/%3E%3C/svg%3E");
  background-size: 200px 200px;
}

/* 淡雅的对角线网格 */
.chat-messages::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  opacity: 0.035;
  background-image:
    linear-gradient(45deg, var(--ink-900) 1px, transparent 1px),
    linear-gradient(-45deg, var(--ink-900) 1px, transparent 1px);
  background-size: 60px 60px;
}

.chat-messages::-webkit-scrollbar {
  width: 5px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: var(--cream-200);
  border-radius: 3px;
}

/* Message */
.message {
  display: flex;
  margin-bottom: 28px;
  opacity: 0;
  animation: fadeIn 0.4s ease forwards;
}

.message.user {
  flex-direction: row-reverse;
}

.slide-in-left {
  animation: slideInLeft 0.4s ease forwards !important;
}

.slide-in-right {
  animation: slideInRight 0.4s ease forwards !important;
}

@keyframes slideInLeft {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes slideInRight {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Avatars */
.message-avatar {
  margin: 0 12px;
  flex-shrink: 0;
}

.avatar-user,
.avatar-ai {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 700;
}

.avatar-user {
  background: #6A8C9E;
  color: #fff;
}

.avatar-ai {
  background: var(--gold-500);
  color: var(--ink-900);
}

/* Message Bubbles */
.message-content {
  max-width: 70%;
  position: relative;
  padding-bottom: 8px;
}

.message.user .message-content {
  text-align: right;
}

.message-text {
  padding: 14px 18px;
  border-radius: 14px;
  line-height: 1.7;
  font-size: 14px;
  text-align: left;
  position: relative;
}

.user-bubble {
  background: var(--ink-900);
  color: var(--cream-100);
  border-bottom-right-radius: 4px;
  box-shadow: 0 2px 12px rgba(15, 20, 25, 0.12);
  border-left: 3px solid #6A8C9E;
}

.ai-bubble {
  background: var(--warm-white);
  color: var(--ink-900);
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 8px rgba(0,0,0,0.04);
  border: 1px solid var(--cream-200);
}

.message-time {
  font-size: 11px;
  color: var(--ink-200);
  margin-top: 6px;
}

/* Copy Button */
.copy-msg-btn {
  position: absolute;
  bottom: 6px;
  right: 0;
  padding: 2px 8px;
  font-size: 11px;
  background: var(--cream-100);
  border: 1px solid var(--cream-200);
  border-radius: 4px;
  cursor: pointer;
  color: var(--ink-400);
  transition: background-color 0.2s, color 0.2s;
  font-family: var(--font-body);
  z-index: 1;
}

.copy-msg-btn:hover {
  background: var(--cream-200);
  color: var(--ink-700);
}

/* Code Block */
.markdown-body :deep(.code-block-wrapper) {
  position: relative;
  margin: 12px 0;
  border-radius: 8px;
  overflow: hidden;
  background: #1a1f27;
}

.markdown-body :deep(.code-block-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  background: rgba(201, 169, 110, 0.06);
  border-bottom: 1px solid rgba(255,255,255,0.04);
}

.markdown-body :deep(.code-lang) {
  font-size: 11px;
  color: #c9a96e;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-family: var(--font-body);
}

.markdown-body :deep(.copy-code-btn) {
  padding: 3px 10px;
  font-size: 11px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 4px;
  cursor: pointer;
  color: rgba(255,255,255,0.5);
  transition: background-color 0.2s, color 0.2s;
}

.markdown-body :deep(.copy-code-btn:hover) {
  background: rgba(201, 169, 110, 0.15);
  color: #c9a96e;
}

.markdown-body :deep(pre) {
  background: #1a1f27;
  color: #c8ccd4;
  padding: 14px;
  margin: 0;
  overflow-x: auto;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 13px;
}

.markdown-body :deep(p) { margin: 0 0 10px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }

.markdown-body :deep(code) {
  background: var(--cream-100);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 13px;
  color: #B5694D;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) { padding-left: 20px; margin: 10px 0; }
.markdown-body :deep(li) { margin: 4px 0; }

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 15px 0 10px;
  font-weight: 600;
  font-family: var(--font-display);
}

.markdown-body :deep(h1) { font-size: 1.4em; }
.markdown-body :deep(h2) { font-size: 1.2em; }
.markdown-body :deep(h3) { font-size: 1.1em; }

.markdown-body :deep(blockquote) {
  border-left: 3px solid #B5694D;
  padding-left: 12px;
  margin: 10px 0;
  color: var(--ink-400);
}

.markdown-body :deep(a) { color: var(--gold-500); text-decoration: none; }
.markdown-body :deep(a:hover) { text-decoration: underline; color: #a8893e; }

.markdown-body :deep(table) { border-collapse: collapse; width: 100%; margin: 10px 0; }
.markdown-body :deep(th),
.markdown-body :deep(td) { border: 1px solid var(--cream-200); padding: 8px; text-align: left; }
.markdown-body :deep(th) { background: var(--cream-100); font-weight: 600; }

/* Typing */
.typing-indicator {
  display: flex;
  gap: 5px;
  padding: 4px 0;
}

.typing-indicator span {
  width: 7px;
  height: 7px;
  background: var(--gold-500);
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

/* Scroll Button */
.scroll-bottom-btn {
  position: absolute;
  bottom: 120px;
  right: 28px;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--warm-white);
  border: 1px solid var(--cream-200);
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-400);
  transition: border-color 0.2s, color 0.2s;
  z-index: 10;
}

.scroll-bottom-btn:hover {
  border-color: var(--gold-400);
  color: var(--gold-500);
}

.bounce-enter-active { animation: bounceIn 0.3s; }
.bounce-leave-active { animation: bounceIn 0.2s reverse; }

@keyframes bounceIn {
  0% { transform: scale(0); opacity: 0; }
  60% { transform: scale(1.1); }
  100% { transform: scale(1); opacity: 1; }
}

/* Input Area */
.chat-input {
  padding: 20px;
  background: linear-gradient(to bottom, var(--warm-white), #f8f6f2);
  border-top: 2px solid var(--gold-500);
  box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.08);
  position: relative;
  z-index: 5;
}

.chat-input::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--gold-400), transparent);
}

.input-container {
  max-width: 800px;
  margin: 0 auto;
}

.input-container :deep(.el-textarea__inner) {
  border-radius: 12px;
  padding: 14px 18px;
  font-size: 14px;
  font-family: var(--font-body);
  border: 2px solid var(--cream-200);
  background: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input-container :deep(.el-textarea__inner:focus) {
  border-color: var(--gold-500);
  box-shadow: 0 4px 16px rgba(201, 169, 110, 0.15);
  background: white;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.knowledge-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
}

.send-btn {
  border-radius: 8px;
  padding: 8px 24px;
  background: #6A8C9E;
  color: #fff;
  border: none;
  font-family: var(--font-body);
  font-weight: 600;
  transition: background-color 0.2s, box-shadow 0.2s, transform 0.2s;
}

.send-btn:hover {
  background: #84A3B3;
  box-shadow: 0 4px 16px rgba(106, 140, 158, 0.3);
  transform: translateY(-1px);
}

.send-btn:active {
  transform: scale(0.96);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }

/* Error */
.error-alert {
  position: absolute;
  bottom: 100px;
  left: 50%;
  transform: translateX(-50%);
  max-width: 500px;
  z-index: 100;
}

/* Respect motion preferences */
@media (prefers-reduced-motion: reduce) {
  .message { animation: none; opacity: 1; }
  .slide-in-left,
  .slide-in-right { animation: none !important; opacity: 1; }
  .typing-indicator span { animation: none; }
  .copy-msg-btn { transition: none; }
  .scroll-bottom-btn { transition: none; }
  .send-btn { transition: none; }
  .bounce-enter-active,
  .bounce-leave-active { animation: none; }
}
</style>

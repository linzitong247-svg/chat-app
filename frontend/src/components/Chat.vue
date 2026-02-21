<template>
  <div class="chat-container">
    <!-- 聊天区域 -->
    <div class="chat-messages" ref="messageContainer">
      <div
        v-for="msg in messages"
        :key="msg.timestamp"
        :class="['message', msg.role]"
      >
        <div class="message-avatar">
          <el-avatar :icon="msg.role === 'user' ? 'User' : 'ChatDotRound'" />
        </div>
        <div class="message-content">
          <!-- 用户消息：普通文本 -->
          <div v-if="msg.role === 'user'" class="message-text">{{ msg.content }}</div>
          <!-- AI 消息：Markdown 渲染 -->
          <div v-else class="message-text markdown-body" v-html="renderMarkdown(msg.content)"></div>
          <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="isLoading" class="message assistant">
        <div class="message-avatar">
          <el-avatar icon="ChatDotRound" />
        </div>
        <div class="message-content">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input">
      <div class="input-container">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="2"
          placeholder="输入您的问题..."
          @keyup.enter="sendMessage"
          :disabled="isLoading"
        />
        <div class="input-actions">
          <el-switch
            v-model="useKnowledge"
            active-text="使用知识库"
            inactive-text="普通对话"
          />
          <el-button
            type="primary"
            @click="sendMessage"
            :loading="isLoading"
          >
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
      @close="error = ''"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import MarkdownIt from 'markdown-it'

// 初始化 Markdown 解析器
const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true
})

// 渲染 Markdown
const renderMarkdown = (content) => {
  if (!content) return ''
  return md.render(content)
}

const props = defineProps({
  id: {
    type: Number,
    required: true
  }
})

const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const error = ref('')
const useKnowledge = ref(true)
const messageContainer = ref(null)

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messageContainer.value) {
      messageContainer.value.scrollTop = messageContainer.value.scrollHeight
    }
  })
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 加载对话历史
const loadMessages = async () => {
  try {
    const response = await axios.get(`/api/conversations/${props.id}/messages`)
    messages.value = response.data || []
    scrollToBottom()
  } catch (err) {
    console.error('加载消息失败:', err)
  }
}

// 发送消息
const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return

  // 添加用户消息 构造一个用户消息对象 userMsg，包含角色（user）、内容和时间戳
  const userMsg = {
    role: 'user',
    content: inputMessage.value,
    timestamp: new Date().toISOString()
  }
  // 将这条消息添加到 messages 响应式数组中，这样页面上就会立刻显示用户刚发送的消息
  messages.value.push(userMsg)

  // 清空输入
  const message = inputMessage.value
  inputMessage.value = ''
  isLoading.value = true
  error.value = ''

  // 滚动到底部
  scrollToBottom()

  try {
    // 选择 API 端点
    const endpoint = useKnowledge.value ? '/api/chat/rag' : '/api/chat'

    const response = await axios.post(endpoint, {
      conversation_id: props.id,
      message: message,
      use_knowledge: useKnowledge.value
    })

    // 根据不同端点解析响应
    let aiContent
    if (useKnowledge.value) {
      // RAG 响应格式: { response: "...", context_used: [...] }
      aiContent = response.data.response
    } else {
      // 普通聊天响应格式: { message: { content: "..." } }
      aiContent = response.data.message.content
    }

    // 添加 AI 回复
    const aiMsg = {
      role: 'assistant',
      content: aiContent,
      timestamp: new Date().toISOString()
    }
    messages.value.push(aiMsg)

    // 如果是 RAG 对话，在控制台会显示使用的上下文
    if (response.data.context_used && response.data.context_used.length > 0) {
      console.log('使用的上下文:', response.data.context_used)
    }

  }   catch (err) {
    console.error('发送消息失败:', err)
    error.value = err.response?.data?.detail || '发送失败，请重试'

    // 移除用户消息
    messages.value.pop()
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

// （切换对话场景）监听对话 ID 变化    watch(要监听谁, 它变了之后要做什么)
watch(() => props.id, () => {
  messages.value = []
  loadMessages()
})

// （加载初始对话的消息）组件挂载时加载消息
onMounted(() => {
  loadMessages()
})
</script>

<style scoped>
.chat-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f5f5;
}

.message {
  display: flex;
  margin-bottom: 20px;
  animation: fadeIn 0.3s ease-in;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  margin: 0 10px;
}

.message-content {
  max-width: 70%;
}

.message.user .message-content {
  text-align: right;
}

.message-text {
  background: white;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
  text-align: left;
}

.message.user .message-text {
  background: #409eff;
  color: white;
}

.message-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.chat-input {
  padding: 20px;
  background: white;
  border-top: 1px solid #eee;
}

.input-container {
  max-width: 800px;
  margin: 0 auto;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #409eff;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-10px);
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Markdown 样式 */
.markdown-body :deep(p) {
  margin: 0 0 10px 0;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(code) {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: Consolas, Monaco, monospace;
  font-size: 14px;
}

.markdown-body :deep(pre) {
  background: #282c34;
  color: #abb2bf;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 10px 0;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 10px 0;
}

.markdown-body :deep(li) {
  margin: 4px 0;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 15px 0 10px 0;
  font-weight: bold;
}

.markdown-body :deep(h1) { font-size: 1.4em; }
.markdown-body :deep(h2) { font-size: 1.2em; }
.markdown-body :deep(h3) { font-size: 1.1em; }

.markdown-body :deep(blockquote) {
  border-left: 4px solid #409eff;
  padding-left: 12px;
  margin: 10px 0;
  color: #666;
}

.markdown-body :deep(a) {
  color: #409eff;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #f5f5f5;
  font-weight: bold;
}
</style>

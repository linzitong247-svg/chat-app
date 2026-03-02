<template>
  <div class="history-container">
    <!-- 顶部操作栏 -->
    <div class="header">
      <el-button class="new-chat-btn" @click="createNewConversation">
        <el-icon><Plus /></el-icon>
        <span>新建对话</span>
      </el-button>
    </div>

    <!-- 搜索框 -->
    <div class="search-box">
      <el-input
        v-model="searchQuery"
        placeholder="搜索对话..."
        :prefix-icon="Search"
        clearable
        size="small"
      />
    </div>

    <!-- 对话列表 -->
    <div class="conversation-list">
      <TransitionGroup name="list" tag="div">
        <div
          v-for="(conversation, index) in filteredConversations"
          :key="conversation.id"
          :class="['conversation-item', { active: currentConversation?.id === conversation.id }]"
          :style="{ '--delay': index * 0.05 + 's' }"
          @click="selectConversation(conversation)"
        >
          <div class="conversation-info">
            <div class="conversation-title">{{ conversation.title || '新对话' }}</div>
            <div class="conversation-meta">
              <span v-if="searchQuery && conversation.matchSnippet" class="conversation-snippet" v-html="conversation.matchSnippet"></span>
              <span class="conversation-time">{{ formatTime(conversation.created_at) }}</span>
            </div>
          </div>
          <div class="conversation-actions">
            <el-button
              link
              @click.stop="openEditDialog(conversation)"
              title="重命名"
            >
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button
              link
              @click.stop="deleteConversation(conversation.id)"
              title="删除"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </TransitionGroup>
    </div>

    <!-- 空状态 -->
    <div v-if="filteredConversations.length === 0 && !searchQuery" class="empty-state">
      <div class="empty-icon">
        <el-icon :size="32"><ChatDotRound /></el-icon>
      </div>
      <p class="empty-text">暂无对话</p>
      <p class="empty-hint">点击上方按钮开启第一段对话</p>
    </div>
    <div v-if="filteredConversations.length === 0 && searchQuery" class="empty-state">
      <div class="empty-icon">
        <el-icon :size="32"><Search /></el-icon>
      </div>
      <p class="empty-text">未找到匹配的对话</p>
    </div>

    <!-- 底部操作区 -->
    <div class="footer-actions">
      <el-button
        v-if="conversations.length > 0"
        class="delete-all-btn"
        @click="deleteAllConversations"
        link
      >
        <el-icon><Delete /></el-icon>
        <span>清空所有对话</span>
      </el-button>
    </div>

    <!-- 编辑标题对话框 -->
    <el-dialog v-model="editDialogVisible" title="重命名对话" width="400px" class="rename-dialog" :teleported="false">
      <el-input v-model="editTitle" placeholder="请输入对话标题" @keyup.enter="saveTitle" />
      <template #footer>
        <el-button class="rename-cancel-btn" @click="editDialogVisible = false">取消</el-button>
        <el-button class="rename-confirm-btn" @click="saveTitle">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, ChatDotRound } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const conversations = ref([])
const currentConversation = ref(null)
const searchQuery = ref('')
const isSearching = ref(false)

const editDialogVisible = ref(false)
const editTitle = ref('')
const editingConversation = ref(null)

// 提取包含搜索词的句子片段
const extractMatchSnippet = (content, query, maxLength = 30) => {
  if (!content || !query) return null
  const lowerContent = content.toLowerCase()
  const lowerQuery = query.toLowerCase()
  const index = lowerContent.indexOf(lowerQuery)
  if (index === -1) return null

  // 计算片段的起始和结束位置
  let start = Math.max(0, index - 10)
  let end = Math.min(content.length, index + query.length + 15)

  // 调整到完整字符
  const snippet = (start > 0 ? '...' : '') + content.slice(start, end) + (end < content.length ? '...' : '')

  // 高亮搜索词
  const highlighted = snippet.replace(
    new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
    '<mark>$1</mark>'
  )
  return highlighted
}

// 搜索对话内容
const searchInMessages = async (query) => {
  if (!query.trim()) {
    // 清除所有 matchSnippet
    conversations.value.forEach(c => { c.matchSnippet = null })
    return
  }

  isSearching.value = true
  const lowerQuery = query.toLowerCase()

  // 为每个对话搜索
  await Promise.all(
    conversations.value.map(async (conv) => {
      // 先检查标题
      if ((conv.title || '新对话').toLowerCase().includes(lowerQuery)) {
        conv.matchSnippet = extractMatchSnippet(conv.title || '新对话', query)
        return
      }

      // 搜索消息内容
      try {
        const response = await axios.get(`/api/conversations/${conv.id}/messages`)
        const messages = response.data || []
        for (const msg of messages) {
          if (msg.content?.toLowerCase().includes(lowerQuery)) {
            conv.matchSnippet = extractMatchSnippet(msg.content, query)
            return
          }
        }
        conv.matchSnippet = null
      } catch (err) {
        conv.matchSnippet = null
      }
    })
  )

  isSearching.value = false
}

// 监听搜索词变化
watch(searchQuery, (newQuery) => {
  if (newQuery.trim()) {
    searchInMessages(newQuery)
  } else {
    conversations.value.forEach(c => { c.matchSnippet = null })
  }
})

const filteredConversations = computed(() => {
  if (!searchQuery.value.trim()) return conversations.value
  return conversations.value.filter(c => c.matchSnippet !== null)
})

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  if (diff < 60 * 60 * 1000) return `${Math.floor(diff / (60 * 1000))}分钟前`
  if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / (60 * 60 * 1000))}小时前`
  if (diff < 24 * 60 * 60 * 1000 * 30) return `${Math.floor(diff / (24 * 60 * 60 * 1000))}天前`
  return date.toLocaleDateString('zh-CN')
}

const loadConversations = async () => {
  try {
    const response = await axios.get('/api/conversations')
    conversations.value = response.data || []
  } catch (err) {
    console.error('加载对话列表失败:', err)
    ElMessage.error('加载失败')
  }
}

const createNewConversation = async () => {
  try {
    const response = await axios.post('/api/conversations', { title: '新对话' })
    await loadConversations()
    currentConversation.value = response.data
    router.push(`/chat/${response.data.id}`)
  } catch (err) {
    console.error('创建对话失败:', err)
    ElMessage.error('创建失败')
  }
}

const selectConversation = (conversation) => {
  currentConversation.value = conversation
  router.push(`/chat/${conversation.id}`)
}

const deleteConversation = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个对话吗？', '提示', {
      type: 'warning',
      customClass: 'custom-message-box'
    })
    await axios.delete(`/api/conversations/${id}`)
    ElMessage.success('删除成功')
    if (currentConversation.value?.id === id) {
      currentConversation.value = null
      router.push('/')
    }
    loadConversations()
  } catch (err) {
    if (err !== 'cancel') {
      console.error('删除失败:', err)
      ElMessage.error('删除失败')
    }
  }
}

const openEditDialog = (conversation) => {
  editingConversation.value = conversation
  editTitle.value = conversation.title || '新对话'
  editDialogVisible.value = true
}

const saveTitle = async () => {
  if (!editTitle.value.trim()) {
    ElMessage.warning('标题不能为空')
    return
  }
  try {
    await axios.put(`/api/conversations/${editingConversation.value.id}/title?title=${encodeURIComponent(editTitle.value)}`)
    ElMessage.success('修改成功')
    editDialogVisible.value = false
    loadConversations()
  } catch (err) {
    console.error('修改标题失败:', err)
    ElMessage.error('修改失败')
  }
}

const deleteAllConversations = async () => {
  try {
    await ElMessageBox.confirm('确定要清空所有对话吗？此操作不可恢复。', '清空对话', {
      type: 'warning',
      confirmButtonText: '确认清空',
      cancelButtonText: '取消',
      customClass: 'custom-message-box'
    })
    await axios.delete('/api/conversations')
    ElMessage.success('已清空所有对话')
    currentConversation.value = null
    router.push('/')
    loadConversations()
  } catch (err) {
    if (err !== 'cancel') {
      console.error('清空对话失败:', err)
      ElMessage.error('清空失败')
    }
  }
}

const currentRoute = useRoute()
watch(() => currentRoute.params.id, (newId) => {
  if (newId) {
    const conv = conversations.value.find(c => c.id == newId)
    if (conv) currentConversation.value = conv
  }
}, { immediate: true })

defineExpose({ loadConversations })

onMounted(() => {
  loadConversations()
})
</script>

<style scoped>
.history-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

/* Header */
.header {
  padding: 16px;
}

.new-chat-btn {
  width: 100%;
  height: 42px;
  border-radius: 8px;
  background: #c9a96e;
  border: none;
  color: #0f1419;
  font-family: 'DM Sans', 'PingFang SC', sans-serif;
  font-size: 14px;
  font-weight: 600;
  transition: background-color 0.25s, box-shadow 0.25s, transform 0.25s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.new-chat-btn:hover {
  background: #d4ba85;
  box-shadow: 0 4px 16px rgba(201, 169, 110, 0.35);
  transform: translateY(-1px);
}

.new-chat-btn:active {
  transform: translateY(0);
}

/* Search */
.search-box {
  padding: 0 16px 12px;
}

.search-box :deep(.el-input__wrapper) {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  box-shadow: none;
}

.search-box :deep(.el-input__inner) {
  color: rgba(255,255,255,0.8);
  font-family: 'DM Sans', 'PingFang SC', sans-serif;
}

.search-box :deep(.el-input__inner::placeholder) {
  color: rgba(255,255,255,0.25);
}

.search-box :deep(.el-input__prefix .el-icon),
.search-box :deep(.el-input__suffix .el-icon) {
  color: rgba(255,255,255,0.25);
}

/* Conversation List */
.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
}

.conversation-list::-webkit-scrollbar {
  width: 3px;
}

.conversation-list::-webkit-scrollbar-thumb {
  background: rgba(201, 169, 110, 0.15);
  border-radius: 2px;
}

.conversation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  margin-bottom: 2px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s, border-left-color 0.2s;
  border-left: 2px solid transparent;
}

.conversation-item:hover {
  background: rgba(255,255,255,0.04);
}

.conversation-item.active {
  background: rgba(201, 169, 110, 0.08);
  border-left-color: #c9a96e;
}

.conversation-title {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255,255,255,0.8);
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.conversation-item.active .conversation-title {
  color: #e0cc9f;
}

.conversation-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.conversation-snippet {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  max-width: 140px;
}

.conversation-snippet :deep(mark) {
  background: rgba(201, 169, 110, 0.3);
  color: #c9a96e;
  padding: 0 2px;
  border-radius: 2px;
}

.conversation-time {
  font-size: 11px;
  color: rgba(255,255,255,0.25);
  flex-shrink: 0;
}

.conversation-actions {
  opacity: 0;
  transition: opacity 0.2s;
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.conversation-item:hover .conversation-actions {
  opacity: 1;
}

.conversation-actions .el-button {
  color: rgba(255,255,255,0.3);
  padding: 4px;
}

.conversation-actions .el-button:hover {
  color: #c9a96e;
}

/* TransitionGroup */
.list-enter-active {
  transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1), transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  transition-delay: var(--delay, 0s);
}

.list-leave-active {
  transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.list-enter-from {
  opacity: 0;
  transform: translateX(-16px);
}

.list-leave-to {
  opacity: 0;
  transform: translateX(16px);
}

.list-move {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Empty State */
.empty-state {
  padding: 24px 20px;
  text-align: center;
}

.empty-icon {
  color: rgba(255, 255, 255, 0.15);
  margin-bottom: 12px;
}

.empty-text {
  color: rgba(255,255,255,0.3);
  font-size: 13px;
  margin: 0 0 6px;
}

.empty-hint {
  color: rgba(255,255,255,0.18);
  font-size: 12px;
  margin: 0;
}

/* Footer Actions */
.footer-actions {
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.delete-all-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: rgba(255, 255, 255, 0.3);
  font-size: 12px;
  padding: 10px;
  border-radius: 8px;
  transition: color 0.2s, background-color 0.2s;
}

.delete-all-btn:hover {
  color: #B5694D;
  background: rgba(181, 105, 77, 0.1);
}

.delete-all-btn .el-icon {
  font-size: 14px;
}

/* ===== Rename Dialog ===== */
/* Rename dialog uses teleported=false, so scoped styles should work.
   If Element Plus styles still override, the issue may be with specificity. */

/* ===== Accent Colors ===== */
.new-chat-btn {
  background: #6A8C9E;
  color: #fff;
}

.new-chat-btn:hover {
  background: #84A3B3;
  box-shadow: 0 4px 16px rgba(106, 140, 158, 0.35);
}

.conversation-actions .el-button:last-child:hover {
  color: #B5694D;
}

/* Respect motion preferences */
@media (prefers-reduced-motion: reduce) {
  .new-chat-btn { transition: none; }
  .conversation-item { transition: none; }
  .conversation-actions { transition: none; }
  .list-enter-active,
  .list-leave-active,
  .list-move { transition: none; }
}
</style>

<style>
/* ===== Custom MessageBox (全局样式) ===== */
.custom-message-box {
  background: #1a1f27 !important;
  border: 1px solid rgba(201, 169, 110, 0.15) !important;
  border-radius: 12px !important;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5) !important;
}

.custom-message-box .el-message-box__header {
  padding: 20px 24px 12px !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
}

.custom-message-box .el-message-box__title {
  color: #e0cc9f !important;
  font-family: 'Noto Serif SC', 'Songti SC', serif !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  letter-spacing: 1px !important;
}

.custom-message-box .el-message-box__headerbtn .el-message-box__close {
  color: rgba(255, 255, 255, 0.35) !important;
}

.custom-message-box .el-message-box__headerbtn:hover .el-message-box__close {
  color: #c9a96e !important;
}

.custom-message-box .el-message-box__content {
  padding: 20px 24px !important;
}

.custom-message-box .el-message-box__message {
  color: rgba(255, 255, 255, 0.7) !important;
  font-family: 'DM Sans', 'PingFang SC', sans-serif !important;
}

.custom-message-box .el-message-box__btns {
  padding: 12px 24px 20px !important;
  border-top: 1px solid rgba(255, 255, 255, 0.06) !important;
}

.custom-message-box .el-button--default {
  background: transparent !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
  color: rgba(255, 255, 255, 0.5) !important;
  border-radius: 8px !important;
  font-family: 'DM Sans', 'PingFang SC', sans-serif !important;
}

.custom-message-box .el-button--default:hover {
  border-color: rgba(255, 255, 255, 0.25) !important;
  color: rgba(255, 255, 255, 0.7) !important;
}

.custom-message-box .el-button--primary {
  background: #c9a96e !important;
  border: none !important;
  color: #0f1419 !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-family: 'DM Sans', 'PingFang SC', sans-serif !important;
}

.custom-message-box .el-button--primary:hover {
  background: #d4ba85 !important;
}

/* ===== Rename Dialog (全局样式) ===== */
.history-container .el-overlay {
  background: rgba(0, 0, 0, 0.5) !important;
}

.history-container .el-overlay-dialog {
  display: flex !important;
  justify-content: center !important;
  align-items: flex-start !important;
  padding-top: 15vh !important;
}

.history-container .rename-dialog.el-dialog {
  background: #1a1f27 !important;
  border: 1px solid rgba(201, 169, 110, 0.15) !important;
  border-radius: 12px !important;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5) !important;
  margin: 0 !important;
}

.history-container .rename-dialog .el-dialog__header {
  padding: 20px 24px 12px !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
}

.history-container .rename-dialog .el-dialog__title {
  color: #e0cc9f !important;
  font-family: 'Noto Serif SC', 'Songti SC', serif !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  letter-spacing: 1px !important;
}

.history-container .rename-dialog .el-dialog__headerbtn .el-dialog__close {
  color: rgba(255, 255, 255, 0.35) !important;
}

.history-container .rename-dialog .el-dialog__headerbtn:hover .el-dialog__close {
  color: #c9a96e !important;
}

.history-container .rename-dialog .el-dialog__body {
  padding: 20px 24px !important;
}

.history-container .rename-dialog .el-input__wrapper {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}

.history-container .rename-dialog .el-input__wrapper:hover {
  border-color: rgba(201, 169, 110, 0.3) !important;
}

.history-container .rename-dialog .el-input__wrapper.is-focus {
  border-color: #c9a96e !important;
  box-shadow: 0 0 0 2px rgba(201, 169, 110, 0.12) !important;
}

.history-container .rename-dialog .el-input__inner {
  color: rgba(255, 255, 255, 0.85) !important;
  font-family: 'DM Sans', 'PingFang SC', sans-serif !important;
}

.history-container .rename-dialog .el-input__inner::placeholder {
  color: rgba(255, 255, 255, 0.25) !important;
}

.history-container .rename-dialog .el-dialog__footer {
  padding: 12px 24px 20px !important;
  border-top: 1px solid rgba(255, 255, 255, 0.06) !important;
}

.history-container .rename-dialog .rename-cancel-btn {
  background: transparent !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
  color: rgba(255, 255, 255, 0.5) !important;
  border-radius: 8px !important;
  font-family: 'DM Sans', 'PingFang SC', sans-serif !important;
}

.history-container .rename-dialog .rename-cancel-btn:hover {
  border-color: rgba(255, 255, 255, 0.25) !important;
  color: rgba(255, 255, 255, 0.7) !important;
}

.history-container .rename-dialog .rename-confirm-btn {
  background: #c9a96e !important;
  border: none !important;
  color: #0f1419 !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-family: 'DM Sans', 'PingFang SC', sans-serif !important;
}

.history-container .rename-dialog .rename-confirm-btn:hover {
  background: #d4ba85 !important;
}
</style>

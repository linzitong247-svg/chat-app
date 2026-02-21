<template>
  <div class="history-container">
    <!-- 顶部操作栏 -->
    <div class="header">
      <h2>对话历史</h2>
      <el-button type="primary" @click="createNewConversation">
        新建对话
      </el-button>
    </div>

    <!-- 对话列表 -->
    <div class="conversation-list">
      <div
        v-for="conversation in conversations"
        :key="conversation.id"
        :class="['conversation-item', { active: currentConversation?.id === conversation.id }]"
        @click="selectConversation(conversation)"
      >
        <div class="conversation-info">
          <div class="conversation-title">{{ conversation.title || '新对话' }}</div>
          <div class="conversation-time">{{ formatTime(conversation.created_at) }}</div>
        </div>
        <div class="conversation-actions">
          <el-button
            link
            type="primary"
            @click.stop="openEditDialog(conversation)"
            title="重命名"
          >
            <el-icon><Edit /></el-icon>
          </el-button>
          <el-button
            link
            type="danger"
            @click.stop="deleteConversation(conversation.id)"
            title="删除"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="conversations.length === 0" class="empty-state">
      <el-empty description="暂无对话历史">
        <el-button type="primary" @click="createNewConversation">
          创建第一个对话
        </el-button>
      </el-empty>
    </div>

    <!-- 编辑标题对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="重命名对话"
      width="400px"
    >
      <el-input
        v-model="editTitle"
        placeholder="请输入对话标题"
        @keyup.enter="saveTitle"
      />
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveTitle">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const conversations = ref([])
const currentConversation = ref(null)

// 编辑相关
const editDialogVisible = ref(false)
const editTitle = ref('')
const editingConversation = ref(null)

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  // 1小时内显示分钟
  if (diff < 60 * 60 * 1000) {
    const minutes = Math.floor(diff / (60 * 1000))
    return `${minutes}分钟前`
  }
  // 24小时内显示小时
  if (diff < 24 * 60 * 60 * 1000) {
    const hours = Math.floor(diff / (60 * 60 * 1000))
    return `${hours}小时前`
  }
  // 超过24天显示日期
  if (diff < 24 * 60 * 60 * 1000 * 30) {
    const days = Math.floor(diff / (24 * 60 * 60 * 1000))
    return `${days}天前`
  }
  return date.toLocaleDateString('zh-CN')
}

// 加载对话列表
const loadConversations = async () => {
  try {
    const response = await axios.get('/api/conversations')
    conversations.value = response.data || []
  } catch (err) {
    console.error('加载对话列表失败:', err)
    ElMessage.error('加载失败')
  }
}

// 创建新对话
const createNewConversation = async () => {
  try {
    const response = await axios.post('/api/conversations', {
      title: '新对话'
    })

    // 刷新列表
    await loadConversations()

    // 设置为新对话
    currentConversation.value = response.data
    // 跳转到聊天页面
    router.push(`/chat/${response.data.id}`)
  } catch (err) {
    console.error('创建对话失败:', err)
    ElMessage.error('创建失败')
  }
}

// 选择对话
const selectConversation = (conversation) => {
  currentConversation.value = conversation
  router.push(`/chat/${conversation.id}`)
}

// 删除对话
const deleteConversation = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个对话吗？', '提示', {
      type: 'warning'
    })

    await axios.delete(`/api/conversations/${id}`)

    ElMessage.success('删除成功')

    // 如果删除的是当前对话，返回列表
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

// 打开编辑对话框
const openEditDialog = (conversation) => {
  editingConversation.value = conversation
  editTitle.value = conversation.title || '新对话'
  editDialogVisible.value = true
}

// 保存标题
const saveTitle = async () => {
  if (!editTitle.value.trim()) {
    ElMessage.warning('标题不能为空')
    return
  }

  try {
    await axios.put(`/api/conversations/${editingConversation.value.id}/title?title=${encodeURIComponent(editTitle.value)}`)

    ElMessage.success('修改成功')
    editDialogVisible.value = false

    // 刷新列表
    loadConversations()
  } catch (err) {
    console.error('修改标题失败:', err)
    ElMessage.error('修改失败')
  }
}

// 监听路由变化
const currentRoute = useRoute()
watch(() => currentRoute.params.id, (newId) => {
  if (newId) {
    const conv = conversations.value.find(c => c.id == newId)
    if (conv) {
      currentConversation.value = conv
    }
  }
}, { immediate: true })

// 组件挂载时加载
onMounted(() => {
  loadConversations()
})
</script>

<style scoped>
.history-container {
  height: 100%;
  background: #f5f5f5;
}

.header {
  padding: 20px;
  background: white;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h2 {
  color: #333;
  margin: 0;
  font-size: 16px;
}

.conversation-list {
  padding: 10px;
}

.conversation-item {
  background: white;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s;
}

.conversation-item:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.conversation-item.active {
  background: #409eff;
  color: white;
}

.conversation-title {
  font-weight: 500;
  margin-bottom: 4px;
  color: #333;
}

.conversation-item.active .conversation-title {
  color: white;
}

.conversation-time {
  font-size: 12px;
  color: #999;
}

.conversation-item.active .conversation-time {
  color: rgba(255,255,255,0.8);
}

.conversation-actions {
  opacity: 0;
  transition: opacity 0.3s;
  display: flex;
  gap: 4px;
}

.conversation-item:hover .conversation-actions {
  opacity: 1;
}

.empty-state {
  padding: 60px 20px;
  text-align: center;
}
</style>

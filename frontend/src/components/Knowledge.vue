<template>
  <div class="knowledge-container">
    <!-- 操作栏 -->
    <div class="knowledge-actions">
      <el-upload
        ref="uploadRef"
        :action="uploadUrl"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :on-progress="handleUploadProgress"
        :before-upload="beforeUpload"
        :show-file-list="false"
        :accept="acceptedTypes"
        :auto-upload="true"
        :drag="false"
        :multiple="true"
        :disabled="uploading"
        class="upload-wrapper"
      >
        <el-button class="upload-btn" :disabled="uploading">
          <template v-if="uploading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>上传中...</span>
          </template>
          <template v-else>
            <el-icon><Upload /></el-icon>
            <span>上传文档</span>
          </template>
        </el-button>
      </el-upload>

      <el-button class="rebuild-btn" @click="rebuildVector" :loading="rebuilding" :disabled="uploading">
        <el-icon><Refresh /></el-icon>
        <span>重建向量库</span>
      </el-button>
    </div>

    <!-- 上传进度 -->
    <div v-if="uploadingFiles.length > 0" class="upload-progress-list">
      <div v-for="file in uploadingFiles" :key="file.uid" class="upload-progress-item">
        <div class="upload-file-info">
          <span class="upload-file-name">{{ file.name }}</span>
          <span class="upload-file-status" :class="{ 'processing': file.processing }">
            {{ file.processing ? '处理中 ' + file.percent + '%' : file.percent + '%' }}
          </span>
        </div>
        <el-progress
          :percentage="file.percent"
          :show-text="false"
          :stroke-width="3"
          :color="file.processing ? '#6A8C9E' : '#c9a96e'"
        />
      </div>
    </div>

    <!-- 上传提示 -->
    <div class="upload-hint">
      <span class="hint-text">支持格式：TXT、PDF、DOCX | 最大 10MB</span>
    </div>

    <!-- 搜索框 -->
    <div class="search-box">
      <el-input
        v-model="searchQuery"
        placeholder="搜索文档..."
        :prefix-icon="Search"
        clearable
        size="small"
      />
    </div>

    <!-- 统计信息 -->
    <div class="stats-bar">
      <div class="stat-item">
        <span class="stat-label">文档数量</span>
        <span class="stat-value">{{ documents.length }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">总大小</span>
        <span class="stat-value">{{ formatTotalSize() }}</span>
      </div>
      <div v-if="loadError" class="stat-item">
        <el-button link class="retry-btn" @click="loadDocuments">
          <el-icon><Refresh /></el-icon>
          <span>重试</span>
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && documents.length === 0" class="loading-state">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <p>加载中...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="filteredDocuments.length === 0" class="empty-state">
      <div class="empty-icon">
        <el-icon :size="32"><FolderOpened /></el-icon>
      </div>
      <p class="empty-text">
        {{ searchQuery ? '未找到匹配的文档' : '知识库暂无文档' }}
      </p>
      <p v-if="!searchQuery" class="empty-hint">点击上方按钮上传文档</p>
    </div>

    <!-- 文档列表 -->
    <div v-else class="document-list">
      <TransitionGroup name="list" tag="div">
        <div
          v-for="(doc, index) in filteredDocuments"
          :key="doc.id"
          class="document-item"
          :style="{ '--delay': index * 0.05 + 's' }"
        >
          <!-- 文档图标 -->
          <div class="document-icon" :class="getFileIconClass(doc.file_type)">
            <el-icon class="icon-inner">
              <Document v-if="doc.file_type === 'txt'" />
              <PDF v-else-if="doc.file_type === 'pdf'" />
              <Files v-else />
            </el-icon>
          </div>

          <!-- 文档信息 -->
          <div class="document-info">
            <div class="document-name" :title="doc.original_name">{{ doc.original_name }}</div>
            <div class="document-meta">
              <span class="document-size">{{ formatFileSize(doc.file_size) }}</span>
              <span class="document-separator">·</span>
              <span class="document-time">{{ formatTime(doc.upload_time) }}</span>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="document-actions">
            <el-button
              link
              class="action-btn preview-btn"
              @click="openPreview(doc)"
              title="预览"
            >
              <el-icon><View /></el-icon>
            </el-button>
            <el-button
              link
              class="action-btn delete-btn"
              @click="deleteDocument(doc)"
              title="删除"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </TransitionGroup>
    </div>

    <!-- 预览弹窗 -->
    <el-dialog
      v-model="previewVisible"
      :title="previewDoc?.original_name || '文档预览'"
      width="700px"
      class="preview-dialog"
      :teleported="false"
    >
      <div class="preview-content" v-loading="previewLoading">
        <div v-if="previewContent" class="preview-text">{{ previewContent }}</div>
        <div v-else-if="!previewLoading" class="preview-empty">文档内容为空</div>
      </div>
      <template #footer>
        <el-button class="preview-close-btn" @click="previewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Upload, Refresh, Document, Files, View, Delete, FolderOpened, Loading } from '@element-plus/icons-vue'
import axios from 'axios'

// PDF as a component placeholder (Element Plus doesn't have PDF icon)
const PDF = {
  template: '<svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M832 64H192c-70.4 0-128 57.6-128 128v640c0 70.4 57.6 128 128 128h640c70.4 0 128-57.6 128-128V192c0-70.4-57.6-128-128-128zm-64 832H256V128h512v768zm-96-640H320v64h352v-64zm0 192H320v64h352v-64zm0 192H320v64h352v-64z"/></svg>'
}

// State
const documents = ref([])
const searchQuery = ref('')
const uploading = ref(false)
const rebuilding = ref(false)
const previewVisible = ref(false)
const previewDoc = ref(null)
const previewContent = ref('')
const previewLoading = ref(false)
const uploadingFiles = ref([])  // 正在上传的文件列表
const loading = ref(false)           // 加载状态
const loadError = ref(false)         // 加载失败状态

// Upload configuration
const uploadUrl = '/api/knowledge/documents'
const acceptedTypes = '.txt,.pdf,.docx'
const maxSize = 10 * 1024 * 1024 // 10MB

// Computed
const filteredDocuments = computed(() => {
  if (!searchQuery.value.trim()) return documents.value
  const query = searchQuery.value.toLowerCase()
  return documents.value.filter(doc =>
    doc.original_name.toLowerCase().includes(query)
  )
})

// Methods
const loadDocuments = async () => {
  loading.value = true
  loadError.value = false

  try {
    console.log('正在加载知识库文档列表...')
    const response = await axios.get('/api/knowledge/documents')
    console.log('API 响应:', response.data)

    // 处理响应数据
    const docs = response.data || []
    console.log(`成功加载 ${docs.length} 个文档`)
    documents.value = docs

    if (docs.length === 0) {
      console.log('知识库暂无文档')
    }
  } catch (err) {
    console.error('加载文档列表失败:', err)
    console.error('错误详情:', {
      message: err.message,
      response: err.response?.data,
      status: err.response?.status
    })

    loadError.value = true

    // 给用户更详细的错误提示
    let errorMsg = '加载文档列表失败'
    if (err.response?.status === 0) {
      errorMsg = '无法连接到服务器，请检查后端是否启动'
    } else if (err.response?.data?.detail) {
      errorMsg = err.response.data.detail
    } else if (err.message) {
      errorMsg = err.message
    }

    ElMessage.error(errorMsg)
  } finally {
    loading.value = false
  }
}

const beforeUpload = (file) => {
  const ext = file.name.split('.').pop().toLowerCase()
  const validTypes = ['txt', 'pdf', 'docx']

  if (!validTypes.includes(ext)) {
    ElMessage.error(`仅支持上传 .txt, .pdf, .docx 格式的文件`)
    return false
  }

  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过 10MB')
    return false
  }

  // 添加到上传列表
  const uploadFile = {
    uid: file.uid,
    name: file.name,
    percent: 0,
    processing: false
  }
  uploadingFiles.value.push(uploadFile)
  uploading.value = true

  return true
}

const handleUploadProgress = (event, file, fileList) => {
  const uploadingFile = uploadingFiles.value.find(f => f.uid === file.uid)
  if (uploadingFile) {
    uploadingFile.percent = Math.floor(event.percent)
    if (event.percent >= 60) {
      uploadingFile.processing = true
    }
  }
}

const handleUploadSuccess = (response, file, fileList) => {
  const index = uploadingFiles.value.findIndex(f => f.uid === file.uid)
  if (index > -1) {
    uploadingFiles.value.splice(index, 1)
    if (uploadingFiles.value.length === 0) {
      uploading.value = false
    }
  }

  console.log('上传成功响应:', response)
  ElMessage.success(response?.message || '文档上传成功')
  loadDocuments()
}

const handleUploadError = (error, file, fileList) => {
  // 移除失败的上传
  const index = uploadingFiles.value.findIndex(f => f.uid === file.uid)
  if (index > -1) {
    uploadingFiles.value.splice(index, 1)
  }

  if (uploadingFiles.value.length === 0) {
    uploading.value = false
  }

  console.error('上传失败:', error)
  console.error('文件信息:', file)

  let errorMsg = '文档上传失败'
  if (error?.response?.data?.detail) {
    errorMsg = error.response.data.detail
  } else if (error?.message) {
    errorMsg = error.message
  } else if (typeof error === 'string') {
    errorMsg = error
  }

  ElMessage.error(`${file.name}: ${errorMsg}`)
}

const deleteDocument = async (doc) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除文档"${doc.original_name}"吗？`,
      '提示',
      {
        type: 'warning',
        customClass: 'custom-message-box'
      }
    )

    await axios.delete(`/api/knowledge/documents/${doc.id}`)
    ElMessage.success('删除成功')
    loadDocuments()
  } catch (err) {
    if (err !== 'cancel') {
      console.error('删除失败:', err)
      ElMessage.error('删除失败')
    }
  }
}

const openPreview = async (doc) => {
  previewDoc.value = doc
  previewVisible.value = true
  previewContent.value = ''
  previewLoading.value = true

  try {
    const response = await axios.get(`/api/knowledge/documents/${doc.id}/preview`)
    previewContent.value = response.data?.content || ''
  } catch (err) {
    console.error('预览失败:', err)
    ElMessage.error('预览失败')
  } finally {
    previewLoading.value = false
  }
}

const rebuildVector = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要重建向量库吗？',
      '提示',
      {
        type: 'warning',
        customClass: 'custom-message-box'
      }
    )

    rebuilding.value = true

    await axios.post('/api/knowledge/rebuild')

    ElMessage.success('向量库重建成功')
    loadDocuments()
  } catch (err) {
    if (err !== 'cancel') {
      console.error('重建失败:', err)
      ElMessage.error('重建失败')
    }
  } finally {
    rebuilding.value = false
  }
}

// Utility functions
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatTotalSize = () => {
  const total = documents.value.reduce((sum, doc) => sum + (doc.file_size || 0), 0)
  return formatFileSize(total)
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  if (diff < 60 * 60 * 1000) return `${Math.floor(diff / (60 * 1000))}分钟前`
  if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / (60 * 60 * 1000))}小时前`
  if (diff < 24 * 60 * 60 * 1000 * 30) return `${Math.floor(diff / (24 * 60 * 60 * 1000))}天前`

  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: 'numeric', day: 'numeric' })
}

const getFileIconClass = (type) => {
  return `file-icon-${type}`
}

// Lifecycle
onMounted(() => {
  loadDocuments()
})

// Expose methods for parent component
defineExpose({ loadDocuments })
</script>

<style scoped>
/* ===== Design Tokens ===== */
.knowledge-container {
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
  --font-display: 'Noto Serif SC', 'Songti SC', serif;
  --font-body: 'DM Sans', 'PingFang SC', sans-serif;

  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: var(--font-body);
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
}

/* ===== Actions Bar ===== */
.knowledge-actions {
  display: flex;
  gap: 8px;
  padding: 16px;
  background: transparent;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.upload-wrapper {
  flex: 1;
}

.upload-btn {
  width: 100%;
  height: 42px;
  border-radius: 8px;
  background: var(--jade-500);
  border: none;
  color: #fff;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.upload-btn:hover {
  background: var(--jade-400);
  box-shadow: 0 4px 16px rgba(106, 140, 158, 0.35);
  transform: translateY(-1px);
}

.upload-btn:active {
  transform: translateY(0);
}

.rebuild-btn {
  width: 120px;
  height: 42px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.6);
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 500;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-shrink: 0;
}

.rebuild-btn:hover {
  border-color: var(--gold-400);
  color: var(--gold-500);
  background: rgba(201, 169, 110, 0.1);
}

/* ===== Upload Hint ===== */
.upload-hint {
  padding: 8px 16px 12px;
  background: transparent;
  text-align: center;
}

.hint-text {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
  font-family: var(--font-body);
}

/* ===== Upload Progress List ===== */
.upload-progress-list {
  padding: 8px 16px 12px;
  background: transparent;
}

.upload-progress-item {
  margin-bottom: 8px;
}

.upload-file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.upload-file-name {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.upload-file-percent {
  font-size: 11px;
  color: var(--gold-500);
}

.upload-file-status {
  font-size: 11px;
  color: var(--gold-500);
}

.upload-file-status.processing {
  color: var(--jade-400);
}

.upload-progress-item :deep(.el-progress-bar__outer) {
  background: rgba(255, 255, 255, 0.08);
}

.upload-progress-item :deep(.el-progress-bar__inner) {
  background: var(--gold-500);
  transition: all 0.3s ease;
}

/* ===== Search Box ===== */
.search-box {
  padding: 12px 16px;
  background: transparent;
}

.search-box :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  box-shadow: none;
  transition: all 0.2s;
}

.search-box :deep(.el-input__wrapper:hover) {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.06);
}

.search-box :deep(.el-input__wrapper.is-focus) {
  border-color: var(--gold-500);
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 0 0 2px rgba(201, 169, 110, 0.15);
}

.search-box :deep(.el-input__inner) {
  color: rgba(255, 255, 255, 0.8);
  font-family: var(--font-body);
}

.search-box :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.3);
}

.search-box :deep(.el-input__prefix .el-icon),
.search-box :deep(.el-input__suffix .el-icon) {
  color: rgba(255, 255, 255, 0.3);
}

/* ===== Stats Bar ===== */
.stats-bar {
  display: flex;
  gap: 16px;
  padding: 0 16px 12px;
  background: transparent;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
}

.stat-value {
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
}

.retry-btn {
  font-size: 11px;
  color: var(--gold-500);
  padding: 0;
}

.retry-btn:hover {
  color: var(--gold-400);
}

/* ===== Loading State ===== */
.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: rgba(255, 255, 255, 0.3);
}

.loading-state .el-icon {
  font-size: 24px;
  color: var(--gold-500);
}

.loading-state p {
  margin: 0;
  font-size: 13px;
}

/* ===== Document List ===== */
.document-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
  background: transparent;
}

.document-list::-webkit-scrollbar {
  width: 5px;
}

.document-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.document-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 4px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 10px;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.document-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(201, 169, 110, 0.3);
  transform: translateY(-1px);
}

/* Document Icon */
.document-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
}

.document-icon::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 8px;
  opacity: 0.1;
  background: currentColor;
}

.icon-inner {
  font-size: 20px;
  z-index: 1;
}

.file-icon-txt {
  color: var(--ink-600);
}

.file-icon-pdf {
  color: #B5694D;
}

.file-icon-docx {
  color: var(--jade-500);
}

/* Document Info */
.document-info {
  flex: 1;
  min-width: 0;
}

.document-name {
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 6px;
}

.document-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
}

.document-type {
  color: rgba(255, 255, 255, 0.5);
}

.document-separator {
  color: rgba(255, 255, 255, 0.2);
}

.document-time {
  color: rgba(255, 255, 255, 0.3);
}

/* Document Actions */
.document-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
  flex-shrink: 0;
}

.document-item:hover .document-actions {
  opacity: 1;
}

.action-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.4);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--jade-400);
}

.delete-btn:hover {
  background: rgba(181, 105, 77, 0.2);
  color: var(--rust-400);
}

/* ===== TransitionGroup ===== */
.list-enter-active {
  transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1), transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  transition-delay: var(--delay, 0s);
}

.list-leave-active {
  transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.list-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.list-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.list-move {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ===== Empty State ===== */
.empty-state {
  padding: 24px 20px;
  text-align: center;
}

.empty-icon {
  color: rgba(255, 255, 255, 0.15);
  margin-bottom: 12px;
}

.empty-text {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.3);
  margin: 0 0 6px;
}

.empty-hint {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.18);
  margin: 0;
}

/* ===== Preview Dialog ===== */
.preview-content {
  max-height: 500px;
  overflow-y: auto;
  padding: 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.preview-text {
  font-size: 13px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.85);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'JetBrains Mono', Consolas, monospace;
}

.preview-empty {
  text-align: center;
  color: rgba(255, 255, 255, 0.3);
  padding: 40px 20px;
  font-size: 14px;
}

.preview-close-btn {
  background: var(--jade-500);
  border: none;
  color: #fff;
  border-radius: 8px;
  padding: 10px 24px;
  font-weight: 600;
}

.preview-close-btn:hover {
  background: var(--jade-400);
}

/* ===== Respect Motion Preferences ===== */
@media (prefers-reduced-motion: reduce) {
  .upload-btn,
  .rebuild-btn {
    transition: none;
  }
  .document-item {
    transition: none;
  }
  .document-actions {
    transition: none;
    opacity: 1;
  }
  .action-btn {
    transition: none;
  }
  .list-enter-active,
  .list-leave-active,
  .list-move {
    transition: none;
  }
}

/* ===== Loading Animation ===== */
@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 禁用按钮的旋转动画，只允许图标旋转 */
.upload-btn.is-loading {
  animation: none !important;
}

/* 只让图标旋转 */
.upload-btn.is-loading .el-icon {
  animation: rotating 2s linear infinite;
}
</style>

<style>
/* ===== Preview Dialog Global Styles ===== */
.knowledge-container .el-overlay {
  background: rgba(0, 0, 0, 0.6) !important;
}

.knowledge-container .el-overlay-dialog {
  display: flex !important;
  justify-content: center !important;
  align-items: flex-start !important;
  padding-top: 10vh !important;
}

.knowledge-container .preview-dialog.el-dialog {
  background: var(--ink-800) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 12px !important;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4) !important;
  margin: 0 !important;
}

.knowledge-container .preview-dialog .el-dialog__header {
  padding: 20px 24px 12px !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
}

.knowledge-container .preview-dialog .el-dialog__title {
  color: rgba(255, 255, 255, 0.9) !important;
  font-family: var(--font-display) !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  letter-spacing: 1px !important;
}

.knowledge-container .preview-dialog .el-dialog__headerbtn .el-dialog__close {
  color: rgba(255, 255, 255, 0.4) !important;
  font-size: 18px !important;
}

.knowledge-container .preview-dialog .el-dialog__headerbtn:hover .el-dialog__close {
  color: var(--rust-400) !important;
}

.knowledge-container .preview-dialog .el-dialog__body {
  padding: 20px 24px !important;
}

.knowledge-container .preview-dialog .el-dialog__footer {
  padding: 12px 24px 20px !important;
  border-top: 1px solid rgba(255, 255, 255, 0.05) !important;
}
</style>

<template>
  <div class="app-container">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="300px">
        <div class="logo">
          <el-icon size="24"><ChatDotRound /></el-icon>
          <span>RAG 企业问答机器人</span>
        </div>
        <History />
      </el-aside>

      <!-- 主内容区 -->
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import History from './components/History.vue'
</script>

<style scoped>
.app-container {
  height: 100vh;
}

.el-container {
  height: 100%;
}

.el-aside {
  background: #f5f5f5;
  border-right: 1px solid #e0e0e0;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  background: white;
  font-size: 16px;
  font-weight: bold;
  color: #333;
  border-bottom: 1px solid #e0e0e0;
}

.logo .el-icon {
  margin-right: 10px;
  color: #409eff;
}

.el-main {
  padding: 0;
  background: #f0f2f5;
}
</style>
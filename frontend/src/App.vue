<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-left">
        <el-icon class="header-logo" :size="24">
          <Monitor />
        </el-icon>
        <span class="header-title">OpsV-Kits</span>
      </div>
      <el-menu
        :default-active="route.path"
        mode="horizontal"
        :ellipsis="false"
        router
        class="header-menu"
      >
        <el-menu-item index="/">
          <el-icon><HomeFilled /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/project">
          <el-icon><TrendCharts /></el-icon>
          <span>项目</span>
        </el-menu-item>
        <el-menu-item index="/file-manager">
          <el-icon><FolderOpened /></el-icon>
          <span>文件管理</span>
        </el-menu-item>
        <el-menu-item index="/ssh-accounts">
          <el-icon><UserFilled /></el-icon>
          <span>SSH 账户</span>
        </el-menu-item>
        <el-menu-item index="/docker">
          <el-icon><Coin /></el-icon>
          <span>Docker</span>
        </el-menu-item>
        <el-menu-item index="/webssh">
          <el-icon><Monitor /></el-icon>
          <span>终端</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
      </el-menu>
    </el-header>
    <el-container class="app-body">
      <el-aside width="220px" class="app-aside">
        <div class="aside-title">导航菜单</div>
        <el-menu
          :default-active="route.path"
          router
          class="aside-menu"
        >
          <el-menu-item index="/">
            <el-icon><HomeFilled /></el-icon>
            <span>控制台</span>
          </el-menu-item>
          <el-menu-item index="/project">
            <el-icon><TrendCharts /></el-icon>
            <span>项目部署</span>
          </el-menu-item>
          <el-menu-item index="/file-manager">
            <el-icon><FolderOpened /></el-icon>
            <span>远程文件管理</span>
          </el-menu-item>
          <el-menu-item index="/ssh-accounts">
            <el-icon><UserFilled /></el-icon>
            <span>SSH 账户管理</span>
          </el-menu-item>
          <el-menu-item index="/docker">
            <el-icon><Coin /></el-icon>
            <span>Docker 管理</span>
          </el-menu-item>
          <el-menu-item index="/webssh">
            <el-icon><Monitor /></el-icon>
            <span>WebSSH 终端</span>
          </el-menu-item>
          <el-menu-item index="/tools">
            <el-icon><Tools /></el-icon>
            <span>工具箱</span>
          </el-menu-item>
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import {
  Monitor,
  HomeFilled,
  TrendCharts,
  FolderOpened,
  UserFilled,
  Coin,
  Setting,
  Tools,
} from '@element-plus/icons-vue'

const route = useRoute()
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  font-family: 'Microsoft YaHei', 'PingFang SC', -apple-system, BlinkMacSystemFont, sans-serif;
}

#app {
  height: 100%;
}
</style>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  display: flex;
  align-items: center;
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  height: 60px !important;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: 32px;
}

.header-logo {
  color: #409eff;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
}

.header-menu {
  flex: 1;
  border-bottom: none !important;
}

.app-body {
  flex: 1;
  overflow: hidden;
}

.app-aside {
  background: #fff;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
}

.aside-title {
  padding: 16px 20px 8px;
  font-size: 12px;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.aside-menu {
  border-right: none !important;
}

.app-main {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>

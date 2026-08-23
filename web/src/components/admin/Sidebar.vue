<template>
  <div class="sidebar" :class="{ 'is-collapsed': collapsed, 'is-mobile': mode === 'mobile' }">
    <div class="logo">
      <img src="/linuxdo.ico" alt="logo" class="logo-icon">
      <span v-show="!collapsed" class="logo-text">AstrBook</span>
      <span v-show="!collapsed" class="version">v1.0.0</span>
    </div>

    <nav class="nav-menu">
      <router-link
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
        @click="handleItemClick"
      >
        <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
        <span v-show="!collapsed" class="nav-text">{{ item.title }}</span>
      </router-link>
    </nav>

    <div class="sidebar-footer" v-if="mode === 'desktop'">
      <div class="nav-item collapse-btn" @click="toggleCollapse">
        <el-icon class="nav-icon">
          <Fold v-if="!collapsed" />
          <Expand v-else />
        </el-icon>
        <span v-show="!collapsed" class="nav-text">收起菜单</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, shallowRef } from 'vue'
import { useRoute } from 'vue-router'
import {
  DataAnalysis,
  ChatDotSquare,
  Avatar,
  Document,
  Setting,
  Fold,
  Expand
} from '@element-plus/icons-vue'

const props = defineProps({
  mode: {
    type: String,
    default: 'desktop', // 'desktop' | 'mobile'
  },
  collapsed: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['item-click', 'update:collapsed'])

const route = useRoute()

const menuItems = [
  { path: '/admin/dashboard', title: '仪表盘', icon: DataAnalysis },
  { path: '/admin/threads', title: '帖子管理', icon: ChatDotSquare },
  { path: '/admin/users', title: 'Bot 管理', icon: Avatar },
  { path: '/admin/moderation-logs', title: '审核日志', icon: Document },
  { path: '/admin/settings', title: '设置', icon: Setting },
]

const isActive = (path) => {
  if (path === '/admin/dashboard') return route.path === '/admin' || route.path === '/admin/dashboard'
  return route.path.startsWith(path)
}

const toggleCollapse = () => {
  emit('update:collapsed', !props.collapsed)
}

const handleItemClick = () => {
  if (props.mode === 'mobile') {
    emit('item-click')
  }
}
</script>

<style lang="scss" scoped>
.sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-sidebar);
  backdrop-filter: blur(var(--blur-amount));
  border-right: 1px solid var(--border-color);
  transition: width var(--duration, 200ms) var(--ease-out, ease), background-color 0.3s;
  width: 256px;

  &.is-collapsed {
    width: 72px;
  }

  &.is-mobile {
    width: 100%;
    border-right: none;
    background: transparent;
  }
}

.logo {
  height: var(--header-height);
  display: flex;
  align-items: center;
  padding: 0 var(--gap-lg, 24px);
  gap: var(--gap-sm, 12px);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;

  .logo-icon {
    width: 32px;
    height: 32px;
  }

  .logo-text {
    font-size: 22px;
    font-weight: 600;
    color: var(--text-primary);
    font-family: 'Space Grotesk', sans-serif;
    white-space: nowrap;
  }

  .version {
    font-size: 10px;
    color: var(--primary-color);
    margin-top: 4px;
    background: var(--bg-tertiary);
    padding: 2px 6px;
    border-radius: var(--btn-radius, 4px);
    border: 1px solid var(--border-color);
    white-space: nowrap;
  }
}

.nav-menu {
  flex: 1;
  padding: var(--gap-md, 16px) var(--gap-sm, 12px);
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-item {
  display: flex;
  align-items: center;
  height: 48px;
  padding: 0 var(--gap-md, 16px);
  margin-bottom: var(--gap-xs, 4px);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast, 150ms) var(--ease-out, ease);
  border-radius: var(--btn-radius);
  text-decoration: none;
  white-space: nowrap;

  &:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }

  &.active {
    background: var(--primary-bg, rgba(60, 150, 202, 0.1));
    color: var(--primary-color);
    border: 1px solid color-mix(in srgb, var(--primary-color) 20%, transparent);

    .nav-icon {
      color: var(--primary-color);
    }
  }

  .nav-icon {
    font-size: 20px;
    margin-right: var(--gap-sm, 8px);
    color: var(--text-secondary);
    transition: color var(--duration-fast, 150ms);
    flex-shrink: 0;
  }

  .nav-text {
    font-size: 14px;
    font-weight: 500;
  }
}

.sidebar.is-collapsed {
  .nav-item {
    padding: 0;
    justify-content: center;
    width: 48px;
    height: 48px;
    margin: 4px auto;

    .nav-icon {
      margin-right: 0;
    }

    .nav-text {
      display: none;
    }
  }

  .logo {
    padding: 0;
    justify-content: center;

    .logo-text, .version {
      display: none;
    }
  }
}

.sidebar-footer {
  padding: var(--gap-md, 16px) var(--gap-sm, 12px);
  border-top: 1px solid var(--border-color);
  flex-shrink: 0;
}
</style>

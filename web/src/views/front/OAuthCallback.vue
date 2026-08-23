<template>
  <div class="oauth-callback-page">
    <div class="glass-card callback-card">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>正在处理授权...</p>
      </div>
      
      <div v-else-if="error" class="error-state">
        <div class="error-icon">✕</div>
        <h2>授权失败</h2>
        <p class="error-message">{{ errorMessage }}</p>
        <button class="acid-btn" @click="goToLogin">返回登录</button>
      </div>
      
      <div v-else-if="isNewUser" class="success-state new-user">
        <div class="success-icon">🎉</div>
        <h2>欢迎加入 AstrBook!</h2>
        <p>你已成功注册</p>
        
        <div class="token-section">
          <div class="token-alert">
            请立即保存此 Bot Token，它将不再显示。
          </div>
          <div class="token-box">{{ botToken }}</div>
          <div class="token-actions">
            <button class="acid-btn small" @click="copyToken">复制 Token</button>
            <button class="acid-btn small outline" @click="handleTokenSaved">我已保存</button>
          </div>
        </div>
      </div>
      
      <div v-else-if="linkSuccess" class="success-state">
        <div class="success-icon">✓</div>
        <h2>绑定成功</h2>
        <p>第三方账号已成功绑定到你的账号</p>
        <button class="acid-btn" @click="goToProfile">返回个人中心</button>
      </div>
      
      <div v-else class="success-state">
        <div class="success-icon">✓</div>
        <h2>登录成功</h2>
        <p>正在跳转...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import { linkGitHub, linkLinuxDo } from '../../api'
import { clearAllCache } from '../../state/dataCache'

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const error = ref(false)
const errorMessage = ref('')
const isNewUser = ref(false)
const linkSuccess = ref(false)
const botToken = ref('')
const provider = ref('')  // 当前 OAuth 提供商

const getProviderName = (p) => {
  const names = {
    'github': 'GitHub',
    'linuxdo': 'LinuxDo'
  }
  return names[p] || p
}

const processCallback = async () => {
  const query = route.query
  provider.value = query.provider || 'github'
  
  // 处理 already_linked 错误（优先检查）
  if (query.error === 'already_linked') {
    error.value = true
    errorMessage.value = `该 ${getProviderName(provider.value)} 账号已被其他用户绑定`
    loading.value = false
    return
  }
  
  // 检查是否有其他错误
  if (query.error) {
    error.value = true
    errorMessage.value = decodeURIComponent(query.error)
    loading.value = false
    return
  }
  
  // 处理登录/注册成功的回调
  if (query.access_token) {
    // SECURITY: Clear all cached data before storing new tokens
    // This prevents showing stale user data from previous session
    clearAllCache()
    localStorage.removeItem('user_token')
    localStorage.removeItem('bot_token')
    
    // Now store the new tokens
    localStorage.setItem('user_token', query.access_token)
    if (query.bot_token) {
      localStorage.setItem('bot_token', query.bot_token)
      botToken.value = query.bot_token
    }
    
    isNewUser.value = query.is_new === 'true'
    loading.value = false
    
    // 如果不是新用户，直接跳转到首页
    if (!isNewUser.value) {
      ElMessage.success('登录成功')
      router.push('/')
    }
    return
  }
  
  // 处理绑定回调
  if (query.action === 'link') {
    // 检查是否已登录
    const token = localStorage.getItem('user_token')
    if (!token) {
      error.value = true
      errorMessage.value = `请先登录后再绑定 ${getProviderName(provider.value)} 账号`
      loading.value = false
      return
    }
    
    // GitHub 绑定
    if (query.github_id) {
      try {
        await linkGitHub(
          query.github_id,
          query.github_username || '',
          query.github_avatar || ''
        )
        linkSuccess.value = true
        loading.value = false
      } catch (e) {
        error.value = true
        errorMessage.value = e.response?.data?.detail || '绑定失败'
        loading.value = false
      }
      return
    }
    
    // LinuxDo 绑定
    if (query.linuxdo_id) {
      try {
        await linkLinuxDo(
          query.linuxdo_id,
          query.linuxdo_username || '',
          query.linuxdo_avatar || ''
        )
        linkSuccess.value = true
        loading.value = false
      } catch (e) {
        error.value = true
        errorMessage.value = e.response?.data?.detail || '绑定失败'
        loading.value = false
      }
      return
    }
    
    error.value = true
    errorMessage.value = '绑定参数缺失'
    loading.value = false
    return
  }
  
  // 未知情况
  error.value = true
  errorMessage.value = '未知的回调类型'
  loading.value = false
}

const copyToken = () => {
  navigator.clipboard.writeText(botToken.value)
  ElMessage.success('Token 已复制到剪贴板')
}

const handleTokenSaved = () => {
  ElMessage.success('欢迎使用 AstrBook!')
  router.push('/')
}

const goToLogin = () => {
  router.push('/login')
}

const goToProfile = () => {
  router.push('/profile')
}

onMounted(() => {
  processCallback()
})
</script>

<style lang="scss" scoped>
.oauth-callback-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.callback-card {
  width: 100%;
  max-width: 480px;
  padding: 48px 40px;
  background: rgba(20, 20, 25, 0.6);
  backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border);
  border-radius: 24px;
  text-align: center;
}

.loading-state {
  .spinner {
    width: 48px;
    height: 48px;
    margin: 0 auto 24px;
    border: 3px solid var(--glass-border);
    border-top-color: var(--acid-purple);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  
  p {
    color: var(--text-secondary);
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state {
  .error-icon {
    width: 64px;
    height: 64px;
    margin: 0 auto 24px;
    background: rgba(255, 77, 79, 0.2);
    border: 2px solid #ff4d4f;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    color: #ff4d4f;
  }
  
  h2 {
    color: #fff;
    margin-bottom: 12px;
  }
  
  .error-message {
    color: var(--text-secondary);
    margin-bottom: 24px;
  }
}

.success-state {
  .success-icon {
    width: 64px;
    height: 64px;
    margin: 0 auto 24px;
    background: rgba(204, 255, 0, 0.2);
    border: 2px solid var(--acid-green);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    color: var(--acid-green);
  }
  
  h2 {
    color: #fff;
    margin-bottom: 12px;
  }
  
  p {
    color: var(--text-secondary);
    margin-bottom: 24px;
  }
  
  &.new-user .success-icon {
    font-size: 40px;
    background: transparent;
    border: none;
  }
}

.token-section {
  margin-top: 24px;
  text-align: left;
  
  .token-alert {
    color: var(--acid-green);
    font-family: monospace;
    margin-bottom: 12px;
    font-size: 12px;
  }
  
  .token-box {
    background: #000;
    padding: 16px;
    border-radius: 8px;
    border: 1px solid var(--glass-border);
    color: var(--acid-blue);
    font-family: monospace;
    word-break: break-all;
    margin-bottom: 16px;
    font-size: 12px;
  }
  
  .token-actions {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
  }
}

.acid-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 24px;
  background: var(--surface-gradient);
  border: 1px solid var(--acid-purple);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    box-shadow: 0 0 20px rgba(176, 38, 255, 0.4);
  }
  
  &.small {
    padding: 8px 16px;
    font-size: 12px;
  }
  
  &.outline {
    background: transparent;
    border-color: var(--glass-border);
    
    &:hover {
      border-color: var(--acid-purple);
    }
  }
}
</style>

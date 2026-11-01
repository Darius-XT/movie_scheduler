<template>
  <slot v-if="unlocked" />
  <main v-else class="password-page">
    <el-card class="password-card" shadow="never">
      <h1>Movie Movie Movie</h1>
      <p>请输入访问密码后进入</p>
      <el-form @submit.prevent="unlock">
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            show-password
            autocomplete="current-password"
            aria-label="访问密码"
            placeholder="访问密码"
            autofocus
            :disabled="!configuredPassword"
            @input="error = ''"
          />
        </el-form-item>
        <p v-if="error" class="password-error" role="alert">{{ error }}</p>
        <p v-if="!configuredPassword" class="password-error" role="alert">
          尚未配置访问密码，请联系维护者。
        </p>
        <el-button
          class="enter-button"
          type="primary"
          native-type="submit"
          :disabled="!configuredPassword || !password"
        >
          进入
        </el-button>
      </el-form>
    </el-card>
  </main>
</template>

<script setup>
import { ref } from 'vue'

const configuredPassword = import.meta.env.VITE_SITE_PASSWORD || ''
const password = ref('')
const error = ref('')
const unlocked = ref(false)

const unlock = () => {
  if (!configuredPassword) return
  if (password.value !== configuredPassword) {
    error.value = '密码不正确，请重试'
    password.value = ''
    return
  }
  password.value = ''
  error.value = ''
  unlocked.value = true
}
</script>

<style scoped>
.password-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background-color: #f5f5f5;
}

.password-card {
  width: 100%;
  max-width: 380px;
  border-radius: 12px;
}

h1 {
  margin-bottom: 12px;
  color: #303133;
  font-size: 24px;
}

p {
  margin-bottom: 20px;
  color: #606266;
}

.password-error {
  color: #c45656;
  font-size: 14px;
}

.enter-button {
  width: 100%;
}
</style>

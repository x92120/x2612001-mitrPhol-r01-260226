<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { appConfig } from '~/appConfig/config'
import { useAuth } from '~/composables/useAuth'

const router = useRouter()
const route = useRoute()
const $q = useQuasar()
const { login: authLogin } = useAuth()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const isLoading = ref(false)

const handleLogin = async () => {
  if (!email.value || !password.value) {
    $q.notify({ type: 'negative', message: 'Please fill in all fields', position: 'top' })
    return
  }

  isLoading.value = true

  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username_or_email: email.value,
        password: password.value,
      }),
    })

    if (response.ok) {
      const data = await response.json()
      authLogin(data.user, data.access_token)

      $q.notify({
        type: 'positive',
        message: 'Login successful!',
        position: 'top',
        timeout: 1000,
      })

      // Redirect back to original route or dashboard
      const redirectPath = (route.query.redirect as string) || '/'
      await router.replace(redirectPath)
    } else {
      const errorData = await response.json().catch(() => ({}))
      $q.notify({
        type: 'negative',
        message: errorData.detail || 'Invalid username or password',
        position: 'top',
      })
    }
  } catch (error) {
    console.error('❌ Login error:', error)
    $q.notify({
      type: 'negative',
      message: `Cannot connect to server. Please check your connection.`,
      position: 'top',
    })
  } finally {
    isLoading.value = false
  }
}

const goToRegister = () => router.push('/x81-UserRegister')

const closeLogin = () => router.replace('/')
</script>

<template>
  <q-page
    class="q-pa-md"
    style="
      background-color: #f5f5f5;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    "
  >
    <div class="col-12 col-sm-8 col-md-5 col-lg-4">
      <q-card class="shadow-1">
        <!-- Title Bar with Close Button -->
        <q-card-section class="bg-primary text-white q-pa-sm">
          <div class="row items-center no-wrap">
            <div class="col text-h6 text-weight-bold">xBatch</div>
            <q-btn icon="close" flat round dense @click="closeLogin" size="sm" />
          </div>
        </q-card-section>

        <!-- Login Header -->
        <q-card-section class="text-center bg-primary text-white q-pt-md q-pb-lg">
          <img src="/logo_wide.svg" style="height: 60px; margin-bottom: 15px; filter: brightness(1.2)" />
          <div class="text-h4 text-weight-bold">User Login</div>
        </q-card-section>

        <!-- Form Content -->
        <q-card-section class="q-pa-lg">
          <!-- Email/Username Field -->
          <div class="q-mb-md">
            <q-input
              v-model="email"
              outlined
              label="Username or Email"
              dense
              @keyup.enter="handleLogin"
            >
              <template v-slot:prepend>
                <q-icon name="person" color="primary" />
              </template>
            </q-input>
          </div>

          <!-- Password Field -->
          <div class="q-mb-md">
            <q-input
              v-model="password"
              outlined
              :label="'Password'"
              :type="showPassword ? 'text' : 'password'"
              dense
              @keyup.enter="handleLogin"
            >
              <template v-slot:prepend>
                <q-icon name="lock" color="primary" />
              </template>
              <template v-slot:append>
                <q-icon
                  :name="showPassword ? 'visibility' : 'visibility_off'"
                  class="cursor-pointer"
                  color="primary"
                  @click="showPassword = !showPassword"
                />
              </template>
            </q-input>
          </div>

          <!-- Login Button -->
          <q-btn
            label="Login"
            color="primary"
            size="lg"
            class="full-width text-white text-weight-bold"
            :loading="isLoading"
            @click="handleLogin"
          />

          <!-- Divider -->
          <div class="q-my-md text-center">
            <q-separator color="primary" class="q-my-md" />
            <div class="text-caption">Don't have an account?</div>
          </div>

          <!-- Register Link -->
          <q-btn
            label="Create New Account"
            color="primary"
            outline
            size="lg"
            class="full-width text-weight-bold"
            @click="goToRegister"
          />

          <!-- Forgot Password -->
          <div class="text-center q-mt-md">
            <q-btn label="Forgot Password?" flat size="sm" color="primary" />
          </div>
        </q-card-section>

        <!-- Footer -->
        <q-card-section class="text-center text-caption bg-primary text-white">
          © 2026 xBatch. All rights reserved.
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>

<style scoped></style>

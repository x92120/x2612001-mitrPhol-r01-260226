<script setup lang="ts">
const { hasPermission, user, logout } = useAuth()
const { t, toggleLocale, localeFlag, localeName } = useI18n()
const $q = useQuasar()

// Zoom control
const ZOOM_KEY = 'app-zoom-level'
const zoomLevel = ref(parseFloat(localStorage.getItem(ZOOM_KEY) || '1.5'))

const applyZoom = () => {
  document.documentElement.style.zoom = String(zoomLevel.value)
  localStorage.setItem(ZOOM_KEY, String(zoomLevel.value))
}

const zoomLabel = computed(() => `${Math.round(zoomLevel.value * 100)}%`)

watch(zoomLevel, applyZoom)
onMounted(applyZoom)

const handleLogout = async () => {
  await logout()
  $q.notify({
    type: 'info',
    message: t('nav.loggedOut'),
    position: 'top',
  })
  navigateTo('/')
}
</script>

<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-primary text-white" height-hint="98">
      <q-toolbar>
        <q-toolbar-title>
          <div class="row items-center q-gutter-sm">
            <img src="/labels/xMixingLogo.svg" alt="xMixing" style="height: 32px; display: block;" />
          </div>
        </q-toolbar-title>

        <!-- Zoom Slider -->
        <div class="row items-center q-mr-md" style="min-width: 180px;">
          <q-icon name="zoom_out" size="xs" class="q-mr-xs" />
          <q-slider
            v-model="zoomLevel"
            :min="0.8"
            :max="2.5"
            :step="0.1"
            color="white"
            thumb-color="white"
            track-color="blue-3"
            dense
            style="flex: 1;"
          />
          <q-icon name="zoom_in" size="xs" class="q-ml-xs" />
          <span class="text-caption q-ml-sm" style="min-width: 35px; text-align: center;">{{ zoomLabel }}</span>
        </div>

        <!-- Language Toggle -->
        <q-btn flat round dense @click="toggleLocale" class="q-mr-sm">
          <span style="font-size: 30px">{{ localeFlag }}</span>
          <q-tooltip>{{ localeName }}</q-tooltip>
        </q-btn>

        <q-btn to="/x80-UserLogin" :label="t('nav.login')" flat icon="login" v-if="!user" />
        <q-btn :label="t('nav.logout')" flat icon="logout" v-if="user" @click="handleLogout" />
      </q-toolbar>

      <q-tabs align="left" dense>
        <q-route-tab to="/" icon="home" :label="t('nav.home')" />
        <q-route-tab
          to="/x10-IngredientIntake"
          icon="local_shipping"
          :label="t('nav.ingredientIntake')"
          v-if="hasPermission('ingredient_receipt')"
        />
        <q-route-tab to="/x20-Sku" icon="inventory_2" :label="t('nav.sku')" v-if="hasPermission('sku_management')" />
        <q-route-tab
          to="/x30-ProductionPlan"
          icon="account_tree"
          :label="t('nav.productionPlan')"
          v-if="hasPermission('production_planning')"
        />
        <q-route-tab
          to="/x40-PreBatch"
          icon="science"
          :label="t('nav.batchPrepare')"
          v-if="hasPermission('prepare_batch')"
        />
        <q-route-tab
          to="/x50-PackingList"
          icon="view_list"
          :label="t('nav.packingList')"
          v-if="hasPermission('production_list')"
        />
        <q-route-tab
          to="/x60-BatchRecheck"
          icon="fact_check"
          :label="t('nav.batchRecheck')"
          v-if="hasPermission('production_list')"
        />
        <q-route-tab to="/x89-UserConfig" icon="manage_accounts" :label="t('nav.user')" v-if="hasPermission('admin')" />
        <q-route-tab to="/x90-systemDashboard" icon="dashboard" :label="t('nav.systemDashboard')" v-if="hasPermission('admin')" />
        <q-route-tab to="/x99-About" icon="info" :label="t('nav.about')" />
      </q-tabs>
    </q-header>

    <q-page-container>
      <NuxtPage />
    </q-page-container>
  </q-layout>
</template>

<style>
/* Global styles if needed */
</style>

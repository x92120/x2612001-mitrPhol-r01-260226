<script setup lang="ts">
const { hasPermission, user, logout } = useAuth()
const { t, toggleLocale, localeFlag, localeName } = useI18n()
const $q = useQuasar()

// Zoom control
const ZOOM_KEY = 'app-zoom-level'
const zoomLevel = ref(1.5)

const applyZoom = () => {
  document.documentElement.style.zoom = String(zoomLevel.value)
  localStorage.setItem(ZOOM_KEY, String(zoomLevel.value))
}

const zoomOptions = [
  { label: '80%', value: 0.8 },
  { label: '90%', value: 0.9 },
  { label: '100%', value: 1.0 },
  { label: '110%', value: 1.1 },
  { label: '120%', value: 1.2 },
  { label: '130%', value: 1.3 },
  { label: '140%', value: 1.4 },
  { label: '150%', value: 1.5 },
  { label: '160%', value: 1.6 },
  { label: '170%', value: 1.7 },
  { label: '180%', value: 1.8 },
  { label: '190%', value: 1.9 },
  { label: '200%', value: 2.0 },
  { label: '210%', value: 2.1 },
  { label: '220%', value: 2.2 },
  { label: '230%', value: 2.3 },
  { label: '240%', value: 2.4 },
  { label: '250%', value: 2.5 },
]

watch(zoomLevel, applyZoom)
onMounted(() => {
  const stored = localStorage.getItem(ZOOM_KEY)
  if (stored) {
    zoomLevel.value = parseFloat(stored)
  } else {
    applyZoom()
  }
})

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

        <!-- Zoom Control: Slider + Dropdown -->
        <div class="row items-center q-mr-md" style="min-width: 220px;">
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
          <q-icon name="zoom_in" size="xs" class="q-mx-xs" />
          <q-select
            v-model="zoomLevel"
            :options="zoomOptions"
            emit-value
            map-options
            dense
            dark
            borderless
            style="min-width: 65px;"
            popup-content-style="min-width: 80px;"
          />
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

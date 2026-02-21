<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '~/composables/useAuth'
import { useQuasar } from 'quasar'
import { appConfig } from '~/appConfig/config'

const router = useRouter()
const route = useRoute()
const $q = useQuasar()
const { hasPermission, user, getAuthHeader } = useAuth()
const { t } = useI18n()

const formatDate = (date: any) => {
  if (!date) return '-'
  const d = new Date(date)
  if (isNaN(d.getTime())) return date
  return d.toLocaleDateString('en-GB')
}

const formatDateTime = (date: any) => {
  if (!date) return '-'
  const d = new Date(date)
  if (isNaN(d.getTime())) return date
  return d.toLocaleString('en-GB')
}

// Fetch dashboard statistics
const activeSKUCount = ref('0')
const ingredientStockCount = ref('0')
const pendingBatchesCount = ref('0')
const activeProductionsCount = ref('0')

// Helper to calculate relative time
const timeAgo = (dateOpt: string | Date) => {
  if (!dateOpt) return ''
  const date = new Date(dateOpt)
  const now = new Date()
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)
  
  let interval = seconds / 31536000
  if (interval > 1) return Math.floor(interval) + " years ago"
  
  interval = seconds / 2592000
  if (interval > 1) return Math.floor(interval) + " months ago"
  
  interval = seconds / 86400
  if (interval > 1) return Math.floor(interval) + " days ago"
  
  interval = seconds / 3600
  if (interval > 1) return Math.floor(interval) + " hours ago"
  
  interval = seconds / 60
  if (interval > 1) return Math.floor(interval) + " minutes ago"
  
  return Math.floor(seconds) + " seconds ago"
}

const systemStatus = ref({
  dbStatus: 'Operational',
  uptime: '99.9%',
  sync: 'Real-time',
  storageUsed: 0,
  storageTotal: 100, // Mock total
  storagePercent: 0.0,
  lastBackup: 'Unknown'
})

const fetchSystemStatus = async () => {
  try {
    const authHeaders = getAuthHeader() as Record<string, string>
    const res = await fetch(`${appConfig.apiBaseUrl}/server-status`, { headers: authHeaders })
    if (res.ok) {
      const data = await res.json()
      // Map API response to UI model (adjust fields based on actual API response)
      systemStatus.value = {
        dbStatus: data.status || 'Operational',
        uptime: data.uptime || '99.9%',
        sync: 'Real-time',
        storageUsed: data.disk_usage_gb || 0,
        storageTotal: data.disk_total_gb || 100,
        storagePercent: (data.disk_usage_gb || 0) / (data.disk_total_gb || 100),
        lastBackup: data.last_backup ? formatDateTime(data.last_backup) : '2 hours ago'
      }
    }
  } catch (e) {
    console.error('Failed to fetch system status', e)
  }
}

const fetchDashboardStats = async () => {
  try {
    const authHeaders = getAuthHeader() as Record<string, string>
    
    // Using Promise.all for faster parallel fetching
    const [skuRes, ingRes, batchRes, prodRes] = await Promise.all([
      fetch(`${appConfig.apiBaseUrl}/skus/`, { headers: authHeaders }),
      fetch(`${appConfig.apiBaseUrl}/ingredient-intake-lists/`, { headers: authHeaders }),
      fetch(`${appConfig.apiBaseUrl}/production-batches/`, { headers: authHeaders }), // Changed to production-batches for better status tracking
      fetch(`${appConfig.apiBaseUrl}/production-plans/`, { headers: authHeaders })
    ])

    const activities: any[] = []

    if (skuRes.ok) {
      const skus = await skuRes.json()
      activeSKUCount.value = skus.filter((s: any) => s.status === 'Active').length.toString()
      
      // Process SKU activities
      skus.forEach((s: any) => {
        if (s.created_at) {
          activities.push({
            id: `sku-${s.id}`,
            title: 'New SKU Created',
            description: `SKU: ${s.sku_name} added to system`,
            time: s.created_at,
            timestamp: new Date(s.created_at).getTime(),
            icon: 'add_circle',
            color: 'blue',
            user: s.creat_by || 'System'
          })
        }
      })
    }

    if (ingRes.ok) {
      const ingredients = await ingRes.json()
      ingredientStockCount.value = ingredients.filter((i: any) => i.status === 'Active').length.toString()
      
      // Process Ingredient activities
      ingredients.forEach((i: any) => {
        if (i.intake_at) {
          activities.push({
            id: `ing-${i.id}`,
            title: 'Ingredient Replenishment',
            description: `${i.material_description || i.mat_sap_code} received: ${i.intake_vol} ${i.uom || 'kg'}`,
            time: i.intake_at,
            timestamp: new Date(i.intake_at).getTime(),
            icon: 'local_shipping',
            color: 'purple',
            user: i.intake_by || 'Warehouse'
          })
        }
      })
    }

    if (batchRes.ok) {
      const batches = await batchRes.json()
      pendingBatchesCount.value = batches.filter((b: any) => 
        ['Pending', 'Planned', 'Created'].includes(b.status)
      ).length.toString()
      
      // Process Batch activities
      batches.forEach((b: any) => {
        if (b.updated_at || b.created_at) {
          const time = b.updated_at || b.created_at
          const isComplete = b.status === 'Completed' || b.done
          activities.push({
            id: `batch-${b.id}`,
            title: isComplete ? 'Batch Completed' : `Batch ${b.status}`,
            description: `Batch ${b.batch_id} is ${b.status}`,
            time: time,
            timestamp: new Date(time).getTime(),
            icon: isComplete ? 'check_circle' : 'play_circle',
            color: isComplete ? 'green' : 'orange',
            user: 'System' // Batch often doesn't have easy user field attached in list view
          })
        }
      })
    }

    if (prodRes.ok) {
      const productions = await prodRes.json()
      activeProductionsCount.value = productions.filter((p: any) => 
        ['In Progress', 'Running', 'Started'].includes(p.status)
      ).length.toString()
    }
    
    // Sort activities by timestamp desc and take top 10
    recentActivities.value = activities
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, 10)
      .map(a => ({...a, time: formatDateTime(a.time)}))

  } catch (error) {
    console.error('❌ Dashboard: Failed to fetch stats:', error)
  }
}

// Check for permission error on mount
onMounted(() => {
  if (route.query.error === 'no-permission') {
    $q.notify({
      type: 'negative',
      message: t('home.accessDenied'),
      position: 'top',
      timeout: 3000
    })
    // Clear the error query parameter
    router.replace({ query: {} })
  }
  
  // Fetch dashboard statistics
  fetchDashboardStats()
  fetchSystemStatus()
})

// Dashboard statistics
const stats = computed(() => [
  {
    labelKey: 'home.totalSKUs',
    label: t('home.totalSKUs'),
    value: activeSKUCount.value,
    icon: 'book',
    color: 'blue',
    path: '/x20-Recipe',
    permission: 'sku_management',
    description: t('home.manageSKU')
  },
  {
    labelKey: 'home.ingredientsStock',
    label: t('home.ingredientsStock'),
    value: ingredientStockCount.value,
    icon: 'inventory_2',
    color: 'green',
    path: '/x10-IngredientIntake',
    permission: 'ingredient_receipt',
    description: t('home.viewInventory')
  },
  {
    labelKey: 'home.pendingBatches',
    label: t('home.pendingBatches'),
    value: pendingBatchesCount.value,
    icon: 'production_quantity_limits',
    color: 'orange',
    path: '/x30-PreBatch',
    permission: 'prepare_batch',
    description: t('home.batchesWaiting')
  },
  {
    labelKey: 'home.activeProductions',
    label: t('home.activeProductions'),
    value: activeProductionsCount.value,
    icon: 'timeline',
    color: 'purple',
    path: '/x40-ProductionPlan',
    permission: 'production_planning',
    description: t('home.monitorProduction')
  },
])

// Recent activities
const recentActivities = ref<any[]>([])

// Quick access menu
const quickAccessMenus = computed(() => [
  {
    label: t('home.createSKU'),
    icon: 'create_new_folder',
    color: 'cyan-7',
    path: '/x20-Sku',
    permission: 'sku_management',
    description: t('home.createSKUDesc')
  },
  {
    label: t('home.ingredientIntake'),
    icon: 'add_box',
    color: 'light-blue-7',
    path: '/x10-IngredientIntake',
    permission: 'ingredient_receipt',
    description: t('home.registerMaterial')
  },
  {
    label: t('home.planBatch'),
    icon: 'event_note',
    color: 'warning',
    path: '/x30-ProductionPlan',
    permission: 'prepare_batch',
    description: t('home.scheduleBatch')
  },
  {
    label: t('home.startProduction'),
    icon: 'play_arrow',
    color: 'light-green-7',
    path: '/x40-PreBatch',
    permission: 'production_planning',
    description: t('home.initiateProduction')
  },
])

const navigateTo = (path: string) => {
  router.push(path)
}

const canAccess = (permission: string) => {
  return user.value && hasPermission(permission)
}
</script>

<template>
  <q-page class="q-pa-md bg-dark-page">
    <!-- Welcome Header -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <q-card class="bg-gradient text-white shadow-10">
          <q-card-section class="q-py-lg">
            <div class="row items-center no-wrap">
              <div class="col">
                <div class="row items-center q-mb-sm">
                  <q-avatar size="56px" class="q-mr-md shadow-2">
                    <div class="bg-white text-primary text-h5 text-weight-bold full-width full-height flex flex-center">
                      {{ user?.full_name?.charAt(0) || user?.username?.charAt(0) || 'U' }}
                    </div>
                  </q-avatar>
                  <div>
                    <div class="text-h4 text-weight-bold">{{ t('home.welcome') }}, {{ user?.full_name || user?.username || t('home.guest') }}</div>
                    <div class="text-subtitle1 text-grey-3">{{ user?.role || t('home.guestUser') }} | {{ user?.department || t('home.production') }}</div>
                  </div>
                </div>
                <div class="text-subtitle2 text-grey-2">
                  {{ t('home.manageDesc') }}
                </div>
                <div class="text-caption q-mt-md text-grey-4">
                  {{ t('home.accountStatus') }}: <span class="text-weight-bold text-green-3">{{ t('home.active') }}</span> | {{ t('home.systemOperational') }}
                </div>
              </div>
              <div class="col-auto q-pl-md gt-xs">
                <!-- Removed Logo as requested -->
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Statistics Dashboard -->
    <div class="row q-mb-lg q-col-gutter-md">
      <div v-for="stat in stats" :key="stat.label" class="col-12 col-sm-6 col-md-3">
        <q-card 
          class="stat-card bg-primary text-white" 
          :class="canAccess(stat.permission) ? 'cursor-pointer' : 'disabled-card'"
          @click="canAccess(stat.permission) ? navigateTo(stat.path) : null"
        >
          <q-card-section class="text-center">
            <q-icon :name="stat.icon" class="text-white q-mb-md" size="2.5rem" />
            <div class="text-h6 text-weight-bold">{{ stat.value }}</div>
            <div class="text-caption text-grey-4">{{ stat.label }}</div>
              <q-badge v-if="!canAccess(stat.permission)" color="grey-8" class="q-mt-sm">
              <q-icon name="lock" size="xs" class="q-mr-xs" />
              {{ t('common.noAccess') }}
            </q-badge>
            <q-tooltip v-else content-class="bg-accent" content-style="font-size: 28px">
              {{ stat.description }}
            </q-tooltip>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Quick Access Section -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <div class="text-h5 q-mb-md text-weight-bold text-white">{{ t('home.quickAccess') }}</div>
      </div>
      <div v-for="menu in quickAccessMenus" :key="menu.label" class="col-12 col-sm-6 col-md-3">
        <q-btn
          :label="menu.label"
          :icon="menu.icon"
          :color="menu.color"
          size="lg"
          class="full-width"
          padding="md"
          :disable="!canAccess(menu.permission)"
          @click="navigateTo(menu.path)"
        >
          <q-tooltip v-if="!canAccess(menu.permission)">
            {{ t('home.noPermission') }}
          </q-tooltip>
          <q-tooltip v-else content-class="bg-accent" content-style="font-size: 28px">
            {{ menu.description }}
          </q-tooltip>
        </q-btn>
      </div>
    </div>

    <!-- Recent Activities Section -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <q-card class="bg-dark text-white shadow-2">
          <q-card-section class="bg-primary">
            <div class="text-h5 text-weight-bold">{{ t('home.recentActivities') }}</div>
          </q-card-section>
          <q-separator color="grey-8" />
          <q-timeline layout="dense" color="secondary" class="q-pa-md">
            <q-timeline-entry
              v-for="activity in recentActivities"
              :key="activity.id"
              :icon="activity.icon"
              :color="activity.color"
              :title="activity.title"
              :subtitle="activity.time"
            >
              <div class="column">
                <span>{{ activity.description }}</span>
                <div class="row items-center q-mt-xs">
                  <q-icon name="person" size="xs" color="grey-5" class="q-mr-xs" />
                  <span class="text-caption text-grey-5">By: {{ activity.user }}</span>
                </div>
              </div>
            </q-timeline-entry>
            <div v-if="recentActivities.length === 0" class="text-center text-grey-5 q-pa-md">
              {{ t('home.noActivities') }}
            </div>
          </q-timeline>
        </q-card>
      </div>
    </div>

    <!-- System Information Footer -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <q-card class="bg-primary text-white">
          <q-card-section>
            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-6">
                <div class="text-subtitle2 text-weight-bold q-mb-sm">{{ t('home.systemStatus') }}</div>
                <q-linear-progress :value="0.95" color="positive" class="q-mb-md" />
                <div class="text-caption">
                  {{ t('home.database') }}: {{ systemStatus.dbStatus }} | {{ t('home.sync') }}: {{ systemStatus.sync }} | {{ t('home.uptime') }}: {{ systemStatus.uptime }}
                </div>
              </div>
              <div class="col-12 col-md-6">
                <div class="text-subtitle2 text-weight-bold q-mb-sm">{{ t('home.storageUsage') }}</div>
                <q-linear-progress :value="systemStatus.storagePercent" color="warning" class="q-mb-md" />
                <div class="text-caption">{{ t('home.used') }}: {{ systemStatus.storageUsed }} GB {{ t('common.of') }} {{ systemStatus.storageTotal }} GB | {{ t('home.lastBackup') }}: {{ systemStatus.lastBackup }}</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<style scoped>
.bg-dark-page {
  background-color: #0a0a20; /* Deep blue background */
}
.bg-gradient {
  background: linear-gradient(135deg, #0384fc 0%, #0260c0 100%);
}

.stat-card {
  transition: all 0.3s ease;
  border-radius: 8px;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 0 20px rgba(33, 150, 243, 0.5);
}

.disabled-card {
  opacity: 0.5;
  cursor: not-allowed !important;
  filter: grayscale(50%);
}

.disabled-card:hover {
  transform: none;
  box-shadow: none;
}
</style>

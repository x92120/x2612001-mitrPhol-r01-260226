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

// Fetch dashboard statistics
const activeSKUCount = ref('0')
const ingredientStockCount = ref('0')
const pendingBatchesCount = ref('0')
const activeProductionsCount = ref('0')

const fetchDashboardStats = async () => {
  try {
    const authHeaders = getAuthHeader() as Record<string, string>
    
    // Using Promise.all for faster parallel fetching
    const [skuRes, ingRes, batchRes, prodRes] = await Promise.all([
      fetch(`${appConfig.apiBaseUrl}/skus/`, { headers: authHeaders }),
      fetch(`${appConfig.apiBaseUrl}/ingredient-intake-lists/`, { headers: authHeaders }),
      fetch(`${appConfig.apiBaseUrl}/pre-batches/`, { headers: authHeaders }),
      fetch(`${appConfig.apiBaseUrl}/production-plans/`, { headers: authHeaders })
    ])

    if (skuRes.ok) {
      const skus = await skuRes.json()
      activeSKUCount.value = skus.filter((s: any) => s.status === 'Active').length.toString()
      if (stats.value[0]) stats.value[0].value = activeSKUCount.value
    }

    if (ingRes.ok) {
      const ingredients = await ingRes.json()
      ingredientStockCount.value = ingredients.filter((i: any) => i.status === 'Active').length.toString()
      if (stats.value[1]) stats.value[1].value = ingredientStockCount.value
    }

    if (batchRes.ok) {
      const batches = await batchRes.json()
      pendingBatchesCount.value = batches.filter((b: any) => 
        ['Pending', 'Planned'].includes(b.status)
      ).length.toString()
      if (stats.value[2]) stats.value[2].value = pendingBatchesCount.value
    }

    if (prodRes.ok) {
      const productions = await prodRes.json()
      activeProductionsCount.value = productions.filter((p: any) => 
        ['In Progress', 'Running'].includes(p.status)
      ).length.toString()
      if (stats.value[3]) stats.value[3].value = activeProductionsCount.value
    }
  } catch (error) {
    console.error('❌ Dashboard: Failed to fetch stats:', error)
  }
}

// Check for permission error on mount
onMounted(() => {
  if (route.query.error === 'no-permission') {
    $q.notify({
      type: 'negative',
      message: 'Access Denied: You do not have permission to access that page',
      position: 'top',
      timeout: 3000
    })
    // Clear the error query parameter
    router.replace({ query: {} })
  }
  
  // Fetch dashboard statistics
  fetchDashboardStats()
})

// Dashboard statistics
const stats = ref([
  {
    label: 'Total SKUs',
    value: '0',
    icon: 'book',
    color: 'blue',
    path: '/x20-Recipe',
    permission: 'sku_management',
    description: 'Manage Product SKUs and Formulations'
  },
  {
    label: 'Ingredients Stock',
    value: '0',
    icon: 'inventory_2',
    color: 'green',
    path: '/x10-IngredientIntake',
    permission: 'ingredient_receipt',
    description: 'View current inventory levels'
  },
  {
    label: 'Pending Batches',
    value: '0',
    icon: 'production_quantity_limits',
    color: 'orange',
    path: '/x30-PreBatch',
    permission: 'prepare_batch',
    description: 'Batches waiting for preparation'
  },
  {
    label: 'Active Productions',
    value: '0',
    icon: 'timeline',
    color: 'purple',
    path: '/x40-ProductionPlan',
    permission: 'production_planning',
    description: 'Monitor ongoing production runs'
  },
])

// Recent activities
const recentActivities = ref([
  {
    id: 1,
    title: 'Batch BP-2025-001 Started',
    description: 'Production batch started with SKU: Chocolate Mix',
    time: '2 hours ago',
    icon: 'play_circle',
    color: 'green',
    user: 'Operator-01',
  },
  {
    id: 2,
    title: 'New SKU Created',
    description: 'SKU: Vanilla Compound added to system',
    time: '5 hours ago',
    icon: 'add_circle',
    color: 'blue',
    user: 'cj (Admin)',
  },
  {
    id: 3,
    title: 'Ingredient Replenishment',
    description: 'Cocoa Butter received: 500kg',
    time: '1 day ago',
    icon: 'local_shipping',
    color: 'purple',
    user: 'Warehouse-Staff',
  },
  {
    id: 4,
    title: 'Batch Completed',
    description: 'Batch BP-2025-000 successfully completed',
    time: '2 days ago',
    icon: 'check_circle',
    color: 'green',
    user: 'Operator-01',
  },
])

// Quick access menu
const quickAccessMenus = ref([
  {
    label: 'Create SKU',
    icon: 'create_new_folder',
    color: 'cyan-7',
    path: '/x20-Sku',
    permission: 'sku_management',
    description: 'Create new product SKU definitions'
  },
  {
    label: 'Ingredient Intake',
    icon: 'add_box',
    color: 'light-blue-7',
    path: '/x10-IngredientIntake',
    permission: 'ingredient_receipt',
    description: 'Register incoming raw material lots'
  },
  {
    label: 'Plan Batch',
    icon: 'event_note',
    color: 'warning',
    path: '/x30-ProductionPlan',
    permission: 'prepare_batch',
    description: 'Schedule and prepare new batches'
  },
  {
    label: 'Start Production',
    icon: 'play_arrow',
    color: 'light-green-7',
    path: '/x40-PreBatch',
    permission: 'production_planning',
    description: 'Initiate production for planned batches'
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
                    <div class="text-h4 text-weight-bold">Welcome, {{ user?.full_name || user?.username || 'Guest' }}</div>
                    <div class="text-subtitle1 text-grey-3">{{ user?.role || 'Guest User' }} | {{ user?.department || 'Production' }}</div>
                  </div>
                </div>
                <div class="text-subtitle2 text-grey-2">
                  Manage your batches, recipes, and production efficiently
                </div>
                <div class="text-caption q-mt-md text-grey-4">
                  Account Status: <span class="text-weight-bold text-green-3">Active</span> | System: Operational
                </div>
              </div>
              <div class="col-auto q-pl-md gt-xs">
                <img src="/logo_wide.svg" style="height: 80px; filter: drop-shadow(0 0 10px rgba(0,0,0,0.3))" />
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
              No Access
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
        <div class="text-h5 q-mb-md text-weight-bold text-white">Quick Access</div>
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
            You don't have permission to access this feature
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
            <div class="text-h5 text-weight-bold">Recent Activities</div>
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
                <div class="text-subtitle2 text-weight-bold q-mb-sm">System Status</div>
                <q-linear-progress :value="0.95" color="positive" class="q-mb-md" />
                <div class="text-caption">
                  Database: Operational | Sync: Real-time | Uptime: 99.9%
                </div>
              </div>
              <div class="col-12 col-md-6">
                <div class="text-subtitle2 text-weight-bold q-mb-sm">Storage Usage</div>
                <q-linear-progress :value="0.65" color="warning" class="q-mb-md" />
                <div class="text-caption">Used: 6.5 GB of 10 GB | Last Backup: 2 hours ago</div>
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

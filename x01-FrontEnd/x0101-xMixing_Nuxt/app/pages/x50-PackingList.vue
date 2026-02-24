<script setup lang="ts">
/**
 * x50-PackingList.vue — Packing List View
 * ========================================
 * Fresh design — v2.0
 * 
 * Purpose:
 *   - View production plans & batches with their ingredient requirements
 *   - Scan prebatch bags → verify → confirm into packing boxes
 *   - Print packing box labels
 *
 * Backend API Endpoints:
 *   GET  /production-plans/             → plans with batches & reqs
 *   GET  /prebatch-recs/?limit=N&wh=X  → all prebatch records (weighed bags)
 *   GET  /prebatch-reqs/by-batch/{id}  → ingredient requirements for a batch
 *   GET  /warehouses/                   → warehouse list for filter
 */

import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { appConfig } from '../appConfig/config'
import { useAuth } from '../composables/useAuth'

const $q = useQuasar()
const { getAuthHeader, user } = useAuth()
const { t } = useI18n()

// --- State ---
const loading = ref(false)
const plans = ref<any[]>([])
const allRecords = ref<any[]>([])  // prebatch_recs (weighed bags)

// --- Lifecycle ---
onMounted(() => {
  fetchPlans()
})

// --- Data Fetching ---
const fetchPlans = async () => {
  loading.value = true
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/production-plans/?skip=0&limit=100`, {
      headers: getAuthHeader() as Record<string, string>
    })
    plans.value = data
  } catch (error) {
    console.error('Error fetching plans:', error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <q-page class="q-pa-md">
    <!-- Page is ready for new design -->
    <div class="text-h5 text-weight-bold q-mb-md">
      {{ t('nav.packingList') }}
    </div>

    <div class="text-grey-7 q-mb-lg">
      Plans loaded: {{ plans.length }}
    </div>
  </q-page>
</template>

<style scoped>
/* Ready for new styles */
</style>

<script setup lang="ts">
/**
 * x50-PackingList.vue — Packing List View v2.1
 * 3-Panel Layout: Production Plans | Warehouse Bags | Batch Packing
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { appConfig } from '../appConfig/config'
import { useAuth } from '../composables/useAuth'
import { useMqttLocalDevice } from '../composables/useMqttLocalDevice'

const $q = useQuasar()
const { getAuthHeader } = useAuth()
const { t } = useI18n()
const { lastScan, connect } = useMqttLocalDevice()

// ═══════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════
const loading = ref(false)
const loadingRecords = ref(false)
const plans = ref<any[]>([])
const allRecords = ref<any[]>([])       // All prebatch_recs (middle panel)
const batchRecords = ref<any[]>([])     // Records for selected batch (right panel)
const selectedBatch = ref<any>(null)
const selectedPlan = ref<any>(null)
const scanBatchId = ref('')
const scanFH = ref('')
const scanSPP = ref('')

// Scan simulation dialog
const showScanDialog = ref(false)
const scanDialogWh = ref<'FH' | 'SPP'>('FH')

// Warehouse sort
const whSortCol = ref<'bag_id' | 're_code' | 'weight' | 'status'>('re_code')
const whSortAsc = ref(true)

// ═══════════════════════════════════════════════════════════════════
// SOUND EFFECTS
// ═══════════════════════════════════════════════════════════════════
const playSound = async (type: 'correct' | 'wrong') => {
  try {
    const ctx = new AudioContext()
    await ctx.resume()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    gain.gain.value = 0.4
    if (type === 'correct') {
      osc.frequency.value = 880
      osc.type = 'sine'
      osc.start()
      setTimeout(() => { osc.frequency.value = 1320 }, 100)
      setTimeout(() => { osc.stop(); ctx.close() }, 250)
    } else {
      osc.frequency.value = 200
      osc.type = 'square'
      osc.start()
      setTimeout(() => { osc.frequency.value = 150 }, 150)
      setTimeout(() => { osc.stop(); ctx.close() }, 400)
    }
  } catch (e) {
    console.warn('Sound playback failed:', e)
  }
}

// ═══════════════════════════════════════════════════════════════════
// COMPUTED
// ═══════════════════════════════════════════════════════════════════

const activePlans = computed(() =>
  plans.value.filter(p => p.status !== 'Cancelled')
)

const isFH = (wh: string) =>
  wh?.toUpperCase().includes('FH') || wh?.toUpperCase().includes('FLAVOUR')

/** Get bags for the selected batch, grouped by warehouse using req_id linkage */
const bagsByWarehouse = computed((): { FH: any[]; SPP: any[] } => {
  const result = { FH: [] as any[], SPP: [] as any[] }
  if (!selectedBatch.value) return result
  // Use batch-specific records (fetched via /prebatch-recs/by-batch/)
  batchRecords.value.forEach(bag => {
    if (isFH(bag.wh || '')) {
      result.FH.push(bag)
    } else {
      result.SPP.push(bag)
    }
  })
  return result
})

/** Weight summaries */
const fhWeight = computed(() =>
  bagsByWarehouse.value.FH.reduce((sum: number, b: any) => sum + (b.net_volume || 0), 0)
)
const sppWeight = computed(() =>
  bagsByWarehouse.value.SPP.reduce((sum: number, b: any) => sum + (b.net_volume || 0), 0)
)
const totalWeight = computed(() => fhWeight.value + sppWeight.value)

/** Check if all bags are packed per warehouse */
const fhPackedCount = computed(() => bagsByWarehouse.value.FH.filter(b => isPacked(b)).length)
const sppPackedCount = computed(() => bagsByWarehouse.value.SPP.filter(b => isPacked(b)).length)
const allFhPacked = computed(() => bagsByWarehouse.value.FH.length > 0 && fhPackedCount.value === bagsByWarehouse.value.FH.length)
const allSppPacked = computed(() => bagsByWarehouse.value.SPP.length > 0 && sppPackedCount.value === bagsByWarehouse.value.SPP.length)

/** Sort helper for warehouse records */
const sortWarehouseRecords = (list: any[]) => {
  const col = whSortCol.value
  const asc = whSortAsc.value ? 1 : -1
  return [...list].sort((a, b) => {
    let va: any, vb: any
    if (col === 'bag_id') {
      va = a.batch_record_id || ''
      vb = b.batch_record_id || ''
    } else if (col === 're_code') {
      va = a.re_code || ''
      vb = b.re_code || ''
    } else if (col === 'weight') {
      va = a.net_volume || 0
      vb = b.net_volume || 0
    } else {
      va = a.packing_status || 0
      vb = b.packing_status || 0
    }
    if (va < vb) return -1 * asc
    if (va > vb) return 1 * asc
    return 0
  })
}

const toggleWhSort = (col: 'bag_id' | 're_code' | 'weight' | 'status') => {
  if (whSortCol.value === col) {
    whSortAsc.value = !whSortAsc.value
  } else {
    whSortCol.value = col
    whSortAsc.value = true
  }
}

const whSortIcon = (col: string) => {
  if (whSortCol.value !== col) return 'unfold_more'
  return whSortAsc.value ? 'arrow_upward' : 'arrow_downward'
}

/** Middle panel: ALL records grouped by warehouse, sorted */
const middlePanelFH = computed(() =>
  sortWarehouseRecords(allRecords.value.filter(r => isFH(r.wh || '')))
)
const middlePanelSPP = computed(() =>
  sortWarehouseRecords(allRecords.value.filter(r => !isFH(r.wh || '')))
)

/** Batch info for right panel */
const batchInfo = computed(() => {
  if (!selectedBatch.value) return null
  const plan = plans.value.find(p =>
    p.batches?.some((b: any) => b.batch_id === selectedBatch.value.batch_id)
  )
  return {
    batch_id: selectedBatch.value.batch_id,
    sku_name: plan?.sku_name || plan?.sku_id || '-',
    plan_id: plan?.plan_id || '-',
    batch_size: selectedBatch.value.batch_size || 0,
    status: selectedBatch.value.status,
  }
})

/** Scan dialog — list of bags filtered to correct ingredients for selected batch */
const scanDialogBags = computed(() => {
  const wh = scanDialogWh.value
  const whBags = wh === 'FH' ? middlePanelFH.value : middlePanelSPP.value
  // If a batch is selected, filter to only show bags with matching re_code
  if (selectedBatch.value) {
    const batchReqs = selectedBatch.value.reqs || []
    const requiredReCodes = new Set(batchReqs.map((r: any) => r.re_code))
    if (requiredReCodes.size === 0) return whBags
    return whBags.filter(b => requiredReCodes.has(b.re_code))
  }
  return whBags
})

// ═══════════════════════════════════════════════════════════════════
// DATA FETCHING
// ═══════════════════════════════════════════════════════════════════

const fetchPlans = async () => {
  loading.value = true
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/production-plans/?skip=0&limit=100`, {
      headers: getAuthHeader() as Record<string, string>
    })
    plans.value = data || []
  } catch (e) {
    console.error('Error fetching plans:', e)
    $q.notify({ type: 'negative', message: 'Failed to load production plans' })
  } finally {
    loading.value = false
  }
}

const fetchAllRecords = async () => {
  loadingRecords.value = true
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-recs/?limit=50`, {
      headers: getAuthHeader() as Record<string, string>
    })
    allRecords.value = data || []
  } catch (e) {
    console.error('Error fetching records:', e)
  } finally {
    loadingRecords.value = false
  }
}

const fetchBatchRecords = async (batchId: string) => {
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-recs/by-batch/${batchId}`, {
      headers: getAuthHeader() as Record<string, string>
    })
    batchRecords.value = data || []
  } catch (e) {
    console.error('Error fetching batch records:', e)
    batchRecords.value = []
  }
}

// ═══════════════════════════════════════════════════════════════════
// ACTIONS
// ═══════════════════════════════════════════════════════════════════

const onPlanClick = (plan: any) => {
  selectedPlan.value = plan
}

const onBatchClick = (batch: any, plan: any) => {
  selectedBatch.value = batch
  selectedPlan.value = plan
  scanBatchId.value = batch.batch_id
  fetchBatchRecords(batch.batch_id)
}

const onScanBatchEnter = () => {
  if (!scanBatchId.value) return
  for (const plan of plans.value) {
    const batch = plan.batches?.find((b: any) => b.batch_id === scanBatchId.value)
    if (batch) {
      selectedBatch.value = batch
      selectedPlan.value = plan
      fetchBatchRecords(batch.batch_id)
      $q.notify({ type: 'positive', message: `Batch ${batch.batch_id} loaded`, position: 'top' })
      return
    }
  }
  $q.notify({ type: 'warning', message: `Batch "${scanBatchId.value}" not found`, position: 'top' })
}

const isPacked = (bag: any) => bag.packing_status === 1
const getBagStatusColor = (bag: any) => isPacked(bag) ? 'green' : 'grey-5'
const getBagStatusIcon = (bag: any) => isPacked(bag) ? 'check_circle' : 'radio_button_unchecked'
const getBagStatusLabel = (bag: any) => isPacked(bag) ? 'Packed' : 'Waiting'
const getBagRowClass = (bag: any) => isPacked(bag) ? 'bg-green-1' : ''

/** Close packing box — ready to transfer */
const onCloseBox = (wh: 'FH' | 'SPP') => {
  $q.dialog({
    title: `Close ${wh} Packing Box`,
    message: `All ${wh} pre-batch bags are packed. Mark this box as Ready to Transfer?`,
    cancel: true,
    persistent: true,
    ok: { label: 'Confirm Transfer', color: wh === 'FH' ? 'green' : 'teal', icon: 'local_shipping' },
  }).onOk(() => {
    playSound('correct')
    $q.notify({
      type: 'positive',
      icon: 'local_shipping',
      message: `✅ ${wh} Packing Box closed — Ready to Transfer`,
      position: 'top',
      timeout: 3000,
    })
  })
}

// ── Scan Simulation ─────────────────────────────────────────────
const openScanSimulator = (wh: 'FH' | 'SPP') => {
  scanDialogWh.value = wh
  showScanDialog.value = true
}

const onSimScanClick = (bag: any) => {
  if (!selectedBatch.value) {
    playSound('wrong')
    $q.notify({ type: 'negative', message: 'Please select a Packing Box first!', icon: 'warning', position: 'top' })
    return
  }

  // Check if this bag belongs to the selected batch via req_id
  const batchReqs = selectedBatch.value.reqs || []
  const reqIds = new Set(batchReqs.map((r: any) => r.id))
  const belongsToBox = reqIds.has(bag.req_id)

  if (belongsToBox) {
    // Correct — this bag belongs to the selected packing box
    playSound('correct')
    bag.packing_status = 1 // Mark as packed locally
    const whLabel = scanDialogWh.value
    if (whLabel === 'FH') scanFH.value = bag.batch_record_id
    else scanSPP.value = bag.batch_record_id
    $q.notify({
      type: 'positive',
      icon: 'check_circle',
      message: `✅ Correct! ${bag.re_code} packed into box`,
      caption: bag.batch_record_id,
      position: 'top',
      timeout: 2000,
    })
  } else {
    // Wrong — this bag does NOT belong to the selected packing box
    playSound('wrong')
    $q.notify({
      type: 'negative',
      icon: 'error',
      message: `❌ Wrong box! This bag belongs to a different batch`,
      caption: `Bag: ${bag.batch_record_id} ≠ Box: ${selectedBatch.value.batch_id}`,
      position: 'top',
      timeout: 3000,
    })
  }
  showScanDialog.value = false
}

// Watch for MQTT scans
watch(lastScan, (scan) => {
  if (scan?.barcode) {
    scanBatchId.value = scan.barcode
    onScanBatchEnter()
  }
})

// ═══════════════════════════════════════════════════════════════════
// LIFECYCLE
// ═══════════════════════════════════════════════════════════════════

onMounted(() => {
  fetchPlans()
  fetchAllRecords()
  connect()
})
</script>

<template>
  <q-page class="q-pa-sm bg-grey-2">
    <!-- Page Header -->
    <div class="bg-blue-9 text-white q-pa-sm rounded-borders q-mb-sm shadow-2">
      <div class="row justify-between items-center">
        <div class="row items-center q-gutter-sm">
          <q-icon name="view_list" size="sm" />
          <div class="text-h6 text-weight-bolder">{{ t('nav.packingList') }}</div>
        </div>
        <div class="row items-center q-gutter-sm">
          <q-btn flat dense round icon="refresh" color="white" @click="fetchPlans(); fetchAllRecords()" :loading="loading">
            <q-tooltip>Refresh</q-tooltip>
          </q-btn>
          <div class="text-caption text-blue-2">v2.1</div>
        </div>
      </div>
    </div>

    <!-- 3-PANEL LAYOUT -->
    <div class="row q-col-gutter-sm" style="height: calc(100vh - 120px);">

      <!-- ═══ LEFT PANEL: Production Plans ═══ -->
      <div class="col-4 column">
        <q-card class="col column shadow-2">
          <q-card-section class="bg-blue-9 text-white q-py-xs">
            <div class="row items-center justify-between no-wrap">
              <div class="row items-center q-gutter-xs">
                <q-icon name="assignment" size="sm" />
                <div class="text-subtitle2 text-weight-bold">Production Plans</div>
              </div>
              <q-badge color="white" text-color="blue-9" class="text-weight-bold">
                {{ activePlans.length }}
              </q-badge>
            </div>
          </q-card-section>

          <div class="col relative-position">
            <q-scroll-area class="fit">
              <q-list dense separator class="text-caption">
                <template v-for="plan in activePlans" :key="plan.plan_id">
                  <q-expansion-item
                    expand-separator
                    :icon="selectedPlan?.plan_id === plan.plan_id ? 'radio_button_checked' : 'radio_button_unchecked'"
                    :label="plan.plan_id"
                    :caption="`${plan.sku_name || plan.sku_id} — ${plan.num_batches || 0} batches`"
                    :header-class="selectedPlan?.plan_id === plan.plan_id ? 'bg-blue-1 text-blue-9 text-weight-bold' : 'text-weight-medium'"
                    dense dense-toggle
                    @show="onPlanClick(plan)"
                  >
                    <q-list dense class="q-pl-md">
                      <template v-for="batch in (plan.batches || [])" :key="batch.batch_id">
                        <q-expansion-item
                          dense dense-toggle expand-separator
                          :icon="batch.batch_prepare ? 'check_circle' : 'pending'"
                          :icon-color="batch.batch_prepare ? 'green' : 'grey-5'"
                          :label="batch.batch_id.split('-').slice(-1)[0]"
                          :caption="batch.batch_prepare ? 'Prepared' : batch.status"
                          :header-class="selectedBatch?.batch_id === batch.batch_id ? 'bg-blue-1 text-blue-9' : (batch.batch_prepare ? 'bg-green-1 text-grey-6' : '')"
                          @show="onBatchClick(batch, plan)"
                        >
                          <q-list dense class="q-pl-md">
                            <q-item
                              v-for="req in (batch.reqs || [])" :key="req.id" dense
                              style="min-height: 24px;"
                              :class="req.status === 2 ? 'bg-green-1 text-grey-6' : ''"
                            >
                              <q-item-section avatar style="min-width: 20px;">
                                <q-icon
                                  :name="req.status === 2 ? 'check_circle' : (req.status === 1 ? 'hourglass_top' : 'circle')"
                                  :color="req.status === 2 ? 'green' : (req.status === 1 ? 'orange' : 'grey-4')"
                                  size="xs"
                                />
                              </q-item-section>
                              <q-item-section>
                                <q-item-label style="font-size: 0.7rem;">
                                  {{ req.re_code }} — {{ req.ingredient_name || req.re_code }}
                                </q-item-label>
                              </q-item-section>
                              <q-item-section side>
                                <q-item-label style="font-size: 0.65rem;" class="text-weight-bold">
                                  {{ req.required_volume?.toFixed(1) }} kg
                                </q-item-label>
                              </q-item-section>
                            </q-item>
                            <q-item v-if="!batch.reqs || batch.reqs.length === 0" style="min-height: 24px;">
                              <q-item-section class="text-grey text-italic" style="font-size: 0.65rem;">No requirements</q-item-section>
                            </q-item>
                          </q-list>
                        </q-expansion-item>
                      </template>
                      <q-item v-if="!plan.batches || plan.batches.length === 0" style="min-height: 28px;">
                        <q-item-section class="text-grey text-italic" style="font-size: 0.7rem;">No batches</q-item-section>
                      </q-item>
                    </q-list>
                  </q-expansion-item>
                </template>

                <div v-if="activePlans.length === 0" class="text-center q-pa-lg text-grey">
                  <q-icon name="inbox" size="lg" class="q-mb-sm" /><br>
                  No active plans
                </div>
              </q-list>
            </q-scroll-area>
          </div>
        </q-card>
      </div>

      <!-- ═══ MIDDLE PANEL: Warehouse Pre-Batch ═══ -->
      <div class="col-4 column">
        <q-card class="col column shadow-2">
          <q-card-section class="bg-blue-grey-8 text-white q-py-xs">
            <div class="row items-center justify-between no-wrap">
              <div class="row items-center q-gutter-xs">
                <q-icon name="warehouse" size="sm" />
                <div class="text-subtitle2 text-weight-bold">Warehouse Pre-Batch Packing</div>
              </div>
              <q-badge color="white" text-color="blue-grey-8" class="text-weight-bold">
                <q-spinner-dots v-if="loadingRecords" size="14px" color="blue-grey-8" class="q-mr-xs" />
                {{ middlePanelFH.length + middlePanelSPP.length }}
              </q-badge>
            </div>
          </q-card-section>

          <div class="col relative-position">
            <q-inner-loading :showing="loadingRecords">
              <q-spinner-gears size="40px" color="blue-grey" />
            </q-inner-loading>
            <q-scroll-area class="fit">
              <div v-if="!loadingRecords && allRecords.length === 0" class="text-center q-pa-lg text-grey">
                <q-icon name="inbox" size="lg" class="q-mb-sm" /><br>
                No pre-batch records found
              </div>

              <template v-else>
                <!-- FH Section -->
                <q-expansion-item
                  default-opened
                  header-class="bg-orange-8 text-white text-weight-bold"
                  expand-icon-class="text-white"
                >
                  <template v-slot:header>
                    <q-item-section avatar style="min-width: 30px;">
                      <q-icon name="science" color="white" />
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-weight-bold">FH Pre-Batch Packing</q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <q-badge color="white" text-color="orange-9">{{ middlePanelFH.length }}</q-badge>
                    </q-item-section>
                  </template>

                  <q-markup-table dense flat square separator="cell" class="bg-white" style="font-size: 0.75rem;">
                    <thead class="bg-orange-1 text-orange-10">
                      <tr>
                        <th class="text-left cursor-pointer" style="font-size: 0.7rem;" @click="toggleWhSort('bag_id')">
                          Bag ID <q-icon :name="whSortIcon('bag_id')" size="12px" />
                        </th>
                        <th class="text-left cursor-pointer" style="font-size: 0.7rem;" @click="toggleWhSort('re_code')">
                          Ingredient <q-icon :name="whSortIcon('re_code')" size="12px" />
                        </th>
                        <th class="text-right cursor-pointer" style="font-size: 0.7rem;" @click="toggleWhSort('weight')">
                          Weight <q-icon :name="whSortIcon('weight')" size="12px" />
                        </th>
                        <th class="text-center cursor-pointer" style="font-size: 0.7rem;" @click="toggleWhSort('status')">
                          Status <q-icon :name="whSortIcon('status')" size="12px" />
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="bag in middlePanelFH" :key="bag.id" :class="getBagRowClass(bag)">
                        <td class="text-weight-medium" style="font-size: 0.65rem;">{{ bag.batch_record_id?.split('-').slice(-2).join('-') }}</td>
                        <td style="font-size: 0.7rem;">{{ bag.re_code }}</td>
                        <td class="text-right text-weight-bold" style="font-size: 0.7rem;">{{ bag.net_volume?.toFixed(3) }}</td>
                        <td class="text-center">
                          <q-icon :name="getBagStatusIcon(bag)" :color="getBagStatusColor(bag)" size="xs" />
                        </td>
                      </tr>
                      <tr v-if="middlePanelFH.length === 0">
                        <td colspan="4" class="text-center text-grey text-italic q-pa-sm">No FH pre-batch</td>
                      </tr>
                    </tbody>
                  </q-markup-table>
                </q-expansion-item>

                <!-- SPP Section -->
                <q-expansion-item
                  default-opened
                  header-class="bg-teal-8 text-white text-weight-bold"
                  expand-icon-class="text-white"
                >
                  <template v-slot:header>
                    <q-item-section avatar style="min-width: 30px;">
                      <q-icon name="inventory_2" color="white" />
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-weight-bold">SPP</q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <q-badge color="white" text-color="teal-9">{{ middlePanelSPP.length }}</q-badge>
                    </q-item-section>
                  </template>

                  <q-markup-table dense flat square separator="cell" class="bg-white" style="font-size: 0.75rem;">
                    <thead class="bg-teal-1 text-teal-10">
                      <tr>
                        <th class="text-left cursor-pointer" style="font-size: 0.7rem;" @click="toggleWhSort('bag_id')">
                          Bag ID <q-icon :name="whSortIcon('bag_id')" size="12px" />
                        </th>
                        <th class="text-left cursor-pointer" style="font-size: 0.7rem;" @click="toggleWhSort('re_code')">
                          Ingredient <q-icon :name="whSortIcon('re_code')" size="12px" />
                        </th>
                        <th class="text-right cursor-pointer" style="font-size: 0.7rem;" @click="toggleWhSort('weight')">
                          Weight <q-icon :name="whSortIcon('weight')" size="12px" />
                        </th>
                        <th class="text-center cursor-pointer" style="font-size: 0.7rem;" @click="toggleWhSort('status')">
                          Status <q-icon :name="whSortIcon('status')" size="12px" />
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="bag in middlePanelSPP" :key="bag.id" :class="getBagRowClass(bag)">
                        <td class="text-weight-medium" style="font-size: 0.65rem;">{{ bag.batch_record_id?.split('-').slice(-2).join('-') }}</td>
                        <td style="font-size: 0.7rem;">{{ bag.re_code }}</td>
                        <td class="text-right text-weight-bold" style="font-size: 0.7rem;">{{ bag.net_volume?.toFixed(3) }}</td>
                        <td class="text-center">
                          <q-icon :name="getBagStatusIcon(bag)" :color="getBagStatusColor(bag)" size="xs" />
                        </td>
                      </tr>
                      <tr v-if="middlePanelSPP.length === 0">
                        <td colspan="4" class="text-center text-grey text-italic q-pa-sm">No SPP pre-batch</td>
                      </tr>
                    </tbody>
                  </q-markup-table>
                </q-expansion-item>
              </template>
            </q-scroll-area>
          </div>
        </q-card>
      </div>

      <!-- ═══ RIGHT PANEL: Packing Box + Packing List ═══ -->
      <div class="col-4 column q-gutter-y-sm">

        <!-- Section 1: Packing Box (from scan) -->
        <q-card class="shadow-2">
          <q-card-section class="bg-indigo-9 text-white q-py-xs">
            <div class="row items-center q-gutter-xs">
              <q-icon name="qr_code_scanner" size="sm" />
              <div class="text-subtitle2 text-weight-bold">Packing Box</div>
            </div>
          </q-card-section>
          <q-card-section class="q-py-sm">
            <q-input
              v-model="scanBatchId" outlined dense
              placeholder="Scan Packing Box Label..."
              bg-color="grey-1"
              @keyup.enter="onScanBatchEnter"
            >
              <template v-slot:prepend>
                <q-icon name="qr_code_scanner" color="indigo" />
              </template>
              <template v-slot:append>
                <q-btn flat round dense icon="search" color="indigo" @click="onScanBatchEnter" />
              </template>
            </q-input>

            <template v-if="batchInfo">
              <div class="q-mt-sm">
                <div class="row q-col-gutter-xs text-caption">
                  <div class="col-6">
                    <div class="text-grey-6">SKU Name</div>
                    <div class="text-weight-bold text-body2">{{ batchInfo.sku_name }}</div>
                  </div>
                  <div class="col-6">
                    <div class="text-grey-6">Plan ID</div>
                    <div class="text-weight-bold text-body2">{{ batchInfo.plan_id }}</div>
                  </div>
                  <div class="col-6 q-mt-xs">
                    <div class="text-grey-6">Batch Size</div>
                    <div class="text-weight-bold text-body2">{{ batchInfo.batch_size }} kg</div>
                  </div>
                  <div class="col-6 q-mt-xs">
                    <div class="text-grey-6">Status</div>
                    <q-badge
                      :color="batchInfo.status === 'Prepared' ? 'green' : (batchInfo.status === 'Created' ? 'grey' : 'blue')"
                      :label="batchInfo.status"
                    />
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="text-center text-grey q-pa-sm">
              <q-icon name="qr_code_2" size="md" class="q-mb-xs" /><br>
              <span class="text-caption">Scan or select a packing box</span>
            </div>
          </q-card-section>
        </q-card>

        <!-- Section 2: Packing List (FH + SPP cards) -->
        <q-card class="col column shadow-2">
          <q-card-section class="bg-blue-grey-9 text-white q-py-xs">
            <div class="row items-center justify-between no-wrap">
              <div class="row items-center q-gutter-xs">
                <q-icon name="inventory" size="sm" />
                <div class="text-subtitle2 text-weight-bold">Packing List</div>
              </div>
              <div v-if="selectedBatch" class="row items-center q-gutter-xs">
                <q-badge color="white" text-color="blue-grey-9" class="text-weight-bold">
                  {{ totalWeight.toFixed(1) }} kg
                </q-badge>
                <q-badge color="green-5" text-color="white" class="text-weight-bold">
                  FH {{ fhWeight.toFixed(1) }} kg
                </q-badge>
                <q-badge color="teal-5" text-color="white" class="text-weight-bold">
                  SPP {{ sppWeight.toFixed(1) }} kg
                </q-badge>
              </div>
            </div>
          </q-card-section>

          <div class="col relative-position">
            <q-scroll-area class="fit q-pa-xs">
              <div v-if="!selectedBatch" class="text-center q-pa-lg text-grey">
                <q-icon name="inventory_2" size="xl" class="q-mb-sm" /><br>
                Select a batch to view packing list
              </div>

              <template v-else>
                <!-- FH Packing Card -->
                <q-card flat bordered class="q-mb-sm">
                  <q-card-section class="bg-green-8 text-white q-py-xs">
                    <div class="row items-center justify-between no-wrap">
                      <div class="row items-center q-gutter-xs">
                        <q-icon name="science" size="xs" />
                        <span class="text-weight-bold text-caption">FH Pre-Batch Packing</span>
                      </div>
                      <div class="row items-center q-gutter-xs">
                        <q-badge color="white" text-color="green-9">{{ fhPackedCount }}/{{ bagsByWarehouse.FH.length }}</q-badge>
                        <q-btn
                          dense flat size="xs" icon="local_shipping" label="Transfer"
                          :color="allFhPacked ? 'white' : 'green-3'"
                          :disable="!allFhPacked"
                          @click="onCloseBox('FH')"
                          class="text-weight-bold"
                        >
                          <q-tooltip>{{ allFhPacked ? 'Close box — Ready to transfer' : `${bagsByWarehouse.FH.length - fhPackedCount} bags remaining` }}</q-tooltip>
                        </q-btn>
                      </div>
                    </div>
                  </q-card-section>

                  <!-- FH Scan Field -->
                  <q-card-section class="q-py-xs">
                    <q-input v-model="scanFH" outlined dense placeholder="Scan FH pre-batch bag..." bg-color="green-1">
                      <template v-slot:prepend>
                        <q-icon name="qr_code_scanner" color="green-8" size="sm" class="cursor-pointer" @click="openScanSimulator('FH')">
                          <q-tooltip>Click to simulate scan</q-tooltip>
                        </q-icon>
                      </template>
                    </q-input>
                  </q-card-section>

                  <q-list dense separator>
                    <q-item
                      v-for="bag in bagsByWarehouse.FH" :key="bag.id" dense
                      :class="isPacked(bag) ? 'bg-green-1' : 'bg-grey-1'"
                      style="min-height: 36px;"
                    >
                      <q-item-section avatar style="min-width: 24px;">
                        <q-icon :name="getBagStatusIcon(bag)" :color="getBagStatusColor(bag)" size="sm" />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label class="text-weight-bold" style="font-size: 0.75rem;">
                          {{ bag.re_code }} | {{ bag.net_volume?.toFixed(3) }} kg
                        </q-item-label>
                        <q-item-label caption style="font-size: 0.6rem;">
                          {{ bag.batch_record_id }}
                        </q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <q-badge :color="isPacked(bag) ? 'green' : 'grey-5'" :label="getBagStatusLabel(bag)" class="text-weight-bold" />
                      </q-item-section>
                    </q-item>
                    <q-item v-if="bagsByWarehouse.FH.length === 0">
                      <q-item-section class="text-center text-grey text-italic text-caption">No FH pre-batch for this box</q-item-section>
                    </q-item>
                  </q-list>
                </q-card>

                <!-- SPP Packing Card -->
                <q-card flat bordered>
                  <q-card-section class="bg-teal-8 text-white q-py-xs">
                    <div class="row items-center justify-between no-wrap">
                      <div class="row items-center q-gutter-xs">
                        <q-icon name="inventory_2" size="xs" />
                        <span class="text-weight-bold text-caption">SPP Pre-Batch Packing</span>
                      </div>
                      <div class="row items-center q-gutter-xs">
                        <q-badge color="white" text-color="teal-9">{{ sppPackedCount }}/{{ bagsByWarehouse.SPP.length }}</q-badge>
                        <q-btn
                          dense flat size="xs" icon="local_shipping" label="Transfer"
                          :color="allSppPacked ? 'white' : 'teal-3'"
                          :disable="!allSppPacked"
                          @click="onCloseBox('SPP')"
                          class="text-weight-bold"
                        >
                          <q-tooltip>{{ allSppPacked ? 'Close box — Ready to transfer' : `${bagsByWarehouse.SPP.length - sppPackedCount} bags remaining` }}</q-tooltip>
                        </q-btn>
                      </div>
                    </div>
                  </q-card-section>

                  <!-- SPP Scan Field -->
                  <q-card-section class="q-py-xs">
                    <q-input v-model="scanSPP" outlined dense placeholder="Scan SPP pre-batch bag..." bg-color="teal-1">
                      <template v-slot:prepend>
                        <q-icon name="qr_code_scanner" color="teal-8" size="sm" class="cursor-pointer" @click="openScanSimulator('SPP')">
                          <q-tooltip>Click to simulate scan</q-tooltip>
                        </q-icon>
                      </template>
                    </q-input>
                  </q-card-section>

                  <q-list dense separator>
                    <q-item
                      v-for="bag in bagsByWarehouse.SPP" :key="bag.id" dense
                      :class="isPacked(bag) ? 'bg-green-1' : 'bg-grey-1'"
                      style="min-height: 36px;"
                    >
                      <q-item-section avatar style="min-width: 24px;">
                        <q-icon :name="getBagStatusIcon(bag)" :color="getBagStatusColor(bag)" size="sm" />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label class="text-weight-bold" style="font-size: 0.75rem;">
                          {{ bag.re_code }} | {{ bag.net_volume?.toFixed(3) }} kg
                        </q-item-label>
                        <q-item-label caption style="font-size: 0.6rem;">
                          {{ bag.batch_record_id }}
                        </q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <q-badge :color="isPacked(bag) ? 'green' : 'grey-5'" :label="getBagStatusLabel(bag)" class="text-weight-bold" />
                      </q-item-section>
                    </q-item>
                    <q-item v-if="bagsByWarehouse.SPP.length === 0">
                      <q-item-section class="text-center text-grey text-italic text-caption">No SPP pre-batch for this box</q-item-section>
                    </q-item>
                  </q-list>
                </q-card>
              </template>
            </q-scroll-area>
          </div>
        </q-card>
      </div>
    </div>

    <!-- ═══ SCAN SIMULATION DIALOG ═══ -->
    <q-dialog v-model="showScanDialog" position="bottom" full-width>
      <q-card style="max-height: 60vh;">
        <q-card-section :class="scanDialogWh === 'FH' ? 'bg-green-8 text-white' : 'bg-teal-8 text-white'" class="q-py-sm">
          <div class="row items-center justify-between no-wrap">
            <div class="row items-center q-gutter-sm">
              <q-icon :name="scanDialogWh === 'FH' ? 'science' : 'inventory_2'" size="sm" />
              <div class="text-subtitle1 text-weight-bold">
                Simulate Scan — {{ scanDialogWh }} Pre-Batch
              </div>
            </div>
            <div class="row items-center q-gutter-xs">
              <q-badge color="white" :text-color="scanDialogWh === 'FH' ? 'green-9' : 'teal-9'">
                {{ scanDialogBags.length }} bags
              </q-badge>
              <q-btn flat round dense icon="close" color="white" v-close-popup />
            </div>
          </div>
          <div class="text-caption q-mt-xs" style="opacity: 0.8;">
            Click a bag to simulate scanning it into the packing box
          </div>
        </q-card-section>

        <q-separator />

        <q-card-section class="q-pa-none" style="max-height: 45vh; overflow: auto;">
          <q-list dense separator>
            <q-item
              v-for="bag in scanDialogBags" :key="bag.id"
              clickable v-ripple
              @click="onSimScanClick(bag)"
              :class="isPacked(bag) ? 'bg-green-1' : ''"
              style="min-height: 48px;"
            >
              <q-item-section avatar style="min-width: 30px;">
                <q-icon
                  :name="isPacked(bag) ? 'check_circle' : 'qr_code'"
                  :color="isPacked(bag) ? 'green' : 'grey-6'"
                  size="sm"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-bold" style="font-size: 0.8rem;">
                  {{ bag.re_code }} — {{ bag.net_volume?.toFixed(3) }} kg
                </q-item-label>
                <q-item-label caption style="font-size: 0.65rem;">
                  {{ bag.batch_record_id }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge
                  :color="isPacked(bag) ? 'green' : 'blue-grey'"
                  :label="isPacked(bag) ? 'Packed' : 'Tap to scan'"
                />
              </q-item-section>
            </q-item>
            <q-item v-if="scanDialogBags.length === 0">
              <q-item-section class="text-center text-grey q-pa-lg">
                <q-icon name="inbox" size="lg" class="q-mb-sm" /><br>
                No {{ scanDialogWh }} pre-batch bags available
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<style scoped>
.transition-all {
  transition: background-color 0.2s ease, color 0.2s ease;
}
</style>

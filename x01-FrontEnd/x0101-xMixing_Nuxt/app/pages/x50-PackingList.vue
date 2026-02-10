<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { appConfig } from '../appConfig/config'
import { useMqttLocalDevice } from '../composables/useMqttLocalDevice'
import { useAuth } from '../composables/useAuth'

const version = '1.1'
const $q = useQuasar()
const { getAuthHeader } = useAuth()
const { lastScan, connect } = useMqttLocalDevice()

// --- State ---
const selectedBatchId = ref<string>('')
const selectedWarehouse = ref<string>('All Warehouse')
const warehouses = ref<string[]>(['All Warehouse'])
const loading = ref(false)
const plansLoading = ref(false)
const allRecords = ref<PreBatchRec[]>([])
const plans = ref<any[]>([])
const pendingRecord = ref<PreBatchRec | null>(null)
const expandedRows = ref<any[]>([])
const expandedBatches = ref<any[]>([])

// For Scan Feedback Dialog
const scanFeedback = ref({
    show: false,
    success: false,
    message: '',
    title: ''
})

const planColumns: any[] = [
    { name: 'plan_id', label: 'Plan ID', field: 'plan_id', align: 'left', sortable: true },
    { name: 'sku_id', label: 'SKU-ID', field: 'sku_id', align: 'left', sortable: true },
    { name: 'plant', label: 'Plant', field: 'plant', align: 'center', sortable: true },
    { name: 'total_volume', label: 'Total Vol', field: 'total_volume', align: 'right', sortable: true },
    { 
        name: 'package_info', 
        label: 'Package', 
        field: 'package_info',
        align: 'center', 
        sortable: false 
    },
    { name: 'status', label: 'Status', field: 'status', align: 'center', sortable: true }
]

interface PreBatchReq {
    id: number
    batch_id: string
    re_code: string
    wh: string
    ingredient_name: string
    required_volume: number
}

interface PreBatchRec {
    id: number
    batch_record_id: string
    plan_id: string
    re_code: string
    net_volume: number
    package_no: number
    req_id?: number
    wh?: string
    isVerified?: boolean
}

// IDs of records that have been verified (packed) in this session
const verifiedRecordIds = ref<Set<string>>(new Set())
// IDs of records that have been confirmed & saved
const confirmedRecordIds = ref<Set<string>>(new Set())

// --- Computed ---

const plantId = computed(() => {
  if (!selectedBatchId.value) return '---'
  const parts = selectedBatchId.value.split('-')
  return parts.length > 2 ? parts[2] : 'Mixing'
})

const packagingSetId = computed(() => {
  if (!selectedBatchId.value) return 'GLOBAL-PACKING'
  return `PKG-${selectedBatchId.value}`
})

// Stats for footer
const totalBoxPackages = computed(() => verifiedRecordIds.value.size)
const totalAvailablePackages = computed(() => allRecords.value.length)

const currentWeight = computed(() => {
    return packedItems.value.reduce((sum: number, item: any) => sum + (item.net_volume || 0), 0)
})

const totalWeight = computed(() => {
    return allRecords.value.reduce((sum: number, item: any) => sum + (item.net_volume || 0), 0)
})

// Global Summary of ALL weighed records grouped by re_code
const reCodeSummary = computed(() => {
    const summary: Record<string, { re_code: string, count: number, weight: number }> = {}
    allRecords.value.forEach(rec => {
        const code = (rec.re_code || 'Unknown').trim().toUpperCase()
        if (!summary[code]) {
            summary[code] = { re_code: code, count: 0, weight: 0 }
        }
        summary[code].count++
        summary[code].weight += rec.net_volume || 0
    })
    return Object.values(summary).sort((a, b) => a.re_code.localeCompare(b.re_code))
})

// Group all pending records by Warehouse (if known) or by Re-Code
const groupedRequirements = computed(() => {
    const groups: Record<string, any[]> = {}
    
    // Group all pending bags by re_code for visibility
    const pendingBags = allRecords.value.filter(r => !verifiedRecordIds.value.has(r.batch_record_id))
    
    // For universal view, we group by re_code as the primary header
    pendingBags.forEach(bag => {
        const code = (bag.re_code || 'OTHER').trim().toUpperCase()
        if (!groups[code]) groups[code] = []
        groups[code].push(bag)
    })
    
    return groups
})

const pendingItems = computed(() => {
    return allRecords.value.filter(r => !verifiedRecordIds.value.has(r.batch_record_id))
})

const packedItems = computed(() => {
    return allRecords.value.filter(r => verifiedRecordIds.value.has(r.batch_record_id))
})

// --- Data Fetching ---
const fetchWarehouses = async () => {
    try {
        const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/warehouses/`, {
            headers: getAuthHeader() as Record<string, string>
        })
        const whIds = data.map(w => w.warehouse_id)
        warehouses.value = ['All Warehouse', ...whIds]
    } catch (error) {
        console.error('Error fetching warehouses:', error)
    }
}

const fetchAllData = async () => {
    loading.value = true
    try {
        const whParam = selectedWarehouse.value === 'All Warehouse' ? '' : `&wh=${selectedWarehouse.value}`
        const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-recs/?limit=1000${whParam}`, {
            headers: getAuthHeader() as Record<string, string>
        })
        allRecords.value = data
    } catch (error) {
        console.error('Error fetching all records:', error)
    } finally {
        loading.value = false
    }
}

const fetchPlans = async () => {
    plansLoading.value = true
    try {
        const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/production-plans/?skip=0&limit=100`, {
            headers: getAuthHeader() as Record<string, string>
        })
        plans.value = data
    } catch (error) {
        console.error('Error fetching plans:', error)
    } finally {
        plansLoading.value = false
    }
}

const getRecordsForBatch = (batchId: string) => {
    return allRecords.value.filter(r => r.batch_record_id.startsWith(batchId))
}

const getRecordsForBatchRequirement = (batchId: string, reCode: string) => {
    return allRecords.value.filter(r => r.plan_id.includes(batchId) && r.re_code === reCode)
}

const getReqStatus = (req: any) => {
    const records = getRecordsForBatchRequirement(req.batch_id, req.re_code)
    if (records.length === 0) return { code: 0, label: 'Awaiting', count: 0, total: 0 }

    const confirmedCount = records.filter(r => confirmedRecordIds.value.has(r.batch_record_id)).length
    const totalCount = records.length
    
    if (confirmedCount === totalCount && totalCount > 0) return { code: 2, label: 'Done', count: confirmedCount, total: totalCount }
    if (confirmedCount > 0 || verifiedRecordIds.value.size > 0) return { code: 1, label: 'Packing', count: confirmedCount, total: totalCount }
    return { code: 0, label: 'Awaiting', count: 0, total: 0 }
}

const isBatchDone = (batch: any) => {
    if (batch.status === 'Done') return true
    if (!batch.reqs || batch.reqs.length === 0) return false
    return batch.reqs.every((req: any) => getReqStatus(req).code === 2)
}

const getRecordsForPlan = (planId: string) => {
    return allRecords.value.filter(r => r.plan_id === planId)
}

// --- Watchers ---

watch(selectedWarehouse, () => {
    fetchAllData()
})

// HANDLE SCANS: 2-Step Verification (Ingredient -> Box)
watch(lastScan, (newScan) => {
    if (!newScan) return
    
    const barcode = newScan.barcode.trim()
    
    // STEP 2: Confirming with Box (Put into Box)
    if (pendingRecord.value) {
        if (barcode === pendingRecord.value.plan_id || barcode === `PKG-${pendingRecord.value.plan_id}`) {
            // Success: MOVE from Verified (Yellow) to Confirmed (Green)
            const recId = pendingRecord.value.batch_record_id
            confirmedRecordIds.value.add(recId)
            verifiedRecordIds.value.delete(recId) 
            
            // Success Dialog
            scanFeedback.value = {
                show: true,
                success: true,
                title: 'PACKED CORRECTLY!',
                message: `Ingredient [${pendingRecord.value.re_code}] is now confirmed inside Box [${barcode}].`
            }
            
            // Auto-select plan if not already set
            selectedBatchId.value = pendingRecord.value.plan_id
            pendingRecord.value = null
            return
        } else {
            // Check if user is trying to scan a NEW ingredient bag instead of the box
            const newIngredient = allRecords.value.find(r => r.batch_record_id === barcode)
            if (newIngredient) {
                // If it's a new bag, just switch the yellow blink to the new one
                // (Optionally keep the old one yellow, but usually only one is "active" in hands)
                pendingRecord.value = newIngredient
                verifiedRecordIds.value.add(barcode) 
                
                $q.notify({
                    type: 'info',
                    message: `Switched: Now scan Box for ${newIngredient.re_code}`,
                    position: 'top'
                })
                return
            } else {
                // Error Dialog
                scanFeedback.value = {
                    show: true,
                    success: false,
                    title: 'WRONG BOX!',
                    message: `CRITICAL: You scanned Box [${barcode}], but this ingredient belongs to Box [${pendingRecord.value.plan_id}]!`
                }
                return
            }
        }
    }

    // STEP 1: Scanning Ingredient Bag (Pick from Shelf)
    const record = allRecords.value.find(r => r.batch_record_id === barcode)
    
    if (record) {
        if (confirmedRecordIds.value.has(barcode)) {
            $q.notify({ type: 'warning', message: `Already Packed & Confirmed: ${barcode}`, position: 'top' })
        } else {
            // Mark as Yellow Blink
            verifiedRecordIds.value.add(barcode)
            pendingRecord.value = record
            
            // Auto-Expand the row
            if (!expandedRows.value.includes(record.plan_id)) {
                expandedRows.value = [...expandedRows.value, record.plan_id]
            }
            
            $q.notify({
                type: 'info',
                message: `Bag Verified: ${record.re_code}. STATUS: YELLOW BLINK. Now scan the BOX.`,
                icon: 'inventory',
                position: 'top',
                timeout: 5000
            })
        }
    } else {
        // Check if it's a Box scan without an ingredient
        const isPlanId = plans.value.some(p => p.plan_id === barcode || `PKG-${p.plan_id}` === barcode)
        if (isPlanId) {
            $q.notify({
                type: 'warning',
                message: `Box ${barcode} scanned, but no ingredient bag pending. Scan bag first!`,
                position: 'top'
            })
        } else {
            $q.notify({
                type: 'negative',
                message: `Unknown Barcode: ${barcode}`,
                position: 'top'
            })
        }
    }
})

onMounted(() => {
  connect()
  fetchWarehouses()
  fetchAllData()
  fetchPlans()
})

// --- Actions ---
const onCreatePackingList = () => {
    if (verifiedRecordIds.value.size === 0) {
        $q.notify({ type: 'warning', message: 'No items verified yet' })
        return
    }
    
    // Move verified items to confirmed status
    verifiedRecordIds.value.forEach(id => {
        confirmedRecordIds.value.add(id)
    })
    verifiedRecordIds.value.clear()
    
    $q.notify({ 
        type: 'positive', 
        message: 'Packing List Confirmed & Saved',
        icon: 'cloud_done'
    })
}

const simulateScanForBatch = (batchId: string) => {
    const records = getRecordsForBatch(batchId)
    // Find the first item that is not yet fully green
    const nextItem = records.find(r => !confirmedRecordIds.value.has(r.batch_record_id))
    
    if (!nextItem) {
        $q.notify({ type: 'info', message: 'All items for this batch are confirmed green.' })
        return
    }
    
    if (verifiedRecordIds.value.has(nextItem.batch_record_id)) {
        confirmedRecordIds.value.add(nextItem.batch_record_id)
        verifiedRecordIds.value.delete(nextItem.batch_record_id)
        $q.notify({ type: 'positive', message: `Box Scan: ${nextItem.re_code} confirmed!`, icon: 'check_circle' })
    } else {
        verifiedRecordIds.value.add(nextItem.batch_record_id)
        $q.notify({ type: 'info', message: `Bag Scan: ${nextItem.re_code} (Yellow Blink)`, icon: 'inventory' })
    }
}

const simulateScanForPlan = (planId: string) => {
    const records = getRecordsForPlan(planId)
    // Find the first item that is not yet fully green
    const nextItem = records.find(r => !confirmedRecordIds.value.has(r.batch_record_id))
    
    if (!nextItem) {
        $q.notify({ type: 'info', message: 'All items for this plan are already confirmed green.' })
        return
    }
    
    // If the item is already yellow (scanned bag), simulate the box scan to turn it green
    if (verifiedRecordIds.value.has(nextItem.batch_record_id)) {
        confirmedRecordIds.value.add(nextItem.batch_record_id)
        verifiedRecordIds.value.delete(nextItem.batch_record_id)
        
        $q.notify({
            type: 'positive',
            message: `Simulated Box Scan: ${nextItem.re_code} confirmed Green!`,
            icon: 'check_circle'
        })
    } else {
        // Otherwise, simulate the bag scan to turn it yellow blinking
        verifiedRecordIds.value.add(nextItem.batch_record_id)
        
        // Simulation Expand
        if (!expandedRows.value.includes(planId)) {
            expandedRows.value = [...expandedRows.value, planId]
        }
        
        $q.notify({
            type: 'info',
            message: `Simulated Bag Scan: ${nextItem.re_code} is now Yellow Blink (Pending Box)`,
            icon: 'inventory'
        })
    }
}

const onClosePackingList = () => {
  verifiedRecordIds.value.clear()
  selectedBatchId.value = ''
  $q.notify({ type: 'grey', message: 'Session Cleared' })
}

const onPrintPackingList = () => {
    if (verifiedRecordIds.value.size === 0) {
        $q.notify({ type: 'warning', message: 'Nothing to print' })
        return
    }
    window.print() 
}

const onManualAdd = (item: any) => {
    verifiedRecordIds.value.add(item.batch_record_id)
    const parts = item.batch_record_id.split('-')
    if (parts.length >= 6) {
        selectedBatchId.value = parts.slice(0, 6).join('-')
    }
}

</script>

<template>
  <q-page class="q-pa-md bg-white">
    <!-- Header Version -->
    <div class="row justify-between items-center q-mb-sm">
      <div class="text-h6 text-primary">List all Packing</div>
      <div class="text-caption text-weight-bold">Version {{ version }}</div>
    </div>

    <div class="row q-col-gutter-md justify-center">
      <!-- LEFT COLUMN: SIDEBAR -->
      <div class="col-12 col-md-5 column q-gutter-y-sm">
        <!-- CUSTOM WAREHOUSE FILTER -->
        <q-select
            outlined
            dense
            v-model="selectedWarehouse"
            :options="warehouses"
            label="Filter by Warehouse Station"
            bg-color="white"
            class="shadow-1"
        >
            <template v-slot:prepend>
                <q-icon name="warehouse" color="primary" />
            </template>
        </q-select>

        <!-- CARD 1: Global Summary Table -->
        <q-card class="col column bg-white shadow-2" style="max-height: 42vh; min-height: 350px;">
            <div class="q-pa-sm bg-blue-grey-8 text-white text-weight-bold text-subtitle2 flex justify-between items-center">
                <span>{{ selectedWarehouse === 'All Warehouse' ? 'Global Summary' : selectedWarehouse + ' Summary' }}</span>
                <q-btn icon="refresh" flat round dense color="white" @click="fetchAllData" :loading="loading" />
            </div>

            <div class="col relative-position">
                <q-scroll-area class="fit">
                   <div class="q-pa-none">
                       <q-markup-table dense flat bordered class="text-caption" separator="cell">
                            <thead class="bg-blue-grey-2">
                                <tr>
                                    <th class="text-left">Ingredient Code</th>
                                    <th class="text-center">Total Bags</th>
                                    <th class="text-right">Total Weight (kg)</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="row in reCodeSummary" :key="row.re_code" class="hover-bg">
                                    <td class="text-left text-weight-bold text-primary">{{ row.re_code }}</td>
                                    <td class="text-center">{{ row.count }}</td>
                                    <td class="text-right">{{ row.weight.toFixed(3) }}</td>
                                </tr>
                                <tr v-if="reCodeSummary.length === 0">
                                    <td colspan="3" class="text-center text-grey q-pa-md">
                                        {{ loading ? 'Data Loading...' : 'No pre-batched materials found' }}
                                    </td>
                                </tr>
                            </tbody>
                       </q-markup-table>
                   </div>
                </q-scroll-area>
            </div>
        </q-card>

        <!-- CARD 2: Individual Bags List (Grouped by Ingredient Code) -->
        <div class="list-container q-pa-none shadow-2" style="height: 450px;">
          <!-- Header -->
          <div class="row items-center q-pa-sm bg-blue-grey-8 text-white border-bottom">
            <div class="col-12 text-weight-bold">Awaiting Scan (Ready Bags)</div>
          </div>

          <!-- List Items Grouped by Code -->
          <div class="col scroll">
            <div
              v-if="pendingItems.length === 0"
              class="q-pa-md text-grey-6 text-center"
            >
              {{ loading ? 'Loading...' : 'Everything is packed!' }}
            </div>
            
            <div v-for="(bags, code) in groupedRequirements" :key="code">
              <!-- Header -->
              <div class="row items-center q-pa-sm bg-blue-grey-2 text-blue-grey-9 text-weight-bold border-bottom">
                <q-icon name="inventory_2" class="q-mr-sm" size="xs" />
                {{ code }} ({{ bags.length }} bags)
              </div>
              
              <div
                v-for="item in bags"
                :key="item.batch_record_id"
                v-ripple
                class="row items-center q-pa-sm border-bottom cursor-pointer hover-bg bg-white"
              >
                <div class="col-10 text-body2">
                  <div class="text-weight-bold text-primary">{{ item.batch_record_id }}</div>
                  <div class="text-caption">Net: <b>{{ item.net_volume }}</b> kg | WH: <q-badge color="grey-3" text-color="black">{{ item.wh || '-' }}</q-badge></div>
                </div>
                <div class="col-2 text-right">
                  <q-btn icon="check" flat round dense color="grey-3" @click.stop="onManualAdd(item)">
                      <q-tooltip>Manual Verify</q-tooltip>
                  </q-btn>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- MIDDLE GAP: Scan Status Flow -->
      <div class="col-12 col-md-1 flex flex-center column q-gutter-y-lg">
        <div class="column items-center">
            <q-icon 
                name="inventory_2" 
                :color="pendingRecord ? 'primary' : 'grey-4'" 
                size="44px" 
                class="transition-all"
                :class="pendingRecord ? 'q-animate-bounce' : ''"
            />
            <div class="text-caption text-weight-bold" :class="pendingRecord ? 'text-primary' : 'text-grey-4'">BAG</div>
        </div>
        
        <q-icon name="arrow_downward" color="grey-3" size="sm" />

        <div class="column items-center">
            <q-icon 
                name="qr_code_scanner" 
                :color="pendingRecord ? 'orange-8' : 'grey-4'" 
                size="44px" 
                :class="pendingRecord ? 'q-animate-pulse' : ''"
            />
            <div class="text-caption text-weight-bold" :class="pendingRecord ? 'text-orange-8' : 'text-grey-4'">BOX</div>
        </div>

        <div v-if="pendingRecord" class="q-mt-xl">
             <q-btn flat round color="negative" icon="close" size="sm" @click="pendingRecord = null">
                 <q-tooltip>Cancel Packing</q-tooltip>
             </q-btn>
        </div>
      </div>

      <!-- RIGHT COLUMN: Production Plan List -->
      <div class="col-12 col-md-5 column q-gutter-y-sm">
        <q-card class="col column bg-white shadow-2" style="height: 800px;">
            <div class="q-pa-sm bg-primary text-white text-weight-bold text-subtitle2 flex justify-between items-center">
                <span>Product Plan List</span>
                <q-btn icon="refresh" flat round dense color="white" @click="fetchPlans" :loading="plansLoading" />
            </div>

            <div class="col relative-position">
                <q-table
                  v-model:expanded="expandedRows"
                  :rows="plans"
                  :columns="planColumns"
                  row-key="plan_id"
                  flat
                  dense
                  class="text-caption"
                  :loading="plansLoading"
                  binary-state-sort
                >
                  <template v-slot:header="props">
                    <q-tr :props="props" class="bg-blue-grey-2">
                      <q-th auto-width />
                      <q-th v-for="col in props.cols" :key="col.name" :props="props">
                        {{ col.label }}
                      </q-th>
                    </q-tr>
                  </template>

                  <template v-slot:body="props">
                    <q-tr :props="props" class="hover-bg cursor-pointer" @click="props.expand = !props.expand">
                      <q-td auto-width>
                        <q-btn size="sm" color="primary" round flat :icon="props.expand ? 'expand_less' : 'expand_more'" @click.stop="props.expand = !props.expand" />
                      </q-td>
                      <q-td key="plan_id" :props="props" class="text-weight-bold text-primary">
                        {{ props.row.plan_id }}
                      </q-td>
                      <q-td key="sku_id" :props="props">
                        {{ props.row.sku_id }}
                      </q-td>
                      <q-td key="plant" :props="props" class="text-center">
                        {{ props.row.plant }}
                      </q-td>
                      <q-td key="total_volume" :props="props" class="text-right">
                        {{ props.row.total_volume }}
                      </q-td>
                      <q-td key="package_info" :props="props" class="text-center">
                        <q-badge color="grey-2" text-color="primary" class="text-weight-bold" outline>
                            {{ (props.row.batches?.filter((b: any) => b.status === 'Done').length || 0) }}/{{ (props.row.batches?.length || 0) }}
                        </q-badge>
                      </q-td>
                      <q-td key="status" :props="props" class="text-center">
                        <q-badge :color="props.row.status === 'Cancelled' ? 'negative' : 'positive'">
                          {{ props.row.status }}
                        </q-badge>
                      </q-td>
                    </q-tr>
                    <q-tr v-show="props.expand" :props="props" class="bg-blue-grey-1">
                      <q-td colspan="100%">
                        <div class="q-pa-sm">
                          <div class="text-weight-bold q-mb-md">Batches for Plan: {{ props.row.plan_id }}</div>
                          
                          <q-list class="bg-white rounded-borders shadow-1">
                            <q-expansion-item
                              v-for="batch in props.row.batches"
                              :key="batch.id"
                              group="batches"
                              header-class="bg-blue-grey-2 text-primary text-weight-bold"
                              expand-icon-class="text-primary"
                            >
                              <template v-slot:header>
                                <q-item-section avatar>
                                  <q-icon name="layers" color="primary" />
                                </q-item-section>
                                <q-item-section>
                                  <q-item-label>{{ batch.batch_id }}</q-item-label>
                                  <q-item-label caption>Batch Size: {{ batch.batch_size }} kg</q-item-label>
                                </q-item-section>
                                  <q-item-section side>
                                  <q-badge :color="isBatchDone(batch) ? 'positive' : 'orange'">
                                    {{ isBatchDone(batch) ? 'Done' : batch.status }}
                                  </q-badge>
                                </q-item-section>
                              </template>

                              <q-card class="bg-grey-1">
                                <q-card-section class="q-pa-sm">
                                  <div class="row items-center justify-between q-mb-xs">
                                      <div class="text-caption text-weight-bold">Scanned Packs for Batch</div>
                                      <q-btn flat round dense color="primary" icon="qr_code_scanner" size="sm" @click="simulateScanForBatch(batch.batch_id)">
                                          <q-tooltip>Simulate Scan Batch</q-tooltip>
                                      </q-btn>
                                  </div>

                                  <q-markup-table dense flat bordered separator="cell" style="background: white">
                                    <thead>
                                      <tr class="bg-grey-2">
                                        <th style="width: 40px"></th>
                                        <th class="text-left">Ingredient</th>
                                        <th class="text-left">Description</th>
                                        <th class="text-right">Required Wt</th>
                                        <th class="text-center">Status</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      <template v-for="req in batch.reqs" :key="req.id">
                                        <tr>
                                          <td class="text-center">
                                            <q-btn 
                                              v-if="getRecordsForBatchRequirement(batch.batch_id, req.re_code).length > 0"
                                              size="xs" 
                                              flat 
                                              round 
                                              color="primary" 
                                              :icon="expandedBatches.includes(req.id) ? 'keyboard_arrow_up' : 'keyboard_arrow_down'"
                                              @click="expandedBatches.includes(req.id) ? expandedBatches = expandedBatches.filter(id => id !== req.id) : expandedBatches = [...expandedBatches, req.id]"
                                            />
                                          </td>
                                          <td class="text-left text-weight-bold text-primary">
                                            {{ req.re_code }}
                                            <div v-if="getRecordsForBatchRequirement(batch.batch_id, req.re_code).length > 1" class="text-caption text-grey-6 text-weight-regular">
                                                {{ getRecordsForBatchRequirement(batch.batch_id, req.re_code).length }} Bags
                                            </div>
                                          </td>
                                          <td class="text-left">{{ req.ingredient_name }}</td>
                                          <td class="text-right">{{ req.required_volume }} kg</td>
                                          <td class="text-center">
                                            <div class="column items-center">
                                                <q-badge :color="getReqStatus(req).code === 2 ? 'positive' : (getReqStatus(req).code === 1 ? 'warning' : 'grey-5')">
                                                    {{ getReqStatus(req).label }}
                                                    <span v-if="getReqStatus(req).total > 0" class="q-ml-xs">
                                                        ({{ getReqStatus(req).count }}/{{ getReqStatus(req).total }})
                                                    </span>
                                                </q-badge>
                                                <q-linear-progress 
                                                    v-if="getReqStatus(req).total > 0" 
                                                    :value="getReqStatus(req).count / getReqStatus(req).total" 
                                                    :color="getReqStatus(req).code === 2 ? 'positive' : 'warning'"
                                                    size="xs"
                                                    class="q-mt-xs"
                                                    style="width: 60px"
                                                />
                                            </div>
                                          </td>
                                        </tr>
                                        <!-- Sub-rows for Scanned Bags -->
                                        <tr v-if="expandedBatches.includes(req.id)" class="bg-blue-grey-1">
                                          <td colspan="5" class="q-pa-none">
                                            <q-markup-table dense flat bordered square class="q-ml-md q-mr-sm q-mb-sm">
                                              <thead class="bg-white">
                                                <tr class="text-grey-7" style="font-size: 0.8em">
                                                  <th>Record ID</th>
                                                  <th>Pkg #</th>
                                                  <th>Net Wt</th>
                                                  <th>Status</th>
                                                </tr>
                                              </thead>
                                              <tbody class="bg-white">
                                                <tr v-for="rec in getRecordsForBatchRequirement(batch.batch_id, req.re_code)" :key="rec.id" style="font-size: 0.85em">
                                                  <td class="text-blue-8">{{ rec.batch_record_id }}</td>
                                                  <td class="text-center">{{ rec.package_no }}</td>
                                                  <td class="text-right">{{ rec.net_volume }} kg</td>
                                                  <td class="text-center">
                                                    <q-icon 
                                                      :name="confirmedRecordIds.has(rec.batch_record_id) ? 'check_circle' : 'pending'" 
                                                      :color="confirmedRecordIds.has(rec.batch_record_id) ? 'positive' : 'warning'" 
                                                      size="xs"
                                                      :class="{ 'blink-yellow': !confirmedRecordIds.has(rec.batch_record_id) }"
                                                    />
                                                  </td>
                                                </tr>
                                              </tbody>
                                            </q-markup-table>
                                          </td>
                                        </tr>
                                      </template>
                                      <tr v-if="!batch.reqs || batch.reqs.length === 0">
                                        <td colspan="5" class="text-center text-grey italic q-pa-sm">No requirements found for this batch</td>
                                      </tr>
                                    </tbody>
                                  </q-markup-table>
                                </q-card-section>
                              </q-card>
                            </q-expansion-item>
                            
                            <q-item v-if="!props.row.batches || props.row.batches.length === 0" class="text-center text-grey italic q-pa-md justify-center">
                                No batches found for this plan
                            </q-item>
                          </q-list>
                        </div>
                      </q-td>
                    </q-tr>
                  </template>
                </q-table>
            </div>

            <!-- ACTIONS FOOTER -->
            <q-separator />
            <q-card-actions align="right" class="q-pa-md bg-blue-grey-1">
                <q-btn 
                    unelevated 
                    color="primary" 
                    icon="check_circle" 
                    label="Confirm Packing Table" 
                    size="lg" 
                    class="full-width text-weight-bold"
                    no-caps
                    @click="onCreatePackingList"
                />
                <div class="row full-width q-gutter-x-sm q-mt-sm">
                    <q-btn outline color="grey-7" label="Clear List" class="col" no-caps @click="onClosePackingList" />
                    <q-btn outline color="blue-grey-8" icon="print" label="Print" class="col" no-caps @click="onPrintPackingList" />
                </div>
            </q-card-actions>
        </q-card>
      </div>
    </div>

    <!-- SCAN FEEDBACK DIALOG -->
    <q-dialog v-model="scanFeedback.show" position="top">
        <q-card style="width: 450px; border-radius: 12px;" :class="scanFeedback.success ? 'bg-positive text-white' : 'bg-negative text-white'">
            <q-card-section class="row items-center q-pb-none">
                <div class="text-h5 text-weight-bolder">{{ scanFeedback.title }}</div>
                <q-space />
                <q-btn icon="close" flat round dense v-close-popup />
            </q-card-section>

            <q-card-section class="column items-center q-pa-xl">
                <q-icon 
                    :name="scanFeedback.success ? 'check_circle' : 'error'" 
                    size="120px" 
                    class="q-mb-md"
                />
                <div class="text-subtitle1 text-center text-weight-medium">
                    {{ scanFeedback.message }}
                </div>
            </q-card-section>

            <q-card-section class="q-pt-none text-center">
                <q-btn 
                    unelevated 
                    :color="scanFeedback.success ? 'white' : 'white'" 
                    :text-color="scanFeedback.success ? 'positive' : 'negative'"
                    label="CONTINUE" 
                    class="q-px-xl text-weight-bold"
                    v-close-popup 
                />
            </q-card-section>
        </q-card>
    </q-dialog>
  </q-page>
</template>

<style scoped>
.list-container {
  border: 1px solid #ccc;
  border-radius: 4px;
  height: 500px;
  background-color: white;
  display: flex;
  flex-direction: column;
}

.packing-list-container {
  border: 1px solid #ccc;
  border-radius: 4px;
  height: 500px; /* Matched to list-container */
  background-color: white;
  display: flex;
  flex-direction: column;
}

.border-bottom {
  border-bottom: 1px solid #ccc;
}

.border-top {
  border-top: 2px solid #777;
}

.hover-bg:hover {
    background-color: #e3f2fd !important;
    transition: background-color 0.2s ease;
}

.blink-yellow {
  color: #f1c40f !important;
  animation: blink-animation 0.8s ease-in-out infinite;
}

@keyframes blink-animation {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.3; transform: scale(0.8); }
  100% { opacity: 1; transform: scale(1); }
}

.q-animate-blink {
  animation: blink-simple 1s infinite;
}

@keyframes blink-simple {
  50% { opacity: 0; }
}
</style>

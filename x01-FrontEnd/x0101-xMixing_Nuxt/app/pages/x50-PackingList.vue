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
const allRecords = ref<PreBatchRec[]>([])

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

// --- Watchers ---

watch(selectedWarehouse, () => {
    fetchAllData()
})

// HANDLE SCANS
watch(lastScan, (newScan) => {
    if (!newScan) return
    
    const barcode = newScan.barcode.trim()
    
    // Check if this barcode exists in ANY record we have
    const record = allRecords.value.find(r => r.batch_record_id === barcode)
    
    if (record) {
        if (verifiedRecordIds.value.has(barcode)) {
            $q.notify({
                type: 'warning',
                message: `Already Verified: ${barcode}`,
                position: 'top'
            })
        } else {
            verifiedRecordIds.value.add(barcode)
            // Auto-set the batch ID from the first scan or update it
            const parts = barcode.split('-')
            if (parts.length >= 6) {
                // Assuming format: plan-Line-X-YYYY-MM-DD-BATCH-RECODE-PKG
                // We want: plan-Line-X-YYYY-MM-DD-BATCH
                selectedBatchId.value = parts.slice(0, 6).join('-')
            }
            
            $q.notify({
                type: 'positive',
                message: `Verified: ${record.re_code} from ${selectedBatchId.value}`,
                icon: 'check_circle',
                position: 'top'
            })
        }
    } else {
        $q.notify({
            type: 'negative',
            message: `Unknown Package! ${barcode} not found in system.`,
            position: 'top',
            timeout: 5000
        })
    }
})

onMounted(() => {
  connect()
  fetchWarehouses()
  fetchAllData()
})

// --- Actions ---
const onCreatePackingList = () => {
    if (verifiedRecordIds.value.size === 0) {
        $q.notify({ type: 'warning', message: 'No items verified yet' })
        return
    }
    $q.notify({ type: 'positive', message: 'Packing List Created Successfully' })
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

    <div class="row q-col-gutter-md">
      <!-- LEFT COLUMN: SIDEBAR -->
      <div class="col-12 col-md-4 column q-gutter-y-sm">
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

      <!-- MIDDLE COLUMN: Status Icon -->
      <div class="col-12 col-md-3 flex flex-center column q-gutter-md">
        <q-icon name="qr_code_scanner" size="100px" :color="verifiedRecordIds.size > 0 ? 'primary' : 'grey-4'" />
        <div class="text-caption text-grey-6 text-center">Scan label at {{ selectedWarehouse }}</div>
        <div v-if="selectedBatchId" class="q-mt-md text-center">
            <q-badge color="blue-10" class="q-pa-sm">
                Current Batch: {{ selectedBatchId }}
            </q-badge>
        </div>
      </div>

      <!-- RIGHT COLUMN: Packing Results -->
      <div class="col-12 col-md-5">
        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col-4">
            <div class="text-subtitle2 q-mb-xs">PlantID</div>
            <q-input outlined :model-value="plantId" dense readonly bg-color="grey-1" />
          </div>
          <div class="col-8">
            <div class="text-subtitle2 q-mb-xs">Current Packing Set</div>
            <q-input outlined :model-value="packagingSetId" dense readonly bg-color="grey-1" />
          </div>
        </div>

        <!-- Packing List Table -->
        <div class="packing-list-container column">
          <!-- Header -->
          <div class="row items-center q-pa-sm bg-positive text-white border-bottom">
            <div class="col-7 text-weight-bold">Verified Packing ID</div>
            <div class="col-3 text-weight-bold text-center">Net Weight</div>
            <div class="col-2 text-weight-bold text-right q-pr-sm">
              Status
            </div>
          </div>

          <!-- Rows -->
          <div class="col scroll q-pa-none">
            <div
              v-if="packedItems.length === 0"
              class="q-pa-md text-grey-6 text-center"
            >
              No items scanned in this session
            </div>
            <div
              v-for="(item, index) in packedItems"
              :key="item.id"
              class="row items-center q-pa-sm border-bottom"
              :class="index % 2 === 0 ? 'bg-green-1' : 'bg-white'"
            >
              <div class="col-7">
                <div class="text-weight-bold text-primary">{{ item.re_code }}</div>
                <div class="text-caption text-grey-8">{{ item.batch_record_id }}</div>
              </div>
              <div class="col-3 text-center text-weight-bold">
                {{ item.net_volume }} kg
              </div>
              <div class="col-2 text-right q-pr-sm">
                <q-icon name="check_circle" color="positive" size="sm" />
              </div>
            </div>
          </div>

          <!-- Footer (Totals) -->
          <div class="row items-center q-pa-md border-top bg-blue-1 q-mt-auto">
            <div class="col-5 text-weight-bold">Session Summary</div>
            <div class="col-3 text-center text-weight-bold">{{ totalBoxPackages }} pcs</div>
            <div class="col-2 text-right">Total Weight</div>
            <div class="col-2 text-right text-weight-bold text-primary">{{ currentWeight.toFixed(2) }} kg</div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="row justify-end q-gutter-md q-mt-md">
          <q-btn
            label="Save Packing List"
            color="primary"
            no-caps
            unelevated
            @click="onCreatePackingList"
          />
          <q-btn
            label="Clear Session"
            color="grey-7"
            outline
            no-caps
            @click="onClosePackingList"
          />
          <q-btn icon="print" label="Print" color="blue-grey-8" no-caps unelevated @click="onPrintPackingList" />
        </div>
      </div>
    </div>
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
</style>

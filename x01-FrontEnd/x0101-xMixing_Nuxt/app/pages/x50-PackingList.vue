<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { appConfig } from '../appConfig/config'

const version = '0.2'

// --- State ---
const selectedBatchId = ref<string>('')
const batchOptions = ref<string[]>([])
const prebatchRecords = ref<any[]>([])
const loading = ref(false)
const selectedProductionIndices = ref<number[]>([])

// --- Computed ---
const productionList = computed(() => {
  return prebatchRecords.value.map(r => {
    // Format: plan_id-package_no/total_packages-net_volume/total_volume/total_request_volume
    return `${r.batch_record_id}-${r.package_no}/${r.total_packages}-${r.net_volume}/${r.total_volume}/${r.total_request_volume}`
  })
})

const plantId = computed(() => {
  if (!selectedBatchId.value) return ''
  const parts = selectedBatchId.value.split('-')
  // Example: plan-Line-1-2026-02-04-001-001
  // We can try to extract something meaningful or just use a default
  if (parts.length > 2) return parts[2]
  return 'Mixing-01'
})

const packagingSetId = computed(() => {
  if (!selectedBatchId.value) return ''
  return `PKG-${selectedBatchId.value}`
})

const packingItems = ref<PackingItem[]>([])

interface PackingItem {
  id: string
  weight: string // Display string like '50/50.0'
  isVerified: boolean
  originalRecord?: any
}

// --- Data Fetching ---
const fetchBatches = async () => {
  try {
    const response = await $fetch<string[]>(`${appConfig.apiBaseUrl}/production-batches/ids`)
    batchOptions.value = response
    if (response && response.length > 0 && !selectedBatchId.value) {
      selectedBatchId.value = response[0] || ''
    }
  } catch (error) {
    console.error('Failed to fetch batches:', error)
  }
}

const fetchPrebatchRecords = async (batchId: string) => {
  if (!batchId) return
  loading.value = true
  try {
    // Extract plan_id from batchId
    // If batchId is plan-Line-1-2026-02-04-001-001
    // plan_id is plan-Line-1-2026-02-04-001
    const parts = batchId.split('-')
    const planId = parts.slice(0, parts.length - 1).join('-')
    
    const response = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-records/by-plan/${planId}`)
    prebatchRecords.value = response
  } catch (error) {
    console.error('Failed to fetch prebatch records:', error)
    prebatchRecords.value = []
  } finally {
    loading.value = false
  }
}

// --- Watchers ---
watch(selectedBatchId, (newId) => {
  selectedProductionIndices.value = []
  fetchPrebatchRecords(newId)
})

onMounted(() => {
  fetchBatches()
})

// --- Actions ---
const onTransfer = () => {
  const selectedItems = selectedProductionIndices.value.map(idx => {
    const record = prebatchRecords.value[idx]
    return {
      id: `${record.batch_record_id}-${record.package_no}/${record.total_packages}`,
      weight: `${record.net_volume}/${record.total_volume}`,
      isVerified: false,
      originalRecord: record
    }
  })
  
  packingItems.value.push(...selectedItems)
  
  // Remove from left list (optional, based on requirement)
  // For now, just clear selection
  selectedProductionIndices.value = []
}

const onCreatePackingList = () => {
  console.log('Create Packing List clicked', packingItems.value)
}

const onClosePackingList = () => {
  packingItems.value = []
  console.log('Close Packing List clicked')
}

const onPrintPackingList = () => {
  console.log('Print Packing List clicked')
}

const onSelectProductionItem = (index: number) => {
  const i = selectedProductionIndices.value.indexOf(index)
  if (i > -1) {
    selectedProductionIndices.value.splice(i, 1)
  } else {
    selectedProductionIndices.value.push(index)
  }
}

// Stats for footer
const totalBoxPackages = computed(() => packingItems.value.length)
const totalRequiredPackages = computed(() => {
    if (prebatchRecords.value.length > 0) return prebatchRecords.value[0].total_packages
    return 0
})
const currentWeight = computed(() => {
    return packingItems.value.reduce((sum, item) => sum + (item.originalRecord?.net_volume || 0), 0)
})
const totalWeight = computed(() => {
    return packingItems.value.reduce((sum, item) => sum + (item.originalRecord?.total_volume || 0), 0)
})

</script>

<template>
  <q-page class="q-pa-md bg-white">
    <!-- Header Version -->
    <div class="row justify-end q-mb-sm">
      <div class="text-caption text-weight-bold">Version {{ version }}</div>
    </div>

    <div class="row q-col-gutter-md">
      <!-- LEFT COLUMN: Production PlanList -->
      <div class="col-12 col-md-5">
        <div class="text-subtitle2 q-mb-xs">Production PlanList</div>
        <!-- Date Selector -->
        <!-- Date Selector (Batch ID) -->
        <q-select
          outlined
          v-model="selectedBatchId"
          :options="batchOptions"
          :loading="loading"
          dense
          class="q-mb-md"
          dropdown-icon="arrow_drop_down"
        />

        <!-- List Container -->
        <div class="list-container q-pa-none">
          <!-- Header -->
          <div class="row items-center q-pa-sm bg-grey-2 border-bottom">
            <div class="col-12 text-weight-bold">PackingList</div>
          </div>

          <!-- List Items -->
          <div class="col scroll">
            <div
              v-if="productionList.length === 0"
              class="q-pa-md text-grey-6 text-center"
            >
              No items available for this batch.
            </div>
            <div
              v-for="(item, index) in productionList"
              :key="index"
              v-ripple
              class="row items-center q-pa-sm border-bottom cursor-pointer"
              :class="{
                'bg-blue-3': selectedProductionIndices.includes(index),
                'bg-blue-1': !selectedProductionIndices.includes(index) && index % 2 === 0,
                'bg-white': !selectedProductionIndices.includes(index) && index % 2 !== 0,
              }"
              @click="onSelectProductionItem(index)"
            >
              <div class="col-12 text-blue-8" style="word-break: break-all">
                {{ item }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- MIDDLE COLUMN: Transfer Button -->
      <div class="col-12 col-md-2 flex flex-center">
        <q-btn
          icon="play_arrow"
          size="lg"
          square
          outline
          color="grey-6"
          class="transfer-btn q-pa-md"
          @click="onTransfer"
        />
      </div>

      <!-- RIGHT COLUMN: Packaging Set -->
      <div class="col-12 col-md-5">
        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col-4">
            <div class="text-subtitle2 q-mb-xs">PlantID</div>
            <q-input outlined :model-value="plantId" dense readonly />
          </div>
          <div class="col-8">
            <div class="text-subtitle2 q-mb-xs">Packaging Set</div>
            <q-input outlined :model-value="packagingSetId" dense readonly />
          </div>
        </div>

        <!-- Packing List Table/Card -->
        <div class="packing-list-container column">
          <!-- Header -->
          <div class="row items-center q-pa-sm bg-grey-2 border-bottom">
            <div class="col-7 text-weight-bold">Packing ID</div>
            <div class="col-3 text-weight-bold text-center">Net Weight (kg)</div>
            <div class="col-2 text-weight-bold text-right q-pr-sm">
              Status <q-icon name="qr_code_scanner" size="xs" />
            </div>
          </div>

          <!-- Rows -->
          <div class="col scroll q-pa-none">
            <div
              v-for="(item, index) in packingItems"
              :key="index"
              class="row items-center q-pa-sm border-bottom"
              :class="{ 'bg-blue-1': index % 2 === 0, 'bg-white': index % 2 !== 0 }"
            >
              <div class="col-7 text-blue-8" style="word-break: break-all">
                {{ item.id }}
              </div>
              <div class="col-3 text-blue-8 text-center text-weight-medium">
                {{ item.weight }}
              </div>
              <div class="col-2 text-right q-pr-sm">
                <q-icon
                  name="search"
                  size="md"
                  :class="item.isVerified ? 'text-green-6' : 'text-grey-8'"
                >
                  <q-badge
                    v-if="item.isVerified"
                    floating
                    color="transparent"
                    text-color="green"
                    icon="check"
                    style="top: 5px; right: 5px; font-size: 8px"
                  />
                  <!-- Using nested icon trick or just switching icon based on state -->
                </q-icon>
                <!-- Alternative icon logic to match image "magnifying glass with check" -->
                <q-icon
                  v-if="item.isVerified"
                  name="check_circle"
                  color="positive"
                  class="absolute-bottom-right"
                  style="font-size: 10px"
                />
              </div>
            </div>
          </div>

          <!-- Footer (Totals) -->
          <div class="row items-center q-pa-md border-top bg-white q-mt-auto">
            <div class="col-5 text-blue-8">Total Package in this Box</div>
            <div class="col-3 text-blue-8 text-center">{{ totalBoxPackages }}/{{ totalRequiredPackages }} pcs</div>
            <div class="col-2 text-blue-8 text-right">Weight</div>
            <div class="col-2 text-blue-8 text-right">{{ currentWeight.toFixed(1) }}/{{ totalWeight.toFixed(1) }} kg</div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="row justify-end q-gutter-md q-mt-md">
          <q-btn
            label="Creat Packing List"
            color="grey-6"
            no-caps
            unelevated
            @click="onCreatePackingList"
          />
          <q-btn
            label="Close Packing List"
            color="grey-6"
            no-caps
            unelevated
            @click="onClosePackingList"
          />
          <q-btn label="Print" color="grey-6" no-caps unelevated @click="onPrintPackingList" />
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

.transfer-btn {
  height: 80px;
  width: 50px;
  border: 1px solid #aaa;
}
</style>

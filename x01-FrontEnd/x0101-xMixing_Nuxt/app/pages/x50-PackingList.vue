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
const showPrintListDialog = ref(false)
const hasAutoPopulated = ref(false)

// For Scan Feedback Dialog
const scanFeedback = ref({
    show: false,
    type: 'success' as 'success' | 'error' | 'instruction',
    message: '',
    title: '',
    batchId: ''
})

const selectedReCode = ref<string | null>(null)

const planColumns: any[] = [
    { name: 'plan_id', label: 'Plan ID', field: 'plan_id', align: 'left', sortable: true },
    { name: 'sku_id', label: 'SKU-ID', field: 'sku_id', align: 'left', sortable: true },
    { name: 'plant', label: 'Plant', field: 'plant', align: 'center', sortable: true },
    { name: 'total_volume', label: 'Total Vol', field: 'total_volume', align: 'right', sortable: true },
    { name: 'create_list', label: 'Action', field: 'create_list', align: 'center', sortable: false },
    { 
        name: 'package_info', 
        label: 'Package', 
        field: 'package_info',
        align: 'center', 
        sortable: false 
    },
    { name: 'status', label: 'Status', field: 'status', align: 'center', sortable: true }
]

const batchColumns: any[] = [
    { name: 'batch_id', label: 'Batch ID', field: 'batch_id', align: 'left', sortable: true },
    { name: 'wh_manifest', label: 'WH Manifest', field: 'wh_manifest', align: 'left' },
    { name: 'batch_size', label: 'Net Weight', field: 'batch_size', align: 'right', sortable: true },
    { name: 'pkg_count', label: 'Packages', field: 'pkg_count', align: 'center' },
    { name: 'status', label: 'Status', field: 'status', align: 'center', sortable: true },
    { name: 'expand', label: '', field: 'expand', align: 'center' }
]

const pagination = ref({
    sortBy: 'plan_id',
    descending: true,
    page: 1,
    rowsPerPage: 10
})

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
    total_packages?: number
    req_id?: number
    wh?: string
    isVerified?: boolean
}

// IDs of records that have been verified (packed) in this session
const verifiedRecordIds = ref<Set<string>>(new Set())
// IDs of records that have been confirmed & saved
const confirmedRecordIds = ref<Set<string>>(new Set())
const selectedPrintBatchId = ref<string | null>(null)
const printQueue = ref<any[]>([])

// --- Computed ---

const plantId = computed(() => {
  if (!selectedBatchId.value) return '---'
  const parts = selectedBatchId.value.split('-')
  return parts.length > 2 ? parts[2] : 'Mixing'
})

const allBatches = computed(() => {
    const list: any[] = []
    plans.value.forEach(plan => {
        if (plan.batches) {
            plan.batches.forEach((batch: any) => {
                list.push({
                    ...batch,
                    parent_plan: plan,
                    plan_sku: plan.sku_id
                })
            })
        }
    })
    return list
})

const packagingSetId = computed(() => {
  if (!selectedBatchId.value) return 'GLOBAL-PACKING'
  return `PKG-${selectedBatchId.value}`
})

// Stats for footer
const totalBoxPackages = computed(() => confirmedRecordIds.value.size)
const totalAvailablePackages = computed(() => allRecords.value.length)

const currentWeight = computed(() => {
    return confirmedItems.value.reduce((sum: number, item: any) => sum + (item.net_volume || 0), 0)
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

// Group records for the inventory list
const groupedRequirements = computed(() => {
    const groups: Record<string, any[]> = {}
    
    // If a code is selected, show ALL records for that code (Packaged + Awaiting)
    // Otherwise, show only pending bags across all codes
    const baseList = selectedReCode.value 
        ? allRecords.value.filter(r => r.re_code === selectedReCode.value)
        : allRecords.value.filter(r => !confirmedRecordIds.value.has(r.batch_record_id))
    
    baseList.forEach(bag => {
        const code = (bag.re_code || 'OTHER').trim().toUpperCase()
        if (!groups[code]) groups[code] = []
        groups[code].push(bag)
    })
    
    // Sort groups alphabetically
    const sortedGroups: Record<string, any[]> = {}
    Object.keys(groups).sort().forEach(key => {
        sortedGroups[key] = groups[key]
    })
    
    return sortedGroups
})

// Group confirmed records by Batch ID for printing labels
const printLabels = computed(() => {
    const labels: Record<string, { 
        batch_id: string, 
        plan_id: string, 
        bag_count: number, 
        sku: string,
        plant: string,
        total_vol: number | string
    }> = {}
    
    allRecords.value.forEach(rec => {
        if (confirmedRecordIds.value.has(rec.batch_record_id)) {
            const batchId = getBatchIdFromRecord(rec)
            if (!labels[batchId]) {
                const plan = plans.value.find(p => p.plan_id === rec.plan_id)
                labels[batchId] = { 
                    batch_id: batchId, 
                    plan_id: rec.plan_id, 
                    bag_count: 0,
                    sku: plan?.sku_id || '---',
                    plant: plan?.plant || '---',
                    total_vol: plan?.total_vol || 0
                }
            }
            labels[batchId].bag_count++
        }
    })
    
    return Object.values(labels)
})

const displayLabels = computed(() => {
    // 1. If we have items in our manual Print Queue, print those
    if (printQueue.value.length > 0) {
        return printQueue.value
    }

    // 2. If a specific batch ID was clicked for direct print (legacy support)
    if (selectedPrintBatchId.value) {
        for (const plan of plans.value) {
            const batch = plan.batches?.find((b: any) => b.batch_id === selectedPrintBatchId.value)
            if (batch) {
                return [{
                    batch_id: batch.batch_id,
                    plan_id: plan.plan_id,
                    sku: plan.sku_id || '---',
                    plant: plan.plant || '---',
                    total_vol: batch.batch_size || plan.total_vol || 0,
                    bag_count: getRecordsForBatch(batch.batch_id).length
                }]
            }
        }
    }
    
    // 3. Fallback to confirmed items
    return printLabels.value
})

const pendingItems = computed(() => {
    // Items are "pending" until boxed (confirmed)
    return allRecords.value.filter(r => !confirmedRecordIds.value.has(r.batch_record_id))
})

const confirmedItems = computed(() => {
    // These are the records that have actually been scanned into boxes in this session
    return allRecords.value.filter(r => confirmedRecordIds.value.has(r.batch_record_id))
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
        
        // Automatic generation of Print List from database data
        if (!hasAutoPopulated.value && data.length > 0) {
            onAddAllToPrintList()
            hasAutoPopulated.value = true
        }
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
    // Records are matched by batch_record_id starting with batchId (e.g. batch-001 matches batch-001-recode-01)
    return allRecords.value.filter(r => r.batch_record_id.startsWith(batchId) && r.re_code === reCode)
}

const getWHSummary = (batch: any) => {
    const reqs = batch.reqs || []
    const whMap: Record<string, number> = {}
    reqs.forEach((r: any) => {
        const whName = r.wh || 'Default'
        whMap[whName] = (whMap[whName] || 0) + 1
    })
    return Object.entries(whMap).length > 0 
        ? Object.entries(whMap).map(([wh, count]) => `${wh}: ${count} packs`).join(' | ')
        : '---'
}

const getReqStatus = (req: any) => {
    const records = getRecordsForBatchRequirement(req.batch_id, req.re_code)
    
    // Total expected packages from the records themselves if available, otherwise 0
    const totalCount = records.length > 0 ? (records[0]?.total_packages || records.length) : 0
    // In Packing List screen, 'count' is what we have verified/confirmed in this session
    const confirmedCount = records.filter(r => confirmedRecordIds.value.has(r.batch_record_id)).length
    
    // 1. Use database status if it's already Completed (2)
    if (req.status === 2) {
        // If it's done in DB, but we want to show packing progress too
        const label = confirmedCount === totalCount && totalCount > 0 ? 'Done' : 'Prepared'
        return { code: 2, label, count: confirmedCount || totalCount, total: totalCount }
    }
    
    // 2. Otherwise calculate based on records in this session
    if (records.length === 0) return { code: 0, label: 'Awaiting', count: 0, total: 0 }
    if (confirmedCount > 0 || verifiedRecordIds.value.size > 0) return { code: 1, label: 'Packing', count: confirmedCount, total: totalCount }
    
    return { code: 0, label: 'Awaiting', count: 0, total: totalCount }
}

const isBatchPacked = (batch: any) => {
    if (batch.status === 'Done') return true
    if (batch.reqs && batch.reqs.length > 0) {
        return batch.reqs.every((req: any) => {
            const records = getRecordsForBatchRequirement(batch.batch_id, req.re_code)
            const total = records.length > 0 ? (records[0]?.total_packages || records.length) : 0
            const confirmed = records.filter(r => confirmedRecordIds.value.has(r.batch_record_id)).length
            return total > 0 && confirmed === total
        })
    }
    return false
}

const isBatchReady = (batch: any) => {
    // A batch is "Ready" (Weighed) if all its requirements have weighed bags (records)
    if (batch.status === 'Done' || batch.status === 'Prepared' || batch.batch_prepare) return true
    if (batch.reqs && batch.reqs.length > 0) {
        return batch.reqs.every((req: any) => {
            const records = getRecordsForBatchRequirement(batch.batch_id, req.re_code)
            return records.length > 0
        })
    }
    return false
}

const getBatchBagProgress = (batch: any) => {
    let packed = 0
    let total = 0
    batch.reqs?.forEach((req: any) => {
        const records = getRecordsForBatchRequirement(batch.batch_id, req.re_code)
        const totalReq = records.length > 0 ? (records[0]?.total_packages || records.length) : 0
        const confirmed = records.filter(r => confirmedRecordIds.value.has(r.batch_record_id)).length
        packed += confirmed
        total += totalReq
    })
    return { packed, total }
}

const getRecordsForPlan = (planId: string) => {
    return allRecords.value.filter(r => r.plan_id === planId)
}

const hasPendingRecords = (records: PreBatchRec[]) => {
    return records.some(r => verifiedRecordIds.value.has(r.batch_record_id))
}

const getPlanPackedBatches = (row: any) => {
    if (!row.batches) return 0
    return row.batches.filter((b: any) => isBatchPacked(b)).length
}

const getPlanReadyBatches = (row: any) => {
    if (!row.batches) return 0
    return row.batches.filter((b: any) => isBatchReady(b)).length
}

const getBatchIdFromRecord = (record: PreBatchRec) => {
    // Search in loaded plans/batches for the most specific batch ID that matches this record
    for (const plan of plans.value) {
        if (plan.batches) {
            for (const batch of plan.batches) {
                if (record.batch_record_id.startsWith(batch.batch_id)) {
                    return batch.batch_id
                }
            }
        }
    }
    // Fallback to plan_id if no specific batch is found
    return record.plan_id
}

// --- Watchers ---

watch(selectedWarehouse, () => {
    fetchAllData()
})

// HANDLE SCANS: 2-Step Verification (Ingredient -> Box)
// HANDLE SCANS: 2-Step Verification (Ingredient -> Box)
const handleBarcodeScan = (barcode: string) => {
    barcode = barcode.trim()
    if (!barcode) return

    // A. CHECK IF SCAN IS A BOX/PLAN (To confirm multiple pending bags)
    const matchedPlan = plans.value.find(p => barcode === p.plan_id || barcode === `PKG-${p.plan_id}`)
    const allBatches = plans.value.flatMap(p => p.batches || [])
    const matchedBatch = allBatches.find(b => barcode === b.batch_id || barcode === `PKG-${b.batch_id}`)
    
    if (matchedPlan || matchedBatch) {
        const targetId = matchedBatch ? matchedBatch.batch_id : matchedPlan.plan_id
        const isPlanScan = !!matchedPlan && !matchedBatch

        // Find all records in "Verified/Yellow" status that belong to this Scan
        const toConfirm = allRecords.value.filter(r => {
            if (!verifiedRecordIds.value.has(r.batch_record_id)) return false
            if (isPlanScan) return r.plan_id === targetId
            return r.batch_record_id.startsWith(targetId)
        })

        if (toConfirm.length > 0) {
            // Confirm all matching bags
            toConfirm.forEach(r => {
                confirmedRecordIds.value.add(r.batch_record_id)
                verifiedRecordIds.value.delete(r.batch_record_id)
            })
            
            scanFeedback.value = {
                show: true,
                type: 'success',
                title: 'BOX CONFIRMED!',
                message: `${toConfirm.length} ingredient(s) successfully confirmed inside Box [${barcode}].`,
                batchId: ''
            }
            pendingRecord.value = null
            return
        } else {
            // No bags pending for this box
            $q.notify({
                type: 'warning',
                message: `Box ${barcode} scanned, but no ingredient bags are currently pending for it. Scan bags first!`,
                position: 'top'
            })
            return
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
            
            // Show Instruction Popup
            const targetId = getBatchIdFromRecord(record)
            scanFeedback.value = {
                show: true,
                type: 'instruction',
                title: 'INSTRUCTION',
                message: `Put this ingredient bag [${record.re_code}] to Batch Packing Box:`,
                batchId: targetId
            }
        }
    } else {
        $q.notify({
            type: 'negative',
            message: `Unknown Barcode: ${barcode}`,
            position: 'top'
        })
    }
}

watch(lastScan, (newScan) => {
    if (newScan) handleBarcodeScan(newScan.barcode)
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
    handleBarcodeScan(batchId)
}

const simulateScanForPlan = (planId: string) => {
    handleBarcodeScan(planId)
}

const onClosePackingList = () => {
  verifiedRecordIds.value.clear()
  selectedBatchId.value = ''
  $q.notify({ type: 'grey', message: 'Session Cleared' })
}


const onAddAllToPrintList = () => {
    plans.value.forEach(plan => {
        if (plan.batches) {
            plan.batches.forEach((b: any) => addToPrintList(b, plan))
        }
    })
    $q.notify({
        type: 'positive',
        message: 'Added all batches from current plans to print list',
        icon: 'playlist_add_check'
    })
}

const onAddPlanToList = (plan: any) => {
    if (plan.batches) {
        plan.batches.forEach((b: any) => addToPrintList(b, plan))
    }
}

const onPrintPlanLabels = (plan: any) => {
    // Clear and add only this plan's batches, then print
    printQueue.value = []
    if (plan.batches) {
        plan.batches.forEach((b: any) => addToPrintList(b, plan))
    }
    
    if (printQueue.value.length > 0) {
        setTimeout(() => { window.print() }, 200)
    }
}

const onPrintBatchLabel = (batch: any) => {
    // For direct print: clear queue, add one, print
    printQueue.value = []
    const plan = plans.value.find(p => p.batches?.some((b: any) => b.batch_id === batch.batch_id))
    addToPrintList(batch, plan)
    
    setTimeout(() => {
        window.print()
    }, 200)
}

const addToPrintList = (batch: any, plan: any) => {
    if (!batch || !batch.batch_id) return

    // Check if Already in list
    if (printQueue.value.find(l => l.batch_id === batch.batch_id)) return

    const planId = plan?.plan_id || batch.plan_id || '---'
    const skuId = plan?.sku_id || batch.sku_id || '---'
    
    // REQUIREMENT DATA: Calculate from prebatch_reqs (the batch.reqs array from DB)
    const reqs = batch.reqs || []
    
    // Group requirements by WH
    const whMap: Record<string, number> = {}
    reqs.forEach((r: any) => {
        const whName = r.wh || 'Default'
        whMap[whName] = (whMap[whName] || 0) + 1
    })
    
    const whSummary = Object.entries(whMap).length > 0 
        ? Object.entries(whMap).map(([wh, count]) => `${wh}: ${count} packs`).join(' | ')
        : 'No Requirements'

    const newLabel = {
        batch_id: batch.batch_id,
        plan_id: planId,
        sku: skuId,
        plant: plan?.plant || '---',
        total_vol: batch.batch_size || 0,
        bag_count: reqs.length, // Total packs required as per prebatch_req
        wh_summary: whSummary
    }

    printQueue.value = [...printQueue.value, newLabel]
}

const removeFromPrintList = (batchId: string) => {
    printQueue.value = printQueue.value.filter(l => l.batch_id !== batchId)
}

const clearPrintList = () => {
    printQueue.value = []
}

const onPrintAllInList = () => {
    if (printQueue.value.length === 0) {
        $q.notify({ type: 'warning', message: 'Print List is empty' })
        return
    }
    window.print()
}

const onManualAdd = (item: any) => {
    // 1. If already yellow (verified), move to green (confirmed)
    if (verifiedRecordIds.value.has(item.batch_record_id)) {
        handleBarcodeScan(getBatchIdFromRecord(item))
    } else {
        // 2. Otherwise, mark as yellow (verified)
        handleBarcodeScan(item.batch_record_id)
    }
}

</script>

<template>
  <q-page class="q-pa-md bg-white">
    <!-- Header Section -->
    <div class="bg-blue-9 text-white q-pa-md rounded-borders q-mb-md shadow-2">
      <div class="row justify-between items-center">
        <div class="text-h6 text-weight-bolder">Production Plan List</div>
        <div class="text-caption text-weight-bold">Version {{ version }}</div>
      </div>
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
                <div class="row items-center">
                    <span class="q-mr-sm">{{ selectedWarehouse === 'All Warehouse' ? 'Global Summary' : selectedWarehouse + ' Summary' }}</span>
                    <q-badge v-if="selectedReCode" color="orange" outline class="q-ml-sm">
                        Filtering: {{ selectedReCode }}
                        <q-icon name="close" class="cursor-pointer q-ml-xs" @click.stop="selectedReCode = null" />
                    </q-badge>
                </div>
                <div class="q-gutter-x-sm">
                    <q-btn v-if="selectedReCode" icon="filter_list_off" flat round dense color="white" @click="selectedReCode = null">
                        <q-tooltip>Clear Filter</q-tooltip>
                    </q-btn>
                    <q-btn icon="playlist_add" flat round dense color="white" @click="onAddAllToPrintList">
                        <q-tooltip>Add all Batches to Print List</q-tooltip>
                    </q-btn>
                    <q-btn icon="refresh" flat round dense color="white" @click="fetchAllData" :loading="loading" />
                </div>
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
                                <tr 
                                    v-for="row in reCodeSummary" 
                                    :key="row.re_code" 
                                    class="hover-bg cursor-pointer"
                                    :class="{ 'bg-blue-1': selectedReCode === row.re_code }"
                                    @click="selectedReCode = row.re_code"
                                >
                                    <td class="text-left text-weight-bold" :class="selectedReCode === row.re_code ? 'text-primary' : 'text-blue-9'">{{ row.re_code }}</td>
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
            <div class="col-12 text-weight-bold">
                {{ selectedReCode ? 'Inventory for ' + selectedReCode : 'Awaiting Scan (Ready Bags)' }}
            </div>
          </div>

          <!-- List Items Grouped by Code -->
          <!-- List Items Grouped by Code (Hierarchy Style) -->
          <div class="col scroll bg-grey-2">
            <div
              v-if="pendingItems.length === 0"
              class="q-pa-xl text-grey-6 text-center column items-center"
            >
              <q-icon name="done_all" size="48px" color="grey-4" class="q-mb-sm" />
              <div class="text-h6">{{ loading ? 'Syncing...' : 'All bags ready!' }}</div>
            </div>
            
            <div v-for="(bags, code) in groupedRequirements" :key="code" class="q-mb-none">
              <!-- Group Header: Ingredient Code -->
              <div class="row items-center q-pa-sm bg-blue-grey-1 text-grey-9 text-weight-bold border-bottom">
                <q-icon name="inventory_2" class="q-mr-sm" size="xs" color="blue-grey-7" />
                <span>{{ code }} ({{ bags.length }} bags)</span>
              </div>
              
              <!-- Child Items: Bag Labels -->
              <div
                v-for="item in bags"
                :key="item.batch_record_id"
                v-ripple
                class="row items-center q-pa-md bg-white border-bottom cursor-pointer hover-bg transition-all"
                style="border-left: 4px solid #fff"
                @click="onManualAdd(item)"
              >
                <div class="col-10">
                  <div class="text-weight-bold text-blue-9 text-subtitle2" style="font-size: 1.1em; line-height: 1.2;">
                    {{ item.batch_record_id }}
                  </div>
                  <div class="row items-center q-mt-xs">
                    <span class="text-caption text-grey-8">Net: <b class="text-black">{{ item.net_volume }}</b> kg</span>
                    <q-separator vertical class="q-mx-sm" inset />
                    <span class="text-caption text-grey-8">Status: </span>
                    <q-badge 
                        :color="confirmedRecordIds.has(item.batch_record_id) ? 'positive' : 'orange'" 
                        class="q-ml-sm q-px-sm"
                        style="font-size: 0.8em"
                    >
                        {{ confirmedRecordIds.has(item.batch_record_id) ? '1 Packaged' : '0 Awaiting' }}
                    </q-badge>
                    <q-separator vertical class="q-mx-sm" inset />
                    <span class="text-caption text-grey-8">WH: {{ item.wh || '-' }}</span>
                  </div>
                </div>
                <div class="col-2 text-right">
                  <q-icon 
                    :name="confirmedRecordIds.has(item.batch_record_id) ? 'check_circle' : (verifiedRecordIds.has(item.batch_record_id) ? 'check' : 'done')" 
                    size="32px"
                    :color="confirmedRecordIds.has(item.batch_record_id) ? 'positive' : (verifiedRecordIds.has(item.batch_record_id) ? 'orange-8' : 'grey-3')" 
                    class="transition-all"
                  />
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
      <div class="col-12 col-md-5 column q-gutter-y-sm" style="height: calc(100vh - 140px);">
        <!-- CARD 0: Box Label Print List (1st Card on Right) -->
        <q-card class="bg-white shadow-2 overflow-hidden" style="max-height: 200px; min-height: 150px;">
            <div class="q-pa-sm bg-blue-grey-9 text-white text-weight-bold text-body2 flex justify-between items-center">
                <div class="row items-center">
                    <q-icon name="print" class="q-mr-sm" />
                    <span>Box Label Print List</span>
                </div>
                <div class="q-gutter-x-xs">
                    <q-btn icon="delete_sweep" flat round dense color="white" size="sm" @click="clearPrintList" v-if="printQueue.length > 0">
                        <q-tooltip>Clear List</q-tooltip>
                    </q-btn>
                    <q-btn icon="print" unelevated color="positive" size="xs" label="PRINT ALL" @click="onPrintAllInList" v-if="printQueue.length > 0" />
                </div>
            </div>

            <div class="col relative-position bg-grey-1">
                <q-scroll-area class="fit">
                    <div v-if="printQueue.length === 0" class="fit flex flex-center text-grey-6 q-pa-sm text-center">
                        <div class="text-caption italic">No labels in queue. Click "CREATE LIST" in table below.</div>
                    </div>
                    
                    <q-list separator dense v-else>
                        <q-item v-for="item in printQueue" :key="item.batch_id" class="bg-white" padding>
                            <q-item-section>
                                <q-item-label class="text-weight-bold text-blue-9" style="font-size: 0.9em">{{ item.batch_id }}</q-item-label>
                                <q-item-label caption style="font-size: 0.8em">{{ item.sku }}</q-item-label>
                            </q-item-section>
                            <q-item-section side>
                                <q-btn icon="close" flat round dense color="grey-5" size="xs" @click="removeFromPrintList(item.batch_id)" />
                            </q-item-section>
                        </q-item>
                    </q-list>
                </q-scroll-area>
            </div>
        </q-card>
        <!-- ACTIONS FOOTER CARD (Re-positioned to Top) -->
        <q-card class="bg-white shadow-2">
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
                </div>
            </q-card-actions>
        </q-card>

        <q-card class="col column bg-white shadow-2 overflow-hidden">
            <div class="q-pa-sm bg-primary text-white text-weight-bold text-subtitle2 flex justify-between items-center">
                <span>Production Plan List</span>
                <q-btn icon="refresh" flat round dense color="white" @click="fetchPlans" :loading="plansLoading" />
            </div>

            <div class="col relative-position">
                <q-table
                  v-model:expanded="expandedRows"
                  v-model:pagination="pagination"
                  :rows="plans"
                  :columns="planColumns"
                  row-key="plan_id"
                  flat
                  dense
                  class="text-caption full-height shadow-1"
                  style="height: 100%"
                  sticky-header
                  :loading="plansLoading"
                  binary-state-sort
                  :rows-per-page-options="[5, 10, 20, 50, 0]"
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
                    <q-tr 
                        :props="props" 
                        class="cursor-pointer" 
                        @click="props.expand = !props.expand"
                    >
                      <q-td auto-width>
                        <q-btn 
                            size="sm" 
                            :color="props.expand ? 'primary' : 'blue-1'" 
                            :text-color="props.expand ? 'white' : 'primary'"
                            round 
                            unelevated
                            :icon="props.expand ? 'keyboard_arrow_up' : 'keyboard_arrow_down'" 
                        />
                      </q-td>
                      <q-td key="plan_id" :props="props" class="text-weight-bold text-blue-9">
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
                      <q-td key="create_list" :props="props" auto-width>
                        <q-btn 
                          outline 
                          color="primary" 
                          icon="playlist_add" 
                          label="CREATE LIST" 
                          size="sm"
                          class="text-weight-bold q-px-md"
                          @click.stop="onAddPlanToList(props.row)"
                        />
                      </q-td>
                      <q-td key="package_info" :props="props" class="text-center">
                        <div class="bg-blue-1 rounded-borders q-pa-xs row no-wrap items-center justify-center">
                            <span class="text-green-9 text-weight-bolder">{{ getPlanPackedBatches(props.row) }}</span>
                            <span class="q-mx-xs text-grey-5">/</span>
                            <span class="text-primary text-weight-bolder">0</span>
                            <span class="q-mx-xs text-grey-5">/</span>
                            <span class="text-black text-weight-bolder">{{ (props.row.batches?.length || 0) }}</span>
                        </div>
                        <q-tooltip anchor="top middle" self="bottom middle" :offset="[0, 8]">
                          Packed Batches / Ready(Weighed) Batches / Total Planned Batches
                        </q-tooltip>
                      </q-td>
                      <q-td key="status" :props="props" class="text-center">
                          {{ props.row.status }}
                      </q-td>
                    </q-tr>
                    <q-tr v-show="props.expand" :props="props" class="bg-blue-grey-1">
                      <q-td colspan="100%">
                        <div class="q-pa-sm">
                          <div class="row items-center justify-between q-mb-sm">
                            <div class="text-weight-bold text-blue-9">
                              <q-icon name="list_alt" class="q-mr-sm" />
                              Batches for Plan: {{ props.row.plan_id }}
                            </div>
                            <div class="q-gutter-x-sm">
                              <q-btn 
                                flat 
                                color="primary" 
                                icon="playlist_add" 
                                label="ADD ALL TO LIST" 
                                size="sm"
                                class="text-weight-bold"
                                @click.stop="onAddPlanToList(props.row)"
                              />
                              <q-btn 
                                unelevated 
                                color="blue-grey-8" 
                                icon="print" 
                                label="PRINT ALL NOW" 
                                size="sm"
                                class="text-weight-bold shadow-1"
                                @click.stop="onPrintPlanLabels(props.row)"
                              />
                            </div>
                          </div>
                          
                          <q-table
                            :rows="props.row.batches"
                            :columns="batchColumns"
                            row-key="id"
                            flat
                            bordered
                            dense
                            class="bg-white rounded-borders shadow-1"
                            style="max-height: 450px"
                            sticky-header
                            :pagination="{ rowsPerPage: 5 }"
                            :rows-per-page-options="[5, 10, 20, 0]"
                          >
                            <template v-slot:body="batchProps">
                              <q-tr 
                                :props="batchProps" 
                                class="hover-bg"
                              >
                                <q-td key="batch_id" :props="batchProps">
                                  <div class="row no-wrap items-center">
                                    <q-icon name="diamond" color="primary" size="xs" class="q-mr-sm" />
                                    <span class="text-weight-bolder text-black">{{ batchProps.row.batch_id }}</span>
                                  </div>
                                </q-td>
                                <q-td key="wh_manifest" :props="batchProps" class="text-caption grey-8">
                                  {{ getWHSummary(batchProps.row) }}
                                </q-td>
                                <q-td key="batch_size" :props="batchProps" class="text-right">
                                  <span class="text-weight-bolder" style="font-size: 1.1em">{{ batchProps.row.batch_size }} kg</span>
                                </q-td>
                                <q-td key="pkg_count" :props="batchProps" class="text-center">
                                  <q-badge outline color="blue-grey-4" class="q-px-sm" text-color="blue-grey-9">
                                    <span class="text-weight-bold">BAGS {{ batchProps.row.reqs?.length || 0 }}</span>
                                  </q-badge>
                                </q-td>
                                <q-td key="status" :props="batchProps">
                                  <div class="row items-center no-wrap justify-between">
                                    <q-badge 
                                        unelevated 
                                        color="orange-8" 
                                        class="q-px-md text-weight-bold" 
                                        style="height: 24px; border-radius: 4px;"
                                        label="Created"
                                    />
                                    
                                    <q-btn 
                                        flat 
                                        round 
                                        dense 
                                        size="sm" 
                                        color="primary" 
                                        icon="add_circle" 
                                        @click.stop="addToPrintList(batchProps.row, props.row)"
                                    />
                                  </div>
                                </q-td>
                                <q-td key="expand" :props="batchProps" auto-width>
                                  <q-btn size="sm" color="blue-grey-3" round flat icon="keyboard_arrow_right" @click.stop="batchProps.expand = !batchProps.expand" />
                                </q-td>
                              </q-tr>

                              <q-tr v-show="batchProps.expand" :props="batchProps" class="bg-blue-grey-1">
                                <q-td colspan="100%" class="q-pa-sm">
                                  <div class="q-card q-pa-sm shadow-1 bg-grey-1 rounded-borders">
                                    <div class="row items-center justify-between q-mb-xs">
                                        <div class="text-caption text-weight-bold color-primary">Scanned Packs for Batch</div>
                                        <q-btn flat round dense color="primary" icon="qr_code_scanner" size="sm" @click="simulateScanForBatch(batchProps.row.batch_id)">
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
                                        <template v-for="req in batchProps.row.reqs" :key="req.id">
                                          <tr>
                                            <td class="text-center">
                                              <q-btn 
                                                v-if="getRecordsForBatchRequirement(batchProps.row.batch_id, req.re_code).length > 0"
                                                size="xs" 
                                                flat 
                                                round 
                                                color="primary" 
                                                :icon="expandedBatches.includes(req.id) ? 'keyboard_arrow_up' : 'keyboard_arrow_down'"
                                                @click.stop="expandedBatches.includes(req.id) ? expandedBatches = expandedBatches.filter(id => id !== req.id) : expandedBatches = [...expandedBatches, req.id]"
                                              />
                                            </td>
                                            <td class="text-left text-weight-bold text-primary">
                                              {{ req.re_code }}
                                              <div v-if="getRecordsForBatchRequirement(batchProps.row.batch_id, req.re_code).length > 1" class="text-caption text-grey-6 text-weight-regular">
                                                  {{ getRecordsForBatchRequirement(batchProps.row.batch_id, req.re_code).length }} bags
                                              </div>
                                            </td>
                                            <td class="text-left text-caption">{{ req.ingredient_name || '-' }}</td>
                                            <td class="text-right text-weight-bold">{{ req.required_volume }} kg</td>
                                            <td class="text-center">
                                              <q-badge
                                                :color="getReqStatus(req).code === 2 ? 'positive' : (getReqStatus(req).code === 1 ? 'warning' : 'grey-4')"
                                                :text-color="getReqStatus(req).code === 0 ? 'black' : 'white'"
                                              >
                                                {{ getReqStatus(req).label }} {{ getReqStatus(req).count }}/{{ getReqStatus(req).total }}
                                              </q-badge>
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
                                                  <tr v-for="rec in getRecordsForBatchRequirement(batchProps.row.batch_id, req.re_code)" :key="rec.id" style="font-size: 0.85em">
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
                                      </tbody>
                                    </q-markup-table>
                                  </div>
                                </q-td>
                              </q-tr>
                            </template>

                            <template v-slot:no-data>
                              <div class="full-width row flex-center text-grey italic q-pa-md">
                                No batches found for this plan
                              </div>
                            </template>
                          </q-table>
                        </div>
                      </q-td>
                    </q-tr>
                  </template>
                </q-table>
            </div>
        </q-card>
      </div>
    </div>

    <!-- SCAN FEEDBACK DIALOG -->
    <q-dialog v-model="scanFeedback.show" position="top">
        <q-card 
          style="width: 480px; border-radius: 16px;" 
          :class="{
            'bg-positive text-white': scanFeedback.type === 'success',
            'bg-negative text-white': scanFeedback.type === 'error',
            'bg-blue-9 text-white shadow-24': scanFeedback.type === 'instruction'
          }"
        >
            <q-card-section class="row items-center q-pb-none">
                <div class="text-h6 text-weight-bolder">{{ scanFeedback.title }}</div>
                <q-space />
                <q-btn icon="close" flat round dense v-close-popup />
            </q-card-section>

            <q-card-section class="column items-center q-pa-lg">
                <q-icon 
                    :name="scanFeedback.type === 'success' ? 'check_circle' : (scanFeedback.type === 'error' ? 'report_problem' : 'move_to_inbox')" 
                    size="80px" 
                    class="q-mb-md"
                    :class="{ 'q-animate-bounce': scanFeedback.type === 'instruction' }"
                />
                <div class="text-subtitle1 text-center text-weight-medium q-px-md">
                    {{ scanFeedback.message }}
                </div>
                
                <div v-if="scanFeedback.batchId" class="q-mt-md q-pa-md bg-white text-primary rounded-borders full-width shadow-3 text-center">
                    <div class="text-caption text-grey-8 text-weight-bold">TARGET BOX ID</div>
                    <div class="text-h5 text-weight-bolder letter-spacing-1">{{ scanFeedback.batchId }}</div>
                </div>
            </q-card-section>

            <q-card-section class="q-pt-none row q-gutter-x-md justify-center q-pb-md">
                <q-btn 
                    v-if="scanFeedback.type === 'instruction'"
                    outline
                    color="white"
                    icon="qr_code_scanner"
                    label="SIMULATE BOX SCAN" 
                    class="q-px-md text-weight-bold"
                    @click="handleBarcodeScan(scanFeedback.batchId)" 
                />
                <q-btn 
                    unelevated 
                    color="white" 
                    :text-color="scanFeedback.type === 'success' ? 'positive' : (scanFeedback.type === 'error' ? 'negative' : 'primary')"
                    :label="scanFeedback.type === 'instruction' ? 'CONTINUE' : 'OK'" 
                    class="q-px-xl text-weight-bold"
                    v-close-popup 
                />
            </q-card-section>
        </q-card>
    </q-dialog>

    <!-- PRINT LIST POPUP DIALOG -->
    <q-dialog v-model="showPrintListDialog" position="right" full-height>
        <q-card class="column" style="width: 450px; max-width: 90vw;">
            <q-card-section class="bg-blue-9 text-white row items-center q-py-sm">
                <div class="text-subtitle1 text-weight-bold">
                    <q-icon name="print" class="q-mr-sm" />
                    Box Label Print Queue
                </div>
                <q-space />
                <q-btn icon="close" flat round dense v-close-popup />
            </q-card-section>

            <q-card-section class="col scroll q-pa-none">
                <div v-if="printQueue.length === 0" class="flex flex-center full-height column text-grey q-pa-xl">
                    <q-icon name="print_disabled" size="64px" class="q-mb-md" />
                    <div class="text-h6">Queue is Empty</div>
                    <div class="text-caption">Add labels from the planning list</div>
                </div>

                <q-list v-else separator class="bg-grey-2 q-pa-sm">
                    <q-item v-for="(item, index) in printQueue" :key="item.batch_id" class="bg-white q-mb-sm shadow-1 rounded-borders q-pa-md">
                        <q-item-section>
                            <div class="row justify-between items-start">
                                <div>
                                    <div class="text-caption text-grey-7 text-weight-bold">#{{ index + 1 }} BOX LABEL</div>
                                    <div class="text-h6 text-primary text-weight-bolder" style="line-height:1.2">{{ item.batch_id }}</div>
                                </div>
                                <q-btn flat round dense color="negative" icon="delete" @click="removeFromPrintList(item.batch_id)" />
                            </div>

                            <q-separator class="q-my-sm" />

                            <div class="q-gutter-y-xs">
                                <div class="row no-wrap items-center">
                                    <q-icon name="warehouse" color="blue-grey" size="14px" class="q-mr-xs" />
                                    <div class="text-caption text-weight-bold q-mr-xs">WH MANIFEST:</div>
                                    <div class="text-caption">{{ item.wh_summary }}</div>
                                </div>
                                <div class="row no-wrap items-center">
                                    <q-icon name="inventory_2" color="blue-grey" size="14px" class="q-mr-xs" />
                                    <div class="text-caption text-weight-bold q-mr-xs">SKU/PLAN:</div>
                                    <div class="text-caption">{{ item.sku }} | {{ item.plan_id }}</div>
                                </div>
                                <div class="row items-center q-mt-sm justify-between bg-blue-1 q-pa-sm rounded-borders">
                                    <div class="column">
                                        <div class="text-overline text-blue-9" style="line-height:1">NET WEIGHT</div>
                                        <div class="text-subtitle1 text-weight-bolder">{{ item.total_vol }} kg</div>
                                    </div>
                                    <q-separator vertical class="q-mx-md" />
                                    <div class="column">
                                        <div class="text-overline text-blue-9" style="line-height:1">QUANTITY</div>
                                        <div class="text-subtitle1 text-weight-bolder">{{ item.bag_count }} BAGS</div>
                                    </div>
                                </div>
                            </div>
                        </q-item-section>
                    </q-item>
                </q-list>
            </q-card-section>

            <q-separator />

            <q-card-section class="q-pa-md bg-white">
                <div class="row q-col-gutter-md">
                    <div class="col-6">
                        <q-btn 
                            stack
                            outline 
                            class="full-width q-py-md text-weight-bold" 
                            color="negative" 
                            label="CLEAR QUEUE" 
                            icon="delete_sweep"
                            @click="clearPrintList"
                            :disable="printQueue.length === 0"
                        />
                    </div>
                    <div class="col-6">
                        <q-btn 
                            stack
                            unelevated 
                            class="full-width q-py-md text-weight-bold shadow-3" 
                            color="blue-9" 
                            label="PRINT ALL" 
                            icon="print"
                            @click="onPrintAllInList"
                            :disable="printQueue.length === 0"
                        />
                    </div>
                </div>
                <div class="text-center q-mt-sm text-caption text-grey-7 italic">
                    Labels will be printed in 4x4 layout
                </div>
            </q-card-section>
        </q-card>
    </q-dialog>

    <div id="print-area" class="print-only">
        <div v-for="label in displayLabels" :key="label.batch_id" class="label-box">
            <!-- Header Bar (Black with White Text) -->
            <div class="label-header-bar row no-wrap items-center justify-between q-px-sm">
                <div class="text-weight-bolder">MITR PHOL GROUP</div>
                <div class="text-weight-bold">BATCH PACKING LABEL</div>
            </div>
            
            <div class="label-body column no-wrap" style="flex: 1">
                <!-- Traceability Section -->
                <div class="q-mt-md">
                    <div class="label-row"><span class="label-title-inline">Batch Planning ID:</span> <span class="label-value-inline">{{ label.batch_id }}</span></div>
                    <div class="label-row q-mt-xs"><span class="label-title-inline">Ingredient Packages by WH:</span> <span class="label-value-inline">{{ label.wh_summary }}</span></div>
                    <div class="label-row q-mt-xs"><span class="label-title-inline">SKU:</span> <span class="label-value-inline">{{ label.sku }}</span> | <span class="label-title-inline">Plan:</span> <span class="label-value-inline">{{ label.plan_id }}</span></div>
                    <div class="label-row q-mt-xs"><span class="label-title-inline">GENERATE STAMP TIME:</span> <span class="label-value-inline">{{ new Date().toLocaleString() }}</span></div>
                </div>

                <!-- Bottom Section Separator -->
                <div class="q-mt-auto" style="border-top: 2px solid #000; padding-top: 10px;">
                    <div class="row no-wrap items-end full-width">
                        <div class="col-7 column q-gutter-y-sm">
                            <div class="weight-row">
                                <div class="label-title-large">NET WEIGHT: <span class="label-value-extra-large">{{ label.total_vol }} kg</span></div>
                            </div>
                            <div class="package-row">
                                <div class="label-title-large">NO. OF PACKAGE: <span class="label-value-extra-large">{{ label.bag_count }} bags</span></div>
                            </div>
                        </div>
                        <div class="col-5 flex justify-end">
                            <img 
                              :src="`https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${label.batch_id}`" 
                              class="qr-image-fixed"
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
  </q-page>
</template>

<style scoped>
/* Screen styles ... */
@media screen {
    .print-only {
        display: none !important;
    }
}

/* Print styles */
@media print {
    @page {
        size: 4in 4in;
        margin: 0;
    }
    body * {
        visibility: hidden !important;
    }
    #print-area, #print-area * {
        visibility: visible !important;
    }
    #print-area {
        position: absolute;
        left: 0;
        top: 0;
        width: 4in;
        height: 4in;
        display: block !important;
        background: white;
    }
    .label-box {
        width: 3.8in;
        height: 3.8in;
        margin: 0.1in auto;
        border: 2px solid #000;
        padding: 10px;
        page-break-after: always;
        font-family: 'Arial', sans-serif;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        box-sizing: border-box;
    }
    .label-header-bar {
        background: #000;
        color: #fff;
        height: 45px;
        font-size: 16px;
        margin-bottom: 2px;
    }
    .qr-image-fixed {
        width: 1.4in !important;
        height: 1.4in !important;
        display: block;
    }
    .label-title-inline {
        font-weight: bold;
        font-size: 13px;
    }
    .label-value-inline {
        font-size: 13px;
    }
    .label-title-large {
        font-weight: bold;
        font-size: 18px;
    }
    .label-value-extra-large {
        font-size: 30px;
        font-weight: 900;
    }
    .label-footer {
        display: none;
    }
}
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

.bg-blink-yellow {
  animation: bg-blink-animation 1s infinite !important;
}

@keyframes bg-blink-animation {
  0% { background-color: white; }
  50% { background-color: #fffde7; }
  100% { background-color: white; }
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

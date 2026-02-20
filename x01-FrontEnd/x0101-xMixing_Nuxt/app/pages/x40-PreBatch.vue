<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'

import { appConfig } from '../appConfig/config'
import { useAuth } from '../composables/useAuth'
import { useLabelPrinter } from '~/composables/useLabelPrinter'

const $q = useQuasar()
const { getAuthHeader, user } = useAuth()
const { generateLabelSvg, printLabel } = useLabelPrinter()
const { t } = useI18n()

// --- State ---
const selectedProductionPlan = ref('')
const selectedReCode = ref('')
const selectedRequirementId = ref<number | null>(null)
const selectedScale = ref(0) // Default to 0 (none selected)
const selectedBatchIndex = ref(0) // Default first one selected
const warehouses = ref<any[]>([])
const selectedWarehouse = ref('')
const showDeleteDialog = ref(false)
const deleteInput = ref('')
const isPackageSizeLocked = ref(true)
const showAuthDialog = ref(false)
const authPassword = ref('')
const selectedPreBatchLogs = ref<any[]>([])
const showPackingBoxLabelDialog = ref(false)
const renderedPackingBoxLabel = ref('')

interface InventoryItem {
  id: number
  intake_lot_id: string
  warehouse_location: string
  lot_id: string
  mat_sap_code: string
  re_code: string
  intake_vol: number
  remain_vol: number
  intake_package_vol: number
  package_intake: number
  expire_date: string
  manufacturing_date?: string
  material_description?: string
  uom?: string
  status: string
}


// Data from backend
const ingredients = ref<any[]>([])
const isLoading = ref(false)
const productionPlans = ref<any[]>([])
const productionPlanOptions = ref<string[]>([])
const allBatches = ref<any[]>([])
const filteredBatches = ref<any[]>([])
// const skuSteps = ref<any[]>([]) // Removed
const prebatchItems = ref<any[]>([])
const ingredientOptions = ref<{label: string, value: string}[]>([])


// Computed batch IDs for display
const batchIds = computed(() => filteredBatches.value.map(b => b.batch_id))

// Selected batch details
const selectedBatch = computed(() => {
  if (selectedBatchIndex.value >= 0 && filteredBatches.value.length > 0) {
    return filteredBatches.value[selectedBatchIndex.value]
  }
  return null
})

// Fetch ingredients from backend
const fetchIngredients = async () => {
    try {
        const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/ingredients/`, {
            headers: getAuthHeader() as Record<string, string>
        })
        ingredients.value = data
    } catch (e) {
        console.error('Error fetching ingredients', e)
    }
}



// Fetch production plans from backend
const fetchProductionPlans = async () => {
  try {
    isLoading.value = true
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/production-plans/`, {
      headers: getAuthHeader() as Record<string, string>
    })
    
    productionPlans.value = data
    productionPlanOptions.value = data.map(plan => plan.plan_id)
    
    /* removed auto-select to minimize initial queries */
  } catch (error) {
    console.error('Error fetching production plans:', error)
    $q.notify({
      type: 'negative',
      message: t('preBatch.errorLoadingPlans'),
      position: 'top'
    })
  } finally {
    isLoading.value = false
  }
}

// Fetch all batch IDs from backend
const fetchBatchIds = async () => {
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/production-batches/`, {
      headers: getAuthHeader() as Record<string, string>
    })
    allBatches.value = data
    filterBatchesByPlan()
  } catch (error) {
    console.error('Error fetching batch IDs:', error)
  }
}

// Filter batches based on selected production plan
const filterBatchesByPlan = async () => {
  if (!selectedProductionPlan.value) {
    filteredBatches.value = []
    ingredientOptions.value = [] // Clear ingredients if no plan
    return
  }
  
  // Find the selected production plan
  const plan = productionPlans.value.find(p => p.plan_id === selectedProductionPlan.value)
  
  if (plan) {
    // 1. Filter batches that belong to this plan and sort by batch_id (ascending)
    filteredBatches.value = allBatches.value
      .filter(batch => {
        // Match by plan_id or sku_id
        return batch.sku_id === plan.sku_id || 
               batch.batch_id.includes(plan.plan_id)
      })
      .sort((a, b) => {
        // Sort by batch_id ascending
        return a.batch_id.localeCompare(b.batch_id)
      })
    
    // 2. Fetch SKU Steps - Logic moved to onBatchSelect per user request
    /*
    if (plan.sku_id) {
       await fetchSkuStepsForPlan(plan.sku_id)
    }
    */

    // Reset selection if current index is out of bounds
    if (selectedBatchIndex.value >= filteredBatches.value.length) {
      selectedBatchIndex.value = 0
    }
    
    // Update require volume based on selected batch
    updateRequireVolume()
  }
}

const onPlanShow = (plan: any) => {
  selectedProductionPlan.value = plan.plan_id
  isBatchSelected.value = false
  // skuSteps.value = [] // Removed
  selectedReCode.value = ''
  selectedRequirementId.value = null
  fetchPreBatchRecords()
}

const onBatchSelect = async (plan: any, batch: any, index: number) => {
  selectedProductionPlan.value = plan.plan_id
  selectedBatchIndex.value = Number(index)
  isBatchSelected.value = true
  
  // Re-filter batches to ensure selectedBatch computed works correctly
  filterBatchesByPlan()

  // Fetch prebatch requirements from db table (triggers auto-creation if missing)
  await fetchPrebatchItems(batch.batch_id)
  
  // Fetch records for this plan
  await fetchPreBatchRecords()
}

const fetchPrebatchItems = async (batchId: string) => {
  try {
    // Calling the new summary endpoint
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-scans/summary/${batchId}`, {
      headers: getAuthHeader() as Record<string, string>
    })
    prebatchItems.value = data
  } catch (error) {
    console.error('Error fetching prebatch (scans) summary:', error)
    prebatchItems.value = []
  }
}

const updatePrebatchItemStatus = async (batchId: string, reCode: string, status: number) => {
  try {
    await $fetch(`${appConfig.apiBaseUrl}/prebatch-items/${batchId}/${reCode}/status?status=${status}`, {
      method: 'PUT',
      headers: getAuthHeader() as Record<string, string>
    })
    // Refresh local list
    await fetchPrebatchItems(batchId)
  } catch (error) {
    console.error('Error updating prebatch requirement status:', error)
  }
}

// State for tracking if a specific batch is selected versus just the plan
const isBatchSelected = ref(false)

// Computed ingredients list based on selected Batch (or Plan)
const selectableIngredients = computed(() => {
    if (!prebatchItems.value || prebatchItems.value.length === 0) return []

    const invList = inventoryRows.value || []
    
    // Map PBTasks to UI rows
    return prebatchItems.value.map((task: any, index: number) => {
        // Find Ingredient info for package size
        const ingInfo = ingredients.value.find(i => i.re_code === task.re_code)
        
        // Try to find inventory source default location
        const stock = invList.find((r: any) => r.re_code === task.re_code)
        
        // Use task WH if set, else stock default, else '-'
        const warehouse = (task.wh && task.wh !== '-' ? task.wh : (stock?.warehouse_location || '-')).toUpperCase()
        
        return {
            index: index + 1,
            re_code: task.re_code,
            ingredient_name: task.ingredient_name || ingInfo?.name || task.re_code,
            std_package_size: ingInfo?.std_package_size || 0,
            batch_require: task.required_volume,
            total_require: task.required_volume, 
            from_warehouse: warehouse,
             isDisabled: warehouse !== selectedWarehouse.value.toUpperCase(),
             isDone: task.status === 2,
             status: task.status,
             req_id: task.id
        }
    })
})

const getIngredientRowClass = (ing: any) => {
    if (ing.isDisabled) return 'bg-grey-3 text-grey-5 cursor-not-allowed'
    if (selectedReCode.value === ing.re_code) return 'bg-orange-2 text-deep-orange-9 text-weight-bold cursor-pointer'
    
    // Status colors
    if (ing.status === 2) return 'bg-green-1 text-green-9 cursor-pointer'
    if (ing.status === 1) return 'bg-amber-1 text-amber-9 cursor-pointer'
    
    return 'hover-bg-grey-1 cursor-pointer'
}

// Fetch Steps for the selected Plan's SKU
// fetchSkuStepsForPlan removed as we now rely on server-side PBTasks

// Watcher to handle selection reset if ingredient disappears
watch(selectableIngredients, (newList) => {
    if (selectedReCode.value && !newList.some(i => i.re_code === selectedReCode.value)) {
        selectedReCode.value = ''
    }
})


// Update require volume when batch is selected
// NOTE: User requested Request Volume to stay 0 until ingredient is selected/double-clicked.
// So we no longer auto-populate from batch size here.
const onSelectIngredient = async (ing: any) => {
    if (ing.isDisabled) return
    selectedReCode.value = ing.re_code
    selectedRequirementId.value = ing.req_id
    updateRequireVolume()

    // Update status to onBatch (1) if it's currently Created (0)
    if (ing.status === 0 && selectedBatch.value) {
        await updatePrebatchItemStatus(selectedBatch.value.batch_id, ing.re_code, 1)
    }
}

const updateRequireVolume = () => {
   // User requested Request Volume to get from Total Require on 2nd card
   if (selectedReCode.value) {
       const ing = selectableIngredients.value.find(i => i.re_code === selectedReCode.value)
       if (ing) {
           requireVolume.value = ing.total_require || 0
           
           // Optionally defaults package size if available
           if (ing.std_package_size > 0) {
               packageSize.value = ing.std_package_size
           }
       }
   } else {
       requireVolume.value = 0
   }
}

// --- Scales (static display, no MQTT) ---
const scales = computed(() => [
  {
    id: 1,
    label: 'Scale 1 (10 Kg +/- 0.01)',
    value: 0.0,
    displayValue: '0.0000',
    targetScaleId: 'scale-01',
    connected: false,
    tolerance: 0.01,
    precision: 4,
    isStable: true,
    isError: false
  },
  {
    id: 2,
    label: 'Scale 2 (30 Kg +/- 0.02)',
    value: 0.0,
    displayValue: '0.0000',
    targetScaleId: 'scale-02',
    connected: false,
    tolerance: 0.02,
    precision: 4,
    isStable: true,
    isError: false
  },
  {
    id: 3,
    label: 'Scale 3 (150 Kg +/- 0.5)',
    value: 0.0,
    displayValue: '0.0000',
    targetScaleId: 'scale-03',
    connected: false,
    tolerance: 0.5,
    precision: 4,
    isStable: true,
    isError: false
  },
])

const connectedScales = ref<Record<number, boolean>>({})

const isScaleConnected = (id: number) => !!connectedScales.value[id]

const toggleScaleConnection = (scaleId: number) => {
  const scale = scales.value.find((s) => s.id === scaleId)
  if (!scale) return
  connectedScales.value[scaleId] = !connectedScales.value[scaleId]
  $q.notify({
    type: connectedScales.value[scaleId] ? 'positive' : 'info',
    message: connectedScales.value[scaleId] ? `${t('preBatch.connected')} ${scale.label}` : `${t('preBatch.disconnected')} ${scale.label}`,
    position: 'top',
    timeout: 500
  })
}

// --- Scanner input ref (keyboard emulator mode) ---
const intakeLotInputRef = ref<any>(null)

const focusIntakeLotInput = () => {
  nextTick(() => {
    intakeLotInputRef.value?.focus()
  })
}

// Handle barcode scanner Enter key for intake lot ID
const onIntakeLotScanEnter = () => {
  // The watcher on selectedIntakeLotId already handles lookup/FIFO validation
  // So when scanner sends Enter, the value is already set and watcher fires
}

const selectedPlanDetails = computed(() => {
    return productionPlans.value.find(p => p.plan_id === selectedProductionPlan.value)
})

const structuredSkuList = computed(() => {
    const groups: Record<string, any> = {}
    
    // Filter active plans
    // Using filtered productionPlans logic
    const activePlans = productionPlans.value.filter(p => 
        !p.status || ['Active', 'In Progress', 'Released', 'Planned'].includes(p.status)
    )
    
    activePlans.forEach(plan => {
        const sku = plan.sku_id || 'No SKU'
        if (!groups[sku]) {
            groups[sku] = {
                sku: sku,
                plans: []
            }
        }
        
        // Find child batches for this plan
        // Assuming allBatches is available in scope
        const childBatches = (allBatches.value || []).filter(b => b.plan_id === plan.id || b.batch_id.includes(plan.plan_id))
                            .sort((a: any, b: any) => a.batch_id.localeCompare(b.batch_id))
        
        groups[sku].plans.push({
            ...plan,
            batches: childBatches
        })
    })
    
    return Object.values(groups).sort((a: any, b: any) => a.sku.localeCompare(b.sku))
})

onMounted(() => {
  fetchIngredients()
  fetchProductionPlans()
  fetchBatchIds()
  fetchInventory()
  fetchPreBatchRecords()
  fetchWarehouses()
  focusIntakeLotInput()
})

const fetchWarehouses = async () => {
    try {
        const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/warehouses/`, {
            headers: getAuthHeader() as Record<string, string>
        })
        warehouses.value = data
        if (data.length > 0) {
            // Auto-select FH if it exists
            const fh = data.find(w => w.warehouse_id === 'FH')
            selectedWarehouse.value = fh ? fh.warehouse_id : data[0].warehouse_id
        }
    } catch (e) {
        console.error('Error fetching warehouses', e)
    }
}

// --- Inventory Logic ---
const inventoryRows = ref<InventoryItem[]>([])
const inventoryLoading = ref(false)
const selectedInventoryItem = ref<InventoryItem[]>([])
const selectedIntakeLotId = ref('')
const showAllInventory = ref(false)
const showHistoryDialog = ref(false)
const showIntakeLabelDialog = ref(false)
const selectedHistoryItem = ref<any>(null)
const intakeLabelData = ref<any>(null)
const selectedPrinter = ref('Zebra-Label-Printer')

const printIntakeLabel = () => {
    window.print()
}

const openIntakeLabelDialog = (item: any) => {
    // Robust mapping for label data to handle potential database naming variations
    // (e.g., PascalCase from MSSQL vs camelCase from proxy)
    const normalizedData = {
        intake_lot_id: item.intake_lot_id || item.IntakeLotId || item.intake_lot || '',
        lot_id: item.lot_id || item.LotId || item.supplier_lot || '',
        re_code: item.re_code || item.ReCode || item.material_code || '',
        mat_sap_code: item.mat_sap_code || item.MatSapCode || item.sap_code || '',
        intake_vol: Number(item.intake_vol ?? item.IntakeVol ?? item.intake_volume ?? item.remain_vol ?? 0),
        package_intake: Number(item.package_intake ?? item.PackageIntake ?? item.packages ?? 1),
        expire_date: item.expire_date || item.ExpireDate || '',
        material_description: item.material_description || item.MaterialDescription || item.description || ''
    }
    
    console.log('Mapping intake label data:', { source: item, mapped: normalizedData })
    intakeLabelData.value = normalizedData
    showIntakeLabelDialog.value = true
}

const onViewHistory = (item: any) => {
    selectedHistoryItem.value = item
    showHistoryDialog.value = true
}

const inventoryColumns = computed<QTableColumn[]>(() => [
    { name: 'id', align: 'center', label: t('common.id'), field: 'id', sortable: true },
    { name: 'intake_lot_id', align: 'left', label: t('preBatch.intakeLotId'), field: 'intake_lot_id', sortable: true },
    { name: 'warehouse_location', align: 'center', label: t('preBatch.fromWarehouse'), field: 'warehouse_location' },
    { name: 'lot_id', align: 'left', label: t('ingredient.lotId'), field: 'lot_id' },
    { name: 'mat_sap_code', align: 'left', label: t('ingredient.matSapCode'), field: 'mat_sap_code' },
    { name: 're_code', align: 'center', label: t('ingredient.reCode'), field: 're_code' },
    { name: 'material_description', align: 'left', label: t('common.description'), field: 'material_description' },
    { name: 'uom', align: 'center', label: t('ingredient.uom'), field: 'uom' },
    { name: 'intake_vol', align: 'right', label: t('ingredient.intakeVolume'), field: 'intake_vol' },
    { name: 'remain_vol', align: 'right', label: t('ingredient.remainVolume'), field: 'remain_vol', classes: 'text-red text-weight-bold' },
    { name: 'intake_package_vol', align: 'right', label: t('ingredient.pkgVol'), field: 'intake_package_vol' },
    { name: 'package_intake', align: 'center', label: t('ingredient.pkgs'), field: 'package_intake' },
    { name: 'expire_date', align: 'center', label: t('ingredient.expiryDate'), field: 'expire_date', format: (val: any) => val ? val.split('T')[0] : '' },
    { name: 'po_number', align: 'left', label: t('ingredient.poNo'), field: 'po_number' },
    { name: 'manufacturing_date', align: 'center', label: t('preBatch.mfgDate'), field: 'manufacturing_date', format: (val: any) => val ? val.split('T')[0] : '' },
    { name: 'status', align: 'center', label: t('common.status'), field: 'status' },
    { name: 'actions', align: 'center', label: t('common.actions'), field: 'id' }
])

const filteredInventory = computed(() => {
    // If no ingredient selected, maybe show empty?
    if (!selectedReCode.value) return []
    // Filter by re_code and sort by expire_date (FIFO/FEFO)
    return inventoryRows.value
        .filter(item => {
            // Simple case-insensitive match just in case
            return (item.re_code || '').trim().toUpperCase() === selectedReCode.value.trim().toUpperCase() &&
                   // Match selected warehouse
                   (item.warehouse_location === selectedWarehouse.value) &&
                   // Only on-hand (>0) and Active items
                   item.remain_vol > 0 && 
                   (showAllInventory.value || item.status === 'Active')
        })
        .sort((a, b) => {
             // Sort by expire_date ascending (FIFO/FEFO)
             const dateA = a.expire_date ? new Date(a.expire_date).getTime() : Infinity
             const dateB = b.expire_date ? new Date(b.expire_date).getTime() : Infinity
             return dateA - dateB
        })
})

// Validate FIFO compliance: Must be the earliest expiring item (or same date)
const isFIFOCompliant = (item: InventoryItem) => {
    if (!item || !item.expire_date) return false // Should have expire date
    const list = filteredInventory.value
    if (list.length === 0) return false
    
    const fifoItem = list[0]
    // If FIFO item has no date, then any item is arguably valid, or invalid?
    if (!fifoItem || !fifoItem.expire_date) return true 
    
    // Strict comparison: Date must be <= FIFO Date
    const d1 = item.expire_date ? String(item.expire_date).split('T')[0] : ''
    const fifoDate = fifoItem.expire_date ? String(fifoItem.expire_date).split('T')[0] : ''
    
    if (!d1 || !fifoDate) return true // Cannot strictly enforce if dates missing
    
    return d1 <= fifoDate
}

// Watcher for manually typed/scanned intake lot id
watch(selectedIntakeLotId, (newVal) => {
    if (!newVal) {
        if (selectedInventoryItem.value.length > 0) {
             selectedInventoryItem.value = []
        }
        return
    }
    
    // Find candidate by exact match (case insensitive)
    const match = filteredInventory.value.find(i => 
        i.intake_lot_id === newVal || i.intake_lot_id.toLowerCase() === newVal.toLowerCase()
    )
    
    if (match) {
        if (isFIFOCompliant(match)) {
            selectedInventoryItem.value = [match]
            // Silent success for scanning
        } else {
             // FIFO Violation
             const fifoItem = filteredInventory.value[0]
             const expDate = (fifoItem && fifoItem.expire_date) ? fifoItem.expire_date.split('T')[0] : 'N/A'
             const expectedLot = fifoItem ? fifoItem.intake_lot_id : 'Unknown'
             
             $q.notify({
                 type: 'negative',
                 message: `FIFO Violation! Expected Lot: ${expectedLot} (Exp: ${expDate})`,
                 position: 'top',
                 timeout: 4000
             })
             // Reject selection but keep input visible for correction
             selectedInventoryItem.value = []
        }
    } else {
        // No match found
        selectedInventoryItem.value = []
    }
})

const simulateScan = () => {
    // Pick the first item from FIFO sorted list
    if (filteredInventory.value.length > 0) {
        const item = filteredInventory.value[0]
        if (item) {
            selectedIntakeLotId.value = item.intake_lot_id
            selectedInventoryItem.value = [item]
            $q.notify({ type: 'positive', message: `Simulated Scan: Selected ${item.intake_lot_id} (FIFO)` })
        }
    } else {
        $q.notify({ type: 'warning', message: 'No inventory available to scan' })
    }
}

const sortedAllInventory = computed(() => {
    // Sort by expire_date ascending (FIFO/FEFO)
    return [...inventoryRows.value]
      .filter(i => i.remain_vol > 0 && i.status === 'Active')
      .sort((a, b) => {
          const dateA = a.expire_date ? new Date(a.expire_date).getTime() : Infinity
          const dateB = b.expire_date ? new Date(b.expire_date).getTime() : Infinity
          return dateA - dateB
      })
})

const inventorySummary = computed(() => {
    const sum = {
        remain_vol: 0,
        pkgs: 0
    }
    filteredInventory.value.forEach(item => {
        sum.remain_vol += Number(item.remain_vol) || 0
        sum.pkgs += Number(item.package_intake) || 0
    })
    return sum
})

const fetchInventory = async () => {
    try {
      inventoryLoading.value = true
      const data = await $fetch<InventoryItem[]>(`${appConfig.apiBaseUrl}/ingredient-intake-lists/`, {
        headers: getAuthHeader() as Record<string, string>
      })
      inventoryRows.value = data
    } catch (error) {
      console.error('Error fetching inventory:', error)
    } finally {
      inventoryLoading.value = false
    }
}
const updateInventoryStatus = async (item: InventoryItem, newStatus: string) => {
    try {
        await $fetch(`${appConfig.apiBaseUrl}/ingredient-intake-lists/${item.id}`, {
            method: 'PUT',
            body: { ...item, status: newStatus },
            headers: getAuthHeader() as Record<string, string>
        })
        $q.notify({ type: 'positive', message: `Status updated to ${newStatus}`, position: 'top' })
        await fetchInventory()
    } catch (e) {
        console.error('Error updating status', e)
        $q.notify({ type: 'negative', message: 'Failed to update status', position: 'top' })
    }
}

// Handle inventory row selection
const onInventoryRowClick = (evt: any, row: InventoryItem) => {
    if (isFIFOCompliant(row)) {
        selectedInventoryItem.value = [row]
        selectedIntakeLotId.value = row.intake_lot_id
        
        $q.notify({
            type: 'positive',
            message: `Selected: ${row.intake_lot_id}`,
            position: 'top',
            timeout: 1000
        })
    } else {
         const fifoItem = filteredInventory.value[0]
         if (fifoItem) {
             $q.notify({
                 type: 'negative',
                 message: `FIFO Violation! Expected Lot: ${fifoItem.intake_lot_id} (Exp: ${fifoItem.expire_date ? fifoItem.expire_date.split('T')[0] : 'N/A'})`,
                 position: 'top',
                 timeout: 3000
             })
         }
         // Do not select
    }
}


// Watch for production plan changes
watch(selectedProductionPlan, () => {
  filterBatchesByPlan()
  fetchPreBatchRecords()
})

// Watch for batch selection changes
watch(selectedBatchIndex, () => {
  updateRequireVolume()
  fetchPreBatchRecords()
})

onUnmounted(() => {
  // cleanup if needed
})

// Control Fields
const requireVolume = ref(0)
const packageSize = ref(0)

const totalCompletedWeight = computed(() => {
    if (!selectedBatch.value || !selectedReCode.value) return 0
    const batchId = selectedBatch.value.batch_id
    const ingLogs = preBatchLogs.value.filter(log => 
        log.re_code === selectedReCode.value && 
        log.batch_record_id.startsWith(batchId)
    )
    return ingLogs.reduce((sum, log) => sum + (Number(log.net_volume) || 0), 0)
})

const completedCount = computed(() => {
    if (!selectedBatch.value || !selectedReCode.value) return 0
    const batchId = selectedBatch.value.batch_id
    return preBatchLogs.value.filter(log => 
        log.re_code === selectedReCode.value && 
        log.batch_record_id.startsWith(batchId)
    ).length
})

const nextPackageNo = computed(() => {
    if (!selectedBatch.value || !selectedReCode.value) return 1
    const batchId = selectedBatch.value.batch_id
    
    // Get all existing package numbers for this ingredient in this batch
    const existingNos = preBatchLogs.value
        .filter(log => log.re_code === selectedReCode.value && log.batch_record_id.startsWith(batchId))
        .map(log => Number(log.package_no))
        .sort((a, b) => a - b)
    
    // Find the first hole or the next number
    let next = 1
    while (existingNos.includes(next)) {
        next++
    }
    return next
})

const remainToBatch = computed(() => {
    return Math.max(0, requireVolume.value - totalCompletedWeight.value - actualScaleValue.value)
})

const targetWeight = computed(() => {
    if (requireVolume.value <= 0 || packageSize.value <= 0) return 0
    return Math.min(remainToBatch.value, packageSize.value)
})

const requestBatch = computed(() => {
    if (packageSize.value <= 0) return 0
    return Math.ceil(requireVolume.value / packageSize.value)
})

// --- Package Label Dialog State ---
const showLabelDialog = ref(false)
const packageLabelId = ref('')
const capturedScaleValue = ref(0)
const renderedLabel = ref('')

const labelDataMapping = computed(() => {
  if (!selectedBatch.value || !selectedReCode.value) return null
  
  const ing = selectableIngredients.value.find(i => i.re_code === selectedReCode.value)
  const pkgNo = nextPackageNo.value
  const totalPkgs = requestBatch.value
  
  return {
    RecipeName: selectedBatch.value.sku_name || selectedBatch.value.sku_id || '-',
    BaseQuantity: selectedBatch.value.batch_size || 0,
    ItemNumber: ing?.index || '-',
    RefCode: selectedReCode.value,
    OrderCode: selectedBatch.value.plan_id || '-',
    BatchSize: selectedBatch.value.batch_size || 0,
    Weight: `${capturedScaleValue.value.toFixed(2)} / ${requireVolume.value.toFixed(2)}`,
    Packages: `${pkgNo} / ${totalPkgs}`,
    LotID: selectedIntakeLotId.value || '-',
    QRCode: `${selectedBatch.value.plan_id},${selectedBatch.value.batch_id},${selectedReCode.value},${capturedScaleValue.value}`,
    SmallQRCode: `${selectedBatch.value.plan_id},${selectedBatch.value.batch_id},${selectedReCode.value},${capturedScaleValue.value}`
  }
})

const updateDialogPreview = async () => {
  if (labelDataMapping.value) {
    const svg = await generateLabelSvg('prebatch-label', labelDataMapping.value)
    renderedLabel.value = svg || ''
  }
}

watch(showLabelDialog, (val) => {
  if (val) updateDialogPreview()
})

const packingBoxLabelDataMapping = computed(() => {
  if (!selectedBatch.value || selectedPreBatchLogs.value.length === 0) return null
  
  const totalWeight = selectedPreBatchLogs.value.reduce((sum, row) => sum + (Number(row.net_volume) || 0), 0)
  const bagCount = selectedPreBatchLogs.value.length
  
  return {
    BoxID: selectedBatch.value.plan_id || '-',
    BatchID: selectedBatch.value.batch_id || '-',
    BagCount: bagCount,
    NetWeight: totalWeight.toFixed(2),
    Operator: user.value?.username || '-',
    Timestamp: new Date().toLocaleString(),
    BoxQRCode: `${selectedBatch.value.plan_id},${selectedBatch.value.batch_id},BOX,${bagCount},${totalWeight.toFixed(2)}`
  }
})

const updatePackingBoxPreview = async () => {
  if (packingBoxLabelDataMapping.value) {
    const svg = await generateLabelSvg('packingbox-label', packingBoxLabelDataMapping.value)
    renderedPackingBoxLabel.value = svg || ''
  }
}

watch(showPackingBoxLabelDialog, (val) => {
  if (val) updatePackingBoxPreview()
})

const onPrintPackingBoxLabel = async () => {
  if (!packingBoxLabelDataMapping.value) return
  
  if (renderedPackingBoxLabel.value) {
    printLabel(renderedPackingBoxLabel.value)
    $q.notify({ type: 'positive', message: 'Packing Box Label Sent to Printer' })
    showPackingBoxLabelDialog.value = false
    selectedPreBatchLogs.value = [] // Clear selection after print
  }
}

const batchedVolume = ref(0) // Total volume already batched
const remainVolume = computed(() => {
    return Math.max(0, requireVolume.value - batchedVolume.value)
})

// Computed Actual Scale Value based on selected scale
const activeScale = computed(() => scales.value.find(s => s.id === selectedScale.value))

const actualScaleValue = computed(() => {
  return activeScale.value ? activeScale.value.value : 0
})

// Automate scale selection based on Package Size
watch(packageSize, (val) => {
  if (val <= 0) {
    selectedScale.value = 0
  } else if (val <= 10) {
    selectedScale.value = 1
  } else if (val <= 30) {
    selectedScale.value = 2
  } else {
    selectedScale.value = 3
  }
})
const filteredPreBatchLogs = computed(() => {
    return preBatchLogs.value
})

const preBatchSummary = computed(() => {
    const logs = filteredPreBatchLogs.value
    const totalNetWeight = logs.reduce((sum, log) => sum + (log.net_volume || 0), 0)
    const count = logs.length
    const targetW = requireVolume.value || 0
    const errorVol = totalNetWeight - targetW
    
    return {
        count,
        totalNetWeight: totalNetWeight.toFixed(4),
        targetCount: requestBatch.value || 0,
        targetWeight: targetW.toFixed(4),
        errorVolume: errorVol.toFixed(4),
        errorColor: errorVol > 0 ? 'text-red' : (errorVol < 0 ? 'text-orange' : 'text-green')
    }
})

// Check if out of tolerance
const isToleranceExceeded = computed(() => {
  if (!activeScale.value) return false
  const diff = Math.abs(targetWeight.value - actualScaleValue.value)
  return diff > activeScale.value.tolerance
})

const isPackagedVolumeInTol = computed(() => {
  if (!activeScale.value || targetWeight.value <= 0) return false
  const diff = Math.abs(targetWeight.value - batchedVolume.value)
  return diff <= activeScale.value.tolerance
})

const packagedVolumeBgColor = computed(() => {
  if (batchedVolume.value <= 0) return 'grey-2' // Neutral if empty
  return isPackagedVolumeInTol.value ? 'green-13' : 'yellow-13'
})

// Sync Packaged Volume with Active Scale live when ingredient is selected
watch(actualScaleValue, (newVal) => {
  if (selectedReCode.value) {
    batchedVolume.value = newVal
  } else {
    batchedVolume.value = 0
  }
}, { immediate: true })

// Also sync if ingredient just got selected to catch current scale value immediately
watch(selectedReCode, (newReCode) => {
  if (newReCode) {
    batchedVolume.value = actualScaleValue.value
  } else {
    batchedVolume.value = 0
  }
})

// PreBatch Records from database
const preBatchLogs = ref<any[]>([])

const prebatchColumns: QTableColumn[] = [
    { name: 'batch_id', align: 'left', label: 'Batch ID', field: 'batch_record_id', format: (val: string) => val.split('-').slice(0, 6).join('-'), classes: 'text-caption' },
    { name: 're_code', align: 'left', label: 'Ingredient', field: 're_code', sortable: true },
    { name: 'package_no', align: 'center', label: 'Pkg', field: 'package_no' },
    { name: 'net_volume', align: 'right', label: 'Net (kg)', field: 'net_volume', format: (val: any) => Number(val).toFixed(4) },
    { name: 'intake_lot_id', align: 'left', label: 'Intake Lot', field: 'intake_lot_id', sortable: true },
    { name: 'reprint', align: 'center', label: 'Print', field: 'id' },
    { name: 'actions', align: 'center', label: '', field: 'id' }
]

const fetchPreBatchRecords = async () => {
  if (!selectedBatch.value) return
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-recs/by-batch/${selectedBatch.value.batch_id}`, {
      headers: getAuthHeader() as Record<string, string>
    })
    preBatchLogs.value = data
  } catch (error) {
    console.error('Error fetching prebatch records:', error)
  }
}

const recordToDelete = ref<any>(null)

const executeDeletion = async (record: any) => {
    try {
      await $fetch(`${appConfig.apiBaseUrl}/prebatch-recs/${record.id}`, {
        method: 'DELETE',
        headers: getAuthHeader() as Record<string, string>
      })
      
      $q.notify({ 
        type: 'positive', 
        message: `Package #${record.package_no} cancelled. Inventory restored.`,
        icon: 'restore'
      })
      
      showDeleteDialog.value = false
      recordToDelete.value = null
      deleteInput.value = ''
      
      await fetchPreBatchRecords()
      if (selectedBatch.value) {
      await fetchPrebatchItems(selectedBatch.value.batch_id)
      }
    } catch (err) {
      console.error('Error deleting record:', err)
      $q.notify({ type: 'negative', message: 'Failed to cancel record' })
    }
}

const onDeleteRecord = (record: any) => {
  recordToDelete.value = record
  deleteInput.value = ''
  showDeleteDialog.value = true
}

const onConfirmDeleteManual = async () => {
    if (!recordToDelete.value) return
    
    const val = deleteInput.value.trim()
    if (val === String(recordToDelete.value.package_no) || val === recordToDelete.value.batch_record_id) {
        await executeDeletion(recordToDelete.value)
    } else {
        $q.notify({ 
          type: 'negative', 
          message: 'Invalid input. Please scan the label or type the exact package number.',
          position: 'top'
        })
    }
}

// Watch for scans during deletion mode
// Delete confirmation via typed input (keyboard scanner emulator)
const onDeleteScanEnter = async () => {
  if (!showDeleteDialog.value || !recordToDelete.value) return

  if (deleteInput.value === recordToDelete.value.batch_record_id) {
    await executeDeletion(recordToDelete.value)
  } else {
    $q.notify({ 
      type: 'negative', 
      message: `Invalid code! Expected: ${recordToDelete.value.batch_record_id}`,
      position: 'top',
      timeout: 3000
    })
  }
}

const unlockPackageSize = () => {
    if (!isPackageSizeLocked.value) {
        isPackageSizeLocked.value = true
        return
    }
    authPassword.value = ''
    showAuthDialog.value = true
}

const verifyAuth = async () => {
    if (!user.value || !authPassword.value) return
    
    try {
        const payload = {
            username_or_email: user.value.username,
            password: authPassword.value
        }
        
        await $fetch(`${appConfig.apiBaseUrl}/auth/verify`, {
            method: 'POST',
            body: payload
        })
        
        isPackageSizeLocked.value = false
        showAuthDialog.value = false
        authPassword.value = ''
        $q.notify({ type: 'positive', message: 'Authorization successful' })
    } catch (err) {
        $q.notify({ type: 'negative', message: 'Invalid password. Authorization failed.' })
    }
}



const onIngredientSelect = () => {
    // When ingredient is selected, we should fetch/filter the PreBatch List
    // For now, we simulate this by refreshing the mock logs or showing a notification
    // If backend existed: fetchPreBatchLogs(planId, reCode)
    
    if (selectedReCode.value) {
        // Auto-select first inventory item (FIFO - First In First Out)
        // The filteredInventory is already filtered by re_code
        if (filteredInventory.value.length > 0) {
            const firstItem = filteredInventory.value[0]
            if (firstItem) {
                selectedInventoryItem.value = [firstItem]
                selectedIntakeLotId.value = firstItem.intake_lot_id
                
                $q.notify({
                    type: 'positive', 
                    message: t('preBatch.autoSelectedFifo', { id: firstItem.intake_lot_id }),
                    position: 'top',
                    timeout: 1000
                })
            }
        } else {
            // No inventory available
            selectedInventoryItem.value = []
            selectedIntakeLotId.value = ''
            
            $q.notify({
                type: 'warning', 
                message: t('preBatch.noInventoryFor', { id: selectedReCode.value }),
                position: 'top',
                timeout: 1000
            })
        }
    }
}

const onIngredientDoubleClick = (ingredient: any) => {
    // Fill Require Volume with the calculated total requirement
    if (ingredient && ingredient.total_require !== undefined) {
        requireVolume.value = Number(ingredient.total_require.toFixed(3))
        
        // Auto-fill Package Size from ingredient standard
        if (ingredient.std_package_size) {
            packageSize.value = Number(ingredient.std_package_size)
        }
        
        $q.notify({
            type: 'positive',
            message: t('preBatch.initBatching', { id: ingredient.re_code }),
            position: 'top',
            timeout: 500
        })
    }
}

// Watch for preBatchLogs or selectedBatch to update isDone status of selectableIngredients
watch([preBatchLogs, selectedBatch], ([logs, batch]) => {
    if (!logs || !batch) {
        selectableIngredients.value.forEach(ing => ing.isDone = false)
        return
    }
    
    let allDone = true
    selectableIngredients.value.forEach(ing => {
        // Filter logs that belong to this specific batch and ingredient
        const ingLogs = logs.filter(l => l.re_code === ing.re_code && l.batch_record_id.startsWith(batch.batch_id))
        
        if (ingLogs.length > 0) {
            // Find max package_no recorded for this specific batch
            const maxPkg = Math.max(...ingLogs.map(l => l.package_no || 0))
            const totalPkgs = ingLogs[0]?.total_packages || 0
            if (maxPkg >= totalPkgs && totalPkgs > 0) {
                ing.isDone = true
            } else {
                ing.isDone = false
                allDone = false
            }
        } else {
            ing.isDone = false
            allDone = false
        }
    })

    // If all ingredients for this batch are done, update the ProductionBatch status in backend
    if (selectableIngredients.value.length > 0 && allDone && !batch.batch_prepare) {
        finalizeBatchPreparation(batch.id)
    }
}, { deep: true })

const finalizeBatchPreparation = async (batchId: number) => {
    try {
        await $fetch(`${appConfig.apiBaseUrl}/production-batches/${batchId}`, {
            method: 'PUT',
            body: { batch_prepare: true, status: 'Prepared' },
            headers: getAuthHeader() as Record<string, string>
        })
        $q.notify({ type: 'positive', message: t('preBatch.prepFinalized'), position: 'top' })
        // Refresh all batch info to reflect status change
        await fetchBatchIds()
    } catch (e) {
        console.error('Failed to finalize batch preparation', e)
    }
}

// --- Helper for Scale Styling ---
const getScaleClass = (scale: any) => {
  if (selectedScale.value !== scale.id) {
    // Unselected card background
    return 'scale-card-border bg-grey-1'
  }
  // Selected card background (keep neutral to let display color pop)
  return 'active-scale-border bg-white'
}

const getDisplayClass = (scale: any) => {
  // 0. Error state - Red Blink (Priority over selection)
  if (scale.isError) {
    return 'bg-red-blink text-white'
  }

  // 1. Not selected - Gray (Inactive)
  if (selectedScale.value !== scale.id) {
    return 'bg-grey-4 text-grey-6' 
  }
  
  // 2. Selected
  const diff = Math.abs(targetWeight.value - scale.value)
  // Check if within tolerance
  if (targetWeight.value > 0 && diff <= scale.tolerance) {
    // In Range -> Green
    return 'bg-green-6 text-white'
  }
  
  // 3. Selected but Not in Range (or request is 0) -> Yellow
  return 'bg-yellow-13 text-black'
}

// --- Actions ---
const onTare = (scaleId: number) => {
  $q.notify({
    type: 'info',
    message: `Tare command sent to Scale ${scaleId}`,
    position: 'top',
    timeout: 1000,
  })
}

// --- Package Label Dialog ---
const openLabelDialog = () => {
  capturedScaleValue.value = actualScaleValue.value
  if (selectedBatch.value && selectedReCode.value) {
    packageLabelId.value = `${selectedBatch.value.batch_id}-${selectedReCode.value}-${nextPackageNo.value}`
  } else {
    packageLabelId.value = ''
  }
  showLabelDialog.value = true
}

const onReprint = () => {
  if (!packageLabelId.value) {
    $q.notify({ type: 'warning', message: 'Please enter Package Label ID' })
    return
  }
  $q.notify({ type: 'info', message: `Reprinting label: ${packageLabelId.value}` })
}

const onPrintLabel = async () => {
  if (!selectedBatch.value || !selectedReCode.value) {
    $q.notify({ type: 'warning', message: 'Missing Batch or Ingredient selection' })
    return
  }

  try {
    const pkgNo = nextPackageNo.value
    const totalPkgs = requestBatch.value
    
    if (isNaN(pkgNo) || isNaN(totalPkgs)) {
        throw new Error('Invalid package numbers')
    }

    // Capture dynamic scale data for record
    const recordData = {
      req_id: selectedRequirementId.value,
      batch_record_id: `${selectedBatch.value.batch_id}-${selectedReCode.value}-${pkgNo}`,
      plan_id: selectedProductionPlan.value,
      re_code: selectedReCode.value,
      package_no: pkgNo,
      total_packages: totalPkgs,
      net_volume: capturedScaleValue.value,
      total_volume: requireVolume.value,
      total_request_volume: targetWeight.value,
      intake_lot_id: selectedIntakeLotId.value
    }

    // 1. Save to Database
    await $fetch(`${appConfig.apiBaseUrl}/prebatch-recs/`, {
      method: 'POST',
      body: recordData,
      headers: getAuthHeader() as Record<string, string>
    })

    // 2. Generate and Print SVG Label
    if (labelDataMapping.value) {
      const svg = await generateLabelSvg('prebatch-label', labelDataMapping.value)
      if (svg) {
        printLabel(svg)
      }
    }

    $q.notify({ type: 'positive', message: t('preBatch.saveAndPrintSuccess'), position: 'top' })
    
    // Refresh prebatch logs
    await fetchPreBatchRecords()
    
    // Check if finished
    if (pkgNo >= totalPkgs) {
        $q.notify({ type: 'info', message: t('preBatch.allPkgsCompleted') })
        if (selectedBatch.value) {
            await updatePrebatchItemStatus(selectedBatch.value.batch_id, selectedReCode.value, 2)
        }
    }

    showLabelDialog.value = false
  } catch (error) {
    console.error('Error saving prebatch record:', error)
    $q.notify({ type: 'negative', message: 'Failed to save record' })
  }
}

const onReprintLabel = async (record: any) => {
  if (!record || !selectedBatch.value) return
  
  try {
    const data = {
      RecipeName: selectedBatch.value.sku_name || selectedBatch.value.sku_id || '-',
      BaseQuantity: selectedBatch.value.batch_size || 0,
      ItemNumber: record.item_number || '-',
      RefCode: record.re_code || '-',
      OrderCode: record.plan_id || selectedBatch.value.plan_id || '-',
      BatchSize: selectedBatch.value.batch_size || 0,
      Weight: `${record.net_volume.toFixed(2)} / ${record.total_volume.toFixed(2)}`,
      Packages: `${record.package_no} / ${record.total_packages}`,
      LotID: record.intake_lot_id || '-',
      QRCode: `${selectedBatch.value.plan_id},${record.batch_record_id},${record.re_code},${record.net_volume}`,
      SmallQRCode: `${selectedBatch.value.plan_id},${record.batch_record_id},${record.re_code},${record.net_volume}`
    }

    const svg = await generateLabelSvg('prebatch-label', data)
    if (svg) {
      printLabel(svg)
      $q.notify({ type: 'info', message: 'Reprinting label...', position: 'top', timeout: 800 })
    }
  } catch (err) {
    console.error('Reprint failed:', err)
    $q.notify({ type: 'negative', message: 'Reprint failed' })
  }
}

const quickReprint = async (ing: any) => {
  if (!ing || !selectedBatch.value) return
  const batchId = selectedBatch.value.batch_id
  const logs = preBatchLogs.value.filter(l => l.re_code === ing.re_code && l.batch_record_id.startsWith(batchId))
  if (logs.length > 0) {
    // Reprint the last one
    const lastRecord = logs.reduce((prev: any, current: any) => (prev.package_no > current.package_no) ? prev : current)
    await onReprintLabel(lastRecord)
  } else {
    $q.notify({ type: 'warning', message: 'No records found to reprint' })
  }
}

const onDone = () => {
  if (!selectedReCode.value) {
    $q.notify({ type: 'warning', message: 'Please select an ingredient first' })
    return
  }
  
  if (completedCount.value >= requestBatch.value && requestBatch.value > 0) {
    $q.notify({ type: 'warning', message: 'All packages for this ingredient are already completed' })
    return
  }
  
  if (!selectedIntakeLotId.value) {
    $q.notify({ type: 'negative', message: 'Please scan or select an Intake Lot ID first', position: 'top' })
    return
  }

  // Open the dialog instead of just notifying
  openLabelDialog()
}

const onSelectBatch = (index: number) => {
  selectedBatchIndex.value = index
}
</script>

<template>
  <q-page class="q-pa-md bg-white">
    <!-- Page Header -->
    <div class="bg-blue-9 text-white q-pa-md rounded-borders q-mb-sm shadow-2">
      <div class="row justify-between items-center">
        <div class="row items-center q-gutter-sm">
          <q-icon name="science" size="sm" />
          <div class="text-h6 text-weight-bolder">{{ t('preBatch.title') }}</div>
        </div>
        <div class="text-caption text-blue-2">{{ t('prodPlan.version') }} 0.1</div>
      </div>
    </div>

    <div class="row q-col-gutter-lg">
      <!-- LEFT SIDEBAR -->
      <div class="col-12 col-md-3 column q-gutter-y-sm" style="height: calc(100vh - 100px);">
        <!-- CARD 1: SKU on Active Master Plans -->
        <q-card class="col column bg-white shadow-2" style="max-height: 30vh;">
            <div class="col relative-position">
                <q-scroll-area class="fit">
                   <q-list class="rounded-borders text-caption">
                      <q-expansion-item
                        v-for="skuGroup in structuredSkuList"
                        :key="skuGroup.sku"
                        expand-separator
                        icon="category"
                        :label="skuGroup.sku"
                        header-class="bg-blue-grey-1 text-weight-bold"
                        default-opened
                        dense
                        dense-toggle
                      >
                        <q-expansion-item
                          v-for="plan in skuGroup.plans"
                          :key="plan.plan_id"
                          :header-inset-level="0.5"
                          expand-separator
                          icon="assignment"
                          :label="plan.plan_id"
                          :caption="String(plan.status || '')"
                          header-class="text-weight-bold"
                          dense
                          dense-toggle
                          @show="onPlanShow(plan)"
                        >
                          <!-- Batch List -->
                           <q-list dense separator padding class="text-caption">
                              <q-item 
                                 v-for="(batch, idx) in plan.batches" 
                                 :key="batch.batch_id"
                                 clickable
                                 v-ripple
                                 :active="selectedProductionPlan === plan.plan_id && selectedBatchIndex === idx && isBatchSelected"
                                 active-class="bg-blue-1 text-primary text-weight-bold"
                                 @click.stop="onBatchSelect(plan, batch, Number(idx))"
                                 style="padding-left: 32px; min-height: 32px;"
                              >
                                 <q-item-section>
                                   <q-item-label>{{ batch.batch_id }}</q-item-label>
                                   <q-item-label caption style="font-size: 0.7rem;">{{ t('preBatch.batchSizeShort', { size: batch.batch_size }) }}</q-item-label>
                                 </q-item-section>
                                 <q-item-section side>
                                     <q-badge color="green" :label="batch.status" size="sm" />
                                 </q-item-section>
                              </q-item>
                              <q-item v-if="!plan.batches || plan.batches.length === 0" style="min-height: 32px;">
                                  <q-item-section class="text-grey text-italic q-pl-lg" style="font-size: 0.7rem;">{{ t('preBatch.noBatchesCreated') }}</q-item-section>
                              </q-item>
                           </q-list>
                        </q-expansion-item>
                      </q-expansion-item>
                      
                      <div v-if="structuredSkuList.length === 0" class="text-center q-pa-md text-grey">
                          {{ t('preBatch.noActiveSkus') }}
                      </div>
                   </q-list>
                </q-scroll-area>
            </div>
        </q-card>

        <!-- NEW CARD: Warehouse Selection -->
        <q-card class="col-auto bg-white shadow-2">
            <q-card-section class="q-py-sm">
                <div class="text-subtitle2 text-weight-bold q-mb-xs">{{ t('preBatch.warehouseLocation') }}</div>
                <q-select
                    v-model="selectedWarehouse"
                    :options="warehouses"
                    option-label="name"
                    option-value="warehouse_id"
                    emit-value
                    map-options
                    outlined
                    dense
                    bg-color="blue-grey-1"
                    class="text-weight-bold"
                >
                    <template v-slot:prepend>
                        <q-icon name="warehouse" color="primary" />
                    </template>
                </q-select>
            </q-card-section>
        </q-card>

        <!-- CARD 2: Ingredients for Selected Plan -->
        <q-card class="col-auto bg-white shadow-2 column" style="max-height: 400px;">
            <template v-if="selectedProductionPlan">
              <q-card-section class="bg-orange-8 text-white q-py-xs shadow-1">
                  <div class="row items-center justify-between no-wrap">
                      <div class="text-subtitle2 text-weight-bold">
                          {{ t('preBatch.requireIngredient') }}
                      </div>
                      <q-badge color="white" text-color="orange-9" class="text-weight-bold">
                          {{ selectableIngredients.length }} {{ t('preBatch.items') }}
                      </q-badge>
                  </div>
                  <div class="text-caption text-orange-1 text-weight-bold ellipsis" style="font-size: 0.9rem;">
                      {{ selectedPlanDetails?.sku_id || 'Unknown SKU' }}
                  </div>
                  <div class="text-caption text-orange-2" style="font-size: 0.7rem;">
                      {{ t('prodPlan.planId') }}: {{ selectedProductionPlan }} <span v-if="isBatchSelected">({{ t('prodPlan.batchId') }}: {{ selectedBatch?.batch_id.slice(-3) }})</span>
                  </div>
              </q-card-section>
            </template>
            <template v-else>
               <q-card-section class="bg-grey-3 text-grey-8 q-py-xs text-center">
                   <div class="text-caption">{{ t('preBatch.selectPlanAbove') }}</div>
               </q-card-section>
            </template>
            <div class="col relative-position" style="overflow-y: auto;">
                <q-markup-table dense flat square separator="cell" sticky-header>
                    <thead class="bg-orange-1 text-orange-10">
                        <tr>
                            <th class="text-left" style="font-size: 0.7rem;">{{ t('preBatch.ingredient') }}</th>
                            <th class="text-center" style="font-size: 0.7rem;">{{ t('preBatch.wh') }}</th>
                            <th class="text-right" style="font-size: 0.7rem;">{{ t('preBatch.reqKg') }}</th>
                            <th class="text-center" style="font-size: 0.7rem;">{{ t('common.status') }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr 
                            v-for="ing in selectableIngredients" 
                            :key="ing.re_code"
                            class="transition-all"
                            :class="getIngredientRowClass(ing)"
                            @click="onSelectIngredient(ing)"
                        >
                            <td class="text-weight-bold" style="font-size: 0.75rem;">
                                {{ ing.re_code }}
                                <q-tooltip>{{ ing.ingredient_name }}</q-tooltip>
                            </td>
                            <td class="text-center text-caption" style="font-size: 0.7rem;">{{ ing.from_warehouse }}</td>
                            <td class="text-right text-weight-bold" style="font-size: 0.75rem;">{{ ing.batch_require ? ing.batch_require.toFixed(3) : '0' }}</td>
                            <td class="text-center">
                                <div v-if="ing.status === 2" class="row no-wrap items-center justify-center q-gutter-x-xs">
                                    <q-badge color="green" :label="t('preBatch.complete')" size="sm" />
                                    <q-btn flat round dense icon="print" size="xs" color="blue-7" @click.stop="quickReprint(ing)">
                                        <q-tooltip>{{ t('preBatch.reprintTooltip') }}</q-tooltip>
                                    </q-btn>
                                </div>
                                <q-badge v-else-if="ing.status === 1" color="orange" :label="t('preBatch.onBatch')" size="sm" />
                                <q-badge v-else color="grey-6" label="Created" size="sm" />
                            </td>
                        </tr>
                        <tr v-if="selectableIngredients.length === 0">
                            <td colspan="4" class="text-center text-grey q-pa-md">
                                <div v-if="selectedProductionPlan && isBatchSelected">{{ t('preBatch.noIngredientsFound') }}</div>
                                <div v-else-if="selectedProductionPlan">{{ t('preBatch.selectBatchToView') }}</div>
                                <div v-else>{{ t('preBatch.selectPlanToView') }}</div>
                            </td>
                        </tr>
                    </tbody>
                </q-markup-table>
            </div>
        </q-card>
      </div>

      <!-- RIGHT MAIN CONTENT -->
      <div class="col-12 col-md-9">
        <!-- SCALES SECTION -->
        <q-card bordered flat class="q-mb-lg">
          <q-card-section class="q-pb-none row items-center">
            <div class="text-h6">{{ t('preBatch.weightingScale') }}</div>
            <q-space />
            <q-badge 
              color="blue-grey" 
              label="Scales"
              class="q-px-md"
            >
              <q-tooltip>Scale display</q-tooltip>
            </q-badge>
          </q-card-section>

          <q-card-section>
            <div class="row q-col-gutter-md">
              <div v-for="scale in scales" :key="scale.id" class="col-12 col-md-4">
                <q-card flat :bordered="selectedScale !== scale.id" class="q-pa-sm column" :class="getScaleClass(scale)">
                  <div class="row justify-between items-center q-mb-sm">
                    <div class="text-h6 text-weight-bold">{{ scale.label }}</div>
                    <div 
                      class="status-indicator shadow-2"
                      :class="scale.connected ? 'bg-green-14' : 'bg-red-14'"
                      @click="toggleScaleConnection(scale.id)"
                    ></div>
                  </div>

                  <!-- Digital Display -->
                  <div class="q-mb-md">
                    <div
                      class="relative-position text-right q-pa-sm text-h3 text-weight-bold rounded-borders flex items-center justify-end"
                      :class="getDisplayClass(scale)"
                    >
                      <!-- Stable Indicator -->
                      <div class="absolute-top-left q-ma-sm row items-center no-wrap" style="pointer-events: none;">
                          <div 
                              class="stable-spot shadow-1"
                              :class="scale.isStable ? 'bg-green-14' : 'bg-orange-14 anim-vibrate'"
                           ></div>
                      </div>

                      {{ scale.displayValue }}
                    </div>
                  </div>
                </q-card>
              </div>
            </div>
          </q-card-section>
        </q-card>

        <q-card bordered flat class="q-mb-md">
            <q-card-section class="q-pb-none row items-center">
              <div class="text-h6">{{ t('preBatch.onHandInventory') }}</div>
              <q-space />
              <q-btn flat round dense icon="refresh" color="primary" @click="fetchInventory" class="q-mr-sm">
                  <q-tooltip>{{ t('preBatch.refreshInventory') }}</q-tooltip>
              </q-btn>
              <q-checkbox v-model="showAllInventory" :label="t('preBatch.showAllInv')" dense class="text-caption" />
            </q-card-section>
           <q-card-section>
              <q-table
                 flat
                 bordered
                 dense
                 :rows="filteredInventory"
                 :columns="inventoryColumns"
                 row-key="id"
                 :loading="inventoryLoading"
                 separator="cell"
                 :pagination="{ rowsPerPage: 5 }"
                 selection="single"
                 v-model:selected="selectedInventoryItem"
                 @row-click="onInventoryRowClick"
              >
                <!-- Status Slot -->
                 <template v-slot:body-cell-status="props">
                    <q-td :props="props" class="text-center">
                        <q-badge :color="props.value === 'Active' ? 'green' : (props.value === 'Hold' ? 'orange' : 'red')">
                            {{ props.value }}
                        </q-badge>
                    </q-td>
                </template>

                <!-- Actions Slot -->
                <template v-slot:body-cell-actions="props">
                    <q-td :props="props" class="text-center">
                        <div class="row no-wrap q-gutter-xs justify-center">
                            <q-btn 
                                round dense flat size="sm" 
                                color="blue" icon="print" 
                                @click.stop="openIntakeLabelDialog(props.row)"
                            >
                                <q-tooltip>{{ t('preBatch.printIntakeLabel') }}</q-tooltip>
                            </q-btn>
                            <q-btn 
                                round dense flat size="sm" 
                                color="blue" icon="history" 
                                @click.stop="onViewHistory(props.row)"
                            >
                                <q-tooltip>{{ t('preBatch.viewHistoryMonitor') }}</q-tooltip>
                            </q-btn>
                            <q-btn 
                                round dense flat size="sm" 
                                color="yellow-9" icon="settings" 
                                @click.stop="onViewHistory(props.row)"
                            >
                                <q-tooltip>{{ t('preBatch.invSettings') }}</q-tooltip>
                            </q-btn>
                        </div>
                    </q-td>
                </template>

                <!-- Summary Row -->
                <template v-slot:bottom-row>
                    <q-tr class="bg-grey-2 text-weight-bold">
                        <q-td colspan="9" class="text-right">{{ t('preBatch.total') }}</q-td>
                        <q-td class="text-right">{{ inventorySummary.remain_vol.toFixed(3) }}</q-td>
                        <q-td></q-td>
                        <q-td class="text-center">{{ inventorySummary.pkgs }}</q-td>
                        <q-td colspan="5"></q-td>
                    </q-tr>
                </template>
                
                <template v-slot:no-data>
                   <div class="full-width row flex-center q-pa-md text-grey">
                      <span v-if="!selectedReCode">Select an ingredient to view inventory</span>
                      <span v-else>No inventory found for {{ selectedReCode }}</span>
                   </div>
                </template>
             </q-table>
           </q-card-section>
        </q-card>

        <!-- Package Batching Prepare Section -->
        <q-card bordered flat class="q-mb-md bg-grey-1">
            <q-card-section class="q-pb-sm">
                <div class="row q-col-gutter-md items-center">
                    <!-- Title -->
                    <div class="col-auto">
                        <div class="text-h6">{{ t('preBatch.packagePrepareFor') }}</div>
                    </div>
                    
                    <!-- Batch Planning ID -->
                    <div class="col">
                        <q-input
                        outlined
                        :model-value="selectedBatch ? selectedBatch.batch_id : ''"
                        dense
                        bg-color="grey-2"
                        readonly
                        :placeholder="t('preBatch.batchPlanningId')"
                        />
                    </div>

                    <!-- From Intake Lot ID Label -->
                    <div class="col-auto">
                        <div class="text-h6">{{ t('preBatch.fromIntakeLotId') }}</div>
                    </div>

                    <!-- Selected Intake Lot ID -->
                    <div class="col">
                        <q-input
                        ref="intakeLotInputRef"
                        outlined
                        v-model="selectedIntakeLotId"
                        dense
                        bg-color="white"
                        :placeholder="t('preBatch.scanIntakeLotId')"
                        clearable
                        autofocus
                        @keyup.enter="onIntakeLotScanEnter"
                        />
                    </div>
                </div>
            </q-card-section>

            <q-card-section>
                <!-- CONTROLS ROW 1 -->
                <div class="row q-col-gutter-md q-mb-md">

                <!-- Request Volume (col-md) -->
                <div class="col-12 col-md">
                    <div class="text-subtitle2 q-mb-xs text-no-wrap">{{ t('preBatch.requestVolume') }}</div>
                    <q-input
                    outlined
                    :model-value="requireVolume.toFixed(4)"
                    dense
                    bg-color="grey-2"
                    readonly
                    input-class="text-right"
                    />
                </div>

                <!-- Req for this Package (col-md) -->
                <div class="col-12 col-md">
                    <div class="text-subtitle2 q-mb-xs text-no-wrap text-blue-9 text-weight-bold">{{ t('preBatch.reqForPackage') }}</div>
                    <q-input
                    outlined
                    :model-value="targetWeight.toFixed(4)"
                    dense
                    bg-color="blue-1"
                    readonly
                    input-class="text-right text-weight-bold"
                    />
                </div>

                <!-- Packaged Volume (col-md) -->
                <div class="col-12 col-md">
                    <div class="text-subtitle2 q-mb-xs text-no-wrap">{{ t('preBatch.packagedVolume') }}</div>
                    <q-input
                    outlined
                    :model-value="batchedVolume.toFixed(4)"
                    dense
                    :bg-color="packagedVolumeBgColor"
                    readonly
                    input-class="text-right text-weight-bold"
                    />
                </div>

                <!-- Remain Volume (col-md) -->
                <div class="col-12 col-md">
                    <div class="text-subtitle2 q-mb-xs text-no-wrap">{{ t('preBatch.remainVolume') }}</div>
                    <q-input
                    outlined
                    :model-value="remainToBatch.toFixed(4)"
                    dense
                    bg-color="grey-2"
                    readonly
                    input-class="text-right"
                    />
                </div>
                
                <!-- Package Size (col-md) -->
                <div class="col-12 col-md">
                    <div class="text-subtitle2 q-mb-xs text-no-wrap">{{ t('preBatch.packageSize') }}</div>
                    <q-input
                    outlined
                    v-model.number="packageSize"
                    dense
                    :bg-color="isPackageSizeLocked ? 'grey-1' : 'white'"
                    input-class="text-right"
                    type="number"
                    step="0.0001"
                    :readonly="isPackageSizeLocked"
                    >
                        <template v-slot:append>
                            <q-btn 
                                :icon="isPackageSizeLocked ? 'lock' : 'lock_open'" 
                                flat 
                                round 
                                dense 
                                :color="isPackageSizeLocked ? 'grey-7' : 'primary'"
                                size="sm" 
                                @click="unlockPackageSize"
                            >
                                <q-tooltip>{{ isPackageSizeLocked ? t('preBatch.unlockToEdit') : t('preBatch.lockField') }}</q-tooltip>
                            </q-btn>
                        </template>
                    </q-input>
                </div>

                <!-- Package (col-md) -->
                <div class="col-12 col-md">
                    <div class="text-subtitle2 q-mb-xs text-no-wrap">{{ t('preBatch.nextPkgNo') }}</div>
                    <q-input
                    outlined
                    :model-value="nextPackageNo"
                    dense
                    bg-color="yellow-1"
                    readonly
                    input-class="text-center text-weight-bold"
                    />
                </div>
                </div>

                <!-- CONTROLS ROW 2 -->
                <div class="row q-col-gutter-md items-end justify-end">
                <!-- Batch Volume Removed -->
                <!-- 
                <div class="col-12 col-md-3">
                    <div class="text-subtitle2 q-mb-xs">Batch Volume (kg)</div>
                    <q-input
                    outlined
                    v-model.number="batchVolume"
                    dense
                    bg-color="grey-2"
                    readonly
                    input-class="text-right"
                    />
                </div>
                -->

                <!-- Request Batch MOVED UP -->

                <!-- Actual Scale Value (Removed) -->
                <!-- 
                <div class="col-12 col-md-2">
                    <div class="text-subtitle2 q-mb-xs">Actual Scale Value</div>
                    <q-input
                    outlined
                    :model-value="actualScaleValue.toFixed(3)"
                    readonly
                    dense
                    :bg-color="isToleranceExceeded ? 'yellow-13' : 'green-13'"
                    input-class="text-center text-weight-bold"
                    />
                </div>
                -->

                <!-- Done Button -->
                <div class="col-12 col-md-2">
                    <q-btn
                    :label="t('prodPlan.done')"
                    color="grey-6"
                    text-color="black"
                    class="full-width q-py-xs"
                    size="md"
                    unelevated
                    @click="onDone"
                    :disable="!selectedIntakeLotId"
                    />
                </div>
                </div>
            </q-card-section>
        </q-card>

        <!-- PreBatch List (Filtered by selected batch) -->
        <q-card bordered flat class="bg-white">
            <q-card-section class="q-py-xs bg-blue-grey-1 text-blue-grey-9 row items-center no-wrap">
                <q-icon name="list_alt" size="xs" class="q-mr-xs" />
                <div class="text-subtitle2 text-weight-bold">{{ t('preBatch.preBatchList') }}</div>
                <q-space />
                
                
                <!-- Delete Confirmation Scanner Input -->
                <q-input 
                    v-if="recordToDelete"
                    v-model="deleteInput"
                    outlined
                    dense
                    placeholder=""
                    @keyup.enter="onDeleteScanEnter"
                    class="q-ml-sm"
                    style="min-width: 250px;"
                >
                    <template v-slot:prepend>
                        <q-icon name="circle" color="positive" />
                    </template>
                </q-input>
            </q-card-section>
            
            <q-card-section class="q-pa-none">
                <q-table
                    :rows="filteredPreBatchLogs"
                    :columns="prebatchColumns"
                    row-key="id"
                    dense
                    flat
                    square
                    separator="cell"
                    :pagination="{ rowsPerPage: 10 }"
                    selection="multiple"
                    v-model:selected="selectedPreBatchLogs"
                    style="max-height: 250px"
                    class="sticky-header-table"
                >
                    <template v-slot:top-right>
                        <q-btn
                            v-if="selectedPreBatchLogs.length > 0"
                            :label="t('preBatch.printPackingBoxLabel')"
                            color="green-7"
                            icon="inventory_2"
                            dense
                            no-caps
                            unelevated
                            class="q-px-sm"
                            @click="showPackingBoxLabelDialog = true"
                        />
                    </template>
                    <template v-slot:body-cell-reprint="props">
                        <q-td :props="props" class="text-center">
                            <q-btn 
                                icon="print" 
                                color="primary" 
                                flat 
                                round 
                                dense 
                                size="sm" 
                                @click.stop="onReprintLabel(props.row)"
                            >
                                <q-tooltip>{{ t('preBatch.reprintLabel') }}</q-tooltip>
                            </q-btn>
                        </q-td>
                    </template>
                    <template v-slot:body-cell-actions="props">
                        <q-td :props="props" class="text-center">
                            <q-btn 
                                icon="delete" 
                                color="negative" 
                                flat 
                                round 
                                dense 
                                size="sm" 
                                @click.stop="onDeleteRecord(props.row)"
                            >
                                <q-tooltip>{{ t('preBatch.cancelReturnInv') }}</q-tooltip>
                            </q-btn>
                        </q-td>
                    </template>
                    <template v-slot:bottom-row>
                        <q-tr class="bg-blue-grey-1 text-weight-bold">
                            <q-td colspan="2" class="text-right text-uppercase text-caption">{{ t('preBatch.summary') }}</q-td>
                            <q-td class="text-center">{{ preBatchSummary.count }} / {{ preBatchSummary.targetCount }}</q-td>
                            <q-td class="text-right">
                                {{ preBatchSummary.totalNetWeight }} / {{ preBatchSummary.targetWeight }}
                                <div class="text-caption" :class="preBatchSummary.errorColor">
                                    {{ t('preBatch.error') }} {{ preBatchSummary.errorVolume }}
                                </div>
                            </q-td>
                            <q-td></q-td>
                        </q-tr>
                    </template>
                    <template v-slot:no-data>
                        <div class="full-width row flex-center q-pa-md text-grey" style="font-size: 0.8rem;">
                            <span v-if="!selectedBatch">{{ t('preBatch.selectBatchRecords') }}</span>
                            <span v-else>{{ t('preBatch.noRecordsForBatch') }}</span>
                        </div>
                    </template>
                </q-table>
            </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Authorization Required Dialog -->
    <q-dialog v-model="showAuthDialog" persistent>
        <q-card style="min-width: 350px">
            <q-card-section class="bg-primary text-white row items-center">
                <div class="text-h6">{{ t('preBatch.authRequired') }}</div>
                <q-space />
                <q-btn icon="close" flat round dense v-close-popup />
            </q-card-section>

            <q-card-section class="q-pa-md">
                <p>{{ t('preBatch.enterPwdUnlock') }}</p>
                <q-input 
                    v-model="authPassword" 
                    type="password" 
                    outlined 
                    dense 
                    :label="t('preBatch.userPassword')" 
                    autofocus
                    @keyup.enter="verifyAuth"
                />
            </q-card-section>

            <q-card-actions align="right" class="q-pa-md">
                <q-btn :label="t('common.cancel')" flat color="grey-7" v-close-popup />
                <q-btn 
                    :label="t('preBatch.verifyUnlock')" 
                    color="primary" 
                    unelevated 
                    @click="verifyAuth" 
                />
            </q-card-actions>
        </q-card>
    </q-dialog>

    <!-- Cancel & Repack Confirmation Dialog -->
    <q-dialog v-model="showDeleteDialog" persistent>
        <q-card style="min-width: 400px; max-width: 500px">
            <q-card-section class="bg-negative text-white row items-center">
                <div class="text-h6">{{ t('preBatch.confirmRepackCancel') }}</div>
                <q-space />
                <q-btn icon="close" flat round dense v-close-popup />
            </q-card-section>

            <q-card-section class="q-pa-md">
                <div v-if="recordToDelete">
                    <p class="text-subtitle1 q-mb-md">
                        To cancel Package #{{ recordToDelete.package_no }}, scan the label or type the package number (<b>{{ recordToDelete.package_no }}</b>) below:
                    </p>
                    <q-input 
                        v-model="deleteInput" 
                        outlined 
                        dense 
                        label="Package Number" 
                        autofocus
                        @keyup.enter="onConfirmDeleteManual"
                    />
                </div>
            </q-card-section>

            <q-card-actions align="right" class="q-pa-md bg-grey-1">
                <!-- Delete Confirmation Scanner Input -->
                <q-input 
                    v-if="recordToDelete"
                    v-model="deleteInput"
                    outlined
                    dense
                    placeholder="Scan label barcode to confirm"
                    @keyup.enter="onDeleteScanEnter"
                    class="q-mr-sm"
                    style="min-width: 250px;"
                >
                    <template v-slot:prepend>
                        <q-icon name="circle" color="positive" />
                    </template>
                </q-input>
                <q-btn :label="t('preBatch.goBack')" flat color="grey-7" v-close-popup />
                <q-btn 
                    :label="t('preBatch.confirmDeletion')" 
                    color="negative" 
                    unelevated 
                    @click="onConfirmDeleteManual" 
                />
            </q-card-actions>
        </q-card>
    </q-dialog>

    <!-- Package Label Dialog -->
    <q-dialog v-model="showLabelDialog" persistent>
      <q-card style="min-width: 650px; max-width: 800px">
        <!-- Dialog Header -->
        <q-card-section class="row items-center q-pb-none bg-grey-3">
          <div class="text-h6 text-weight-bold text-grey-8">{{ t('preBatch.packageLabelPrint') }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup class="bg-grey-5 text-white" />
        </q-card-section>

        <q-separator />

        <q-card-section class="q-pt-md">
          <!-- ID Input Row -->
          <div class="row q-col-gutter-md q-mb-md items-end">
            <div class="col-8">
              <div class="text-subtitle2 q-mb-xs">{{ t('preBatch.packageLabelId') }}</div>
              <div class="row no-wrap">
                <q-input v-model="packageLabelId" outlined dense class="full-width bg-white" />
                <q-btn icon="arrow_drop_down" outline color="grey-7" class="q-ml-sm" />
              </div>
            </div>
            <div class="col-4">
              <q-btn
                :label="t('preBatch.reprint')"
                color="grey-6"
                class="full-width"
                size="md"
                @click="onReprint"
                no-caps
              />
            </div>
          </div>

          <!-- Label Preview Container (Enforced 6x6 Square Ratio) -->
          <div class="row justify-center q-mb-md">
            <div class="label-preview-container q-pa-md shadow-2">
            <!-- Main Label Area -->
            <!-- SVG Production Label Render -->
            <div 
              v-if="labelDataMapping" 
              class="label-svg-preview bg-white q-pa-md shadow-2 flex flex-center"
              v-html="renderedLabel"
            ></div>
            </div>
          </div>

          <!-- Main Print Button -->
          <div class="row justify-end">
            <q-btn
              :label="t('common.print')"
              color="primary"
              class="q-px-xl q-py-sm"
              size="lg"
              unelevated
              @click="onPrintLabel"
              no-caps
            />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- History Monitor Dialog -->
    <q-dialog v-model="showHistoryDialog">
      <q-card style="min-width: 700px">
        <q-card-section class="row items-center q-pb-none bg-blue-1">
          <div class="text-h6 text-blue-9">
            <q-icon name="history" class="q-mr-sm" />
            Inventory History Monitor - {{ selectedHistoryItem?.intake_lot_id }}
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-separator />

        <q-card-section class="q-pa-none">
          <q-markup-table flat bordered square dense separator="cell">
            <thead class="bg-grey-2">
              <tr>
                <th class="text-left">Timestamp</th>
                <th class="text-left">Action</th>
                <th class="text-center">Old Status</th>
                <th class="text-center">New Status</th>
                <th class="text-left">By</th>
                <th class="text-left">Remarks</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(h, idx) in selectedHistoryItem?.history || []" :key="idx">
                <td class="text-caption">{{ h.changed_at ? h.changed_at.replace('T', ' ').split('.')[0] : '-' }}</td>
                <td class="text-weight-bold">{{ h.action }}</td>
                <td class="text-center">
                   <q-badge :color="h.old_status === 'Active' ? 'green' : 'orange'" dense>
                     {{ h.old_status || '-' }}
                   </q-badge>
                </td>
                <td class="text-center">
                   <q-badge :color="h.new_status === 'Active' ? 'green' : 'orange'" dense>
                     {{ h.new_status || '-' }}
                   </q-badge>
                </td>
                <td class="text-caption">{{ h.changed_by }}</td>
                <td class="text-caption">{{ h.remarks || '-' }}</td>
              </tr>
              <tr v-if="!selectedHistoryItem?.history || selectedHistoryItem.history.length === 0">
                <td colspan="6" class="text-center text-grey q-pa-md italic">{{ t('preBatch.noHistoryRecords') }}</td>
              </tr>
            </tbody>
          </q-markup-table>
        </q-card-section>

        <q-card-section class="q-pt-md">
           <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6">
                 <div class="text-caption text-grey">{{ t('preBatch.targetInfo') }}</div>
                 <div class="text-subtitle2">Lot: {{ selectedHistoryItem?.intake_lot_id }}</div>
                 <div class="text-subtitle2">MAT: {{ selectedHistoryItem?.mat_sap_code }}</div>
              </div>
              <div class="col-12 col-md-6">
                 <div class="text-caption text-grey">{{ t('preBatch.currentStatus') }}</div>
                 <q-badge :color="selectedHistoryItem?.status === 'Active' ? 'green' : (selectedHistoryItem?.status === 'Hold' ? 'orange' : 'red')" size="md">
                    {{ selectedHistoryItem?.status }}
                 </q-badge>
              </div>
           </div>
        </q-card-section>

        <q-separator />

        <q-card-actions align="right">
          <q-btn flat :label="t('common.close')" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Ingredient Intake Label Dialog (6x6) -->
    <q-dialog v-model="showIntakeLabelDialog">
      <q-card style="min-width: 650px">
        <q-card-section class="row items-center q-pb-none bg-grey-3 text-black">
          <div class="text-h6 text-weight-bold">{{ t('preBatch.intakeLabelPrint') }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="q-pa-md">
            <!-- Label Selection / Printer Settings -->
            <div class="row q-col-gutter-sm q-mb-md">
                <div class="col-8">
                    <q-select
                        outlined
                        dense
                        :label="t('preBatch.defaultPrinter')"
                        v-model="selectedPrinter"
                        :options="['Zebra-Label-Printer', 'Brother-QL-800', 'Microsoft Print to PDF']"
                        bg-color="white"
                    />
                </div>
                <div class="col-4">
                    <q-btn color="primary" icon="print" :label="t('preBatch.directPrint')" class="full-width" @click="printIntakeLabel" />
                </div>
            </div>

            <!-- 6x6 Preview Area -->
            <div class="row justify-center">
                <div id="intake-label-printable" class="intake-label-6x6 shadow-3">
                    <!-- Top Part -->
                    <div class="intake-header q-pa-sm text-center">
                        <div class="text-h5 text-weight-bolder letter-spacing-2">INGREDIENT INTAKE</div>
                    </div>
                    
                    <div class="q-pa-md col-grow column">
                        <!-- Lot ID Row -->
                        <div class="row items-start q-mb-md">
                            <div class="col">
                                <div class="text-caption text-weight-bold text-grey-7">INTAKE LOT ID</div>
                                <div class="text-h6 text-weight-bolder text-mono line-height-1">{{ intakeLabelData?.intake_lot_id }}</div>
                            </div>
                            <div class="col-auto">
                                <q-icon name="qr_code_2" size="80px" />
                            </div>
                        </div>

                        <!-- Ingredient Code Row -->
                        <div class="q-mb-md">
                            <div class="text-caption text-weight-bold text-grey-7">INGREDIENT CODE</div>
                            <div class="text-h3 text-weight-bolder">{{ intakeLabelData?.re_code }}</div>
                            <div class="text-subtitle1 text-grey-8">{{ intakeLabelData?.mat_sap_code }}</div>
                        </div>

                        <!-- Volume and Package Row -->
                        <div class="row q-col-gutter-lg q-mb-md">
                            <div class="col">
                                <div class="text-caption text-weight-bold text-grey-7">INTAKE VOL</div>
                                <div class="text-h4 text-weight-bolder">{{ (intakeLabelData?.intake_vol ?? 0).toFixed(2) }} <span class="text-h6">kg</span></div>
                            </div>
                            <div class="col-auto text-right">
                                <div class="text-caption text-weight-bold text-grey-7">PACKAGE</div>
                                <div class="text-h4 text-weight-bolder">1 / {{ intakeLabelData?.package_intake }}</div>
                            </div>
                        </div>

                        <!-- Dates Row -->
                        <div class="row q-col-gutter-md">
                            <div class="col-6">
                                <div class="text-caption text-weight-bold text-grey-7 uppercase">Expire Date</div>
                                <div class="text-h6 text-weight-bold">{{ intakeLabelData?.expire_date?.split('T')[0] }}</div>
                            </div>
                            <div class="col-6">
                                <div class="text-caption text-weight-bold text-grey-7 uppercase">Supplier Lot</div>
                                <div class="text-subtitle1 text-weight-bold word-break-all">{{ intakeLabelData?.lot_id }}</div>
                            </div>
                        </div>
                    </div>

                    <!-- Dashed Line -->
                    <div class="q-px-md">
                        <div style="border-top: 2px dashed #333; height: 1px; width: 100%;"></div>
                    </div>

                    <!-- Sub Label (Bottom) -->
                    <div class="q-pa-md row items-center">
                        <div class="col-8">
                             <div class="text-caption text-weight-bold text-grey-7 uppercase" style="font-size: 0.6rem;">INTAKE LOT ID</div>
                             <div class="text-subtitle2 text-weight-bold q-mb-xs">{{ intakeLabelData?.intake_lot_id }}</div>
                             
                             <div class="row">
                                <div class="col-6">
                                    <div class="text-caption uppercase text-grey-8" style="font-size: 0.65rem;">Material</div>
                                    <div class="text-subtitle2 text-weight-bold">{{ intakeLabelData?.re_code }}</div>
                                    <div class="text-caption text-grey-7" style="font-size: 0.6rem;">{{ intakeLabelData?.mat_sap_code }}</div>
                                </div>
                                <div class="col-6">
                                    <div class="text-caption uppercase text-grey-8" style="font-size: 0.65rem;">Weight</div>
                                    <div class="text-subtitle2 text-weight-bold">{{ (intakeLabelData?.intake_vol ?? 0).toFixed(2) }} kg</div>
                                    <div class="text-caption text-grey-7" style="font-size: 0.6rem;">1 / {{ intakeLabelData?.package_intake }}</div>
                                </div>
                             </div>
                        </div>
                        <div class="col-4 flex flex-center">
                            <q-icon name="qr_code_2" size="60px" />
                        </div>
                    </div>
                </div>
            </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Packing Box Label Dialog -->
    <q-dialog v-model="showPackingBoxLabelDialog" persistent>
      <q-card style="min-width: 650px; max-width: 800px">
        <q-card-section class="row items-center q-pb-none bg-green-1 text-green-9">
          <div class="text-h6 text-weight-bold">{{ t('preBatch.packingBoxPreview') }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="q-pa-md">
          <div class="row justify-center q-mb-md">
            <div class="label-preview-container q-pa-md shadow-2">
              <div 
                v-if="packingBoxLabelDataMapping" 
                class="label-svg-preview bg-white q-pa-md flex flex-center"
                v-html="renderedPackingBoxLabel"
              ></div>
            </div>
          </div>

          <div class="row justify-end q-gutter-sm">
            <q-btn :label="t('common.cancel')" flat color="grey-7" v-close-popup />
            <q-btn
              :label="t('preBatch.printPackingBoxLabel')"
              color="green-7"
              class="q-px-xl"
              size="lg"
              unelevated
              @click="onPrintPackingBoxLabel"
              no-caps
            />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

  </q-page>
</template>

<style scoped>
.batch-list-container {
  border: 1px solid #ccc;
  border-radius: 4px;
  height: 400px; /* Example height to make it look like a panel */
  overflow-y: auto;
  background: #f8f9fa;
}

.ingredient-list-container {
  border: 1px solid #ccc;
  border-radius: 4px;
  height: 300px; /* Slightly shorter than batch list or adjust as needed */
  overflow-y: auto;
  background: #f8f9fa;
}

.scale-card-border {
  border: 1px solid #000;
  border-radius: 8px;
}

.status-indicator {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid white;
}

.status-indicator:hover {
  transform: scale(1.1);
}

.prebatch-list-container {
  border: 1px solid #777;
  border-radius: 4px;
  height: 250px;
  overflow-y: auto;
  background: #fff;
  font-family: monospace; /* Log style font */
  font-size: 13px;
}

/* Custom styling to match radio button size in image roughly (if needed) */
:deep(.q-radio__inner) {
  font-size: 24px;
}

/* Override input styles to match specific visual cues from image */
:deep(.focused-border-blue .q-field__control) {
  border-color: #1976d2 !important;
  border-width: 2px;
}

/* Label Dialog Styles */
.label-preview-container {
  border: 4px solid #1d3557; /* Dark border */
  border-radius: 8px;
  background-color: #ffffff;
  width: 550px;
  height: 550px;
  display: flex;
  flex-direction: column;
}
.main-label-area {
  flex-grow: 1;
}
/* Active Scale Highlighting */
.active-scale-border {
  border: 5px solid #4caf50 !important; /* Green */
  border-radius: 8px;
}
.border-left {
  border-left: 1px solid #e0e0e0;
}
.text-mono {
  font-family: 'Courier New', Courier, monospace;
}
.letter-spacing-2 {
  letter-spacing: 2px;
}
.line-height-1 {
  line-height: 1;
}
.word-break-all {
  word-break: break-all;
}

.label-svg-preview {
  width: 100%;
  max-width: 400px;
  min-height: 400px;
  border-radius: 8px;
  overflow: hidden;
}

.label-svg-preview :deep(svg) {
  width: 100%;
  height: auto;
}

/* Print Specifics */
@media print {
  body * {
    visibility: hidden;
  }
  #intake-label-printable, #intake-label-printable * {
    visibility: visible;
  }
  #intake-label-printable {
    position: fixed;
    left: 0;
    top: 0;
    width: 6cm;
    height: 6cm;
    border: none;
    margin: 0;
    padding: 0;
  }
  @page {
    size: 6cm 6cm;
    margin: 0;
  }
}

/* Sticky Header Table */
.sticky-header-table {
  height: 250px;
}
.sticky-header-table thead tr th {
  position: sticky;
  z-index: 1;
}
.sticky-header-table thead tr:first-child th {
  top: 0;
  background-color: #f5f5f5;
}

@keyframes pulse-orange {
  0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(230, 81, 0, 0.4); }
  70% { transform: scale(1.05); box-shadow: 0 0 0 10px rgba(230, 81, 0, 0); }
  100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(230, 81, 0, 0); }
}
.anim-pulse {
  animation: pulse-orange 1.5s infinite;
}
@keyframes blink-red {
  0% { background-color: #ef5350; }
  50% { background-color: #b71c1c; }
  100% { background-color: #ef5350; }
}
.bg-red-blink {
  animation: blink-red 1s infinite;
}

/* Stable Indicator Styles */
.stable-spot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid white;
  transition: all 0.2s ease;
}

@keyframes vibrate {
  0% { transform: translate(0); }
  20% { transform: translate(-2px, 2px); }
  40% { transform: translate(-2px, -2px); }
  60% { transform: translate(2px, 2px); }
  80% { transform: translate(2px, -2px); }
  100% { transform: translate(0); }
}
.anim-vibrate {
  animation: vibrate 0.2s linear infinite;
}
</style>

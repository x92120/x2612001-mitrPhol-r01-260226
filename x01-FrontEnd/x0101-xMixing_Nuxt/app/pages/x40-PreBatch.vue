<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'

import { appConfig } from '../appConfig/config'
import { useAuth } from '../composables/useAuth'

const $q = useQuasar()
const { getAuthHeader } = useAuth()

// --- State ---
const selectedProductionPlan = ref('')
const selectedReCode = ref('')
const selectedScale = ref(0) // Default to 0 (none selected)
const selectedBatchIndex = ref(0) // Default first one selected

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
const skuSteps = ref<any[]>([])
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
    // Keeping this generic fetch if needed, but main logic will shift to filtered ingredients by Plan
    // ...
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
    
    // Auto-select first plan if available
    if (productionPlanOptions.value.length > 0 && !selectedProductionPlan.value) {
      selectedProductionPlan.value = productionPlanOptions.value[0] || ''
    }
  } catch (error) {
    console.error('Error fetching production plans:', error)
    $q.notify({
      type: 'negative',
      message: 'Error loading production plans',
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
    
    // 2. Fetch SKU Steps to get relevant Ingredients
    if (plan.sku_id) {
       // Pass plan.batch_size (or default to 0) to calculate required weights
       // Updated: No longer passing plan.batch_size, as it is handled by computed property
       await fetchSkuStepsForPlan(plan.sku_id)
    }

    // Reset selection if current index is out of bounds
    if (selectedBatchIndex.value >= filteredBatches.value.length) {
      selectedBatchIndex.value = 0
    }
    
    // Update require volume based on selected batch
    updateRequireVolume()
  }
}

// State for tracking if a specific batch is selected versus just the plan
const isBatchSelected = ref(false)

// Computed ingredients list based on selected Batch (or Plan)
const selectableIngredients = computed(() => {
    if (!skuSteps.value || skuSteps.value.length === 0) return []

    // Determine target sizes for calculation
    const planTotalSize = selectedPlanDetails.value?.total_volume || 0
    const batchSize = (isBatchSelected.value && selectedBatch.value) 
        ? (selectedBatch.value.batch_size || 0) 
        : (selectedPlanDetails.value?.batch_size || 0)

    console.log(`Calculating Ingredients. Batch: ${batchSize}, Plan: ${planTotalSize}`)

    const uniqueMap = new Map()
    let counter = 1
    const invList = inventoryRows.value || []

    skuSteps.value.forEach((step: any) => {
        if (step.re_code) {
             if (!uniqueMap.has(step.re_code)) {
                // Try to find inventory source default location
                const stock = invList.find((r: any) => r.re_code === step.re_code)
                const warehouse = stock ? (stock.warehouse_location || '').toUpperCase() : '-'
                
                uniqueMap.set(step.re_code, {
                    index: counter++,
                    re_code: step.re_code,
                    ingredient_name: step.ingredient_name || step.re_code,
                    std_package_size: step.std_package_size || 0,
                    batch_require: 0,
                    total_require: 0,
                    from_warehouse: stock ? stock.warehouse_location : '-',
                    isDisabled: !(warehouse === 'SPP' || warehouse === 'FH'),
                    isDone: false 
                })
            }
            
            const entry = uniqueMap.get(step.re_code)
            
            // Calculate step requirement for one batch
            let batchStepReq = parseFloat(step.require) || 0
            if (batchSize > 0 && step.std_batch_size > 0) {
                batchStepReq = (batchStepReq / step.std_batch_size) * batchSize
            }
            
            // Calculate step requirement for total plan
            let totalStepReq = parseFloat(step.require) || 0
            if (planTotalSize > 0 && step.std_batch_size > 0) {
                totalStepReq = (totalStepReq / step.std_batch_size) * planTotalSize
            }
            
            entry.batch_require += batchStepReq
            entry.total_require += totalStepReq
        }
    })
    
    return Array.from(uniqueMap.values())
})

const getIngredientRowClass = (ing: any) => {
    if (ing.isDisabled) return 'bg-grey-3 text-grey-5 cursor-not-allowed'
    if (selectedReCode.value === ing.re_code) return 'bg-orange-2 text-deep-orange-9 text-weight-bold cursor-pointer'
    return 'hover-bg-grey-1 cursor-pointer'
}

// Fetch Steps for the selected Plan's SKU
const fetchSkuStepsForPlan = async (skuId: string) => {
    try {
        const steps = await $fetch<any[]>(`${appConfig.apiBaseUrl}/api/v_sku_step_detail?sku_id=${skuId}`, {
            headers: getAuthHeader() as Record<string, string>
        })
        skuSteps.value = steps
    } catch (e) {
        console.error('Error fetching SKU steps for ingredients', e)
        skuSteps.value = []
    }
}

// Watcher to handle selection reset if ingredient disappears
watch(selectableIngredients, (newList) => {
    if (selectedReCode.value && !newList.some(i => i.re_code === selectedReCode.value)) {
        selectedReCode.value = ''
    }
})


// Update require volume when batch is selected
// NOTE: User requested Request Volume to stay 0 until ingredient is selected/double-clicked.
// So we no longer auto-populate from batch size here.
const onSelectIngredient = (ing: any) => {
    if (ing.isDisabled) return
    selectedReCode.value = ing.re_code
    updateRequireVolume()
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

// --- MQTT Configuration ---
import { useMQTT } from '~/composables/useMQTT'

// Use shared MQTT composable
const { 
  connect: connectMQTT, 
  disconnect: disconnectMQTT, 
  mqttClient, 
  isConnected: isBrokerConnected 
} = useMQTT()


// Init scales with connection state and topic
const scales = ref([
  {
    id: 1,
    label: 'Scale 1 (10 Kg +/- 0.01)',
    value: 0.0,
    displayValue: '0.000',
    targetScaleId: 'scale-01',
    connected: false,
    tolerance: 0.01,
  },
  {
    id: 2,
    label: 'Scale 2 (30 Kg +/- 0.02)',
    value: 0.0,
    displayValue: '0.000',
    targetScaleId: 'scale-02',
    connected: false,
    tolerance: 0.02,
  },
  {
    id: 3,
    label: 'Scale 3 (150 Kg +/- 0.5)',
    value: 0.0,
    displayValue: '0.000',
    targetScaleId: 'scale-03',
    connected: false,
    tolerance: 0.5,
  },
])

// Single shared topic
const TOPIC_SCALE = 'scale'

// Handle incoming messages
const handleMqttMessage = (topic: string, message: any) => {
  // Only process if it matches our shared topic
  if (topic !== TOPIC_SCALE) return

  try {
    const msgStr = message.toString()
    const data = JSON.parse(msgStr)

    // Check payload for scale_id
    if (data && data.scale_id && data.weight !== undefined) {
      // Find matching scale by ID
      const scale = scales.value.find(s => s.targetScaleId === data.scale_id && s.connected)
      
      if (scale) {
        const val = parseFloat(data.weight)
        if (!isNaN(val)) {
          scale.value = val
          scale.displayValue = val.toFixed(3)
        }
      }
    }
  } catch (e) {
    console.warn('Failed to parse scale message', e)
  }
}

// Watch for client initialization to attach listeners
watch(mqttClient, (client) => {
  if (client) {
    // Remove any existing listener to be safe (though this is a new client usually)
    client.removeListener('message', handleMqttMessage)
    client.on('message', handleMqttMessage)
  }
})

// Watch for broker connection to Auto-Subscribe
watch(isBrokerConnected, (connected) => {
  if (connected && mqttClient.value) {
    console.log('Broker connected - Auto-subscribing scales')
    // Reset subscriptions based on desired state
    refreshSubscription()
    
    // Auto-connect all scales visually if they were default
    scales.value.forEach(s => s.connected = true)
    refreshSubscription()
  }
})

const refreshSubscription = () => {
  if (!mqttClient.value || !isBrokerConnected.value) return

  const anyConnected = scales.value.some(s => s.connected)
  
  if (anyConnected) {
    mqttClient.value.subscribe(TOPIC_SCALE, (err?: any) => {
      if (err) console.error('Sub error', err)
      else console.log('Subscribed to', TOPIC_SCALE)
    })
  } else {
    mqttClient.value.unsubscribe(TOPIC_SCALE, (err?: any) => { 
        if (!err) console.log('Unsubscribed', TOPIC_SCALE)
    })
  }
}

const toggleScaleConnection = (scaleId: number) => {
  const scale = scales.value.find((s) => s.id === scaleId)
  if (!scale) return

  if (!isBrokerConnected.value) {
    $q.notify({ type: 'warning', message: 'Broker connecting... please wait', timeout: 1000 })
    return
  }

  // Toggle visual state
  scale.connected = !scale.connected
  
  // Update subscription
  refreshSubscription()

  $q.notify({
    type: scale.connected ? 'positive' : 'info',
    message: scale.connected ? `Connected ${scale.label}` : `Disconnected ${scale.label}`,
    position: 'top',
    timeout: 500
  })
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
  // Connect to shared broker
  connectMQTT()
  fetchIngredients()
  fetchProductionPlans()
  fetchBatchIds()
  fetchInventory()
  fetchPreBatchRecords()
})

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

const inventoryColumns: QTableColumn[] = [
    { name: 'id', align: 'center', label: 'ID', field: 'id', sortable: true },
    { name: 'intake_lot_id', align: 'left', label: 'Intake Lot ID', field: 'intake_lot_id', sortable: true },
    { name: 'warehouse_location', align: 'center', label: 'From Warehouse', field: 'warehouse_location' },
    { name: 'lot_id', align: 'left', label: 'Lot ID', field: 'lot_id' },
    { name: 'mat_sap_code', align: 'left', label: 'MAT.SAP Code', field: 'mat_sap_code' },
    { name: 're_code', align: 'center', label: 'Re-Code', field: 're_code' },
    { name: 'material_description', align: 'left', label: 'Description', field: 'material_description' },
    { name: 'uom', align: 'center', label: 'UOM', field: 'uom' },
    { name: 'intake_vol', align: 'right', label: 'Intake Vol (kg)', field: 'intake_vol' },
    { name: 'remain_vol', align: 'right', label: 'Remain Vol (kg)', field: 'remain_vol', classes: 'text-red text-weight-bold' },
    { name: 'intake_package_vol', align: 'right', label: 'Pkg Vol', field: 'intake_package_vol' },
    { name: 'package_intake', align: 'center', label: 'Pkgs', field: 'package_intake' },
    { name: 'expire_date', align: 'center', label: 'Expire Date', field: 'expire_date', format: (val: any) => val ? val.split('T')[0] : '' },
    { name: 'po_number', align: 'left', label: 'PO No.', field: 'po_number' },
    { name: 'manufacturing_date', align: 'center', label: 'Mfg Date', field: 'manufacturing_date', format: (val: any) => val ? val.split('T')[0] : '' },
    { name: 'status', align: 'center', label: 'Status', field: 'status' },
    { name: 'actions', align: 'center', label: 'Actions', field: 'id' }
]

const filteredInventory = computed(() => {
    // If no ingredient selected, maybe show empty?
    if (!selectedReCode.value) return []
    // Filter by re_code and sort by expire_date (FIFO/FEFO)
    return inventoryRows.value
        .filter(item => {
            // Simple case-insensitive match just in case
            return (item.re_code || '').trim().toUpperCase() === selectedReCode.value.trim().toUpperCase() &&
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
})

// Watch for batch selection changes
watch(selectedBatchIndex, () => {
  updateRequireVolume()
})

onUnmounted(() => {
  disconnectMQTT()
})

// Control Fields
const requireVolume = ref(0)
const packageSize = ref(0)
// const batchVolume = ref(0) // Removed per user request
const currentPackage = ref('0/0')
const targetWeight = ref(0) // The target weight for the current package
const requestBatch = computed(() => {
    if (packageSize.value <= 0) return 0
    return Math.ceil(requireVolume.value / packageSize.value)
})

const labelData = computed(() => {
  if (!selectedBatch.value || !selectedReCode.value) return null
  
  const ing = selectableIngredients.value.find(i => i.re_code === selectedReCode.value)
  const parts = currentPackage.value.split('/')
  const pkgNo = parts[0]?.trim() || '0'
  const totalPkgs = parts[1]?.trim() || '0'
  
  return {
    sku_id: selectedBatch.value.sku_id || '-',
    sku_name: selectedBatch.value.sku_name || selectedBatch.value.sku_id || '-',
    base_quantity: selectedBatch.value.batch_size || 0,
    item_number: ing?.index || '-',
    re_code: selectedReCode.value,
    ingredient_name: ing?.ingredient_name || '-',
    order_code: selectedBatch.value.plan_id || '-',
    batch_id: selectedBatch.value.batch_id || '-',
    net_volume: capturedScaleValue.value.toFixed(3),
    total_volume: requireVolume.value.toFixed(3),
    package_no: pkgNo,
    total_packages: totalPkgs
  }
})
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
    if (!selectedBatch.value) return []
    return preBatchLogs.value.filter(log => log.batch_record_id.startsWith(selectedBatch.value.batch_id))
})

// Check if out of tolerance
const isToleranceExceeded = computed(() => {
  if (!activeScale.value) return false
  const diff = Math.abs(targetWeight.value - actualScaleValue.value)
  return diff > activeScale.value.tolerance
})

// PreBatch Records from database
const preBatchLogs = ref<any[]>([])

const fetchPreBatchRecords = async () => {
  if (!selectedProductionPlan.value) return
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-records/by-plan/${selectedProductionPlan.value}`, {
      headers: getAuthHeader() as Record<string, string>
    })
    preBatchLogs.value = data
  } catch (error) {
    console.error('Error fetching prebatch records:', error)
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
                    message: `Auto-selected (FIFO): ${firstItem.intake_lot_id}`,
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
                message: `No inventory available for ${selectedReCode.value}`,
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
        
        // Reset and recalculate batching fields
        if (requireVolume.value > 0 && packageSize.value > 0) {
             const numPackages = Math.ceil(requireVolume.value / packageSize.value)
             
             // batchVolume.value = packageSize.value 
             
             // Reset Current Package to 1 / Total
             currentPackage.value = `1 / ${numPackages}`
             
             // Set Request Batch to the first package amount
             // If Total < PackageSize, then Request = Total
             // Else Request = PackageSize
             targetWeight.value = Math.min(requireVolume.value, packageSize.value)
        } else {
            // Fallback reset
            // batchVolume.value = 0
            currentPackage.value = ''
            targetWeight.value = 0
        }
        
        $q.notify({
            type: 'positive',
            message: `Initialized batching for ${ingredient.re_code}`,
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
        $q.notify({ type: 'positive', message: 'Batch preparation finalized', position: 'top' })
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
const showLabelDialog = ref(false)
const packageLabelId = ref('')

const capturedScaleValue = ref(0)
const openLabelDialog = () => {
  capturedScaleValue.value = actualScaleValue.value
  packageLabelId.value = ''
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
    const parts = currentPackage.value.split('/')
    if (parts.length < 2) {
        throw new Error('Invalid package format')
    }
    const pkgNo = parseInt(parts[0]?.trim() || '0')
    const totalPkgs = parseInt(parts[1]?.trim() || '0')
    
    if (isNaN(pkgNo) || isNaN(totalPkgs)) {
        throw new Error('Invalid package numbers')
    }

    // Construct Prebatch Record data
    const recordData = {
      batch_record_id: `${selectedBatch.value.batch_id}-${selectedReCode.value}-${pkgNo}`,
      plan_id: selectedProductionPlan.value,
      re_code: selectedReCode.value,
      package_no: pkgNo,
      total_packages: totalPkgs,
      net_volume: capturedScaleValue.value,
      total_volume: requireVolume.value, // This is the total required for this ingredient in this batch
      total_request_volume: targetWeight.value
    }

    await $fetch(`${appConfig.apiBaseUrl}/prebatch-records/`, {
      method: 'POST',
      body: recordData,
      headers: getAuthHeader() as Record<string, string>
    })

    $q.notify({ type: 'positive', message: 'Prebatch Record saved and Label Printed', position: 'top' })
    
    // Refresh prebatch logs
    await fetchPreBatchRecords()
    
    // Move to next package if available
    if (pkgNo < totalPkgs) {
        currentPackage.value = `${pkgNo + 1} / ${totalPkgs}`
        // Recalculate remain and request batch if needed
        const nextReq = Math.min(requireVolume.value - (pkgNo * packageSize.value), packageSize.value)
        targetWeight.value = Math.max(0, Number(nextReq.toFixed(3)))
    } else {
        $q.notify({ type: 'info', message: 'All packages for this ingredient completed' })
        // Update ingredient status in list
        const ing = selectableIngredients.value.find(i => i.re_code === selectedReCode.value)
        if (ing) ing.isDone = true
    }

    showLabelDialog.value = false
  } catch (error) {
    console.error('Error saving prebatch record:', error)
    $q.notify({ type: 'negative', message: 'Failed to save record' })
  }
}

const onDone = () => {
  // Open the dialog instead of just notifying
  openLabelDialog()
}

const onSelectBatch = (index: number) => {
  selectedBatchIndex.value = index
}
</script>

<template>
  <q-page class="q-pa-md bg-white">
    <div class="row q-mb-sm justify-between items-center">
      <div class="text-h6">Pre-Batch</div>
      <div class="text-caption">Version 0.1</div>
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
                          @show="selectedProductionPlan = plan.plan_id; isBatchSelected = false"
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
                                 @click.stop="selectedProductionPlan = plan.plan_id; selectedBatchIndex = Number(idx); isBatchSelected = true"
                                 style="padding-left: 32px; min-height: 32px;"
                              >
                                 <q-item-section>
                                   <q-item-label>{{ batch.batch_id }}</q-item-label>
                                   <q-item-label caption style="font-size: 0.7rem;">Batch Size: {{ batch.batch_size }} kg</q-item-label>
                                 </q-item-section>
                                 <q-item-section side>
                                     <q-badge color="green" :label="batch.status" size="sm" />
                                 </q-item-section>
                              </q-item>
                              <q-item v-if="!plan.batches || plan.batches.length === 0" style="min-height: 32px;">
                                  <q-item-section class="text-grey text-italic q-pl-lg" style="font-size: 0.7rem;">No Batches Created</q-item-section>
                              </q-item>
                           </q-list>
                        </q-expansion-item>
                      </q-expansion-item>
                      
                      <div v-if="structuredSkuList.length === 0" class="text-center q-pa-md text-grey">
                          No Active SKUs/Plans Found
                      </div>
                   </q-list>
                </q-scroll-area>
            </div>
        </q-card>

        <!-- CARD 2: Ingredients for Selected Plan -->
        <q-card class="col-auto bg-white shadow-2 column" style="max-height: 400px;">
            <template v-if="selectedProductionPlan">
              <q-card-section class="bg-orange-8 text-white q-py-xs shadow-1">
                  <div class="row items-center justify-between no-wrap">
                      <div class="text-subtitle2 text-weight-bold ellipsis" style="max-width: 60%;">
                          {{ selectedPlanDetails?.sku_id || 'Unknown SKU' }}
                      </div>
                      <q-badge color="white" text-color="orange-9" class="text-weight-bold">
                          {{ selectableIngredients.length }} Item{{ selectableIngredients.length !== 1 ? 's' : '' }}
                      </q-badge>
                  </div>
                  <div class="text-caption text-orange-2" style="font-size: 0.7rem;">
                      Plan: {{ selectedProductionPlan }} <span v-if="isBatchSelected">(Batch: {{ selectedBatch?.batch_id.slice(-3) }})</span>
                  </div>
              </q-card-section>
            </template>
            <template v-else>
               <q-card-section class="bg-grey-3 text-grey-8 q-py-xs text-center">
                   <div class="text-caption">Select a Plan above</div>
               </q-card-section>
            </template>
            <div class="col relative-position" style="overflow-y: auto;">
                <q-markup-table dense flat square separator="cell" sticky-header>
                    <thead class="bg-orange-1 text-orange-10">
                        <tr>
                            <th class="text-left" style="font-size: 0.7rem;">Ingredient</th>
                            <th class="text-center" style="font-size: 0.7rem;">WH</th>
                            <th class="text-right" style="font-size: 0.7rem;">Batch Req (kg)</th>
                            <th class="text-right" style="font-size: 0.7rem;">Total Plan Req (kg)</th>
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
                            <td class="text-weight-bold" style="font-size: 0.75rem;">{{ ing.re_code }}</td>
                            <td class="text-center text-caption" style="font-size: 0.7rem;">{{ ing.from_warehouse }}</td>
                            <td class="text-right text-weight-bold" style="font-size: 0.75rem;">{{ ing.batch_require ? ing.batch_require.toFixed(3) : '0' }}</td>
                            <td class="text-right text-weight-bold" style="font-size: 0.75rem;">{{ ing.total_require ? ing.total_require.toFixed(3) : '0' }}</td>
                        </tr>
                        <tr v-if="selectableIngredients.length === 0">
                            <td colspan="4" class="text-center text-grey q-pa-md">
                                <div v-if="selectedProductionPlan">No Ingredients Found</div>
                                <div v-else>Select a Plan to view ingredients</div>
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
          <q-card-section class="q-pb-none">
            <div class="text-h6">Weighting Scale</div>
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

                  <!-- Digital Display and Tare Row -->
                  <div class="row q-col-gutter-sm q-mb-md">
                    <div class="col">
                      <div
                        class="text-right q-pa-sm text-h3 text-weight-bold rounded-borders flex items-center justify-end full-height"
                        :class="getDisplayClass(scale)"
                      >
                        {{ scale.displayValue }}
                      </div>
                    </div>
                    <div class="col-auto">
                       <q-btn
                          label="Tare"
                          color="grey-6"
                          text-color="black"
                          unelevated
                          class="text-weight-bold full-height"
                          style="font-size: 1.2rem;"
                          @click="onTare(scale.id)"
                        />
                    </div>
                  </div>
                </q-card>
              </div>
            </div>
          </q-card-section>
        </q-card>

        <q-card bordered flat class="q-mb-md">
            <q-card-section class="q-pb-none row items-center">
              <div class="text-h6">On Hand Inventory</div>
              <q-space />
              <q-btn flat round dense icon="refresh" color="primary" @click="fetchInventory" class="q-mr-sm">
                  <q-tooltip>Refresh Inventory</q-tooltip>
              </q-btn>
              <q-checkbox v-model="showAllInventory" label="Show All (including Hold/Inactive)" dense class="text-caption" />
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
                                <q-tooltip>Print Intake Label</q-tooltip>
                            </q-btn>
                            <q-btn 
                                round dense flat size="sm" 
                                color="blue" icon="history" 
                                @click.stop="onViewHistory(props.row)"
                            >
                                <q-tooltip>View History (Monitor Only)</q-tooltip>
                            </q-btn>
                            <q-btn 
                                round dense flat size="sm" 
                                color="yellow-9" icon="settings" 
                                @click.stop="onViewHistory(props.row)"
                            >
                                <q-tooltip>Inventory Settings & History</q-tooltip>
                            </q-btn>
                        </div>
                    </q-td>
                </template>

                <!-- Summary Row -->
                <template v-slot:bottom-row>
                    <q-tr class="bg-grey-2 text-weight-bold">
                        <q-td colspan="9" class="text-right">Total:</q-td>
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
                        <div class="text-h6">Package Batching Prepare for:</div>
                    </div>
                    
                    <!-- Batch Planning ID -->
                    <div class="col-12 col-md-4">
                        <q-input
                        outlined
                        :model-value="selectedBatch ? selectedBatch.batch_id : ''"
                        dense
                        bg-color="grey-2"
                        readonly
                        placeholder="Batch Planning ID"
                        />
                    </div>

                    <!-- From Label -->
                    <div class="col-auto">
                        <div class="text-h6">From</div>
                    </div>

                    <!-- Selected Intake Lot ID -->
                    <div class="col-12 col-md-4">
                        <q-input
                        outlined
                        v-model="selectedIntakeLotId"
                        dense
                        bg-color="white"
                        placeholder="Scan Intake Lot ID"
                        clearable
                        >
                          <template v-slot:append>
                            <q-btn round dense flat icon="qr_code_scanner" @click="simulateScan">
                                 <q-tooltip>Simulate Scan (FIFO)</q-tooltip>
                            </q-btn>
                          </template>
                        </q-input>
                    </div>
                </div>
            </q-card-section>

            <q-card-section>
                <!-- CONTROLS ROW 1 -->
                <div class="row q-col-gutter-md q-mb-md">

                <!-- Request Volume (col-2) -->
                <div class="col-12 col-md-2">
                    <div class="text-subtitle2 q-mb-xs">Request Volume</div>
                    <q-input
                    outlined
                    :model-value="requireVolume.toFixed(3)"
                    dense
                    bg-color="grey-2"
                    readonly
                    input-class="text-right"
                    />
                </div>

                <!-- Packaged Volume (col-2) -->
                <div class="col-12 col-md-2">
                    <div class="text-subtitle2 q-mb-xs">Packaged Volume</div>
                    <q-input
                    outlined
                    :model-value="batchedVolume.toFixed(3)"
                    dense
                    bg-color="grey-2"
                    readonly
                    input-class="text-right"
                    />
                </div>

                <!-- Remain Volume (col-2) -->
                <div class="col-12 col-md-2">
                    <div class="text-subtitle2 q-mb-xs">Remain Volume</div>
                    <q-input
                    outlined
                    :model-value="remainVolume.toFixed(3)"
                    dense
                    bg-color="grey-2"
                    readonly
                    input-class="text-right"
                    />
                </div>
                
                <!-- Package Size (col-2) -->
                <div class="col-12 col-md-2">
                    <div class="text-subtitle2 q-mb-xs">Package Size (kg)</div>
                    <q-input
                    outlined
                    v-model.number="packageSize"
                    dense
                    bg-color="white"
                    input-class="text-right"
                    type="number"
                    />
                </div>

                <!-- Request Batch (Count) -->
                <div class="col-12 col-md-2">
                    <div class="text-subtitle2 q-mb-xs">Request Batch</div>
                    <q-input :model-value="requestBatch" outlined readonly dense bg-color="yellow-1" input-class="text-center text-weight-bold" />
                </div>



                <!-- Package (col-2) -->
                <div class="col-12 col-md-2">
                    <div class="text-subtitle2 q-mb-xs">Package</div>
                    <q-input
                    outlined
                    v-model="currentPackage"
                    dense
                    bg-color="white"
                    class="focused-border-blue"
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
                    label="Done"
                    color="grey-6"
                    text-color="black"
                    class="full-width q-py-xs"
                    size="md"
                    unelevated
                    @click="onDone"
                    />
                </div>
                </div>
            </q-card-section>
        </q-card>

        <!-- PreBatch List (Filtered by selected batch) -->
        <div>
          <div class="text-subtitle2 q-mb-xs">PreBatch-List (Current Batch)</div>
          <div class="prebatch-list-container q-pa-sm">
            <div v-if="!selectedBatch" class="text-grey-6 text-center q-pa-md">Select a batch to see records</div>
            <div v-else-if="filteredPreBatchLogs.length === 0" class="text-grey-6 text-center q-pa-md">No records for this batch</div>
            <div v-for="(record, idx) in filteredPreBatchLogs" :key="idx" class="text-blue-8 q-mb-xs">
              {{ record.batch_record_id }} - {{ record.package_no }}/{{ record.total_packages }} - {{ record.net_volume }}/{{ record.total_volume }}/{{ record.total_request_volume }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Package Label Dialog -->
    <q-dialog v-model="showLabelDialog" persistent>
      <q-card style="min-width: 650px; max-width: 800px">
        <!-- Dialog Header -->
        <q-card-section class="row items-center q-pb-none bg-grey-3">
          <div class="text-h6 text-weight-bold text-grey-8">Package Label Print</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup class="bg-grey-5 text-white" />
        </q-card-section>

        <q-separator />

        <q-card-section class="q-pt-md">
          <!-- ID Input Row -->
          <div class="row q-col-gutter-md q-mb-md items-end">
            <div class="col-8">
              <div class="text-subtitle2 q-mb-xs">Package Label ID</div>
              <div class="row no-wrap">
                <q-input v-model="packageLabelId" outlined dense class="full-width bg-white" />
                <q-btn icon="arrow_drop_down" outline color="grey-7" class="q-ml-sm" />
              </div>
            </div>
            <div class="col-4">
              <q-btn
                label="Reprint"
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
            <div class="main-label-area q-pa-sm row">
              <!-- Text Details -->
              <div class="col-7 text-body2 q-pr-sm" style="line-height: 1.4">
                <div class="row q-mb-xs">
                  <div class="col-5 text-weight-light">SKU Name</div>
                  <div class="col-7 text-weight-bolder text-uppercase">{{ labelData?.sku_id }}</div>
                </div>
                <div class="row q-mb-xs">
                  <div class="col-5 text-weight-light">Base Quantity</div>
                  <div class="col-7 text-weight-bolder">{{ labelData?.base_quantity }} kg</div>
                </div>
                <div class="row q-mb-xs">
                  <div class="col-5 text-weight-light">Item Number</div>
                  <div class="col-7 text-weight-bolder">{{ labelData?.item_number }}</div>
                </div>
                <div class="row q-mb-xs">
                  <div class="col-5 text-weight-light">Ref Code</div>
                  <div class="col-7 text-weight-bolder">{{ labelData?.re_code }}</div>
                </div>
                <div class="row q-mb-xs">
                  <div class="col-5 text-weight-light">Order Code</div>
                  <div class="col-7 text-weight-bolder">{{ labelData?.order_code }}</div>
                </div>
                <div class="row">
                  <div class="col-5 text-weight-light">Batch ID</div>
                  <div class="col-7 text-weight-bolder">{{ labelData?.batch_id }}</div>
                </div>
              </div>
              <!-- QR Code -->
              <div class="col-5 flex flex-center">
                <q-icon name="qr_code_2" size="140px" />
              </div>
            </div>

            <!-- Weight / Packages Footer of Main Label -->
            <div class="row q-px-sm q-pb-md">
              <div class="col-6 text-center">
                <div class="text-overline text-grey-7" style="line-height: 1">Weight (kg)</div>
                <div class="text-h6 text-weight-bold text-blue-9">
                  {{ labelData?.net_volume }} / {{ labelData?.total_volume }}
                </div>
              </div>
              <div class="col-6 text-center border-left">
                <div class="text-overline text-grey-7" style="line-height: 1">Packages</div>
                <div class="text-h6 text-weight-bold text-deep-orange-9">
                  {{ labelData?.package_no }} / {{ labelData?.total_packages }}
                </div>
              </div>
            </div>

            <q-separator color="grey-3" size="2px" />

            <!-- Sub Label Strip -->
            <div class="sub-label-area q-pa-sm row items-center bg-white q-mt-sm rounded-borders">
              <div class="col-9 text-caption text-mono" style="line-height: 1.2; font-size: 0.75rem;">
                <div>{{ labelData?.order_code }}, {{ labelData?.item_number }}, {{ labelData?.re_code }}</div>
                <div>{{ labelData?.sku_id }}, {{ labelData?.base_quantity }} kg</div>
                <div>W: {{ labelData?.net_volume }} / {{ labelData?.total_volume }}</div>
                <div>P: {{ labelData?.package_no }} / {{ labelData?.total_packages }}</div>
              </div>
              <div class="col-3 flex flex-center">
                <q-icon name="qr_code_2" size="60px" />
              </div>
            </div>
            </div>
          </div>

          <!-- Main Print Button -->
          <div class="row justify-end">
            <q-btn
              label="Print"
              color="grey-6"
              class="q-px-xl q-py-sm"
              size="lg"
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
                <td colspan="6" class="text-center text-grey q-pa-md italic">No history records found</td>
              </tr>
            </tbody>
          </q-markup-table>
        </q-card-section>

        <q-card-section class="q-pt-md">
           <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6">
                 <div class="text-caption text-grey">Target Information</div>
                 <div class="text-subtitle2">Lot: {{ selectedHistoryItem?.intake_lot_id }}</div>
                 <div class="text-subtitle2">MAT: {{ selectedHistoryItem?.mat_sap_code }}</div>
              </div>
              <div class="col-12 col-md-6">
                 <div class="text-caption text-grey">Current Status</div>
                 <q-badge :color="selectedHistoryItem?.status === 'Active' ? 'green' : (selectedHistoryItem?.status === 'Hold' ? 'orange' : 'red')" size="md">
                    {{ selectedHistoryItem?.status }}
                 </q-badge>
              </div>
           </div>
        </q-card-section>

        <q-separator />

        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Ingredient Intake Label Dialog (6x6) -->
    <q-dialog v-model="showIntakeLabelDialog">
      <q-card style="min-width: 650px">
        <q-card-section class="row items-center q-pb-none bg-grey-3 text-black">
          <div class="text-h6 text-weight-bold">Ingredient Intake Label Print</div>
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
                        label="Default Printer"
                        v-model="selectedPrinter"
                        :options="['Zebra-Label-Printer', 'Brother-QL-800', 'Microsoft Print to PDF']"
                        bg-color="white"
                    />
                </div>
                <div class="col-4">
                    <q-btn color="primary" icon="print" label="Direct Print" class="full-width" @click="printIntakeLabel" />
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

.intake-label-6x6 {
  width: 550px;
  height: 550px;
  background: #fff;
  border: 4px solid #000;
  display: flex;
  flex-direction: column;
}

.intake-header {
  border-bottom: 3px solid #000;
  background: #eee;
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
</style>

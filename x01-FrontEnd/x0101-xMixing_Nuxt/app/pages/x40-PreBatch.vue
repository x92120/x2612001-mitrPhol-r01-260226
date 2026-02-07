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
       await fetchSkuStepsForPlan(plan.sku_id, plan.batch_size || 0)
    }

    // Reset selection if current index is out of bounds
    if (selectedBatchIndex.value >= filteredBatches.value.length) {
      selectedBatchIndex.value = 0
    }
    
    // Update require volume based on selected batch
    updateRequireVolume()
  }
}

const selectableIngredients = ref<any[]>([])

// Fetch Steps for the selected Plan's SKU to filter ingredients
const fetchSkuStepsForPlan = async (skuId: string, planBatchSize: number = 0) => {
    try {
        const steps = await $fetch<any[]>(`${appConfig.apiBaseUrl}/api/v_sku_step_detail?sku_id=${skuId}`, {
            headers: getAuthHeader() as Record<string, string>
        })
        
        skuSteps.value = steps
        
        // Filter unique ingredients for the list view
        const uniqueMap = new Map()
        let counter = 1
        
        steps.forEach((step: any) => {
            if (step.re_code && step.ingredient_name) {
                if (!uniqueMap.has(step.re_code)) {
                    uniqueMap.set(step.re_code, {
                        index: counter++,
                        re_code: step.re_code,
                        ingredient_name: step.ingredient_name,
                        std_package_size: step.std_package_size || 0,
                        total_require: 0,
                        isDone: false 
                    })
                }
                
                const entry = uniqueMap.get(step.re_code)
                
                // Calculate required weight based on Plan Batch Size vs SKU Std Batch Size
                let stepReq = parseFloat(step.require) || 0
                if (planBatchSize > 0 && step.std_batch_size > 0) {
                    stepReq = (stepReq / step.std_batch_size) * planBatchSize
                }
                
                entry.total_require += stepReq
            }
        })
        
        selectableIngredients.value = Array.from(uniqueMap.values())
        
        // Clear current selection if it's not in the new list
        if (selectedReCode.value && !uniqueMap.has(selectedReCode.value)) {
            selectedReCode.value = ''
        }
    } catch (e) {
        console.error('Error fetching SKU steps for ingredients', e)
    }
}


// Update require volume when batch is selected
// NOTE: User requested Request Volume to stay 0 until ingredient is selected/double-clicked.
// So we no longer auto-populate from batch size here.
const updateRequireVolume = () => {
  // if (selectedBatch.value) {
  //   requireVolume.value = selectedBatch.value.batch_size || 0
  //   
  //   // Calculate package size and batch volume if needed
  //   if (requireVolume.value > 0) {
  //     // Example: if package size is 50kg
  //     const numPackages = Math.ceil(requireVolume.value / packageSize.value)
  //     batchVolume.value = packageSize.value
  //   }
  // }
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

const inventoryColumns: QTableColumn[] = [
    { name: 'id', align: 'center', label: 'ID', field: 'id', sortable: true },
    { name: 'intake_lot_id', align: 'left', label: 'Intake Lot ID', field: 'intake_lot_id', sortable: true },
    { name: 'warehouse_location', align: 'center', label: 'From Warehouse', field: 'warehouse_location' },
    { name: 'lot_id', align: 'left', label: 'Lot ID', field: 'lot_id' },
    { name: 'mat_sap_code', align: 'left', label: 'MAT.SAP Code', field: 'mat_sap_code' },
    { name: 're_code', align: 'center', label: 'Re-Code', field: 're_code' },
    { name: 'intake_vol', align: 'right', label: 'Intake Vol (kg)', field: 'intake_vol' },
    { name: 'remain_vol', align: 'right', label: 'Remain Vol (kg)', field: 'remain_vol', classes: 'text-red text-weight-bold' },
    { name: 'intake_package_vol', align: 'right', label: 'Pkg Vol', field: 'intake_package_vol' },
    { name: 'package_intake', align: 'center', label: 'Pkgs', field: 'package_intake' },
    { name: 'expire_date', align: 'center', label: 'Expire Date', field: 'expire_date', format: (val: any) => val ? val.split('T')[0] : '' },
    { name: 'status', align: 'center', label: 'Status', field: 'status' }
]

const filteredInventory = computed(() => {
    // If no ingredient selected, maybe show empty?
    if (!selectedReCode.value) return []
    // Filter by re_code and sort by intake_lot_id (FIFO - ascending)
    return inventoryRows.value
        .filter(item => {
            // Simple case-insensitive match just in case
            return (item.re_code || '').trim().toUpperCase() === selectedReCode.value.trim().toUpperCase() &&
                   // Optional: Filter only active/non-empty? User just said filter by re-code. 
                   // Usually on-hand implies remain_vol > 0. Let's assume on-hand.
                   item.remain_vol > 0 && 
                   ['Active', 'Hold'].includes(item.status)
        })
        .sort((a, b) => {
            // Sort by intake_lot_id ascending (FIFO)
            return a.intake_lot_id.localeCompare(b.intake_lot_id)
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

// Handle inventory row selection
const onInventoryRowClick = (evt: any, row: InventoryItem) => {
    selectedInventoryItem.value = [row]
    selectedIntakeLotId.value = row.intake_lot_id
    
    $q.notify({
        type: 'positive',
        message: `Selected: ${row.intake_lot_id}`,
        position: 'top',
        timeout: 1000
    })
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
const requestBatch = ref(0)
const batchedVolume = ref(0) // Total volume already batched
const remainVolume = computed(() => {
    return Math.max(0, requireVolume.value - batchedVolume.value)
})

// Computed Actual Scale Value based on selected scale
const activeScale = computed(() => scales.value.find(s => s.id === selectedScale.value))

const actualScaleValue = computed(() => {
  return activeScale.value ? activeScale.value.value : 0
})

// Automate scale selection based on Request Batch
watch(requestBatch, (val) => {
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
  const diff = Math.abs(requestBatch.value - actualScaleValue.value)
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
             requestBatch.value = Math.min(requireVolume.value, packageSize.value)
        } else {
            // Fallback reset
            // batchVolume.value = 0
            currentPackage.value = ''
            requestBatch.value = 0
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
  const diff = Math.abs(requestBatch.value - scale.value)
  // Check if within tolerance
  if (requestBatch.value > 0 && diff <= scale.tolerance) {
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

const openLabelDialog = () => {
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
      net_volume: actualScaleValue.value,
      total_volume: requireVolume.value, // This is the total required for this ingredient in this batch
      total_request_volume: requestBatch.value
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
        requestBatch.value = Math.max(0, Number(nextReq.toFixed(3)))
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
      <div class="col-12 col-md-3">
        <!-- Master Production Plan -->
        <div class="q-mb-md">
          <div class="text-subtitle2 q-mb-xs">Master Production Plan</div>
          <q-select
            outlined
            v-model="selectedProductionPlan"
            :options="productionPlanOptions"
            dense
            bg-color="white"
            dropdown-icon="arrow_drop_down"
            options-dense
            :loading="isLoading"
          />
        </div>

        <!-- RE-Code List View -->
        <div class="q-mb-md">
          <div class="text-subtitle2 q-mb-xs">Ingredient List</div>
          <div class="ingredient-list-container">
            <q-list separator dense class="bg-white">
                <!-- Header -->
                <q-item class="bg-grey-3 text-weight-bold" dense>
                    <q-item-section avatar style="min-width: 30px;">#</q-item-section>
                    <q-item-section>Ingredient</q-item-section>
                    <q-item-section style="max-width: 80px;" class="text-right">Req. Wt</q-item-section>
                    <q-item-section side>Status</q-item-section>
                </q-item>

                <q-item
                    v-for="ing in selectableIngredients"
                    :key="ing.re_code"
                    clickable
                    v-ripple
                    :active="selectedReCode === ing.re_code"
                    active-class="bg-blue-1 text-blue-9"
                    @click="selectedReCode = ing.re_code; onIngredientSelect()"
                    @dblclick="onIngredientDoubleClick(ing)"
                >
                    <!-- Column 1: Item Number -->
                    <q-item-section avatar style="min-width: 30px;">
                        {{ ing.index }}
                    </q-item-section>

                    <!-- Column 2: Code and Description -->
                    <q-item-section>
                        <q-item-label class="text-weight-bold">{{ ing.re_code }}</q-item-label>
                        <q-item-label caption lines="1">{{ ing.ingredient_name }}</q-item-label>
                    </q-item-section>

                    <!-- Column 3: Request Weight -->
                    <q-item-section style="max-width: 80px;" class="text-right">
                         <q-item-label class="text-weight-bold">{{ ing.total_require.toFixed(3) }}</q-item-label>
                    </q-item-section>

                    <!-- Column 4: Status -->
                    <q-item-section side>
                        <div v-if="ing.isDone" class="row items-center">
                            <q-icon name="check_circle" color="green" size="sm" />
                        </div>
                        <div v-else>
                           <q-icon name="radio_button_unchecked" color="grey-4" size="sm" />
                        </div>
                    </q-item-section>
                </q-item>
            </q-list>
          </div>
        </div>

        <!-- Batch ID List -->
        <div>
          <div class="text-subtitle2 q-mb-xs">Select Batch Planning ID</div>
          <div class="batch-list-container">
            <q-list class="no-border">
              <q-item
                v-for="(batch, index) in batchIds"
                :key="index"
                clickable
                v-ripple
                dense
                :class="{ 'bg-blue-1 text-blue-9': selectedBatchIndex === index }"
                @click="onSelectBatch(index)"
              >
                <q-item-section>
                  <q-item-label>{{ batch }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </div>
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
           <q-card-section class="q-pb-none">
             <div class="text-h6">On Hand Inventory</div>
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
                        <q-badge :color="props.value === 'Active' ? 'green' : 'orange'">
                            {{ props.value }}
                        </q-badge>
                    </q-td>
                </template>

                <!-- Summary Row -->
                <template v-slot:bottom-row>
                    <q-tr class="bg-grey-2 text-weight-bold">
                        <q-td colspan="7" class="text-right">Total:</q-td>
                        <q-td class="text-right">{{ inventorySummary.remain_vol.toFixed(3) }}</q-td>
                        <q-td></q-td>
                        <q-td class="text-center">{{ inventorySummary.pkgs }}</q-td>
                        <q-td colspan="2"></q-td>
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
                        bg-color="blue-1"
                        readonly
                        placeholder="Selected Intake Lot ID"
                        />
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

                <!-- Request Batch Moved Here -->
                <div class="col-12 col-md-2">
                    <div class="text-subtitle2 q-mb-xs">Request Batch</div>
                    <q-input outlined v-model.number="requestBatch" dense bg-color="yellow-1" />
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
      <q-card style="min-width: 600px; max-width: 800px">
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

          <!-- Label Preview Container -->
          <div class="label-preview-container q-pa-sm q-mb-md">
            <!-- Main Label Area -->
            <div class="main-label-area q-pa-sm row">
              <!-- Text Details -->
              <div class="col-7 text-body2 q-pr-sm" style="line-height: 1.4">
                <div class="row">
                  <div class="col-5">SKUName</div>
                  <div class="col-7 text-weight-bold">S77CA4SN02</div>
                </div>
                <div class="row">
                  <div class="col-5">BaseQuantity</div>
                  <div class="col-7 text-weight-bold">1000</div>
                </div>
                <div class="row">
                  <div class="col-5">ItemNumber</div>
                  <div class="col-7 text-weight-bold">10</div>
                </div>
                <div class="row">
                  <div class="col-5">RefCode</div>
                  <div class="col-7 text-weight-bold">S710009900</div>
                </div>
                <div class="row">
                  <div class="col-5">OrderCode</div>
                  <div class="col-7 text-weight-bold">ord251110-001</div>
                </div>
                <div class="row">
                  <div class="col-5">BatchSize</div>
                  <div class="col-7 text-weight-bold">500.00</div>
                </div>
              </div>
              <!-- QR Code -->
              <div class="col-5 flex flex-center">
                <q-icon name="qr_code_2" size="140px" />
              </div>
            </div>

            <!-- Weight / Packages Footer of Main Label -->
            <div class="row q-px-sm q-pb-sm">
              <div class="col-6 text-center">
                <div class="text-caption text-weight-bold">Weight</div>
                <div class="text-subtitle1 text-weight-bold">100.50/414.50</div>
              </div>
              <div class="col-6 text-center">
                <div class="text-caption text-weight-bold">Packages</div>
                <div class="text-subtitle1 text-weight-bold">1/5</div>
              </div>
            </div>

            <q-separator color="black" size="2px" />

            <!-- Sub Label Strip -->
            <div class="sub-label-area q-pa-sm row items-center">
              <div class="col-9 text-caption" style="line-height: 1.2">
                <div>ord251110-001,10,S710009900</div>
                <div>S77CA4SN02, 1000</div>
                <div>100.50/414.50</div>
                <div>1/5</div>
              </div>
              <div class="col-3 flex flex-center">
                <q-icon name="qr_code_2" size="60px" />
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
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid rgba(0,0,0,0.1);
  cursor: pointer;
  transition: all 0.3s ease;
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
  border: 3px solid #1d3557; /* Dark border */
  border-radius: 12px;
  background-color: #f8f9fa;
}
.main-label-area {
  min-height: 200px;
}
/* Active Scale Highlighting */
.active-scale-border {
  border: 5px solid #4caf50 !important; /* Green */
  border-radius: 8px;
}
</style>

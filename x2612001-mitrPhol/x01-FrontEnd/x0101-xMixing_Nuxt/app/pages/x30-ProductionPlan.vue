<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { RouterView } from 'vue-router'
import { appConfig } from '~/appConfig/config'

const $q = useQuasar()

// --- State ---
const skuId = ref('')
const skuName = ref('')
const plantOptions = ref<{ label: string; value: string }[]>([])
const plant = ref('')
const productionRequire = ref<number | null>(null) // Total Volume
const batchStandard = ref<number | null>(null) // Batch Size
const numberOfBatch = ref<number>(0)
const totalPlanVolume = computed(() => {
  if (numberOfBatch.value && batchStandard.value) {
    return numberOfBatch.value * batchStandard.value
  }
  return 0
})
const startDate = ref(new Date().toISOString().slice(0, 10))
const finishDate = ref(new Date().toISOString().slice(0, 10))

// Plant Configurations from API
const plantConfigs = ref<Record<string, number>>({})
const plantNames = ref<Record<string, string>>({})

// Data from API
const availableSkus = ref<any[]>([])
const plans = ref<any[]>([])
const showAll = ref(false)
const showSkuList = ref(false)

// Filtered plans based on showAll checkbox
const filteredPlans = computed(() => {
  if (showAll.value) {
    return plans.value
  }
  return plans.value.filter(plan => plan.status !== 'Cancelled')
})

// Fetch plants from API
const fetchPlants = async () => {
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/plants/`)
    if (response.ok) {
      const data = await response.json()
      // Use map-options/emit-value in q-select to handle objects
      plantOptions.value = data.map((p: any) => ({
        label: p.plant_name,
        value: p.plant_id,
      }))
      // Build capacity and name map
      data.forEach((p: any) => {
        plantConfigs.value[p.plant_id] = p.plant_capacity
        plantNames.value[p.plant_id] = p.plant_name
      })
      // Set default plant if available
      if (plantOptions.value.length > 0 && !plant.value) {
        plant.value = plantOptions.value[0]?.value || ''
      }
    }
  } catch (error) {
    console.error('Error fetching plants:', error)
  }
}

// Computed Options
const skuOptions = computed(() => {
  return availableSkus.value.map((r) => ({
    label: `${r.sku_id} - ${r.sku_name}`,
    value: r.sku_id,
    sku_name: r.sku_name,
  }))
})

// Auto-fill Batch Size when Plant changes
watch(
  plant,
  (newVal) => {
    if (newVal && plantConfigs.value[newVal]) {
      batchStandard.value = plantConfigs.value[newVal]
    }
  },
  { immediate: true },
)

// Auto-calculate logic
watch([productionRequire, batchStandard], () => {
  if (productionRequire.value && batchStandard.value && batchStandard.value > 0) {
    numberOfBatch.value = Math.ceil(productionRequire.value / batchStandard.value)
  } else {
    numberOfBatch.value = 0
  }
})

const onManualBatchChange = () => {
  if (numberOfBatch.value && batchStandard.value && batchStandard.value > 0) {
    productionRequire.value = numberOfBatch.value * batchStandard.value
  }
}

const onSkuIdSelect = (val: any) => {
  const selected = availableSkus.value.find((s) => s.sku_id === val)
  if (selected) {
    skuName.value = selected.sku_name
  }
}

const onSkuNameSelect = (val: any) => {
  const selected = availableSkus.value.find((s) => s.sku_name === val)
  if (selected) {
    skuId.value = selected.sku_id
  }
}

const selectSku = (row: any) => {
  skuId.value = row.sku_id
  skuName.value = row.sku_name
  $q.notify({
    type: 'positive',
    message: `Selected: ${row.sku_id}`,
    position: 'top',
    timeout: 1000
  })
  
  // Optional: Auto-scroll to create form
  setTimeout(() => {
    const el = document.getElementById('create-plan-form')
    if (el) el.scrollIntoView({ behavior: 'smooth' })
  }, 100)
}

const skuFilters = ref<Record<string, string>>({})
const showSkuFilters = ref(false)
const showAllSkus = ref(false)

const filteredSkus = computed(() => {
  let filtered = availableSkus.value

  // Filter out Inactive if showAllSkus is false
  if (!showAllSkus.value) {
    filtered = filtered.filter((s) => s.status === 'Active')
  }

  // Filter by columns
  return filtered.filter((row) => {
    return Object.keys(skuFilters.value).every((key) => {
      const filterVal = skuFilters.value[key]?.toLowerCase()
      if (!filterVal) return true

      const rowVal = String(row[key] || '').toLowerCase()
      return rowVal.includes(filterVal)
    })
  })
})

const resetSkuFilters = () => {
  skuFilters.value = {}
}

const skuColumns: QTableColumn[] = [
  { name: 'sku_id', label: 'SKU ID', field: 'sku_id', align: 'left', sortable: true },
  { name: 'sku_name', label: 'SKU Name', field: 'sku_name', align: 'left', sortable: true },
  { name: 'creat_by', label: 'Created By', field: 'creat_by', align: 'left' },
  {
    name: 'created_at',
    label: 'Created At',
    field: 'created_at',
    align: 'left',
    format: (val: string) => (val ? new Date(val).toLocaleString() : '-'),
  },
  { name: 'update_by', label: 'Edit By', field: 'update_by', align: 'left' },
  {
    name: 'updated_at',
    label: 'Edit At',
    field: 'updated_at',
    align: 'left',
    format: (val: string) => (val ? new Date(val).toLocaleString() : '-'),
  },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'sku_actions', label: 'Actions', field: 'sku_actions', align: 'center' },
]

// Columns
const columns: QTableColumn[] = [
  { name: 'id', label: 'ID', field: 'id', align: 'left', sortable: true },
  { name: 'plan_id', label: 'Plan ID', field: 'plan_id', align: 'left', sortable: true },
  { name: 'sku_id', label: 'SKU-ID', field: 'sku_id', align: 'left', sortable: true },
  { name: 'plant', label: 'Plant', field: 'plant', align: 'left', sortable: true },
  {
    name: 'total_volume',
    label: 'Total Vol',
    field: 'total_volume',
    align: 'right',
    sortable: true,
  },
  {
    name: 'total_plan_volume',
    label: 'Total Plan Vol',
    field: 'total_plan_volume',
    align: 'right',
    sortable: true,
  },
  { name: 'flavour_house', label: 'Flavour House', field: 'flavour_house', align: 'center' },
  { name: 'spp', label: 'SPP', field: 'spp', align: 'center' },
  { name: 'batch_prepare', label: 'Batch Prepare', field: 'batch_prepare', align: 'center' },
  { name: 'ready_to_product', label: 'Ready to Prod', field: 'ready_to_product', align: 'center' },
  { name: 'production', label: 'Production', field: 'production', align: 'center' },
  { name: 'done', label: 'Done', field: 'done', align: 'center' },
  { name: 'status', label: 'Status', field: 'status', align: 'center', sortable: true },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
]

// Batch Columns
const batchColumns: QTableColumn[] = [
  { name: 'batch_id', label: 'Batch ID', field: 'batch_id', align: 'left', sortable: true },
  { name: 'batch_size', label: 'Batch Size', field: 'batch_size', align: 'right', sortable: true },
  { name: 'flavour_house', label: 'Flavour House', field: 'flavour_house', align: 'center' },
  { name: 'spp', label: 'SPP', field: 'spp', align: 'center' },
  { name: 'batch_prepare', label: 'Batch Prepare', field: 'batch_prepare', align: 'center' },
  { name: 'ready_to_product', label: 'Ready to Prod', field: 'ready_to_product', align: 'center' },
  { name: 'production', label: 'Production', field: 'production', align: 'center' },
  { name: 'done', label: 'Done', field: 'done', align: 'center' },
]
// Actions
// Fetch SKUs
const fetchSkus = async () => {
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/skus/`)
    if (response.ok) {
      availableSkus.value = await response.json()
    }
  } catch (error) {
    console.error('Error fetching SKUs:', error)
  }
}

// Fetch Plans
const fetchPlans = async () => {
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/production-plans/?skip=0&limit=100`)
    if (response.ok) {
      plans.value = await response.json()
    }
  } catch (error) {
    console.error('Error fetching plans:', error)
  }
}

const isCreating = ref(false)

const onCreatePlan = async () => {
  if (!skuId.value || !plant.value || !productionRequire.value || !numberOfBatch.value) {
    $q.notify({ type: 'warning', message: 'Please fill all required fields' })
    return
  }

  isCreating.value = true
  try {
    const payload = {
      sku_id: skuId.value,
      sku_name: skuName.value,
      plant: plant.value,
      total_volume: Number(productionRequire.value),
      batch_size: Number(batchStandard.value),
      num_batches: Number(numberOfBatch.value),
      start_date: startDate.value,
      finish_date: finishDate.value,
    }

    const response = await fetch(`${appConfig.apiBaseUrl}/production-plans/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (response.ok) {
      $q.notify({ type: 'positive', message: 'Plan created successfully' })
      resetForm()
      fetchPlans()
    } else {
      const err = await response.json()
      $q.notify({ type: 'negative', message: err.detail || 'Failed to create plan' })
    }
  } catch (error) {
    console.error('Error creating plan:', error)
    $q.notify({ type: 'negative', message: 'Network error or server down' })
  } finally {
    isCreating.value = false
  }
}



const onCancelPlan = async (plan: any) => {
  $q.dialog({
    title: 'Cancel Production Plan',
    message: 'Are you sure you want to cancel this plan? This will also cancel all associated batches.',
    prompt: {
      model: '',
      type: 'text',
      label: 'Reason for cancellation (optional)',
      outlined: true
    },
    cancel: true,
    persistent: true
  }).onOk(async (comment: string) => {
    try {
      const response = await fetch(`${appConfig.apiBaseUrl}/production-plans/${plan.id}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          comment: comment || null,
          changed_by: 'user' // You can replace this with actual user info
        })
      })

      if (response.ok) {
        $q.notify({ type: 'positive', message: 'Plan cancelled successfully' })
        fetchPlans()
      } else {
        const error = await response.json()
        $q.notify({ type: 'negative', message: `Failed to cancel plan: ${error.detail || 'Unknown error'}` })
      }
    } catch (e) {
      console.error(e)
      $q.notify({ type: 'negative', message: 'Network error while cancelling plan' })
    }
  })
}

const showHistory = async (plan: any) => {
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/production-plans/${plan.id}/history`)
    if (response.ok) {
      const history = await response.json()
      
      // Format history for display
      const historyText = history.length > 0 
        ? history.map((h: any) => {
            const date = new Date(h.changed_at).toLocaleString()
            const statusChange = h.old_status && h.new_status 
              ? `${h.old_status} → ${h.new_status}` 
              : h.new_status || 'N/A'
            return `<div style="margin-bottom: 12px; padding: 8px; background: #f5f5f5; border-radius: 4px;">
              <strong>${h.action.toUpperCase()}</strong> by <strong>${h.changed_by}</strong><br/>
              <small>${date}</small><br/>
              Status: ${statusChange}<br/>
              ${h.remarks ? `<em>${h.remarks}</em>` : ''}
            </div>`
          }).join('')
        : '<p>No history available for this plan.</p>'
      
      $q.dialog({
        title: `History: ${plan.plan_id}`,
        message: historyText,
        html: true,
        style: 'max-width: 600px'
      })
    } else {
      $q.notify({ type: 'negative', message: 'Failed to load history' })
    }
  } catch (e) {
  }
}

const printPlan = (plan: any) => {
  const printWindow = window.open('', '_blank')
  if (!printWindow) return
  
  const batchesHTML = plan.batches?.map((batch: any, index: number) => `
    <tr>
      <td style="border: 1px solid #ddd; padding: 8px;">${index + 1}</td>
      <td style="border: 1px solid #ddd; padding: 8px;">${batch.batch_id}</td>
      <td style="border: 1px solid #ddd; padding: 8px;">${batch.batch_size || 'N/A'}</td>
      <td style="border: 1px solid #ddd; padding: 8px;">${batch.status}</td>
    </tr>
  `).join('') || '<tr><td colspan="4" style="text-align: center; padding: 16px;">No batches</td></tr>'
  
  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>Production Plan - ${plan.plan_id}</title>
      <style>
        @page { size: A4; margin: 20mm; }
        body { font-family: Arial, sans-serif; font-size: 12px; }
        h1 { font-size: 18px; margin-bottom: 10px; }
        h2 { font-size: 14px; margin-top: 20px; margin-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; font-weight: bold; }
        .summary { background-color: #f9f9f9; padding: 10px; margin-top: 20px; }
      </style>
    </head>
    <body>
      <div style="page-break-after: always;">
        <h1 style="text-align: center; color: #1976d2; border-bottom: 2px solid #1976d2; padding-bottom: 10px;">Production Plan Summary</h1>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
          <tr><th style="width: 40%; background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">Plan ID</th><td style="border: 1px solid #ddd; padding: 12px;">${plan.plan_id}</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">SKU ID</th><td style="border: 1px solid #ddd; padding: 12px;">${plan.sku_id}</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">SKU Name</th><td style="border: 1px solid #ddd; padding: 12px;">${plan.sku_name || 'N/A'}</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">Plant</th><td style="border: 1px solid #ddd; padding: 12px;">${plantNames.value[plan.plant] || plan.plant}</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">Total Plan Volume</th><td style="border: 1px solid #ddd; padding: 12px;">${plan.total_plan_volume || '0'} kg</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">Number of Batches</th><td style="border: 1px solid #ddd; padding: 12px;">${plan.num_batches || 0}</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">Batch Size</th><td style="border: 1px solid #ddd; padding: 12px;">${plan.batch_size || 'N/A'} kg</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">Period</th><td style="border: 1px solid #ddd; padding: 12px;">${plan.start_date || 'N/A'} to ${plan.finish_date || 'N/A'}</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">Status</th><td style="border: 1px solid #ddd; padding: 12px;"><strong>${plan.status}</strong></td></tr>
        </table>
        
        <div style="margin-top: 40px; background: #f9f9f9; padding: 20px; border-radius: 8px; border-left: 5px solid #1976d2;">
          <h2 style="margin-top: 0; font-size: 16px;">Creation Details</h2>
          <p><strong>Created:</strong> ${new Date(plan.created_at).toLocaleString()}</p>
          <p><strong>Created By:</strong> ${plan.created_by || 'N/A'}</p>
          ${plan.updated_by ? '<p><strong>Last Updated By:</strong> ' + plan.updated_by + '</p>' : ''}
        </div>
      </div>
      
      <div>
        <h2 style="color: #1976d2; border-bottom: 2px solid #1976d2; padding-bottom: 10px;">Batch Details</h2>
        <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
          <thead>
            <tr>
              <th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5;">#</th>
              <th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5;">Batch ID</th>
              <th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5;">Size (kg)</th>
              <th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5;">Status</th>
            </tr>
          </thead>
          <tbody>
            ${batchesHTML}
          </tbody>
        </table>
      </div>
      ` + 
      '<script>' +
      '  window.onload = () => {' +
      '    window.print();' +
      '    window.onafterprint = () => window.close();' +
      '  };' +
      '<' + '/script>' +
      `
    </body>
    </html>
  `

  
  printWindow.document.write(html)
  printWindow.document.close()
}

const printAllPlans = () => {
  const printWindow = window.open('', '_blank')
  if (!printWindow) return
  
  const plansHTML = filteredPlans.value.map((plan: any) => {
    const batchesHTML = plan.batches?.map((batch: any, index: number) => `
      <tr>
        <td style="border: 1px solid #ddd; padding: 4px; font-size: 10px;">${index + 1}</td>
        <td style="border: 1px solid #ddd; padding: 4px; font-size: 10px;">${batch.batch_id}</td>
        <td style="border: 1px solid #ddd; padding: 4px; font-size: 10px;">${batch.batch_size || 'N/A'}</td>
        <td style="border: 1px solid #ddd; padding: 4px; font-size: 10px;">${batch.status}</td>
      </tr>
    `).join('') || '<tr><td colspan="4" style="text-align: center; padding: 8px; font-size: 10px;">No batches</td></tr>'
    
    return `
      <!-- Page 1: Plan Summary -->
      <div style="page-break-after: always; margin-bottom: 20px;">
        <h2 style="font-size: 16px; margin-bottom: 15px; color: #1976d2; border-bottom: 1px solid #1976d2; padding-bottom: 5px;">
          ${plan.plan_id} - Summary
        </h2>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 11px;">
          <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f2f2f2; width: 35%;">SKU</th><td style="border: 1px solid #ddd; padding: 8px;">${plan.sku_id} - ${plan.sku_name || ''}</td></tr>
          <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f2f2f2;">Plant</th><td style="border: 1px solid #ddd; padding: 8px;">${plantNames.value[plan.plant] || plan.plant}</td></tr>
          <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f2f2f2;">Total Plan Volume</th><td style="border: 1px solid #ddd; padding: 8px;">${plan.total_plan_volume || 'N/A'} kg</td></tr>
          <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f2f2f2;">Number of Batches</th><td style="border: 1px solid #ddd; padding: 8px;">${plan.num_batches || 0}</td></tr>
          <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f2f2f2;">Period</th><td style="border: 1px solid #ddd; padding: 8px;">${plan.start_date || 'N/A'} to ${plan.finish_date || 'N/A'}</td></tr>
          <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f2f2f2;">Status</th><td style="border: 1px solid #ddd; padding: 8px;"><strong>${plan.status}</strong></td></tr>
        </table>
        
        <div style="margin-top: 30px; background: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 5px solid #1976d2;">
          <h3 style="margin-top: 0; font-size: 12px;">Timeline</h3>
          <p style="margin: 5px 0;"><strong>Created:</strong> ${new Date(plan.created_at).toLocaleString()}</p>
          <p style="margin: 5px 0;"><strong>Created By:</strong> ${plan.created_by || 'N/A'}</p>
          ${plan.updated_by ? `<p style="margin: 5px 0;"><strong>Last Updated By:</strong> ${plan.updated_by}</p>` : ''}
        </div>
      </div>

      <!-- Page 2: Batch Details -->
      <div style="page-break-after: always; margin-bottom: 20px;">
        <h2 style="font-size: 16px; margin-bottom: 15px; color: #1976d2; border-bottom: 1px solid #1976d2; padding-bottom: 5px;">
          ${plan.plan_id} - Batch Details
        </h2>
        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr>
              <th style="border: 1px solid #ddd; padding: 6px; background: #f2f2f2; font-size: 11px;">#</th>
              <th style="border: 1px solid #ddd; padding: 6px; background: #f2f2f2; font-size: 11px;">Batch ID</th>
              <th style="border: 1px solid #ddd; padding: 6px; background: #f2f2f2; font-size: 11px;">Size (kg)</th>
              <th style="border: 1px solid #ddd; padding: 6px; background: #f2f2f2; font-size: 11px;">Status</th>
            </tr>
          </thead>
          <tbody>${batchesHTML}</tbody>
        </table>
      </div>
    `
  }).join('')
  
  const totalPlans = filteredPlans.value.length
  const totalBatches = filteredPlans.value.reduce((sum: number, plan: any) => sum + (plan.batches?.length || 0), 0)
  const totalVolume = filteredPlans.value.reduce((sum: number, plan: any) => sum + (plan.total_plan_volume || 0), 0)
  
  // Calculate status and plant breakdowns for the summary page
  const statusCounts: Record<string, number> = {}
  const plantCounts: Record<string, number> = {}
  const plantVolumes: Record<string, number> = {}
  
  filteredPlans.value.forEach((plan: any) => {
    statusCounts[plan.status] = (statusCounts[plan.status] || 0) + 1
    const pName = plantNames.value[plan.plant] || plan.plant
    plantCounts[pName] = (plantCounts[pName] || 0) + 1
    plantVolumes[pName] = (plantVolumes[pName] || 0) + (plan.total_plan_volume || 0)
  })

  const statusRows = Object.entries(statusCounts).map(([status, count]) => 
    `<tr><td style="border: 1px solid #ddd; padding: 8px;">${status}</td><td style="border: 1px solid #ddd; padding: 8px; text-align: right;">${count}</td></tr>`
  ).join('')
  
  const plantRows = Object.entries(plantCounts).map(([p, count]) => 
    `<tr><td style="border: 1px solid #ddd; padding: 8px;">${p}</td><td style="border: 1px solid #ddd; padding: 8px; text-align: right;">${count}</td><td style="border: 1px solid #ddd; padding: 8px; text-align: right;">${(plantVolumes[p] || 0).toFixed(2)} kg</td></tr>`
  ).join('')

  const summaryPage = `
    <div style="page-break-after: always; margin-bottom: 30px;">
      <h1 style="font-size: 24px; color: #1976d2; text-align: center; margin-bottom: 20px; border-bottom: 3px solid #1976d2; padding-bottom: 10px;">
        Production Plans Summary Report
      </h1>
      
      <div style="background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
        <h2 style="margin: 0 0 15px 0; font-size: 18px;">Overall Statistics</h2>
        <div style="display: flex; justify-content: space-around; gap: 10px;">
          <div style="background: rgba(255,255,255,0.2); padding: 15px; border-radius: 5px; text-align: center; flex: 1;">
            <div style="font-size: 28px; font-weight: bold;">${totalPlans}</div>
            <div style="font-size: 11px;">Total Plans</div>
          </div>
          <div style="background: rgba(255,255,255,0.2); padding: 15px; border-radius: 5px; text-align: center; flex: 1;">
            <div style="font-size: 28px; font-weight: bold;">${totalBatches}</div>
            <div style="font-size: 11px;">Total Batches</div>
          </div>
          <div style="background: rgba(255,255,255,0.2); padding: 15px; border-radius: 5px; text-align: center; flex: 1;">
            <div style="font-size: 28px; font-weight: bold;">${totalVolume.toFixed(2)}</div>
            <div style="font-size: 11px;">Total Volume (kg)</div>
          </div>
        </div>
      </div>
      
      <div style="margin-bottom: 20px;">
        <h2 style="font-size: 14px; border-left: 4px solid #1976d2; padding-left: 8px; margin-bottom: 10px;">Status Breakdown</h2>
        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
          <thead>
            <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5; text-align: left;">Status</th><th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5; text-align: right;">Count</th></tr>
          </thead>
          <tbody>${statusRows}</tbody>
        </table>
      </div>
      
      <div>
        <h2 style="font-size: 14px; border-left: 4px solid #1976d2; padding-left: 8px; margin-bottom: 10px;">Plant Distribution</h2>
        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
          <thead>
            <tr>
              <th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5; text-align: left;">Plant</th>
              <th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5; text-align: right;">Plans</th>
              <th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5; text-align: right;">Total Volume</th>
            </tr>
          </thead>
          <tbody>${plantRows}</tbody>
        </table>
      </div>
    </div>
  `

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>All Production Plans</title>
      <style>
        @page { size: A4; margin: 15mm; }
        body { font-family: Arial, sans-serif; }
        h1 { font-size: 16px; margin-bottom: 15px; }
        table { border-collapse: collapse; }
      </style>
    </head>
    <body>
      ${summaryPage}
      <h1 style="text-align: center; border-bottom: 1px solid #eee; padding-bottom: 10px;">Detailed Production Plans</h1>
      ${plansHTML}
      ` + 
      '<script>' +
      '  window.onload = () => {' +
      '    window.print();' +
      '    window.onafterprint = () => window.close();' +
      '  };' +
      '<' + '/script>' +
      `
    </body>
    </html>
  `
  
  printWindow.document.write(html)
  printWindow.document.close()
}




// Search support for QSelect
const filteredSkuIdOptions = ref<any[]>([])
const filteredSkuNameOptions = ref<any[]>([])

const skuNameOptions = computed(() => {
  return availableSkus.value.map((r) => ({
    label: r.sku_name,
    value: r.sku_name,
  }))
})

const onSkuIdFilter = (val: string, update: any) => {
  update(() => {
    const needle = val.toLowerCase()
    filteredSkuIdOptions.value = skuOptions.value.filter(
      (v) => v.label.toLowerCase().includes(needle) || v.value.toLowerCase().includes(needle),
    )
  })
}

const onSkuNameFilter = (val: string, update: any) => {
  update(() => {
    const needle = val.toLowerCase()
    filteredSkuNameOptions.value = skuNameOptions.value.filter((v: any) =>
      v.label.toLowerCase().includes(needle),
    )
  })
}

const resetForm = () => {
  skuId.value = ''
  skuName.value = ''
  plant.value = plantOptions.value.length > 0 ? (plantOptions.value[0]?.value || '') : ''
  productionRequire.value = null
  batchStandard.value = null
  numberOfBatch.value = 0
  startDate.value = new Date().toISOString().slice(0, 10)
  finishDate.value = new Date().toISOString().slice(0, 10)
}

// Styling Helper
const getStatusColor = (status: string) => {
  if (status === 'Hold') return 'text-magenta'
  return 'text-blue-8'
}

onMounted(() => {
  fetchPlants()
  fetchSkus()
  fetchPlans()
})
</script>

<template>
  <!-- If child route is active, show child component. Otherwise show parent content -->
  <RouterView v-slot="{ Component }">
    <component v-if="Component" :is="Component" />
    <q-page v-else class="q-pa-md bg-white">
      <div class="row justify-between items-center q-mb-sm">
        <div class="row items-center q-gutter-sm">
          <q-btn
            :label="showSkuList ? 'Hide SKU List' : 'Show SKU List'"
            :color="showSkuList ? 'grey-7' : 'primary'"
            unelevated
            no-caps
            dense
            @click="showSkuList = !showSkuList"
            icon="list_alt"
          />
        </div>
        <div class="text-caption">Version 0.2</div>
      </div>

      <!-- SKU Master List Table -->
      <q-slide-transition>
        <div v-show="showSkuList" class="q-mb-xl">
          <div class="row items-center justify-between q-mb-sm">
            <div class="text-h6">SKU Master List</div>
            <div class="row items-center q-gutter-sm">
              <q-btn
                icon="refresh"
                color="primary"
                round
                flat
                dense
                @click="fetchSkus"
              >
                <q-tooltip>Refresh</q-tooltip>
              </q-btn>
              <q-btn
                icon="filter_alt_off"
                color="primary"
                round
                flat
                dense
                @click="resetSkuFilters"
              >
                <q-tooltip>Reset Filters</q-tooltip>
              </q-btn>
              <q-btn
                icon="filter_alt"
                color="accent"
                round
                flat
                dense
                @click="showSkuFilters = !showSkuFilters"
              >
                <q-tooltip>{{ showSkuFilters ? 'Hide Filters' : 'Show Filters' }}</q-tooltip>
              </q-btn>
              <q-checkbox
                v-model="showAllSkus"
                label="Show All (including Inactive)"
                dense
              />
            </div>
          </div>
          <q-card flat bordered class="custom-table-border">
            <q-table
              :rows="filteredSkus"
              :columns="skuColumns"
              row-key="id"
              flat
              dense
              :pagination="{ rowsPerPage: 10 }"
            >
              <template v-slot:header="props">
                <q-tr :props="props">
                  <q-th
                    v-for="col in props.cols"
                    :key="col.name"
                    :props="props"
                    class="text-black bg-white"
                    style="vertical-align: bottom; font-weight: normal; border-bottom: 2px solid #000"
                  >
                    <div v-if="showSkuFilters && col.name !== 'sku_actions'" class="q-pb-sm">
                      <q-input
                        v-model="skuFilters[col.field]"
                        dense
                        outlined
                        bg-color="white"
                        class="q-pa-none"
                        placeholder="Search"
                        style="font-weight: normal"
                        @click.stop
                      ></q-input>
                    </div>
                    {{ col.label }}
                  </q-th>
                </q-tr>
              </template>
              <template v-slot:body-cell-status="props">
                <q-td :props="props">
                  <q-chip
                    :color="props.value === 'Active' ? 'positive' : 'grey'"
                    text-color="white"
                    size="xs"
                  >
                    {{ props.value }}
                  </q-chip>
                </q-td>
              </template>
              <template v-slot:body-cell-sku_actions="props">
                <q-td :props="props" align="center">
                  <q-btn
                    icon="check_circle"
                    color="positive"
                    unelevated
                    no-caps
                    dense
                    size="sm"
                    label="Select"
                    @click="selectSku(props.row)"
                  >
                    <q-tooltip>Use this SKU for New Plan</q-tooltip>
                  </q-btn>
                </q-td>
              </template>
            </q-table>
          </q-card>
          <q-separator class="q-mt-md" color="black" size="2px" />
        </div>
      </q-slide-transition>

      <!-- HEADER FORM -->
      <div class="q-mb-lg" id="create-plan-form">
        <div class="text-h6 q-mb-md">Create Production Plan</div>
        <!-- Row 1 -->
        <div class="row q-col-gutter-md q-mb-sm">
          <div class="col-12 col-md-3">
            <div class="text-subtitle2 q-mb-xs">SKU-ID</div>
            <q-select
              outlined
              v-model="skuId"
              :options="filteredSkuIdOptions"
              dense
              bg-color="white"
              use-input
              input-debounce="0"
              @filter="onSkuIdFilter"
              emit-value
              map-options
              @update:model-value="onSkuIdSelect"
            />
          </div>
          <div class="col-12 col-md-6">
            <div class="text-subtitle2 q-mb-xs">SKU-Name</div>
            <q-select
              outlined
              v-model="skuName"
              :options="filteredSkuNameOptions"
              dense
              bg-color="white"
              use-input
              input-debounce="0"
              @filter="onSkuNameFilter"
              emit-value
              map-options
              @update:model-value="onSkuNameSelect"
            />
          </div>
          <div class="col-12 col-md-3">
            <div class="text-subtitle2 q-mb-xs">Plant</div>
            <div class="row q-gutter-xs">
              <div class="col">
                <q-select
                  outlined
                  v-model="plant"
                  :options="plantOptions"
                  dense
                  bg-color="white"
                  dropdown-icon="arrow_drop_down"
                  emit-value
                  map-options
                />
              </div>
              <div>
                <q-btn
                  icon="settings"
                  color="primary"
                  outline
                  dense
                  @click="$router.push({ name: 'PlantConfig' })"
                  style="height: 40px; width: 40px"
                >
                  <q-tooltip>Plant Configuration</q-tooltip>
                </q-btn>
              </div>
            </div>
          </div>
        </div>

        <!-- Row 2 -->
        <div class="row q-col-gutter-md q-mb-sm">
          <div class="col-12 col-md-3">
            <div class="text-subtitle2 q-mb-xs">Require Total Volume</div>
            <q-input outlined v-model="productionRequire" type="number" dense bg-color="white" />
          </div>
          <div class="col-12 col-md-2">
            <div class="text-subtitle2 q-mb-xs">Batch Standard</div>
            <q-input outlined v-model="batchStandard" type="number" dense bg-color="white" />
          </div>
          <div class="col-12 col-md-2">
            <div class="text-subtitle2 q-mb-xs">Number of Batch</div>
            <q-input
              outlined
              v-model="numberOfBatch"
              type="number"
              @update:model-value="onManualBatchChange"
              dense
              bg-color="white"
            />
          </div>
          <div class="col-12 col-md-2">
            <div class="text-subtitle2 q-mb-xs">Total Plan Volume</div>
             <q-input
              outlined
              :model-value="totalPlanVolume"
              readonly
              type="number"
              dense
              bg-color="grey-2"
            />
          </div>
        </div>

        <!-- Row 3 - Dates and Action -->
        <div class="row q-col-gutter-md q-mb-sm">
          <div class="col-12 col-md-3">
            <div class="text-subtitle2 q-mb-xs">Plan Start Date</div>
            <q-input outlined v-model="startDate" dense bg-color="white" type="date" />
          </div>
          <div class="col-12 col-md-3">
            <div class="text-subtitle2 q-mb-xs">Plan Finish Date</div>
            <q-input outlined v-model="finishDate" dense bg-color="white" type="date" />
          </div>
          <div class="col-12 col-md-6 flex items-end justify-end">
            <q-btn
              label="Add Plan"
              color="primary"
              class="q-px-lg"
              @click="onCreatePlan"
              unelevated
              no-caps
              :loading="isCreating"
              :disable="isCreating"
              style="height: 40px"
            />
          </div>
        </div>
      </div>

      <q-separator class="q-mb-md" color="black" size="2px" />

      <!-- BATCH TABLE -->
      <div class="row items-center justify-between q-mb-sm">
        <div class="text-h6">Production Plans</div>
        <div class="row items-center q-gutter-sm">
          <q-btn
            icon="refresh"
            color="primary"
            round
            flat
            dense
            @click="fetchPlans"
          >
            <q-tooltip>Refresh</q-tooltip>
          </q-btn>
          <q-btn
            icon="print"
            color="primary"
            round
            flat
            dense
            @click="printAllPlans"
          >
            <q-tooltip>Print All</q-tooltip>
          </q-btn>
          <q-checkbox
            v-model="showAll"
            label="Show All (including Cancelled)"
            dense
          />
        </div>
      </div>
      <q-card flat bordered class="q-mb-md custom-table-border">
        <q-table
          :rows="filteredPlans"
          :columns="columns"
          row-key="id"
          flat
          hide-bottom
          :pagination="{ rowsPerPage: 20 }"
        >
          <template v-slot:header="props">
            <q-tr :props="props">
              <q-th auto-width />
              <q-th
                v-for="col in props.cols"
                :key="col.name"
                :props="props"
                class="text-black bg-white"
                style="font-weight: normal; border-bottom: 2px solid #000"
              >
                {{ col.label }}
              </q-th>
            </q-tr>
          </template>

          <template v-slot:body="props">
            <q-tr :props="props">
              <q-td auto-width>
                <q-btn
                  size="sm"
                  color="accent"
                  round
                  dense
                  @click="props.expand = !props.expand"
                  :icon="props.expand ? 'remove' : 'add'"
                />
              </q-td>
              <q-td v-for="col in props.cols" :key="col.name" :props="props">
                <template v-if="col.name === 'plant'">
                  {{ plantNames[props.row.plant] || props.row.plant }}
                </template>
                <template
                  v-else-if="
                    [
                      'flavour_house',
                      'spp',
                      'batch_prepare',
                      'ready_to_product',
                      'production',
                      'done',
                    ].includes(col.name)
                  "
                >
                  <q-checkbox
                    v-model="props.row[col.name]"
                    disable
                  />
                </template>
                <template v-else-if="col.name === 'status'">
                   <q-chip
                      :color="
                        props.row.status === 'Cancelled'
                          ? 'red'
                          : props.row.status === 'Planned'
                            ? 'blue'
                            : 'green'
                      "
                      text-color="white"
                      size="sm"
                    >
                      {{ props.row.status }}
                    </q-chip>
                </template>
                  <template v-else-if="col.name === 'actions'">
                    <q-btn
                        icon="print"
                        color="primary"
                        unelevated
                        no-caps
                        dense
                        size="sm"
                        class="q-mr-xs"
                        @click="printPlan(props.row)"
                      >
                        <q-tooltip>Print Plan</q-tooltip>
                      </q-btn>
                    <q-btn
                        icon="history"
                        color="primary"
                        unelevated
                        no-caps
                        dense
                        size="sm"
                        class="q-mr-xs"
                        @click="showHistory(props.row)"
                      >
                        <q-tooltip>View History</q-tooltip>
                      </q-btn>
                    <q-btn
                        icon="cancel"
                        color="negative"
                        unelevated
                        no-caps
                        dense
                        size="sm"
                        @click="onCancelPlan(props.row)"
                        :disable="props.row.status === 'Cancelled'"
                      >
                        <q-tooltip>Cancel Plan</q-tooltip>
                      </q-btn>
                  </template>
                <template v-else>
                  {{ col.value }}
                </template>
              </q-td>
            </q-tr>
            <q-tr v-show="props.expand" :props="props">
              <q-td colspan="100%">
                <div class="q-pa-md">
                  <div class="text-subtitle2 q-mb-xs">Batch List</div>
                  <q-table
                    :rows="props.row.batches || []"
                    :columns="batchColumns"
                    row-key="id"
                    flat
                    bordered
                    dense
                    hide-bottom
                  >
                    <template v-slot:body-cell-flavour_house="bProps">
                      <q-td :props="bProps">
                        <q-checkbox
                          v-model="bProps.row.flavour_house"
                          disable
                          size="sm"
                        />
                      </q-td>
                    </template>
                    <template v-slot:body-cell-spp="bProps">
                      <q-td :props="bProps">
                        <q-checkbox
                          v-model="bProps.row.spp"
                          disable
                          size="sm"
                        />
                      </q-td>
                    </template>
                    <template v-slot:body-cell-batch_prepare="bProps">
                      <q-td :props="bProps">
                        <q-checkbox
                          v-model="bProps.row.batch_prepare"
                          disable
                          size="sm"
                        />
                      </q-td>
                    </template>
                    <template v-slot:body-cell-ready_to_product="bProps">
                      <q-td :props="bProps">
                        <q-checkbox
                          v-model="bProps.row.ready_to_product"
                          disable
                          size="sm"
                        />
                      </q-td>
                    </template>
                    <template v-slot:body-cell-production="bProps">
                      <q-td :props="bProps">
                        <q-checkbox
                          v-model="bProps.row.production"
                          disable
                          size="sm"
                        />
                      </q-td>
                    </template>
                    <template v-slot:body-cell-done="bProps">
                      <q-td :props="bProps">
                        <q-checkbox
                          v-model="bProps.row.done"
                          disable
                          size="sm"
                        />
                      </q-td>
                    </template>

                  </q-table>
                </div>
              </q-td>
            </q-tr>
          </template>
        </q-table>
      </q-card>

    </q-page>
  </RouterView>
</template>

<style scoped>
.text-magenta {
  color: #ff00ff;
}
.custom-table-border {
  border: 1px solid #777;
  border-radius: 8px;
}
</style>

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
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/plants/`)
    plantOptions.value = data.map((p: any) => ({
      label: p.plant_name,
      value: p.plant_id,
    }))
    data.forEach((p: any) => {
      plantConfigs.value[p.plant_id] = p.plant_capacity
      plantNames.value[p.plant_id] = p.plant_name
    })
    if (plantOptions.value.length > 0 && !plant.value) {
      plant.value = plantOptions.value[0]?.value || ''
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
    availableSkus.value = await $fetch<any[]>(`${appConfig.apiBaseUrl}/skus/`)
  } catch (error) {
    console.error('Error fetching SKUs:', error)
  }
}

const fetchPlans = async () => {
  try {
    plans.value = await $fetch<any[]>(`${appConfig.apiBaseUrl}/production-plans/?skip=0&limit=100`)
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

    await $fetch(`${appConfig.apiBaseUrl}/production-plans/`, {
      method: 'POST',
      body: payload,
    })

    $q.notify({ type: 'positive', message: 'Plan created successfully' })
    resetForm()
    fetchPlans()
  } catch (error: any) {
    console.error('Error creating plan:', error)
    $q.notify({ type: 'negative', message: error.data?.detail || 'Failed to create plan' })
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
      await $fetch(`${appConfig.apiBaseUrl}/production-plans/${plan.id}/cancel`, {
        method: 'POST',
        body: {
          comment: comment || null,
          changed_by: 'user'
        }
      })
      $q.notify({ type: 'positive', message: 'Plan cancelled successfully' })
      fetchPlans()
    } catch (e) {
      console.error(e)
      $q.notify({ type: 'negative', message: 'Network error while cancelling plan' })
    }
  })
}

const showHistory = async (plan: any) => {
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/production-plans/${plan.id}/history`)
    const historyText = data.length > 0 
      ? data.map((h: any) => {
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
  } catch (e) {
    console.error('Error loading history:', e)
    $q.notify({ type: 'negative', message: 'Failed to load history' })
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
      <!-- Header Section -->
      <div class="bg-blue-9 text-white q-pa-md rounded-borders q-mb-md shadow-2">
        <div class="row justify-between items-center">
          <div class="text-h6 text-weight-bolder">Production Plan List</div>
          <div class="text-caption text-weight-bold">Version 0.3</div>
        </div>
      </div>

      <!-- Create Plan Form (Top) -->
      <q-card flat bordered class="shadow-1 q-mb-md" id="create-plan-form">
        <q-card-section class="q-pa-sm bg-primary text-white row items-center justify-between">
          <div class="text-subtitle2 text-weight-bold">
            <q-icon name="add_circle" class="q-mr-xs" />
            Create New Production Plan
          </div>
          <q-btn
            label="Generate Plan"
            color="white"
            text-color="primary"
            unelevated
            no-caps
            :loading="isCreating"
            icon="playlist_add"
            size="sm"
            @click="onCreatePlan"
            class="text-weight-bold"
          />
        </q-card-section>

        <q-card-section class="q-pa-md bg-blue-grey-1">
          <!-- Form Row 1: SKU & Dates -->
          <div class="row q-col-gutter-md q-mb-md">
            <div class="col-12 col-md-3">
              <div class="text-caption text-weight-bold q-mb-xs">SKU-ID</div>
              <q-select
                outlined v-model="skuId" :options="filteredSkuIdOptions"
                dense bg-color="white" use-input input-debounce="0"
                @filter="onSkuIdFilter" emit-value map-options
                @update:model-value="onSkuIdSelect"
              />
            </div>
            <div class="col-12 col-md-5">
              <div class="text-caption text-weight-bold q-mb-xs">SKU Name</div>
              <q-select
                outlined v-model="skuName" :options="filteredSkuNameOptions"
                dense bg-color="white" use-input input-debounce="0"
                @filter="onSkuNameFilter" emit-value map-options
                @update:model-value="onSkuNameSelect"
              />
            </div>
            <div class="col-6 col-md-2">
              <div class="text-caption text-weight-bold q-mb-xs">Start Date</div>
              <q-input outlined v-model="startDate" dense bg-color="white" type="date" />
            </div>
            <div class="col-6 col-md-2">
              <div class="text-caption text-weight-bold q-mb-xs">Finish Date</div>
              <q-input outlined v-model="finishDate" dense bg-color="white" type="date" />
            </div>
          </div>

          <!-- Form Row 2: Plant, Volume & Batches -->
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-3">
              <div class="text-caption text-weight-bold q-mb-xs">Plant</div>
              <q-select
                outlined v-model="plant" :options="plantOptions"
                dense bg-color="white" emit-value map-options
              >
                <template v-slot:append>
                  <q-btn icon="settings" flat round dense size="sm" color="primary" @click="$router.push({ name: 'PlantConfig' })" />
                </template>
              </q-select>
            </div>
            <div class="col-6 col-md-2">
              <div class="text-caption text-weight-bold q-mb-xs">Require Vol (kg)</div>
              <q-input outlined v-model="productionRequire" type="number" dense bg-color="white" input-class="text-right" />
            </div>
            <div class="col-6 col-md-2">
              <div class="text-caption text-weight-bold q-mb-xs">Batch Standard</div>
              <q-input outlined v-model="batchStandard" type="number" dense bg-color="white" input-class="text-right" />
            </div>
            <div class="col-6 col-md-2">
              <div class="text-caption text-weight-bold q-mb-xs">Total Plan Vol</div>
              <q-input outlined :model-value="totalPlanVolume" readonly dense bg-color="grey-2" input-class="text-right text-weight-bold" />
            </div>
            <div class="col-6 col-md-1">
              <div class="text-caption text-weight-bold q-mb-xs">No. of Batches</div>
              <q-input outlined v-model="numberOfBatch" type="number" dense bg-color="white" @update:model-value="onManualBatchChange" input-class="text-center" />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Plans Master (Full Width Below) -->
      <div class="row items-center justify-between q-mb-xs">
        <div class="text-subtitle2 text-weight-bold">Plans Master</div>
        <div class="row items-center q-gutter-x-xs">
          <q-btn icon="refresh" flat round dense color="primary" @click="fetchPlans" size="sm" />
          <q-btn icon="print" flat round dense color="primary" @click="printAllPlans" size="sm">
            <q-tooltip>Print All Plans</q-tooltip>
          </q-btn>
          <q-checkbox v-model="showAll" label="Show All" dense class="text-caption" />
        </div>
      </div>

      <q-card flat bordered class="shadow-1 overflow-hidden" style="border-radius: 8px;">
        <q-table
          :rows="filteredPlans"
          :columns="columns"
          row-key="id"
          flat
          dense
          class="text-caption sticky-header-table"
          :pagination="{ rowsPerPage: 0 }"
          hide-bottom
          style="max-height: calc(100vh - 380px);"
        >
          <template v-slot:header="props">
            <q-tr :props="props" class="bg-blue-grey-2">
              <q-th auto-width />
              <q-th
                v-for="col in props.cols"
                :key="col.name"
                :props="props"
                class="text-weight-bold"
              >
                {{ col.label }}
              </q-th>
            </q-tr>
          </template>

          <template v-slot:body="props">
            <q-tr :props="props" class="cursor-pointer hover-bg" @click="props.expand = !props.expand">
              <q-td auto-width>
                <q-btn
                  size="xs"
                  color="primary"
                  round
                  flat
                  dense
                  @click.stop="props.expand = !props.expand"
                  :icon="props.expand ? 'keyboard_arrow_up' : 'keyboard_arrow_down'"
                />
              </q-td>
              <q-td v-for="col in props.cols" :key="col.name" :props="props">
                <template v-if="col.name === 'plant'">
                  <span class="text-weight-medium">{{ plantNames[props.row.plant] || props.row.plant }}</span>
                </template>
                <template v-else-if="col.name === 'status'">
                   <q-badge
                      :color="
                        props.row.status === 'Cancelled'
                          ? 'red'
                          : props.row.status === 'Planned'
                            ? 'blue'
                            : 'green'
                      "
                      text-color="white"
                      class="text-weight-bold"
                    >
                      {{ props.row.status }}
                    </q-badge>
                </template>
                <template v-else-if="col.name === 'plan_id'">
                  <span class="text-weight-bolder text-blue-9">{{ props.row.plan_id }}</span>
                </template>
                <template v-else-if="col.name === 'total_volume'">
                  <span class="text-weight-bold">{{ props.row.total_volume }}</span>
                </template>
                <template v-else-if="col.name === 'actions'">
                    <q-btn icon="more_vert" flat round dense size="sm" color="grey-7">
                        <q-menu auto-close>
                            <q-list style="min-width: 150px">
                                <q-item clickable @click="printPlan(props.row)">
                                    <q-item-section avatar><q-icon name="print" color="primary" /></q-item-section>
                                    <q-item-section>Print Plan</q-item-section>
                                </q-item>
                                <q-item clickable @click="showHistory(props.row)">
                                    <q-item-section avatar><q-icon name="history" color="primary" /></q-item-section>
                                    <q-item-section>View History</q-item-section>
                                </q-item>
                                <q-separator />
                                <q-item clickable @click="onCancelPlan(props.row)" :disable="props.row.status === 'Cancelled'">
                                    <q-item-section avatar><q-icon name="cancel" color="negative" /></q-item-section>
                                    <q-item-section class="text-negative">Cancel Plan</q-item-section>
                                </q-item>
                            </q-list>
                        </q-menu>
                    </q-btn>
                </template>
                <template v-else>
                  {{ col.value }}
                </template>
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

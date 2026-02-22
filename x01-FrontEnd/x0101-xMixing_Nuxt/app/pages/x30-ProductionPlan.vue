<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { RouterView } from 'vue-router'
import { appConfig } from '~/appConfig/config'

const $q = useQuasar()
const { t } = useI18n()
const { generateQrDataUrl } = useQrCode()

const formatDate = (date: any) => {
  if (!date) return '-'
  const d = new Date(date)
  if (isNaN(d.getTime())) return date
  return d.toLocaleDateString('en-GB')
}

const formatDateTime = (date: any) => {
  if (!date) return '-'
  const d = new Date(date)
  if (isNaN(d.getTime())) return date
  return d.toLocaleString('en-GB')
}

const formatDateForInput = (date: any) => {
  if (!date) return ''
  const d = new Date(date)
  if (isNaN(d.getTime())) return ''
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  return `${day}/${month}/${year}`
}

const parseInputDate = (val: string | null | undefined) => {
  if (!val || val === '--/--/----') return null
  const parts = val.split('/')
  if (parts.length === 3 && parts[0] && parts[1] && parts[2]) {
    const day = parseInt(parts[0])
    const month = parseInt(parts[1]) - 1
    const year = parseInt(parts[2])
    const d = new Date(year, month, day)
    return isNaN(d.getTime()) ? null : d
  }
  const d = new Date(val)
  return isNaN(d.getTime()) ? null : d
}

const formatDateToApi = (val: string | null | undefined) => {
  if (!val || val === '--/--/----') return null
  const parts = val.split('/')
  if (parts.length === 3 && parts[0] && parts[1] && parts[2]) {
    const day = parts[0].padStart(2, '0')
    const month = parts[1].padStart(2, '0')
    const year = parts[2]
    return `${year}-${month}-${day}`
  }
  // Try fallback for other formats
  const d = new Date(val)
  if (isNaN(d.getTime())) return null
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const da = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${da}`
}

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
const startDate = ref(formatDateForInput(new Date()))
const finishDate = ref(formatDateForInput(new Date()))

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
const columns = computed<QTableColumn[]>(() => [
  { name: 'id', label: t('prodPlan.id'), field: 'id', align: 'left', sortable: true },
  { name: 'plan_id', label: t('prodPlan.planId'), field: 'plan_id', align: 'left', sortable: true },
  { name: 'sku_id', label: t('prodPlan.skuId'), field: 'sku_id', align: 'left', sortable: true },
  { name: 'plant', label: t('prodPlan.plant'), field: 'plant', align: 'left', sortable: true },
  {
    name: 'total_volume',
    label: t('prodPlan.totalVol'),
    field: 'total_volume',
    align: 'right',
    sortable: true,
  },
  {
    name: 'total_plan_volume',
    label: t('prodPlan.totalPlanVol'),
    field: 'total_plan_volume',
    align: 'right',
    sortable: true,
  },
  { name: 'start_date', label: t('prodPlan.startDate'), field: 'start_date', align: 'center', sortable: true, format: (val: any) => formatDate(val) },
  { name: 'finish_date', label: t('prodPlan.finishDate'), field: 'finish_date', align: 'center', sortable: true, format: (val: any) => formatDate(val) },
  { name: 'flavour_house', label: t('prodPlan.flavourHouse'), field: 'flavour_house', align: 'center' },
  { name: 'spp', label: t('prodPlan.spp'), field: 'spp', align: 'center' },
  { name: 'batch_prepare', label: t('prodPlan.batchPrepare'), field: 'batch_prepare', align: 'center' },
  { name: 'ready_to_product', label: t('prodPlan.readyToProd'), field: 'ready_to_product', align: 'center' },
  { name: 'production', label: t('prodPlan.production'), field: 'production', align: 'center' },
  { name: 'done', label: t('prodPlan.done'), field: 'done', align: 'center' },
  { name: 'status', label: t('common.status'), field: 'status', align: 'center', sortable: true },
  { name: 'actions', label: t('common.actions'), field: 'actions', align: 'center' },
])

// Batch Columns
const batchColumns = computed<QTableColumn[]>(() => [
  { name: 'batch_id', label: t('prodPlan.batchId'), field: 'batch_id', align: 'left', sortable: true },
  { name: 'batch_size', label: t('prodPlan.batchSize'), field: 'batch_size', align: 'right', sortable: true },
  { name: 'flavour_house', label: t('prodPlan.flavourHouse'), field: 'flavour_house', align: 'center' },
  { name: 'spp', label: t('prodPlan.spp'), field: 'spp', align: 'center' },
  { name: 'batch_prepare', label: t('prodPlan.batchPrepare'), field: 'batch_prepare', align: 'center' },
  { name: 'ready_to_product', label: t('prodPlan.readyToProd'), field: 'ready_to_product', align: 'center' },
  { name: 'production', label: t('prodPlan.production'), field: 'production', align: 'center' },
  { name: 'done', label: t('prodPlan.done'), field: 'done', align: 'center' },
  { name: 'actions', label: t('common.actions'), field: 'actions', align: 'center' },
])
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

const resetForm = () => {
  skuId.value = ''
  skuName.value = ''
  plant.value = plantOptions.value.length > 0 ? (plantOptions.value[0]?.value || '') : ''
  productionRequire.value = null
  batchStandard.value = null
  numberOfBatch.value = 0
  startDate.value = formatDateForInput(new Date())
  finishDate.value = formatDateForInput(new Date())
}

const onCreatePlan = async () => {
  if (!skuId.value || !plant.value || !productionRequire.value || !numberOfBatch.value) {
    $q.notify({ type: 'warning', message: t('prodPlan.fillAllFields') })
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
      start_date: formatDateToApi(startDate.value),
      finish_date: formatDateToApi(finishDate.value),
    }

    await $fetch(`${appConfig.apiBaseUrl}/production-plans/`, {
      method: 'POST',
      body: payload,
    })

    $q.notify({ type: 'positive', message: t('prodPlan.createdSuccess') })
    resetForm()
    fetchPlans()
  } catch (error: any) {
    console.error('Error creating plan:', error)
    $q.notify({ type: 'negative', message: error.data?.detail || t('prodPlan.failedCreate') })
  } finally {
    isCreating.value = false
  }
}


// Cancel reason options
const cancelReasonOptions = [
  'Plan Change',
  'Customer Request',
  'Quality Issue',
  'Material Shortage',
  'Equipment Failure',
  'Schedule Conflict',
  'Duplicate Plan',
  'Other'
]

const showCancelDialog = ref(false)
const cancelPlanTarget = ref<any>(null)
const cancelReason = ref('')
const cancelCustomReason = ref('')

const onCancelPlan = (plan: any) => {
  cancelPlanTarget.value = plan
  cancelReason.value = ''
  cancelCustomReason.value = ''
  showCancelDialog.value = true
}

const confirmCancelPlan = async () => {
  const plan = cancelPlanTarget.value
  if (!plan) return

  const comment = cancelReason.value === 'Other'
    ? cancelCustomReason.value || 'Other'
    : cancelReason.value || null

  try {
    await $fetch(`${appConfig.apiBaseUrl}/production-plans/${plan.id}`, {
      method: 'DELETE',
      body: {
        comment,
        changed_by: 'user'
      }
    })
    $q.notify({ type: 'positive', message: t('prodPlan.cancelSuccess') })
    showCancelDialog.value = false
    fetchPlans()
  } catch (e) {
    console.error(e)
    $q.notify({ type: 'negative', message: t('prodPlan.networkErrorCancel') })
  }
}

const showHistory = async (plan: any) => {
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/production-plans/${plan.id}/history`)
    const historyText = data.length > 0 
      ? data.map((h: any) => {
          const date = new Date(h.changed_at).toLocaleString('en-GB')
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
      : `<p>${t('prodPlan.noHistory')}</p>`
    
    $q.dialog({
      title: t('prodPlan.historyTitle', { id: plan.plan_id }),
      message: historyText,
      html: true,
      style: 'max-width: 600px'
    })
  } catch (e) {
    console.error('Error loading history:', e)
    $q.notify({ type: 'negative', message: t('common.error') })
  }
}

const printBatchLabel = async (plan: any, batch: any) => {
  const existingIframe = document.getElementById('print-iframe')
  if (existingIframe) {
    document.body.removeChild(existingIframe)
  }

  const iframe = document.createElement('iframe')
  iframe.id = 'print-iframe'
  iframe.style.position = 'fixed'
  iframe.style.right = '0'
  iframe.style.bottom = '0'
  iframe.style.width = '1px'
  iframe.style.height = '1px'
  iframe.style.border = '0'
  iframe.style.opacity = '0.01'
  document.body.appendChild(iframe)

  try {
    const templateResponse = await fetch('/labels/BatchPlan-Label.svg')
    const templateStr = await templateResponse.text()

    // Determine batch index from the batch_id string (e.g. plan-Line-1-2026-02-23-001-003 -> 3)
    const batchIndex = batch.batch_id ? parseInt(batch.batch_id.split('-').pop() || '1', 10) : 1
    const totalBatches = plan.num_batches || plan.batches?.length || 1

    const qrLarge = await generateQrDataUrl(batch.batch_id, 150)

    const plantName = plantNames.value[plan.plant] || plan.plant || '-'

    let formattedSvg = templateStr
      .replace(/\{\{PlanId\}\}/g, plan.plan_id || '-')
      .replace(/\{\{BatchId\}\}/g, batch.batch_id || '-')
      .replace(/\{\{SKU\}\}/g, `${plan.sku_id}${plan.sku_name ? ' - ' + plan.sku_name : ''}`)
      .replace(/\{\{BatchNo\}\}/g, `${batchIndex} / ${totalBatches}`)
      .replace(/\{\{PlanStartDate\}\}/g, plan.start_date || '-')
      .replace(/\{\{PlanFinishDate\}\}/g, plan.finish_date || '-')
      .replace(/\{\{BatchSize\}\}/g, batch.batch_size?.toString() || '0')
      .replace(/\{\{PlanSize\}\}/g, plan.total_plan_volume?.toString() || '0')
      .replace(/\{\{PlantId\}\}/g, plan.plant || '-')
      .replace(/\{\{PlantName\}\}/g, plantName)
      .replace(/\{\{Timestamp\}\}/g, new Date().toLocaleString('en-GB'))
      .replace(/\{\{QRCode\}\}/g, `<image href="${qrLarge}" x="0" y="0" width="100" height="100" />`)

    const html = `
      <html>
        <head>
          <title>Print Label - ${batch.batch_id}</title>
          <style>
            @page {
              size: 4in 6in;
              margin: 0;
            }
            body {
              margin: 0;
              padding: 0;
              background: white;
              box-sizing: border-box;
            }
            .label-container {
              width: 4in;
              height: 6in;
              display: flex;
              justify-content: center;
              align-items: center;
            }
            .label-container svg {
              width: 100%;
              height: 100%;
            }
          </style>
        </head>
        <body>
          <div class="label-container">${formattedSvg}</div>
        </body>
      </html>
    `

    const doc = iframe.contentWindow?.document
    if (doc) {
      doc.open()
      doc.write(html)
      doc.close()
      iframe.onload = () => {
        iframe.contentWindow?.focus()
        iframe.contentWindow?.print()
      }
    }
  } catch (error) {
    console.error('Failed to print batch label:', error)
    $q.notify({ type: 'negative', message: 'Failed to generate label' })
  }
}

const printAllBatchLabels = async (plan: any) => {
  const batches = plan.batches
  if (!batches || batches.length === 0) {
    $q.notify({ type: 'warning', message: 'No batches to print' })
    return
  }

  const existingIframe = document.getElementById('print-iframe')
  if (existingIframe) {
    document.body.removeChild(existingIframe)
  }

  const iframe = document.createElement('iframe')
  iframe.id = 'print-iframe'
  iframe.style.position = 'fixed'
  iframe.style.right = '0'
  iframe.style.bottom = '0'
  iframe.style.width = '1px'
  iframe.style.height = '1px'
  iframe.style.border = '0'
  iframe.style.opacity = '0.01'
  document.body.appendChild(iframe)

  try {
    const templateResponse = await fetch('/labels/BatchPlan-Label.svg')
    const templateStr = await templateResponse.text()
    const plantName = plantNames.value[plan.plant] || plan.plant || '-'
    const totalBatches = plan.num_batches || batches.length || 1

    let labelsHtml = ''

    for (let i = 0; i < batches.length; i++) {
      const batch = batches[i]
      const batchIndex = batch.batch_id ? parseInt(batch.batch_id.split('-').pop() || '1', 10) : (i + 1)

      const qrLarge = await generateQrDataUrl(batch.batch_id, 150)

      const svgContent = templateStr
        .replace(/\{\{PlanId\}\}/g, plan.plan_id || '-')
        .replace(/\{\{BatchId\}\}/g, batch.batch_id || '-')
        .replace(/\{\{SKU\}\}/g, `${plan.sku_id}${plan.sku_name ? ' - ' + plan.sku_name : ''}`)
        .replace(/\{\{BatchNo\}\}/g, `${batchIndex} / ${totalBatches}`)
        .replace(/\{\{PlanStartDate\}\}/g, plan.start_date || '-')
        .replace(/\{\{PlanFinishDate\}\}/g, plan.finish_date || '-')
        .replace(/\{\{BatchSize\}\}/g, batch.batch_size?.toString() || '0')
        .replace(/\{\{PlanSize\}\}/g, plan.total_plan_volume?.toString() || '0')
        .replace(/\{\{PlantId\}\}/g, plan.plant || '-')
        .replace(/\{\{PlantName\}\}/g, plantName)
        .replace(/\{\{Timestamp\}\}/g, new Date().toLocaleString('en-GB'))
        .replace(/\{\{QRCode\}\}/g, `<image href="${qrLarge}" x="0" y="0" width="100" height="100" />`)

      labelsHtml += `<div class="label-container">${svgContent}</div>`
    }

    const html = `
      <html>
        <head>
          <title>Batch Labels - ${plan.plan_id}</title>
          <style>
            @page { size: 4in 6in; margin: 0; }
            body { margin: 0; padding: 0; background: white; }
            .label-container {
              width: 4in; height: 6in;
              page-break-after: always;
              display: flex; justify-content: center; align-items: center;
            }
            .label-container svg { width: 100%; height: 100%; }
          </style>
        </head>
        <body>${labelsHtml}</body>
      </html>
    `

    const doc = iframe.contentWindow?.document
    if (doc) {
      doc.open()
      doc.write(html)
      doc.close()
      iframe.onload = () => {
        iframe.contentWindow?.focus()
        iframe.contentWindow?.print()
      }
    }
  } catch (error) {
    console.error('Failed to print all batch labels:', error)
    $q.notify({ type: 'negative', message: 'Failed to generate labels' })
  }
}

// Expand / Collapse All
const expandedRows = ref<any[]>([])

const expandAll = () => {
  expandedRows.value = filteredPlans.value.map((p: any) => p.id)
}

const collapseAll = () => {
  expandedRows.value = []
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
        <h1 style="text-align: center; color: #1976d2; border-bottom: 2px solid #1976d2; padding-bottom: 10px;">${t('prodPlan.summaryReportTitle')}</h1>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
          <tr><th style="width: 40%; background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">${t('prodPlan.planId')}</th><td style="border: 1px solid #ddd; padding: 12px;">${plan.plan_id}</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">${t('prodPlan.skuId')}</th><td style="border: 1px solid #ddd; padding: 12px;">${plan.sku_id}</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">${t('prodPlan.skuName')}</th><td style="border: 1px solid #ddd; padding: 12px;">${plan.sku_name || '—'}</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">${t('prodPlan.plant')}</th><td style="border: 1px solid #ddd; padding: 12px;">${plantNames.value[plan.plant] || plan.plant}</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">${t('prodPlan.totalPlanVol')}</th><td style="border: 1px solid #ddd; padding: 12px;">${plan.total_plan_volume || '0'} kg</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">${t('prodPlan.numBatches')}</th><td style="border: 1px solid #ddd; padding: 12px;">${plan.num_batches || 0}</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">${t('prodPlan.batchSize')}</th><td style="border: 1px solid #ddd; padding: 12px;">${plan.batch_size || '—'} kg</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">${t('prodPlan.startDate')} - ${t('prodPlan.finishDate')}</th><td style="border: 1px solid #ddd; padding: 12px;">${formatDate(plan.start_date)} to ${formatDate(plan.finish_date)}</td></tr>
          <tr><th style="background: #f5f5f5; border: 1px solid #ddd; padding: 12px; text-align: left;">${t('common.status')}</th><td style="border: 1px solid #ddd; padding: 12px;"><strong>${plan.status}</strong></td></tr>
        </table>
        
        <div style="margin-top: 40px; background: #f9f9f9; padding: 20px; border-radius: 8px; border-left: 5px solid #1976d2;">
          <h2 style="margin-top: 0; font-size: 16px;">${t('prodPlan.creationDetails')}</h2>
          <p><strong>Created:</strong> ${formatDateTime(plan.created_at)}</p>
          <p><strong>Created By:</strong> ${plan.created_by || '—'}</p>
          ${plan.updated_by ? '<p><strong>Last Updated By:</strong> ' + plan.updated_by + '</p>' : ''}
        </div>
      </div>
      
      <div>
        <h2 style="color: #1976d2; border-bottom: 2px solid #1976d2; padding-bottom: 10px;">${t('prodPlan.batchDetails')}</h2>
        <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
          <thead>
            <tr>
              <th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5;">#</th>
              <th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5;">${t('prodPlan.batchId')}</th>
              <th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5;">${t('prodPlan.batchSize')} (kg)</th>
              <th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5;">${t('common.status')}</th>
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
        <td style="border: 1px solid #ddd; padding: 4px; font-size: 10px;">${batch.batch_size || '—'}</td>
        <td style="border: 1px solid #ddd; padding: 4px; font-size: 10px;">${batch.status}</td>
      </tr>
    `).join('') || `<tr><td colspan="4" style="text-align: center; padding: 8px; font-size: 10px;">${t('common.noData')}</td></tr>`
    
    return `
      <!-- Page 1: Plan Summary -->
      <div style="page-break-after: always; margin-bottom: 20px;">
        <h2 style="font-size: 16px; margin-bottom: 15px; color: #1976d2; border-bottom: 1px solid #1976d2; padding-bottom: 5px;">
          ${plan.plan_id} - ${t('common.details')}
        </h2>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 11px;">
          <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f2f2f2; width: 35%;">SKU</th><td style="border: 1px solid #ddd; padding: 8px;">${plan.sku_id} - ${plan.sku_name || ''}</td></tr>
          <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f2f2f2;">${t('prodPlan.plant')}</th><td style="border: 1px solid #ddd; padding: 8px;">${plantNames.value[plan.plant] || plan.plant}</td></tr>
          <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f2f2f2;">${t('prodPlan.totalPlanVol')}</th><td style="border: 1px solid #ddd; padding: 8px;">${plan.total_plan_volume || '—'} kg</td></tr>
          <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f2f2f2;">${t('prodPlan.numBatches')}</th><td style="border: 1px solid #ddd; padding: 8px;">${plan.num_batches || 0}</td></tr>
          <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f2f2f2;">${t('prodPlan.startDate')} - ${t('prodPlan.finishDate')}</th><td style="border: 1px solid #ddd; padding: 8px;">${formatDate(plan.start_date)} to ${formatDate(plan.finish_date)}</td></tr>
          <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f2f2f2;">${t('common.status')}</th><td style="border: 1px solid #ddd; padding: 8px;"><strong>${plan.status}</strong></td></tr>
        </table>
        
        <div style="margin-top: 30px; background: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 5px solid #1976d2;">
          <h3 style="margin-top: 0; font-size: 12px;">${t('prodPlan.creationDetails')}</h3>
          <p style="margin: 5px 0;"><strong>Created:</strong> ${formatDateTime(plan.created_at)}</p>
          <p style="margin: 5px 0;"><strong>Created By:</strong> ${plan.created_by || '—'}</p>
          ${plan.updated_by ? `<p style="margin: 5px 0;"><strong>Last Updated By:</strong> ${plan.updated_by}</p>` : ''}
        </div>
      </div>

      <!-- Page 2: Batch Details -->
      <div style="page-break-after: always; margin-bottom: 20px;">
        <h2 style="font-size: 16px; margin-bottom: 15px; color: #1976d2; border-bottom: 1px solid #1976d2; padding-bottom: 5px;">
          ${plan.plan_id} - ${t('prodPlan.batchDetails')}
        </h2>
        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr>
              <th style="border: 1px solid #ddd; padding: 6px; background: #f2f2f2; font-size: 11px;">#</th>
              <th style="border: 1px solid #ddd; padding: 6px; background: #f2f2f2; font-size: 11px;">${t('prodPlan.batchId')}</th>
              <th style="border: 1px solid #ddd; padding: 6px; background: #f2f2f2; font-size: 11px;">${t('prodPlan.batchSize')} (kg)</th>
              <th style="border: 1px solid #ddd; padding: 6px; background: #f2f2f2; font-size: 11px;">${t('common.status')}</th>
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
  
  // Breakdown calculations remain same
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
        ${t('prodPlan.summaryReportTitle')}
      </h1>
      
      <div style="background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
        <h2 style="margin: 0 0 15px 0; font-size: 18px;">${t('prodPlan.overallStats')}</h2>
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
        <h2 style="font-size: 14px; border-left: 4px solid #1976d2; padding-left: 8px; margin-bottom: 10px;">${t('prodPlan.statusBreakdown')}</h2>
        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
          <thead>
            <tr><th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5; text-align: left;">${t('common.status')}</th><th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5; text-align: right;">Count</th></tr>
          </thead>
          <tbody>${statusRows}</tbody>
        </table>
      </div>
      
      <div>
        <h2 style="font-size: 14px; border-left: 4px solid #1976d2; padding-left: 8px; margin-bottom: 10px;">${t('prodPlan.plantDist')}</h2>
        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
          <thead>
            <tr>
              <th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5; text-align: left;">${t('prodPlan.plant')}</th>
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
      <title>${t('prodPlan.title')}</title>
      <style>
        @page { size: A4; margin: 15mm; }
        body { font-family: Arial, sans-serif; }
        h1 { font-size: 16px; margin-bottom: 15px; }
        table { border-collapse: collapse; }
      </style>
    </head>
    <body>
      ${summaryPage}
      <h1 style="text-align: center; border-bottom: 1px solid #eee; padding-bottom: 10px;">${t('prodPlan.title')}</h1>
      ${plansHTML}
      <script>
        window.onload = () => {
          window.print();
          window.onafterprint = () => window.close();
        };
      </scr` + `ipt>
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

// Styling Helper
const getStatusColor = (status: string) => {
  if (status === 'Hold') return 'text-magenta'
  return 'text-blue-8'
}

const getPlanIngredients = (plan: any) => {
  if (!plan.batches || plan.batches.length === 0) return []
  const ingredientsMap: Record<string, any> = {}
  
  plan.batches.forEach((b: any) => {
     if(b.reqs) {
        b.reqs.forEach((req: any) => {
           if (!ingredientsMap[req.re_code]) {
               ingredientsMap[req.re_code] = {
                   re_code: req.re_code,
                   name: req.ingredient_name || req.re_code,
                   wh: req.wh || '-',
                   vol_per_batch: req.required_volume || 0,
                   total_vol: 0
               }
           }
           ingredientsMap[req.re_code].total_vol += (req.required_volume || 0)
        })
     }
  })

  // Provide deterministic sorting by re_code
  return Object.values(ingredientsMap).sort((a, b) => a.re_code.localeCompare(b.re_code))
}

const ingredientColumns = computed<QTableColumn[]>(() => [
  { name: 're_code', label: t('prodPlan.ingredientCode'), field: 're_code', align: 'left', sortable: true },
  { name: 'name', label: t('prodPlan.ingredientName'), field: 'name', align: 'left', sortable: true },
  { name: 'wh', label: 'Warehouse', field: 'wh', align: 'center', sortable: true },
  { name: 'vol_per_batch', label: t('prodPlan.volPerBatch'), field: 'vol_per_batch', align: 'right', sortable: true, format: val => val?.toFixed(2) },
  { name: 'total_vol', label: t('prodPlan.totalVol'), field: 'total_vol', align: 'right', sortable: true, format: val => val?.toFixed(2) },
])

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
          <div class="row items-center q-gutter-sm">
            <q-icon name="account_tree" size="sm" />
            <div class="text-h6 text-weight-bolder">{{ t('prodPlan.title') }}</div>
          </div>
          <div class="text-caption text-weight-bold text-blue-2">{{ t('prodPlan.version') }} 0.3</div>
        </div>
      </div>

      <!-- Create Plan Form (Top) -->
      <q-card flat bordered class="shadow-1 q-mb-md" id="create-plan-form">
        <q-card-section class="q-pa-sm bg-primary text-white row items-center justify-between">
          <div class="text-subtitle2 text-weight-bold">
            <q-icon name="add_circle" class="q-mr-xs" />
            {{ t('prodPlan.createNew') }}
          </div>
          <q-btn
            :label="t('prodPlan.generatePlan')"
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
              <div class="text-caption text-weight-bold q-mb-xs">{{ t('prodPlan.skuId') }}</div>
              <q-select
                outlined v-model="skuId" :options="filteredSkuIdOptions"
                dense bg-color="white" use-input input-debounce="0"
                @filter="onSkuIdFilter" emit-value map-options
                @update:model-value="onSkuIdSelect"
              />
            </div>
            <div class="col-12 col-md-5">
              <div class="text-caption text-weight-bold q-mb-xs">{{ t('prodPlan.skuName') }}</div>
              <q-select
                outlined v-model="skuName" :options="filteredSkuNameOptions"
                dense bg-color="white" use-input input-debounce="0"
                @filter="onSkuNameFilter" emit-value map-options
                @update:model-value="onSkuNameSelect"
              />
            </div>
            <div class="col-6 col-md-2">
              <div class="text-caption text-weight-bold q-mb-xs">{{ t('prodPlan.startDate') }}</div>
              <q-input outlined v-model="startDate" dense bg-color="white" mask="##/##/####" placeholder="DD/MM/YYYY">
                <template v-slot:append>
                  <q-icon name="event" class="cursor-pointer">
                    <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                      <q-date v-model="startDate" mask="DD/MM/YYYY">
                        <div class="row items-center justify-end">
                          <q-btn v-close-popup :label="t('common.close')" color="primary" flat />
                        </div>
                      </q-date>
                    </q-popup-proxy>
                  </q-icon>
                </template>
              </q-input>
            </div>
            <div class="col-6 col-md-2">
              <div class="text-caption text-weight-bold q-mb-xs">{{ t('prodPlan.finishDate') }}</div>
              <q-input outlined v-model="finishDate" dense bg-color="white" mask="##/##/####" placeholder="DD/MM/YYYY">
                <template v-slot:append>
                  <q-icon name="event" class="cursor-pointer">
                    <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                      <q-date v-model="finishDate" mask="DD/MM/YYYY">
                        <div class="row items-center justify-end">
                          <q-btn v-close-popup :label="t('common.close')" color="primary" flat />
                        </div>
                      </q-date>
                    </q-popup-proxy>
                  </q-icon>
                </template>
              </q-input>
            </div>
          </div>

          <!-- Form Row 2: Plant, Volume & Batches -->
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-3">
              <div class="text-caption text-weight-bold q-mb-xs">{{ t('prodPlan.plant') }}</div>
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
              <div class="text-caption text-weight-bold q-mb-xs">{{ t('prodPlan.requireVol') }}</div>
              <q-input outlined v-model="productionRequire" type="number" dense bg-color="white" input-class="text-right" />
            </div>
            <div class="col-6 col-md-2">
              <div class="text-caption text-weight-bold q-mb-xs">{{ t('prodPlan.batchStandard') }}</div>
              <q-input outlined v-model="batchStandard" type="number" dense bg-color="white" input-class="text-right" />
            </div>
            <div class="col-6 col-md-2">
              <div class="text-caption text-weight-bold q-mb-xs">{{ t('prodPlan.totalPlanVol') }}</div>
              <q-input outlined :model-value="totalPlanVolume" readonly dense bg-color="grey-2" input-class="text-right text-weight-bold" />
            </div>
            <div class="col-6 col-md-1">
              <div class="text-caption text-weight-bold q-mb-xs">{{ t('prodPlan.numBatches') }}</div>
              <q-input outlined v-model="numberOfBatch" type="number" dense bg-color="white" @update:model-value="onManualBatchChange" input-class="text-center" />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Plans Master (Full Width Below) -->
      <div class="row items-center justify-between q-mb-xs">
        <div class="text-subtitle2 text-weight-bold">{{ t('prodPlan.plansMaster') }}</div>
        <div class="row items-center q-gutter-x-xs">
          <q-btn icon="unfold_more" flat round dense color="primary" size="sm" @click="expandAll">
            <q-tooltip>Expand All</q-tooltip>
          </q-btn>
          <q-btn icon="unfold_less" flat round dense color="primary" size="sm" @click="collapseAll">
            <q-tooltip>Collapse All</q-tooltip>
          </q-btn>
          <q-separator vertical inset />
          <q-btn icon="refresh" flat round dense color="primary" @click="fetchPlans" size="sm" />
          <q-btn icon="print" flat round dense color="primary" @click="printAllPlans" size="sm">
            <q-tooltip>{{ t('prodPlan.printAllPlans') }}</q-tooltip>
          </q-btn>
          <q-checkbox v-model="showAll" :label="t('prodPlan.showAll')" dense class="text-caption" />
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
          style="max-height: 320px;"
          v-model:expanded="expandedRows"
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
                  size="sm"
                  color="primary"
                  round
                  flat
                  dense
                  @click.stop="props.expand = !props.expand"
                  :icon="props.expand ? 'keyboard_arrow_down' : 'keyboard_arrow_right'"
                />
              </q-td>
              <q-td v-for="col in props.cols" :key="col.name" :props="props">
                <template v-if="['flavour_house', 'spp', 'batch_prepare', 'ready_to_product', 'production', 'done'].includes(col.name)">
                  <q-icon v-if="col.value" name="check_circle" color="positive" size="sm" />
                  <q-icon v-else name="cancel" color="grey-4" size="sm" />
                </template>
                <template v-else-if="col.name === 'plant'">
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
                    <div class="row no-wrap items-center">
                      <q-btn
                        flat round dense size="sm" color="blue-7"
                        @click.stop="printAllBatchLabels(props.row)"
                      >
                        <q-tooltip>Print All Batch Labels</q-tooltip>
                        <q-icon name="layers" />
                      </q-btn>
                      <q-btn icon="more_vert" flat round dense size="sm" color="grey-7" @click.stop>
                        <q-menu auto-close>
                            <q-list style="min-width: 150px">
                                <q-item clickable @click="printPlan(props.row)">
                                    <q-item-section avatar><q-icon name="print" color="primary" /></q-item-section>
                                    <q-item-section>{{ t('prodPlan.printPlan') }}</q-item-section>
                                </q-item>
                                <q-item clickable @click="showHistory(props.row)">
                                    <q-item-section avatar><q-icon name="history" color="primary" /></q-item-section>
                                    <q-item-section>{{ t('prodPlan.viewHistory') }}</q-item-section>
                                </q-item>
                                <q-separator />
                                <q-item clickable @click="onCancelPlan(props.row)" :disable="props.row.status === 'Cancelled'">
                                    <q-item-section avatar><q-icon name="cancel" color="negative" /></q-item-section>
                                    <q-item-section class="text-negative">{{ t('prodPlan.cancelPlan') }}</q-item-section>
                                </q-item>
                            </q-list>
                        </q-menu>
                      </q-btn>
                    </div>
                </template>
                <template v-else>
                  {{ col.value }}
                </template>
              </q-td>
            </q-tr>
            
            <!-- Expanded Row for Batches -->
            <q-tr v-show="props.expand" :props="props" class="bg-blue-grey-1">
              <q-td colspan="100%" class="q-pa-md">
                <div class="row q-col-gutter-lg">
                  <!-- Ingredients List -->
                  <div class="col-12 col-md-5">
                    <div class="text-subtitle2 q-mb-sm text-blue-9">{{ t('prodPlan.ingredientRequirement') }}</div>
                    <q-table
                      :rows="getPlanIngredients(props.row)"
                      :columns="ingredientColumns"
                      row-key="re_code"
                      flat
                      dense
                      hide-bottom
                      :pagination="{ rowsPerPage: 0 }"
                      class="bg-white shadow-1"
                      style="border-radius: 6px; border: 1px solid #e0e0e0;"
                    >
                      <template v-slot:header="ingProps">
                        <q-tr :props="ingProps" class="bg-grey-2">
                          <q-th v-for="col in ingProps.cols" :key="col.name" :props="ingProps" class="text-weight-bold">
                            {{ col.label }}
                          </q-th>
                        </q-tr>
                      </template>
                      <template v-slot:body="ingProps">
                         <q-tr :props="ingProps" class="hover-bg">
                           <q-td v-for="col in ingProps.cols" :key="col.name" :props="ingProps">
                             <template v-if="col.name === 're_code'">
                               <span class="text-weight-medium text-blue-8">{{ col.value }}</span>
                             </template>
                             <template v-else-if="col.name === 'vol_per_batch' || col.name === 'total_vol'">
                               <span class="text-weight-bold">{{ col.value }}</span>
                             </template>
                             <template v-else>
                               {{ col.value }}
                             </template>
                           </q-td>
                         </q-tr>
                      </template>
                    </q-table>
                  </div>

                  <!-- Batches List -->
                  <div class="col-12 col-md-7">
                    <div class="text-subtitle2 q-mb-sm text-blue-9">{{ t('prodPlan.batchDetails') }} - {{ props.row.plan_id }}</div>
                    <template v-if="props.row.batches && props.row.batches.length > 0">
                      <q-table
                        :rows="props.row.batches"
                        :columns="batchColumns"
                        row-key="batch_id"
                        flat
                        dense
                        hide-bottom
                        :pagination="{ rowsPerPage: 0 }"
                        class="bg-white shadow-1"
                        style="border-radius: 6px; border: 1px solid #e0e0e0;"
                      >
                        <template v-slot:header="batchProps">
                          <q-tr :props="batchProps" class="bg-grey-2">
                            <q-th
                              v-for="col in batchProps.cols"
                              :key="col.name"
                              :props="batchProps"
                              class="text-weight-bold"
                            >
                              {{ col.label }}
                            </q-th>
                          </q-tr>
                        </template>
                        <template v-slot:body="batchProps">
                          <q-tr :props="batchProps" class="hover-bg">
                            <q-td v-for="col in batchProps.cols" :key="col.name" :props="batchProps">
                              <template v-if="['flavour_house', 'spp', 'batch_prepare', 'ready_to_product', 'production', 'done'].includes(col.name)">
                                <q-icon v-if="col.value" name="check_circle" color="positive" size="sm" />
                                <q-icon v-else name="cancel" color="grey-4" size="sm" />
                              </template>
                              <template v-else-if="col.name === 'status'">
                                <q-badge
                                  :color="
                                    batchProps.row.status === 'Cancelled'
                                      ? 'red'
                                      : batchProps.row.status === 'Draft' || batchProps.row.status === 'Pending' || batchProps.row.status === 'Created'
                                        ? 'grey-6'
                                        : 'green'
                                  "
                                  text-color="white"
                                  class="text-weight-bold"
                                >
                                  {{ batchProps.row.status }}
                                </q-badge>
                              </template>
                              <template v-else-if="col.name === 'batch_id'">
                                <span class="text-weight-medium text-blue-8">{{ batchProps.row.batch_id }}</span>
                              </template>
                              <template v-else-if="col.name === 'actions'">
                                <q-btn icon="print" flat round dense color="primary" @click="printBatchLabel(props.row, batchProps.row)">
                                  <q-tooltip>{{ t('prodPlan.printLabel') }}</q-tooltip>
                                </q-btn>
                              </template>
                              <template v-else>
                                {{ col.value }}
                              </template>
                            </q-td>
                          </q-tr>
                        </template>
                      </q-table>
                    </template>
                    <div v-else class="text-caption text-grey-7 q-py-sm">
                      {{ t('common.noData') }}
                    </div>
                  </div>
                </div>
              </q-td>
            </q-tr>
          </template>
        </q-table>
      </q-card>
    </q-page>

    <!-- Cancel Plan Dialog -->
    <q-dialog v-model="showCancelDialog" persistent>
      <q-card style="min-width: 420px;">
        <q-card-section class="bg-negative text-white">
          <div class="text-h6 row items-center q-gutter-sm">
            <q-icon name="cancel" size="sm" />
            <span>{{ t('prodPlan.cancelConfirmTitle') }}</span>
          </div>
        </q-card-section>

        <q-card-section class="q-pt-md">
          <p class="text-body2 q-mb-md">{{ t('prodPlan.cancelConfirmMessage') }}</p>

          <div class="text-caption text-weight-bold q-mb-xs">{{ t('prodPlan.cancelReasonLabel') }}</div>
          <q-select
            v-model="cancelReason"
            :options="cancelReasonOptions"
            outlined
            dense
            emit-value
            map-options
            class="q-mb-md"
          />

          <template v-if="cancelReason === 'Other'">
            <div class="text-caption text-weight-bold q-mb-xs">{{ t('prodPlan.cancelCustomReason', 'Specify reason') }}</div>
            <q-input
              v-model="cancelCustomReason"
              outlined
              dense
              autofocus
              type="textarea"
              rows="2"
            />
          </template>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat :label="t('common.cancel', 'Cancel')" color="grey-7" v-close-popup />
          <q-btn
            unelevated
            :label="t('prodPlan.confirmCancel', 'Confirm Cancel')"
            color="negative"
            :disable="!cancelReason"
            @click="confirmCancelPlan"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

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

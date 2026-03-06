<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'

import { useAuth } from '../composables/useAuth'
import { appConfig } from '~/appConfig/config'
import { useLabelPrinter } from '~/composables/useLabelPrinter'
import { usePreBatchProduction } from '~/composables/usePreBatchProduction'
import { usePreBatchIngredients } from '~/composables/usePreBatchIngredients'
import { usePreBatchInventory } from '~/composables/usePreBatchInventory'
import { usePreBatchScales } from '~/composables/usePreBatchScales'
import { usePreBatchLabels } from '~/composables/usePreBatchLabels'
import { usePreBatchRecords } from '~/composables/usePreBatchRecords'
import { useMqttLocalDevice } from '~/composables/useMqttLocalDevice'

const $q = useQuasar()
const { getAuthHeader, user } = useAuth()
const { generateLabelSvg, printLabel } = useLabelPrinter()
const { t } = useI18n()
const { connect: connectMqtt, mqttClient } = useMqttLocalDevice()

const formatDate = (date: any) => {
  if (!date) return '-'
  const d = new Date(date)
  if (isNaN(d.getTime())) return date
  return d.toLocaleDateString('en-GB')
}



// ─── Shared refs (owned by page, passed into composables) ───
const selectedReCode = ref('')
const selectedRequirementId = ref<number | null>(null)
const requireVolume = ref(0)
const packageSize = ref(0)
const isBatchSelected = ref(false)
const ingredients = ref<any[]>([])

const containerSizeOptions = [0.5, 1, 2, 5, 10, 20, 25]
const containerSize = ref(25)

// Watch containerSize to update packageSize
watch(containerSize, (val) => {
  if (val !== packageSize.value) {
    packageSize.value = val
  }
})

watch(packageSize, (val) => {
  if (containerSizeOptions.includes(val)) {
    containerSize.value = val
  }
})

// Cast getAuthHeader for composable compatibility
const authHeader = () => getAuthHeader() as Record<string, string>

const currentPackageId = computed(() => {
  if (selectedBatch.value && selectedReCode.value) {
    return `${selectedBatch.value.batch_id}-${selectedReCode.value}-${nextPackageNo.value}`
  }
  return '-'
})

// ─── 1. Inventory ───
const {
  warehouses, selectedWarehouse, inventoryRows, inventoryLoading,
  selectedInventoryItem, selectedIntakeLotId, showAllInventory,
  showHistoryDialog, showIntakeLabelDialog, selectedHistoryItem,
  intakeLabelData, selectedPrinter, intakeLotInputRef,
  inventoryColumns, filteredInventory, sortedAllInventory, inventorySummary,
  fetchWarehouses, fetchInventory, updateInventoryStatus,
  printIntakeLabel, openIntakeLabelDialog, onViewHistory,
  focusIntakeLotInput, onIntakeLotScanEnter, isFIFOCompliant,
  simulateScan, onInventoryRowClick,
} = usePreBatchInventory({
  $q, getAuthHeader: authHeader, t, formatDate,
  selectedReCode,
})

// ─── 2. Scales ───
const scalesComposable = usePreBatchScales({
  $q, t,
  selectedReCode,
  requireVolume,
  packageSize,
  mqttClient,
})
const {
  selectedScale, scales, connectedScales, batchedVolume, currentPackageOrigins,
  activeScale, actualScaleValue, remainVolume, remainToBatch,
  targetWeight, requestBatch, isToleranceExceeded, isPackagedVolumeInTol,
  packagedVolumeBgColor,
  onScaleInput, isScaleConnected, toggleScaleConnection,
  getScaleClass, getDisplayClass, onTare,
  getOriginDelta, onAddLot, onRemoveLot,
} = scalesComposable

// ─── Forward declarations for cross-references ───
// These functions are set after the composables that own them are created.
let _fetchPrebatchItems: (batchId: string) => Promise<void> = async () => {}
let _updatePrebatchItemStatus: (batchId: string, reCode: string, status: number) => Promise<void> = async () => {}
let _fetchPreBatchRecords: () => Promise<void> = async () => {}
let _updateRequireVolume: () => void = () => {}
let _finalizeBatchPreparation: (batchId: number) => Promise<void> = async () => {}

// ─── 3. Ingredients ───
// selectedProductionPlan and selectedBatch are owned by production composable
// but ingredients needs them. We create a ref/computed that we'll sync later.
const _selectedProductionPlan = ref('')
const _selectedBatch = ref<any>(null)
const _preBatchLogs = ref<any[]>([])

const ingredientsComposable = usePreBatchIngredients({
  $q, getAuthHeader: authHeader, t,
  ingredients,
  selectedProductionPlan: _selectedProductionPlan,
  selectedBatch: computed(() => _selectedBatch.value),
  selectedReCode,
  selectedRequirementId,
  selectedWarehouse,
  isBatchSelected,
  inventoryRows,
  preBatchLogs: _preBatchLogs,
  requireVolume,
  packageSize,
  filteredInventory,
  selectedInventoryItem,
  selectedIntakeLotId,
  updatePrebatchItemStatus: (...args: [string, string, number]) => _updatePrebatchItemStatus(...args),
})
const {
  prebatchItems, expandedIngredients, ingredientBatchDetail, expandedBatchRows,
  selectableIngredients, ingredientsByWarehouse,
  fetchPrebatchItems, updatePrebatchItemStatus,
  toggleIngredientExpand, isExpanded, fetchIngredientBatchDetail,
  toggleBatchRow, isBatchRowExpanded, getPackagePlan,
  getIngredientLogs, getIngredientRowClass,
  onSelectIngredient, updateRequireVolume, onIngredientSelect, onIngredientDoubleClick,
} = ingredientsComposable

// Wire forward refs
_fetchPrebatchItems = fetchPrebatchItems
_updatePrebatchItemStatus = updatePrebatchItemStatus
_updateRequireVolume = updateRequireVolume

// ─── 4. Records ───
const recordsComposable = usePreBatchRecords({
  $q, getAuthHeader: authHeader, t, user, formatDate,
  selectedBatch: computed(() => _selectedBatch.value),
  selectedProductionPlan: _selectedProductionPlan,
  selectedReCode,
  requireVolume,
  selectableIngredients,
  requestBatch,
  fetchPrebatchItems,
  finalizeBatchPreparation: (...args: [number]) => _finalizeBatchPreparation(...args),
})
const {
  preBatchLogs, recordToDelete, showDeleteDialog, deleteInput,
  isPackageSizeLocked, showAuthDialog, authPassword, selectedPreBatchLogs,
  prebatchColumns, filteredPreBatchLogs, totalCompletedWeight,
  completedCount, nextPackageNo, preBatchSummary,
  fetchPreBatchRecords, executeDeletion, onDeleteRecord,
  onConfirmDeleteManual, onDeleteScanEnter, unlockPackageSize, verifyAuth,
} = recordsComposable

// Wire forward refs
_fetchPreBatchRecords = fetchPreBatchRecords

// Sync preBatchLogs into ingredients composable
watch(preBatchLogs, (val) => { _preBatchLogs.value = val }, { deep: true, immediate: true })

// Sync computed values from records into scales
watch(totalCompletedWeight, (val) => { scalesComposable.totalCompletedWeight.value = val }, { immediate: true })
watch(completedCount, (val) => { scalesComposable.completedCount.value = val }, { immediate: true })
watch(nextPackageNo, (val) => { scalesComposable.nextPackageNo.value = val }, { immediate: true })

// ─── 5. Production ───
const production = usePreBatchProduction({
  $q, getAuthHeader: authHeader, t,
  ingredients,
  prebatchItems,
  inventoryRows,
  requireVolume,
  packageSize,
  selectedReCode,
  selectedRequirementId,
  isBatchSelected,
  selectedWarehouse,
  fetchPrebatchItems,
  fetchPreBatchRecords,
  updatePrebatchItemStatus,
  updateRequireVolume,
  ingredientBatchDetail,
})
const {
  selectedBatchIndex, isLoading, productionPlans, planFilter, productionPlanOptions,
  allBatches, filteredBatches, ingredientOptions, batchIngredients,
  filteredProductionPlans, plansWithBatches, batchIds, selectedBatch, selectedProductionPlan, selectedPlanDetails, structuredSkuList,
  fetchIngredients, fetchProductionPlans, fetchBatchIds,
  filterBatchesByPlan, onPlanShow, onBatchSelect, onBatchExpand,
  onBatchIngredientClick, advanceToNextBatch, finalizeBatchPreparation, onSelectBatch,
} = production

// Wire forward ref & sync production-owned refs into ingredients/records composable
_finalizeBatchPreparation = finalizeBatchPreparation
watch(selectedProductionPlan, (val) => { _selectedProductionPlan.value = val }, { immediate: true })
watch(selectedBatch, (val) => { _selectedBatch.value = val }, { immediate: true })

// ─── 6. Labels ───
const {
  showLabelDialog, packageLabelId, capturedScaleValue, renderedLabel,
  showPackingBoxLabelDialog, renderedPackingBoxLabel,
  labelDataMapping, packingBoxLabelDataMapping,
  buildLotStrings, buildLabelData,
  updateDialogPreview, updatePackingBoxPreview,
  openLabelDialog, onPrintLabel, onReprintLabel,
  quickReprint, printAllPlanLabels, printAllBatchLabels, onPrintPackingBoxLabel, onDone,
} = usePreBatchLabels({
  $q, getAuthHeader: authHeader, t, user, formatDate,
  generateLabelSvg: (async (template: string, data: any) => (await generateLabelSvg(template, data)) ?? '') as (template: string, data: any) => Promise<string>,
  printLabel,
  selectedBatch,
  selectedReCode,
  selectedRequirementId,
  selectedProductionPlan,
  selectedPlanDetails,
  selectableIngredients,
  ingredients,
  requireVolume,
  packageSize,
  capturedScaleValue: batchedVolume,
  nextPackageNo,
  requestBatch,
  actualScaleValue,
  currentPackageOrigins,
  preBatchLogs,
  selectedPreBatchLogs,
  getPackagePlan,
  fetchPreBatchRecords,
  fetchPrebatchItems,
  updatePrebatchItemStatus,
  onBatchExpand,
  onPlanShow,
  advanceToNextBatch,
  getOriginDelta,
  selectedIntakeLotId,
  selectedInventoryItem,
  productionPlans,
})

// ── Pre-Batch Summary Report ──────────────
const showPreBatchReportDialog = ref(false)
const prebatchReportFromDate = ref('')
const prebatchReportToDate = ref(new Date().toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' }))
const prebatchReportLoading = ref(false)

const formatDateToApi2 = (val: string) => {
  if (!val) return null
  const parts = val.split('/')
  if (parts.length === 3) return `${parts[2]}-${parts[1]}-${parts[0]}`
  return null
}

const printPreBatchReport = async () => {
  prebatchReportLoading.value = true
  const printWindow = window.open('', '_blank')
  if (!printWindow) { prebatchReportLoading.value = false; return }
  printWindow.document.write('<html><body><h2 style="font-family:sans-serif;color:#1565c0;">⏳ Loading...</h2></body></html>')
  try {
    let url = `${appConfig.apiBaseUrl}/reports/prebatch-summary`
    const p: string[] = []
    const f = formatDateToApi2(prebatchReportFromDate.value)
    const t2 = formatDateToApi2(prebatchReportToDate.value)
    if (f) p.push(`from_date=${f}`)
    if (t2) p.push(`to_date=${t2}`)
    if (p.length) url += '?' + p.join('&')
    const data = await $fetch<any>(url)
    const now = new Date().toLocaleString('en-GB')

    const recordRows = (data.records || []).map((r: any, i: number) => `
      <tr><td class="tc">${i+1}</td><td>${r.batch_record_id}</td><td>${r.plan_id || '-'}</td><td>${r.mat_sap_code || '-'}</td><td>${r.re_code || '-'}</td><td class="tr">${(r.net_volume || 0).toFixed(4)}</td><td class="tr">${(r.total_request_volume || 0).toFixed(4)}</td><td class="tc">${r.package_no || '-'}/${r.total_packages || '-'}</td><td class="tc">${r.created_at ? new Date(r.created_at).toLocaleString('en-GB') : '-'}</td></tr>
    `).join('')

    const ingredientRows = (data.ingredient_totals || []).map((ing: any, i: number) => `
      <tr><td class="tc">${i+1}</td><td class="tb">${ing.mat_sap_code || '-'}</td><td>${ing.re_code || '-'}</td><td class="tr">${(ing.total_net || 0).toFixed(4)}</td><td class="tr">${(ing.total_request || 0).toFixed(4)}</td><td class="tr">${((ing.total_net || 0) - (ing.total_request || 0)).toFixed(4)}</td><td class="tc">${ing.count}</td></tr>
    `).join('')

    const s = data.summary || {}
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Pre-Batch Summary Report</title>
    <style>@page{size:A4 landscape;margin:8mm 10mm}*{box-sizing:border-box;margin:0;padding:0}body{font-family:'Courier Prime',monospace;font-size:13px;color:#222;line-height:1.4}.header{background:#1565c0;color:#fff;padding:14px 20px;display:flex;justify-content:space-between;align-items:center;border-radius:4px;margin-bottom:8px}.header h1{font-size:22px;margin:0}.info-bar{background:#e3f2fd;padding:8px 14px;border-radius:3px;margin-bottom:10px;font-size:13px;color:#1565c0;font-weight:bold}.section-title{background:#37474f;color:#fff;padding:8px 14px;font-size:14px;font-weight:bold;border-radius:3px;margin:12px 0 4px}table.dt{width:100%;border-collapse:collapse;font-size:12px;table-layout:fixed}table.dt th{background:#546e7a;color:#fff;padding:4px 8px;text-align:left;font-size:10px;text-transform:uppercase}table.dt td{padding:4px 8px;border-bottom:1px solid #e0e0e0;overflow:hidden;text-overflow:ellipsis}.grand{background:#1565c0;color:#fff;padding:12px 18px;border-radius:4px;font-size:14px;margin-top:10px;display:flex;justify-content:space-between}.footer{border-top:2px solid #1565c0;font-size:10px;color:#888;padding:6px 0;margin-top:10px;display:flex;justify-content:space-between}.tr{text-align:right}.tc{text-align:center}.tb{font-weight:bold}@media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}</style></head><body>
    <div class="header"><div><h1>🧪 Pre-Batch Summary Report</h1><div style="font-size:12px;margin-top:3px;opacity:.85">xMixing Control System</div></div><div style="font-size:12px;text-align:right;opacity:.9">Generated: ${now}</div></div>
    <div class="info-bar">📅 Period: ${prebatchReportFromDate.value || 'All'} — ${prebatchReportToDate.value || 'All'} | Total Records: ${s.total_records || 0} | Total Net: ${(s.total_net_volume || 0).toFixed(4)} kg</div>
    <div class="section-title">📋 Pre-Batch Records</div>
    <table class="dt"><thead><tr><th style="width:3%">#</th><th style="width:16%">Batch Record ID</th><th style="width:10%">Plan ID</th><th style="width:14%">Mat SAP Code</th><th style="width:8%">RE Code</th><th style="width:10%" class="tr">Net Vol (kg)</th><th style="width:10%" class="tr">Request (kg)</th><th style="width:8%" class="tc">Pkg</th><th style="width:12%" class="tc">Date</th></tr></thead>
    <tbody>${recordRows || '<tr><td colspan="9" class="tc">No records</td></tr>'}</tbody></table>
    <div class="section-title">📊 Ingredient Totals</div>
    <table class="dt"><thead><tr><th style="width:4%">#</th><th style="width:18%">Mat SAP Code</th><th style="width:10%">RE Code</th><th style="width:14%" class="tr">Total Net (kg)</th><th style="width:14%" class="tr">Total Request (kg)</th><th style="width:14%" class="tr">Variance (kg)</th><th style="width:8%" class="tc">Count</th></tr></thead>
    <tbody>${ingredientRows}</tbody></table>
    <div class="grand"><span>Total: ${s.total_records || 0} pre-batch records</span><span>Net Volume: ${(s.total_net_volume || 0).toFixed(4)} kg</span></div>
    <div class="footer"><span>xMixing 2025 | xMix.co.th</span><span>Pre-Batch Summary Report</span></div>
    </body></html>`
    printWindow.document.open(); printWindow.document.write(html); printWindow.document.close()
    showPreBatchReportDialog.value = false
  } catch (e) { console.error(e); printWindow.close(); $q.notify({ type: 'negative', message: 'Failed', position: 'top' }) }
  finally { prebatchReportLoading.value = false }
}

// ─── Lifecycle ───
onMounted(() => {
  fetchIngredients()
  fetchProductionPlans()
  fetchBatchIds()
  fetchInventory()
  fetchPreBatchRecords()
  fetchWarehouses()
  focusIntakeLotInput()
  connectMqtt()
})
</script>
<template>
  <q-page class="q-pa-md bg-white">
    <!-- Page Header -->
    <div class="bg-blue-9 text-white q-pa-md rounded-borders q-mb-sm shadow-2">
      <div class="row justify-between items-center">
        <div class="row items-center q-gutter-md">
          <div class="row items-center q-gutter-sm">
            <q-icon name="science" size="sm" />
            <div class="text-h6 text-weight-bolder">{{ t('preBatch.title') }}</div>
          </div>
          <div class="row items-center no-wrap bg-blue-10 q-px-md q-py-xs rounded-borders shadow-1">
            <div class="text-subtitle2 text-weight-bold q-mr-md">Select Production Plan:</div>
            <q-select
              v-model="planFilter"
              :options="productionPlanOptions"
              dense
              filled
              square
              emit-value
              map-options
              bg-color="blue-1"
              label-color="blue-9"
              style="min-width: 250px;"
              popup-content-class="bg-blue-1"
            >
              <template v-slot:prepend>
                <q-icon name="filter_alt" size="xs" color="blue-9" />
              </template>
            </q-select>
          </div>
        </div>
        <div class="row items-center q-gutter-sm">
          <q-btn flat round dense icon="assessment" text-color="white" @click="showPreBatchReportDialog = true">
            <q-tooltip>Pre-Batch Summary Report</q-tooltip>
          </q-btn>
          <div class="text-caption text-blue-2">{{ t('prodPlan.version') }} 0.2</div>
        </div>
      </div>
    </div>

    <div class="row q-col-gutter-lg">
      <!-- LEFT SIDEBAR -->
      <div class="col-12 col-md-4 column q-gutter-y-sm" style="height: calc(100vh - 140px);">

        <!-- CARD 1: Production Plans with expandable Batches -->
        <q-card class="col column bg-white shadow-2" style="max-height: 40vh;">
          <q-card-section class="bg-blue-9 text-white q-py-xs">
            <div class="row items-center justify-between no-wrap q-gutter-x-sm">
              <div class="row items-center no-wrap">
                <q-icon name="assignment" size="sm" class="q-mr-xs" />
                <div class="text-subtitle2 text-weight-bold">{{ t('prodPlan.productionPlan') }}</div>
              </div>
              <q-badge color="white" text-color="blue-9" class="text-weight-bold">
                {{ filteredProductionPlans.length }} Plans Found
              </q-badge>
            </div>
          </q-card-section>
          <div class="col relative-position">
            <q-scroll-area class="fit">
              <template v-if="plansWithBatches.length > 0">
                <q-list dense separator class="text-caption">
                  <template v-for="plan in plansWithBatches" :key="plan.plan_id">
                    <q-item
                      clickable
                      v-ripple
                      :active="selectedProductionPlan === plan.plan_id"
                      active-class="bg-blue-1 text-blue-9 text-weight-bold"
                      :class="selectedProductionPlan !== plan.plan_id ? 'text-weight-bold bg-blue-grey-1 text-blue-grey-9' : ''"
                      @click="onPlanShow(plan)"
                    >
                      <q-item-section avatar style="min-width: 24px;">
                        <q-icon 
                          :name="selectedProductionPlan === plan.plan_id ? 'radio_button_checked' : 'radio_button_unchecked'" 
                          :color="selectedProductionPlan === plan.plan_id ? 'blue-9' : 'grey-5'"
                          size="xs" 
                        />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label>{{ plan.sku_id }} - {{ plan.sku_name || 'No Name' }}</q-item-label>
                        <q-item-label caption>Plan: {{ plan.plan_id }} ({{ plan.batches.length }} batches)</q-item-label>
                      </q-item-section>
                    </q-item>
                  </template>
                </q-list>
              </template>
              <div v-else class="text-center q-pa-md text-grey">
                <q-icon name="inbox" size="lg" class="q-mb-sm" /><br>
                No active production plans matching selection
              </div>
            </q-scroll-area>
          </div>
        </q-card>


        <!-- CARD 2: Ingredients for Selected Plan -->
        <q-card class="col-auto bg-white shadow-2 column" style="max-height: 400px;">
            <q-card-section class="bg-blue-grey-2 q-py-xs">
                <div class="row items-center justify-between no-wrap">
                    <div class="text-subtitle2 text-weight-bold text-blue-grey-8 row items-center no-wrap">
                        {{ t('preBatch.requireIngredient') }}
                        <q-select
                            v-model="selectedWarehouse"
                            :options="warehouses"
                            dense
                            filled
                            square
                            emit-value
                            map-options
                            option-value="warehouse_id"
                            option-label="name"
                            bg-color="white"
                            label-color="blue-grey-8"
                            class="q-ml-md"
                            style="min-width: 120px;"
                        >
                            <template v-slot:prepend>
                                <q-icon name="filter_list" size="xs" color="blue-grey-6" />
                            </template>
                        </q-select>
                    </div>
                    <q-badge color="blue-grey-6" text-color="white" class="text-weight-bold">
                        {{ selectableIngredients.length }} {{ t('preBatch.items') }}
                    </q-badge>
                </div>
            </q-card-section>
            <div class="col relative-position" style="overflow-y: auto;">
                <q-markup-table dense flat square separator="cell" sticky-header>
                    <thead class="bg-orange-1 text-orange-10">
                        <tr>
                            <th class="text-center" style="width: 30px"></th>
                            <th class="text-left" style="font-size: 0.7rem;">RE-Code</th>
                            <th class="text-center" style="font-size: 0.7rem;">Container</th>
                            <th class="text-center" style="font-size: 0.7rem;">{{ t('preBatch.wh') }}</th>
                            <th class="text-right" style="font-size: 0.7rem;">Require</th>
                            <th class="text-right" style="font-size: 0.7rem;">Packaged</th>
                            <th class="text-center" style="font-size: 0.7rem;">{{ t('common.status') }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <template v-for="ing in selectableIngredients" :key="ing.re_code">
                            <tr 
                                class="transition-all"
                                :class="getIngredientRowClass(ing)"
                                @click="onSelectIngredient(ing)"
                            >
                                <td class="text-center" style="padding: 0;">
                                    <q-btn
                                        flat round dense
                                        :icon="isExpanded(ing.re_code) ? 'expand_more' : 'chevron_right'"
                                        color="orange-9"
                                        size="xs"
                                        @click.stop="toggleIngredientExpand(ing.re_code)"
                                    />
                                </td>
                                <td class="text-weight-bold transition-all" style="font-size: 0.75rem;">
                                    <div class="cursor-pointer text-blue-9" @click.stop="onSelectIngredient(ing)">
                                        {{ ing.re_code }}
                                    </div>
                                    <q-tooltip>{{ ing.ingredient_name }}</q-tooltip>
                                </td>
                                <td class="text-center text-caption" style="font-size: 0.7rem;">{{ ing.package_container_type }}</td>
                                <td class="text-center text-caption" style="font-size: 0.7rem;">{{ ing.from_warehouse }}</td>
                                <td class="text-right text-weight-bold text-orange-9" style="font-size: 0.75rem;">{{ ing.batch_require ? ing.batch_require.toFixed(5) : '0' }}</td>
                                <td class="text-right text-weight-bold text-green-9" style="font-size: 0.75rem;">{{ ing.total_packaged ? ing.total_packaged.toFixed(5) : '0' }}</td>
                                <td class="text-center">
                                    <div v-if="ing.status === 2" class="row no-wrap items-center justify-center q-gutter-x-xs">
                                        <q-badge color="green" :label="t('preBatch.complete')" size="sm" />
                                        <q-btn flat round dense icon="print" size="xs" color="blue-9" @click.stop="printAllPlanLabels(ing)">
                                            <q-tooltip>Print All Labels for Plan</q-tooltip>
                                        </q-btn>
                                    </div>
                                    <q-badge v-else-if="ing.status === 1" color="orange" :label="t('preBatch.onBatch')" size="sm" />
                                    <q-badge v-else color="grey-6" label="Created" size="sm" />
                                </td>
                            </tr>
                            
                            <!-- Per-batch breakdown table -->
                            <tr v-if="isExpanded(ing.re_code)" class="bg-blue-grey-1">
                                <td colspan="7" class="q-pa-none">
                                    <div class="q-pl-lg q-pr-sm q-py-xs" style="max-width: 100%; overflow-x: auto;">
                                        <q-markup-table dense flat square separator="cell" class="bg-white rounded-borders shadow-1" style="font-size: 0.65rem;">
                                            <thead class="bg-blue-grey-2">
                                                <tr>
                                                    <th style="width: 20px;"></th>
                                                    <th class="text-left" style="font-size: 0.65rem;">Batch ID</th>
                                                    <th class="text-right" style="font-size: 0.65rem;">Require</th>
                                                    <th class="text-right" style="font-size: 0.65rem;">Packaged</th>
                                                    <th class="text-center" style="font-size: 0.65rem;">Status</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <template v-for="bd in (ingredientBatchDetail[ing.re_code] || [])" :key="bd.batch_id">
                                                    <tr 
                                                        class="cursor-pointer"
                                                        :class="bd.status === 2 ? 'bg-green-1 text-grey-6' : ''"
                                                        @click="onBatchIngredientClick({ batch_id: bd.batch_id }, { re_code: ing.re_code, id: bd.req_id, required_volume: bd.required_volume, status: bd.status }, selectedPlanDetails)"
                                                    >
                                                        <td style="padding: 0; width: 20px;">
                                                            <q-btn flat round dense size="xs"
                                                                :icon="isBatchRowExpanded(bd.batch_id + '-' + ing.re_code) ? 'expand_more' : 'chevron_right'"
                                                                color="blue-grey-6"
                                                                @click.stop="toggleBatchRow(bd.batch_id + '-' + ing.re_code)"
                                                            />
                                                        </td>
                                                        <td class="text-left">{{ bd.batch_id }}</td>
                                                        <td class="text-right">{{ bd.required_volume.toFixed(5) }}</td>
                                                        <td class="text-right" :class="bd.actual_volume > 0 ? 'text-blue-9 text-weight-bold' : ''">{{ bd.actual_volume.toFixed(5) }}</td>
                                                        <td class="text-center">
                                                            <q-badge v-if="bd.status === 2" color="green" label="Done" size="sm" />
                                                            <q-badge v-else-if="bd.status === 1" color="orange" label="Batch" size="sm" />
                                                            <q-badge v-else color="grey-5" label="Wait" size="sm" />
                                                        </td>
                                                    </tr>
                                                    <!-- Expanded package plan -->
                                                    <tr v-if="isBatchRowExpanded(bd.batch_id + '-' + ing.re_code)" class="bg-blue-grey-1">
                                                        <td :colspan="5" class="q-pa-none q-pl-lg">
                                                            <q-markup-table dense flat square separator="cell" class="bg-white" style="font-size: 0.6rem;">
                                                                <thead class="bg-grey-2">
                                                                    <tr>
                                                                        <th style="font-size: 0.6rem; width: 30px;">Pkg#</th>
                                                                        <th class="text-right" style="font-size: 0.6rem;">Target</th>
                                                                        <th class="text-right" style="font-size: 0.6rem;">Packaged</th>
                                                                        <th class="text-center" style="font-size: 0.6rem; width: 40px;"></th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    <tr v-for="pkg in getPackagePlan(bd.batch_id, ing.re_code, bd.required_volume)" :key="pkg.pkg_no"
                                                                        :class="pkg.status === 'done' ? 'bg-green-1' : ''">
                                                                        <td class="text-center">#{{ pkg.pkg_no }}</td>
                                                                        <td class="text-right">{{ pkg.target.toFixed(3) }}</td>
                                                                        <td class="text-right" :class="pkg.status === 'done' ? 'text-blue-9 text-weight-bold' : 'text-grey-5'">
                                                                            {{ pkg.actual !== null ? pkg.actual.toFixed(4) : '-' }}
                                                                        </td>
                                                                        <td class="text-center">
                                                                            <q-icon v-if="pkg.status === 'done'" name="check_circle" color="green" size="xs" />
                                                                        </td>
                                                                    </tr>
                                                                </tbody>
                                                            </q-markup-table>
                                                        </td>
                                                    </tr>
                                                </template>
                                                <tr v-if="!ingredientBatchDetail[ing.re_code] || ingredientBatchDetail[ing.re_code]?.length === 0">
                                                    <td colspan="5" class="text-center text-grey text-italic">Loading...</td>
                                                </tr>
                                            </tbody>
                                        </q-markup-table>
                                    </div>
                                </td>
                            </tr>
                        </template>
                        <tr v-if="selectableIngredients.length === 0">
                            <td colspan="7" class="text-center text-grey q-pa-md">
                                <template v-if="selectedProductionPlan">
                                    <div v-if="prebatchItems.length > 0">
                                        {{ t('preBatch.noMatchingIngredients') }}
                                    </div>
                                    <div v-else-if="isBatchSelected">
                                        {{ t('preBatch.noIngredientsForBatch') }}
                                    </div>
                                    <div v-else>
                                        {{ t('preBatch.selectBatchToViewDetailed') }}
                                    </div>
                                </template>
                                <div v-else>{{ t('preBatch.selectPlanToView') }}</div>
                            </td>
                        </tr>
                    </tbody>
                </q-markup-table>
            </div>
        </q-card>
      </div>

      <!-- RIGHT MAIN CONTENT -->
      <div class="col-12 col-md-8">

        <!-- SCALES SECTION -->
        <q-card bordered flat class="q-mb-md">
          <q-card-section class="q-py-xs row items-center">
            <div class="text-subtitle1 text-weight-bold">{{ t('preBatch.weightingScale') }}</div>
            <q-space />
          </q-card-section>

          <q-card-section class="q-py-sm">
            <div class="row q-col-gutter-sm">
              <div v-for="scale in scales" :key="scale.id" class="col">
                <q-card flat :bordered="selectedScale !== scale.id" class="q-pa-xs column" :class="getScaleClass(scale)">
                  <div class="row justify-between items-center q-mb-xs">
                    <div class="text-caption text-weight-bold">{{ scale.label }}</div>
                    <div 
                      class="status-indicator shadow-2"
                      :class="scale.connected ? 'bg-green-14' : 'bg-red-14'"
                    >
                      <q-tooltip>{{ scale.connected ? 'Connected' : 'Disconnected' }}</q-tooltip>
                    </div>
                  </div>
                  <!-- Digital Display (read-only monitor) -->
                    <div
                      class="relative-position text-right q-pa-xs text-h4 text-weight-bold rounded-borders flex items-center justify-end"
                      :class="getDisplayClass(scale)"
                      style="min-height: 80px;"
                    >
                      <div class="absolute-top-left q-ma-xs row items-center no-wrap" style="pointer-events: none;">
                        <div 
                          class="stable-spot shadow-1"
                          :class="scale.isStable ? 'bg-green-14' : 'bg-orange-14 anim-vibrate'"
                        ></div>
                      </div>
                      <div class="scale-value text-right" style="width: 100%; padding-right: 4px;">
                        {{ scale.displayValue }}
                      </div>
                      <div class="text-caption text-weight-bolder q-ml-xs" style="font-size: 0.8rem; margin-top: 15px;">{{ scale.unit || 'kg' }}</div>
                    </div>
                </q-card>
              </div>
            </div>
          </q-card-section>
        </q-card>


        <!-- Package Batching Prepare Section -->
        <q-card bordered flat class="q-mb-md">
            <q-card-section class="q-py-xs row items-center">
                <div class="text-subtitle1 text-weight-bold">{{ t('preBatch.packagePrepareFor') }}</div>
                <div class="col-4 q-ml-sm">
                    <q-input
                        outlined
                        :model-value="selectedBatch ? selectedBatch.batch_id : ''"
                        dense
                        bg-color="grey-2"
                        readonly
                        :placeholder="t('preBatch.batchPlanningId')"
                    />
                </div>
                <q-space />
                <div class="text-subtitle1 text-weight-bold q-mr-sm">{{ t('preBatch.fromIntakeLotId') }}</div>
                <div class="col-4">
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
                    >
                        <template v-slot:after>
                           <q-btn icon="add" color="primary" round dense @click="() => onAddLot(selectedIntakeLotId, selectableIngredients, selectedInventoryItem)">
                               <q-tooltip>Add Lot & weight</q-tooltip>
                           </q-btn>
                        </template>
                    </q-input>
                    <div v-if="currentPackageOrigins.length > 0" class="q-mt-xs row q-gutter-xs">
                        <q-chip v-for="(o, i) in currentPackageOrigins" :key="i" removable @remove="onRemoveLot(i)" color="blue-1" text-color="blue-9" dense class="q-ma-xs">
                            {{ o.intake_lot_id }} ({{ o.take_volume.toFixed(4) }}kg)
                        </q-chip>
                    </div>
                </div>
            </q-card-section>

            <q-card-section>
                <!-- ROW 1: Volumes and Scale -->
                <div class="row q-col-gutter-md q-mb-md">
                    <!-- Batch Request volume -->
                    <div class="col">
                        <div class="text-subtitle2 q-mb-xs text-no-wrap">{{ t('preBatch.requestVolume') }}</div>
                        <q-input
                            outlined
                            :model-value="requireVolume.toFixed(5)"
                            dense
                            bg-color="grey-2"
                            readonly
                            input-class="text-right"
                        />
                    </div>

                    <!-- Packaged Volume -->
                    <div class="col">
                        <div class="text-subtitle2 q-mb-xs text-no-wrap">{{ t('preBatch.packagedVolume') }}</div>
                        <q-input
                            outlined
                            :model-value="batchedVolume.toFixed(5)"
                            dense
                            :bg-color="packagedVolumeBgColor"
                            readonly
                            input-class="text-right text-weight-bold"
                        />
                    </div>

                    <!-- Remain Volume -->
                    <div class="col">
                        <div class="text-subtitle2 q-mb-xs text-no-wrap">{{ t('preBatch.remainVolume') }}</div>
                        <q-input
                            outlined
                            :model-value="remainToBatch.toFixed(5)"
                            dense
                            bg-color="grey-2"
                            readonly
                            input-class="text-right"
                        />
                    </div>

                    <!-- Package Request Volume -->
                    <div class="col">
                        <div class="text-subtitle2 q-mb-xs text-no-wrap text-blue-9 text-weight-bold">{{ t('preBatch.reqForPackage') }}</div>
                        <q-input
                            outlined
                            :model-value="targetWeight.toFixed(5)"
                            dense
                            bg-color="blue-1"
                            readonly
                            input-class="text-right text-weight-bold"
                        />
                    </div>

                    <!-- Weight scale Value -->
                    <div class="col">
                        <div class="text-subtitle2 q-mb-xs text-no-wrap">{{ t('preBatch.weightingScale') }}</div>
                        <q-input
                            outlined
                            :model-value="activeScale?.displayValue || '0'"
                            dense
                            :bg-color="activeScale?.isError ? 'red-8' : (isToleranceExceeded ? 'yellow-4' : 'green-1')"
                            readonly
                            :input-class="(activeScale?.isError ? 'text-white' : 'text-black') + ' text-right text-weight-bold'"
                        >
                            <template v-slot:append>
                                <div class="text-caption text-weight-bolder">{{ activeScale?.unit || 'kg' }}</div>
                            </template>
                        </q-input>
                    </div>
                </div>

                <!-- ROW 2: Package Info and Container -->
                <div class="row q-col-gutter-md">
                    <!-- This Package ID -->
                    <div class="col-12 col-md-4">
                        <div class="text-subtitle2 q-mb-xs text-no-wrap">This Package ID</div>
                        <q-input
                            outlined
                            :model-value="currentPackageId"
                            dense
                            bg-color="grey-2"
                            readonly
                            input-class="text-weight-bold"
                        />
                    </div>

                    <!-- Container Type -->
                    <div class="col-12 col-md-3">
                        <div class="text-subtitle2 q-mb-xs text-no-wrap">{{ t('ingConfig.containerType') }}</div>
                        <q-input
                            outlined
                            :model-value="selectableIngredients.find(i => i.re_code === selectedReCode)?.package_container_type || 'Bag'"
                            dense
                            bg-color="grey-2"
                            readonly
                            input-class="text-center"
                        />
                    </div>

                    <!-- Container Size -->
                    <div class="col-12 col-md-3">
                        <div class="text-subtitle2 q-mb-xs text-no-wrap">Container Size (kg)</div>
                        <q-select
                            outlined
                            v-model="containerSize"
                            :options="containerSizeOptions"
                            dense
                            bg-color="white"
                            input-class="text-right"
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
                        </q-select>
                    </div>

                    <!-- Next Package No -->
                    <div class="col-12 col-md-2">
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
                    :disable="!selectedIntakeLotId && currentPackageOrigins.length === 0"
                    />
                </div>
                </div>
            </q-card-section>
        </q-card>

        <!-- INVENTORY SECTION (compact) -->
        <q-card bordered flat class="q-mb-md">
            <q-card-section class="q-py-xs row items-center">
              <div class="text-subtitle1 text-weight-bold">{{ t('preBatch.onHandInventory') }}</div>
              <q-space />
              <q-btn flat round dense icon="refresh" color="primary" @click="fetchInventory" size="sm" class="q-mr-xs">
                  <q-tooltip>{{ t('preBatch.refreshInventory') }}</q-tooltip>
              </q-btn>
              <q-checkbox v-model="showAllInventory" :label="t('preBatch.showAllInv')" dense class="text-caption" />
            </q-card-section>
           <q-card-section class="q-py-sm">
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
                 :row-class="(row: any) => {
                   const first = filteredInventory[0]
                   if (!first) return ''
                   const rowDate = row.expire_date ? new Date(row.expire_date).getTime() : Infinity
                   const firstDate = first.expire_date ? new Date(first.expire_date).getTime() : Infinity
                   return rowDate <= firstDate ? 'bg-green-1 cursor-pointer' : 'text-grey-5 cursor-not-allowed'
                 }"
              >
                <!-- Expire Date Highlight -->
                <template v-slot:body-cell-expire_date="props">
                    <q-td :props="props" class="text-center">
                        <template v-if="filteredInventory.length > 0 && props.row.id === filteredInventory[0].id">
                            <q-badge color="green" text-color="white">{{ formatDate(props.value) }}</q-badge>
                        </template>
                        <template v-else>{{ formatDate(props.value) }}</template>
                    </q-td>
                </template>
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
              <!-- Reprint uses onReprintLabel from history table -->
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
                        :options="['TSC_MB241', 'Zebra-Label-Printer', 'Brother-QL-800', 'Microsoft Print to PDF']"
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
                                <div class="text-h4 text-weight-bolder">{{ (intakeLabelData?.intake_vol ?? 0).toFixed(4) }} <span class="text-h6">kg</span></div>
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
                                <div class="text-h6 text-weight-bold">{{ formatDate(intakeLabelData?.expire_date) }}</div>
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
                                    <div class="text-subtitle2 text-weight-bold">{{ (intakeLabelData?.intake_vol ?? 0).toFixed(4) }} kg</div>
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

    <!-- Pre-Batch Report Dialog -->
    <q-dialog v-model="showPreBatchReportDialog">
      <q-card style="min-width: 400px;">
        <q-card-section class="bg-primary text-white">
          <div class="text-h6"><q-icon name="assessment" class="q-mr-sm" />Pre-Batch Summary Report</div>
          <div class="text-caption">Select date range for the report</div>
        </q-card-section>
        <q-card-section class="q-gutter-md">
          <q-input v-model="prebatchReportFromDate" label="From Date" filled mask="##/##/####" fill-mask>
            <template #append><q-icon name="event" class="cursor-pointer"><q-popup-proxy cover><q-date v-model="prebatchReportFromDate" mask="DD/MM/YYYY" /></q-popup-proxy></q-icon></template>
          </q-input>
          <q-input v-model="prebatchReportToDate" label="To Date" filled mask="##/##/####" fill-mask>
            <template #append><q-icon name="event" class="cursor-pointer"><q-popup-proxy cover><q-date v-model="prebatchReportToDate" mask="DD/MM/YYYY" /></q-popup-proxy></q-icon></template>
          </q-input>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="primary" icon="print" label="Generate Report" :loading="prebatchReportLoading" @click="printPreBatchReport" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<style scoped>
.scale-value,
:deep(.scale-value) {
  font-weight: bold !important;
  font-size: 48px !important;
  line-height: 1.1 !important;
}

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
    width: 4in;
    height: 3in;
    border: none;
    margin: 0;
    padding-left: 2.5mm; /* Safety offset */
    padding-top: 1.5mm;
    box-sizing: border-box;
    background: white;
  }
  @page {
    size: auto;
    margin: 0 !important;
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

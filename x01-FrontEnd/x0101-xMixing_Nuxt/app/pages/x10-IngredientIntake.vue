<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useMqttLocalDevice } from '~/composables/useMqttLocalDevice'
import { formatDate, formatDateTime } from '~/composables/intake/useIntakeHelpers'
import { useIntakeTable } from '~/composables/intake/useIntakeTable'
import { useIntakeLabels } from '~/composables/intake/useIntakeLabels'
import { useIntakeForm } from '~/composables/intake/useIntakeForm'
import { useIntakeConfig } from '~/composables/intake/useIntakeConfig'
import { useIntakeStockAdjust } from '~/composables/intake/useIntakeStockAdjust'
import { useIntakeReports } from '~/composables/intake/useIntakeReports'

const { isConnected: mqttConnected } = useMqttLocalDevice()
const { t } = useI18n()

// ── Table ──
const {
  rows, isLoading, showAll, filters, showFilters, columns, filteredRows,
  showDetailDialog, selectedRecord, openDetailDialog,
  fileInput, fetchReceipts, resetFilters, exportTable, importTable, onFileSelected,
} = useIntakeTable()

// ── Labels ──
const { printLabel, printSinglePackageLabel, testPrint1Page, testPrint2Pages } = useIntakeLabels()

// ── Form ──
const {
  ingredientCodeRef, scannerReady, intakeFrom, intakeTo, lotNumber, expireDate,
  ingredientId, xIngredientName, xMatSapCode, xReCode,
  intakeVol, packageVol, numberOfPackages, manufacturingDate, poNumber, intakeLotId,
  extDate, reservNo, stockZone, materialType,
  showIngredientDialog, tempIngredientId, isSaving,
  isEditing, editId,
  allIngredients, ingredientOptions, fetchAllIngredients, filterIngredients, lookupIngredient,
  onScannerEnter, focusScannerInput, generateIntakeLotId,
  openIngredientDialog, confirmIngredientCode, cancelIngredientDialog,
  statusOptions, getStatusColor, updateRecordStatus,
  onClear, onSave, onEdit, onRejectIntake,
} = useIntakeForm(rows, fetchReceipts, printLabel)

// ── Config (Intake From/To) ──
const {
  intakeFromOptions, intakeToOptions, intakeFromList, intakeToList,
  newIntakeFromName, newIntakeToId, newIntakeToName,
  showIntakeFromDialog, showIntakeToDialog,
  fetchIntakeFromOptions, addIntakeFrom, deleteIntakeFrom,
  fetchIntakeToOptions, addWarehouse, deleteWarehouse,
} = useIntakeConfig()

// ── Stock Adjustment ──
const {
  showAdjustDialog, adjReportFrom, adjReportTo,
  adjSelectedReCode, adjSelectedLotId, adjSelectedLot,
  adjNewRemainVol, adjReason, adjRemark, adjBy, adjSubmitting,
  adjReasonOptions, adjTotalIntake, adjRemaining,
  adjComputedType, adjComputedQty,
  activeReCodes, adjLotsForReCode, stockOverviewLots, stockOverviewSummary,
  adjustments, adjColumnFilters, adjColumns, filteredAdjustments,
  lotUsageMap, fetchLotUsage,
  fetchAdjustments, resetAdjForm, openStockAdjustDialog, submitAdjustment,
} = useIntakeStockAdjust(rows, fetchReceipts)

// ── Reports ──
const {
  showTraceDialog, traceSearchId, traceLoading,
  traceOptions, traceFilteredOptions, traceOptionsLoading,
  fetchTraceOptions, onTraceFilter, onOpenTraceDialog, printTraceReport,
  printExpiryReport,
  showSummaryReport, summaryFromDate, summaryToDate, summaryLoading, printSummaryReport,
  printAdjustmentReport: _printAdjReport,
} = useIntakeReports()

// Wrapper to pass stock-adjust state into the report function
const printAdjustmentReport = () => _printAdjReport(adjReportFrom.value, adjReportTo.value, adjustments.value)

// ── Lifecycle ──
let refreshInterval: any = null

onMounted(() => {
  fetchReceipts()
  generateIntakeLotId()
  fetchAllIngredients()
  fetchIntakeFromOptions()
  fetchIntakeToOptions()
  fetchAdjustments()
  focusScannerInput()
  refreshInterval = setInterval(() => fetchReceipts(true), 5000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})



</script>

<template>
  <q-page class="q-pa-md bg-white">
    <!-- Page Header -->
    <div class="bg-blue-9 text-white q-pa-md rounded-borders q-mb-md shadow-2">
      <div class="row justify-between items-center">
        <div class="row items-center q-gutter-sm">
          <q-icon name="local_shipping" size="sm" />
          <div class="text-h6 text-weight-bolder">{{ t('ingredient.title') }}</div>
        </div>
        <div class="row items-center q-gutter-sm">
          <q-btn icon="assessment" round flat text-color="white" @click="showSummaryReport = true" title="Stock Summary Report">
            <q-tooltip>Stock Summary Report</q-tooltip>
          </q-btn>
          <q-btn icon="warning_amber" round flat text-color="yellow-4" @click="printExpiryReport" title="Expiry Alert">
            <q-tooltip>Ingredient Expiry Alert</q-tooltip>
          </q-btn>
          <q-btn icon="device_hub" round flat text-color="white" @click="onOpenTraceDialog" title="Traceability Report">
            <q-tooltip>Traceability Report</q-tooltip>
          </q-btn>
          <q-btn icon="save" round flat text-color="white" @click="onSave" :loading="isSaving" title="Save Intake" />
          <q-btn icon="clear_all" round flat text-color="white" @click="onClear" title="Clear Form" />
        </div>
      </div>
    </div>

    <!-- ═══ INGREDIENT INTAKE ═══ -->
    <div>
    <div class="row q-mb-lg">
      <div class="col-12">
        <q-card class="shadow-1">
          <q-form class="q-pa-md">
            <!-- Row 1: Intake ID + Ingredient ID + MAT SAP + Re-Code -->
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-3">
                <q-input
                  outlined
                  dense
                  hide-bottom-space
                  v-model="intakeLotId"
                  :label="t('ingredient.intakeId')"
                  readonly
                  bg-color="grey-2"
                  :hint="t('ingredient.autoGenId')"
                />
              </div>
              <div class="col-12 col-md-3">
                <q-select
                  ref="ingredientCodeRef"
                  outlined
                  dense
                  hide-bottom-space
                  v-model="ingredientId"
                  use-input
                  hide-selected
                  fill-input
                  input-debounce="0"
                  :options="ingredientOptions"
                  option-value="ingredient_id"
                  option-label="ingredient_id"
                  emit-value
                  map-options
                  :label="t('ingredient.ingredientCode')"
                  @filter="filterIngredients"
                  @keyup.enter="onScannerEnter"
                  autofocus
                >
                  <template v-slot:option="scope">
                    <q-item v-bind="scope.itemProps">
                      <q-item-section>
                        <q-item-label>{{ scope.opt.ingredient_id }}</q-item-label>
                        <q-item-label caption>{{ scope.opt.name }} ({{ scope.opt.mat_sap_code }})</q-item-label>
                      </q-item-section>
                    </q-item>
                  </template>
                  <template v-slot:prepend>
                    <q-icon
                      name="circle"
                      color="positive"
                    />
                  </template>
                  <template v-slot:append>
                    <q-icon
                      name="qr_code_scanner"
                      class="cursor-pointer"
                      @click="openIngredientDialog"
                    />
                  </template>
                </q-select>
              </div>
              <div class="col-12 col-md-3">
                <q-input
                  outlined
                  dense
                  hide-bottom-space
                  v-model="xMatSapCode"
                  :label="t('ingredient.matSapCode')"
                  readonly
                  bg-color="grey-2"
                />
              </div>
              <div class="col-12 col-md-3">
                <q-input outlined dense hide-bottom-space v-model="xReCode" :label="t('ingredient.reCode')" readonly bg-color="grey-2" />
              </div>
            </div>

            <!-- Row 1.5: Ingredient Name, Mfg Date, Expire Date -->
            <div class="row q-col-gutter-sm q-mt-xs">
                <div class="col-12 col-md-6">
                     <q-input
                        outlined
                        dense
                        hide-bottom-space
                        v-model="xIngredientName"
                        :label="t('ingredient.ingredientName')"
                        readonly
                        bg-color="grey-2"
                        >
                        <template v-slot:after>
                            <q-btn
                            icon="settings"
                            color="primary"
                            round
                            flat
                            to="/x11-IngredientConfig"
                            title="Ingredient"
                            />
                        </template>
                    </q-input>
                </div>
              <div class="col-12 col-md-3">
                <q-input outlined dense hide-bottom-space v-model="manufacturingDate" :label="t('ingredient.manufacturingDate')" mask="##/##/####" placeholder="DD/MM/YYYY">
                  <template v-slot:append>
                    <q-icon name="event" class="cursor-pointer">
                      <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                        <q-date v-model="manufacturingDate" mask="DD/MM/YYYY">
                          <div class="row items-center justify-end">
                            <q-btn v-close-popup :label="t('common.close')" color="primary" flat />
                          </div>
                        </q-date>
                      </q-popup-proxy>
                    </q-icon>
                  </template>
                </q-input>
              </div>
              <div class="col-12 col-md-3">
                <q-input outlined dense hide-bottom-space v-model="expireDate" :label="t('ingredient.expiryDate') + ' *'" mask="##/##/####" placeholder="DD/MM/YYYY">
                  <template v-slot:append>
                    <q-icon name="event" class="cursor-pointer">
                      <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                        <q-date v-model="expireDate" mask="DD/MM/YYYY">
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

            <!-- Row 3: *Intake From, *Intake To, *Lot Number, PO Number -->
            <div class="row q-col-gutter-sm q-mt-xs">
              <div class="col-12 col-md-3">
                <q-select
                  outlined
                  dense
                  hide-bottom-space
                  v-model="intakeFrom"
                  :options="intakeFromOptions"
                  label="Intake From *"
                  map-options
                  emit-value
                  dropdown-icon="arrow_drop_down"
                  bg-color="white"
                >
                  <template v-slot:after>
                    <q-btn
                      icon="settings"
                      color="primary"
                      round
                      flat
                      size="sm"
                      @click="showIntakeFromDialog = true"
                      title="Config Intake Destination"
                    />
                  </template>
                </q-select>
              </div>
              <div class="col-12 col-md-3">
                <q-select
                  outlined
                  dense
                  hide-bottom-space
                  v-model="intakeTo"
                  :options="intakeToOptions"
                  label="Intake To *"
                  map-options
                  emit-value
                  dropdown-icon="arrow_drop_down"
                  bg-color="white"
                >
                  <template v-slot:after>
                    <q-btn
                      icon="settings"
                      color="primary"
                      round
                      flat
                      size="sm"
                      @click="showIntakeToDialog = true"
                      title="Config Intake Destination"
                    />
                  </template>
                </q-select>
              </div>
              <div class="col-12 col-md-3">
                <q-input outlined dense hide-bottom-space v-model="lotNumber" :label="t('ingredient.lotNumber') + ' *'" />
              </div>
              <div class="col-12 col-md-3">
                <q-input outlined dense hide-bottom-space v-model="poNumber" :label="t('ingredient.poNumber')" />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-xs">
              <div class="col-12 col-md-4">
                <q-input outlined dense hide-bottom-space v-model="intakeVol" :label="t('ingredient.intakeVolume') + ' *'" />
              </div>
              <div class="col-12 col-md-4">
                <q-input outlined dense hide-bottom-space v-model="packageVol" :label="t('ingredient.packageVol')" />
              </div>
              <div class="col-12 col-md-4">
                <q-input
                  outlined
                  dense
                  hide-bottom-space
                  v-model="numberOfPackages"
                  :label="t('ingredient.numPackages')"
                  readonly
                  bg-color="grey-2"
                  input-class="text-right"
                />
              </div>
            </div>

            <!-- Row 5: Ext Date, Reserv No, Stock Zone, Material Type -->
            <div class="row q-col-gutter-sm q-mt-xs">
              <div class="col-12 col-md-3">
                <q-input outlined dense hide-bottom-space v-model="extDate" label="EXT. Date" mask="##/##/####" placeholder="DD/MM/YYYY">
                  <template v-slot:append>
                    <q-icon name="event" class="cursor-pointer">
                      <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                        <q-date v-model="extDate" mask="DD/MM/YYYY">
                          <div class="row items-center justify-end">
                            <q-btn v-close-popup :label="t('common.close')" color="primary" flat />
                          </div>
                        </q-date>
                      </q-popup-proxy>
                    </q-icon>
                  </template>
                </q-input>
              </div>
              <div class="col-12 col-md-3">
                <q-input outlined dense hide-bottom-space v-model="reservNo" label="Reserv No" />
              </div>
              <div class="col-12 col-md-3">
                <q-input outlined dense hide-bottom-space v-model="stockZone" label="Stock Zone" />
              </div>
              <div class="col-12 col-md-3">
                <q-input outlined dense hide-bottom-space v-model="materialType" label="Material Type" />
              </div>
            </div>


          </q-form>
        </q-card>
      </div>
    </div>

    <!-- Ingredient Intake Table -->
    <div class="row items-center justify-between q-mb-sm">
      <div class="text-h6">{{ t('ingredient.intakeList') }}</div>
      <div class="row items-center q-gutter-sm">
        <q-btn
          icon="refresh"
          color="primary"
          round
          flat
          dense
          @click="() => fetchReceipts()"
        >
          <q-tooltip>{{ t('common.refresh') }}</q-tooltip>
        </q-btn>
        <q-btn
          icon="filter_alt_off"
          color="primary"
          round
          flat
          dense
          @click="resetFilters"
        >
          <q-tooltip>{{ t('ingredient.resetFilters') }}</q-tooltip>
        </q-btn>
        <q-btn
          icon="filter_alt"
          color="accent"
          round
          flat
          dense
          @click="showFilters = !showFilters"
        >
          <q-tooltip>{{ showFilters ? t('ingredient.hideFilters') : t('ingredient.showFilters') }}</q-tooltip>
        </q-btn>
        <q-btn
          icon="file_download"
          color="secondary"
          round
          flat
          dense
          @click="exportTable"
        >
          <q-tooltip>{{ t('ingredient.exportExcel') }}</q-tooltip>
        </q-btn>
        <q-btn
          icon="file_upload"
          color="accent"
          round
          flat
          dense
          @click="importTable"
        >
          <q-tooltip>{{ t('ingredient.importCsv') }}</q-tooltip>
        </q-btn>
        <!-- Hidden File Input -->
        <input
          type="file"
          ref="fileInput"
          accept=".csv"
          style="display: none"
          @change="onFileSelected"
        />
        <q-checkbox
          v-model="showAll"
          :label="t('ingredient.showAll')"
          dense
        />
      </div>
    </div>

    <div class="row">
      <div class="col-12">
        <q-card flat bordered class="q-mb-md custom-table-border">
          <q-table
            :rows="filteredRows"
            :columns="columns"
            row-key="id"
            flat
            bordered
            class="intake-table"
            :loading="isLoading"
            :rows-per-page-options="[10, 20, 50, 100]"
          >
            <!-- Custom Header to include Filters -->
            <template v-slot:header="props">
              <q-tr :props="props">
                <q-th
                  v-for="col in props.cols"
                  :key="col.name"
                  :props="props"
                  class="text-black bg-white"
                  style="vertical-align: bottom; font-weight: normal; border-bottom: 2px solid #000"
                >
                  <div v-if="showFilters && col.name !== 'xActions'" class="q-pb-sm">
                    <q-input
                      v-model="filters[col.field]"
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

            <!-- Body Slot for Expansion -->
            <template v-slot:body="props">
              <q-tr :props="props">
                <q-td
                  v-for="col in props.cols"
                  :key="col.name"
                  :props="props"
                >
                  <template v-if="col.name === 'expand'">
                    <q-btn
                      size="sm"
                      color="primary"
                      round
                      dense
                      @click="props.expand = !props.expand"
                      :icon="props.expand ? 'keyboard_arrow_down' : 'chevron_right'"
                    />
                  </template>

                  <template v-else-if="col.name === 'status'">
                    <div
                      :class="[
                        'text-white',
                        'row',
                        'flex-center',
                        'rounded-borders',
                        `bg-${getStatusColor(props.row.status)}`,
                      ]"
                      style="height: 28px; font-size: 12px; min-width: 80px;"
                    >
                      {{ props.row.status }}
                    </div>
                  </template>

                  <template v-else-if="col.name === 'xActions'">
                    <q-btn
                      icon="print"
                      color="primary"
                      unelevated
                      no-caps
                      dense
                      size="sm"
                      class="q-mr-xs"
                      @click="printLabel(props.row)"
                    >
                      <q-tooltip>{{ t('ingredient.printLabel') }}</q-tooltip>
                    </q-btn>
                    <q-btn
                      icon="tune"
                      color="blue-8"
                      unelevated
                      round
                      dense
                      size="sm"
                      class="q-mr-xs"
                      @click="openStockAdjustDialog(props.row)"
                    >
                      <q-tooltip>Stock Adjustment</q-tooltip>
                    </q-btn>
                    <q-btn
                      icon="info"
                      color="info"
                      unelevated
                      round
                      dense
                      size="sm"
                      @click="openDetailDialog(props.row)"
                    >
                      <q-tooltip>{{ t('ingredient.infoHistory') }}</q-tooltip>
                    </q-btn>
                  </template>

                  <template v-else>
                    {{ col.value }}
                  </template>
                </q-td>
              </q-tr>

              <!-- Expansion Row -->
              <q-tr v-show="props.expand" :props="props" class="bg-grey-1">
                <q-td colspan="100%">
                  <div class="q-pa-md">
                    <!-- Intake Summary Info -->
                    <div class="row q-col-gutter-sm q-mb-md">
                      <div class="col-12 col-md-3">
                        <div class="text-subtitle2 q-mb-xs text-primary row items-center">
                          <q-icon name="info" class="q-mr-xs" />
                          General Info
                        </div>
                        <q-list bordered dense separator class="bg-white rounded-borders">
                          <q-item>
                            <q-item-section class="text-grey-7">ID</q-item-section>
                            <q-item-section side>{{ props.row.id }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">{{ t('ingredient.intakeLotId') }}</q-item-section>
                            <q-item-section side class="text-weight-bold">{{ props.row.intake_lot_id }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">Material Description</q-item-section>
                            <q-item-section side>{{ props.row.material_description }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">{{ t('ingredient.matSapCode') }}</q-item-section>
                            <q-item-section side>{{ props.row.mat_sap_code }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">RE Code</q-item-section>
                            <q-item-section side class="text-weight-bold text-blue-9">{{ props.row.re_code || '-' }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">{{ t('ingredient.uom') }}</q-item-section>
                            <q-item-section side>{{ props.row.uom }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">Status</q-item-section>
                            <q-item-section side>
                              <q-chip :color="getStatusColor(props.row.status)" text-color="white" dense size="sm">
                                {{ props.row.status }}
                              </q-chip>
                            </q-item-section>
                          </q-item>
                        </q-list>
                      </div>

                      <div class="col-12 col-md-3">
                        <div class="text-subtitle2 q-mb-xs text-primary row items-center">
                          <q-icon name="assignment" class="q-mr-xs" />
                          Logistics
                        </div>
                        <q-list bordered dense separator class="bg-white rounded-borders">
                          <q-item>
                            <q-item-section class="text-grey-7">{{ t('ingredient.lotId') }}</q-item-section>
                            <q-item-section side>{{ props.row.lot_id }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">{{ t('ingredient.poNo') }}</q-item-section>
                            <q-item-section side>{{ props.row.po_number || '-' }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">Intake From</q-item-section>
                            <q-item-section side>{{ props.row.intake_from || '-' }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">Intake To</q-item-section>
                            <q-item-section side>{{ props.row.intake_to || '-' }}</q-item-section>
                          </q-item>
                        </q-list>
                      </div>

                      <div class="col-12 col-md-3">
                        <div class="text-subtitle2 q-mb-xs text-primary row items-center">
                          <q-icon name="scale" class="q-mr-xs" />
                          Volumes
                        </div>
                        <q-list bordered dense separator class="bg-white rounded-borders">
                          <q-item>
                            <q-item-section class="text-grey-7">{{ t('ingredient.intakeVolume') }}</q-item-section>
                            <q-item-section side>{{ props.row.intake_vol }} kg</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">{{ t('ingredient.remainVolume') }}</q-item-section>
                            <q-item-section side class="text-negative text-weight-bolder">{{ props.row.remain_vol }} kg</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">{{ t('ingredient.pkgVol') }}</q-item-section>
                            <q-item-section side>{{ props.row.intake_package_vol || '-' }} kg</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">{{ t('ingredient.pkgs') }}</q-item-section>
                            <q-item-section side>{{ props.row.package_intake || '-' }}</q-item-section>
                          </q-item>
                        </q-list>
                      </div>

                      <div class="col-12 col-md-3">
                         <div class="text-subtitle2 q-mb-xs text-primary row items-center">
                          <q-icon name="history" class="q-mr-xs" />
                          Dates & Tracking
                        </div>
                        <q-list bordered dense separator class="bg-white rounded-borders">
                          <q-item>
                            <q-item-section class="text-grey-7">{{ t('ingredient.mfgDate') }}</q-item-section>
                            <q-item-section side>{{ formatDate(props.row.manufacturing_date) }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">{{ t('ingredient.expiryDate') }}</q-item-section>
                            <q-item-section side>{{ formatDate(props.row.expire_date) }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">{{ t('ingredient.intakeAt') }}</q-item-section>
                            <q-item-section side>{{ formatDateTime(props.row.intake_at) }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">Intake By</q-item-section>
                            <q-item-section side class="text-blue-7">{{ props.row.intake_by }}</q-item-section>
                          </q-item>
                        </q-list>
                      </div>
                    </div>

                    <!-- Package Details -->
                    <div class="text-subtitle2 q-mb-xs text-primary row items-center">
                       <q-icon name="inventory_2" class="q-mr-xs" />
                       Intake Package Details (Individual Weights)
                    </div>
                    
                    <div v-if="!props.row.packages || props.row.packages.length === 0" class="text-grey-7 italic q-pl-md">
                      No individual package data recorded for this lot.
                    </div>
                    
                    <div v-else style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px;">
                      <div v-for="pkg in [...props.row.packages].sort((a, b) => a.package_no - b.package_no)" :key="pkg.id || pkg.package_no">
                        <q-card flat bordered class="bg-white">
                          <q-item dense class="q-px-sm">
                            <q-item-section side class="q-pr-xs">
                              <q-btn icon="print" flat round dense size="sm" color="primary" @click="printSinglePackageLabel(props.row, pkg)" />
                            </q-item-section>
                            <q-item-section side class="q-pr-xs">
                              <span class="text-subtitle1 text-weight-medium">{{ pkg.package_no }}.</span>
                            </q-item-section>
                            <q-item-section>
                              <q-item-label class="text-weight-bold">{{ pkg.weight.toFixed(4) }} kg</q-item-label>
                            </q-item-section>
                          </q-item>
                        </q-card>
                      </div>
                    </div>

                    <!-- Usage Details (Pre-batch) -->
                    <div class="q-mt-md">
                      <div class="text-subtitle2 q-mb-xs text-primary row items-center">
                        <q-icon name="output" class="q-mr-xs" />
                        Usage Details (Pre-batch)
                        <q-btn flat dense round icon="refresh" size="sm" color="primary" class="q-ml-sm"
                          @click="fetchLotUsage(props.row.intake_lot_id)" />
                      </div>
                      <div v-if="!lotUsageMap[props.row.intake_lot_id]" class="text-grey-7 italic q-pl-md">
                        <q-btn flat dense size="sm" color="primary" label="Load usage data"
                          @click="fetchLotUsage(props.row.intake_lot_id)" />
                      </div>
                      <div v-else-if="lotUsageMap[props.row.intake_lot_id]?.length === 0" class="text-grey-7 italic q-pl-md">
                        No pre-batch usage recorded for this lot.
                      </div>
                      <q-markup-table v-else dense flat bordered separator="cell" class="text-caption" style="max-height: 250px; overflow-y: auto;">
                        <thead>
                          <tr class="bg-blue-1">
                            <th class="text-left">Batch Record ID</th>
                            <th class="text-left">Plan ID</th>
                            <th class="text-left">RE Code</th>
                            <th class="text-right">Volume (kg)</th>
                            <th class="text-center">Date</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="u in lotUsageMap[props.row.intake_lot_id]" :key="u.id">
                            <td class="text-bold">{{ u.batch_record_id || '-' }}</td>
                            <td>{{ u.plan_id || '-' }}</td>
                            <td class="text-blue-9 text-bold">{{ u.re_code || '-' }}</td>
                            <td class="text-right text-red-8 text-bold">−{{ u.take_volume?.toFixed(4) }}</td>
                            <td class="text-center">{{ formatDateTime(u.created_at) }}</td>
                          </tr>
                          <tr class="bg-grey-2">
                            <td colspan="3" class="text-right text-bold">Total Used:</td>
                            <td class="text-right text-red-9 text-bold">
                              −{{ lotUsageMap[props.row.intake_lot_id]?.reduce((s: number, u: any) => s + (u.take_volume || 0), 0).toFixed(4) }} kg
                            </td>
                            <td class="text-center text-grey-7">{{ lotUsageMap[props.row.intake_lot_id]?.length }} records</td>
                          </tr>
                        </tbody>
                      </q-markup-table>
                    </div>
                  </div>
                </q-td>
              </q-tr>
            </template>
          </q-table>
        </q-card>
      </div>
    </div>

    <!-- Ingredient Code Entry Dialog -->
    <q-dialog v-model="showIngredientDialog">
      <q-card style="min-width: 400px">
        <q-card-section class="bg-info text-white">
          <div class="text-h6">{{ t('ingredient.enterCode') }}</div>
        </q-card-section>

        <q-card-section class="q-pt-md">
          <q-input
            v-model="tempIngredientId"
            :label="t('ingredient.ingredientId')"
            outlined
            autofocus
            @keyup.enter="confirmIngredientCode"
          >
            <template v-slot:prepend>
              <q-icon name="qr_code_2" color="info" />
            </template>
            <template v-slot:hint>
              {{
                mqttConnected
                  ? 'Listening from MQTT or type manually'
                  : 'Type ingredient code manually'
              }}
            </template>
          </q-input>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat :label="t('common.cancel')" color="grey" @click="cancelIngredientDialog" />
          <q-btn
            :label="t('common.confirm')"
            color="info"
            @click="confirmIngredientCode"
            :disable="!tempIngredientId"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Detail Dialog -->
    <q-dialog v-model="showDetailDialog">
      <q-card style="min-width: 500px" class="q-pa-md">
        <q-card-section class="bg-info text-white row items-center">
          <div class="text-h6">{{ t('ingredient.detailTitle') }} - {{ selectedRecord?.intake_lot_id }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="q-pt-md">
          <div class="row q-col-gutter-sm">
            <div class="col-6 text-weight-bold">{{ t('ingredient.intakeLotId') }}:</div>
            <div class="col-6">{{ selectedRecord?.intake_lot_id }}</div>

            <div class="col-6 text-weight-bold">{{ t('ingredient.lotId') }}:</div>
            <div class="col-6">{{ selectedRecord?.lot_id }}</div>

            <div class="col-6 text-weight-bold">{{ t('ingredient.matSapCode') }}:</div>
            <div class="col-6">{{ selectedRecord?.mat_sap_code }}</div>

            <div class="col-6 text-weight-bold">{{ t('ingredient.reCode') }}:</div>
            <div class="col-6">{{ selectedRecord?.re_code || '-' }}</div>

            <div class="col-6 text-weight-bold">Intake From:</div>
            <div class="col-6">{{ selectedRecord?.intake_from || '-' }}</div>

            <div class="col-6 text-weight-bold">{{ t('ingredient.poNo') }}:</div>
            <div class="col-6">{{ selectedRecord?.po_number || '-' }}</div>

            <div class="col-6 text-weight-bold">{{ t('ingredient.mfgDate') }}:</div>
            <div class="col-6">{{ formatDate(selectedRecord?.manufacturing_date) }}</div>

            <div class="col-6 text-weight-bold">{{ t('ingredient.intakeVolume') }}:</div>
            <div class="col-6">{{ selectedRecord?.intake_vol }} kg</div>

            <div class="col-6 text-weight-bold">{{ t('ingredient.remainVolume') }}:</div>
            <div class="col-6 text-negative text-weight-bolder">
              {{ selectedRecord?.remain_vol }} kg
            </div>

            <div class="col-6 text-weight-bold">{{ t('ingredient.pkgVol') }}:</div>
            <div class="col-6">{{ selectedRecord?.intake_package_vol || '-' }} kg</div>

            <div class="col-6 text-weight-bold">{{ t('ingredient.packages') }}:</div>
            <div class="col-6">{{ selectedRecord?.package_intake || '-' }}</div>

            <div class="col-6 text-weight-bold">{{ t('ingredient.expiryDate') }}:</div>
            <div class="col-6">{{ formatDate(selectedRecord?.expire_date) }}</div>

            <div class="col-6 text-weight-bold">{{ t('common.status') }}:</div>
            <div class="col-6">
              <q-chip
                :color="getStatusColor(selectedRecord?.status || '')"
                text-color="white"
                dense
                clickable
                class="cursor-pointer"
              >
                {{ selectedRecord?.status }}
                <q-menu auto-close>
                  <q-list style="min-width: 100px">
                    <q-item
                      v-for="opt in statusOptions"
                      :key="opt"
                      clickable
                      v-close-popup
                      @click="updateRecordStatus(selectedRecord!, opt)"
                    >
                      <q-item-section>
                        <div class="row items-center">
                          <q-icon
                            name="circle"
                            :color="getStatusColor(opt)"
                            size="xs"
                            class="q-mr-xs"
                          />
                          {{ opt }}
                        </div>
                      </q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-chip>
              <q-icon name="edit" size="xs" color="grey-7" class="q-ml-xs" />
            </div>

            <q-separator class="col-12 q-my-sm" />

            <div class="col-6 text-weight-bold">{{ t('ingredient.intakeBy') }}:</div>
            <div class="col-6">{{ selectedRecord?.intake_by }}</div>

            <div class="col-6 text-weight-bold">{{ t('ingredient.intakeAt') }}:</div>
            <div class="col-6">
              {{ selectedRecord ? new Date(selectedRecord.intake_at).toLocaleString('en-GB') : '' }}
            </div>

            <div class="col-6 text-weight-bold">{{ t('ingredient.lastEditedBy') }}:</div>
            <div class="col-6">{{ selectedRecord?.edit_by || '-' }}</div>

            <div class="col-6 text-weight-bold">{{ t('ingredient.lastEditedAt') }}:</div>
            <div class="col-6">
              {{
                selectedRecord?.edit_at ? new Date(selectedRecord.edit_at).toLocaleString('en-GB') : '-'
              }}
            </div>
          </div>

          <!-- History Section -->
          <!-- History Section -->
          <div class="q-mt-lg">
            <div class="text-subtitle1 text-weight-bold q-mb-sm row items-center">
              <q-icon name="history" color="primary" class="q-mr-xs" />
              {{ t('ingredient.historyChanges') }}
            </div>
            <div
              v-if="!selectedRecord?.history || selectedRecord.history.length === 0"
              class="text-grey-7 q-pl-sm"
            >
              {{ t('ingredient.noHistory') }}
            </div>
            <q-list v-else bordered separator dense class="rounded-borders">
              <q-item v-for="h in [...selectedRecord.history].reverse()" :key="h.id">
                <q-item-section>
                  <q-item-label class="text-weight-bold">
                    {{ h.action }}
                    <span v-if="h.old_status" class="text-weight-normal text-grey-7">
                      ({{ h.old_status }} → {{ h.new_status }})
                    </span>
                  </q-item-label>
                  <q-item-label caption>
                    By {{ h.changed_by }} at {{ new Date(h.changed_at).toLocaleString('en-GB') }}
                  </q-item-label>
                  <q-item-label v-if="h.remarks" caption italic> "{{ h.remarks }}" </q-item-label>
                </q-item-section>
                <q-item-section side v-if="h.new_status">
                  <q-chip :color="getStatusColor(h.new_status)" text-color="white" size="xs">
                    {{ h.new_status }}
                  </q-chip>
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn
            flat
            :label="t('ingredient.printLabel')"
            color="secondary"
            icon="print"
            @click="printLabel(selectedRecord!)"
          />
          <q-btn flat :label="t('common.close')" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Intake From Config Dialog (ingredient_intake_from table) -->
    <q-dialog v-model="showIntakeFromDialog">
      <q-card style="min-width: 400px">
        <q-card-section class="bg-primary text-white row items-center">
          <div class="text-h6">Manage Intake Source</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div class="row q-col-gutter-sm items-center q-mb-md">
            <div class="col">
              <q-input
                v-model="newIntakeFromName"
                label="Source Name (e.g. Supplier)"
                outlined
                dense
                @keyup.enter="addIntakeFrom"
              />
            </div>
            <div class="col-auto">
              <q-btn icon="add" color="primary" round @click="addIntakeFrom" :disable="!newIntakeFromName" />
            </div>
          </div>

          <q-list bordered separator>
            <q-item v-for="item in intakeFromList" :key="item.id">
              <q-item-section>
                <q-item-label>{{ item.name }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-btn icon="delete" color="negative" flat round dense @click="deleteIntakeFrom(item.id)" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Intake To Config Dialog (warehouses table) -->
    <q-dialog v-model="showIntakeToDialog">
      <q-card style="min-width: 400px">
        <q-card-section class="bg-primary text-white row items-center">
          <div class="text-h6">Manage Intake Destination (Warehouses)</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div class="row q-col-gutter-sm items-center q-mb-md">
            <div class="col-12 col-md-5">
              <q-input
                v-model="newIntakeToId"
                label="Warehouse ID (e.g. FH)"
                outlined
                dense
              />
            </div>
            <div class="col-12 col-md-5">
              <q-input
                v-model="newIntakeToName"
                label="Name (e.g. Flavour House)"
                outlined
                dense
                @keyup.enter="addWarehouse"
              />
            </div>
            <div class="col-auto">
              <q-btn icon="add" color="primary" round @click="addWarehouse" :disable="!newIntakeToId || !newIntakeToName" />
            </div>
          </div>

          <q-list bordered separator>
            <q-item v-for="wh in intakeToList" :key="wh.warehouse_id">
              <q-item-section>
                <q-item-label>{{ wh.warehouse_id }} - {{ wh.name }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-btn icon="delete" color="negative" flat round dense @click="deleteWarehouse(wh.warehouse_id)" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    </div><!-- end intake tab -->

    <!-- ═══ STOCK ADJUSTMENT DIALOG ═══ -->
    <q-dialog v-model="showAdjustDialog" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card class="column" style="max-width: 100vw;">
        <!-- Dialog Header -->
        <q-card-section class="q-pa-sm bg-blue-8 text-white row items-center justify-between">
          <div class="row items-center q-gutter-sm">
            <q-icon name="tune" size="sm" />
            <div class="text-h6 text-weight-bold">Stock Adjustment</div>
            <q-badge v-if="adjSelectedLot" color="white" text-color="blue-9" class="text-weight-bold">
              {{ adjSelectedReCode }} | {{ adjSelectedLotId }}
            </q-badge>
          </div>
          <div class="row items-center q-gutter-sm">
            <!-- Report Date Range -->
            <q-input
              v-model="adjReportFrom" type="date" dense outlined
              label="From" dark
              style="width: 150px;"
              input-class="text-white" label-color="white"
            />
            <q-input
              v-model="adjReportTo" type="date" dense outlined
              label="To" dark
              style="width: 150px;"
              input-class="text-white" label-color="white"
            />
            <q-btn icon="print" flat round dense text-color="white" @click="printAdjustmentReport">
              <q-tooltip>Print Adjustment Report</q-tooltip>
            </q-btn>
            <q-separator vertical dark class="q-mx-xs" />
            <q-btn icon="close" flat round dense text-color="white" v-close-popup />
          </div>
        </q-card-section>

        <q-card-section class="col q-pa-md" style="overflow-y: auto;">

      <!-- Adjustment Form -->
      <q-card flat bordered class="shadow-1 q-mb-md">
        <q-card-section class="q-pa-sm bg-blue-8 text-white row items-center">
          <q-icon name="tune" class="q-mr-xs" />
          <div class="text-subtitle2 text-weight-bold">New Stock Adjustment</div>
        </q-card-section>

        <q-card-section class="q-pa-md bg-grey-1">
          <!-- Row 1: RE-Code + Lot ID Selection -->
          <div class="row q-col-gutter-md q-mb-md">
            <div class="col-12 col-md-4">
              <div class="text-caption text-weight-bold q-mb-xs">① Select RE-Code (Active Only)</div>
              <q-select
                v-model="adjSelectedReCode"
                :options="activeReCodes"
                option-value="re_code"
                :option-label="(opt: any) => `${opt.re_code} — ${opt.material_description}`"
                emit-value map-options
                outlined dense clearable
                bg-color="white"
                placeholder="Choose material..."
              >
                <template v-slot:no-option>
                  <q-item><q-item-section>No active materials</q-item-section></q-item>
                </template>
              </q-select>
            </div>

            <div class="col-12 col-md-4">
              <div class="text-caption text-weight-bold q-mb-xs">② Select Intake Lot ID</div>
              <q-select
                v-model="adjSelectedLotId"
                :options="adjLotsForReCode"
                option-value="intake_lot_id"
                :option-label="(opt: any) => `${opt.intake_lot_id}  (${opt.remain_vol?.toFixed(3)} kg)`"
                emit-value map-options
                outlined dense clearable
                bg-color="white"
                placeholder="Choose lot..."
                :disable="!adjSelectedReCode"
              >
                <template v-slot:no-option>
                  <q-item><q-item-section>No lots for this material</q-item-section></q-item>
                </template>
              </q-select>
            </div>

            <div class="col-12 col-md-4">
              <div class="text-caption text-weight-bold q-mb-xs">Material Info</div>
              <q-input
                :model-value="adjSelectedLot ? `${adjSelectedLot.mat_sap_code} — ${adjSelectedLot.material_description || adjSelectedLot.re_code}` : ''"
                outlined dense readonly
                bg-color="grey-2"
                placeholder="(auto-filled)"
              />
            </div>
          </div>

          <!-- Stock Overview Table for selected RE-Code -->
          <div v-if="adjSelectedReCode && stockOverviewLots.length > 0" class="q-mb-md">
            <q-card flat bordered class="shadow-0 overflow-hidden" style="border-radius: 6px;">
              <q-card-section class="q-pa-xs bg-indigo-8 text-white row items-center justify-between">
                <div class="text-caption text-weight-bold">
                  <q-icon name="inventory" class="q-mr-xs" size="xs" />
                  Stock Overview — {{ adjSelectedReCode }} ({{ stockOverviewSummary.totalLots }} lots)
                </div>
                <div class="text-caption">
                  Total Remaining: <strong>{{ stockOverviewSummary.totalRemaining.toFixed(3) }} kg</strong>
                </div>
              </q-card-section>

              <q-table
                :rows="stockOverviewLots"
                :columns="[
                  { name: 'intake_lot_id', label: 'Lot ID', field: 'intake_lot_id', align: 'left' as const, sortable: true },
                  { name: 'intake_from', label: 'From', field: 'intake_from', align: 'left' as const },
                  { name: 'lot_id', label: 'Lot Date', field: 'lot_id', align: 'center' as const },
                  { name: 'mfg_date', label: 'Mfg Date', field: 'mfg_date', align: 'center' as const },
                  { name: 'expire_date', label: 'Expire', field: 'expire_date', align: 'center' as const },
                  { name: 'intake_vol', label: 'Intake (kg)', field: 'intake_vol', align: 'right' as const, sortable: true, format: (v: any) => v?.toFixed(3) },
                  { name: 'remain_vol', label: 'Remaining (kg)', field: 'remain_vol', align: 'right' as const, sortable: true, format: (v: any) => v?.toFixed(3) },
                  { name: 'pct', label: '% Left', field: (row: any) => row.intake_vol ? ((row.remain_vol / row.intake_vol) * 100) : 0, align: 'center' as const, format: (v: any) => v?.toFixed(1) + '%' },
                ]"
                row-key="intake_lot_id"
                flat dense hide-bottom
                class="text-caption"
                :pagination="{ rowsPerPage: 0 }"
                style="max-height: 200px;"
                virtual-scroll
              >
                <template v-slot:body="props">
                  <q-tr
                    :props="props"
                    :class="adjSelectedLotId === props.row.intake_lot_id ? 'bg-blue-1 text-weight-bold' : ''"
                    style="cursor: pointer;"
                    @click="adjSelectedLotId = props.row.intake_lot_id"
                  >
                    <q-td v-for="col in props.cols" :key="col.name" :props="props">
                      <template v-if="col.name === 'remain_vol'">
                        <span :class="props.row.remain_vol <= 0 ? 'text-red-8' : 'text-green-8'" class="text-weight-bold">
                          {{ col.value }}
                        </span>
                      </template>
                      <template v-else-if="col.name === 'pct'">
                        <q-badge
                          :color="(props.row.remain_vol / props.row.intake_vol) > 0.5 ? 'green' : (props.row.remain_vol / props.row.intake_vol) > 0.2 ? 'orange' : 'red'"
                          text-color="white" class="text-weight-bold"
                        >
                          {{ col.value }}
                        </q-badge>
                      </template>
                      <template v-else>{{ col.value }}</template>
                    </q-td>
                  </q-tr>
                </template>

                <!-- Summary Footer -->
                <template v-slot:bottom-row>
                  <q-tr class="bg-indigo-1 text-weight-bold">
                    <q-td colspan="5" class="text-right text-indigo-9">
                      TOTAL ({{ stockOverviewSummary.totalLots }} lots)
                    </q-td>
                    <q-td class="text-right text-indigo-9">{{ stockOverviewSummary.totalIntake.toFixed(3) }}</q-td>
                    <q-td class="text-right text-indigo-9">{{ stockOverviewSummary.totalRemaining.toFixed(3) }}</q-td>
                    <q-td class="text-center text-indigo-9">
                      {{ stockOverviewSummary.totalIntake ? ((stockOverviewSummary.totalRemaining / stockOverviewSummary.totalIntake) * 100).toFixed(1) : 0 }}%
                    </q-td>
                  </q-tr>
                </template>
              </q-table>
            </q-card>
          </div>

          <!-- Row 2: Stock Summary Cards -->
          <div v-if="adjSelectedLot" class="row q-col-gutter-md q-mb-md">
            <div class="col-12 col-md-3">
              <q-card flat bordered class="bg-blue-1 text-center q-pa-sm">
                <div class="text-caption text-grey-7">Total Intake</div>
                <div class="text-h6 text-weight-bold text-blue-9">{{ adjTotalIntake.toFixed(3) }} <span class="text-caption">kg</span></div>
              </q-card>
            </div>
            <div class="col-12 col-md-3">
              <q-card flat bordered class="bg-orange-1 text-center q-pa-sm">
                <div class="text-caption text-grey-7">Current Remaining</div>
                <div class="text-h6 text-weight-bold text-orange-9">{{ adjRemaining.toFixed(3) }} <span class="text-caption">kg</span></div>
              </q-card>
            </div>
            <div class="col-12 col-md-3">
              <q-card flat bordered :class="adjComputedType === 'increase' ? 'bg-green-1' : adjComputedType === 'decrease' ? 'bg-red-1' : 'bg-grey-1'" class="text-center q-pa-sm">
                <div class="text-caption text-grey-7">Difference</div>
                <div class="text-h6 text-weight-bold" :class="adjComputedType === 'increase' ? 'text-green-8' : adjComputedType === 'decrease' ? 'text-red-8' : 'text-grey-6'">
                  <template v-if="adjComputedType">
                    {{ adjComputedType === 'increase' ? '+' : '−' }}{{ adjComputedQty.toFixed(3) }} <span class="text-caption">kg</span>
                  </template>
                  <template v-else>—</template>
                </div>
              </q-card>
            </div>
            <div class="col-12 col-md-3">
              <q-card flat bordered class="bg-blue-1 text-center q-pa-sm">
                <div class="text-caption text-grey-7">New Value</div>
                <div class="text-h6 text-weight-bold" :class="(adjNewRemainVol ?? adjRemaining) < 0 ? 'text-red-8' : 'text-blue-9'">
                  {{ (adjNewRemainVol ?? adjRemaining).toFixed(3) }} <span class="text-caption">kg</span>
                </div>
              </q-card>
            </div>
          </div>

          <!-- Row 3: New Value, Reason, Remark, By, Submit -->
          <div class="row q-col-gutter-md items-end">
            <div class="col-12 col-md-2">
              <div class="text-caption text-weight-bold q-mb-xs">③ New Adjust Value (kg)</div>
              <q-input
                v-model.number="adjNewRemainVol"
                outlined dense type="number" step="0.001"
                bg-color="white" placeholder="0.000"
                :disable="!adjSelectedLot"
              />
            </div>

            <div class="col-12 col-md-2">
              <div class="text-caption text-weight-bold q-mb-xs">Reason</div>
              <q-select v-model="adjReason" :options="adjReasonOptions" outlined dense bg-color="white" placeholder="Select..." />
            </div>

            <div class="col-12 col-md-3">
              <div class="text-caption text-weight-bold q-mb-xs">Remark</div>
              <q-input v-model="adjRemark" outlined dense bg-color="white" placeholder="Optional notes..." />
            </div>

            <div class="col-12 col-md-1">
              <div class="text-caption text-weight-bold q-mb-xs">By</div>
              <q-input v-model="adjBy" outlined dense bg-color="white" />
            </div>

            <div class="col-12 col-md-4">
              <q-btn
                label="Submit Adjustment"
                color="blue-8" icon="check"
                unelevated no-caps class="full-width"
                :loading="adjSubmitting"
                :disable="!adjSelectedLot || adjNewRemainVol === null || !adjReason"
                @click="submitAdjustment"
              />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Adjustment History Table -->
      <q-card flat bordered class="shadow-1 overflow-hidden" style="border-radius: 8px;">
        <q-card-section class="q-pa-sm bg-blue-7 text-white row items-center justify-between">
          <div class="text-subtitle2 text-weight-bold">
            <q-icon name="history" class="q-mr-xs" />
            Adjustment History ({{ filteredAdjustments.length }})
          </div>
          <q-btn flat dense round icon="refresh" color="white" @click="fetchAdjustments" />
        </q-card-section>

        <q-table
          :rows="filteredAdjustments"
          :columns="adjColumns"
          row-key="id"
          flat dense
          class="text-caption"
          :pagination="{ rowsPerPage: 50 }"
          style="max-height: calc(100vh - 500px);"
        >
          <template v-slot:header="props">
            <q-tr :props="props" class="bg-blue-1">
              <q-th v-for="col in props.cols" :key="col.name" :props="props" class="text-weight-bold">
                {{ col.label }}
              </q-th>
            </q-tr>
            <!-- Filter Row -->
            <q-tr class="bg-grey-1">
              <q-td v-for="col in props.cols" :key="'adj-filter-' + col.name" style="padding: 2px 4px;">
                <q-input
                  v-model="adjColumnFilters[col.name]"
                  dense outlined clearable
                  placeholder="🔍"
                  size="xs"
                  style="min-width: 50px; font-size: 0.75rem;"
                  bg-color="white"
                  @click.stop
                />
              </q-td>
            </q-tr>
          </template>

          <template v-slot:body="props">
            <q-tr :props="props">
              <q-td v-for="col in props.cols" :key="col.name" :props="props">
                <template v-if="col.name === 'adjust_type'">
                  <q-badge
                    :color="props.row.adjust_type === 'increase' ? 'green' : 'red'"
                    text-color="white"
                    class="text-weight-bold"
                  >
                    {{ props.row.adjust_type === 'increase' ? '↑ +' : '↓ −' }}
                  </q-badge>
                </template>
                <template v-else-if="col.name === 'adjust_qty'">
                  <span :class="props.row.adjust_type === 'increase' ? 'text-green-8 text-weight-bold' : 'text-red-8 text-weight-bold'">
                    {{ props.row.adjust_type === 'increase' ? '+' : '−' }}{{ props.row.adjust_qty?.toFixed(3) }}
                  </span>
                </template>
                <template v-else-if="col.name === 'prev_remain_vol' || col.name === 'new_remain_vol'">
                  {{ col.value?.toFixed(3) }}
                </template>
                <template v-else>
                  {{ col.value }}
                </template>
              </q-td>
            </q-tr>
          </template>
        </q-table>
      </q-card>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Stock Summary Report Dialog -->
    <q-dialog v-model="showSummaryReport">
      <q-card style="min-width: 450px;">
        <q-card-section class="bg-blue-9 text-white">
          <div class="row items-center q-gutter-sm">
            <q-icon name="assessment" size="sm" />
            <div class="text-h6">Stock Summary Report</div>
          </div>
        </q-card-section>

        <q-card-section class="q-pt-lg">
          <div class="text-subtitle2 q-mb-sm text-grey-8">Select date range for the report</div>
          <div class="row q-col-gutter-md">
            <div class="col-6">
              <q-input filled v-model="summaryFromDate" label="From Date" mask="##/##/####" placeholder="DD/MM/YYYY">
                <template v-slot:append>
                  <q-icon name="event" class="cursor-pointer">
                    <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                      <q-date v-model="summaryFromDate" mask="DD/MM/YYYY">
                        <div class="row items-center justify-end">
                          <q-btn v-close-popup label="Close" color="primary" flat />
                        </div>
                      </q-date>
                    </q-popup-proxy>
                  </q-icon>
                </template>
              </q-input>
            </div>
            <div class="col-6">
              <q-input filled v-model="summaryToDate" label="To Date" mask="##/##/####" placeholder="DD/MM/YYYY">
                <template v-slot:append>
                  <q-icon name="event" class="cursor-pointer">
                    <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                      <q-date v-model="summaryToDate" mask="DD/MM/YYYY">
                        <div class="row items-center justify-end">
                          <q-btn v-close-popup label="Close" color="primary" flat />
                        </div>
                      </q-date>
                    </q-popup-proxy>
                  </q-icon>
                </template>
              </q-input>
            </div>
          </div>
          <div class="q-mt-md text-caption text-grey-7">
            Report includes: Intake lots, stock details, pre-batch usage, and adjustments grouped by warehouse (FH, SPP).
          </div>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="Cancel" color="grey" v-close-popup />
          <q-btn
            icon="print"
            label="Generate Report"
            color="blue-9"
            :loading="summaryLoading"
            @click="printSummaryReport"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Traceability Report Dialog -->
    <q-dialog v-model="showTraceDialog">
      <q-card style="min-width: 480px;">
        <q-card-section class="bg-primary text-white">
          <div class="text-h6"><q-icon name="device_hub" class="q-mr-sm" />Traceability Report</div>
          <div class="text-caption">Select an Intake Lot ID (forward trace) or Batch ID (backward trace)</div>
        </q-card-section>
        <q-card-section>
          <q-select
            v-model="traceSearchId"
            :options="traceFilteredOptions"
            :loading="traceOptionsLoading"
            label="Lot ID or Batch ID"
            filled
            use-input
            input-debounce="200"
            emit-value
            map-options
            option-value="value"
            option-label="label"
            @filter="onTraceFilter"
            clearable
            popup-content-class="trace-dropdown"
          >
            <template #prepend><q-icon name="search" /></template>
            <template #no-option>
              <q-item>
                <q-item-section class="text-grey text-italic">
                  {{ traceOptionsLoading ? 'Loading...' : 'No matching IDs found — type to filter' }}
                </q-item-section>
              </q-item>
            </template>
            <template #option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section>
                  <q-item-label>{{ scope.opt.label }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-separator v-if="scope.index === traceFilteredOptions.findIndex(o => o.group === 'Batches') - 1" />
            </template>
          </q-select>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="primary" icon="print" label="Generate Report" :loading="traceLoading" @click="printTraceReport" :disable="!traceSearchId" />
        </q-card-actions>
      </q-card>
    </q-dialog>

  </q-page>
</template>

<style scoped>
.intake-table :deep(td),
.intake-table :deep(th) {
  font-size: 14px !important;
}
.custom-table-border {
  border: 1px solid #777;
  border-radius: 8px;
}
</style>

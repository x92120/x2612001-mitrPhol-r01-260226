<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useQuasar } from 'quasar'
import { appConfig } from '../appConfig/config'
import { useLabelPrinter } from '../composables/useLabelPrinter'

const $q = useQuasar()
const { getAuthHeader, user } = useAuth()
const { generateLabelSvg } = useLabelPrinter()

// --- State ---
const boxId = ref('')
const boxDetails = ref<any>(null)
const loading = ref(false)

// Box scan input (top bar)
const boxScanInput = ref('')

// Bag scan input (above bag list)
const bagScanInput = ref('')
const bagScanRef = ref<any>(null)

// Scanner Simulator Dialog
const showScannerDialog = ref(false)
const scannerMode = ref<'box' | 'bag'>('box')
const scannerLoading = ref(false)

// All available batches for the simulator
const allBatches = ref<any[]>([])

// Label preview in simulator
const previewLabelSvg = ref('')
const previewBagLabels = ref<{svg: string, batch_record_id: string, re_code: string}[]>([])
const selectedSimBatch = ref<any>(null)

// Feedback overlay
const feedback = ref<{ show: boolean, type: 'success' | 'error' | 'warning', message: string, title: string }>({
    show: false,
    type: 'success',
    message: '',
    title: ''
})

// --- Computed ---
const scannedCount = computed(() => {
    if (!boxDetails.value) return 0
    return boxDetails.value.bags.filter((b: any) => b.status === 1).length
})

const errorCount = computed(() => {
    if (!boxDetails.value) return 0
    return boxDetails.value.bags.filter((b: any) => b.status === 2).length
})

const totalCount = computed(() => {
    if (!boxDetails.value) return 0
    return boxDetails.value.total_bags || 0
})

const progress = computed(() => {
    if (totalCount.value === 0) return 0
    return scannedCount.value / totalCount.value
})

const allVerified = computed(() => {
    if (!boxDetails.value || totalCount.value === 0) return false
    return boxDetails.value.bags.every((b: any) => b.status === 1)
})

// --- Methods ---

const fetchPlansAndBatches = async () => {
    try {
        const plans = await $fetch<any[]>(`${appConfig.apiBaseUrl}/production-plans/`, {
            headers: getAuthHeader() as Record<string, string>
        })

        const batches: any[] = []
        plans.forEach((p: any) => {
            if (p.batches) {
                p.batches.forEach((b: any) => {
                    batches.push({ ...b, plan_id: p.plan_id, sku_id: p.sku_id, sku_name: p.sku_name })
                })
            }
        })
        allBatches.value = batches
    } catch (err) {
        console.error('Error fetching batches:', err)
    }
}

const fetchBoxDetails = async (id: string) => {
    loading.value = true
    try {
        const data = await $fetch<any>(`${appConfig.apiBaseUrl}/prebatch-recs/recheck-box/${id}`, {
            headers: getAuthHeader() as Record<string, string>
        })
        boxDetails.value = data
        boxId.value = id
        showFeedback('success', `Box loaded: ${data.total_bags} bags found`, 'BOX SCANNED')
        // Auto-focus bag scan for immediate scanning
        nextTick(() => { bagScanRef.value?.focus() })
    } catch (error: any) {
        console.error('Error fetching box details:', error)
        $q.notify({
            type: 'negative',
            message: error.data?.detail || 'Box not found or no bags inside',
            position: 'top'
        })
        boxDetails.value = null
    } finally {
        loading.value = false
    }
}

const parseAndHandleScan = (barcode: string, context: 'box' | 'bag') => {
    barcode = barcode.trim()
    if (!barcode) return

    // Parse QR code format: plan_id,batch_id,TYPE,extra...
    const parts = barcode.split(',')

    if (context === 'box') {
        if (parts.length >= 3 && parts[2] === 'BOX') {
            // Box QR: plan_id,batch_id,BOX,bag_count,total_vol
            fetchBoxDetails(parts[1]!)
        } else {
            // Plain text as box ID
            fetchBoxDetails(barcode)
        }
    } else {
        // Bag scan
        if (parts.length >= 4 && parts[2] !== 'BOX') {
            // Bag QR: plan_id,batch_record_id,re_code,net_volume
            verifyBag(parts[1]!)
        } else {
            // Plain text as bag barcode
            verifyBag(barcode)
        }
    }
}

const verifyBag = async (bagBarcode: string) => {
    if (!boxDetails.value) {
        $q.notify({ type: 'warning', message: 'Scan a Box first!' })
        return
    }

    loading.value = true
    try {
        const response = await $fetch<any>(`${appConfig.apiBaseUrl}/prebatch-recs/recheck-bag`, {
            method: 'POST',
            headers: getAuthHeader() as Record<string, string>,
            body: {
                box_id: boxId.value,
                bag_barcode: bagBarcode,
                operator: user.value?.username || 'Operator'
            }
        })

        if (response.status === 'OK') {
            showFeedback('success', `${response.bag.re_code} — ${response.bag.actual}kg ✓`, 'RE-CHECK OK')
            playSound('success')
        } else {
            showFeedback('error', `${response.bag.re_code}: Expected ${response.bag.target}kg, got ${response.bag.actual}kg (diff: ${response.bag.diff.toFixed(3)}kg)`, 'WEIGHT MISMATCH')
            playSound('error')
        }

        // Refresh box details
        await fetchBoxDetails(boxId.value)
    } catch (error: any) {
        showFeedback('error', error.data?.detail || 'Verification failed', 'ERROR')
        playSound('error')
    } finally {
        loading.value = false
        bagScanInput.value = ''
        // Re-focus bag scan input for next scan
        nextTick(() => { bagScanRef.value?.focus() })
    }
}

const releaseBatch = async () => {
    if (!boxId.value) return
    
    loading.value = true
    try {
        await $fetch(`${appConfig.apiBaseUrl}/production-batches/${boxId.value}/release`, {
            method: 'PATCH',
            headers: getAuthHeader() as Record<string, string>
        })
        
        showFeedback('success', 'Batch approved and released!', 'PRODUCTION READY')
        playSound('success')
        await fetchBoxDetails(boxId.value)
    } catch (error: any) {
        $q.notify({
            type: 'negative',
            message: error.data?.detail || 'Failed to release batch',
            position: 'top'
        })
    } finally {
        loading.value = false
    }
}

const resetBox = () => {
    boxDetails.value = null
    boxId.value = ''
    boxScanInput.value = ''
    bagScanInput.value = ''
}

// --- Scanner Simulator ---

const openScannerSimulator = (mode: 'box' | 'bag') => {
    scannerMode.value = mode
    showScannerDialog.value = true
    if (allBatches.value.length === 0) {
        scannerLoading.value = true
        fetchPlansAndBatches().then(() => { scannerLoading.value = false })
    }
}

const onSimSelectBatch = async (batch: any) => {
    selectedSimBatch.value = batch
    scannerLoading.value = true
    
    try {
        // Fetch all bag records for this batch
        const records = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-recs/by-batch/${batch.batch_id}`, {
            headers: getAuthHeader() as Record<string, string>
        })
        
        // Generate the Box Label
        const summaryMap: Record<string, { re_code: string, weight: number, count: number }> = {}
        records.forEach((r: any) => {
            const code = (r.re_code || '---').trim()
            if (!summaryMap[code]) summaryMap[code] = { re_code: code, weight: 0, count: 0 }
            summaryMap[code].weight += (r.net_volume || 0)
            summaryMap[code].count++
        })
        const sortedSummary = Object.values(summaryMap).sort((a, b) => a.re_code.localeCompare(b.re_code))
        const ingredientsSvg = sortedSummary.map((s, idx) =>
            `<tspan x="25" dy="${idx === 0 ? '0' : '1.2em'}">${s.re_code.padEnd(10)} | ${s.weight.toFixed(3).padStart(8)} kg | ${s.count} packs</tspan>`
        ).join('')
        
        const totalVol = records.reduce((sum: number, r: any) => sum + (r.net_volume || 0), 0)
        
        const boxMapping = {
            BoxID: batch.batch_id,
            BatchID: batch.batch_id,
            BagCount: records.length,
            NetWeight: totalVol.toFixed(3),
            Operator: user.value?.username || 'Operator',
            Timestamp: new Date().toLocaleString('en-GB', {
                day: '2-digit', month: '2-digit', year: 'numeric',
                hour: '2-digit', minute: '2-digit', second: '2-digit'
            }),
            BoxQRCode: `${batch.plan_id},${batch.batch_id},BOX,${records.length},${totalVol.toFixed(3)}`,
            prebatch_recs: ingredientsSvg,
            SKU: batch.sku_id,
            PlanID: batch.plan_id,
            WHManifest: '-'
        }
        
        const boxSvg = await generateLabelSvg('packingbox-label', boxMapping as any)
        previewLabelSvg.value = boxSvg || ''
        
        // Generate individual bag labels
        const bagLabels: {svg: string, batch_record_id: string, re_code: string}[] = []
        for (const record of records) {
            const bagMapping = {
                RecipeName: batch.sku_name || batch.sku_id || '-',
                BaseQuantity: batch.batch_size || 0,
                ItemNumber: '-',
                RefCode: record.re_code || '-',
                OrderCode: batch.plan_id || '-',
                BatchSize: batch.batch_size || 0,
                Weight: `${(record.net_volume || 0).toFixed(3)} / ${(record.total_volume || 0).toFixed(3)}`,
                Packages: `${record.package_no || 1} / ${record.total_packages || 1}`,
                LotID: record.intake_lot_id || '-',
                QRCode: `${batch.plan_id},${record.batch_record_id},${record.re_code},${record.net_volume}`,
                SmallQRCode: `${batch.plan_id},${record.batch_record_id},${record.re_code},${record.net_volume}`
            }
            const svg = await generateLabelSvg('prebatch-label', bagMapping as any)
            if (svg) {
                bagLabels.push({
                    svg,
                    batch_record_id: record.batch_record_id,
                    re_code: record.re_code
                })
            }
        }
        previewBagLabels.value = bagLabels
    } catch (err) {
        console.error('Error generating labels:', err)
        $q.notify({ type: 'negative', message: 'Error loading batch labels' })
    } finally {
        scannerLoading.value = false
    }
}

const onClickBoxLabel = () => {
    if (!selectedSimBatch.value) return
    const batch = selectedSimBatch.value
    const records = previewBagLabels.value
    const totalVol = 0
    const qrData = `${batch.plan_id},${batch.batch_id},BOX,${records.length},${totalVol}`
    
    showScannerDialog.value = false
    parseAndHandleScan(qrData, 'box')
}

const onClickBagLabel = (bag: {batch_record_id: string, re_code: string}) => {
    const batch = selectedSimBatch.value
    if (!batch) return
    const qrData = `${batch.plan_id},${bag.batch_record_id},${bag.re_code},0`
    
    showScannerDialog.value = false
    parseAndHandleScan(qrData, 'bag')
}

const onBoxScanSubmit = () => {
    const val = boxScanInput.value.trim()
    if (val) {
        parseAndHandleScan(val, 'box')
        boxScanInput.value = ''
    }
}

const onBagScanSubmit = () => {
    const val = bagScanInput.value.trim()
    if (val) {
        parseAndHandleScan(val, 'bag')
        bagScanInput.value = ''
    }
}

// --- Helpers ---

const showFeedback = (type: 'success' | 'error' | 'warning', message: string, title: string) => {
    feedback.value = { show: true, type, message, title }
    setTimeout(() => { feedback.value.show = false }, 3500)
}

const playSound = (type: 'success' | 'error') => {
    try {
        const context = new (window.AudioContext || (window as any).webkitAudioContext)()
        const osc = context.createOscillator()
        const gain = context.createGain()
        osc.connect(gain)
        gain.connect(context.destination)
        
        if (type === 'success') {
            osc.frequency.setValueAtTime(880, context.currentTime)
            gain.gain.setValueAtTime(0.08, context.currentTime)
            gain.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 0.15)
        } else {
            osc.frequency.setValueAtTime(220, context.currentTime)
            gain.gain.setValueAtTime(0.15, context.currentTime)
            gain.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 0.3)
        }
        osc.start()
        osc.stop(context.currentTime + 0.3)
    } catch {}
}

const getStatusIcon = (status: number) => {
    if (status === 1) return 'check_circle'
    if (status === 2) return 'error'
    return 'radio_button_unchecked'
}

const getStatusColor = (status: number) => {
    if (status === 1) return 'positive'
    if (status === 2) return 'negative'
    return 'grey-6'
}

const isBagScannedInBox = (batchRecordId: string) => {
    if (!boxDetails.value) return false
    const bag = boxDetails.value.bags.find((b: any) => b.batch_record_id === batchRecordId)
    return bag && bag.status === 1
}

onMounted(() => {
    fetchPlansAndBatches()
})
</script>

<template>
  <q-page class="q-pa-md bg-white">

    <!-- ===== PAGE HEADER ===== -->
    <div class="bg-blue-9 text-white q-pa-md rounded-borders q-mb-md shadow-2">
      <div class="row justify-between items-center">
        <div class="row items-center q-gutter-sm">
          <q-icon name="fact_check" size="sm" />
          <div class="text-h6 text-weight-bolder">Batch Packing Re-Check</div>
        </div>
        <div class="text-caption text-blue-2">Scan → Verify → Release</div>
      </div>
    </div>

    <!-- ===== BOX SCAN BAR ===== -->
    <q-card flat bordered class="q-mb-md shadow-1">
      <q-card-section class="q-py-sm bg-blue-grey-1">
        <div class="row items-center q-gutter-sm">
          <q-icon name="inbox" color="blue-9" />
          <span class="text-subtitle2 text-weight-bold text-blue-9">SCAN PACKING BOX</span>
        </div>
      </q-card-section>
      <q-card-section class="q-py-sm">
        <div class="row q-col-gutter-sm items-center">
          <div class="col">
            <q-input
              v-model="boxScanInput"
              outlined dense
              placeholder="Scan or type Packing Box ID / QR Code"
              @keyup.enter="onBoxScanSubmit"
              autofocus
              bg-color="white"
            >
              <template v-slot:prepend>
                <q-icon name="qr_code" color="blue-9" />
              </template>
              <template v-slot:append>
                <q-btn icon="document_scanner" flat round dense color="blue-9" @click="openScannerSimulator('box')">
                  <q-tooltip>Open Scanner Simulator</q-tooltip>
                </q-btn>
              </template>
            </q-input>
          </div>
          <div class="col-auto">
            <q-btn unelevated color="blue-9" icon="search" label="Load Box" @click="onBoxScanSubmit" :loading="loading && !boxDetails" />
          </div>
          <div class="col-auto" v-if="boxDetails">
            <q-btn flat icon="close" label="Reset" color="grey-7" @click="resetBox" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- ===== BOX LOADED ===== -->
    <div v-if="boxDetails">

      <!-- Box Info Header -->
      <q-card flat bordered class="q-mb-md shadow-1 overflow-hidden">
        <div class="bg-blue-9 text-white q-pa-md row items-center q-col-gutter-md">
          <div class="col-auto">
            <q-circular-progress
              show-value
              :value="progress * 100"
              size="80px"
              :color="allVerified ? 'positive' : 'yellow'"
              track-color="blue-7"
              :thickness="0.18"
            >
              <span class="text-h6 text-weight-bold text-white">{{ scannedCount }}/{{ totalCount }}</span>
            </q-circular-progress>
          </div>
          <div class="col">
            <div class="text-caption text-blue-3">Box ID</div>
            <div class="text-h6 text-weight-bold">{{ boxId }}</div>
            <div class="text-caption text-blue-2">
              SKU: {{ boxDetails.sku_id }} &nbsp;|&nbsp; {{ boxDetails.sku_name }} &nbsp;|&nbsp; Plan: {{ boxDetails.plan_id }}
            </div>
          </div>
          <div class="col-auto text-right">
            <div v-if="allVerified">
              <q-btn
                color="positive" size="md"
                label="RELEASE TO PRODUCTION"
                icon="rocket_launch"
                unelevated
                class="text-weight-bold pulse-btn"
                @click="releaseBatch"
                :loading="loading"
              />
              <div class="text-caption text-positive q-mt-xs">All bags verified ✓</div>
            </div>
            <div v-else class="text-right">
              <div class="text-h6 text-blue-2">
                <q-icon name="hourglass_empty" /> {{ totalCount - scannedCount }} Remaining
              </div>
              <div v-if="errorCount > 0" class="text-caption text-red-3">
                {{ errorCount }} error(s) detected
              </div>
            </div>
          </div>
        </div>
        <q-linear-progress
          :value="progress"
          :color="allVerified ? 'positive' : 'yellow'"
          track-color="blue-8"
          style="height: 6px"
        />
      </q-card>

      <!-- ===== BAG SCAN INPUT ===== -->
      <q-card flat bordered class="q-mb-md shadow-1">
        <q-card-section class="q-py-sm bg-blue-grey-1">
          <div class="row items-center q-gutter-sm">
            <q-icon name="qr_code_scanner" color="blue-9" />
            <span class="text-subtitle2 text-weight-bold text-blue-9">SCAN PACKING BAG</span>
            <q-badge color="primary" :label="`${scannedCount} / ${totalCount} Verified`" />
          </div>
        </q-card-section>
        <q-card-section class="q-py-sm">
          <div class="row q-col-gutter-sm items-center">
            <div class="col">
              <q-input
                v-model="bagScanInput"
                outlined dense
                placeholder="Scan Packing Bag QR Code to verify..."
                @keyup.enter="onBagScanSubmit"
                ref="bagScanRef"
                bg-color="white"
              >
                <template v-slot:prepend>
                  <q-icon name="inventory_2" color="primary" />
                </template>
                <template v-slot:append>
                  <q-btn icon="document_scanner" flat round dense color="primary" @click="openScannerSimulator('bag')">
                    <q-tooltip>Open Bag Scanner Simulator</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
            </div>
            <div class="col-auto">
              <q-btn unelevated color="primary" icon="check" label="Verify" @click="onBagScanSubmit" :loading="loading" />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Bag List Table -->
      <q-card flat bordered class="shadow-1">
        <div class="q-pa-sm bg-primary text-white text-subtitle2 text-weight-bold row items-center justify-between">
          <div class="row items-center">
            <q-icon name="inventory_2" class="q-mr-sm" />
            <span>Packing Bags in Box</span>
          </div>
          <q-badge color="white" text-color="primary" :label="`${scannedCount} / ${totalCount} OK`" />
        </div>

        <q-markup-table flat dense separator="cell">
          <thead class="bg-blue-grey-2 text-blue-grey-9">
            <tr>
              <th class="text-center" style="width: 50px">Status</th>
              <th class="text-left">Ingredient (Re-Code)</th>
              <th class="text-left">Bag Barcode</th>
              <th class="text-right">Target (kg)</th>
              <th class="text-right">Actual (kg)</th>
              <th class="text-right">Diff</th>
              <th class="text-left">Verified By</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="bag in boxDetails.bags"
              :key="bag.batch_record_id"
              :class="{
                'bg-green-1': bag.status === 1,
                'bg-red-1':   bag.status === 2,
                'bg-white':   bag.status === 0
              }"
            >
              <td class="text-center">
                <q-icon :name="getStatusIcon(bag.status)" :color="getStatusColor(bag.status)" size="20px" />
              </td>
              <td class="text-weight-bold">{{ bag.re_code }}</td>
              <td class="text-caption text-grey-7">{{ bag.batch_record_id }}</td>
              <td class="text-right">{{ bag.target_volume?.toFixed(3) }}</td>
              <td class="text-right text-weight-bold" :class="bag.is_valid ? 'text-green-9' : 'text-red-9'">
                {{ bag.net_volume?.toFixed(3) }}
              </td>
              <td class="text-right text-caption" :class="bag.is_valid ? 'text-green-7' : 'text-red-7'">
                {{ ((bag.net_volume || 0) - (bag.target_volume || 0)).toFixed(3) }}
                <span class="text-grey-5">(±{{ bag.tolerance?.toFixed(3) }})</span>
              </td>
              <td class="text-caption text-grey-7">
                <span v-if="bag.recheck_by">
                  {{ bag.recheck_by }}<br />
                  <span class="text-grey-5">{{ new Date(bag.recheck_at).toLocaleTimeString() }}</span>
                </span>
                <span v-else class="text-grey-4">—</span>
              </td>
            </tr>
          </tbody>
        </q-markup-table>
      </q-card>
    </div>

    <!-- ===== EMPTY STATE ===== -->
    <div v-else class="text-center q-pa-xl">
      <q-icon name="outbox" size="120px" color="blue-grey-3" />
      <div class="text-h5 text-grey-6 text-weight-light q-mt-md">Scan a Packing Box to begin</div>
      <div class="text-body2 text-grey-5 q-mb-lg">Load a box to verify its bag contents before releasing to production</div>
      <q-btn
        icon="document_scanner"
        label="Open Scanner Simulator"
        unelevated color="blue-9"
        @click="openScannerSimulator('box')"
      />
    </div>

    <!-- ===== SCANNER SIMULATOR DIALOG ===== -->
    <q-dialog v-model="showScannerDialog" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card class="bg-grey-10 text-white">
        <q-bar class="bg-blue-9 text-white">
          <q-icon name="document_scanner" />
          <div class="text-weight-bold q-ml-sm">
            SCANNER SIMULATOR —
            {{ scannerMode === 'box' ? 'Click Box Label to Load Box' : 'Click Bag Label to Verify Bag' }}
          </div>
          <q-space />
          <q-btn dense flat icon="close" v-close-popup />
        </q-bar>

        <q-card-section class="row q-col-gutter-md" style="height: calc(100vh - 50px); overflow: auto;">
          <!-- Left: Batch Selector -->
          <div class="col-12 col-md-3">
            <div class="text-overline text-blue-3 q-mb-sm">SELECT BATCH</div>
            <q-list dark separator dense class="rounded-borders" style="background: rgba(255,255,255,0.05)">
              <q-item
                v-for="batch in allBatches"
                :key="batch.batch_id"
                clickable
                @click="onSimSelectBatch(batch)"
                :active="selectedSimBatch?.batch_id === batch.batch_id"
                active-class="bg-blue-9 text-white"
                class="q-py-sm"
              >
                <q-item-section>
                  <q-item-label class="text-weight-bold text-white">{{ batch.batch_id }}</q-item-label>
                  <q-item-label caption class="text-grey-4">{{ batch.sku_name }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </div>

          <!-- Right: Labels Preview -->
          <div class="col-12 col-md-9">
            <q-inner-loading :showing="scannerLoading" dark />

            <div v-if="selectedSimBatch && !scannerLoading">
              <!-- Box Label -->
              <div class="text-overline text-blue-3 q-mb-sm">
                📦 BOX LABEL {{ scannerMode === 'box' ? '— Click to load this box' : '' }}
              </div>
              <div
                class="label-preview box-label-preview q-mb-lg"
                :class="{ 'cursor-pointer hover-highlight': scannerMode === 'box' }"
                @click="scannerMode === 'box' && onClickBoxLabel()"
                v-html="previewLabelSvg"
              />

              <!-- Bag Labels -->
              <div class="text-overline text-blue-3 q-mb-sm">
                🏷️ BAG LABELS {{ scannerMode === 'bag' ? '— Click any bag to verify it' : '' }}
              </div>
              <div class="row q-col-gutter-sm">
                <div
                  v-for="bag in previewBagLabels"
                  :key="bag.batch_record_id"
                  class="col-6 col-md-4 col-lg-3"
                >
                  <div
                    class="label-preview bag-label-preview"
                    :class="{
                      'cursor-pointer hover-highlight': scannerMode === 'bag',
                      'bag-label-scanned': isBagScannedInBox(bag.batch_record_id)
                    }"
                    @click="scannerMode === 'bag' && onClickBagLabel(bag)"
                  >
                    <div v-html="bag.svg" />
                    <div v-if="isBagScannedInBox(bag.batch_record_id)" class="scanned-overlay">
                      <q-icon name="check_circle" color="positive" size="42px" />
                      <div class="text-positive text-weight-bold text-caption">VERIFIED</div>
                    </div>
                  </div>
                  <div class="text-caption text-center text-grey-4 q-mt-xs">{{ bag.re_code }}</div>
                </div>
              </div>
            </div>

            <div v-else-if="!scannerLoading" class="text-center q-pa-xl text-grey-5">
              <q-icon name="touch_app" size="80px" />
              <div class="text-h6 q-mt-md">Select a batch from the left</div>
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- ===== FEEDBACK BANNER ===== -->
    <q-dialog v-model="feedback.show" position="top" seamless>
      <q-card class="feedback-card" :class="`feedback-${feedback.type}`">
        <q-card-section class="row items-center no-wrap q-pa-md">
          <q-icon
            :name="feedback.type === 'success' ? 'check_circle' : (feedback.type === 'warning' ? 'warning' : 'error')"
            size="36px" class="q-mr-md"
          />
          <div>
            <div class="text-subtitle1 text-weight-bold">{{ feedback.title }}</div>
            <div class="text-body2">{{ feedback.message }}</div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

  </q-page>
</template>

<style scoped>
/* Label previews in simulator */
.label-preview {
  background: white;
  border-radius: 6px;
  padding: 6px;
  transition: all 0.2s ease;
  border: 2px solid transparent;
  position: relative;
}
.hover-highlight:hover {
  border-color: #1565c0;
  box-shadow: 0 2px 12px rgba(21, 101, 192, 0.25);
  transform: scale(1.02);
}
.label-preview :deep(svg) {
  width: 100%;
  height: auto;
}
.box-label-preview {
  max-width: 380px;
}
.bag-label-scanned {
  border-color: #4caf50 !important;
  opacity: 0.55;
}
.scanned-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 6px;
}

/* Feedback banner */
.feedback-card {
  min-width: 400px;
  border-radius: 0 0 10px 10px;
  color: white;
}
.feedback-success { background: #2e7d32; }
.feedback-error   { background: #c62828; }
.feedback-warning { background: #e65100; }

/* Release button pulse */
.pulse-btn {
  animation: pulse-glow 1.5s infinite;
}
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 6px rgba(56, 142, 60, 0.4); }
  50%       { box-shadow: 0 0 18px rgba(56, 142, 60, 0.8); }
}
</style>

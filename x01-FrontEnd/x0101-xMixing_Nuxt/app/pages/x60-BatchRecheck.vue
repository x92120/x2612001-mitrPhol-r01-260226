<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useQuasar } from 'quasar'
import { appConfig } from '../appConfig/config'
import { useLabelPrinter } from '../composables/useLabelPrinter'

const $q = useQuasar()
const { getAuthHeader, user } = useAuth()
const { generateLabelSvg, printLabel } = useLabelPrinter()
const { t } = useI18n()

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

// Bags from OTHER batches (for wrong-box simulation)
const otherBatchBagLabels = ref<{svg: string, batch_record_id: string, re_code: string, source_batch: string}[]>([])

// Feedback overlay
const feedback = ref<{ show: boolean, type: 'success' | 'error' | 'warning', message: string, title: string }>({
    show: false,
    type: 'success',
    message: '',
    title: ''
})

// Wrong Box full-screen alert overlay
const wrongBoxAlert = ref<{ show: boolean, bagCode: string, expectedBox: string }>({ show: false, bagCode: '', expectedBox: '' })

// Sound Settings
const showSoundSettings = ref(false)
const successSoundPreset = ref(typeof localStorage !== 'undefined' ? (localStorage.getItem('recheck_success_sound') || 'beep') : 'beep')
const errorSoundPreset = ref(typeof localStorage !== 'undefined' ? (localStorage.getItem('recheck_error_sound') || 'siren') : 'siren')

const successSoundOptions = [
    { value: 'beep', labelKey: 'sound.shortBeep', icon: 'music_note' },
    { value: 'double_beep', labelKey: 'sound.doubleBeep', icon: 'music_note' },
    { value: 'chime', labelKey: 'sound.chime', icon: 'notifications' },
    { value: 'ding', labelKey: 'sound.ding', icon: 'campaign' },
]
const errorSoundOptions = [
    { value: 'buzzer', labelKey: 'sound.buzzer', icon: 'volume_up' },
    { value: 'siren', labelKey: 'sound.siren', icon: 'warning' },
    { value: 'horn', labelKey: 'sound.horn', icon: 'volume_up' },
    { value: 'alarm', labelKey: 'sound.alarm', icon: 'crisis_alert' },
]

const saveSoundSettings = () => {
    localStorage.setItem('recheck_success_sound', successSoundPreset.value)
    localStorage.setItem('recheck_error_sound', errorSoundPreset.value)
    showSoundSettings.value = false
    $q.notify({ type: 'positive', message: t('sound.saved'), position: 'top' })
}

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
        const detail = error.data?.detail || 'Verification failed'
        // Detect "wrong box" type errors
        if (detail.includes('does not belong') || detail.includes('not found')) {
            // WRONG BOX! Show alarming full-screen alert
            wrongBoxAlert.value = { show: true, bagCode: bagBarcode, expectedBox: boxId.value }
            playSound('wrong_box')
            showFeedback('error', `BAG [${bagBarcode}] does NOT belong to this box!`, '⚠ WRONG BOX ⚠')
            setTimeout(() => { wrongBoxAlert.value.show = false }, 3500)
        } else {
            showFeedback('error', detail, 'ERROR')
            playSound('error')
        }
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
        
        // Generate bag labels from OTHER batches (for wrong-box simulation)
        const otherLabels: {svg: string, batch_record_id: string, re_code: string, source_batch: string}[] = []
        const otherBatches = allBatches.value.filter(b => b.batch_id !== batch.batch_id).slice(0, 3)
        for (const otherBatch of otherBatches) {
            try {
                const otherRecords = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-recs/by-batch/${otherBatch.batch_id}`, {
                    headers: getAuthHeader() as Record<string, string>
                })
                // Take up to 2 bags from each other batch
                for (const record of otherRecords.slice(0, 2)) {
                    const bagMapping = {
                        RecipeName: otherBatch.sku_name || otherBatch.sku_id || '-',
                        BaseQuantity: otherBatch.batch_size || 0,
                        ItemNumber: '-',
                        RefCode: record.re_code || '-',
                        OrderCode: otherBatch.plan_id || '-',
                        BatchSize: otherBatch.batch_size || 0,
                        Weight: `${(record.net_volume || 0).toFixed(3)} / ${(record.total_volume || 0).toFixed(3)}`,
                        Packages: `${record.package_no || 1} / ${record.total_packages || 1}`,
                        LotID: record.intake_lot_id || '-',
                        QRCode: `${otherBatch.plan_id},${record.batch_record_id},${record.re_code},${record.net_volume}`,
                        SmallQRCode: `${otherBatch.plan_id},${record.batch_record_id},${record.re_code},${record.net_volume}`
                    }
                    const svg = await generateLabelSvg('prebatch-label', bagMapping as any)
                    if (svg) {
                        otherLabels.push({
                            svg,
                            batch_record_id: record.batch_record_id,
                            re_code: record.re_code,
                            source_batch: otherBatch.batch_id
                        })
                    }
                }
            } catch { /* skip if error */ }
        }
        otherBatchBagLabels.value = otherLabels
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

// Simulate scanning a bag from the WRONG batch (wrong box)
const onClickWrongBagLabel = (bag: {batch_record_id: string, re_code: string, source_batch: string}) => {
    // The bag_barcode is the real batch_record_id from another batch
    // This will be rejected by the backend because it doesn't belong to current box
    showScannerDialog.value = false
    verifyBag(bag.batch_record_id)
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

// --- Sound Engine ---
const playSoundPreset = (preset: string) => {
    try {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
        const t = ctx.currentTime
        
        const tone = (freq: number, start: number, dur: number, vol: number, wave: OscillatorType = 'sine') => {
            const osc = ctx.createOscillator()
            const gain = ctx.createGain()
            osc.type = wave
            osc.connect(gain)
            gain.connect(ctx.destination)
            osc.frequency.setValueAtTime(freq, t + start)
            gain.gain.setValueAtTime(vol, t + start)
            gain.gain.exponentialRampToValueAtTime(0.01, t + start + dur)
            osc.start(t + start)
            osc.stop(t + start + dur)
        }

        switch (preset) {
            // === SUCCESS SOUNDS ===
            case 'beep':
                tone(880, 0, 0.2, 0.12)
                break
            case 'double_beep':
                tone(880, 0, 0.12, 0.12)
                tone(1100, 0.15, 0.12, 0.12)
                break
            case 'chime':
                tone(523, 0, 0.15, 0.1)
                tone(659, 0.12, 0.15, 0.1)
                tone(784, 0.24, 0.25, 0.12)
                break
            case 'ding':
                tone(1200, 0, 0.4, 0.1)
                tone(1200, 0, 0.4, 0.06, 'triangle')
                break

            // === ERROR SOUNDS ===
            case 'buzzer':
                for (let i = 0; i < 3; i++) tone(400 - i * 80, i * 0.18, 0.15, 0.18, 'square')
                break
            case 'siren':
                for (let i = 0; i < 6; i++) tone(i % 2 === 0 ? 800 : 400, i * 0.2, 0.18, 0.25, 'sawtooth')
                break
            case 'horn':
                tone(200, 0, 0.6, 0.25, 'sawtooth')
                tone(201, 0, 0.6, 0.15, 'square')
                break
            case 'alarm':
                for (let i = 0; i < 8; i++) tone(i % 2 === 0 ? 600 : 900, i * 0.12, 0.1, 0.2, 'square')
                break
        }
    } catch {}
}

const playSound = (type: 'success' | 'error' | 'wrong_box') => {
    if (type === 'success') {
        playSoundPreset(successSoundPreset.value)
    } else {
        playSoundPreset(errorSoundPreset.value)
    }
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
          <div class="text-h6 text-weight-bolder">{{ t('recheck.title') }}</div>
        </div>
        <div class="row items-center q-gutter-sm">
          <div class="text-caption text-blue-2">{{ t('recheck.subtitle') }}</div>
          <q-btn flat round dense icon="volume_up" color="white" @click="showSoundSettings = true">
            <q-tooltip>{{ t('sound.title') }}</q-tooltip>
          </q-btn>
        </div>
      </div>
    </div>

    <!-- ===== BOX SCAN BAR ===== -->
    <q-card flat bordered class="q-mb-md shadow-1">
      <q-card-section class="q-py-sm bg-blue-grey-1">
        <div class="row items-center q-gutter-sm">
          <q-icon name="inbox" color="blue-9" />
          <span class="text-subtitle2 text-weight-bold text-blue-9">{{ t('recheck.scanPackingBox') }}</span>
        </div>
      </q-card-section>
      <q-card-section class="q-py-sm">
        <div class="row q-col-gutter-sm items-center">
          <div class="col">
            <q-input
              v-model="boxScanInput"
              outlined dense
              :placeholder="t('recheck.scanBoxPlaceholder')"
              @keyup.enter="onBoxScanSubmit"
              autofocus
              bg-color="white"
            >
              <template v-slot:prepend>
                <q-icon name="qr_code" color="blue-9" />
              </template>
              <template v-slot:append>
                <q-btn icon="document_scanner" flat round dense color="blue-9" @click="openScannerSimulator('box')">
                  <q-tooltip>{{ t('recheck.openSimulator') }}</q-tooltip>
                </q-btn>
              </template>
            </q-input>
          </div>
          <div class="col-auto">
            <q-btn unelevated color="blue-9" icon="search" :label="t('recheck.loadBox')" @click="onBoxScanSubmit" :loading="loading && !boxDetails" />
          </div>
          <div class="col-auto" v-if="boxDetails">
            <q-btn flat icon="close" :label="t('common.reset')" color="grey-7" @click="resetBox" />
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
                :label="t('recheck.releaseToProduction')"
                icon="rocket_launch"
                unelevated
                class="text-weight-bold pulse-btn"
                @click="releaseBatch"
                :loading="loading"
              />
              <div class="text-caption text-positive q-mt-xs">{{ t('recheck.allBagsVerified') }}</div>
            </div>
            <div v-else class="text-right">
              <div class="text-h6 text-blue-2">
                <q-icon name="hourglass_empty" /> {{ totalCount - scannedCount }} {{ t('recheck.remaining') }}
              </div>
              <div v-if="errorCount > 0" class="text-caption text-red-3">
                {{ errorCount }} {{ t('recheck.errorsDetected') }}
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
            <span class="text-subtitle2 text-weight-bold text-blue-9">{{ t('recheck.scanPackingBag') }}</span>
            <q-badge color="primary" :label="`${scannedCount} / ${totalCount} ${t('recheck.verified')}`" />
          </div>
        </q-card-section>
        <q-card-section class="q-py-sm">
          <div class="row q-col-gutter-sm items-center">
            <div class="col">
              <q-input
                v-model="bagScanInput"
                outlined dense
                :placeholder="t('recheck.scanBagPlaceholder')"
                @keyup.enter="onBagScanSubmit"
                ref="bagScanRef"
                bg-color="white"
              >
                <template v-slot:prepend>
                  <q-icon name="inventory_2" color="primary" />
                </template>
                <template v-slot:append>
                  <q-btn icon="document_scanner" flat round dense color="primary" @click="openScannerSimulator('bag')">
                    <q-tooltip>{{ t('recheck.openSimulator') }}</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
            </div>
            <div class="col-auto">
              <q-btn unelevated color="primary" icon="check" :label="t('common.confirm')" @click="onBagScanSubmit" :loading="loading" />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Bag List Table -->
      <q-card flat bordered class="shadow-1">
        <div class="q-pa-sm bg-primary text-white text-subtitle2 text-weight-bold row items-center justify-between">
          <div class="row items-center">
            <q-icon name="inventory_2" class="q-mr-sm" />
            <span>{{ t('recheck.bagsInBox') }}</span>
          </div>
          <q-badge color="white" text-color="primary" :label="`${scannedCount} / ${totalCount} OK`" />
        </div>

        <q-markup-table flat dense separator="cell">
          <thead class="bg-blue-grey-2 text-blue-grey-9">
            <tr>
              <th class="text-center" style="width: 50px">{{ t('common.status') }}</th>
              <th class="text-left">{{ t('recheck.ingredient') }}</th>
              <th class="text-left">{{ t('recheck.bagBarcode') }}</th>
              <th class="text-right">{{ t('recheck.target') }}</th>
              <th class="text-right">{{ t('recheck.actual') }}</th>
              <th class="text-right">{{ t('recheck.diff') }}</th>
              <th class="text-left">{{ t('recheck.verifiedBy') }}</th>
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
      <div class="text-h5 text-grey-6 text-weight-light q-mt-md">{{ t('recheck.scanToBegin') }}</div>
      <div class="text-body2 text-grey-5 q-mb-lg">{{ t('recheck.loadBoxToVerify') }}</div>
      <q-btn
        icon="document_scanner"
        :label="t('recheck.openSimulator')"
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
            {{ t('recheck.simulatorTitle') }} —
            {{ scannerMode === 'box' ? t('recheck.clickBoxToLoad') : t('recheck.clickBagToVerify') }}
          </div>
          <q-space />
          <q-btn dense flat icon="close" v-close-popup />
        </q-bar>

        <q-card-section class="row q-col-gutter-md" style="height: calc(100vh - 50px); overflow: auto;">
          <!-- Left: Batch Selector -->
          <div class="col-12 col-md-3">
            <div class="text-overline text-blue-3 q-mb-sm">{{ t('recheck.selectBatch') }}</div>
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
              <div class="row items-center q-mb-sm q-gutter-md">
                <div class="text-overline text-blue-3">
                  📦 {{ t('recheck.boxLabel') }} {{ scannerMode === 'box' ? '— ' + t('recheck.clickBoxToLoad') : '' }}
                </div>
                <q-btn v-if="previewLabelSvg" size="sm" color="blue-9" icon="print" label="Print Box" @click="printLabel(previewLabelSvg)" />
              </div>
              <div
                class="label-preview box-label-preview q-mb-lg"
                :class="{ 'cursor-pointer hover-highlight': scannerMode === 'box' }"
                @click="scannerMode === 'box' && onClickBoxLabel()"
                v-html="previewLabelSvg"
              />

              <!-- Bags inside box (correct + wrong mixed together) -->
              <div class="text-overline text-blue-3 q-mb-sm">
                🏷️ {{ t('recheck.bagsInBoxLabel') }} {{ scannerMode === 'bag' ? '— ' + t('recheck.clickToScan') : '' }}
              </div>
              <div class="row q-col-gutter-sm">
                <!-- Correct bags from this batch -->
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
                  <div class="row items-center justify-between q-mt-xs">
                    <div class="text-caption text-grey-4">{{ bag.re_code }}</div>
                    <q-btn size="xs" color="blue-9" icon="print" label="Print" @click.stop="printLabel(bag.svg)" />
                  </div>
                </div>

                <!-- WRONG bags mixed in (from other batches — simulating wrong placement) -->
                <div
                  v-for="bag in (scannerMode === 'bag' ? otherBatchBagLabels : [])"
                  :key="'wrong-' + bag.batch_record_id"
                  class="col-6 col-md-4 col-lg-3"
                >
                  <div
                    class="label-preview bag-label-preview wrong-bag-preview cursor-pointer"
                    @click="onClickWrongBagLabel(bag)"
                  >
                    <div v-html="bag.svg" />
                    <div class="wrong-bag-badge">
                      <q-icon name="warning" size="16px" />
                      {{ t('recheck.wrongBatch') }}
                    </div>
                  </div>
                  <div class="row items-center justify-between q-mt-xs">
                    <div class="text-caption text-red-4">{{ bag.re_code }}</div>
                    <q-btn size="xs" color="blue-9" icon="print" label="Print" @click.stop="printLabel(bag.svg)" />
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="!scannerLoading" class="text-center q-pa-xl text-grey-5">
              <q-icon name="touch_app" size="80px" />
              <div class="text-h6 q-mt-md">{{ t('recheck.selectBatchPrompt') }}</div>
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- ===== SOUND SETTINGS DIALOG ===== -->
    <q-dialog v-model="showSoundSettings">
      <q-card style="min-width: 420px" class="bg-grey-9 text-white">
        <q-bar class="bg-blue-9">
          <q-icon name="volume_up" />
          <div class="text-weight-bold q-ml-sm">{{ t('sound.title') }}</div>
          <q-space />
          <q-btn dense flat icon="close" v-close-popup />
        </q-bar>

        <q-card-section>
          <div class="text-overline text-green-4 q-mb-sm">✅ {{ t('sound.correctScan') }}</div>
          <q-list dark dense separator class="rounded-borders" style="background: rgba(255,255,255,0.05)">
            <q-item
              v-for="opt in successSoundOptions"
              :key="opt.value"
              tag="label"
              class="q-py-sm"
            >
              <q-item-section side>
                <q-radio v-model="successSoundPreset" :val="opt.value" color="green" dark />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-white">{{ t(opt.labelKey) }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-btn flat round dense icon="play_arrow" color="green" @click.stop="playSoundPreset(opt.value)">
                  <q-tooltip>{{ t('sound.preview') }}</q-tooltip>
                </q-btn>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <q-separator dark />

        <q-card-section>
          <div class="text-overline text-red-4 q-mb-sm">❌ {{ t('sound.wrongScan') }}</div>
          <q-list dark dense separator class="rounded-borders" style="background: rgba(255,255,255,0.05)">
            <q-item
              v-for="opt in errorSoundOptions"
              :key="opt.value"
              tag="label"
              class="q-py-sm"
            >
              <q-item-section side>
                <q-radio v-model="errorSoundPreset" :val="opt.value" color="red" dark />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-white">{{ t(opt.labelKey) }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-btn flat round dense icon="play_arrow" color="red" @click.stop="playSoundPreset(opt.value)">
                  <q-tooltip>{{ t('sound.preview') }}</q-tooltip>
                </q-btn>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat :label="t('common.cancel')" color="grey" v-close-popup />
          <q-btn unelevated :label="t('common.save')" color="blue-9" icon="save" @click="saveSoundSettings" />
        </q-card-actions>
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

    <!-- ===== WRONG BOX FULL-SCREEN ALERT ===== -->
    <Teleport to="body">
      <div v-if="wrongBoxAlert.show" class="wrong-box-overlay" @click="wrongBoxAlert.show = false">
        <div class="wrong-box-content">
          <q-icon name="gpp_bad" size="120px" color="white" />
          <div class="wrong-box-title">{{ t('wrongBox.title') }}</div>
          <div class="wrong-box-title-thai">{{ t('wrongBox.titleThai') }}</div>
          <div class="wrong-box-subtitle">{{ t('wrongBox.subtitle') }}</div>
          <div class="wrong-box-detail">
            {{ t('wrongBox.bag') }}: <strong>{{ wrongBoxAlert.bagCode }}</strong>
          </div>
          <div class="wrong-box-detail">
            {{ t('wrongBox.currentBox') }}: <strong>{{ wrongBoxAlert.expectedBox }}</strong>
          </div>
          <div class="wrong-box-instruction">{{ t('wrongBox.removeImmediately') }}</div>
        </div>
      </div>
    </Teleport>

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

/* Wrong Bag label in simulator */
.wrong-bag-preview {
  border: 2px dashed #e53935 !important;
  position: relative;
  opacity: 0.85;
}
.wrong-bag-preview:hover {
  border-color: #ff1744 !important;
  box-shadow: 0 2px 16px rgba(229, 57, 53, 0.4);
  transform: scale(1.02);
  opacity: 1;
}
.wrong-bag-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  background: #e53935;
  color: white;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* WRONG BOX full-screen overlay */
.wrong-box-overlay {
  position: fixed;
  inset: 0;
  z-index: 99999;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: wrongBoxFlash 0.4s ease-in-out infinite alternate;
  cursor: pointer;
}
@keyframes wrongBoxFlash {
  0%   { background: rgba(198, 40, 40, 0.92); }
  100% { background: rgba(255, 23, 68, 0.97); }
}
.wrong-box-content {
  text-align: center;
  color: white;
  animation: wrongBoxShake 0.15s ease-in-out infinite alternate;
}
@keyframes wrongBoxShake {
  0%   { transform: translateX(-4px); }
  100% { transform: translateX(4px); }
}
.wrong-box-title {
  font-size: 64px;
  font-weight: 900;
  letter-spacing: 4px;
  text-shadow: 0 4px 20px rgba(0,0,0,0.5);
  margin-top: 12px;
}
.wrong-box-title-thai {
  font-size: 48px;
  font-weight: 800;
  text-shadow: 0 4px 20px rgba(0,0,0,0.5);
  margin-top: 4px;
}
.wrong-box-subtitle {
  font-size: 24px;
  font-weight: 500;
  opacity: 0.9;
  margin-top: 8px;
}
.wrong-box-detail {
  font-size: 18px;
  margin-top: 8px;
  opacity: 0.85;
}
.wrong-box-instruction {
  font-size: 28px;
  font-weight: 800;
  margin-top: 24px;
  padding: 12px 32px;
  background: rgba(255,255,255,0.15);
  border-radius: 8px;
  border: 2px solid rgba(255,255,255,0.4);
  animation: pulseInstruction 0.8s ease-in-out infinite alternate;
}
@keyframes pulseInstruction {
  0%   { transform: scale(1); }
  100% { transform: scale(1.05); }
}
</style>

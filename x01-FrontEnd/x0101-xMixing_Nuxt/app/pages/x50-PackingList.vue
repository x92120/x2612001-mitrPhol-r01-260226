<script setup lang="ts">
/**
 * x50-PackingList.vue — Packing List View v2.1
 * 3-Panel Layout: Production Plans | Warehouse Bags | Batch Packing
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import QRCode from 'qrcode'
import { appConfig } from '../appConfig/config'
import { useAuth } from '../composables/useAuth'
import { useMqttLocalDevice } from '../composables/useMqttLocalDevice'

const $q = useQuasar()
const { getAuthHeader } = useAuth()
const { t } = useI18n()
const { lastScan, connect } = useMqttLocalDevice()

// ═══════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════
const loading = ref(false)
const loadingRecords = ref(false)
const plans = ref<any[]>([])
const fhRecords = ref<any[]>([])         // FH prebatch_recs (middle panel)
const sppRecords = ref<any[]>([])        // SPP prebatch_recs (middle panel)
const batchRecords = ref<any[]>([])      // Records for selected batch (right panel)
const selectedBatch = ref<any>(null)
const selectedPlan = ref<any>(null)
const scanBatchId = ref('')
const scanFH = ref('')
const scanSPP = ref('')

// Scan simulation dialog
const showScanDialog = ref(false)
const scanDialogWh = ref<'FH' | 'SPP'>('FH')

// Warehouse sort
const whSortCol = ref<'bag_id' | 're_code' | 'weight' | 'status' | 'batch_id' | 'plan_id'>('re_code')
const whSortAsc = ref(true)
const filterMiddleWh = ref<'FH' | 'SPP'>('FH')
const middleHideBoxed = ref(false)   // false = show All, true = hide Boxed

// ═══════════════════════════════════════════════════════════════════
// SOUND SETTINGS
// ═══════════════════════════════════════════════════════════════════
const showSoundSettings = ref(false)

interface SoundSettings {
  enabled: boolean
  volume: number           // 0 - 100
  correctSound: 'beep' | 'chime' | 'bell' | 'ding'
  wrongSound: 'buzzer' | 'error' | 'alarm' | 'honk'
}

const defaultSoundSettings: SoundSettings = {
  enabled: true,
  volume: 60,
  correctSound: 'chime',
  wrongSound: 'buzzer',
}

const soundSettings = ref<SoundSettings>({ ...defaultSoundSettings })

// Load from localStorage
const loadSoundSettings = () => {
  try {
    const saved = localStorage.getItem('packinglist_sound_settings')
    if (saved) {
      soundSettings.value = { ...defaultSoundSettings, ...JSON.parse(saved) }
    }
  } catch { /* ignore */ }
}

const saveSoundSettings = () => {
  try {
    localStorage.setItem('packinglist_sound_settings', JSON.stringify(soundSettings.value))
  } catch { /* ignore */ }
}

watch(soundSettings, saveSoundSettings, { deep: true })

// ═══════════════════════════════════════════════════════════════════
// SOUND EFFECTS
// ═══════════════════════════════════════════════════════════════════
const correctSoundOptions = [
  { value: 'beep',  label: '🔔 Beep',  desc: 'Simple beep tone' },
  { value: 'chime', label: '🎵 Chime', desc: 'Two-tone ascending chime' },
  { value: 'bell',  label: '🔔 Bell',  desc: 'Bright bell ring' },
  { value: 'ding',  label: '✨ Ding',  desc: 'Soft ding notification' },
]
const wrongSoundOptions = [
  { value: 'buzzer', label: '🚨 Buzzer', desc: 'Low buzzer tone' },
  { value: 'error',  label: '❌ Error',  desc: 'Error alert sound' },
  { value: 'alarm',  label: '⚠️ Alarm',  desc: 'Warning alarm' },
  { value: 'honk',   label: '📢 Honk',   desc: 'Short horn honk' },
]

const playSound = async (type: 'correct' | 'wrong') => {
  if (!soundSettings.value.enabled) return

  const vol = soundSettings.value.volume / 100
  try {
    const ctx = new AudioContext()
    await ctx.resume()

    if (type === 'correct') {
      await _playCorrectSound(ctx, vol)
    } else {
      await _playWrongSound(ctx, vol)
    }
  } catch (e) {
    console.warn('Sound playback failed:', e)
  }
}

const _playCorrectSound = async (ctx: AudioContext, vol: number) => {
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.connect(gain)
  gain.connect(ctx.destination)
  gain.gain.value = vol * 0.5

  const soundType = soundSettings.value.correctSound
  switch (soundType) {
    case 'beep':
      osc.frequency.value = 1000
      osc.type = 'sine'
      osc.start()
      setTimeout(() => { osc.stop(); ctx.close() }, 200)
      break
    case 'chime':
      osc.frequency.value = 880
      osc.type = 'sine'
      osc.start()
      setTimeout(() => { osc.frequency.value = 1320 }, 100)
      setTimeout(() => { osc.stop(); ctx.close() }, 280)
      break
    case 'bell': {
      osc.frequency.value = 1200
      osc.type = 'sine'
      gain.gain.setValueAtTime(vol * 0.6, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5)
      osc.start()
      setTimeout(() => { osc.stop(); ctx.close() }, 500)
      break
    }
    case 'ding': {
      osc.frequency.value = 1500
      osc.type = 'sine'
      gain.gain.setValueAtTime(vol * 0.4, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3)
      osc.start()
      setTimeout(() => { osc.stop(); ctx.close() }, 350)
      break
    }
  }
}

const _playWrongSound = async (ctx: AudioContext, vol: number) => {
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.connect(gain)
  gain.connect(ctx.destination)
  gain.gain.value = vol * 0.5

  const soundType = soundSettings.value.wrongSound
  switch (soundType) {
    case 'buzzer':
      osc.frequency.value = 200
      osc.type = 'square'
      osc.start()
      setTimeout(() => { osc.frequency.value = 150 }, 150)
      setTimeout(() => { osc.stop(); ctx.close() }, 400)
      break
    case 'error': {
      osc.frequency.value = 400
      osc.type = 'sawtooth'
      osc.start()
      setTimeout(() => { osc.frequency.value = 300 }, 100)
      setTimeout(() => { osc.frequency.value = 200 }, 200)
      setTimeout(() => { osc.stop(); ctx.close() }, 350)
      break
    }
    case 'alarm': {
      osc.frequency.value = 600
      osc.type = 'square'
      gain.gain.value = vol * 0.35
      osc.start()
      setTimeout(() => { osc.frequency.value = 400 }, 120)
      setTimeout(() => { osc.frequency.value = 600 }, 240)
      setTimeout(() => { osc.frequency.value = 400 }, 360)
      setTimeout(() => { osc.stop(); ctx.close() }, 480)
      break
    }
    case 'honk': {
      osc.frequency.value = 250
      osc.type = 'sawtooth'
      gain.gain.setValueAtTime(vol * 0.5, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3)
      osc.start()
      setTimeout(() => { osc.stop(); ctx.close() }, 350)
      break
    }
  }
}

// ═══════════════════════════════════════════════════════════════════
// COMPUTED
// ═══════════════════════════════════════════════════════════════════

const activePlans = computed(() =>
  plans.value.filter(p => p.status !== 'Cancelled')
)

const isFH = (wh: string) =>
  wh?.toUpperCase().includes('FH') || wh?.toUpperCase().includes('FLAVOUR')

const isSPP = (wh: string) =>
  wh?.toUpperCase().includes('SPP')

/** Get bags for the selected batch, grouped by warehouse (FH/SPP only, excludes MIX) */
const bagsByWarehouse = computed((): { FH: any[]; SPP: any[] } => {
  const result = { FH: [] as any[], SPP: [] as any[] }
  if (!selectedBatch.value) return result
  // Use batch-specific records (fetched via /prebatch-recs/by-batch/)
  batchRecords.value.forEach(bag => {
    const wh = bag.wh || ''
    if (isFH(wh)) {
      result.FH.push(bag)
    } else if (isSPP(wh)) {
      result.SPP.push(bag)
    }
    // MIX and other warehouses are excluded
  })
  return result
})

/** Weight summaries */
const fhWeight = computed(() =>
  bagsByWarehouse.value.FH.reduce((sum: number, b: any) => sum + (b.net_volume || 0), 0)
)
const sppWeight = computed(() =>
  bagsByWarehouse.value.SPP.reduce((sum: number, b: any) => sum + (b.net_volume || 0), 0)
)
const totalWeight = computed(() => fhWeight.value + sppWeight.value)

/** Check if all bags are packed per warehouse */
const fhPackedCount = computed(() => bagsByWarehouse.value.FH.filter(b => isPacked(b)).length)
const sppPackedCount = computed(() => bagsByWarehouse.value.SPP.filter(b => isPacked(b)).length)
const allFhPacked = computed(() => bagsByWarehouse.value.FH.length > 0 && fhPackedCount.value === bagsByWarehouse.value.FH.length)
const allSppPacked = computed(() => bagsByWarehouse.value.SPP.length > 0 && sppPackedCount.value === bagsByWarehouse.value.SPP.length)

/** Sort helper for warehouse records */
const sortWarehouseRecords = (list: any[]) => {
  const col = whSortCol.value
  const asc = whSortAsc.value ? 1 : -1
  return [...list].sort((a, b) => {
    let va: any, vb: any
    if (col === 'bag_id') {
      va = a.batch_record_id || ''
      vb = b.batch_record_id || ''
    } else if (col === 'batch_id') {
      va = a.batch_id || ''
      vb = b.batch_id || ''
    } else if (col === 'plan_id') {
      va = a.plan_id || ''
      vb = b.plan_id || ''
    } else if (col === 're_code') {
      va = a.re_code || ''
      vb = b.re_code || ''
    } else if (col === 'weight') {
      va = a.net_volume || 0
      vb = b.net_volume || 0
    } else {
      va = a.packing_status || 0
      vb = b.packing_status || 0
    }
    if (va < vb) return -1 * asc
    if (va > vb) return 1 * asc
    return 0
  })
}

const toggleWhSort = (col: 'bag_id' | 're_code' | 'weight' | 'status' | 'batch_id' | 'plan_id') => {
  if (whSortCol.value === col) {
    whSortAsc.value = !whSortAsc.value
  } else {
    whSortCol.value = col
    whSortAsc.value = true
  }
}

const whSortIcon = (col: string) => {
  if (whSortCol.value !== col) return 'unfold_more'
  return whSortAsc.value ? 'arrow_upward' : 'arrow_downward'
}

/** Middle panel: records per warehouse, sorted */
const middlePanelFH = computed(() => sortWarehouseRecords(fhRecords.value.filter((b: any) => b.packing_status !== 1)))
const middlePanelSPP = computed(() => sortWarehouseRecords(sppRecords.value.filter((b: any) => b.packing_status !== 1)))

/** Hierarchical grouping for middle panel tree view:
 *  Level 1: re_code  → totalWeight (all packages across all batches)
 *  Level 2: batch_id → totalWeight (all packages for that batch)
 *  Level 3: individual prebatch package (batch_record_id, weight, status)
 */
interface PkgNode   { id: string; label: string; weight: number; status: number; recheck: number }
interface BatchNode { batch_id: string; totalWeight: number; pkgs: PkgNode[] }
interface RecodeNode { re_code: string; totalWeight: number; batches: BatchNode[] }

const groupedMiddlePanel = computed((): RecodeNode[] => {
  let src = filterMiddleWh.value === 'FH' ? fhRecords.value : sppRecords.value
  if (middleHideBoxed.value) src = src.filter((b: any) => b.packing_status !== 1)

  const map = new Map<string, RecodeNode>()

  for (const bag of src) {
    const re = bag.re_code || '?'
    const bid = bag.batch_id || '?'

    if (!map.has(re)) map.set(re, { re_code: re, totalWeight: 0, batches: [] })
    const reNode = map.get(re)!

    let bNode = reNode.batches.find(b => b.batch_id === bid)
    if (!bNode) { bNode = { batch_id: bid, totalWeight: 0, pkgs: [] }; reNode.batches.push(bNode) }

    const pkgNo  = bag.package_no ?? 1
    const pkgTot = bag.total_packages ?? 1
    const label  = `${(bag.batch_record_id || bid + '-PKG').split('-').slice(-2).join('-')}  (Pkg ${pkgNo}/${pkgTot})`
    bNode.pkgs.push({ id: bag.id || bag.batch_record_id, label, weight: bag.net_volume || 0, status: bag.packing_status || 0, recheck: bag.recheck_status || 0 })
    bNode.totalWeight += bag.net_volume || 0
    reNode.totalWeight += bag.net_volume || 0
  }

  // Sort: re_code alphabetically, batches by id, pkgs by label
  return [...map.values()]
    .sort((a, b) => a.re_code.localeCompare(b.re_code))
    .map(r => ({
      ...r,
      batches: r.batches
        .sort((a, b) => a.batch_id.localeCompare(b.batch_id))
        .map(b => ({ ...b, pkgs: b.pkgs.sort((a, b) => a.label.localeCompare(b.label)) }))
    }))
})

/** Batch info for right panel */
const batchInfo = computed(() => {
  if (!selectedBatch.value) return null
  const plan = plans.value.find(p =>
    p.batches?.some((b: any) => b.batch_id === selectedBatch.value.batch_id)
  )
  return {
    batch_id: selectedBatch.value.batch_id,
    sku_name: plan?.sku_name || plan?.sku_id || '-',
    plan_id: plan?.plan_id || '-',
    batch_size: selectedBatch.value.batch_size || 0,
    status: selectedBatch.value.status,
  }
})

/** Scan dialog — list of bags filtered to correct ingredients for selected batch */
const scanDialogBags = computed(() => {
  const wh = scanDialogWh.value
  const whBags = wh === 'FH' ? middlePanelFH.value : middlePanelSPP.value
  // If a batch is selected, filter to only show bags with matching re_code
  if (selectedBatch.value) {
    const batchReqs = selectedBatch.value.reqs || []
    const requiredReCodes = new Set(batchReqs.map((r: any) => r.re_code))
    if (requiredReCodes.size === 0) return whBags
    return whBags.filter(b => requiredReCodes.has(b.re_code))
  }
  return whBags
})

// ═══════════════════════════════════════════════════════════════════
// DATA FETCHING
// ═══════════════════════════════════════════════════════════════════

const fetchPlans = async () => {
  loading.value = true
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/production-plans/?skip=0&limit=100`, {
      headers: getAuthHeader() as Record<string, string>
    })
    plans.value = data || []
  } catch (e) {
    console.error('Error fetching plans:', e)
    $q.notify({ type: 'negative', message: 'Failed to load production plans' })
  } finally {
    loading.value = false
  }
}

/** Fetch ready-to-deliver batches from the database */
const fetchReadyToDeliver = async () => {
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/production-batches/ready-to-deliver`, {
      headers: getAuthHeader() as Record<string, string>
    })
    // Convert API response to TransferredBox entries
    const boxes: TransferredBox[] = []
    for (const b of (data || [])) {
      if (b.fh_boxed_at) {
        boxes.push({
          id: `${b.batch_id}-FH`,
          wh: 'FH',
          batch_id: b.batch_id,
          bagsCount: 0,
          time: new Date(b.fh_boxed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        })
      }
      if (b.spp_boxed_at) {
        boxes.push({
          id: `${b.batch_id}-SPP`,
          wh: 'SPP',
          batch_id: b.batch_id,
          bagsCount: 0,
          time: new Date(b.spp_boxed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        })
      }
      // Populate deliveredMap from DB
      if (b.delivered_at) {
        deliveredMap.value.set(b.batch_id, new Date(b.delivered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))
      }
    }
    transferredBoxes.value = boxes
  } catch (e) {
    console.error('Error fetching ready-to-deliver:', e)
  }
}


const fetchAllRecords = async () => {
  loadingRecords.value = true
  try {
    const [fh, spp] = await Promise.all([
      $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-recs/?limit=200&wh=FH`, {
        headers: getAuthHeader() as Record<string, string>
      }),
      $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-recs/?limit=200&wh=SPP`, {
        headers: getAuthHeader() as Record<string, string>
      }),
    ])
    fhRecords.value = fh || []
    sppRecords.value = spp || []
  } catch (e) {
    console.error('Error fetching records:', e)
  } finally {
    loadingRecords.value = false
  }
}

let _batchFetchController: AbortController | null = null
const fetchBatchRecords = async (batchId: string) => {
  // Cancel any in-flight request
  if (_batchFetchController) _batchFetchController.abort()
  _batchFetchController = new AbortController()
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-recs/by-batch/${batchId}`, {
      headers: getAuthHeader() as Record<string, string>,
      signal: _batchFetchController.signal as AbortSignal,
    })
    batchRecords.value = data || []
  } catch (e: any) {
    if (e?.name !== 'AbortError') {
      console.error('Error fetching batch records:', e)
      batchRecords.value = []
    }
  }
}

// ═══════════════════════════════════════════════════════════════════
// ACTIONS
// ═══════════════════════════════════════════════════════════════════

const onPlanClick = (plan: any) => {
  selectedPlan.value = plan
}

const onBatchClick = (batch: any, plan: any) => {
  selectedBatch.value = batch
  selectedPlan.value = plan
  scanBatchId.value = batch.batch_id
  fetchBatchRecords(batch.batch_id)
}

const onScanBatchEnter = () => {
  if (!scanBatchId.value) return
  for (const plan of plans.value) {
    const batch = plan.batches?.find((b: any) => b.batch_id === scanBatchId.value)
    if (batch) {
      selectedBatch.value = batch
      selectedPlan.value = plan
      fetchBatchRecords(batch.batch_id)
      $q.notify({ type: 'positive', message: `Batch ${batch.batch_id} loaded`, position: 'top' })
      return
    }
  }
  $q.notify({ type: 'warning', message: `Batch "${scanBatchId.value}" not found`, position: 'top' })
}

const isPacked    = (bag: any) => bag.packing_status === 1
const isPrepared  = (bag: any) => bag.recheck_status === 1 && bag.packing_status !== 1

// 3-tier status
const getBagStatus = (bag: any): 'boxed' | 'prepare' | 'waiting' => {
  if (bag.packing_status === 1) return 'boxed'
  if (bag.recheck_status === 1) return 'prepare'
  return 'waiting'
}
const getBagStatusColor = (bag: any) => {
  const s = getBagStatus(bag)
  if (s === 'boxed')   return 'blue-7'
  if (s === 'prepare') return 'orange-7'
  return 'grey-5'
}
const getBagStatusIcon = (bag: any) => {
  const s = getBagStatus(bag)
  if (s === 'boxed')   return 'inventory'
  if (s === 'prepare') return 'hourglass_top'
  return 'radio_button_unchecked'
}
const getBagStatusLabel = (bag: any) => {
  const s = getBagStatus(bag)
  if (s === 'boxed')   return 'Boxed'
  if (s === 'prepare') return 'Prepare'
  return 'Waiting'
}
const getBagRowClass = (bag: any) => {
  const s = getBagStatus(bag)
  if (s === 'boxed')   return 'bg-blue-1'
  if (s === 'prepare') return 'bg-orange-1'
  return ''
}

/** Close packing box — ready to transfer */
interface TransferredBox {
  id: string
  wh: 'FH' | 'SPP'
  batch_id: string
  bagsCount: number
  time: string
}
const transferredBoxes = ref<TransferredBox[]>([])

// ── Transfer Dialog ──────────────────────────────────────────────
const showTransferDialog   = ref(false)
const selectedForTransfer  = ref<string[]>([])   // list of TransferredBox.id
const filterDeliveryWh     = ref<'ALL'|'FH'|'SPP'>('ALL')
const deliveredMap         = ref<Map<string, string>>(new Map())  // batch_id → delivery time

const markDelivered = async (batch_id: string) => {
  try {
    await $fetch(`${appConfig.apiBaseUrl}/production-batches/by-batch-id/${batch_id}/deliver`, {
      method: 'PATCH',
      headers: getAuthHeader() as Record<string, string>,
      body: { delivered_by: 'operator' },
    })
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    deliveredMap.value = new Map(deliveredMap.value).set(batch_id, time)
    playSound('correct')
    $q.notify({ type: 'positive', icon: 'local_shipping', message: `✅ Batch ${batch_id} delivered at ${time}`, position: 'top', timeout: 2500 })
  } catch (e) {
    console.error('Error marking delivery:', e)
    $q.notify({ type: 'negative', message: `Failed to mark ${batch_id} as delivered` })
  }
}

const filteredTransferredBoxes = computed(() => {
  return transferredBoxes.value.filter(b => b.wh === filterMiddleWh.value)
})

/** Group transferred boxes by batch_id so FH+SPP appear in one row */
interface TransferredBatchRow {
  batch_id: string
  fh: TransferredBox | null
  spp: TransferredBox | null
  time: string
}
const groupedTransferredBoxes = computed((): TransferredBatchRow[] => {
  const map = new Map<string, TransferredBatchRow>()
  for (const box of transferredBoxes.value) {
    if (!map.has(box.batch_id)) {
      map.set(box.batch_id, { batch_id: box.batch_id, fh: null, spp: null, time: box.time })
    }
    const row = map.get(box.batch_id)!
    if (box.wh === 'FH') row.fh = box
    else row.spp = box
    if (box.time !== '—') row.time = box.time
  }
  return Array.from(map.values())
})


const onCloseBox = (wh: 'FH' | 'SPP') => {
  if (!selectedBatch.value) return
  const batchId = selectedBatch.value.batch_id
  $q.dialog({
    title: `Close ${wh} Packing Box`,
    message: `All ${wh} pre-batch bags are packed. Mark this box as Boxed?`,
    cancel: true,
    persistent: true,
    ok: { label: 'Confirm Boxed', color: wh === 'FH' ? 'blue' : 'light-blue', icon: 'unarchive' },
  }).onOk(async () => {
    try {
      await $fetch(`${appConfig.apiBaseUrl}/production-batches/by-batch-id/${batchId}/box-close`, {
        method: 'PATCH',
        headers: getAuthHeader() as Record<string, string>,
        body: { wh },
      })
      playSound('correct')
      $q.notify({
        type: 'positive',
        icon: 'unarchive',
        message: `✅ ${wh} Packing Box closed — Ready to Delivery`,
        position: 'top',
        timeout: 3000,
      })
      // Refresh the delivery list from DB
      await fetchReadyToDeliver()
    } catch (e) {
      console.error('Error closing box:', e)
      $q.notify({ type: 'negative', message: `Failed to close ${wh} box for ${batchId}` })
    }
  })
}

// ── Transfer Report Print ─────────────────────────────────────────
const printTransferReport = async () => {
  const boxes = transferredBoxes.value.filter(b => selectedForTransfer.value.includes(b.id))
  if (boxes.length === 0) return

  const now        = new Date()
  const dateStr    = now.toLocaleDateString('th-TH', { year: 'numeric', month: '2-digit', day: '2-digit' })
  const timeStr    = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const reportNo   = `TR-${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}-${String(Math.floor(Math.random()*9000)+1000)}`
  const whs        = [...new Set(boxes.map(b => b.wh))].join(' / ')
  const totalBags  = boxes.reduce((s, b) => s + b.bagsCount, 0)

  // Build table rows SVG — each row is 26px tall, starting at y=158
  const ROW_H = 26
  const START = 158
  let rowsSvg = ''
  boxes.forEach((box, i) => {
    const y   = START + i * ROW_H
    const bg  = i % 2 === 0 ? '#f2f2f2' : '#ffffff'
    const plan = plans.value.find(p => p.batches?.some((b: any) => b.batch_id === box.batch_id))
    const sku  = plan?.sku_name || plan?.sku_id || '-'
    rowsSvg += `
      <rect x="20" y="${y}" width="754" height="${ROW_H}" fill="${bg}"/>
      <line x1="20" y1="${y+ROW_H}" x2="774" y2="${y+ROW_H}" stroke="#cccccc" stroke-width="0.4"/>
      <text x="36"  y="${y+16}" style="font-size:8px;font-family:Arial,sans-serif;fill:#555555">${i+1}</text>
      <text x="60"  y="${y+14}" style="font-size:8px;font-family:Arial,sans-serif;font-weight:bold;fill:#000000">${box.batch_id}</text>
      <text x="60"  y="${y+24}" style="font-size:7px;font-family:'Courier New',monospace;fill:#888888">${box.id.slice(0,8)}</text>
      <text x="230" y="${y+16}" style="font-size:8px;font-family:Arial,sans-serif;fill:#000000">${sku.length > 28 ? sku.slice(0,28)+'…' : sku}</text>
      <rect x="424" y="${y+5}" width="28" height="14" rx="3" fill="#333333"/>
      <text x="438" y="${y+16}" text-anchor="middle" style="font-size:8px;font-family:Arial,sans-serif;font-weight:bold;fill:#ffffff">${box.wh}</text>
      <text x="478" y="${y+16}" style="font-size:9px;font-family:Arial,sans-serif;font-weight:bold;fill:#000000">${box.bagsCount}</text>
      <text x="520" y="${y+16}" style="font-size:8px;font-family:Arial,sans-serif;fill:#000000">${box.time}</text>
      <rect x="652" y="${y+5}" width="56" height="14" rx="3" fill="#222222"/>
      <text x="680" y="${y+16}" text-anchor="middle" style="font-size:7.5px;font-family:Arial,sans-serif;font-weight:bold;fill:#ffffff">TRANSFERRED</text>
    `
    // column separators
    ;[52, 222, 422, 460, 512, 650].forEach(x => {
      rowsSvg += `<line x1="${x}" y1="${y}" x2="${x}" y2="${y+ROW_H}" stroke="#cccccc" stroke-width="0.4"/>`
    })
  })

  try {
    const resp   = await fetch('/labels/report-transfer-a4.svg')
    let svgText  = await resp.text()

    svgText = svgText
      .replace('{{ReportNo}}',     reportNo)
      .replace('{{PrintDate}}',    `${dateStr} ${timeStr}`)
      .replace('{{Warehouse}}',    whs || 'FH / SPP')
      .replace('{{TransferDate}}', dateStr)
      .replace('{{TotalBoxes}}',   String(boxes.length))
      .replace('{{TotalBags}}',    String(totalBags))
      .replace('{{TransferRows}}', rowsSvg)
      .replace('{{ReportQR}}',     '')   // QR placeholder — can be enhanced later

    const pw   = Math.round(window.screen.width  * 0.8)
    const ph   = Math.round(window.screen.height * 0.8)
    const left = Math.round((window.screen.width  - pw) / 2)
    const top  = Math.round((window.screen.height - ph) / 2)
    const win  = window.open('', '_blank', `width=${pw},height=${ph},left=${left},top=${top}`)
    if (!win) { $q.notify({ type: 'warning', message: 'Popup blocked — allow popups and retry', position: 'top' }); return }

    win.document.write(`<!DOCTYPE html><html><head>
      <title>Transfer Report ${reportNo}</title>
      <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background:#888; display:flex; justify-content:center; align-items:flex-start; padding:20px; }
        .page { background:#fff; box-shadow:0 4px 20px rgba(0,0,0,.4); }
        @media print {
          body { background:white; padding:0; }
          .page { box-shadow:none; }
          @page { size: A4 portrait; margin:0; }
        }
      </style>
    </head><body>
      <div class="page">${svgText}</div>
      <script>window.onload = () => { setTimeout(() => window.print(), 400) }<\/script>
    </body></html>`)
    win.document.close()
  } catch(e) {
    $q.notify({ type: 'negative', message: 'Failed to load report template', position: 'top' })
  }
  showTransferDialog.value = false
  selectedForTransfer.value = []
}

// ── Box Packing Label Print ──────────────────────────────────────
const printBoxLabel = async (wh: 'FH' | 'SPP') => {
  if (!selectedBatch.value || !batchInfo.value) return

  const bags = wh === 'FH' ? bagsByWarehouse.value.FH : bagsByWarehouse.value.SPP
  const plan = plans.value.find(p => p.batches?.some((b: any) => b.batch_id === selectedBatch.value.batch_id))

  // Group bags by re_code, sorted by re_code then package_no
  type BagGroup = { re_code: string; req_vol: number; bags: any[] }
  const grouped: BagGroup[] = []
  const seenCodes = new Map<string, BagGroup>()

  for (const bag of bags) {
    const code = bag.re_code || '?'
    if (!seenCodes.has(code)) {
      const g: BagGroup = {
        re_code: code,
        req_vol: bag.total_request_volume ?? bag.total_volume ?? 0,
        bags: []
      }
      seenCodes.set(code, g)
      grouped.push(g)
    }
    seenCodes.get(code)!.bags.push(bag)
  }
  // Sort packages within each group
  grouped.forEach(g => g.bags.sort((a, b) => (a.package_no ?? 0) - (b.package_no ?? 0)))

  // Build SVG rows — ingredient header (15px) + sub-rows (13px)
  const HDR_H = 15   // ingredient row height
  const PKG_H = 13   // package sub-row height
  const START_Y = 252

  let curY = START_Y
  let rowsSvg = ''

  for (const grp of grouped) {
    // Stop if we'd overflow past footer line (y=555)
    if (curY + HDR_H > 544) break

    // ── Ingredient header row (white bg + bottom border line) ──
    rowsSvg += `
      <rect x="15" y="${curY}" width="370" height="${HDR_H}" fill="#ffffff"/>
      <text x="22" y="${curY + 10}" style="font-size:8px;font-family:Arial,sans-serif;font-weight:bold;fill:#000000">${grp.re_code}</text>
      <text x="385" y="${curY + 10}" text-anchor="end" style="font-size:8px;font-family:Arial,sans-serif;fill:#000000">Require ${grp.req_vol.toFixed(4)} kg</text>
      <line x1="15" y1="${curY + HDR_H}" x2="385" y2="${curY + HDR_H}" stroke="#000000" stroke-width="0.5"/>
    `
    curY += HDR_H

    // ── Package sub-rows ──
    for (const bag of grp.bags) {
      if (curY + PKG_H > 544) break
      const pkgLabel = `-->Pkg ${bag.package_no ?? 1}/${bag.total_packages ?? 1}`
      rowsSvg += `
        <rect x="15" y="${curY}" width="370" height="${PKG_H}" fill="#ffffff"/>
        <text x="30" y="${curY + 9}" style="font-size:7.5px;font-family:'Courier New',monospace;fill:#000000">${pkgLabel}</text>
        <text x="385" y="${curY + 9}" text-anchor="end" style="font-size:7.5px;font-family:Arial,sans-serif;fill:#000000">${(bag.net_volume ?? 0).toFixed(4)} kg</text>
      `
      rowsSvg += `<line x1="30" y1="${curY + PKG_H}" x2="385" y2="${curY + PKG_H}" stroke="#000000" stroke-width="0.2"/>`
      curY += PKG_H
    }
  }


  const totalWt     = bags.reduce((s: number, b: any) => s + (b.net_volume || 0), 0)
  const now         = new Date()
  const printDate   = now.toLocaleDateString('th-TH') + ' ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  try {
    const resp = await fetch('/labels/label-box-packing-100x150.svg')
    let svgText = await resp.text()

    // replaceAll handles multiple occurrences of the same placeholder
    svgText = svgText
      .replaceAll('{{Warehouse}}',     wh)
      .replaceAll('{{PrintDate}}',     printDate)
      .replace('{{SkuId}}',            batchInfo.value?.sku_name || '-')
      .replace('{{BatchId}}',          selectedBatch.value.batch_id)
      .replace('{{Plant}}',            plan?.plant || selectedBatch.value.plant || 'Line-1')
      .replace('{{BatchSize}}',        (batchInfo.value?.batch_size || 0).toFixed(0))
      .replace('{{TotalNetWeight}}',   totalWt.toFixed(3))
      .replace('{{PreBatchRows}}',     rowsSvg)

    // QR Code content: two lines separated by newline
    const qrData = `Batch_ID:${selectedBatch.value.batch_id}\nWarehouse:${wh}`
    const qrDataUrl = await QRCode.toDataURL(qrData, {
      width: 150, margin: 1,
      color: { dark: '#000000', light: '#ffffff' }
    })
    // Scale: QR box is 110×110, QR image is 150×150 → scale = 110/150 ≈ 0.733
    const qrImageSvg = `<image x="0" y="0" width="150" height="150" href="${qrDataUrl}" />`
    svgText = svgText.replace('{{BoxQRCode}}', qrImageSvg)

    const pw   = Math.round(window.screen.width  * 0.8)
    const ph   = Math.round(window.screen.height * 0.8)
    const left = Math.round((window.screen.width  - pw) / 2)
    const top  = Math.round((window.screen.height - ph) / 2)
    const printWin = window.open('', '_blank', `width=${pw},height=${ph},left=${left},top=${top}`)
    if (!printWin) {
      $q.notify({ type: 'warning', message: 'Popup blocked — allow popups and retry', position: 'top' })
      return
    }
    printWin.document.write(`
      <!DOCTYPE html><html><head>
      <title>Box Packing Label — ${selectedBatch.value.batch_id} [${wh}]</title>
      <style>
        @page { size: 100mm 150mm; margin: 0; }
        body  { margin: 0; padding: 0; background: #fff; }
        svg   { display: block; width: 100mm; height: 150mm; }
      </style>
      </head><body>
        ${svgText}
        <script>window.onload = () => { window.print(); window.onafterprint = () => window.close(); }<\/script>
      </body></html>
    `)
    printWin.document.close()
  } catch (e) {
    console.error('Print error:', e)
    $q.notify({ type: 'negative', message: 'Failed to load label template', position: 'top' })
  }
}



// ── Scan Simulation ─────────────────────────────────────────────
const openScanSimulator = (wh: 'FH' | 'SPP') => {
  scanDialogWh.value = wh
  showScanDialog.value = true
}

const onSimScanClick = async (bag: any) => {
  if (!selectedBatch.value) {
    playSound('wrong')
    $q.notify({ type: 'negative', message: 'Please select a Packing Box first!', icon: 'warning', position: 'top' })
    return
  }

  // Check if this bag belongs to the selected batch via req_id
  const batchReqs = selectedBatch.value.reqs || []
  const reqIds = new Set(batchReqs.map((r: any) => r.id))
  const belongsToBox = reqIds.has(bag.req_id)

  if (belongsToBox) {
    // Correct — this bag belongs to the selected packing box
    playSound('correct')

    // Persist packing_status=1 to backend
    try {
      await $fetch(`${appConfig.apiBaseUrl}/prebatch-recs/${bag.id}/packing-status`, {
        method: 'PATCH',
        headers: getAuthHeader() as Record<string, string>,
        body: { packing_status: 1, packed_by: 'operator' },
      })
    } catch (e) {
      console.error('Failed to update packing status:', e)
    }

    // Update ALL local data sources that may reference this bag
    const markPacked = (list: any[]) => {
      const found = list.find((b: any) => b.id === bag.id)
      if (found) found.packing_status = 1
    }
    markPacked(fhRecords.value)       // Middle panel FH
    markPacked(sppRecords.value)      // Middle panel SPP
    markPacked(batchRecords.value)    // Right panel (packing box list)
    bag.packing_status = 1            // Current scan dialog item

    const whLabel = scanDialogWh.value
    if (whLabel === 'FH') scanFH.value = bag.batch_record_id
    else scanSPP.value = bag.batch_record_id
    $q.notify({
      type: 'positive',
      icon: 'check_circle',
      message: `✅ Correct! ${bag.re_code} packed into box`,
      caption: bag.batch_record_id,
      position: 'top',
      timeout: 2000,
    })
  } else {
    // Wrong — this bag does NOT belong to the selected packing box
    playSound('wrong')
    $q.notify({
      type: 'negative',
      icon: 'error',
      message: `❌ Wrong box! This bag belongs to a different batch`,
      caption: `Bag: ${bag.batch_record_id} ≠ Box: ${selectedBatch.value.batch_id}`,
      position: 'top',
      timeout: 3000,
    })
  }
  showScanDialog.value = false
}

// Watch for MQTT scans
watch(lastScan, (scan) => {
  if (scan?.barcode) {
    scanBatchId.value = scan.barcode
    onScanBatchEnter()
  }
})

// ═══════════════════════════════════════════════════════════════════
// LIFECYCLE
// ═══════════════════════════════════════════════════════════════════

onMounted(async () => {
  loadSoundSettings()
  connect()
  // Parallel fetch — plans, records, and delivery list
  await Promise.all([fetchPlans(), fetchAllRecords(), fetchReadyToDeliver()])
})
</script>

<template>
  <q-page class="bg-grey-2" style="height:100vh;max-height:100vh;overflow:hidden;display:flex;flex-direction:column;padding:6px;">
    <!-- Page Header -->
    <div class="bg-white q-pa-sm rounded-borders q-mb-sm shadow-2">
      <div class="row justify-between items-center">
        <div class="row items-center q-gutter-sm">
          <q-icon name="view_list" size="sm" color="blue-9" />
          <div class="text-h6 text-weight-bolder text-blue-9">{{ t('nav.packingList') }}</div>
        </div>
        <div class="row items-center q-gutter-sm">
          <q-btn flat dense round :icon="soundSettings.enabled ? 'volume_up' : 'volume_off'" color="blue-9" @click="showSoundSettings = true">
            <q-tooltip>Sound Settings</q-tooltip>
          </q-btn>
          <q-btn flat dense round icon="refresh" color="blue-9" @click="fetchPlans(); fetchAllRecords(); fetchReadyToDeliver()" :loading="loading">
            <q-tooltip>Refresh</q-tooltip>
          </q-btn>
          <div class="text-caption text-grey-5">v2.2</div>
        </div>
      </div>
    </div>

    <!-- 4-PANEL LAYOUT -->
    <div class="row q-col-gutter-sm" style="flex:1;min-height:0;overflow-x:auto;overflow-y:hidden;flex-wrap:nowrap;">

      <!-- ═══ LEFT PANEL: Production Plans + Transferred ═══ -->
      <div class="col-2 column q-gutter-y-sm" style="height:100%;min-height:0;overflow:hidden;">
        <q-card class="column shadow-2" style="flex:1;min-height:0;overflow:hidden;">
          <q-card-section class="bg-blue-9 text-white q-py-xs">
            <div class="row items-center justify-between no-wrap">
              <div class="row items-center q-gutter-xs">
                <q-icon name="assignment" size="sm" />
                <div class="text-subtitle2 text-weight-bold">Production Plans</div>
              </div>
              <q-badge color="white" text-color="blue-9" class="text-weight-bold">
                {{ activePlans.length }}
              </q-badge>
            </div>
          </q-card-section>

          <div class="col relative-position">
            <q-scroll-area class="fit">
              <q-list dense separator class="text-caption">
                <template v-for="plan in activePlans" :key="plan.plan_id">
                  <q-expansion-item
                    expand-separator
                    :icon="selectedPlan?.plan_id === plan.plan_id ? 'radio_button_checked' : 'radio_button_unchecked'"
                    :label="plan.plan_id"
                    :caption="`${plan.sku_name || plan.sku_id} — ${plan.num_batches || 0} batches`"
                    :header-class="selectedPlan?.plan_id === plan.plan_id ? 'bg-blue-1 text-blue-9 text-weight-bold' : 'text-weight-medium'"
                    dense dense-toggle
                    @show="onPlanClick(plan)"
                  >
                    <q-list dense class="q-pl-md">
                      <template v-for="batch in (plan.batches || [])" :key="batch.batch_id">
                        <q-expansion-item
                          dense dense-toggle expand-separator
                          :icon="batch.batch_prepare ? 'check_circle' : 'pending'"
                          :icon-color="batch.batch_prepare ? 'blue' : 'grey-5'"
                          :label="batch.batch_id.split('-').slice(-1)[0]"
                          :caption="batch.batch_prepare ? 'Prepared' : batch.status"
                          :header-class="selectedBatch?.batch_id === batch.batch_id ? 'bg-blue-1 text-blue-9' : (batch.batch_prepare ? 'bg-blue-1 text-grey-6' : '')"
                          @show="onBatchClick(batch, plan)"
                        >
                          <q-list dense class="q-pl-md">
                            <q-item
                              v-for="req in (batch.reqs || [])" :key="req.id" dense
                              style="min-height: 24px;"
                              :class="req.status === 2 ? 'bg-blue-1 text-grey-6' : ''"
                            >
                              <q-item-section avatar style="min-width: 20px;">
                                <q-icon
                                  :name="req.status === 2 ? 'check_circle' : (req.status === 1 ? 'hourglass_top' : 'circle')"
                                  :color="req.status === 2 ? 'blue' : (req.status === 1 ? 'orange' : 'grey-4')"
                                  size="xs"
                                />
                              </q-item-section>
                              <q-item-section>
                                <q-item-label style="font-size: 0.7rem;">
                                  {{ req.re_code }} — {{ req.ingredient_name || req.re_code }}
                                </q-item-label>
                              </q-item-section>
                              <q-item-section side>
                                <q-item-label style="font-size: 0.65rem;" class="text-weight-bold">
                                  {{ req.required_volume?.toFixed(1) }} kg
                                </q-item-label>
                              </q-item-section>
                            </q-item>
                            <q-item v-if="!batch.reqs || batch.reqs.length === 0" style="min-height: 24px;">
                              <q-item-section class="text-grey text-italic" style="font-size: 0.65rem;">No requirements</q-item-section>
                            </q-item>
                          </q-list>
                        </q-expansion-item>
                      </template>
                      <q-item v-if="!plan.batches || plan.batches.length === 0" style="min-height: 28px;">
                        <q-item-section class="text-grey text-italic" style="font-size: 0.7rem;">No batches</q-item-section>
                      </q-item>
                    </q-list>
                  </q-expansion-item>
                </template>

                <div v-if="activePlans.length === 0" class="text-center q-pa-lg text-grey">
                  <q-icon name="inbox" size="lg" class="q-mb-sm" /><br>
                  No active plans
                </div>
              </q-list>
            </q-scroll-area>
          </div>
        </q-card>
      </div>


      <!-- ═══ RIGHT PANEL: Packing Box + Pre-Batch Package ═══ -->
      <div class="col-4 column q-gutter-y-sm" style="order:2;height:100%;min-height:0;overflow:hidden;">
        <q-card class="col-auto shadow-2">
          <q-card-section class="bg-indigo-9 text-white q-py-xs">
            <div class="row items-center justify-between no-wrap">
              <div class="row items-center q-gutter-xs">
                <q-icon name="qr_code_scanner" size="sm" />
                <div class="text-subtitle2 text-weight-bold">Packing Box</div>
              </div>
              <div class="row items-center q-gutter-sm">
                <q-select
                  v-model="filterMiddleWh"
                  :options="['FH', 'SPP']"
                  dense borderless dark options-dense
                  style="width: 70px; font-size: 0.85rem;"
                  class="text-weight-bold"
                >
                  <template v-slot:selected>
                    <div class="text-white">{{ filterMiddleWh }}</div>
                  </template>
                </q-select>
                <!-- Print Button: active only when all bags for current WH are Boxed -->
                <q-btn
                  flat round dense icon="print" size="sm"
                  :color="(filterMiddleWh === 'FH' ? allFhPacked : allSppPacked) ? 'white' : 'indigo-3'"
                  :disable="!(filterMiddleWh === 'FH' ? allFhPacked : allSppPacked)"
                  @click="printBoxLabel(filterMiddleWh)"
                >
                  <q-tooltip>{{ (filterMiddleWh === 'FH' ? allFhPacked : allSppPacked) ? 'Print Box Packing Label' : 'Pack all bags first' }}</q-tooltip>
                </q-btn>
              </div>
            </div>
          </q-card-section>
          <q-card-section class="q-py-sm">
            <q-input
              v-model="scanBatchId" outlined dense
              placeholder="Scan Packing Box Label..."
              bg-color="grey-1"
              @keyup.enter="onScanBatchEnter"
            >
              <template v-slot:prepend>
                <q-icon name="qr_code_scanner" color="indigo" />
              </template>
              <template v-slot:append>
                <q-btn flat round dense icon="search" color="indigo" @click="onScanBatchEnter" />
              </template>
            </q-input>

            <template v-if="batchInfo">
              <div class="q-mt-sm">
                <div class="row q-col-gutter-xs text-caption">
                  <div class="col-6">
                    <div class="text-grey-6">SKU Name</div>
                    <div class="text-weight-bold text-body2">{{ batchInfo.sku_name }}</div>
                  </div>
                  <div class="col-6">
                    <div class="text-grey-6">Plan ID</div>
                    <div class="text-weight-bold text-body2">{{ batchInfo.plan_id }}</div>
                  </div>
                  <div class="col-6 q-mt-xs">
                    <div class="text-grey-6">Batch Size</div>
                    <div class="text-weight-bold text-body2">{{ batchInfo.batch_size }} kg</div>
                  </div>
                  <div class="col-6 q-mt-xs">
                    <div class="text-grey-6">Status</div>
                    <q-badge
                      :color="batchInfo.status === 'Prepared' ? 'blue' : (batchInfo.status === 'Created' ? 'grey' : 'light-blue')"
                      :label="batchInfo.status"
                    />
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="text-center text-grey q-pa-sm">
              <q-icon name="qr_code_2" size="md" class="q-mb-xs" /><br>
              <span class="text-caption">Scan or select a packing box</span>
            </div>

          </q-card-section>
        </q-card>


        <q-card class="col column shadow-2">
          <q-card-section class="bg-blue-10 text-white q-py-xs">
            <div class="row items-center justify-between no-wrap">
              <div class="row items-center q-gutter-xs">
                <q-icon name="inventory" size="sm" />
                <div class="text-subtitle2 text-weight-bold">Warehouse Pre-Batch Package</div>
              </div>
              <div v-if="selectedBatch" class="row items-center q-gutter-xs">
                <q-badge color="white" text-color="blue-10" class="text-weight-bold">
                  {{ totalWeight.toFixed(1) }} kg
                </q-badge>
                <q-badge color="blue-5" text-color="white" class="text-weight-bold">
                  FH {{ fhWeight.toFixed(1) }} kg
                </q-badge>
                <q-badge color="light-blue-5" text-color="white" class="text-weight-bold">
                  SPP {{ sppWeight.toFixed(1) }} kg
                </q-badge>
              </div>
            </div>
          </q-card-section>

          <div class="col relative-position">
            <q-scroll-area class="fit q-pa-xs">
              <div v-if="!selectedBatch" class="text-center q-pa-lg text-grey">
                <q-icon name="inventory_2" size="xl" class="q-mb-sm" /><br>
                Select a batch to view packing list
              </div>

              <template v-else>
                <!-- FH Packing Card -->
                <q-card v-show="filterMiddleWh === 'FH'" flat bordered class="q-mb-sm">
                  <q-card-section class="bg-blue-7 text-white q-py-xs">
                    <div class="row items-center justify-between no-wrap">
                      <div class="row items-center q-gutter-xs">
                        <q-icon name="science" size="xs" />
                        <span class="text-weight-bold text-caption">FH Pre-Batch Packing</span>
                      </div>
                      <div class="row items-center q-gutter-xs">
                        <q-badge color="white" text-color="blue-9">{{ fhPackedCount }}/{{ bagsByWarehouse.FH.length }}</q-badge>
                        <q-btn
                          dense flat size="xs" icon="unarchive" label="Boxed"
                          :color="allFhPacked ? 'white' : 'blue-3'"
                          :disable="!allFhPacked"
                          @click="onCloseBox('FH')"
                          class="text-weight-bold"
                        >
                          <q-tooltip>{{ allFhPacked ? 'Close box — Ready to transfer' : `${bagsByWarehouse.FH.length - fhPackedCount} bags remaining` }}</q-tooltip>
                        </q-btn>
                      </div>
                    </div>
                  </q-card-section>

                  <!-- FH Scan Field -->
                  <q-card-section class="q-py-xs">
                    <q-input v-model="scanFH" outlined dense placeholder="Scan FH pre-batch bag..." bg-color="blue-1">
                      <template v-slot:prepend>
                        <q-icon name="qr_code_scanner" color="blue-8" size="sm" class="cursor-pointer" @click="openScanSimulator('FH')">
                          <q-tooltip>Click to simulate scan</q-tooltip>
                        </q-icon>
                      </template>
                    </q-input>
                  </q-card-section>

                  <q-list dense separator>
                    <q-item
                      v-for="bag in bagsByWarehouse.FH" :key="bag.id" dense
                      :class="getBagRowClass(bag)"
                      style="min-height: 36px;"
                    >
                      <q-item-section avatar style="min-width: 24px;">
                        <q-icon :name="getBagStatusIcon(bag)" :color="getBagStatusColor(bag)" size="sm" />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label class="text-weight-bold" style="font-size: 0.75rem;">
                          {{ bag.re_code }} | {{ bag.net_volume?.toFixed(3) }} kg
                        </q-item-label>
                        <q-item-label caption style="font-size: 0.6rem;">
                          {{ bag.batch_record_id }}
                        </q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <q-badge :color="getBagStatusColor(bag)" :label="getBagStatusLabel(bag)" class="text-weight-bold" />
                      </q-item-section>
                    </q-item>
                    <q-item v-if="bagsByWarehouse.FH.length === 0">
                      <q-item-section class="text-center text-grey text-italic text-caption">No FH pre-batch for this box</q-item-section>
                    </q-item>
                  </q-list>
                </q-card>

                <!-- SPP Packing Card -->
                <q-card v-show="filterMiddleWh === 'SPP'" flat bordered>
                  <q-card-section class="bg-light-blue-8 text-white q-py-xs">
                    <div class="row items-center justify-between no-wrap">
                      <div class="row items-center q-gutter-xs">
                        <q-icon name="inventory_2" size="xs" />
                        <span class="text-weight-bold text-caption">SPP Pre-Batch Packing</span>
                      </div>
                      <div class="row items-center q-gutter-xs">
                        <q-badge color="white" text-color="light-blue-9">{{ sppPackedCount }}/{{ bagsByWarehouse.SPP.length }}</q-badge>
                        <q-btn
                          dense flat size="xs" icon="unarchive" label="Boxed"
                          :color="allSppPacked ? 'white' : 'light-blue-3'"
                          :disable="!allSppPacked"
                          @click="onCloseBox('SPP')"
                          class="text-weight-bold"
                        >
                          <q-tooltip>{{ allSppPacked ? 'Close box — Ready to transfer' : `${bagsByWarehouse.SPP.length - sppPackedCount} bags remaining` }}</q-tooltip>
                        </q-btn>
                      </div>
                    </div>
                  </q-card-section>

                  <!-- SPP Scan Field -->
                  <q-card-section class="q-py-xs">
                    <q-input v-model="scanSPP" outlined dense placeholder="Scan SPP pre-batch bag..." bg-color="light-blue-1">
                      <template v-slot:prepend>
                        <q-icon name="qr_code_scanner" color="light-blue-8" size="sm" class="cursor-pointer" @click="openScanSimulator('SPP')">
                          <q-tooltip>Click to simulate scan</q-tooltip>
                        </q-icon>
                      </template>
                    </q-input>
                  </q-card-section>

                  <q-list dense separator>
                    <q-item
                      v-for="bag in bagsByWarehouse.SPP" :key="bag.id" dense
                      :class="getBagRowClass(bag)"
                      style="min-height: 36px;"
                    >
                      <q-item-section avatar style="min-width: 24px;">
                        <q-icon :name="getBagStatusIcon(bag)" :color="getBagStatusColor(bag)" size="sm" />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label class="text-weight-bold" style="font-size: 0.75rem;">
                          {{ bag.re_code }} | {{ bag.net_volume?.toFixed(3) }} kg
                        </q-item-label>
                        <q-item-label caption style="font-size: 0.6rem;">
                          {{ bag.batch_record_id }}
                        </q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <q-badge :color="getBagStatusColor(bag)" :label="getBagStatusLabel(bag)" class="text-weight-bold" />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label class="text-weight-bold" style="font-size: 0.75rem;">
                          {{ bag.re_code }} | {{ bag.net_volume?.toFixed(3) }} kg
                        </q-item-label>
                        <q-item-label caption style="font-size: 0.6rem;">
                          {{ bag.batch_record_id }}
                        </q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <q-badge :color="isPacked(bag) ? 'blue' : 'grey-5'" :label="getBagStatusLabel(bag)" class="text-weight-bold" />
                      </q-item-section>
                    </q-item>
                    <q-item v-if="bagsByWarehouse.SPP.length === 0">
                      <q-item-section class="text-center text-grey text-italic text-caption">No SPP pre-batch for this box</q-item-section>
                    </q-item>
                  </q-list>
                </q-card>
              </template>
            </q-scroll-area>
          </div>
        </q-card>

      </div>

      <!-- ═══ MIDDLE PANEL: List all PreBatch Package of this Warehouse ═══ -->
      <div class="col-3 column q-gutter-y-sm" style="order:1;height:100%;min-height:0;overflow:hidden;">
        <q-card class="column shadow-2" style="flex:1;min-height:0;overflow:hidden;">
          <q-card-section class="bg-blue-8 text-white q-py-xs">
            <div class="row items-center justify-between no-wrap">
              <div class="row items-center q-gutter-xs">
                <q-icon name="warehouse" size="sm" />
                <div class="text-subtitle2 text-weight-bold" style="font-size: 0.8rem">List all PreBatch Package</div>
              </div>
              <div class="row items-center q-gutter-xs">
                <!-- All / Hide Boxed toggle -->
                <q-btn-group flat dense>
                  <q-btn
                    flat dense no-caps size="sm"
                    label="All"
                    :color="!middleHideBoxed ? 'white' : 'blue-3'"
                    :class="!middleHideBoxed ? 'bg-blue-6' : ''"
                    @click="middleHideBoxed = false"
                  />
                  <q-btn
                    flat dense no-caps size="sm"
                    icon="visibility_off"
                    label="Boxed"
                    :color="middleHideBoxed ? 'white' : 'blue-3'"
                    :class="middleHideBoxed ? 'bg-blue-6' : ''"
                    @click="middleHideBoxed = true"
                  />
                </q-btn-group>
                <q-badge color="white" text-color="blue-8" class="text-weight-bold">
                  <q-spinner-dots v-if="loadingRecords" size="14px" color="blue-8" class="q-mr-xs" />
                  {{ groupedMiddlePanel.reduce((n, r) => n + r.batches.reduce((m, b) => m + b.pkgs.length, 0), 0) }}
                </q-badge>
              </div>
            </div>
          </q-card-section>

          <div class="col relative-position">
            <q-inner-loading :showing="loadingRecords">
              <q-spinner-gears size="40px" color="blue-grey" />
            </q-inner-loading>
            <q-scroll-area class="fit">
              <div v-if="!loadingRecords && fhRecords.length === 0 && sppRecords.length === 0" class="text-center q-pa-lg text-grey">
                <q-icon name="inbox" size="lg" class="q-mb-sm" /><br>
                No pre-batch records found
              </div>

              <!-- ── 3-Level Tree: re_code → batch_id → package ── -->
              <q-list dense separator class="bg-white">
                <q-expansion-item
                  v-for="reNode in groupedMiddlePanel"
                  :key="reNode.re_code"
                  dense expand-separator
                  :header-class="filterMiddleWh === 'FH' ? 'bg-blue-1 text-blue-10' : 'bg-light-blue-1 text-light-blue-10'"
                >
                  <!-- Level 1 header: re_code + total weight -->
                  <template v-slot:header>
                    <q-item-section>
                      <q-item-label class="text-weight-bold" style="font-size:0.8rem">
                        {{ reNode.re_code }}
                      </q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <q-badge
                        :color="filterMiddleWh === 'FH' ? 'blue-7' : 'light-blue-7'"
                        class="text-weight-bold"
                        style="font-size:0.7rem"
                      >
                        {{ reNode.totalWeight.toFixed(3) }} kg
                      </q-badge>
                    </q-item-section>
                  </template>

                  <!-- Level 2: per-batch expansion -->
                  <q-list dense separator class="q-pl-sm">
                    <q-expansion-item
                      v-for="bNode in reNode.batches"
                      :key="bNode.batch_id"
                      dense expand-separator
                      header-class="bg-grey-1 text-grey-9"
                    >
                      <template v-slot:header>
                        <q-item-section avatar style="min-width:20px">
                          <q-icon name="inventory_2" size="xs" color="grey-6" />
                        </q-item-section>
                        <q-item-section>
                          <q-item-label style="font-size:0.72rem" class="text-weight-medium">
                            {{ bNode.batch_id.split('-').slice(-1)[0] }}
                            <span class="text-grey-5" style="font-size:0.65rem"> — {{ bNode.batch_id }}</span>
                          </q-item-label>
                        </q-item-section>
                        <q-item-section side>
                          <span class="text-weight-bold" style="font-size:0.72rem">
                            {{ bNode.totalWeight.toFixed(3) }} kg
                          </span>
                        </q-item-section>
                      </template>

                      <!-- Level 3: individual packages -->
                      <q-list dense class="q-pl-md bg-white">
                        <q-item
                          v-for="pkg in bNode.pkgs" :key="pkg.id"
                          dense style="min-height:28px"
                        >
                          <q-item-section avatar style="min-width:18px">
                            <q-icon
                              :name="pkg.status === 1 ? 'check_circle' : (pkg.recheck === 1 ? 'hourglass_top' : 'radio_button_unchecked')"
                              :color="pkg.status === 1 ? 'blue-7' : (pkg.recheck === 1 ? 'orange-7' : 'grey-4')"
                              size="xs"
                            />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label style="font-size:0.7rem" class="text-mono">
                              {{ pkg.label }}
                            </q-item-label>
                          </q-item-section>
                          <q-item-section side>
                            <span class="text-weight-bold" style="font-size:0.7rem">
                              {{ pkg.weight.toFixed(3) }} kg
                            </span>
                          </q-item-section>
                          <q-item-section side style="min-width:52px">
                            <q-badge
                              :color="pkg.status === 1 ? 'blue-7' : (pkg.recheck === 1 ? 'orange-7' : 'grey-4')"
                              :label="pkg.status === 1 ? 'Boxed' : (pkg.recheck === 1 ? 'Prepare' : 'Waiting')"
                              style="font-size:0.6rem"
                            />
                          </q-item-section>
                        </q-item>
                      </q-list>
                    </q-expansion-item>
                  </q-list>
                </q-expansion-item>

                <q-item v-if="groupedMiddlePanel.length === 0">
                  <q-item-section class="text-center text-grey q-pa-lg text-caption">
                    <q-icon name="inbox" size="sm" class="q-mb-xs" /><br>No pre-batch records
                  </q-item-section>
                </q-item>
              </q-list>
            </q-scroll-area>

          </div>
        </q-card>

      </div>

      <!-- ═══ 4TH PANEL: Ready to Delivery ═══ -->
      <div class="col-3 column" style="order:3;height:100%;min-height:0;overflow:hidden;">
        <q-card class="column shadow-2" style="flex:1;min-height:0;overflow:hidden;">
          <q-card-section class="bg-indigo-7 text-white q-py-xs">
            <div class="row items-center justify-between no-wrap">
              <div class="row items-center q-gutter-xs">
                <q-icon name="local_shipping" size="sm" />
                <div class="text-subtitle2 text-weight-bold">Ready to Delivery</div>
              </div>
              <div class="row items-center q-gutter-xs">
                <!-- WH Filter -->
                <q-btn-group flat dense>
                  <q-btn flat dense no-caps size="xs" label="All"
                    :color="filterDeliveryWh === 'ALL' ? 'yellow' : 'white'"
                    :text-color="filterDeliveryWh === 'ALL' ? 'indigo-9' : 'white'"
                    @click="filterDeliveryWh = 'ALL'"
                  />
                  <q-btn flat dense no-caps size="xs" label="FH"
                    :color="filterDeliveryWh === 'FH' ? 'yellow' : 'white'"
                    :text-color="filterDeliveryWh === 'FH' ? 'indigo-9' : 'white'"
                    @click="filterDeliveryWh = 'FH'"
                  />
                  <q-btn flat dense no-caps size="xs" label="SPP"
                    :color="filterDeliveryWh === 'SPP' ? 'yellow' : 'white'"
                    :text-color="filterDeliveryWh === 'SPP' ? 'indigo-9' : 'white'"
                    @click="filterDeliveryWh = 'SPP'"
                  />
                </q-btn-group>
                <q-badge color="white" text-color="indigo-7" class="text-weight-bold">
                  {{ groupedTransferredBoxes.filter(r =>
                      filterDeliveryWh === 'ALL' ||
                      (filterDeliveryWh === 'FH' && r.fh) ||
                      (filterDeliveryWh === 'SPP' && r.spp)
                    ).length }}
                </q-badge>
                <q-btn
                  flat round dense icon="local_shipping" size="sm" color="white"
                  :disable="groupedTransferredBoxes.length === 0"
                  @click="selectedForTransfer = transferredBoxes.map(b => b.id); showTransferDialog = true"
                >
                  <q-tooltip>Delivery &amp; Print Report</q-tooltip>
                </q-btn>
                <q-btn
                  flat round dense icon="print" size="sm" color="white"
                  :disable="groupedTransferredBoxes.length === 0"
                  @click="selectedForTransfer = transferredBoxes.map(b => b.id); showTransferDialog = true"
                >
                  <q-tooltip>Print Delivery Report</q-tooltip>
                </q-btn>
              </div>
            </div>
          </q-card-section>

          <div class="col relative-position">
            <q-scroll-area class="fit bg-white">
              <q-list dense separator>
                <template v-for="row in groupedTransferredBoxes" :key="row.batch_id">
                  <q-item
                    v-if="filterDeliveryWh === 'ALL' || (filterDeliveryWh === 'FH' && row.fh) || (filterDeliveryWh === 'SPP' && row.spp)"
                    class="q-pa-xs"
                  >
                    <q-item-section avatar style="min-width:28px;">
                      <q-icon
                        :name="deliveredMap.get(row.batch_id) ? 'verified' : 'check_circle'"
                        :color="deliveredMap.get(row.batch_id) ? 'green-8' : 'green'"
                        size="sm"
                      />
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="text-weight-bold text-caption">
                        {{ row.batch_id?.split('-').slice(0, -1).join('-') }} — <span class="text-indigo-8">{{ row.batch_id?.split('-').slice(-1)[0] }}</span>
                      </q-item-label>
                      <q-item-label caption style="font-size:0.62rem;">Boxed: {{ row.time }}</q-item-label>
                    </q-item-section>
                    <!-- WH badges -->
                    <q-item-section side style="min-width:60px;">
                      <div class="row q-gutter-xs">
                        <q-badge :color="row.fh ? 'blue-7' : 'grey-4'" class="text-weight-bold" style="font-size:0.6rem;">FH</q-badge>
                        <q-badge :color="row.spp ? 'light-blue-7' : 'grey-4'" class="text-weight-bold" style="font-size:0.6rem;">SPP</q-badge>
                      </div>
                    </q-item-section>
                    <!-- Delivery column -->
                    <q-item-section side>
                      <template v-if="deliveredMap.get(row.batch_id)">
                        <q-badge color="green-8" class="text-weight-bold" style="font-size:0.62rem;">
                          <q-icon name="local_shipping" size="10px" class="q-mr-xs"/>
                          {{ deliveredMap.get(row.batch_id) }}
                        </q-badge>
                      </template>
                      <template v-else>
                        <q-btn
                          dense unelevated no-caps size="xs"
                          color="amber-7" text-color="white"
                          icon="local_shipping" label="Deliver"
                          @click="markDelivered(row.batch_id)"
                        >
                          <q-tooltip>Mark as Delivered</q-tooltip>
                        </q-btn>
                      </template>
                    </q-item-section>
                  </q-item>
                </template>

                <q-item v-if="groupedTransferredBoxes.length === 0">
                  <q-item-section class="text-center text-grey q-pa-lg text-caption">
                    <q-icon name="inbox" size="sm" class="q-mb-sm" /><br>
                    No boxes ready for delivery yet
                  </q-item-section>
                </q-item>
              </q-list>
            </q-scroll-area>
          </div>
        </q-card>
      </div>
    </div>


    <!-- ═══ TRANSFER REPORT DIALOG ═══ -->
    <q-dialog v-model="showTransferDialog" persistent>
      <q-card style="width:560px;max-width:96vw;">
        <q-card-section class="bg-indigo-9 text-white q-py-sm">
          <div class="row items-center q-gutter-sm">
            <q-icon name="print" size="sm" />
            <div class="text-subtitle1 text-weight-bold">Transfer Report</div>
            <q-space />
            <q-btn flat round dense icon="close" v-close-popup />
          </div>
        </q-card-section>

        <q-card-section class="q-pa-sm">
          <div class="row items-center justify-between q-mb-sm">
            <div class="text-caption text-grey-7">Select boxes to include in report</div>
            <div class="row q-gutter-xs">
              <q-btn flat dense no-caps size="sm" label="All" color="indigo"
                @click="selectedForTransfer = transferredBoxes.map(b => b.id)" />
              <q-btn flat dense no-caps size="sm" label="None" color="grey"
                @click="selectedForTransfer = []" />
            </div>
          </div>
          <q-scroll-area style="height:320px;">
            <q-list dense separator>
              <q-item
                v-for="box in transferredBoxes" :key="box.id"
                clickable @click="() => {
                  const idx = selectedForTransfer.indexOf(box.id)
                  if (idx >= 0) selectedForTransfer.splice(idx, 1)
                  else selectedForTransfer.push(box.id)
                }"
                :class="selectedForTransfer.includes(box.id) ? 'bg-indigo-1' : ''"
              >
                <q-item-section avatar style="min-width:32px">
                  <q-checkbox
                    :model-value="selectedForTransfer.includes(box.id)"
                    color="indigo"
                    @update:model-value="(v) => {
                      const idx = selectedForTransfer.indexOf(box.id)
                      if (v && idx < 0) selectedForTransfer.push(box.id)
                      else if (!v && idx >= 0) selectedForTransfer.splice(idx, 1)
                    }"
                  />
                </q-item-section>
                <q-item-section avatar style="min-width:28px">
                  <q-icon
                    name="inventory_2"
                    :color="box.wh === 'FH' ? 'blue-7' : 'light-blue-7'"
                    size="sm"
                  />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-bold text-caption">
                    {{ box.batch_id }}
                  </q-item-label>
                  <q-item-label caption>{{ box.bagsCount }} bags · {{ box.time }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-badge
                    :color="box.wh === 'FH' ? 'blue-7' : 'light-blue-7'"
                    :label="box.wh"
                    class="text-weight-bold"
                  />
                </q-item-section>
              </q-item>
            </q-list>
          </q-scroll-area>
        </q-card-section>

        <q-separator />
        <q-card-actions align="between" class="q-px-md q-py-sm">
          <div class="text-caption text-grey-6">
            {{ selectedForTransfer.length }} / {{ transferredBoxes.length }} selected
          </div>
          <div class="row q-gutter-sm">
            <q-btn flat no-caps label="Cancel" color="grey" v-close-popup />
            <q-btn
              no-caps unelevated color="indigo-8"
              icon="print" label="Print Report"
              :disable="selectedForTransfer.length === 0"
              @click="printTransferReport"
            />
          </div>
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- ═══ SCAN SIMULATION DIALOG ═══ -->
    <q-dialog v-model="showScanDialog" position="bottom" full-width>
      <q-card style="max-height: 60vh;">
        <q-card-section :class="scanDialogWh === 'FH' ? 'bg-blue-7 text-white' : 'bg-light-blue-8 text-white'" class="q-py-sm">
          <div class="row items-center justify-between no-wrap">
            <div class="row items-center q-gutter-sm">
              <q-icon :name="scanDialogWh === 'FH' ? 'science' : 'inventory_2'" size="sm" />
              <div class="text-subtitle1 text-weight-bold">
                Simulate Scan — {{ scanDialogWh }} Pre-Batch
              </div>
            </div>
            <div class="row items-center q-gutter-xs">
              <q-badge color="white" :text-color="scanDialogWh === 'FH' ? 'blue-9' : 'light-blue-9'">
                {{ scanDialogBags.length }} bags
              </q-badge>
              <q-btn flat round dense icon="close" color="white" v-close-popup />
            </div>
          </div>
          <div class="text-caption q-mt-xs" style="opacity: 0.8;">
            Click a bag to simulate scanning it into the packing box
          </div>
        </q-card-section>

        <q-separator />

        <q-card-section class="q-pa-none" style="max-height: 45vh; overflow: auto;">
          <q-list dense separator>
            <q-item
              v-for="bag in scanDialogBags" :key="bag.id"
              clickable v-ripple
              @click="onSimScanClick(bag)"
              :class="isPacked(bag) ? 'bg-blue-1' : ''"
              style="min-height: 48px;"
            >
              <q-item-section avatar style="min-width: 30px;">
                <q-icon
                  :name="isPacked(bag) ? 'check_circle' : 'qr_code'"
                  :color="isPacked(bag) ? 'blue' : 'grey-6'"
                  size="sm"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-bold" style="font-size: 0.8rem;">
                  {{ bag.re_code }} — {{ bag.net_volume?.toFixed(3) }} kg
                </q-item-label>
                <q-item-label caption style="font-size: 0.65rem;">
                  {{ bag.batch_record_id }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge
                  :color="isPacked(bag) ? 'blue' : 'blue-grey'"
                  :label="isPacked(bag) ? 'Packed' : 'Tap to scan'"
                />
              </q-item-section>
            </q-item>
            <q-item v-if="scanDialogBags.length === 0">
              <q-item-section class="text-center text-grey q-pa-lg">
                <q-icon name="inbox" size="lg" class="q-mb-sm" /><br>
                No {{ scanDialogWh }} pre-batch bags available
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- ═══ SOUND SETTINGS DIALOG ═══ -->
    <q-dialog v-model="showSoundSettings" position="right" full-height>
      <q-card style="width: 380px; max-width: 90vw;" class="column">
        <!-- Header -->
        <q-card-section class="bg-blue-9 text-white q-py-sm">
          <div class="row items-center justify-between no-wrap">
            <div class="row items-center q-gutter-sm">
              <q-icon name="tune" size="sm" />
              <div class="text-subtitle1 text-weight-bold">Sound Settings</div>
            </div>
            <q-btn flat round dense icon="close" color="white" v-close-popup />
          </div>
        </q-card-section>

        <q-separator />

        <q-card-section class="col q-pa-md" style="overflow: auto;">
          <!-- Master Enable -->
          <div class="row items-center justify-between q-mb-md q-pa-sm rounded-borders" :class="soundSettings.enabled ? 'bg-green-1' : 'bg-grey-2'">
            <div class="row items-center q-gutter-sm">
              <q-icon :name="soundSettings.enabled ? 'volume_up' : 'volume_off'" :color="soundSettings.enabled ? 'green' : 'grey'" size="sm" />
              <div>
                <div class="text-weight-bold">Sound Effects</div>
                <div class="text-caption text-grey-7">{{ soundSettings.enabled ? 'Sounds are ON' : 'Sounds are OFF' }}</div>
              </div>
            </div>
            <q-toggle v-model="soundSettings.enabled" color="green" />
          </div>

          <template v-if="soundSettings.enabled">
            <!-- Volume Slider -->
            <div class="q-mb-lg">
              <div class="row items-center justify-between q-mb-xs">
                <div class="text-weight-bold text-body2">
                  <q-icon name="volume_up" size="xs" class="q-mr-xs" />Volume
                </div>
                <q-badge color="blue-9" :label="`${soundSettings.volume}%`" />
              </div>
              <q-slider
                v-model="soundSettings.volume"
                :min="10" :max="100" :step="5"
                color="blue-9"
                label
                :label-value="`${soundSettings.volume}%`"
                markers marker-labels
                snap
              />
            </div>

            <q-separator class="q-mb-md" />

            <!-- Correct Sound Selection -->
            <div class="q-mb-md">
              <div class="row items-center q-gutter-xs q-mb-sm">
                <q-icon name="check_circle" color="green" size="sm" />
                <span class="text-weight-bold text-body2">Correct Scan Sound</span>
              </div>
              <div class="q-gutter-xs">
                <q-btn
                  v-for="opt in correctSoundOptions" :key="opt.value"
                  :outline="soundSettings.correctSound !== opt.value"
                  :color="soundSettings.correctSound === opt.value ? 'green' : 'grey-5'"
                  :text-color="soundSettings.correctSound === opt.value ? 'white' : 'dark'"
                  dense no-caps size="sm"
                  class="q-mr-xs q-mb-xs"
                  @click="soundSettings.correctSound = opt.value as any"
                >
                  {{ opt.label }}
                </q-btn>
              </div>
              <div class="text-caption text-grey-6 q-mt-xs">
                {{ correctSoundOptions.find(o => o.value === soundSettings.correctSound)?.desc }}
              </div>
              <q-btn
                flat dense size="sm" icon="play_circle" label="Preview"
                color="green" class="q-mt-xs" no-caps
                @click="playSound('correct')"
              />
            </div>

            <q-separator class="q-mb-md" />

            <!-- Wrong Sound Selection -->
            <div class="q-mb-md">
              <div class="row items-center q-gutter-xs q-mb-sm">
                <q-icon name="cancel" color="red" size="sm" />
                <span class="text-weight-bold text-body2">Wrong Scan Sound</span>
              </div>
              <div class="q-gutter-xs">
                <q-btn
                  v-for="opt in wrongSoundOptions" :key="opt.value"
                  :outline="soundSettings.wrongSound !== opt.value"
                  :color="soundSettings.wrongSound === opt.value ? 'red' : 'grey-5'"
                  :text-color="soundSettings.wrongSound === opt.value ? 'white' : 'dark'"
                  dense no-caps size="sm"
                  class="q-mr-xs q-mb-xs"
                  @click="soundSettings.wrongSound = opt.value as any"
                >
                  {{ opt.label }}
                </q-btn>
              </div>
              <div class="text-caption text-grey-6 q-mt-xs">
                {{ wrongSoundOptions.find(o => o.value === soundSettings.wrongSound)?.desc }}
              </div>
              <q-btn
                flat dense size="sm" icon="play_circle" label="Preview"
                color="red" class="q-mt-xs" no-caps
                @click="playSound('wrong')"
              />
            </div>
          </template>

          <template v-else>
            <div class="text-center q-pa-lg text-grey">
              <q-icon name="volume_off" size="xl" class="q-mb-sm" /><br>
              <div class="text-body2">Sound effects are disabled</div>
              <div class="text-caption">Toggle the switch above to enable</div>
            </div>
          </template>
        </q-card-section>

        <!-- Footer -->
        <q-separator />
        <q-card-actions align="between" class="q-px-md">
          <q-btn flat dense no-caps color="grey" label="Reset Defaults" icon="restart_alt" @click="soundSettings = { ...defaultSoundSettings }" />
          <q-btn flat dense no-caps color="blue-9" label="Done" icon="check" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- ── Footer Bar ── -->
    <div class="row items-center justify-between q-px-sm"
         style="height:22px;background:#1a237e;flex-shrink:0;">
      <span style="font-size:0.65rem;color:#7986cb;">
        Packing List v2.2
      </span>
      <span style="font-size:0.65rem;font-family:'Courier New',monospace;color:#FFCC00;font-weight:bold;">
        xdev.co.th
      </span>
    </div>

  </q-page>
</template>

<style scoped>
.transition-all {
  transition: background-color 0.2s ease, color 0.2s ease;
}
</style>

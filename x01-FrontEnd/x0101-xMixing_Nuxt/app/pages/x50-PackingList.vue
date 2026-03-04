<script setup lang="ts">
/**
 * x50-PackingList.vue — Packing List View v2.1
 * 3-Panel Layout: Production Plans | Warehouse Bags | Batch Packing
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { appConfig } from '../appConfig/config'
import { useAuth } from '../composables/useAuth'
import { useMqttLocalDevice } from '../composables/useMqttLocalDevice'
import { usePackingPrints } from '../composables/usePackingPrints'

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
const filterReCode = ref('')         // filter ingredients by re_code

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

/** Group bags by ingredient re_code within selected warehouse for requirement list */
interface IngredientReq {
  re_code: string
  name: string
  totalVol: number
  packedVol: number
  totalBags: number
  packedBags: number
  bags: any[]
}
const ingredientsByDept = computed((): IngredientReq[] => {
  const whBags = filterMiddleWh.value === 'FH' ? bagsByWarehouse.value.FH : bagsByWarehouse.value.SPP
  const map = new Map<string, IngredientReq>()
  for (const bag of whBags) {
    const code = bag.re_code || '?'
    if (!map.has(code)) {
      map.set(code, { re_code: code, name: bag.ingredient_name || code, totalVol: 0, packedVol: 0, totalBags: 0, packedBags: 0, bags: [] })
    }
    const ing = map.get(code)!
    ing.totalVol += bag.net_volume || 0
    ing.totalBags++
    ing.bags.push(bag)
    if (isPacked(bag)) {
      ing.packedVol += bag.net_volume || 0
      ing.packedBags++
    }
  }
  let result = [...map.values()].sort((a, b) => a.re_code.localeCompare(b.re_code))
  // Apply re_code filter
  if (filterReCode.value.trim()) {
    const q = filterReCode.value.trim().toLowerCase()
    result = result.filter(i => i.re_code.toLowerCase().includes(q) || i.name.toLowerCase().includes(q))
  }
  return result
})

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
          inProduction: !!b.production,
        })
      }
      if (b.spp_boxed_at) {
        boxes.push({
          id: `${b.batch_id}-SPP`,
          wh: 'SPP',
          batch_id: b.batch_id,
          bagsCount: 0,
          time: new Date(b.spp_boxed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          inProduction: !!b.production,
        })
      }
      // Populate deliveredMap from DB (keyed per WH: "batch_id-FH" / "batch_id-SPP")
      if (b.fh_delivered_at) {
        deliveredMap.value.set(`${b.batch_id}-FH`, new Date(b.fh_delivered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))
      }
      if (b.spp_delivered_at) {
        deliveredMap.value.set(`${b.batch_id}-SPP`, new Date(b.spp_delivered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))
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
  inProduction: boolean  // batch.production flag — hides from delivery panel
}
const transferredBoxes = ref<TransferredBox[]>([])

// ── Transfer Dialog ──────────────────────────────────────────────
const showTransferDialog   = ref(false)
const selectedForTransfer  = ref<string[]>([])   // list of TransferredBox.id
const filterDeliveryWh     = ref<'ALL'|'FH'|'SPP'>('ALL')
const filterDeliveryStatus = ref<'ALL'|'WAITING'>('WAITING')  // ALL=show delivered too, WAITING=pending only
const deliveredMap         = ref<Map<string, string>>(new Map())  // "batch_id-WH" → delivery time

const markDelivered = async (batch_id: string, wh: 'FH' | 'SPP') => {
  const label = wh === 'FH' ? 'FH → SPP' : 'SPP → Production'
  try {
    await $fetch(`${appConfig.apiBaseUrl}/production-batches/by-batch-id/${batch_id}/deliver`, {
      method: 'PATCH',
      headers: getAuthHeader() as Record<string, string>,
      body: { wh, delivered_by: 'operator' },
    })
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    deliveredMap.value = new Map(deliveredMap.value).set(`${batch_id}-${wh}`, time)
    playSound('correct')
    $q.notify({ type: 'positive', icon: 'local_shipping', message: `✅ ${label}: ${batch_id} delivered at ${time}`, position: 'top', timeout: 2500 })
  } catch (e) {
    console.error('Error marking delivery:', e)
    $q.notify({ type: 'negative', message: `Failed to mark ${batch_id} ${wh} as delivered` })
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
  inProduction: boolean
}
const groupedTransferredBoxes = computed((): TransferredBatchRow[] => {
  const map = new Map<string, TransferredBatchRow>()
  for (const box of transferredBoxes.value) {
    if (!map.has(box.batch_id)) {
      map.set(box.batch_id, { batch_id: box.batch_id, fh: null, spp: null, time: box.time, inProduction: box.inProduction })
    }
    const row = map.get(box.batch_id)!
    if (box.wh === 'FH') row.fh = box
    else row.spp = box
    if (box.time !== '—') row.time = box.time
    if (box.inProduction) row.inProduction = true
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

// ── Print Functions (composable) ──────────────────────────────────
const { printPackingBoxReport, printTransferReport, printBoxLabel, printBagLabel } = usePackingPrints({
  $q,
  plans,
  selectedBatch,
  batchInfo,
  bagsByWarehouse,
  allRecords,
  transferredBoxes,
  selectedForTransfer,
  showTransferDialog,
})




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

/** Handle scan input from FH/SPP scan fields — lookup by batch_record_id */
const onScanInputEnter = async (wh: 'FH' | 'SPP') => {
  const scanValue = wh === 'FH' ? scanFH.value.trim() : scanSPP.value.trim()
  if (!scanValue) return

  if (!selectedBatch.value) {
    playSound('wrong')
    $q.notify({ type: 'negative', message: t('packingList.selectBatchFirst'), icon: 'warning', position: 'top' })
    return
  }

  // Find the bag by batch_record_id in batchRecords for this warehouse
  const whBags = wh === 'FH' ? bagsByWarehouse.value.FH : bagsByWarehouse.value.SPP
  const bag = whBags.find(b => 
    b.batch_record_id === scanValue || 
    b.id?.toString() === scanValue ||
    b.intake_id === scanValue
  )

  if (!bag) {
    playSound('wrong')
    $q.notify({ type: 'negative', icon: 'error', message: t('packingList.bagNotFound'), caption: scanValue, position: 'top', timeout: 3000 })
    if (wh === 'FH') scanFH.value = ''
    else scanSPP.value = ''
    return
  }

  if (isPacked(bag)) {
    $q.notify({ type: 'info', message: t('packingList.alreadyPacked'), caption: bag.batch_record_id, position: 'top', timeout: 2000 })
    if (wh === 'FH') scanFH.value = ''
    else scanSPP.value = ''
    return
  }

  // Process the scan — same logic as onSimScanClick
  await onSimScanClick(bag)
  if (wh === 'FH') scanFH.value = ''
  else scanSPP.value = ''
}

// Watch for MQTT scans — smart routing: intake ID vs batch ID
watch(lastScan, (scan) => {
  if (!scan?.barcode) return
  const barcode = scan.barcode.trim()

  // If a batch is selected, try to match as intake ID first
  if (selectedBatch.value) {
    const allBags = [...bagsByWarehouse.value.FH, ...bagsByWarehouse.value.SPP]
    const bag = allBags.find(b =>
      b.batch_record_id === barcode ||
      b.id?.toString() === barcode ||
      b.intake_id === barcode
    )
    if (bag) {
      // Route to packing
      onSimScanClick(bag)
      return
    }
  }

  // Otherwise, treat as batch ID scan
  scanBatchId.value = barcode
  onScanBatchEnter()
})

// Auto-close box prompt when all bags for a warehouse are packed
watch([allFhPacked, allSppPacked], ([fhDone, sppDone]) => {
  if (!selectedBatch.value) return
  if (fhDone && filterMiddleWh.value === 'FH' && bagsByWarehouse.value.FH.length > 0) {
    $q.notify({ type: 'positive', icon: 'check_circle', message: t('packingList.allFhPacked'), position: 'top', timeout: 2000 })
  }
  if (sppDone && filterMiddleWh.value === 'SPP' && bagsByWarehouse.value.SPP.length > 0) {
    $q.notify({ type: 'positive', icon: 'check_circle', message: t('packingList.allSppPacked'), position: 'top', timeout: 2000 })
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
          <q-separator vertical class="q-mx-xs" />
          <!-- Department Filter -->
          <q-select
            v-model="filterMiddleWh"
            :options="['FH', 'SPP']"
            dense outlined options-dense
            style="width: 80px;"
            class="text-weight-bold"
            color="blue-9"
          />
          <!-- RE-Code Filter -->
          <q-input
            v-model="filterReCode"
            outlined dense clearable
            placeholder="Filter RE-Code..."
            style="width: 180px;"
            bg-color="grey-1"
          >
            <template v-slot:prepend>
              <q-icon name="filter_list" color="grey-6" size="xs" />
            </template>
          </q-input>
        </div>
        <div class="row items-center q-gutter-sm">
          <q-btn flat dense round :icon="soundSettings.enabled ? 'volume_up' : 'volume_off'" color="blue-9" @click="showSoundSettings = true">
            <q-tooltip>Sound Settings</q-tooltip>
          </q-btn>
          <q-btn flat dense round icon="refresh" color="blue-9" @click="fetchPlans(); fetchAllRecords(); fetchReadyToDeliver()" :loading="loading">
            <q-tooltip>Refresh</q-tooltip>
          </q-btn>
          <div class="text-caption text-grey-5">v2.3</div>
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
                <div class="text-subtitle2 text-weight-bold">{{ t('packingList.productionPlans') }}</div>
              </div>
              <q-badge color="white" text-color="blue-9" class="text-weight-bold">
                {{ activePlans.length }}
              </q-badge>
            </div>
          </q-card-section>

          <div class="col relative-position">
            <q-scroll-area class="fit">
              <q-list dense separator class="bg-white">
                <q-expansion-item
                  v-for="plan in activePlans" :key="plan.plan_id"
                  dense expand-separator
                  :header-class="selectedPlan?.plan_id === plan.plan_id ? 'bg-blue-1 text-blue-10' : 'bg-grey-1 text-grey-9'"
                  @show="onPlanClick(plan)"
                >
                  <!-- Level 1 header: plan_id + batch count -->
                  <template v-slot:header>
                    <q-item-section>
                      <q-item-label class="text-weight-bold" style="font-size:0.8rem">
                        {{ plan.plan_id }}
                      </q-item-label>
                      <q-item-label caption style="font-size:0.65rem">{{ plan.sku_name || plan.sku_id }}</q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <q-badge color="blue-7" class="text-weight-bold" style="font-size:0.7rem">
                        {{ (plan.batches || []).length }} batch
                      </q-badge>
                    </q-item-section>
                  </template>

                  <!-- Level 2: per-batch expansion -->
                  <q-list dense separator class="q-pl-sm">
                    <q-expansion-item
                      v-for="batch in (plan.batches || [])" :key="batch.batch_id"
                      dense expand-separator
                      :header-class="selectedBatch?.batch_id === batch.batch_id ? 'bg-blue-1 text-blue-9' : 'bg-grey-1 text-grey-9'"
                      @show="onBatchClick(batch, plan)"
                    >
                      <template v-slot:header>
                        <q-item-section avatar style="min-width:20px">
                          <q-icon
                            :name="batch.batch_prepare ? 'check_circle' : 'pending'"
                            :color="batch.batch_prepare ? 'blue-7' : 'grey-5'"
                            size="xs"
                          />
                        </q-item-section>
                        <q-item-section>
                          <q-item-label style="font-size:0.72rem" class="text-weight-medium">
                            {{ batch.batch_id.split('-').slice(-1)[0] }}
                            <span class="text-grey-5" style="font-size:0.65rem"> — {{ batch.batch_id }}</span>
                          </q-item-label>
                        </q-item-section>
                        <q-item-section side>
                          <q-badge
                            :color="batch.batch_prepare ? 'blue-7' : 'grey-5'"
                            :label="batch.batch_prepare ? 'Prepared' : batch.status"
                            style="font-size:0.6rem"
                          />
                        </q-item-section>
                      </template>

                      <!-- Level 3: ingredients -->
                      <q-list dense class="q-pl-md bg-white">
                        <q-item
                          v-for="req in (batch.reqs || [])" :key="req.id"
                          dense style="min-height:28px"
                        >
                          <q-item-section avatar style="min-width:18px">
                            <q-icon
                              :name="req.status === 2 ? 'check_circle' : (req.status === 1 ? 'hourglass_top' : 'radio_button_unchecked')"
                              :color="req.status === 2 ? 'blue-7' : (req.status === 1 ? 'orange-7' : 'grey-4')"
                              size="xs"
                            />
                          </q-item-section>
                          <q-item-section>
                            <q-item-label style="font-size:0.7rem" class="text-mono">
                              {{ req.re_code }}
                            </q-item-label>
                          </q-item-section>
                          <q-item-section side>
                            <span class="text-weight-bold" style="font-size:0.7rem">
                              {{ req.required_volume?.toFixed(1) }} kg
                            </span>
                          </q-item-section>
                          <q-item-section side style="min-width:52px">
                            <q-badge
                              :color="req.status === 2 ? 'blue-7' : (req.status === 1 ? 'orange-7' : 'grey-4')"
                              :label="req.status === 2 ? 'Done' : (req.status === 1 ? 'In-Prog' : 'Waiting')"
                              style="font-size:0.6rem"
                            />
                          </q-item-section>
                        </q-item>
                        <q-item v-if="!batch.reqs || batch.reqs.length === 0" style="min-height:28px">
                          <q-item-section class="text-grey text-italic" style="font-size:0.65rem">No requirements</q-item-section>
                        </q-item>
                      </q-list>
                    </q-expansion-item>
                    <q-item v-if="!plan.batches || plan.batches.length === 0" style="min-height:28px">
                      <q-item-section class="text-grey text-italic" style="font-size:0.7rem">No batches</q-item-section>
                    </q-item>
                  </q-list>
                </q-expansion-item>

                <q-item v-if="activePlans.length === 0">
                  <q-item-section class="text-center text-grey q-pa-lg text-caption">
                    <q-icon name="inbox" size="sm" class="q-mb-xs" /><br>No active plans
                  </q-item-section>
                </q-item>
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
                <div class="text-subtitle2 text-weight-bold">{{ t('packingList.packingBox') }}</div>
              </div>
              <div class="row items-center q-gutter-sm">
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
              :placeholder="t('packingList.scanBoxLabel')"
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
                    <div class="text-grey-6">{{ t('packingList.skuName') }}</div>
                    <div class="text-weight-bold text-body2">{{ batchInfo.sku_name }}</div>
                  </div>
                  <div class="col-6">
                    <div class="text-grey-6">{{ t('packingList.planId') }}</div>
                    <div class="text-weight-bold text-body2">{{ batchInfo.plan_id }}</div>
                  </div>
                  <div class="col-6 q-mt-xs">
                    <div class="text-grey-6">{{ t('packingList.batchSize') }}</div>
                    <div class="text-weight-bold text-body2">{{ batchInfo.batch_size }} kg</div>
                  </div>
                  <div class="col-6 q-mt-xs">
                    <div class="text-grey-6">{{ t('packingList.status') }}</div>
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
              <span class="text-caption">{{ t('packingList.scanOrSelect') }}</span>
            </div>

          </q-card-section>
        </q-card>


        <q-card class="col column shadow-2">
          <q-card-section :class="filterMiddleWh === 'FH' ? 'bg-blue-8 text-white' : 'bg-light-blue-8 text-white'" class="q-py-xs">
            <div class="row items-center justify-between no-wrap">
              <div class="row items-center q-gutter-xs">
                <q-icon :name="filterMiddleWh === 'FH' ? 'science' : 'inventory_2'" size="sm" />
                <div class="text-subtitle2 text-weight-bold">{{ t('packingList.requiredIngredients') }} — {{ filterMiddleWh }}</div>
              </div>
              <div class="row items-center q-gutter-xs">
                <q-badge color="white" :text-color="filterMiddleWh === 'FH' ? 'blue-9' : 'light-blue-9'" class="text-weight-bold">
                  {{ ingredientsByDept.reduce((s, i) => s + i.packedVol, 0).toFixed(2) }}/{{ ingredientsByDept.reduce((s, i) => s + i.totalVol, 0).toFixed(2) }} kg
                </q-badge>
                <q-badge color="white" :text-color="filterMiddleWh === 'FH' ? 'blue-9' : 'light-blue-9'" class="text-weight-bold">
                  {{ ingredientsByDept.reduce((s, i) => s + i.packedBags, 0) }}/{{ ingredientsByDept.reduce((s, i) => s + i.totalBags, 0) }}
                </q-badge>
                <q-btn
                  dense flat size="xs" icon="unarchive" label="Boxed"
                  :color="(filterMiddleWh === 'FH' ? allFhPacked : allSppPacked) ? 'white' : 'blue-3'"
                  :disable="!(filterMiddleWh === 'FH' ? allFhPacked : allSppPacked)"
                  @click="onCloseBox(filterMiddleWh)"
                  class="text-weight-bold"
                />
              </div>
            </div>
          </q-card-section>

          <!-- Scan Field -->
          <q-card-section class="q-py-xs">
            <q-input
              v-if="filterMiddleWh === 'FH'"
              v-model="scanFH"
              outlined dense
              :placeholder="t('packingList.scanFhBag')"
              bg-color="blue-1"
              @keyup.enter="onScanInputEnter('FH')"
            >
              <template v-slot:prepend>
                <q-icon name="qr_code_scanner" color="blue-8" size="sm" class="cursor-pointer" @click="openScanSimulator('FH')">
                  <q-tooltip>{{ t('packingList.clickSimScan') }}</q-tooltip>
                </q-icon>
              </template>
              <template v-slot:append>
                <q-btn flat round dense icon="search" color="blue-8" size="sm" @click="onScanInputEnter('FH')" />
              </template>
            </q-input>
            <q-input
              v-else
              v-model="scanSPP"
              outlined dense
              :placeholder="t('packingList.scanSppBag')"
              bg-color="light-blue-1"
              @keyup.enter="onScanInputEnter('SPP')"
            >
              <template v-slot:prepend>
                <q-icon name="qr_code_scanner" color="light-blue-8" size="sm" class="cursor-pointer" @click="openScanSimulator('SPP')">
                  <q-tooltip>{{ t('packingList.clickSimScan') }}</q-tooltip>
                </q-icon>
              </template>
              <template v-slot:append>
                <q-btn flat round dense icon="search" color="light-blue-8" size="sm" @click="onScanInputEnter('SPP')" />
              </template>
            </q-input>
          </q-card-section>

          <div class="col relative-position">
            <q-scroll-area class="fit q-pa-xs">
              <div v-if="!selectedBatch" class="text-center q-pa-lg text-grey">
                <q-icon name="inventory_2" size="xl" class="q-mb-sm" /><br>
                {{ t('packingList.selectBatchToView') }}
              </div>

              <template v-else>
                <!-- Ingredient Requirements List -->
                <q-list dense separator class="bg-white">
                  <q-expansion-item
                    v-for="ing in ingredientsByDept" :key="ing.re_code"
                    dense expand-separator
                    :header-class="ing.packedBags === ing.totalBags ? 'bg-blue-1' : (ing.packedBags > 0 ? 'bg-orange-1' : 'bg-grey-1')"
                  >
                    <template v-slot:header>
                      <q-item-section avatar style="min-width:24px">
                        <q-icon
                          :name="ing.packedBags === ing.totalBags ? 'check_circle' : (ing.packedBags > 0 ? 'hourglass_top' : 'radio_button_unchecked')"
                          :color="ing.packedBags === ing.totalBags ? 'blue-7' : (ing.packedBags > 0 ? 'orange-7' : 'grey-4')"
                          size="sm"
                        />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label class="text-weight-bold" style="font-size:0.8rem">
                          {{ ing.re_code }}
                        </q-item-label>
                        <q-item-label caption style="font-size:0.65rem">
                          {{ ing.totalVol.toFixed(3) }} kg
                        </q-item-label>
                      </q-item-section>
                      <q-item-section side>
                        <q-badge
                          :color="ing.packedBags === ing.totalBags ? 'blue-7' : (ing.packedBags > 0 ? 'orange-7' : 'grey-4')"
                          class="text-weight-bold"
                          style="font-size:0.65rem"
                        >
                          {{ ing.packedBags }}/{{ ing.totalBags }} bags
                        </q-badge>
                      </q-item-section>
                    </template>

                    <!-- Expandable: individual bags -->
                    <q-list dense class="q-pl-md bg-white">
                      <q-item
                        v-for="bag in ing.bags" :key="bag.id"
                        dense clickable style="min-height:30px;cursor:pointer"
                        :class="getBagRowClass(bag)"
                        @click="printBagLabel(bag)"
                      >
                        <q-item-section avatar style="min-width:20px">
                          <q-icon :name="getBagStatusIcon(bag)" :color="getBagStatusColor(bag)" size="xs" />
                        </q-item-section>
                        <q-item-section>
                          <q-item-label style="font-size:0.7rem" class="text-mono">
                            {{ bag.batch_record_id }}
                          </q-item-label>
                        </q-item-section>
                        <q-item-section side>
                          <span class="text-weight-bold" style="font-size:0.7rem">{{ bag.net_volume?.toFixed(3) }} kg</span>
                        </q-item-section>
                        <q-item-section side style="min-width:52px">
                          <q-badge :color="getBagStatusColor(bag)" :label="getBagStatusLabel(bag)" style="font-size:0.6rem" />
                        </q-item-section>
                      </q-item>
                    </q-list>
                  </q-expansion-item>

                  <q-item v-if="ingredientsByDept.length === 0">
                    <q-item-section class="text-center text-grey text-italic text-caption q-pa-md">
                      <q-icon name="inbox" size="md" class="q-mb-xs" /><br>
                      {{ filterMiddleWh === 'FH' ? t('packingList.noFhBags') : t('packingList.noSppBags') }}
                    </q-item-section>
                  </q-item>
                </q-list>
              </template>
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
                <div class="text-subtitle2 text-weight-bold">
                  Ready to Delivery
                  <span class="text-caption" style="opacity:0.8">— {{ filterMiddleWh === 'FH' ? 'FH → SPP' : 'SPP → Prod' }}</span>
                </div>
              </div>
              <div class="row items-center q-gutter-xs">
                <q-select
                  v-model="filterDeliveryStatus"
                  :options="[{ label: 'All', value: 'ALL' }, { label: 'Waiting', value: 'WAITING' }]"
                  emit-value map-options dense outlined
                  style="min-width:80px;background:rgba(255,255,255,0.15);border-radius:4px;"
                  input-class="text-white text-caption"
                  popup-content-class="text-caption"
                  color="white"
                  dark
                />
                <q-badge color="white" text-color="indigo-7" class="text-weight-bold">
                  {{ groupedTransferredBoxes.filter(r => {
                    if (r.inProduction) return false
                    const hasWh = filterMiddleWh === 'FH' ? !!r.fh : !!r.spp
                    const isDelivered = filterMiddleWh === 'FH' ? !!deliveredMap.get(`${r.batch_id}-FH`) : !!deliveredMap.get(`${r.batch_id}-SPP`)
                    return hasWh && (filterDeliveryStatus === 'ALL' || !isDelivered)
                  }).length }}
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
                    v-if="(() => {
                      if (row.inProduction) return false
                      const hasWh = filterMiddleWh === 'FH' ? !!row.fh : !!row.spp
                      const isDelivered = filterMiddleWh === 'FH' ? !!deliveredMap.get(`${row.batch_id}-FH`) : !!deliveredMap.get(`${row.batch_id}-SPP`)
                      return hasWh && (filterDeliveryStatus === 'ALL' || !isDelivered)
                    })()"
                    class="q-pa-xs"
                  >
                    <q-item-section>
                      <q-item-label class="text-weight-bold text-caption">
                        {{ row.batch_id?.split('-').slice(0, -1).join('-') }} — <span class="text-indigo-8">{{ row.batch_id?.split('-').slice(-1)[0] }}</span>
                      </q-item-label>
                    </q-item-section>

                    <q-item-section side style="padding-right:0;min-width:28px">
                      <q-btn flat round dense icon="print" size="xs" color="indigo-4"
                        @click.stop="printPackingBoxReport(row.batch_id, filterMiddleWh)">
                        <q-tooltip>Print Box Report (A4)</q-tooltip>
                      </q-btn>
                    </q-item-section>

                    <!-- Per-WH delivery: only shows the section matching the Packing Box dropdown -->
                    <q-item-section side>
                      <div class="column q-gutter-xs items-end">
                        <!-- FH boxed → deliver to SPP (only when FH dropdown selected) -->
                        <template v-if="row.fh && filterMiddleWh === 'FH'">
                          <div class="row items-center q-gutter-xs">
                            <q-badge color="blue-7" style="font-size:0.58rem;">
                              FH <q-icon name="unarchive" size="10px" class="q-ml-xs"/> {{ row.fh.time }}
                            </q-badge>
                            <q-badge v-if="deliveredMap.get(`${row.batch_id}-FH`)" color="green-8" class="text-weight-bold" style="font-size:0.58rem;">
                              <q-icon name="local_shipping" size="10px" class="q-mr-xs"/>→SPP {{ deliveredMap.get(`${row.batch_id}-FH`) }}
                            </q-badge>
                            <q-btn v-else dense unelevated no-caps size="xs" color="blue-7" text-color="white" icon="local_shipping" label="→SPP" @click="markDelivered(row.batch_id, 'FH')">
                              <q-tooltip>Deliver FH to SPP</q-tooltip>
                            </q-btn>
                          </div>
                        </template>
                        <!-- SPP boxed → deliver to Production Hall (only when SPP dropdown selected) -->
                        <template v-if="row.spp && filterMiddleWh === 'SPP'">
                          <div class="row items-center q-gutter-xs">
                            <q-badge color="light-blue-7" style="font-size:0.58rem;">
                              SPP <q-icon name="unarchive" size="10px" class="q-ml-xs"/> {{ row.spp.time }}
                            </q-badge>
                            <q-badge v-if="deliveredMap.get(`${row.batch_id}-SPP`)" color="green-8" class="text-weight-bold" style="font-size:0.58rem;">
                              <q-icon name="local_shipping" size="10px" class="q-mr-xs"/>→Prod {{ deliveredMap.get(`${row.batch_id}-SPP`) }}
                            </q-badge>
                            <q-btn v-else dense unelevated no-caps size="xs" color="amber-7" text-color="white" icon="local_shipping" label="→Prod" @click="markDelivered(row.batch_id, 'SPP')">
                              <q-tooltip>Deliver SPP to Production Hall</q-tooltip>
                            </q-btn>
                          </div>
                        </template>
                      </div>
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
            <div class="text-subtitle1 text-weight-bold">
              Transfer Report
              <span class="text-caption" style="opacity:0.8"> — {{ filterMiddleWh === 'FH' ? 'FH → SPP' : 'SPP → Production' }}</span>
            </div>
            <q-space />
            <q-btn flat round dense icon="close" v-close-popup />
          </div>
        </q-card-section>

        <q-card-section class="q-pa-sm">
          <div class="row items-center justify-between q-mb-sm">
            <div class="text-caption text-grey-7">Select boxes to include in report</div>
            <div class="row q-gutter-xs">
              <q-btn flat dense no-caps size="sm" label="All" color="indigo"
                @click="selectedForTransfer = transferredBoxes.filter(b => b.wh === filterMiddleWh).map(b => b.id)" />
              <q-btn flat dense no-caps size="sm" label="None" color="grey"
                @click="selectedForTransfer = []" />
            </div>
          </div>
          <q-scroll-area style="height:320px;">
            <q-list dense separator>
              <q-item
                v-for="box in transferredBoxes.filter(b => b.wh === filterMiddleWh)" :key="box.id"
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
                    :label="box.wh === 'FH' ? 'FH→SPP' : 'SPP→Prod'"
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
            {{ selectedForTransfer.length }} / {{ transferredBoxes.filter(b => b.wh === filterMiddleWh).length }} selected
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

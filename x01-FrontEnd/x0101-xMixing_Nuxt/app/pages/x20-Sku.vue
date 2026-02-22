<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { QTableColumn } from 'quasar'
import { useQuasar } from 'quasar'
import { appConfig } from '~/appConfig/config'

const formatDate = (date: any) => {
  if (!date) return '-'
  const d = new Date(date)
  if (isNaN(d.getTime())) return date
  return d.toLocaleDateString('en-GB')
}

// ============================================================================
// INTERFACES
// ============================================================================

interface SkuMaster {
  id?: number
  sku_id: string
  sku_name: string
  std_batch_size?: number
  uom?: string
  sku_group?: number | null
  sku_group_code?: string
  sku_group_name?: string
  status: string
  creat_by?: string
  created_at?: string
  update_by?: string
  updated_at?: string
  total_phases?: number
  total_sub_steps?: number
}

interface SkuStep {
  id?: number
  step_id?: number
  sku_id: string
  phase_number: string
  phase_id?: string
  sub_step: number
  step_label?: string
  action?: string
  re_code?: string
  action_code?: string
  action_description?: string
  full_action_description?: string
  destination?: string
  destination_description?: string
  ingredient_name?: string
  mat_sap_code?: string
  blind_code?: string
  require?: number
  uom?: string
  low_tol?: number
  high_tol?: number
  step_condition?: string
  agitator_rpm?: number
  high_shear_rpm?: number
  temperature?: number
  temp_low?: number
  temp_high?: number
  ph?: number
  brix?: number
  brix_sp?: string
  ph_sp?: string
  step_time?: number
  setup_step?: string
  ingredient_unit?: string
  step_timer_control?: number
  qc_temp?: boolean
  qc_ph?: boolean
  qc_brix?: boolean
  record_steam_pressure?: boolean
  record_ctw?: boolean
  operation_brix_record?: boolean
  operation_ph_record?: boolean
  master_step?: boolean
}

interface SkuAction {
  action_code: string
  action_description: string
  component_filter?: string
}

interface SkuDestination {
  destination_code: string
  description: string
}

interface SkuPhase {
  phase_id: number
  phase_code: string // Made required to help TS, or handle empty string
  phase_description: string
}

interface Ingredient {
  re_code?: string
  name: string
  mat_sap_code?: string
  blind_code?: string
  Group?: string // Added
}

const $q = useQuasar()
const { t } = useI18n()

// --- Master Data ---
const skuMasters = ref<SkuMaster[]>([])
const skuStepsMap = ref<{ [key: string]: SkuStep[] }>({})
const selectedSkuId = ref<string | null>(null)
const selectedSkuData = ref<SkuMaster | null>(null)
const expandedPhases = ref<{[key: string]: string[]}>({})

// --- Lookups ---
const skuActions = ref<SkuAction[]>([])
const skuDestinations = ref<SkuDestination[]>([])
const skuPhases = ref<SkuPhase[]>([])
const skuGroups = ref<{ id: number, group_code: string, group_name: string, description?: string, status?: string }[]>([])
const ingredients = ref<Ingredient[]>([])
const ingredientOptions = ref<{label: string, value: string, original: Ingredient}[]>([])

// --- State Tracking ---
const isLoading = ref(false)
const isSaving = ref(false)
const searchFilter = ref('')
const selectedSkus = ref<SkuMaster[]>([])
const showAllIncludingInactive = ref(false)
const showFilters = ref(false)
const filterSkuId = ref('')
const filterSkuName = ref('')
const filterGroup = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const skuTableExpanded = ref(true)

const groupedSteps = computed<{ phaseNum: string, steps: SkuStep[], firstStep: SkuStep | undefined }[]>(() => {
  if (!selectedSkuId.value) return []
  const steps = skuStepsMap.value[selectedSkuId.value] || []
  const groups: { [key: string]: { phaseNum: string, steps: SkuStep[], firstStep: SkuStep | undefined } } = {}
  steps.forEach(s => {
    const pn = s.phase_number
    if (!groups[pn]) groups[pn] = { phaseNum: pn, steps: [], firstStep: s }
    groups[pn].steps.push(s)
  })
  return Object.values(groups).sort((a,b) => a.phaseNum.localeCompare(b.phaseNum))
})

const ingredientSummary = computed(() => {
  if (!selectedSkuId.value) return []
  const steps = skuStepsMap.value[selectedSkuId.value] || []
  const map: { [key: string]: { re_code: string, name: string, total: number, uom: string, phases: string[] } } = {}
  steps.forEach(s => {
    if (s.ingredient_name && s.require && s.require > 0) {
      const key = s.re_code || s.ingredient_name || ''
      if (!map[key]) map[key] = { re_code: s.re_code || '', name: s.ingredient_name || '', total: 0, uom: s.uom || s.ingredient_unit || 'kg', phases: [] }
      map[key].total += s.require
      if (!map[key].phases.includes(s.phase_number)) map[key].phases.push(s.phase_number)
    }
  })
  return Object.values(map).sort((a, b) => b.total - a.total)
})

// --- Control State ---
const showSkuDialog = ref(false)
const showStepDialog = ref(false)
const showActionDialog = ref(false)
const showPhaseDialog = ref(false)
const showDuplicateDialog = ref(false)
const showGroupDialog = ref(false)

const isCreatingSku = ref(false)
const isEditMode = ref(false)
const isSavingAction = ref(false)
const isActionEdit = ref(false)
const isDuplicating = ref(false)
const actionSearch = ref('')
const phaseSearch = ref('')
const groupSearch = ref('')
const isGroupEdit = ref(false)
const isSavingGroup = ref(false)

// --- Forms ---
const editingSkuId = ref<number | undefined>(undefined)
const skuForm = ref({
  sku_id: '',
  sku_name: '',
  std_batch_size: 0,
  uom: 'kg',
  sku_group: null as number | null,
  status: 'Active'
})

const duplicateForm = ref({
  source_sku_id: '',
  new_sku_id: '',
  new_sku_name: ''
})

const groupForm = ref({
  group_code: '',
  group_name: '',
  description: ''
})

const editingStep = ref<SkuStep | null>(null)
const stepForm = ref<SkuStep>({
  sku_id: '',
  phase_number: '',
  phase_id: '',
  sub_step: 0,
  action: '',
  re_code: '',
  action_code: '',
  action_description: '',
  destination: '',
  require: 0,
  uom: 'kg',
  low_tol: 0.001,
  high_tol: 0.001,
  step_condition: '',
  agitator_rpm: 0,
  high_shear_rpm: 0,
  temperature: 0,
  temp_low: 0,
  temp_high: 0,
  step_time: 0,
  brix_sp: '',
  ph_sp: '',
  qc_temp: false,
  record_steam_pressure: false,
  record_ctw: false,
  operation_brix_record: false,
  operation_ph_record: false,
  master_step: false
})

const actionForm = ref<SkuAction>({
  action_code: '',
  action_description: ''
})

const editingPhase = ref<SkuPhase | null>(null)
const phaseForm = ref<{ phase_id: number | null, phase_code: string, phase_description: string }>({ 
  phase_id: null, 
  phase_code: '', 
  phase_description: '' 
})

// ============================================================================
// ACTION MANAGEMENT
// ============================================================================

const openActionDialog = () => {
  actionForm.value = { action_code: '', action_description: '' }
  isActionEdit.value = false
  showActionDialog.value = true
}

const editAction = (action: SkuAction) => {
  actionForm.value = { ...action }
  isActionEdit.value = true
  showActionDialog.value = true
}

const saveAction = async () => {
  if (!actionForm.value.action_code || !actionForm.value.action_description) return $q.notify({ type: 'warning', message: t('sku.fillAllFields') })
  isSavingAction.value = true
  try {
    const method = isActionEdit.value ? 'PUT' : 'POST'
    const url = isActionEdit.value ? `${appConfig.apiBaseUrl}/sku-actions/${actionForm.value.action_code}` : `${appConfig.apiBaseUrl}/sku-actions/`
    await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(actionForm.value) })
    $q.notify({ type: 'positive', message: t('sku.actionSaved') })
    await fetchActions()
    if (isActionEdit.value) showActionDialog.value = false
    else actionForm.value = { action_code: '', action_description: '' }
  } catch (e) { $q.notify({ type: 'negative', message: t('sku.saveFailed') }) }
  finally { isSavingAction.value = false }
}

const deleteAction = (action: SkuAction) => {
  $q.dialog({ title: t('common.confirm'), message: t('sku.deleteActionMsg', { code: action.action_code }), cancel: true }).onOk(async () => {
    try {
      await fetch(`${appConfig.apiBaseUrl}/sku-actions/${action.action_code}`, { method: 'DELETE' })
      $q.notify({ type: 'positive', message: t('sku.actionDeleted') })
      await fetchActions()
    } catch (e) { $q.notify({ type: 'negative', message: t('sku.deleteFailed') }) }
  })
}

// ============================================================================
// SKU GROUP MANAGEMENT
// ============================================================================

const filteredSkuGroups = computed(() => {
  if (!groupSearch.value) return skuGroups.value
  const q = groupSearch.value.toLowerCase()
  return skuGroups.value.filter(g => g.group_code.toLowerCase().includes(q) || g.group_name.toLowerCase().includes(q))
})

const openGroupDialog = () => {
  groupForm.value = { group_code: '', group_name: '', description: '' }
  isGroupEdit.value = false
  showGroupDialog.value = true
}

const editGroup = (group: any) => {
  groupForm.value = { group_code: group.group_code, group_name: group.group_name, description: group.description || '' }
  isGroupEdit.value = true
  showGroupDialog.value = true
}

const saveGroup = async () => {
  if (!groupForm.value.group_code || !groupForm.value.group_name) return $q.notify({ type: 'warning', message: 'Fill in code and name' })
  isSavingGroup.value = true
  try {
    const method = isGroupEdit.value ? 'PUT' : 'POST'
    const url = isGroupEdit.value ? `${appConfig.apiBaseUrl}/sku-groups/${groupForm.value.group_code}` : `${appConfig.apiBaseUrl}/sku-groups/`
    await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(groupForm.value) })
    $q.notify({ type: 'positive', message: 'Group saved' })
    await fetchSkuGroups()
    if (isGroupEdit.value) { isGroupEdit.value = false }
    groupForm.value = { group_code: '', group_name: '', description: '' }
  } catch (e) { $q.notify({ type: 'negative', message: 'Save failed' }) }
  finally { isSavingGroup.value = false }
}

const deleteGroup = (group: any) => {
  $q.dialog({ title: 'Confirm', message: `Delete group ${group.group_code} - ${group.group_name}?`, cancel: true }).onOk(async () => {
    try {
      await fetch(`${appConfig.apiBaseUrl}/sku-groups/${group.group_code}`, { method: 'DELETE' })
      $q.notify({ type: 'positive', message: 'Group deleted' })
      await fetchSkuGroups()
    } catch (e) { $q.notify({ type: 'negative', message: 'Delete failed' }) }
  })
}

// ============================================================================
// PHASE MANAGEMENT
// ============================================================================

const openPhaseDialog = () => {
  phaseForm.value = { phase_id: null, phase_code: '', phase_description: '' }
  editingPhase.value = null
  showPhaseDialog.value = true
}

const onPhaseIdChange = (id: number | null) => {
  if (id === null) return
  const existing = skuPhases.value.find(p => p.phase_id === id)
  if (existing) {
    phaseForm.value.phase_description = existing.phase_description
    phaseForm.value.phase_code = existing.phase_code || ''
    editingPhase.value = existing
  } else editingPhase.value = null
}

const editPhase = (phase: SkuPhase) => {
  phaseForm.value = { ...phase }
  editingPhase.value = phase
  showPhaseDialog.value = true
}

const savePhase = async () => {
  if (!phaseForm.value.phase_id || !phaseForm.value.phase_description) return $q.notify({ type: 'warning', message: t('sku.fillAllFields') })
  try {
    const method = editingPhase.value ? 'PUT' : 'POST'
    const url = editingPhase.value ? `${appConfig.apiBaseUrl}/sku-phases/${phaseForm.value.phase_id}` : `${appConfig.apiBaseUrl}/sku-phases/`
    await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(phaseForm.value) })
    $q.notify({ type: 'positive', message: t('sku.phaseSaved') })
    await fetchPhases()
    if (editingPhase.value) showPhaseDialog.value = false
    else phaseForm.value = { phase_id: null, phase_code: '', phase_description: '' }
  } catch (e) { $q.notify({ type: 'negative', message: t('sku.saveFailed') }) }
}

const deletePhase = (phase: SkuPhase) => {
  $q.dialog({ title: t('common.confirm'), message: t('sku.deletePhaseConfirm', { name: phase.phase_description }), cancel: true }).onOk(async () => {
    try {
      await fetch(`${appConfig.apiBaseUrl}/sku-phases/${phase.phase_id}`, { method: 'DELETE' })
      $q.notify({ type: 'positive', message: t('sku.phaseDeletedMsg') })
      await fetchPhases()
    } catch (e) { $q.notify({ type: 'negative', message: t('sku.deleteFailed') }) }
  })
}



// ============================================================================
// COMPUTED
// ============================================================================

const filteredSkus = computed(() => {
  let skus = skuMasters.value

  // Always filter out deleted SKUs
  skus = skus.filter(s => s.status !== 'Deleted')

  // Filter by status
  if (!showAllIncludingInactive.value) {
    skus = skus.filter(s => s.status === 'Active')
  }

  // Filter by search
  if (searchFilter.value) {
    const needle = searchFilter.value.toLowerCase()
    skus = skus.filter(sku =>
      sku.sku_id.toLowerCase().includes(needle) ||
      sku.sku_name.toLowerCase().includes(needle)
    )
  }
  // Column filters
  if (filterSkuId.value) {
    const f = filterSkuId.value.toLowerCase()
    skus = skus.filter(s => s.sku_id.toLowerCase().includes(f))
  }
  if (filterSkuName.value) {
    const f = filterSkuName.value.toLowerCase()
    skus = skus.filter(s => s.sku_name.toLowerCase().includes(f))
  }
  if (filterGroup.value) {
    const f = filterGroup.value.toLowerCase()
    skus = skus.filter(s => (s.sku_group_name || '').toLowerCase().includes(f))
  }

  return skus
})

// When collapsed, show only the selected row
const displayedSkus = computed(() => {
  if (skuTableExpanded.value) return filteredSkus.value
  if (selectedSkuId.value) {
    const selected = filteredSkus.value.find(s => s.sku_id === selectedSkuId.value)
    return selected ? [selected] : filteredSkus.value.slice(0, 1)
  }
  return filteredSkus.value.slice(0, 1)
})

const filteredSkuActions = computed(() => {
  if (!actionSearch.value) return skuActions.value
  const needle = actionSearch.value.toLowerCase()
  return skuActions.value.filter(a => 
    a.action_code.toLowerCase().includes(needle) || 
    a.action_description.toLowerCase().includes(needle)
  )
})

const filteredSkuPhases = computed(() => {
  if (!phaseSearch.value) return skuPhases.value
  const needle = phaseSearch.value.toLowerCase()
  return skuPhases.value.filter(p => 
    p.phase_id.toString().toLowerCase().includes(needle) || 
    (p.phase_code || '').toLowerCase().includes(needle) || 
    p.phase_description.toLowerCase().includes(needle)
  )
})

// ============================================================================
// FILTER & IMPORT/EXPORT UTILITIES
// ============================================================================

const resetFilters = () => {
  searchFilter.value = ''
  filterSkuId.value = ''
  filterSkuName.value = ''
  filterGroup.value = ''
  showAllIncludingInactive.value = false
  $q.notify({ type: 'info', message: t('sku.filtersReset') })
}

const importCSV = () => {
  fileInput.value?.click()
}

const onFileSelected = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  try {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await fetch(`${appConfig.apiBaseUrl}/skus/import`, {
      method: 'POST',
      body: formData
    })
    
    if (response.ok) {
      $q.notify({ type: 'positive', message: t('sku.importSuccess') })
      await fetchSkuMasters()
    } else {
      const error = await response.json()
      $q.notify({ type: 'negative', message: error.detail || t('sku.importFailed') })
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: t('sku.importFailed') })
  } finally {
    if (target) target.value = ''
  }
}

// ============================================================================
// API SERVICES & UTILITIES
// ============================================================================

const fetchSkuMasters = async () => {
  try {
    const res = await fetch(`${appConfig.apiBaseUrl}/api/v_sku_master_detail`)
    if (res.ok) skuMasters.value = await res.json()
  } catch (err) {
    $q.notify({ type: 'negative', message: t('sku.fetchFailed') })
  }
}

const fetchSkuSteps = async (skuId: string) => {
  if (skuStepsMap.value[skuId]) return
  try {
    const res = await fetch(`${appConfig.apiBaseUrl}/api/v_sku_step_detail?sku_id=${skuId}`)
    if (res.ok) skuStepsMap.value[skuId] = await res.json()
  } catch (err) {
    $q.notify({ type: 'negative', message: t('sku.fetchStepsFailed') })
  }
}

const fetchActions = async () => {
  try { const res = await fetch(`${appConfig.apiBaseUrl}/sku-actions/`); if (res.ok) skuActions.value = await res.json() } 
  catch (e) { console.error(e) }
}

const fetchDestinations = async () => {
  try { const res = await fetch(`${appConfig.apiBaseUrl}/sku-destinations/`); if (res.ok) skuDestinations.value = await res.json() } 
  catch (e) { console.error(e) }
}

const fetchPhases = async () => {
  try { const res = await fetch(`${appConfig.apiBaseUrl}/sku-phases/`); if (res.ok) skuPhases.value = await res.json() } 
  catch (e) { console.error(e) }
}

const fetchIngredients = async () => {
  try {
    const res = await fetch(`${appConfig.apiBaseUrl}/ingredients/`)
    if (res.ok) { const data = await res.json(); ingredients.value = data; updateIngredientOptions(data) }
  } catch (e) { console.error(e) }
}

const fetchSkuGroups = async () => {
  try {
    const res = await fetch(`${appConfig.apiBaseUrl}/sku-groups/`)
    if (res.ok) skuGroups.value = await res.json()
  } catch (e) { console.error(e) }
}

const updateIngredientOptions = (data: Ingredient[]) => {
  ingredientOptions.value = data.map(i => ({
    label: i.re_code || '?',
    value: i.re_code || '',
    original: i
  }))
}

const filterIngredients = (val: string, update: any) => {
  update(() => {
    let filtered = ingredients.value
    if (stepForm.value.action_code) {
      const action = skuActions.value.find(a => a.action_code === stepForm.value.action_code)
      if (action?.component_filter) {
        const filter = action.component_filter.trim()
        if (filter.includes('=')) {
          const [key, value] = filter.split('=').map(s => s.trim())
          if (key === 're_code' && value) {
            filtered = value.endsWith('*') ? filtered.filter(i => i.re_code?.startsWith(value.slice(0, -1))) : filtered.filter(i => i.re_code === value)
          } else if (key === 'Group' && value) filtered = filtered.filter(i => i.Group === value)
        } else if (filter.includes('^=')) {
          const [key, value] = filter.split('^=').map(s => s.trim())
          if (key === 're_code' && value) filtered = filtered.filter(i => i.re_code?.startsWith(value))
        } else filtered = filtered.filter(i => i.re_code === filter || i.name === filter || i.Group === filter)
      }
    }
    if (val !== '') {
      const needle = val.toLowerCase()
      filtered = filtered.filter(v => (v.name?.toLowerCase().includes(needle)) || (v.re_code?.toLowerCase().includes(needle)))
    }
    updateIngredientOptions(filtered)
  })
}

const exportToExcel = async () => {
  try {
    const ids = selectedSkus.value.map(s => s.sku_id).join(',')
    const url = `${appConfig.apiBaseUrl}/skus/export${ids ? `?sku_ids=${ids}` : ''}`
    const response = await fetch(url)
    if (response.ok) {
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = `sku_export_${new Date().toISOString().split('T')[0]}.xlsx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      $q.notify({ type: 'positive', message: t('sku.exportSuccess'), icon: 'download' })
    }
  } catch (err) { $q.notify({ type: 'negative', message: t('sku.exportFailed') }) }
}



// ============================================================================
// STEP MANAGEMENT
// ============================================================================

const openStepDialog = (step: SkuStep) => {
  editingStep.value = step; stepForm.value = { ...step }
  const flags: (keyof SkuStep)[] = ['qc_temp', 'record_steam_pressure', 'record_ctw', 'operation_brix_record', 'operation_ph_record']
  flags.forEach(f => (stepForm.value[f] as any) = !!step[f])
  showStepDialog.value = true
}

const addStep = (skuId: string) => {
  const steps = skuStepsMap.value[skuId] || []
  const maxPN = steps.length > 0 ? [...steps].sort((a,b) => b.phase_number.localeCompare(a.phase_number))[0]?.phase_number || 'p0000' : 'p0000'
  const nextVal = (parseInt(maxPN.substring(1)) || 0) + 10
  const pn = 'p' + nextVal.toString().padStart(4, '0')
  const phaseLink = skuPhases.value.find(p => (p.phase_id as any) === nextVal)?.phase_code || ''
  
  // Create a completely new object to avoid carrying over old sku_id
  stepForm.value = {
    sku_id: skuId,
    phase_number: pn,
    phase_id: phaseLink,
    sub_step: 10,
    action: '',
    re_code: '',
    action_code: '',
    action_description: '',
    destination: '',
    require: 0,
    uom: 'kg',
    low_tol: 0.001,
    high_tol: 0.001,
    step_condition: '',
    agitator_rpm: 0,
    high_shear_rpm: 0,
    temperature: 0,
    temp_low: 0,
    temp_high: 0,
    step_time: 0,
    brix_sp: '',
    ph_sp: '',
    qc_temp: false,
    record_steam_pressure: false,
    record_ctw: false,
    operation_brix_record: false,
    operation_ph_record: false,
    master_step: true,
    step_id: undefined
  }
  editingStep.value = null
  showStepDialog.value = true
}

const addStepToPhase = (skuId: string, phaseNumber: string) => {
  const steps = skuStepsMap.value[skuId] || []
  const stepsInPhase = steps.filter(s => s.phase_number === phaseNumber)
  const nextSub = stepsInPhase.length > 0 ? Math.max(...stepsInPhase.map(s => s.sub_step)) + 10 : 10
  
  // Create a completely new object to avoid carrying over old sku_id
  stepForm.value = {
    sku_id: skuId,
    phase_number: phaseNumber,
    phase_id: stepsInPhase[0]?.phase_id || '',
    sub_step: nextSub,
    action: '',
    re_code: '',
    action_code: '',
    action_description: '',
    destination: '',
    require: 0,
    uom: 'kg',
    low_tol: 0.001,
    high_tol: 0.001,
    step_condition: '',
    agitator_rpm: 0,
    high_shear_rpm: 0,
    temperature: 0,
    temp_low: 0,
    temp_high: 0,
    step_time: 0,
    brix_sp: '',
    ph_sp: '',
    qc_temp: false,
    record_steam_pressure: false,
    record_ctw: false,
    operation_brix_record: false,
    operation_ph_record: false,
    master_step: stepsInPhase.length === 0,
    step_id: undefined
  }
  editingStep.value = null
  showStepDialog.value = true
  if (!expandedPhases.value[skuId]) expandedPhases.value[skuId] = []
  if (!expandedPhases.value[skuId].includes(phaseNumber)) expandedPhases.value[skuId].push(phaseNumber)
}

const onActionChange = (code: string) => { stepForm.value.action_description = skuActions.value.find(a => a.action_code === code)?.action_description || '' }
const closeStepDialog = () => { showStepDialog.value = false; editingStep.value = null }

const saveStep = async () => {
  isSaving.value = true
  try {
    const isNew = !stepForm.value.step_id
    const url = isNew ? `${appConfig.apiBaseUrl}/sku-steps/` : `${appConfig.apiBaseUrl}/sku-steps/${stepForm.value.step_id}`
    await fetch(url, { method: isNew ? 'POST' : 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(stepForm.value) })
    $q.notify({ type: 'positive', message: `${t('sku.steps')} ${isNew ? t('sku.stepCreated') : t('sku.stepUpdated')}` })
    delete skuStepsMap.value[stepForm.value.sku_id]; await fetchSkuSteps(stepForm.value.sku_id)
    closeStepDialog()
  } catch (e: any) { $q.notify({ type: 'negative', message: t('sku.saveFailed') }) }
  finally { isSaving.value = false }
}

const copyStep = (step: SkuStep) => {
  const steps = skuStepsMap.value[step.sku_id] || []
  const maxSub = steps.filter(s => s.phase_number === step.phase_number).reduce((max, s) => Math.max(max, s.sub_step), 0)
  stepForm.value = { ...step, step_id: undefined, sub_step: maxSub + 10 }
  editingStep.value = null; showStepDialog.value = true
}

const deleteStep = (step: SkuStep) => {
  $q.dialog({ title: t('sku.confirmDelete'), message: t('sku.deleteStep', { id: `${step.phase_number}.${step.sub_step}` }), cancel: true }).onOk(async () => {
    try {
      await fetch(`${appConfig.apiBaseUrl}/sku-steps/${step.step_id}`, { method: 'DELETE' })
      $q.notify({ type: 'positive', message: t('sku.stepDeleted') })
      delete skuStepsMap.value[step.sku_id]; await fetchSkuSteps(step.sku_id)
    } catch (e) { $q.notify({ type: 'negative', message: t('sku.deleteFailed') }) }
  })
}

const deletePhaseSteps = (skuId: string, phaseNumber: string) => {
  const steps = skuStepsMap.value[skuId] || []
  const stepsInPhase = steps.filter(s => s.phase_number === phaseNumber)
  
  if (stepsInPhase.length === 0) {
    $q.notify({ type: 'warning', message: t('sku.noStepsInPhase') })
    return
  }
  
  $q.dialog({
    title: t('sku.confirmDeletePhase'),
    message: t('sku.deletePhaseMsg', { count: String(stepsInPhase.length), phase: phaseNumber }),
    cancel: true,
    persistent: true
  }).onOk(async () => {
    try {
      // Delete all steps in the phase
      for (const step of stepsInPhase) {
        await fetch(`${appConfig.apiBaseUrl}/sku-steps/${step.step_id}`, { method: 'DELETE' })
      }
      $q.notify({ type: 'positive', message: t('sku.phaseDeleted', { phase: phaseNumber, count: String(stepsInPhase.length) }) })
      delete skuStepsMap.value[skuId]
      await fetchSkuSteps(skuId)
    } catch (e) {
      $q.notify({ type: 'negative', message: t('sku.deleteFailed') })
    }
  })
}

const onIngredientChange = (reCode: string) => { /* Placeholder for future logic */ }

// ============================================================================
// NAVIGATION & VIEW UTILITIES
// ============================================================================

const selectSku = async (sku: SkuMaster) => {
  if (selectedSkuId.value === sku.sku_id) {
    selectedSkuId.value = null
    selectedSkuData.value = null
  } else {
    selectedSkuId.value = sku.sku_id
    selectedSkuData.value = sku
    await fetchSkuSteps(sku.sku_id)
  }
}

const isSkuSelected = (skuId: string) => selectedSkuId.value === skuId

const togglePhase = (skuId: string, phaseNumber: string) => {
  if (!expandedPhases.value[skuId]) expandedPhases.value[skuId] = []
  const index = expandedPhases.value[skuId].indexOf(phaseNumber)
  if (index > -1) expandedPhases.value[skuId].splice(index, 1)
  else expandedPhases.value[skuId].push(phaseNumber)
}

const isPhaseExpanded = (skuId: string, phaseNumber: string) => expandedPhases.value[skuId]?.includes(phaseNumber) ?? false

const expandAllPhases = () => {
  if (!selectedSkuId.value) return
  const allPhaseNums = groupedSteps.value.map(g => g.phaseNum)
  expandedPhases.value[selectedSkuId.value] = [...allPhaseNums]
}

const collapseAllPhases = () => {
  if (!selectedSkuId.value) return
  expandedPhases.value[selectedSkuId.value] = []
}

const getPhaseDescription = (phaseId: string | null) => {
  if (!phaseId) return ''
  return skuPhases.value.find(p => p.phase_code === phaseId)?.phase_description || ''
}

// = ===========================================================================
// SKU MANAGEMENT
// ============================================================================

const createNewSku = () => {
  skuForm.value = { sku_id: '', sku_name: '', std_batch_size: 0, uom: 'kg', sku_group: null as number | null, status: 'Active' }
  isEditMode.value = false; editingSkuId.value = undefined; showSkuDialog.value = true
}

const editSku = (skuId: string) => {
  const sku = skuMasters.value.find(s => s.sku_id === skuId)
  if (!sku) return $q.notify({ type: 'negative', message: t('sku.skuNotFound') })
  skuForm.value = { sku_id: sku.sku_id, sku_name: sku.sku_name, std_batch_size: sku.std_batch_size || 0, uom: sku.uom || 'kg', sku_group: sku.sku_group || null, status: sku.status || 'Active' }
  isEditMode.value = true; editingSkuId.value = sku.id; showSkuDialog.value = true
}

const saveNewSku = async () => {
  if (!skuForm.value.sku_id || !skuForm.value.sku_name) return $q.notify({ type: 'warning', message: t('sku.fillMandatory') })
  isCreatingSku.value = true
  try {
    const isEdit = isEditMode.value && editingSkuId.value
    const url = isEdit ? `${appConfig.apiBaseUrl}/skus/${editingSkuId.value}` : `${appConfig.apiBaseUrl}/skus/`
    const method = isEdit ? 'PUT' : 'POST'
    await fetch(url, { 
      method, 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ 
        sku_id: skuForm.value.sku_id, 
        sku_name: skuForm.value.sku_name, 
        std_batch_size: skuForm.value.std_batch_size,
        uom: skuForm.value.uom,
        sku_group: skuForm.value.sku_group || null,
        status: skuForm.value.status 
      }) 
    })
    $q.notify({ type: 'positive', message: isEdit ? t('sku.skuUpdated') : t('sku.skuCreated') })
    showSkuDialog.value = false
    await fetchSkuMasters()
  } catch (e) { $q.notify({ type: 'negative', message: t('sku.saveFailed') }) }
  finally { isCreatingSku.value = false }
}

const deleteSku = (sku: SkuMaster) => {
  $q.dialog({ title: t('sku.confirmDelete'), message: t('sku.markDeleted', { id: sku.sku_id }), cancel: true }).onOk(async () => {
    try {
      await fetch(`${appConfig.apiBaseUrl}/skus/${sku.id}`, { method: 'DELETE' })
      $q.notify({ type: 'positive', message: t('sku.skuDeleted') })
      await fetchSkuMasters()
    } catch (e) { $q.notify({ type: 'negative', message: t('sku.deleteFailed') }) }
  })
}

const copySku = (sku: SkuMaster) => {
  duplicateForm.value = {
    source_sku_id: sku.sku_id,
    new_sku_id: `${sku.sku_id}-COPY`,
    new_sku_name: `${sku.sku_name} (Copy)`
  }
  showDuplicateDialog.value = true
}

const saveDuplicateSku = async () => {
  if (!duplicateForm.value.new_sku_id || !duplicateForm.value.new_sku_name) {
    return $q.notify({ type: 'warning', message: t('sku.fillMandatory') })
  }
  
  isDuplicating.value = true
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/skus/duplicate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(duplicateForm.value)
    })
    
    if (response.ok) {
      $q.notify({ type: 'positive', message: t('sku.duplicateSuccess') })
      showDuplicateDialog.value = false
      await fetchSkuMasters()
    } else {
      const error = await response.json()
      $q.notify({ type: 'negative', message: error.detail || t('sku.saveFailed') })
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: t('sku.networkError') })
  } finally {
    isDuplicating.value = false
  }
}

// ============================================================================
// TABLE CONFIGURATION & LIFECYCLE
// ============================================================================

const masterColumns = computed<QTableColumn[]>(() => [
  { name: 'sku_id', label: t('sku.skuId'), field: 'sku_id', align: 'left' as const, sortable: true },
  { name: 'sku_name', label: t('sku.skuName'), field: 'sku_name', align: 'left' as const, sortable: true },
  { name: 'sku_group', label: t('sku.skuGroup', 'Group'), field: 'sku_group_name', align: 'left' as const, sortable: true },
  { name: 'std_batch', label: t('sku.stdBatch'), field: 'std_batch_size', align: 'right' as const, sortable: true },
  { name: 'phases', label: t('sku.phases'), field: 'total_phases', align: 'center' as const, sortable: true },
  { name: 'steps', label: t('sku.steps'), field: 'total_sub_steps', align: 'center' as const, sortable: true },
  { name: 'actions', label: t('common.actions'), field: 'actions', align: 'center' as const, style: 'width: 220px' }
])

const stepColumns = computed<QTableColumn[]>(() => [
  { name: 'actions', label: t('common.actions'), field: 'actions', align: 'center', style: 'width: 90px' },
  { name: 'sub_step', label: t('sku.subStep'), field: 'sub_step', align: 'center', sortable: true, style: 'width: 55px' },
  { name: 'action_code', label: t('sku.actionCode'), field: 'action_code', align: 'center', sortable: true, style: 'width: 70px' },
  { name: 'action_description', label: t('common.description'), field: 'action_description', align: 'left', sortable: true, style: 'width: 160px' },
  { name: 'ingredient_name', label: t('sku.ingredientComponent'), field: 'ingredient_name', align: 'left', sortable: true, style: 'width: auto' },
  { name: 'require', label: t('sku.volumeAmount'), field: 'require', align: 'right', style: 'width: 65px' },
  { name: 'uom', label: t('sku.uom'), field: 'uom', align: 'center', style: 'width: 55px' },
  { name: 'temperature', label: t('sku.prepareTemp'), field: 'temperature', align: 'right', style: 'width: 60px' },
  { name: 'agitator_rpm', label: t('sku.agitatorRpm'), field: 'agitator_rpm', align: 'right', style: 'width: 70px' },
  { name: 'step_time', label: t('sku.timeMinutes'), field: (row: any) => row.step_time ? (row.step_time / 60).toFixed(1) : '', align: 'right', style: 'width: 55px' },
  { name: 'qc_flags', label: t('sku.qcRecords'), field: 'qc_temp', align: 'center', style: 'width: 70px' }
])

const refreshAll = async () => {
  isLoading.value = true
  try {
    await Promise.all([
      fetchSkuMasters(),
      fetchActions(),
      fetchDestinations(),
      fetchPhases(),
      fetchIngredients(),
      fetchSkuGroups()
    ])
  } finally {
    isLoading.value = false
  }
}

onMounted(refreshAll)

// ============================================================================
// SKU PRINT / PDF REPORT
// ============================================================================
const printSkuReport = async (sku: SkuMaster) => {
  // Ensure steps are loaded
  if (!skuStepsMap.value[sku.sku_id]) {
    await fetchSkuSteps(sku.sku_id)
  }
  const steps = skuStepsMap.value[sku.sku_id] || []

  // Group steps by phase
  const phaseMap: { [key: string]: SkuStep[] } = {}
  steps.forEach(s => {
    if (!phaseMap[s.phase_number]) phaseMap[s.phase_number] = []
    phaseMap[s.phase_number].push(s)
  })
  const phases = Object.keys(phaseMap).sort()

  // Build required ingredients summary
  const ingredientMap: { [key: string]: { name: string, re_code: string, total: number, uom: string, phases: string[] } } = {}
  steps.forEach(s => {
    if (s.ingredient_name && s.require && s.require > 0) {
      const key = s.re_code || s.ingredient_name || ''
      if (!ingredientMap[key]) {
        ingredientMap[key] = { name: s.ingredient_name || '', re_code: s.re_code || '', total: 0, uom: s.uom || s.ingredient_unit || 'kg', phases: [] }
      }
      ingredientMap[key].total += s.require
      if (!ingredientMap[key].phases.includes(s.phase_number)) {
        ingredientMap[key].phases.push(s.phase_number)
      }
    }
  })
  const ingredientList = Object.values(ingredientMap).sort((a, b) => a.name.localeCompare(b.name))

  const qcFlags = (step: SkuStep) => {
    const flags: string[] = []
    if (step.qc_temp) flags.push('🌡️ Temp')
    if (step.record_steam_pressure) flags.push('💨 Steam')
    if (step.record_ctw) flags.push('💧 CTW')
    if (step.operation_brix_record) flags.push('📊 Brix')
    if (step.operation_ph_record) flags.push('🧪 pH')
    return flags.join(', ') || '-'
  }

  const now = new Date().toLocaleString()

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>SKU Report - ${sku.sku_id}</title>
  <style>
    @page { size: A4; margin: 12mm 15mm; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Courier Prime', 'Courier New', Courier, monospace; font-size: 11px; color: #222; line-height: 1.4; }

    /* Repeating header/footer via table trick */
    .page-wrapper { display: table; width: 100%; }
    .page-header { display: table-header-group; }
    .page-footer { display: table-footer-group; }
    .page-body { display: table-row-group; }

    .report-header { background: #0384fc; color: white; padding: 10px 16px; display: flex; justify-content: space-between; align-items: center; border-radius: 4px; margin-bottom: 4px; }
    .report-header h1 { font-size: 16px; margin: 0; }
    .report-header .meta { font-size: 9px; text-align: right; opacity: 0.9; }
    .report-footer { border-top: 2px solid #0384fc; font-size: 8px; color: #888; padding: 6px 0; display: flex; justify-content: space-between; margin-top: 4px; }

    .info-grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 6px; margin-bottom: 12px; }
    .info-box { background: #f5f7fa; border: 1px solid #dde; border-radius: 3px; padding: 6px 10px; }
    .info-box .label { font-size: 8px; color: #666; text-transform: uppercase; font-weight: bold; }
    .info-box .value { font-size: 12px; font-weight: bold; color: #1a237e; margin-top: 1px; }

    .section-title { font-size: 13px; font-weight: bold; color: #1a237e; margin: 12px 0 6px 0; border-bottom: 2px solid #1a237e; padding-bottom: 3px; }
    .phase-header { background: #e8eaf6; padding: 6px 12px; font-weight: bold; font-size: 11px; color: #283593; border-left: 4px solid #3f51b5; margin-top: 10px; margin-bottom: 2px; border-radius: 2px; page-break-after: avoid; }

    table.data-table { width: 100%; border-collapse: collapse; margin-bottom: 4px; font-size: 10px; }
    table.data-table th { background: #37474f; color: white; padding: 4px 5px; text-align: left; font-weight: bold; font-size: 8px; text-transform: uppercase; }
    table.data-table td { padding: 3px 5px; border-bottom: 1px solid #e0e0e0; }
    table.data-table tr:nth-child(even) td { background: #fafafa; }

    table.ingredient-table { width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 10px; }
    table.ingredient-table th { background: #1b5e20; color: white; padding: 4px 6px; text-align: left; font-weight: bold; font-size: 8px; text-transform: uppercase; }
    table.ingredient-table td { padding: 3px 6px; border-bottom: 1px solid #c8e6c9; }
    table.ingredient-table tr:nth-child(even) td { background: #f1f8e9; }
    table.ingredient-table tr.total-row td { background: #e8f5e9; font-weight: bold; border-top: 2px solid #2e7d32; }

    .text-right { text-align: right; }
    .text-center { text-align: center; }
    .badge { display: inline-block; background: #e3f2fd; color: #1565c0; padding: 1px 5px; border-radius: 3px; font-size: 8px; font-weight: bold; }
    .badge-green { background: #e8f5e9; color: #2e7d32; }
    .page-break { page-break-before: always; }
    @media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
  </style>
</head>
<body>
  <div class="page-wrapper">
    <!-- Repeating Page Header -->
    <div class="page-header">
      <div>
        <div class="report-header">
          <div>
            <h1>📋 SKU Report: ${sku.sku_id}</h1>
            <div style="margin-top:2px; font-size:12px;">${sku.sku_name}</div>
          </div>
          <div class="meta">
            <div>Generated: ${now}</div>
            <div>xMixing 2025 | xDev.co.th</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Repeating Page Footer -->
    <div class="page-footer">
      <div>
        <div class="report-footer">
          <span>xDev.co.th - xMixing Control System 2025</span>
          <span>SKU: ${sku.sku_id} | ${sku.sku_name} | Std Batch: ${sku.std_batch_size || '-'} ${sku.uom || ''}</span>
        </div>
      </div>
    </div>

    <!-- Page Body -->
    <div class="page-body">
      <div>
        <!-- SKU Info -->
        <div class="info-grid">
          <div class="info-box"><div class="label">SKU ID</div><div class="value">${sku.sku_id}</div></div>
          <div class="info-box"><div class="label">SKU Name</div><div class="value">${sku.sku_name}</div></div>
          <div class="info-box"><div class="label">Std Batch Size</div><div class="value">${sku.std_batch_size || '-'} ${sku.uom || ''}</div></div>
          <div class="info-box"><div class="label">Status</div><div class="value">${sku.status}</div></div>
          <div class="info-box"><div class="label">Total Phases</div><div class="value">${sku.total_phases || 0}</div></div>
          <div class="info-box"><div class="label">Total Steps</div><div class="value">${sku.total_sub_steps || 0}</div></div>
          <div class="info-box"><div class="label">Created</div><div class="value">${sku.created_at ? new Date(sku.created_at).toLocaleDateString() : '-'}</div></div>
          <div class="info-box"><div class="label">Updated</div><div class="value">${sku.updated_at ? new Date(sku.updated_at).toLocaleDateString() : '-'}</div></div>
        </div>

        <!-- Required Ingredients Summary -->
        <div class="section-title">🧪 Required Ingredients (${ingredientList.length} items)</div>
        <table class="ingredient-table">
          <thead>
            <tr>
              <th style="width:30px;">#</th>
              <th style="width:90px;">RE Code</th>
              <th>Ingredient Name</th>
              <th class="text-right" style="width:80px;">Total Amount</th>
              <th class="text-center" style="width:50px;">UOM</th>
              <th style="width:120px;">Used in Phases</th>
            </tr>
          </thead>
          <tbody>
            ${ingredientList.map((ing, idx) => `
              <tr>
                <td class="text-center">${idx + 1}</td>
                <td><span class="badge badge-green">${ing.re_code || '-'}</span></td>
                <td>${ing.name}</td>
                <td class="text-right"><strong>${ing.total.toFixed(3)}</strong></td>
                <td class="text-center">${ing.uom}</td>
                <td>${ing.phases.join(', ')}</td>
              </tr>
            `).join('')}
            <tr class="total-row">
              <td colspan="3" class="text-right">Total Ingredients: ${ingredientList.length}</td>
              <td class="text-right">${ingredientList.reduce((sum, i) => sum + i.total, 0).toFixed(3)}</td>
              <td class="text-center">-</td>
              <td>-</td>
            </tr>
          </tbody>
        </table>

        <!-- Process Steps Detail -->
        <div class="section-title page-break">⚙️ Process Steps Detail</div>

        ${phases.map(phaseNum => {
          const phaseSteps = phaseMap[phaseNum]
          const firstStep = phaseSteps[0]
          const phaseDesc = firstStep?.action || ''
          const phaseId = firstStep?.phase_id || ''
          return `
            <div class="phase-header">
              ${phaseNum} ${phaseDesc ? '- ' + phaseDesc : ''}
              ${phaseId ? '<span class="badge">' + phaseId + '</span>' : ''}
              (${phaseSteps.length} steps)
            </div>
            <table class="data-table">
              <thead>
                <tr>
                  <th style="width:35px;">Sub</th>
                  <th style="width:50px;">Code</th>
                  <th>Description</th>
                  <th>Ingredient / Component</th>
                  <th class="text-right" style="width:55px;">Amount</th>
                  <th class="text-center" style="width:30px;">UOM</th>
                  <th class="text-right" style="width:40px;">Temp°C</th>
                  <th class="text-right" style="width:40px;">RPM</th>
                  <th class="text-right" style="width:45px;">Time(m)</th>
                  <th style="width:80px;">QC Records</th>
                </tr>
              </thead>
              <tbody>
                ${phaseSteps.map(s => `
                  <tr>
                    <td class="text-center">${s.sub_step}</td>
                    <td><span class="badge">${s.action_code || '-'}</span></td>
                    <td>${s.action_description || '-'}</td>
                    <td>${s.ingredient_name || '-'}</td>
                    <td class="text-right">${s.require || '-'}</td>
                    <td class="text-center">${s.uom || s.ingredient_unit || '-'}</td>
                    <td class="text-right">${s.temperature || '-'}</td>
                    <td class="text-right">${s.agitator_rpm || '-'}</td>
                    <td class="text-right">${s.step_time ? (s.step_time / 60).toFixed(1) : '-'}</td>
                    <td>${qcFlags(s)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          `
        }).join('')}

      </div>
    </div>
  </div>
</body>
</html>`

  const printWindow = window.open('', '_blank')
  if (printWindow) {
    printWindow.document.write(html)
    printWindow.document.close()
    printWindow.onload = () => { printWindow.print() }
  }
}
</script>

<template>
  <q-page class="q-pa-md bg-white">
    <!-- Page Header -->
    <div class="bg-blue-9 text-white q-pa-md rounded-borders q-mb-md shadow-2">
      <div class="row justify-between items-center">
        <div class="row items-center q-gutter-sm">
          <q-icon name="inventory_2" size="sm" />
          <div class="text-h6 text-weight-bolder">{{ t('sku.title') }}</div>
        </div>
        <div class="text-caption text-blue-2">{{ t('sku.subtitle') }}</div>
      </div>
    </div>
    <!-- Header with Action Bar -->
    <div class="row q-mb-md items-center">
      <q-space />
      
      <!-- Action Buttons -->
      <div class="row q-gutter-sm items-center">
        <q-btn 
          color="positive" 
          icon="add" 
          @click="createNewSku" 
          round
          flat
        >
          <q-tooltip>{{ t('sku.newSku') }}</q-tooltip>
        </q-btn>
        <q-btn 
          color="primary" 
          icon="refresh" 
          @click="refreshAll" 
          round
          flat
        >
          <q-tooltip>{{ t('common.refresh') }}</q-tooltip>
        </q-btn>
        <q-btn 
          color="primary" 
          icon="filter_alt_off" 
          @click="resetFilters" 
          round
          flat
        >
          <q-tooltip>{{ t('sku.resetFilters') }}</q-tooltip>
        </q-btn>
        <q-btn 
          color="accent" 
          icon="filter_alt" 
          @click="showFilters = !showFilters" 
          round
          flat
        >
          <q-tooltip>{{ showFilters ? t('sku.hideFilters') : t('sku.showFilters') }}</q-tooltip>
        </q-btn>
        <q-btn 
          color="secondary" 
          icon="file_download" 
          @click="exportToExcel" 
          round
          flat
        >
          <q-tooltip>{{ t('sku.exportExcel') }}</q-tooltip>
        </q-btn>
        <q-btn 
          color="accent" 
          icon="file_upload" 
          @click="importCSV" 
          round
          flat
        >
          <q-tooltip>{{ t('sku.importCsv') }}</q-tooltip>
        </q-btn>
        <!-- Hidden File Input -->
        <input
          type="file"
          ref="fileInput"
          accept=".csv"
          style="display: none"
          @change="onFileSelected"
        />
        <q-btn 
          color="accent" 
          icon="settings" 
          @click="openActionDialog" 
          round
          flat
        >
          <q-tooltip>{{ t('sku.manageActions') }}</q-tooltip>
        </q-btn>
        <q-checkbox 
          v-model="showAllIncludingInactive" 
          :label="t('sku.showAllInactive')" 
          dense
        />
        <q-input 
          v-model="searchFilter" 
          :placeholder="t('sku.searchSku')" 
          dense 
          outlined
          style="min-width: 300px"
          clearable
        >
          <template v-slot:prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </div>
    </div>

    <!-- Master Table Toggle -->
    <div class="row items-center q-mb-xs">
      <q-btn
        flat
        dense
        :icon="skuTableExpanded ? 'expand_less' : 'expand_more'"
        :label="skuTableExpanded ? t('sku.collapseTable', 'Collapse Table') : t('sku.expandTable', 'Expand Table')"
        color="primary"
        size="sm"
        @click="skuTableExpanded = !skuTableExpanded"
      />
    </div>
    <q-table
      :rows="displayedSkus"
      :columns="masterColumns"
      row-key="sku_id"
      :rows-per-page-options="skuTableExpanded ? [10, 25, 50, 100] : [0]"
      :pagination="skuTableExpanded ? { rowsPerPage: 25 } : { rowsPerPage: 0 }"
      flat
      bordered
      :loading="isLoading"
      class="master-table q-mb-lg"
      :style="skuTableExpanded ? 'max-height: 50vh; overflow: auto;' : ''"
      :hide-bottom="!skuTableExpanded"
    >
      <!-- Custom Row Template for Selection -->
      <template v-slot:header="props">
        <q-tr :props="props">
          <q-th v-for="col in props.cols" :key="col.name" :props="props">
            {{ col.label }}
          </q-th>
        </q-tr>
        <q-tr v-if="showFilters" class="bg-grey-1">
          <q-th v-for="col in props.cols" :key="'f-' + col.name" style="padding: 2px 4px">
            <q-input
              v-if="col.name === 'sku_id'"
              v-model="filterSkuId"
              dense
              outlined
              placeholder="Filter..."
              clearable
              size="sm"
              class="filter-input"
            />
            <q-input
              v-else-if="col.name === 'sku_name'"
              v-model="filterSkuName"
              dense
              outlined
              placeholder="Filter..."
              clearable
              size="sm"
              class="filter-input"
            />
            <q-input
              v-else-if="col.name === 'sku_group'"
              v-model="filterGroup"
              dense
              outlined
              placeholder="Filter..."
              clearable
              size="sm"
              class="filter-input"
            />
          </q-th>
        </q-tr>
      </template>
      <template v-slot:body="props">
        <q-tr 
          :props="props" 
          class="cursor-pointer"
          :class="isSkuSelected(props.row.sku_id) ? 'bg-blue-1 text-primary text-bold' : ''"
          @click="selectSku(props.row)"
        >
          <q-td v-for="col in props.cols" :key="col.name" :props="props">
            <template v-if="col.name === 'std_batch'">
              <span v-if="props.row.std_batch_size">
                {{ props.row.std_batch_size }} {{ props.row.uom || '' }}
              </span>
              <span v-else class="text-grey-5">-</span>
            </template>
            <template v-else-if="col.name === 'phases'">
              <q-badge color="indigo-6" :label="props.row.total_phases || 0" />
            </template>
            <template v-else-if="col.name === 'steps'">
              <q-badge color="blue-grey-6" :label="props.row.total_sub_steps || 0" />
            </template>
            <template v-else-if="col.name === 'actions'">
              <div class="row items-center justify-center no-wrap q-gutter-xs">
                <q-btn 
                  size="sm" 
                  color="teal" 
                  flat 
                  round
                  icon="info" 
                  @click.stop
                >
                  <q-tooltip>SKU Detail</q-tooltip>
                  <q-popup-proxy>
                    <q-card style="min-width: 280px;">
                      <q-card-section class="bg-primary text-white q-py-sm">
                        <div class="text-subtitle2">{{ props.row.sku_id }}</div>
                        <div class="text-caption">{{ props.row.sku_name }}</div>
                      </q-card-section>
                      <q-card-section class="q-pa-sm">
                        <div class="q-gutter-xs">
                          <div><strong>Batch Size:</strong> {{ props.row.std_batch_size || '-' }} {{ props.row.uom || '' }}</div>
                          <div><strong>Status:</strong> <q-badge :color="props.row.status === 'Active' ? 'positive' : 'grey'" :label="props.row.status" /></div>
                          <div><strong>Phases:</strong> {{ props.row.total_phases || 0 }}</div>
                          <div><strong>Steps:</strong> {{ props.row.total_sub_steps || 0 }}</div>
                          <div><strong>Created:</strong> {{ props.row.created_at ? new Date(props.row.created_at).toLocaleString() : '-' }}</div>
                          <div><strong>Created by:</strong> {{ props.row.creat_by || '-' }}</div>
                          <div><strong>Updated:</strong> {{ props.row.updated_at ? new Date(props.row.updated_at).toLocaleString() : '-' }}</div>
                          <div><strong>Updated by:</strong> {{ props.row.update_by || '-' }}</div>
                        </div>
                      </q-card-section>
                    </q-card>
                  </q-popup-proxy>
                </q-btn>
                <q-btn 
                  size="sm" 
                  color="amber-8" 
                  flat 
                  round
                  icon="history" 
                  @click.stop
                >
                  <q-tooltip>History</q-tooltip>
                  <q-popup-proxy>
                    <q-card style="min-width: 250px;">
                      <q-card-section class="bg-amber-8 text-white q-py-sm">
                        <div class="text-subtitle2">History: {{ props.row.sku_id }}</div>
                      </q-card-section>
                      <q-card-section class="q-pa-sm">
                        <q-timeline color="primary" dense>
                          <q-timeline-entry
                            v-if="props.row.created_at"
                            :subtitle="new Date(props.row.created_at).toLocaleString()"
                            icon="add_circle"
                            color="positive"
                          >
                            <div class="text-caption">Created by {{ props.row.creat_by || 'system' }}</div>
                          </q-timeline-entry>
                          <q-timeline-entry
                            v-if="props.row.updated_at && props.row.updated_at !== props.row.created_at"
                            :subtitle="new Date(props.row.updated_at).toLocaleString()"
                            icon="edit"
                            color="info"
                          >
                            <div class="text-caption">Updated by {{ props.row.update_by || 'system' }}</div>
                          </q-timeline-entry>
                        </q-timeline>
                      </q-card-section>
                    </q-card>
                  </q-popup-proxy>
                </q-btn>
                <q-btn 
                  size="sm" 
                  color="deep-purple" 
                  flat 
                  round
                  icon="print" 
                  @click.stop="printSkuReport(props.row)"
                >
                  <q-tooltip>Print SKU Report</q-tooltip>
                </q-btn>
                <q-btn 
                  size="sm" 
                  color="info" 
                  flat 
                  round
                  icon="content_copy" 
                  @click.stop="copySku(props.row)"
                >
                  <q-tooltip>{{ t('sku.duplicateSku') }}</q-tooltip>
                </q-btn>
                <q-btn 
                  size="sm" 
                  color="primary" 
                  flat 
                  round
                  icon="edit" 
                  @click.stop="editSku(props.row.sku_id)"
                >
                  <q-tooltip>{{ t('sku.editSKU') }}</q-tooltip>
                </q-btn>
                <q-btn 
                  size="sm" 
                  color="negative" 
                  flat 
                  round
                  icon="delete" 
                  @click.stop="deleteSku(props.row)"
                >
                  <q-tooltip>{{ t('sku.deleteSku') }}</q-tooltip>
                </q-btn>
              </div>
            </template>
            <template v-else>
              {{ col.value }}
            </template>
          </q-td>
        </q-tr>
      </template>


      <!-- Expanded Row (Child Steps) -->

      <!-- No Data -->
      <template v-slot:no-data>
        <div class="full-width row flex-center text-grey-6 q-gutter-sm q-pa-lg">
          <q-icon size="2em" name="inventory_2" />
          <span>{{ t('sku.noSkuFound') }}</span>
        </div>
      </template>
    </q-table>

    <!-- Ingredient Requirement Table -->
    <q-card v-if="selectedSkuId && ingredientSummary.length > 0" flat bordered class="q-mt-md q-mb-md">
      <q-card-section class="q-pa-sm">
        <div class="row items-center q-mb-sm">
          <q-icon name="science" color="green-7" size="sm" class="q-mr-xs" />
          <span class="text-subtitle2 text-green-8 text-bold">Required Ingredients</span>
          <q-badge color="green-7" class="q-ml-sm">{{ ingredientSummary.length }}</q-badge>
          <q-space />
          <span class="text-caption text-grey-6">{{ selectedSkuId }}</span>
        </div>
        <q-markup-table dense flat bordered separator="cell" class="text-caption">
          <thead>
            <tr class="bg-green-1">
              <th class="text-left">RE Code</th>
              <th class="text-left">Ingredient</th>
              <th class="text-right">Qty Required</th>
              <th class="text-center">UOM</th>
              <th class="text-center">Phases</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ing in ingredientSummary" :key="ing.re_code || ing.name">
              <td class="text-bold text-green-9">{{ ing.re_code || '?' }}</td>
              <td>{{ ing.name }}</td>
              <td class="text-right text-bold">{{ ing.total.toFixed(2) }}</td>
              <td class="text-center">{{ ing.uom }}</td>
              <td class="text-center">{{ ing.phases.join(', ') }}</td>
            </tr>
          </tbody>
        </q-markup-table>
      </q-card-section>
    </q-card>

    <!-- Detail View (Always Visible) -->
      <div class="detail-container q-pa-md bg-white rounded-borders shadow-1 bordered">
      <template v-if="selectedSkuId">
        <div class="row items-center q-mb-md">
          <div class="text-h6 text-primary row items-center">
            <q-icon name="format_list_numbered" size="md" class="q-mr-sm" />
            {{ t('sku.processSteps') }} {{ selectedSkuId }} 
            <span class="text-subtitle1 text-grey-7 q-ml-md" v-if="selectedSkuData">
              - {{ selectedSkuData?.sku_name }}
            </span>
          </div>
          
          <q-space />
          
          <div class="row items-center q-gutter-sm">
            <q-btn 
              flat 
              round 
              dense 
              icon="settings" 
              color="primary" 
              @click="openPhaseDialog"
            >
              <q-tooltip>{{ t('sku.phaseManagement') }}</q-tooltip>
            </q-btn>
            
            <q-btn 
              flat 
              round 
              dense 
              icon="refresh" 
              color="grey-7" 
              @click="fetchSkuSteps(selectedSkuId)"
            >
              <q-tooltip>{{ t('sku.refreshSteps') }}</q-tooltip>
            </q-btn>
            
            <q-btn 
              flat 
              round 
              dense 
              icon="add_circle" 
              color="primary" 
              @click="addStep(selectedSkuId)"
            >
              <q-tooltip>{{ t('sku.addNewPhase') }}</q-tooltip>
            </q-btn>

            <q-separator vertical inset class="q-mx-xs" />

            <q-btn 
              flat 
              round 
              dense 
              icon="unfold_more" 
              color="teal" 
              @click="expandAllPhases"
            >
              <q-tooltip>{{ t('sku.expandAll') }}</q-tooltip>
            </q-btn>
            <q-btn 
              flat 
              round 
              dense 
              icon="unfold_less" 
              color="teal" 
              @click="collapseAllPhases"
            >
              <q-tooltip>{{ t('sku.collapseAll') }}</q-tooltip>
            </q-btn>
          </div>
        </div>

        <!-- Grouping Logic -->
        <template v-if="selectedSkuId && groupedSteps.length > 0">
          <div v-for="group in groupedSteps" :key="group.phaseNum" class="q-mb-md">
            <!-- Master Step Header (Clickable) -->
            <div 
              class="bg-blue-grey-1 q-px-md q-py-sm rounded-borders text-bold text-blue-grey-9 row items-center"
              style="user-select: none;"
            >
              <div class="row items-center cursor-pointer" style="flex: 1;" @click="togglePhase(selectedSkuId!, group.phaseNum)">
                <q-icon 
                  :name="isPhaseExpanded(selectedSkuId!, group.phaseNum) ? 'expand_more' : 'chevron_right'" 
                  size="sm" 
                  class="q-mr-xs" 
                />
                <q-icon name="timeline" size="xs" class="q-mr-sm" />
                <span class="text-uppercase q-mr-sm">{{ group.phaseNum }}</span>
                <span v-if="getPhaseDescription(group.firstStep?.phase_id || null)" class="text-weight-regular text-grey-8">
                  - {{ getPhaseDescription(group.firstStep?.phase_id || null) }}
                </span>
                <q-badge v-if="group.firstStep?.phase_id" color="grey-8" class="q-ml-sm" outline>
                  {{ group.firstStep.phase_id }}
                </q-badge>
              </div>
              
              <!-- Action Buttons -->
              <div class="row q-gutter-xs">
                <q-btn 
                  flat
                  round
                  dense
                  icon="add" 
                  size="sm" 
                  color="primary" 
                  @click.stop="addStepToPhase(selectedSkuId!, group.phaseNum)"
                >
                  <q-tooltip>{{ t('sku.addStepToPhase') }}</q-tooltip>
                </q-btn>
                <q-btn 
                  flat
                  round
                  dense
                  icon="delete" 
                  size="sm" 
                  color="negative" 
                  @click.stop="deletePhaseSteps(selectedSkuId!, group.phaseNum)"
                >
                  <q-tooltip>{{ t('sku.deleteEntirePhase') }}</q-tooltip>
                </q-btn>
              </div>
            </div>

            <!-- Steps Table -->
            <q-table
              v-show="isPhaseExpanded(selectedSkuId!, group.phaseNum)"
              :rows="group.steps"
              :columns="stepColumns"
              row-key="step_id"
              flat
              dense
              hide-pagination
              :rows-per-page-options="[0]"
              class="child-table q-mt-xs"
              @row-dblclick="(evt, row) => openStepDialog(row)"
            >
               <!-- Cell Templates -->
               <template v-slot:body-cell-actions="stepProps">
                  <q-td :props="stepProps" class="text-center">
                    <div class="row no-wrap items-center q-gutter-xs">
                      <q-btn color="primary" icon="edit" size="xs" flat round @click.stop="openStepDialog(stepProps.row)">
                        <q-tooltip>{{ t('common.edit') }}</q-tooltip>
                      </q-btn>
                      <q-btn color="info" icon="content_copy" size="xs" flat round @click.stop="copyStep(stepProps.row)">
                        <q-tooltip>{{ t('common.copy') }}</q-tooltip>
                      </q-btn>
                      <q-btn color="negative" icon="delete" size="xs" flat round @click.stop="deleteStep(stepProps.row)">
                        <q-tooltip>{{ t('common.delete') }}</q-tooltip>
                      </q-btn>
                    </div>
                  </q-td>
               </template>

               <template v-slot:body-cell-action_code="stepProps">
                  <q-td :props="stepProps">
                    <q-badge color="blue-7" outline v-if="stepProps.row.action_code">
                      {{ stepProps.row.action_code }}
                    </q-badge>
                  </q-td>
               </template>

               <template v-slot:body-cell-uom="stepProps">
                  <q-td :props="stepProps">
                    {{ stepProps.row.uom || stepProps.row.ingredient_unit || '' }}
                  </q-td>
               </template>

               <template v-slot:body-cell-qc_flags="stepProps">
                  <q-td :props="stepProps" class="q-gutter-xs text-center">
                    <q-tooltip>
                      <div v-if="stepProps.row.qc_temp">QC Temp Required</div>
                      <div v-if="stepProps.row.record_steam_pressure">Record Steam Pressure Required</div>
                      <div v-if="stepProps.row.record_ctw">Record CTW Required</div>
                      <div v-if="stepProps.row.operation_brix_record">Record Brix Required</div>
                      <div v-if="stepProps.row.operation_ph_record">Record PH Required</div>
                    </q-tooltip>
                    <q-icon v-if="stepProps.row.qc_temp" name="thermostat" color="primary" size="xs" />
                    <q-icon v-if="stepProps.row.record_steam_pressure" name="compress" color="amber-8" size="xs" />
                    <q-icon v-if="stepProps.row.record_ctw" name="water_drop" color="blue" size="xs" />
                    <q-icon v-if="stepProps.row.operation_brix_record" name="percent" color="green" size="xs" />
                    <q-icon v-if="stepProps.row.operation_ph_record" name="science" color="deep-purple" size="xs" />
                  </q-td>
               </template>
            </q-table>
          </div>
        </template>

        <div v-else class="text-center text-grey-6 q-pa-xl">
          <q-icon name="list_alt" size="4em" class="q-mb-md" />
          <div class="text-h6">{{ t('sku.noStepsDefined') }}</div>
          <div class="text-subtitle2">{{ t('sku.noStepsDesc') }}</div>
        </div>
      </template>

      <!-- Placeholder when no SKU selected -->
      <div v-else class="text-center text-grey-5 q-pa-xl">
        <q-icon name="touch_app" size="4em" class="q-mb-md" />
        <div class="text-h6">{{ t('sku.selectSku') }}</div>
        <div class="text-subtitle2">{{ t('sku.selectSkuDesc') }}</div>
      </div>
    </div>

    <!-- Step Edit Dialog -->
    <q-dialog v-model="showStepDialog" persistent>
      <q-card style="min-width: 900px; max-width: 90vw;">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            <q-icon :name="!editingStep ? 'add_circle' : 'edit'" color="positive" class="q-mr-sm" />
            {{ !editingStep ? t('sku.addNewStep') : t('sku.editStep') + ' ' + (stepForm.phase_number + '.' + stepForm.sub_step) }}
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup @click="closeStepDialog" />
        </q-card-section>

        <q-card-section class="q-pa-md scroll" style="max-height: 80vh">
          <div class="row q-col-gutter-md">
            
            <!-- SECTION 1: Step Identification -->
            <div class="col-12">
              <div class="text-subtitle2 text-primary q-mb-xs text-uppercase text-bold">{{ t('sku.stepIdentification') }}</div>
              <q-separator class="q-mb-sm" />
            </div>
            
            <!-- Row 1: Alphanumeric IDs and Sequencing -->
            <div class="col-12 col-md-4">
              <q-input
                v-model="stepForm.phase_number"
                :label="t('sku.phaseNumber')"
                outlined
                dense
                placeholder="p0010"
                hint="Alphanumeric sequence"
              />
            </div>

            <div class="col-12 col-md-4">
              <q-select
                v-model="stepForm.phase_id"
                :options="skuPhases.map(p => ({ label: `${p.phase_code} - ${p.phase_description}`, value: p.phase_code }))"
                emit-value
                map-options
                :label="t('sku.phaseLink')"
                outlined
                dense
                hint="Relates to Master Phase Code"
              >
                <template v-slot:after>
                  <q-btn
                    round
                    dense
                    flat
                    icon="settings"
                    color="primary"
                    @click.stop="openPhaseDialog"
                  >
                    <q-tooltip v-if="!showPhaseDialog">{{ t('sku.managePhases') }}</q-tooltip>
                  </q-btn>
                </template>
              </q-select>
            </div>
            
            <div class="col-12 col-md-4">
              <q-input 
                v-model.number="stepForm.sub_step" 
                :label="t('sku.subStep')" 
                type="number"
                outlined 
                dense
                hint="Sequence in phase"
              />
            </div>

            <!-- Row 2: Descriptive text -->
            <div class="col-12">
              <q-input 
                v-model="stepForm.action" 
                :label="t('sku.phaseDesc')" 
                outlined 
                dense
                hint="Optional description for this phase"
              />
            </div>
             
             <!-- SECTION 2: Action & Component -->
            <div class="col-12">
               <div class="text-subtitle2 text-primary q-mb-xs text-uppercase text-bold q-mt-sm">{{ t('sku.actionComponent') }}</div>
               <q-separator class="q-mb-sm" />
            </div>

                <div class="col-4">
                    <q-select
                      v-model="stepForm.action_code"
                      :options="skuActions.map(a => ({ label: `${a.action_code} - ${a.action_description}`, value: a.action_code }))"
                      :label="t('sku.actionCode')"
                      outlined
                      dense
                      emit-value
                      map-options
                      clearable
                      @update:model-value="onActionChange"
                    >
                      <template v-slot:after>
                        <q-btn
                          round
                          dense
                          flat
                          icon="settings"
                          color="primary"
                          @click.stop="openActionDialog"
                        >
                          <q-tooltip v-if="!showActionDialog">{{ t('sku.manageActions') }}</q-tooltip>
                        </q-btn>
                      </template>
                    </q-select>
                </div>
                <div class="col-8">
                  <q-input 
                    v-model="stepForm.action_description" 
                    :label="t('sku.actionDesc')" 
                    outlined 
                    dense
                    readonly
                    bg-color="grey-2"
                    hint="Auto-filled from Action Code"
                  />
                </div>

            <div class="col-12 col-sm-6">
              <q-select
                v-model="stepForm.re_code"
                :options="ingredientOptions"
                :label="t('sku.ingredientComponent')"
                outlined
                dense
                emit-value
                map-options
                clearable
                use-input
                input-debounce="0"
                @filter="filterIngredients"
                @update:model-value="onIngredientChange"
              >
                <template v-slot:no-option>
                  <q-item><q-item-section class="text-grey">{{ t('sku.noResults') }}</q-item-section></q-item>
                </template>
              </q-select>
            </div>

            <div class="col-12 col-sm-6">
              <q-select
                v-model="stepForm.destination"
                :options="skuDestinations.map(d => ({ label: d.destination_code, value: d.destination_code }))"
                :label="t('sku.destination')"
                outlined
                dense
                emit-value
                map-options
                clearable
              />
            </div>

            <!-- SECTION 3: Process Requirements -->
            <div class="col-12">
               <div class="text-subtitle2 text-primary q-mb-xs text-uppercase text-bold q-mt-sm">{{ t('sku.processRequirements') }}</div>
               <q-separator class="q-mb-sm" />
            </div>

            <div class="col-6 col-sm-4">
              <q-input 
                v-model.number="stepForm.require" 
                :label="t('sku.volumeAmount')" 
                type="number"
                outlined 
                dense
                step="0.001"
              />
            </div>
            
             <div class="col-6 col-sm-2">
              <q-input 
                v-model="stepForm.uom" 
                :label="t('sku.uom')" 
                outlined 
                dense
              />
            </div>

            <div class="col-6 col-sm-3">
              <q-input 
                v-model.number="stepForm.low_tol" 
                :label="t('sku.lowTol')" 
                type="number"
                outlined 
                dense
                step="0.001"
              />
            </div>

            <div class="col-6 col-sm-3">
              <q-input 
                v-model.number="stepForm.high_tol" 
                :label="t('sku.highTol')" 
                type="number"
                outlined 
                dense
                step="0.001"
              />
            </div>
            
            <div class="col-12">
               <q-input 
                v-model="stepForm.step_condition" 
                :label="t('sku.condition')" 
                outlined 
                dense
              />
            </div>

            <!-- SECTION 4: Mechanical Settings -->
            <div class="col-12">
               <div class="text-subtitle2 text-primary q-mb-xs text-uppercase text-bold q-mt-sm">{{ t('sku.equipmentSettings') }}</div>
               <q-separator class="q-mb-sm" />
            </div>

            <div class="col-6 col-sm-3">
              <q-input 
                v-model.number="stepForm.agitator_rpm" 
                :label="t('sku.agitatorRpm')" 
                type="number"
                outlined 
                dense
              />
            </div>

            <div class="col-6 col-sm-3">
              <q-input 
                v-model.number="stepForm.high_shear_rpm" 
                :label="t('sku.highShearRpm')" 
                type="number"
                outlined 
                dense
              />
            </div>
            
             <div class="col-6 col-sm-3">
              <q-input 
                v-model.number="stepForm.step_time" 
                :label="t('sku.timeSeconds')" 
                type="number"
                outlined 
                dense
                hint="Stored as seconds"
              />
            </div>
            
             <div class="col-6 col-sm-3">
              <q-input 
                 :model-value="stepForm.step_time ? (stepForm.step_time / 60).toFixed(2) : 0"
                 :label="t('sku.timeMinutes')"
                 readonly
                 outlined
                 dense
                 bg-color="grey-2"
                 hint="Read-only calc"
              />
            </div>

             <!-- SECTION 5: Temperature -->
            <div class="col-12">
               <div class="text-subtitle2 text-primary q-mb-xs text-uppercase text-bold q-mt-sm">{{ t('sku.tempControl') }}</div>
               <q-separator class="q-mb-sm" />
            </div>
            
             <div class="col-12 col-sm-4">
              <q-input 
                v-model.number="stepForm.temperature" 
                :label="t('sku.prepareTemp')" 
                type="number"
                outlined 
                dense
                step="0.1"
              />
            </div>
            
             <div class="col-6 col-sm-4">
              <q-input 
                v-model.number="stepForm.temp_low" 
                :label="t('sku.offsetLow')" 
                type="number"
                outlined 
                dense
                step="0.1"
              />
            </div>
            
             <div class="col-6 col-sm-4">
              <q-input 
                v-model.number="stepForm.temp_high" 
                :label="t('sku.offsetHigh')" 
                type="number"
                outlined 
                dense
                step="0.1"
              />
            </div>

            <!-- SECTION 6: QC & Records -->
            <div class="col-12">
              <div class="text-subtitle2 text-primary q-mb-xs text-uppercase text-bold q-mt-sm">{{ t('sku.qcRecords') }}</div>
              <q-separator class="q-mb-sm" />
            </div>

            <div class="col-12 row q-col-gutter-sm">
               <!-- Checkboxes row -->
               <div class="col-12 row items-center q-gutter-x-md">
                   <q-checkbox v-model="stepForm.qc_temp" :label="t('sku.qcTemp')" dense />
                   <q-checkbox v-model="stepForm.record_steam_pressure" :label="t('sku.recordSteam')" dense />
                   <q-checkbox v-model="stepForm.record_ctw" :label="t('sku.recordCtw')" dense />
                   <q-checkbox v-model="stepForm.operation_brix_record" :label="t('sku.opBrixRecord')" dense />
                   <q-checkbox v-model="stepForm.operation_ph_record" :label="t('sku.opPhRecord')" dense />
               </div>
               
               <div class="col-12 row q-col-gutter-md q-mt-xs">
                   <div class="col-6">
                      <q-input 
                        v-model="stepForm.brix_sp" 
                        :label="t('sku.brixSp')" 
                        outlined 
                        dense
                      />
                   </div>
                   <div class="col-6">
                      <q-input 
                        v-model="stepForm.ph_sp" 
                        :label="t('sku.phSp')" 
                        outlined 
                        dense
                      />
                   </div>
               </div>
            </div>

          </div>
        </q-card-section>

        <q-separator />

        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat :label="t('common.cancel')" color="grey-7" @click="closeStepDialog" />
          <q-btn 
            unelevated 
            :label="t('sku.saveStep')" 
            color="primary" 
            @click="saveStep"
            :loading="isSaving"
            icon="save"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- SKU Creation Dialog -->
    <q-dialog v-model="showSkuDialog" persistent>
      <q-card style="min-width: 500px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            <q-icon :name="isEditMode ? 'edit' : 'add_circle'" color="positive" class="q-mr-sm" />
            {{ isEditMode ? t('sku.editSKU') : t('sku.createNew') }}
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div class="column q-gutter-y-lg q-pt-md">
            <q-input
              v-model="skuForm.sku_id"
              :label="t('sku.skuId') + ' *'"
              outlined
              dense
              :rules="[val => !!val || t('sku.skuIdRequired')]"
              :hint="t('sku.uniqueIdHint')"
            />

            <q-input
              v-model="skuForm.sku_name"
              :label="t('sku.skuName') + ' *'"
              outlined
              dense
              :rules="[val => !!val || t('sku.skuNameRequired')]"
              :hint="t('sku.descNameHint')"
            />

            <div class="row q-col-gutter-x-md">
              <div class="col-6">
                <q-input
                  v-model.number="skuForm.std_batch_size"
                  :label="t('sku.stdBatchSize')"
                  type="number"
                  outlined
                  dense
                  :hint="t('sku.defaultBatchSize')"
                />
              </div>
              <div class="col-6">
                <q-select
                  v-model="skuForm.uom"
                  :options="['kg', 'L', 'unit']"
                  :label="t('sku.uom')"
                  outlined
                  dense
                  :hint="t('sku.unitOfMeasure')"
                />
              </div>
            </div>

            <q-select
              v-model="skuForm.sku_group"
              :options="[{label: '-- None --', value: null}, ...skuGroups.map(g => ({label: `${g.group_code} - ${g.group_name}`, value: g.id}))]"
              emit-value
              map-options
              :label="t('sku.skuGroup', 'SKU Group')"
              outlined
              dense
              clearable
              :hint="'Group for categorizing SKUs'"
            >
              <template v-slot:after>
                <q-btn
                  round
                  dense
                  flat
                  icon="settings"
                  color="grey-7"
                  @click.stop="openGroupDialog"
                >
                  <q-tooltip v-if="!showGroupDialog">Manage SKU Groups</q-tooltip>
                </q-btn>
              </template>
            </q-select>

            <q-select
              v-model="skuForm.status"
              :options="['Active', 'Inactive']"
              :label="t('common.status')"
              outlined
              dense
            />
          </div>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md q-gutter-sm">
          <q-btn
            :label="t('common.cancel')"            color="grey-7"
            flat
            v-close-popup
            class="q-px-md"
          />
          <q-btn
            :label="isEditMode ? t('sku.saveChanges') : t('sku.createSku')"
            color="positive"
            unelevated
            @click="saveNewSku"
            :loading="isCreatingSku"
            :icon="isEditMode ? 'save' : 'add'"
            class="q-px-lg"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- SKU Duplicate Dialog -->
    <q-dialog v-model="showDuplicateDialog">
      <q-card style="min-width: 500px" class="q-pa-md">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            <q-icon name="content_copy" color="accent" class="q-mr-sm" />
            {{ t('sku.duplicateSku') }}: {{ duplicateForm.source_sku_id }}
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="q-pt-md">
          <div class="text-subtitle2 text-grey-7 q-mb-md">
            {{ t('sku.duplicateDesc') }}
          </div>
          
          <div class="q-gutter-y-md">
            <q-input
              v-model="duplicateForm.new_sku_id"
              :label="t('sku.newSkuId')"
              outlined
              dense
              autofocus
              :rules="[val => !!val || t('sku.newSkuIdRequired')]"
              :hint="t('sku.uniqueId')"
            />

            <q-input
              v-model="duplicateForm.new_sku_name"
              :label="t('sku.newSkuName')"
              outlined
              dense
              :rules="[val => !!val || t('sku.newSkuNameRequired')]"
              :hint="t('sku.descName')"
            />
          </div>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md q-gutter-sm">
          <q-btn
            :label="t('common.cancel')"            color="grey-7"
            flat
            v-close-popup
            class="q-px-md"
          />
          <q-btn
            :label="t('sku.duplicateSkuBtn')"
            color="accent"
            unelevated
            @click="saveDuplicateSku"
            :loading="isDuplicating"
            icon="content_copy"
            class="q-px-lg"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>



    <!-- SKU Action Dialog -->

    <q-dialog v-model="showActionDialog">
      <q-card style="min-width: 500px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            <q-icon name="settings" color="positive" class="q-mr-sm" />
            {{ t('sku.manageActions') }}
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div class="row q-col-gutter-sm q-mb-md q-pt-md">
            <div class="col-4">
               <q-input v-model="actionForm.action_code" label="Action Code" type="number" outlined dense :readonly="isActionEdit" :rules="[val => !!val || 'Required', val => /^\d+$/.test(val) || 'Numeric only']" hint="e.g., 10010" />
            </div>
            <div class="col-8">
               <q-input v-model="actionForm.action_description" label="Description" outlined dense :rules="[val => !!val || 'Required']" />
            </div>
            <div class="col-12">
               <q-input v-model="actionForm.component_filter" label="Component Filter (Optional)" outlined dense hint="e.g. re_code=RO-Water" />
            </div>
           </div>
           
           <div class="row q-mb-lg justify-end q-gutter-sm">
             <q-btn v-if="isActionEdit" :label="t('sku.cancelEdit')" flat color="grey-7" @click="openActionDialog" />
             <q-btn :label="isActionEdit ? t('sku.updateAction') : t('sku.addAction')" color="positive" unelevated :loading="isSavingAction" @click="saveAction" />
           </div>

           <q-separator class="q-mb-md" />
           
           <div class="row items-center q-mb-sm">
             <div class="text-subtitle2 text-grey-8 uppercase text-bold">Existing Actions</div>
             <q-space />
             <q-btn flat round dense icon="refresh" color="primary" @click="fetchActions" :loading="isLoading" size="sm">
               <q-tooltip>Refresh Actions</q-tooltip>
             </q-btn>
           </div>

           <q-input 
             v-model="actionSearch" 
             placeholder="Filter actions..." 
             dense 
             outlined 
             class="q-mb-sm"
             clearable
           >
             <template v-slot:prepend>
               <q-icon name="search" />
             </template>
           </q-input>

           <q-list bordered separator style="max-height: 300px; overflow-y: auto" class="rounded-borders">
             <q-item v-for="action in filteredSkuActions" :key="action.action_code">
               <q-item-section>
                 <q-item-label class="text-bold text-primary">{{ action.action_code }}</q-item-label>
                 <q-item-label caption>{{ action.action_description }}</q-item-label>
               </q-item-section>
               <q-item-section side>
                 <div class="row q-gutter-xs">
                   <q-btn flat round dense icon="edit" color="primary" @click="editAction(action)" />
                   <q-btn flat round dense icon="delete" color="negative" @click="deleteAction(action)" />
                 </div>
               </q-item-section>
             </q-item>
                <q-item v-if="filteredSkuActions.length === 0">
                  <q-item-section class="text-center text-grey">No matching actions found</q-item-section>
               </q-item>
           </q-list>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat :label="t('common.close')" color="grey-7" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- SKU Phase Dialog -->
    <q-dialog v-model="showPhaseDialog">
      <q-card style="min-width: 500px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            <q-icon name="layers" color="positive" class="q-mr-sm" />
            {{ t('sku.managePhases') }}
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div class="row q-col-gutter-sm q-mb-md q-pt-md">
            <div class="col-3">
               <q-select v-model.number="phaseForm.phase_id" :options="skuPhases.map(p => p.phase_id)" label="Phase ID" outlined dense use-input input-debounce="0" @update:model-value="onPhaseIdChange" :rules="[val => !!val || 'Required']" />
            </div>
            <div class="col-3">
               <q-input v-model="phaseForm.phase_code" label="Code" outlined dense hint="p0010" />
            </div>
            <div class="col-6">
               <q-input v-model="phaseForm.phase_description" label="Description" outlined dense :rules="[val => !!val || 'Required']" />
            </div>
           </div>
           
           <div class="row q-mb-lg justify-end q-gutter-sm">
             <q-btn v-if="editingPhase" :label="t('sku.cancelEdit')" flat color="grey-7" @click="openPhaseDialog" />
             <q-btn :label="editingPhase ? t('sku.updatePhase') : t('sku.addPhase')" color="positive" unelevated @click="savePhase" />
           </div>

           <q-separator class="q-mb-md" />
           
           <div class="row items-center q-mb-sm">
             <div class="text-subtitle2 text-grey-8 uppercase text-bold">{{ t('sku.existingPhases') }}</div>
             <q-space />
             <q-btn flat round dense icon="refresh" color="primary" @click="fetchPhases" :loading="isLoading" size="sm">
               <q-tooltip>{{ t('sku.refreshPhases') }}</q-tooltip>
             </q-btn>
           </div>

           <q-input 
             v-model="phaseSearch" 
             :placeholder="t('sku.filterPhases')"
             dense 
             outlined 
             class="q-mb-sm"
             clearable
           >
             <template v-slot:prepend>
               <q-icon name="search" />
             </template>
           </q-input>

           <q-list bordered separator style="max-height: 300px; overflow-y: auto" class="rounded-borders">
             <q-item v-for="phase in filteredSkuPhases" :key="phase.phase_id">
               <q-item-section avatar v-if="phase.phase_code">
                 <q-badge color="primary">{{ phase.phase_code }}</q-badge>
               </q-item-section>
               <q-item-section>
                 <q-item-label class="text-bold">ID: {{ phase.phase_id }}</q-item-label>
                 <q-item-label caption>{{ phase.phase_description }}</q-item-label>
               </q-item-section>
               <q-item-section side>
                 <div class="row q-gutter-xs">
                   <q-btn flat round dense icon="edit" color="primary" @click="editPhase(phase)" />
                   <q-btn flat round dense icon="delete" color="negative" @click="deletePhase(phase)" />
                 </div>
               </q-item-section>
             </q-item>
           </q-list>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat :label="t('common.close')" color="grey-7" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>


    <!-- SKU Group Dialog -->
    <q-dialog v-model="showGroupDialog">
      <q-card style="min-width: 500px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            <q-icon name="category" color="teal" class="q-mr-sm" />
            Manage SKU Groups
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div class="row q-col-gutter-sm q-mb-md q-pt-md">
            <div class="col-3">
              <q-input v-model="groupForm.group_code" label="Code *" outlined dense :readonly="isGroupEdit" :rules="[val => !!val || 'Required']" hint="e.g. SYR" />
            </div>
            <div class="col-4">
              <q-input v-model="groupForm.group_name" label="Name *" outlined dense :rules="[val => !!val || 'Required']" hint="e.g. Syrup" />
            </div>
            <div class="col-5">
              <q-input v-model="groupForm.description" label="Description" outlined dense />
            </div>
          </div>

          <div class="row q-mb-lg justify-end q-gutter-sm">
            <q-btn v-if="isGroupEdit" label="Cancel" flat color="grey-7" @click="openGroupDialog" />
            <q-btn :label="isGroupEdit ? 'Update' : 'Add Group'" color="teal" unelevated :loading="isSavingGroup" @click="saveGroup" />
          </div>

          <q-separator class="q-mb-md" />

          <div class="row items-center q-mb-sm">
            <div class="text-subtitle2 text-grey-8 uppercase text-bold">Existing Groups</div>
            <q-space />
            <q-btn flat round dense icon="refresh" color="primary" @click="fetchSkuGroups" size="sm">
              <q-tooltip>Refresh</q-tooltip>
            </q-btn>
          </div>

          <q-input v-model="groupSearch" placeholder="Filter groups..." dense outlined class="q-mb-sm" clearable>
            <template v-slot:prepend><q-icon name="search" /></template>
          </q-input>

          <q-list bordered separator style="max-height: 300px; overflow-y: auto" class="rounded-borders">
            <q-item v-for="group in filteredSkuGroups" :key="group.group_code">
              <q-item-section>
                <q-item-label class="text-bold text-teal">{{ group.group_code }}</q-item-label>
                <q-item-label caption>{{ group.group_name }} <span v-if="group.description" class="text-grey-6">— {{ group.description }}</span></q-item-label>
              </q-item-section>
              <q-item-section side>
                <div class="row q-gutter-xs">
                  <q-btn flat round dense icon="edit" color="primary" @click="editGroup(group)" />
                  <q-btn flat round dense icon="delete" color="negative" @click="deleteGroup(group)" />
                </div>
              </q-item-section>
            </q-item>
            <q-item v-if="filteredSkuGroups.length === 0">
              <q-item-section class="text-center text-grey">No groups found</q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="Close" color="grey-7" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

  </q-page>
</template>

<style scoped>
.sku-master-view {
  max-width: 1600px;
  margin: 0 auto;
}

.master-table {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.filter-input :deep(.q-field__control) {
  min-height: 28px !important;
  height: 28px !important;
}
.filter-input :deep(.q-field__native) {
  font-size: 12px;
  padding: 0 4px;
}
.filter-input :deep(.q-field__marginal) {
  height: 28px;
}

.child-row {
  background-color: #f5f5f5;
}

.child-table-container {
  padding: 16px;
  background: white;
  border-radius: 4px;
  margin: 8px;
}

.child-table {
  background: white;
}

.child-table :deep(table) {
  table-layout: fixed;
  width: 100%;
}

.child-table :deep(thead) {
  background: #e3f2fd;
}

.child-table :deep(tbody tr:hover) {
  background: #f5f5f5;
}

.cursor-pointer {
  cursor: pointer;
}

.cursor-pointer:hover {
  background-color: #cfd8dc !important;
  transition: background-color 0.2s ease;
}
</style>

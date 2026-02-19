<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { QTableColumn } from 'quasar'
import { useQuasar } from 'quasar'
import { appConfig } from '~/appConfig/config'

// ============================================================================
// INTERFACES
// ============================================================================

interface SkuMaster {
  id?: number
  sku_id: string
  sku_name: string
  std_batch_size?: number
  uom?: string
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
const ingredients = ref<Ingredient[]>([])
const ingredientOptions = ref<{label: string, value: string, original: Ingredient}[]>([])

// --- State Tracking ---
const isLoading = ref(false)
const isSaving = ref(false)
const searchFilter = ref('')
const selectedSkus = ref<SkuMaster[]>([])
const showAllIncludingInactive = ref(false)
const showFilters = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

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

// --- Control State ---
const showSkuDialog = ref(false)
const showStepDialog = ref(false)
const showActionDialog = ref(false)
const showPhaseDialog = ref(false)
const showDuplicateDialog = ref(false)

const isCreatingSku = ref(false)
const isEditMode = ref(false)
const isSavingAction = ref(false)
const isActionEdit = ref(false)
const isDuplicating = ref(false)
const actionSearch = ref('')
const phaseSearch = ref('')

// --- Forms ---
const editingSkuId = ref<number | undefined>(undefined)
const skuForm = ref({
  sku_id: '',
  sku_name: '',
  std_batch_size: 0,
  uom: 'kg',
  status: 'Active'
})

const duplicateForm = ref({
  source_sku_id: '',
  new_sku_id: '',
  new_sku_name: ''
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
  if (!actionForm.value.action_code || !actionForm.value.action_description) return $q.notify({ type: 'warning', message: 'Fill all fields' })
  isSavingAction.value = true
  try {
    const method = isActionEdit.value ? 'PUT' : 'POST'
    const url = isActionEdit.value ? `${appConfig.apiBaseUrl}/sku-actions/${actionForm.value.action_code}` : `${appConfig.apiBaseUrl}/sku-actions/`
    await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(actionForm.value) })
    $q.notify({ type: 'positive', message: 'Action saved' })
    await fetchActions()
    if (isActionEdit.value) showActionDialog.value = false
    else actionForm.value = { action_code: '', action_description: '' }
  } catch (e) { $q.notify({ type: 'negative', message: 'Save failed' }) }
  finally { isSavingAction.value = false }
}

const deleteAction = (action: SkuAction) => {
  $q.dialog({ title: 'Confirm', message: `Delete action ${action.action_code}?`, cancel: true }).onOk(async () => {
    try {
      await fetch(`${appConfig.apiBaseUrl}/sku-actions/${action.action_code}`, { method: 'DELETE' })
      $q.notify({ type: 'positive', message: 'Action deleted' })
      await fetchActions()
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
  if (!phaseForm.value.phase_id || !phaseForm.value.phase_description) return $q.notify({ type: 'warning', message: 'Fill all fields' })
  try {
    const method = editingPhase.value ? 'PUT' : 'POST'
    const url = editingPhase.value ? `${appConfig.apiBaseUrl}/sku-phases/${phaseForm.value.phase_id}` : `${appConfig.apiBaseUrl}/sku-phases/`
    await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(phaseForm.value) })
    $q.notify({ type: 'positive', message: 'Phase saved' })
    await fetchPhases()
    if (editingPhase.value) showPhaseDialog.value = false
    else phaseForm.value = { phase_id: null, phase_code: '', phase_description: '' }
  } catch (e) { $q.notify({ type: 'negative', message: 'Save failed' }) }
}

const deletePhase = (phase: SkuPhase) => {
  $q.dialog({ title: 'Confirm', message: `Delete phase ${phase.phase_description}?`, cancel: true }).onOk(async () => {
    try {
      await fetch(`${appConfig.apiBaseUrl}/sku-phases/${phase.phase_id}`, { method: 'DELETE' })
      $q.notify({ type: 'positive', message: 'Phase deleted' })
      await fetchPhases()
    } catch (e) { $q.notify({ type: 'negative', message: 'Delete failed' }) }
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

  return skus
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
  showAllIncludingInactive.value = false
  $q.notify({ type: 'info', message: 'Filters reset' })
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
      $q.notify({ type: 'positive', message: 'SKUs imported successfully' })
      await fetchSkuMasters()
    } else {
      const error = await response.json()
      $q.notify({ type: 'negative', message: error.detail || 'Import failed' })
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Import failed' })
  } finally {
    if (target) target.value = ''
  }
}

// ============================================================================
// API SERVICES & UTILITIES
// ============================================================================

const fetchSkuMasters = async () => {
  isLoading.value = true
  try {
    const data = await fetch(`${appConfig.apiBaseUrl}/api/v_sku_master_detail`).then(res => res.json())
    skuMasters.value = data
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Failed to fetch SKU list' })
  } finally { isLoading.value = false }
}

const fetchSkuSteps = async (skuId: string) => {
  if (skuStepsMap.value[skuId]) return
  try {
    skuStepsMap.value[skuId] = await fetch(`${appConfig.apiBaseUrl}/api/v_sku_step_detail?sku_id=${skuId}`).then(res => res.json())
  } catch (err) {
    $q.notify({ type: 'negative', message: 'Failed to fetch steps' })
  }
}

const fetchActions = async () => {
  isLoading.value = true
  try { skuActions.value = await fetch(`${appConfig.apiBaseUrl}/sku-actions/`).then(res => res.json()) } 
  catch (e) { console.error(e) }
  finally { isLoading.value = false }
}

const fetchDestinations = async () => {
  try { skuDestinations.value = await fetch(`${appConfig.apiBaseUrl}/sku-destinations/`).then(res => res.json()) } 
  catch (e) { console.error(e) }
}

const fetchPhases = async () => {
  isLoading.value = true
  try { skuPhases.value = await fetch(`${appConfig.apiBaseUrl}/sku-phases/`).then(res => res.json()) } 
  catch (e) { console.error(e) }
  finally { isLoading.value = false }
}

const fetchIngredients = async () => {
  try {
    const data = await fetch(`${appConfig.apiBaseUrl}/ingredients/`).then(res => res.json())
    ingredients.value = data
    updateIngredientOptions(data)
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
      $q.notify({ type: 'positive', message: 'Export successful', icon: 'download' })
    }
  } catch (err) { $q.notify({ type: 'negative', message: 'Export failed' }) }
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
    $q.notify({ type: 'positive', message: `Step ${isNew ? 'created' : 'updated'}` })
    delete skuStepsMap.value[stepForm.value.sku_id]; await fetchSkuSteps(stepForm.value.sku_id)
    closeStepDialog()
  } catch (e: any) { $q.notify({ type: 'negative', message: 'Save failed' }) }
  finally { isSaving.value = false }
}

const copyStep = (step: SkuStep) => {
  const steps = skuStepsMap.value[step.sku_id] || []
  const maxSub = steps.filter(s => s.phase_number === step.phase_number).reduce((max, s) => Math.max(max, s.sub_step), 0)
  stepForm.value = { ...step, step_id: undefined, sub_step: maxSub + 10 }
  editingStep.value = null; showStepDialog.value = true
}

const deleteStep = (step: SkuStep) => {
  $q.dialog({ title: 'Confirm Delete', message: `Delete step ${step.phase_number}.${step.sub_step}?`, cancel: true }).onOk(async () => {
    try {
      await fetch(`${appConfig.apiBaseUrl}/sku-steps/${step.step_id}`, { method: 'DELETE' })
      $q.notify({ type: 'positive', message: 'Step deleted' })
      delete skuStepsMap.value[step.sku_id]; await fetchSkuSteps(step.sku_id)
    } catch (e) { $q.notify({ type: 'negative', message: 'Delete failed' }) }
  })
}

const deletePhaseSteps = (skuId: string, phaseNumber: string) => {
  const steps = skuStepsMap.value[skuId] || []
  const stepsInPhase = steps.filter(s => s.phase_number === phaseNumber)
  
  if (stepsInPhase.length === 0) {
    $q.notify({ type: 'warning', message: 'No steps to delete in this phase' })
    return
  }
  
  $q.dialog({
    title: 'Confirm Delete Phase',
    message: `Delete all ${stepsInPhase.length} step(s) in phase ${phaseNumber}?`,
    cancel: true,
    persistent: true
  }).onOk(async () => {
    try {
      // Delete all steps in the phase
      for (const step of stepsInPhase) {
        await fetch(`${appConfig.apiBaseUrl}/sku-steps/${step.step_id}`, { method: 'DELETE' })
      }
      $q.notify({ type: 'positive', message: `Phase ${phaseNumber} deleted (${stepsInPhase.length} steps)` })
      delete skuStepsMap.value[skuId]
      await fetchSkuSteps(skuId)
    } catch (e) {
      $q.notify({ type: 'negative', message: 'Delete failed' })
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
  skuForm.value = { sku_id: '', sku_name: '', std_batch_size: 0, uom: 'kg', status: 'Active' }
  isEditMode.value = false; editingSkuId.value = undefined; showSkuDialog.value = true
}

const editSku = (skuId: string) => {
  const sku = skuMasters.value.find(s => s.sku_id === skuId)
  if (!sku) return $q.notify({ type: 'negative', message: 'SKU not found' })
  skuForm.value = { sku_id: sku.sku_id, sku_name: sku.sku_name, std_batch_size: sku.std_batch_size || 0, uom: sku.uom || 'kg', status: sku.status || 'Active' }
  isEditMode.value = true; editingSkuId.value = sku.id; showSkuDialog.value = true
}

const saveNewSku = async () => {
  if (!skuForm.value.sku_id || !skuForm.value.sku_name) return $q.notify({ type: 'warning', message: 'Fill mandatory fields' })
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
        status: skuForm.value.status 
      }) 
    })
    $q.notify({ type: 'positive', message: `SKU ${isEdit ? 'updated' : 'created'}` })
    showSkuDialog.value = false
    await fetchSkuMasters()
  } catch (e) { $q.notify({ type: 'negative', message: 'Save failed' }) }
  finally { isCreatingSku.value = false }
}

const deleteSku = (sku: SkuMaster) => {
  $q.dialog({ title: 'Confirm Delete', message: `Mark SKU "${sku.sku_id}" as deleted?`, cancel: true }).onOk(async () => {
    try {
      await fetch(`${appConfig.apiBaseUrl}/skus/${sku.id}`, { method: 'DELETE' })
      $q.notify({ type: 'positive', message: 'SKU deleted' })
      await fetchSkuMasters()
    } catch (e) { $q.notify({ type: 'negative', message: 'Delete failed' }) }
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
    return $q.notify({ type: 'warning', message: 'Please fill all mandatory fields' })
  }
  
  isDuplicating.value = true
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/skus/duplicate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(duplicateForm.value)
    })
    
    if (response.ok) {
      $q.notify({ type: 'positive', message: 'SKU duplicated successfully' })
      showDuplicateDialog.value = false
      await fetchSkuMasters()
    } else {
      const error = await response.json()
      $q.notify({ type: 'negative', message: error.detail || 'Duplication failed' })
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Network error or server down' })
  } finally {
    isDuplicating.value = false
  }
}

// ============================================================================
// TABLE CONFIGURATION & LIFECYCLE
// ============================================================================

const masterColumns: QTableColumn[] = [
  { name: 'sku_id', label: 'SKU ID', field: 'sku_id', align: 'left' as const, sortable: true },
  { name: 'sku_name', label: 'SKU Name', field: 'sku_name', align: 'left' as const, sortable: true },
  { name: 'std_batch', label: 'Std Batch', field: 'std_batch_size', align: 'right' as const, sortable: true },
  { name: 'phases', label: 'Phases', field: 'total_phases', align: 'center' as const, sortable: true },
  { name: 'steps', label: 'Steps', field: 'total_sub_steps', align: 'center' as const, sortable: true },
  { name: 'status', label: 'Status', field: 'status', align: 'center' as const, sortable: true },
  { name: 'updated_at', label: 'Updated', field: 'updated_at', align: 'center' as const, sortable: true },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' as const, style: 'width: 140px' }
]

const stepColumns: QTableColumn[] = [
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center', style: 'width: 90px' },
  { name: 'sub_step', label: 'Sub', field: 'sub_step', align: 'center', sortable: true, style: 'width: 55px' },
  { name: 'action_code', label: 'Action', field: 'action_code', align: 'center', sortable: true, style: 'width: 70px' },
  { name: 'action_description', label: 'Description', field: 'action_description', align: 'left', sortable: true, style: 'width: 160px' },
  { name: 'ingredient_name', label: 'Ingredient', field: 'ingredient_name', align: 'left', sortable: true, style: 'width: auto' },
  { name: 'require', label: 'Vol', field: 'require', align: 'right', style: 'width: 65px' },
  { name: 'uom', label: 'UOM', field: 'uom', align: 'center', style: 'width: 55px' },
  { name: 'temperature', label: 'Temp', field: 'temperature', align: 'right', style: 'width: 60px' },
  { name: 'agitator_rpm', label: 'Agitator', field: 'agitator_rpm', align: 'right', style: 'width: 70px' },
  { name: 'step_time', label: 'Time', field: (row: any) => row.step_time ? (row.step_time / 60).toFixed(1) : '', align: 'right', style: 'width: 55px' },
  { name: 'qc_flags', label: 'QC/Rec', field: 'qc_temp', align: 'center', style: 'width: 70px' }
]

const refreshAll = async () => {
  await Promise.all([
    fetchSkuMasters(),
    fetchActions(),
    fetchDestinations(),
    fetchPhases(),
    fetchIngredients()
  ])
}

onMounted(refreshAll)
</script>

<template>
  <q-page class="q-pa-md bg-white">
    <!-- Page Header -->
    <div class="bg-blue-9 text-white q-pa-md rounded-borders q-mb-md shadow-2">
      <div class="row justify-between items-center">
        <div class="row items-center q-gutter-sm">
          <q-icon name="inventory_2" size="sm" />
          <div class="text-h6 text-weight-bolder">SKU Masters</div>
        </div>
        <div class="text-caption text-blue-2">Manage SKU masters and process steps</div>
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
          <q-tooltip>New SKU</q-tooltip>
        </q-btn>
        <q-btn 
          color="primary" 
          icon="refresh" 
          @click="refreshAll" 
          round
          flat
        >
          <q-tooltip>Refresh</q-tooltip>
        </q-btn>
        <q-btn 
          color="primary" 
          icon="filter_alt_off" 
          @click="resetFilters" 
          round
          flat
        >
          <q-tooltip>Reset Filters</q-tooltip>
        </q-btn>
        <q-btn 
          color="accent" 
          icon="filter_alt" 
          @click="showFilters = !showFilters" 
          round
          flat
        >
          <q-tooltip>{{ showFilters ? 'Hide Filters' : 'Show Filters' }}</q-tooltip>
        </q-btn>
        <q-btn 
          color="secondary" 
          icon="file_download" 
          @click="exportToExcel" 
          round
          flat
        >
          <q-tooltip>Export Excel</q-tooltip>
        </q-btn>
        <q-btn 
          color="accent" 
          icon="file_upload" 
          @click="importCSV" 
          round
          flat
        >
          <q-tooltip>Import CSV</q-tooltip>
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
          <q-tooltip>Actions</q-tooltip>
        </q-btn>
        <q-checkbox 
          v-model="showAllIncludingInactive" 
          label="Show All (including Inactive)" 
          dense
        />
        <q-input 
          v-model="searchFilter" 
          placeholder="Search SKU..." 
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

    <!-- Master Table -->
    <q-table
      :rows="filteredSkus"
      :columns="masterColumns"
      row-key="sku_id"
      :rows-per-page-options="[10, 25, 50, 100]"
      :pagination="{ rowsPerPage: 25 }"
      flat
      bordered
      :loading="isLoading"
      class="master-table q-mb-lg"
    >
      <!-- Custom Row Template for Selection -->
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
            <template v-else-if="col.name === 'status'">
              <q-badge 
                :color="props.row.status === 'Active' ? 'positive' : 'grey'" 
                :label="props.row.status"
              />
            </template>
            <template v-else-if="col.name === 'updated_at'">
              <div v-if="props.row.updated_at" class="text-caption">
                {{ new Date(props.row.updated_at).toLocaleDateString() }}
              </div>
              <div v-else class="text-grey-5">-</div>
            </template>
            <template v-else-if="col.name === 'actions'">
              <div class="row items-center justify-center q-gutter-xs">
                <q-btn 
                  size="sm" 
                  color="info" 
                  flat 
                  round
                  icon="content_copy" 
                  @click.stop="copySku(props.row)"
                >
                  <q-tooltip>Duplicate SKU</q-tooltip>
                </q-btn>
                <q-btn 
                  size="sm" 
                  color="primary" 
                  flat 
                  round
                  icon="edit" 
                  @click.stop="editSku(props.row.sku_id)"
                >
                  <q-tooltip>Edit SKU</q-tooltip>
                </q-btn>
                <q-btn 
                  size="sm" 
                  color="negative" 
                  flat 
                  round
                  icon="delete" 
                  @click.stop="deleteSku(props.row)"
                >
                  <q-tooltip>Delete SKU</q-tooltip>
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
          <span>No SKUs found</span>
        </div>
      </template>
    </q-table>

    <!-- Detail View (Always Visible) -->
      <div class="detail-container q-pa-md bg-white rounded-borders shadow-1 bordered">
      <template v-if="selectedSkuId">
        <div class="row items-center q-mb-md">
          <div class="text-h6 text-primary row items-center">
            <q-icon name="format_list_numbered" size="md" class="q-mr-sm" />
            Process Steps for {{ selectedSkuId }} 
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
              <q-tooltip>Phase Management</q-tooltip>
            </q-btn>
            
            <q-btn 
              flat 
              round 
              dense 
              icon="refresh" 
              color="grey-7" 
              @click="fetchSkuSteps(selectedSkuId)"
            >
              <q-tooltip>Refresh Steps</q-tooltip>
            </q-btn>
            
            <q-btn 
              flat 
              round 
              dense 
              icon="add_circle" 
              color="primary" 
              @click="addStep(selectedSkuId)"
            >
              <q-tooltip>Add New Phase</q-tooltip>
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
              <q-tooltip>Expand All</q-tooltip>
            </q-btn>
            <q-btn 
              flat 
              round 
              dense 
              icon="unfold_less" 
              color="teal" 
              @click="collapseAllPhases"
            >
              <q-tooltip>Collapse All</q-tooltip>
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
                  <q-tooltip>Add Step to Phase</q-tooltip>
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
                  <q-tooltip>Delete Entire Phase</q-tooltip>
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
                        <q-tooltip>Edit</q-tooltip>
                      </q-btn>
                      <q-btn color="info" icon="content_copy" size="xs" flat round @click.stop="copyStep(stepProps.row)">
                        <q-tooltip>Copy</q-tooltip>
                      </q-btn>
                      <q-btn color="negative" icon="delete" size="xs" flat round @click.stop="deleteStep(stepProps.row)">
                        <q-tooltip>Delete</q-tooltip>
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
          <div class="text-h6">No Process Steps Defined</div>
          <div class="text-subtitle2">Click the plus icon above to add your first phase</div>
        </div>
      </template>

      <!-- Placeholder when no SKU selected -->
      <div v-else class="text-center text-grey-5 q-pa-xl">
        <q-icon name="touch_app" size="4em" class="q-mb-md" />
        <div class="text-h6">Select a SKU</div>
        <div class="text-subtitle2">Click on a SKU row above to view its process steps</div>
      </div>
    </div>

    <!-- Step Edit Dialog -->
    <q-dialog v-model="showStepDialog" persistent>
      <q-card style="min-width: 900px; max-width: 90vw;">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            <q-icon :name="!editingStep ? 'add_circle' : 'edit'" color="positive" class="q-mr-sm" />
            {{ !editingStep ? 'Add New Step' : 'Edit Step ' + (stepForm.phase_number + '.' + stepForm.sub_step) }}
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup @click="closeStepDialog" />
        </q-card-section>

        <q-card-section class="q-pa-md scroll" style="max-height: 80vh">
          <div class="row q-col-gutter-md">
            
            <!-- SECTION 1: Step Identification -->
            <div class="col-12">
              <div class="text-subtitle2 text-primary q-mb-xs text-uppercase text-bold">Step Identification</div>
              <q-separator class="q-mb-sm" />
            </div>
            
            <!-- Row 1: Alphanumeric IDs and Sequencing -->
            <div class="col-12 col-md-4">
              <q-input
                v-model="stepForm.phase_number"
                label="Phase Number"
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
                label="Phase Link (Code)"
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
                    <q-tooltip>Manage Phases</q-tooltip>
                  </q-btn>
                </template>
              </q-select>
            </div>
            
            <div class="col-12 col-md-4">
              <q-input 
                v-model.number="stepForm.sub_step" 
                label="Sub Step" 
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
                label="Phase Description" 
                outlined 
                dense
                hint="Optional description for this phase"
              />
            </div>
             
             <!-- SECTION 2: Action & Component -->
            <div class="col-12">
               <div class="text-subtitle2 text-primary q-mb-xs text-uppercase text-bold q-mt-sm">Action & Component</div>
               <q-separator class="q-mb-sm" />
            </div>

                <div class="col-4">
                    <q-select
                      v-model="stepForm.action_code"
                      :options="skuActions.map(a => ({ label: `${a.action_code} - ${a.action_description}`, value: a.action_code }))"
                      label="Action Code"
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
                          <q-tooltip>Manage Actions</q-tooltip>
                        </q-btn>
                      </template>
                    </q-select>
                </div>
                <div class="col-8">
                  <q-input 
                    v-model="stepForm.action_description" 
                    label="Action Description" 
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
                label="Ingredient / Component"
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
                  <q-item><q-item-section class="text-grey">No results</q-item-section></q-item>
                </template>
              </q-select>
            </div>

            <div class="col-12 col-sm-6">
              <q-select
                v-model="stepForm.destination"
                :options="skuDestinations.map(d => ({ label: d.destination_code, value: d.destination_code }))"
                label="Destination"
                outlined
                dense
                emit-value
                map-options
                clearable
              />
            </div>

            <!-- SECTION 3: Process Requirements -->
            <div class="col-12">
               <div class="text-subtitle2 text-primary q-mb-xs text-uppercase text-bold q-mt-sm">Process Requirements</div>
               <q-separator class="q-mb-sm" />
            </div>

            <div class="col-6 col-sm-4">
              <q-input 
                v-model.number="stepForm.require" 
                label="Volume / Amount" 
                type="number"
                outlined 
                dense
                step="0.001"
              />
            </div>
            
             <div class="col-6 col-sm-2">
              <q-input 
                v-model="stepForm.uom" 
                label="UOM" 
                outlined 
                dense
              />
            </div>

            <div class="col-6 col-sm-3">
              <q-input 
                v-model.number="stepForm.low_tol" 
                label="Low Tol" 
                type="number"
                outlined 
                dense
                step="0.001"
              />
            </div>

            <div class="col-6 col-sm-3">
              <q-input 
                v-model.number="stepForm.high_tol" 
                label="High Tol" 
                type="number"
                outlined 
                dense
                step="0.001"
              />
            </div>
            
            <div class="col-12">
               <q-input 
                v-model="stepForm.step_condition" 
                label="Condition" 
                outlined 
                dense
              />
            </div>

            <!-- SECTION 4: Mechanical Settings -->
            <div class="col-12">
               <div class="text-subtitle2 text-primary q-mb-xs text-uppercase text-bold q-mt-sm">Equipment Settings</div>
               <q-separator class="q-mb-sm" />
            </div>

            <div class="col-6 col-sm-3">
              <q-input 
                v-model.number="stepForm.agitator_rpm" 
                label="Agitator RPM" 
                type="number"
                outlined 
                dense
              />
            </div>

            <div class="col-6 col-sm-3">
              <q-input 
                v-model.number="stepForm.high_shear_rpm" 
                label="High Shear RPM" 
                type="number"
                outlined 
                dense
              />
            </div>
            
             <div class="col-6 col-sm-3">
              <q-input 
                v-model.number="stepForm.step_time" 
                label="Time (Seconds)" 
                type="number"
                outlined 
                dense
                hint="Stored as seconds"
              />
            </div>
            
             <div class="col-6 col-sm-3">
              <q-input 
                 :model-value="stepForm.step_time ? (stepForm.step_time / 60).toFixed(2) : 0"
                 label="Time (Minutes)"
                 readonly
                 outlined
                 dense
                 bg-color="grey-2"
                 hint="Read-only calc"
              />
            </div>

             <!-- SECTION 5: Temperature -->
            <div class="col-12">
               <div class="text-subtitle2 text-primary q-mb-xs text-uppercase text-bold q-mt-sm">Temperature Control</div>
               <q-separator class="q-mb-sm" />
            </div>
            
             <div class="col-12 col-sm-4">
              <q-input 
                v-model.number="stepForm.temperature" 
                label="Prepare Temp (°C)" 
                type="number"
                outlined 
                dense
                step="0.1"
              />
            </div>
            
             <div class="col-6 col-sm-4">
              <q-input 
                v-model.number="stepForm.temp_low" 
                label="Offset Low" 
                type="number"
                outlined 
                dense
                step="0.1"
              />
            </div>
            
             <div class="col-6 col-sm-4">
              <q-input 
                v-model.number="stepForm.temp_high" 
                label="Offset High" 
                type="number"
                outlined 
                dense
                step="0.1"
              />
            </div>

            <!-- SECTION 6: QC & Records -->
            <div class="col-12">
              <div class="text-subtitle2 text-primary q-mb-xs text-uppercase text-bold q-mt-sm">QC & Records</div>
              <q-separator class="q-mb-sm" />
            </div>

            <div class="col-12 row q-col-gutter-sm">
               <!-- Checkboxes row -->
               <div class="col-12 row items-center q-gutter-x-md">
                   <q-checkbox v-model="stepForm.qc_temp" label="QC-Temp" dense />
                   <q-checkbox v-model="stepForm.record_steam_pressure" label="Record Steam Pressure" dense />
                   <q-checkbox v-model="stepForm.record_ctw" label="Record CTW" dense />
                   <q-checkbox v-model="stepForm.operation_brix_record" label="Op Brix Record" dense />
                   <q-checkbox v-model="stepForm.operation_ph_record" label="Op PH Record" dense />
               </div>
               
               <div class="col-12 row q-col-gutter-md q-mt-xs">
                   <div class="col-6">
                      <q-input 
                        v-model="stepForm.brix_sp" 
                        label="Brix SP" 
                        outlined 
                        dense
                      />
                   </div>
                   <div class="col-6">
                      <q-input 
                        v-model="stepForm.ph_sp" 
                        label="pH SP" 
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
          <q-btn flat label="Cancel" color="grey-7" @click="closeStepDialog" />
          <q-btn 
            unelevated 
            label="Save Step" 
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
            {{ isEditMode ? 'Edit SKU' : 'Create New SKU' }}
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div class="column q-gutter-y-lg q-pt-md">
            <q-input
              v-model="skuForm.sku_id"
              label="SKU ID *"
              outlined
              dense
              :rules="[val => !!val || 'SKU ID is required']"
              hint="Unique identifier for the SKU"
            />

            <q-input
              v-model="skuForm.sku_name"
              label="SKU Name *"
              outlined
              dense
              :rules="[val => !!val || 'SKU Name is required']"
              hint="Descriptive name for the SKU"
            />

            <div class="row q-col-gutter-x-md">
              <div class="col-6">
                <q-input
                  v-model.number="skuForm.std_batch_size"
                  label="Standard Batch Size"
                  type="number"
                  outlined
                  dense
                  hint="Default batch size"
                />
              </div>
              <div class="col-6">
                <q-select
                  v-model="skuForm.uom"
                  :options="['kg', 'L', 'unit']"
                  label="UOM"
                  outlined
                  dense
                  hint="Unit of measure"
                />
              </div>
            </div>

            <q-select
              v-model="skuForm.status"
              :options="['Active', 'Inactive']"
              label="Status"
              outlined
              dense
            />
          </div>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md q-gutter-sm">
          <q-btn
            label="CANCEL"
            color="grey-7"
            flat
            v-close-popup
            class="q-px-md"
          />
          <q-btn
            :label="isEditMode ? 'SAVE CHANGES' : 'CREATE SKU'"
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
            Duplicate SKU: {{ duplicateForm.source_sku_id }}
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="q-pt-md">
          <div class="text-subtitle2 text-grey-7 q-mb-md">
            This will copy all production steps and settings from the source SKU to the new one.
          </div>
          
          <div class="q-gutter-y-md">
            <q-input
              v-model="duplicateForm.new_sku_id"
              label="New SKU ID *"
              outlined
              dense
              autofocus
              :rules="[val => !!val || 'New SKU ID is required']"
              hint="Unique identifier for the new SKU"
            />

            <q-input
              v-model="duplicateForm.new_sku_name"
              label="New SKU Name *"
              outlined
              dense
              :rules="[val => !!val || 'New SKU Name is required']"
              hint="Descriptive name for the new SKU"
            />
          </div>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md q-gutter-sm">
          <q-btn
            label="CANCEL"
            color="grey-7"
            flat
            v-close-popup
            class="q-px-md"
          />
          <q-btn
            label="DUPLICATE SKU"
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
            Manage Actions
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
             <q-btn v-if="isActionEdit" label="CANCEL EDIT" flat color="grey-7" @click="openActionDialog" />
             <q-btn :label="isActionEdit ? 'UPDATE ACTION' : 'ADD ACTION'" color="positive" unelevated :loading="isSavingAction" @click="saveAction" />
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
          <q-btn flat label="CLOSE" color="grey-7" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- SKU Phase Dialog -->
    <q-dialog v-model="showPhaseDialog">
      <q-card style="min-width: 500px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            <q-icon name="layers" color="positive" class="q-mr-sm" />
            Manage Phases
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
             <q-btn v-if="editingPhase" label="CANCEL EDIT" flat color="grey-7" @click="openPhaseDialog" />
             <q-btn :label="editingPhase ? 'UPDATE PHASE' : 'ADD PHASE'" color="positive" unelevated @click="savePhase" />
           </div>

           <q-separator class="q-mb-md" />
           
           <div class="row items-center q-mb-sm">
             <div class="text-subtitle2 text-grey-8 uppercase text-bold">Existing Phases</div>
             <q-space />
             <q-btn flat round dense icon="refresh" color="primary" @click="fetchPhases" :loading="isLoading" size="sm">
               <q-tooltip>Refresh Phases</q-tooltip>
             </q-btn>
           </div>

           <q-input 
             v-model="phaseSearch" 
             placeholder="Filter phases..." 
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
          <q-btn flat label="CLOSE" color="grey-7" v-close-popup />
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

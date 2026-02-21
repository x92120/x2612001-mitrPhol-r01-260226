<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import type { QTableColumn } from 'quasar'
import { useQuasar, exportFile } from 'quasar'
import { appConfig } from '~/appConfig/config'
import { useAuth } from '~/composables/useAuth'
import { useMqttLocalDevice } from '~/composables/useMqttLocalDevice'

const { isConnected: mqttConnected } = useMqttLocalDevice()

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

interface IngredientIntakeHistory {
  id: number
  action: string
  old_status?: string
  new_status?: string
  remarks?: string
  update_by: string
  update_at: string
}

interface IngredientIntake {
  id: number
  intake_lot_id: string
  lot_id: string
  intake_from?: string
  intake_to?: string
  mat_sap_code: string
  re_code?: string
  material_description?: string
  uom?: string
  intake_vol: number
  remain_vol: number
  intake_package_vol?: number
  package_intake?: number
  expire_date?: string
  status: string
  intake_at: string
  intake_by: string
  edit_at?: string
  edit_by?: string
  history?: IngredientIntakeHistory[]
  packages?: { package_no: number, weight: number }[]
  po_number?: string
  manufacturing_date?: string
}

const $q = useQuasar()
const { getAuthHeader, user } = useAuth()
const { t } = useI18n()

// Scanner input ref (keyboard emulator mode)
const ingredientCodeRef = ref<any>(null)
const scannerReady = ref(true)

const intakeFrom = ref('')
const intakeTo = ref('')
const intakeFromOptions = ref<{ label: string, value: string }[]>([])
const intakeToOptions = ref<{ label: string, value: string }[]>([])
const lotNumber = ref('')
const expireDate = ref('')
const ingredientId = ref('')
const xIngredientName = ref('')
const xMatSapCode = ref('')
const xReCode = ref('')
const intakeVol = ref('')
const packageVol = ref('')
const numberOfPackages = ref('')
const manufacturingDate = ref('')
const poNumber = ref('')
const intakeLotId = ref('') // Manual or Auto-generated ID
const showIngredientDialog = ref(false)
const showIntakeFromDialog = ref(false)
const showIntakeToDialog = ref(false)
const intakeFromList = ref<any[]>([])
const intakeToList = ref<any[]>([])
const newIntakeFromName = ref('')
const newIntakeToId = ref('')
const newIntakeToName = ref('')
const tempIngredientId = ref('')

// Editing state
const isEditing = ref(false)
const editId = ref<number | null>(null)
const originalRemainVol = ref<number | null>(null)
const originalStatus = ref<string>('Active')

// Handle barcode scanner input (keyboard emulator sends chars + Enter)
const onScannerEnter = () => {
  const code = ingredientId.value?.trim()
  if (code) {
    lookupIngredient(code)
  }
}

// Focus the scanner input field
const focusScannerInput = () => {
  nextTick(() => {
    ingredientCodeRef.value?.focus()
  })
}

const columns = computed<QTableColumn[]>(() => [
  { name: 'expand', label: '', field: 'expand', align: 'center' },
  { name: 'id', align: 'center', label: 'ID', field: 'id', sortable: true },
  { name: 'intake_lot_id', align: 'center', label: t('ingredient.intakeLotId'), field: 'intake_lot_id', sortable: true },
  { name: 'intake_from', align: 'center', label: 'Intake From', field: 'intake_from', sortable: true },
  { name: 'lot_id', align: 'center', label: t('ingredient.lotId'), field: 'lot_id', sortable: true },
  { name: 'mat_sap_code', align: 'center', label: t('ingredient.matSapCode'), field: 'mat_sap_code', sortable: true },
  { name: 're_code', align: 'center', label: t('ingredient.reCode'), field: 're_code', sortable: true },
  { name: 'material_description', align: 'left', label: t('ingredient.materialDesc'), field: 'material_description', sortable: true },
  { name: 'uom', align: 'center', label: t('ingredient.uom'), field: 'uom', sortable: true },
  { name: 'intake_vol', align: 'center', label: t('ingredient.intakeVolume'), field: 'intake_vol', sortable: true, format: (val: number) => val?.toFixed(4) || '-' },
  { name: 'remain_vol', align: 'center', label: t('ingredient.remainVolume'), field: 'remain_vol', sortable: true, classes: 'text-negative text-weight-bold', format: (val: number) => val?.toFixed(4) || '-' },
  { name: 'intake_package_vol', align: 'center', label: t('ingredient.pkgVol'), field: 'intake_package_vol', sortable: true, format: (val: number) => val?.toFixed(4) || '-' },
  { name: 'package_intake', align: 'center', label: t('ingredient.pkgs'), field: 'package_intake', sortable: true },
  { name: 'expire_date', align: 'center', label: t('ingredient.expiryDate'), field: 'expire_date', sortable: true, format: (val: string) => formatDate(val) },
  { name: 'po_number', align: 'center', label: t('ingredient.poNo'), field: 'po_number', sortable: true },
  { name: 'manufacturing_date', align: 'center', label: t('ingredient.mfgDate'), field: 'manufacturing_date', sortable: true, format: (val: string) => formatDate(val) },
  { name: 'intake_at', align: 'center', label: t('ingredient.intakeAt'), field: 'intake_at', sortable: true, format: (val: string) => formatDateTime(val) },
  { name: 'status', align: 'center', label: t('common.status'), field: 'status', sortable: true },
  { name: 'xActions', align: 'center', label: t('common.actions'), field: 'xActions' },
])

const showDetailDialog = ref(false)
const selectedRecord = ref<IngredientIntake | null>(null)

const openDetailDialog = (row: IngredientIntake) => {
  selectedRecord.value = row
  showDetailDialog.value = true
}

// Data from API
const rows = ref<IngredientIntake[]>([])
const isLoading = ref(false)
const showAll = ref(false)

// Helper for fetch headers to keep TS happy
const getHeaders = (extraHeaders: Record<string, string> = {}) => {
  const authHeader = getAuthHeader() as Record<string, string>
  return { ...authHeader, ...extraHeaders }
}

const fetchIntakeFromOptions = async () => {
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/intake-from/`, {
      headers: getAuthHeader() as Record<string, string>,
    })
    intakeFromOptions.value = data.map(item => ({
      label: item.name,
      value: item.name
    }))
    intakeFromList.value = data
  } catch (error) {
    console.error('Failed to fetch intake-from:', error)
  }
}

const fetchIntakeToOptions = async () => {
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/warehouses/`, {
      headers: getAuthHeader() as Record<string, string>,
    })
    intakeToOptions.value = data.map(item => ({
      label: `${item.warehouse_id} - ${item.name}`,
      value: item.warehouse_id
    }))
    intakeToList.value = data
  } catch (error) {
    console.error('Failed to fetch warehouses:', error)
  }
}

const addIntakeFrom = async () => {
  if (!newIntakeFromName.value) return
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/intake-from/`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ name: newIntakeFromName.value }),
    })
    if (response.ok) {
      newIntakeFromName.value = ''
      await fetchIntakeFromOptions()
    }
  } catch (err) {
    console.error('Failed to add intake source:', err)
  }
}

const deleteIntakeFrom = async (id: number) => {
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/intake-from/${id}`, {
      method: 'DELETE',
      headers: getAuthHeader() as Record<string, string>,
    })
    if (response.ok) {
      await fetchIntakeFromOptions()
    }
  } catch (err) {
    console.error('Failed to delete intake source:', err)
  }
}

const addWarehouse = async () => {
  if (!newIntakeToName.value || !newIntakeToId.value) return
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/warehouses/`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ 
        warehouse_id: newIntakeToId.value.toUpperCase(),
        name: newIntakeToName.value,
        description: 'Added via Intake page'
      }),
    })
    if (response.ok) {
      newIntakeToName.value = ''
      newIntakeToId.value = ''
      await fetchIntakeToOptions()
    }
  } catch (err) {
    console.error('Failed to add warehouse:', err)
  }
}

const deleteWarehouse = async (id: string) => {
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/warehouses/${id}`, {
      method: 'DELETE',
      headers: getAuthHeader() as Record<string, string>,
    })
    if (response.ok) {
      await fetchIntakeToOptions()
    }
  } catch (err) {
    console.error('Failed to delete warehouse:', err)
  }
}

// Fetch Receipt History
const fetchReceipts = async (isBackground = false) => {
  if (!isBackground) isLoading.value = true
  try {
    const data = await $fetch<IngredientIntake[]>(`${appConfig.apiBaseUrl}/ingredient-intake-lists/`, {
      headers: getAuthHeader() as Record<string, string>,
    })
    if (JSON.stringify(data) !== JSON.stringify(rows.value)) {
      rows.value = data
    }
  } catch (error) {
    console.error('Failed to fetch history:', error)
  } finally {
    if (!isBackground) isLoading.value = false
  }
}

// Lookup Ingredient by ID or blind code
const lookupIngredient = async (query: string) => {
  if (!query || query.length < 3) {
    xIngredientName.value = xMatSapCode.value = xReCode.value = ''
    return
  }

  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/ingredients/?lookup=${query}`, {
      headers: getAuthHeader() as Record<string, string>,
    })

    if (data.length > 0) {
      const ingredient = data[0]
      xIngredientName.value = ingredient.name
      xMatSapCode.value = ingredient.mat_sap_code
      xReCode.value = ingredient.re_code || ''

      if (ingredientId.value !== ingredient.ingredient_id) {
        ingredientId.value = ingredient.ingredient_id
        intakeVol.value = ''
        packageVol.value = Number(ingredient.std_package_size || 25).toFixed(4)
        intakeFrom.value = 'Warehouse' // Default
      }

      $q.notify({
        type: 'positive',
        message: `Found: ${ingredient.name}`,
        position: 'top',
        timeout: 1000,
      })
    } else {
      xIngredientName.value = xMatSapCode.value = xReCode.value = ''
    }
  } catch (error) {
    console.error('Lookup error:', error)
  }
}

// Automatic lookup as they type/scan
let lookupTimeout: any = null
watch(ingredientId, (newId) => {
  if (lookupTimeout) clearTimeout(lookupTimeout)
  lookupTimeout = setTimeout(() => {
    // Only lookup if we have a value.
    // Optimization: if the current value matches the already found ingredient ID, maybe don't re-lookup?
    // But simplest is to just lookup.
    if (newId) lookupIngredient(newId)
  }, 500) // Increased debounce slightly
})

// Auto-calculate Number of Packages and Sync Remain Vol
watch([intakeVol, packageVol], ([newVol, newPkg]) => {
  // Only auto-sync remain vol if we are NOT editing, or if the user wants it...
  // Usually, if you edit a record, remain_vol might have changed due to consumption.
  // But for now, let's keep the sync behavior simple: if creating new, sync.
  // Only auto-sync remain vol if we are NOT editing, or if the user wants it...
  // Usually, if you edit a record, remain_vol might have changed due to consumption.
  // But for now, let's keep the sync behavior simple: if creating new, sync.
  // remainVol logic removed per request

  const vol = parseFloat(newVol)
  const pkg = parseFloat(newPkg)

  if (!isNaN(vol) && !isNaN(pkg) && pkg > 0) {
    numberOfPackages.value = Math.ceil(vol / pkg).toString()
  } else {
    numberOfPackages.value = ''
  }
})

// Generate new Intake Lot ID
const generateIntakeLotId = async () => {
  try {
    const data = await $fetch<{next_id: string}>(`${appConfig.apiBaseUrl}/ingredient-intake-next-id`)
    intakeLotId.value = data.next_id
  } catch (e: any) {
    console.error('Failed to generate ID', e)
    intakeLotId.value = 'Error: ' + e.message
  }
}

const isSaving = ref(false)

// Save Receipt (Create or Update)
const onSave = async () => {
  // Detailed Validation
  const missingFields: string[] = []
  if (!ingredientId.value && !xMatSapCode.value) missingFields.push('Ingredient ID')
  if (!lotNumber.value) missingFields.push('Lot Number')
  if (!intakeFrom.value) missingFields.push('Intake From')
  if (!intakeVol.value) missingFields.push('Intake Volume')
  if (!expireDate.value) missingFields.push('Expire Date')

  if (missingFields.length > 0) {
    $q.notify({
      type: 'negative',
      message: `${t('ingredient.enterData')}: ${missingFields.join(', ')}`,
      position: 'top',
    })
    return
  }

  // Logical Validation
  const rVol = parseFloat(intakeVol.value)
  if (isNaN(rVol) || rVol <= 0) {
    $q.notify({
      type: 'negative',
      message: t('ingredient.volPositive'),
      position: 'top',
    })
    return
  }

  if (packageVol.value) {
    const pVol = parseFloat(packageVol.value)
    if (isNaN(pVol) || pVol <= 0) {
      $q.notify({
        type: 'negative',
        message: t('ingredient.pkgPositive'),
        position: 'top',
      })
      return
    }
  }

  $q.dialog({
    title: t('ingredient.confirmSave'),
    message: isEditing.value
      ? t('ingredient.confirmSaveUpdate')
      : t('ingredient.confirmSaveNew'),
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    isSaving.value = true

    const payload = {
      intake_lot_id: intakeLotId.value,
      lot_id: lotNumber.value,
      intake_from: intakeFrom.value,
      intake_to: intakeTo.value,
      mat_sap_code: xMatSapCode.value,
      re_code: xReCode.value,
      material_description: xIngredientName.value,
      uom: 'kg', // Default or from lookup
      intake_vol: parseFloat(intakeVol.value),
      remain_vol:
        isEditing.value && originalRemainVol.value !== null
          ? originalRemainVol.value
          : parseFloat(intakeVol.value),
      intake_package_vol: packageVol.value ? parseFloat(packageVol.value) : null,
      package_intake: numberOfPackages.value ? parseInt(numberOfPackages.value) : null,
      expire_date: expireDate.value ? formatDateToApi(expireDate.value) : null,
      status: isEditing.value ? originalStatus.value : 'Active',
      intake_by: user.value?.username || 'cj',
      edit_by: user.value?.username || 'cj',
      manufacturing_date: manufacturingDate.value ? formatDateToApi(manufacturingDate.value) : null,
      po_number: poNumber.value || null,
    }

    try {
      let response
      if (isEditing.value && editId.value) {
        // Update
        response = await fetch(`${appConfig.apiBaseUrl}/ingredient-intake-lists/${editId.value}`, {
          method: 'PUT',
          headers: getHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify(payload),
        })
      } else {
        // Create
        response = await fetch(`${appConfig.apiBaseUrl}/ingredient-intake-lists/`, {
          method: 'POST',
          headers: getHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify(payload),
        })
      }

      if (response.ok) {
        const savedRecord = await response.json()

        $q.notify({
          type: 'positive',
          message: isEditing.value
            ? t('ingredient.updatedSuccess')
            : t('ingredient.savedSuccess'),
          position: 'top',
          icon: 'check_circle',
        })

        // Auto-print label for new intakes
        if (!isEditing.value) {
          printLabel(savedRecord)
        }

        onClear()
        await fetchReceipts()
      } else {
        const error = await response.json()
        $q.notify({
          type: 'negative',
          message: `${t('common.error')}: ${error.detail || t('ingredient.saveFailed')}`,
          position: 'top',
        })
      }
    } catch (error) {
      console.error('Save error:', error)
      $q.notify({
        type: 'negative',
        message: t('ingredient.networkError'),
        position: 'top',
      })
    } finally {
      isSaving.value = false
    }
  })
}

// Prepare Edit
const onEdit = (row: IngredientIntake) => {
  isEditing.value = true
  editId.value = row.id

  // Populate form
  intakeLotId.value = row.intake_lot_id
  lotNumber.value = row.lot_id
  intakeFrom.value = row.intake_from || ''
  intakeTo.value = row.intake_to || ''
  xMatSapCode.value = row.mat_sap_code
  xReCode.value = row.re_code || ''
  intakeVol.value = row.intake_vol.toString()
  // remainVol removed
  packageVol.value = row.intake_package_vol ? row.intake_package_vol.toString() : ''
  numberOfPackages.value = row.package_intake ? row.package_intake.toString() : ''
  expireDate.value = row.expire_date ? formatDateForInput(row.expire_date) : ''
  manufacturingDate.value = row.manufacturing_date ? formatDateForInput(row.manufacturing_date) : ''
  poNumber.value = row.po_number || ''

  // We need to fetch ingredient details to show name and fill ingredientId
  // We can just call lookup
  lookupIngredient(row.mat_sap_code)

  // Store original values
  originalRemainVol.value = row.remain_vol
  originalStatus.value = row.status
}

// Reject Intake (Successively replaces Cancel/Delete)
const onRejectIntake = async (row: IngredientIntake) => {
  $q.dialog({
    title: t('ingredient.confirmReject'),
    message: `${t('ingredient.rejectPrompt')} ${row.intake_lot_id}?`,
    cancel: true,
    persistent: true,
    prompt: {
      model: '',
      type: 'text',
      label: t('ingredient.rejectReason'),
      outlined: true,
    },
  }).onOk(async (remarks: string) => {
    try {
      const response = await fetch(`${appConfig.apiBaseUrl}/ingredient-intake-lists/${row.id}`, {
        method: 'PUT',
        headers: getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          ...row,
          status: 'Reject',
          remarks: remarks || 'Rejected by user',
          edit_by: user.value?.username || 'system',
        }),
      })
      if (response.ok) {
        $q.notify({ type: 'warning', message: t('ingredient.rejected') })
        fetchReceipts()
      } else {
        const err = await response.json()
        $q.notify({ type: 'negative', message: `${t('ingredient.rejectFailed')}: ${err.detail || 'Unknown error'}` })
      }
    } catch (error) {
      console.error('Reject error:', error)
      $q.notify({ type: 'negative', message: t('ingredient.networkRejectError') })
    }
  })
}



// Initialize
// Filtering state
const filters = ref<Record<string, string>>({})
const showFilters = ref(false) // Toggle filters if needed

// Computed filtered rows
const filteredRows = computed(() => {
  let filtered = rows.value

  // Filter out Cancelled and Reject if showAll is false
  if (!showAll.value) {
    filtered = filtered.filter((row) => row.status !== 'Cancelled' && row.status !== 'Reject')
  }

  // Filter by columns
  return filtered.filter((row) => {
    return Object.keys(filters.value).every((key) => {
      const filterVal = filters.value[key]?.toLowerCase()
      if (!filterVal) return true

      // Access property safely via any cast since column field matches data key
      const rowVal = String((row as any)[key] || '').toLowerCase()
      return rowVal.includes(filterVal)
    })
  })
})

// Auto-refresh timer
let refreshInterval: any = null

const allIngredients = ref<any[]>([])
const ingredientOptions = ref<any[]>([])

const fetchAllIngredients = async () => {
  try {
    const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/ingredients/`, {
      headers: getAuthHeader() as Record<string, string>,
    })
    allIngredients.value = data
  } catch (error) {
    console.error('Failed to fetch all ingredients:', error)
  }
}

const filterIngredients = (val: string, update: (callback: () => void) => void) => {
  if (val === '') {
    update(() => {
      ingredientOptions.value = allIngredients.value
    })
    return
  }
  update(() => {
    const needle = val.toLowerCase()
    ingredientOptions.value = allIngredients.value.filter(
      v => 
        (v.ingredient_id && v.ingredient_id.toLowerCase().includes(needle)) || 
        (v.name && v.name.toLowerCase().includes(needle)) ||
        (v.mat_sap_code && String(v.mat_sap_code).toLowerCase().includes(needle))
    )
  })
}

onMounted(() => {
  fetchReceipts()
  generateIntakeLotId() // Generate initial ID
  fetchAllIngredients() // Fetch list of ingredients for the autocomplete dropdown
  fetchIntakeFromOptions()
  fetchIntakeToOptions()

  // Auto-focus scanner input on mount
  focusScannerInput()

  // Auto-refresh every 5 seconds
  refreshInterval = setInterval(() => {
    fetchReceipts(true)
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})

const onClear = () => {
  isEditing.value = false
  editId.value = null
  ingredientId.value = ''
  lotNumber.value = ''
  expireDate.value = ''
  manufacturingDate.value = ''
  poNumber.value = ''
  xIngredientName.value = ''
  xMatSapCode.value = ''
  xReCode.value = ''
  intakeVol.value = ''
  // remainVol removed
  packageVol.value = ''
  numberOfPackages.value = ''
  intakeFrom.value = ''
  intakeTo.value = ''
  originalRemainVol.value = null
  originalStatus.value = 'Active'
  generateIntakeLotId() // Get fresh ID after clear/save
  focusScannerInput() // Re-focus for next scan
}

// Open dialog to enter ingredient code
const openIngredientDialog = () => {
  tempIngredientId.value = ingredientId.value
  showIngredientDialog.value = true
}

// Confirm ingredient code from dialog
const confirmIngredientCode = () => {
  const val = tempIngredientId.value
  if (val) {
    ingredientId.value = val
    showIngredientDialog.value = false
    lookupIngredient(val)
  }
}

// Cancel dialog
const cancelIngredientDialog = () => {
  tempIngredientId.value = ''
  showIngredientDialog.value = false
}

// Status options
const statusOptions = ['Active', 'Hold', 'Reject']

// Status badge helper
const getStatusColor = (status: string) => {
  switch (status) {
    case 'Active':
      return 'positive'
    case 'Hold':
      return 'warning'
    case 'Reject':
      return 'negative'
    case 'Cancelled':
      return 'grey-7'
    default:
      return 'grey'
  }
}

// Update record status only
const updateRecordStatus = async (row: IngredientIntake, newStatus: string) => {
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/ingredient-intake-lists/${row.id}`, {
      method: 'PUT',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        ...row,
        status: newStatus,
        edit_by: user.value?.username || 'system',
      }),
    })

    if (response.ok) {
      $q.notify({
        type: 'positive',
        message: `${t('ingredient.statusUpdated')} ${newStatus}`,
        timeout: 1000,
      })
      if (selectedRecord.value && selectedRecord.value.id === row.id) {
        selectedRecord.value.status = newStatus
      }
      fetchReceipts() // Refresh table
    } else {
      throw new Error('Failed to update status')
    }
  } catch (error) {
    console.error('Error updating status:', error)
    $q.notify({
      type: 'negative',
      message: t('ingredient.statusUpdateFailed'),
    })
  }
}

// Print Label Function — offline-safe using local qrcode package
const { generateQrDataUrl } = useQrCode()

const printLabel = async (record: IngredientIntake) => {
  // Always recreate iframe to ensure window.onload fires correctly
  const existingIframe = document.getElementById('print-iframe')
  if (existingIframe) {
    document.body.removeChild(existingIframe)
  }

  const iframe = document.createElement('iframe')
  iframe.id = 'print-iframe'
  iframe.style.position = 'fixed'
  iframe.style.right = '0'
  iframe.style.bottom = '0'
  iframe.style.width = '1px' // Non-zero size to ensure rendering
  iframe.style.height = '1px'
  iframe.style.border = '0'
  iframe.style.opacity = '0.01'
  document.body.appendChild(iframe)

  const templateResponse = await fetch('/labels/ingredient_intake-label.svg')
  const templateStr = await templateResponse.text()

  const numPackages = record.package_intake || 1
  let labelsHtml = ''

  for (let i = 1; i <= numPackages; i++) {
    // Determine the weight for this specific package
    let currentPkgVol = record.intake_package_vol || 0
    if (record.packages && record.packages.length > 0) {
      const pkgRec = record.packages.find(p => p.package_no === i)
      if (pkgRec) currentPkgVol = pkgRec.weight
    } else {
      // On-the-fly calculation if not from DB (e.g. just saved)
      const isLast = i === numPackages
      if (isLast && record.intake_package_vol) {
        currentPkgVol = record.intake_vol - (record.intake_package_vol * (numPackages - 1))
      }
    }

    // Construct full data object for QR
    const qrData = {
      intake_lot_id: record.intake_lot_id,
      lot_id: record.lot_id,
      mat_sap_code: record.mat_sap_code,
      re_code: record.re_code,
      intake_package_vol: currentPkgVol,
      package_no: i,
      total_packages: numPackages,
      expire_date: record.expire_date?.split('T')[0],
      intake_at: record.intake_at?.split('T')[0],
    }
    const qrString = JSON.stringify(qrData)

    // Generate QR codes locally
    const qrLarge = await generateQrDataUrl(qrString, 150)

    let formattedSvg = templateStr
      .replace(/\{\{IntakeLotId\}\}/g, record.intake_lot_id || '-')
      .replace(/\{\{ReCode\}\}/g, record.re_code || '-')
      .replace(/\{\{MatSapCode\}\}/g, record.mat_sap_code || '-')
      .replace(/\{\{SupplierLot\}\}/g, record.lot_id || '-')
      .replace(/\{\{ExpireDate\}\}/g, formatDate(record.expire_date))
      .replace(/\{\{MenufacturingDate\}\}/g, formatDate(record.manufacturing_date))
      .replace(/\{\{PackageString\}\}/g, `${i} / ${numPackages}`)
      .replace(/\{\{IntakeVol\}\}/g, record.intake_vol?.toFixed(4) || '0.0000')
      .replace(/\{\{PackageVol\}\}/g, currentPkgVol.toFixed(4) || '0.0000')
      .replace(/\{\{QRCode\}\}/g, `<image href="${qrLarge}" x="18.9" y="115.2" width="134" height="134" />`)
      .replace(/\{\{Operator\}\}/g, record.intake_by || 'Operator')
      .replace(/\{\{Timestamp\}\}/g, new Date().toLocaleString('en-GB'))

    // Replace fixed width/height in SVG with 100% so it scales to container via viewBox
    formattedSvg = formattedSvg.replace(/(<svg[\s\S]*?)width="[^"]*"/, '$1width="100%"')
                               .replace(/(<svg[\s\S]*?)height="[^"]*"/, '$1height="100%"')

    labelsHtml += `<div class="label-container">${formattedSvg}</div>`
  }

  const html = `
    <html>
      <head>
        <title>Print Labels - ${record.intake_lot_id}</title>
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
            page-break-after: always;
            overflow: hidden;
          }
          .label-container svg {
            width: 4in;
            height: 6in;
            display: block;
          }
        </style>
      </head>
      <body>
        ${labelsHtml}
      </body>
    </html>
  `

  // Use parent-side onload handler for better reliability
  iframe.onload = () => {
    setTimeout(() => {
      if (iframe.contentWindow) {
        iframe.contentWindow.focus()
        iframe.contentWindow.print()
      }
    }, 500)
  }

  const doc = iframe.contentWindow?.document
  if (doc) {
    doc.open()
    doc.write(html)
    doc.close()
  }
}

/**
 * Print a single label for a specific package from the expanded list
 */
const printSinglePackageLabel = async (record: IngredientIntake, pkg: { package_no: number, weight: number }) => {
  const numPackages = record.package_intake || 1
  const templateResponse = await fetch('/labels/ingredient_intake-label.svg')
  const templateStr = await templateResponse.text()
  
  // Construct full data object for QR
  const qrData = {
    intake_lot_id: record.intake_lot_id,
    lot_id: record.lot_id,
    mat_sap_code: record.mat_sap_code,
    re_code: record.re_code,
    intake_package_vol: pkg.weight,
    package_no: pkg.package_no,
    total_packages: numPackages,
    expire_date: record.expire_date?.split('T')[0],
    intake_at: record.intake_at?.split('T')[0],
  }
  const qrString = JSON.stringify(qrData)
  const qrLarge = await generateQrDataUrl(qrString, 150)

  let formattedSvg = templateStr
    .replace(/\{\{IntakeLotId\}\}/g, record.intake_lot_id || '-')
    .replace(/\{\{ReCode\}\}/g, record.re_code || '-')
    .replace(/\{\{MatSapCode\}\}/g, record.mat_sap_code || '-')
    .replace(/\{\{SupplierLot\}\}/g, record.lot_id || '-')
    .replace(/\{\{ExpireDate\}\}/g, formatDate(record.expire_date))
    .replace(/\{\{MenufacturingDate\}\}/g, formatDate(record.manufacturing_date))
    .replace(/\{\{PackageString\}\}/g, `${pkg.package_no} / ${numPackages}`)
    .replace(/\{\{IntakeVol\}\}/g, record.intake_vol?.toFixed(4) || '0.0000')
    .replace(/\{\{PackageVol\}\}/g, pkg.weight.toFixed(4) || '0.0000')
    .replace(/\{\{QRCode\}\}/g, `<image href="${qrLarge}" x="18.9" y="115.2" width="134" height="134" />`)
    .replace(/\{\{Operator\}\}/g, record.intake_by || 'Operator')
    .replace(/\{\{Timestamp\}\}/g, new Date().toLocaleString('en-GB'))

  // Replace fixed width/height in SVG with 100%
  formattedSvg = formattedSvg.replace(/(<svg[\s\S]*?)width="[^"]*"/, '$1width="100%"')
                             .replace(/(<svg[\s\S]*?)height="[^"]*"/, '$1height="100%"')

  const labelsHtml = `<div class="label-container">${formattedSvg}</div>`
  
  // Create iframe for printing
  const iframe = document.createElement('iframe')
  iframe.style.display = 'none'
  document.body.appendChild(iframe)

  const html = `
    <html>
      <head>
        <title>Print Label - ${record.intake_lot_id} - Pkg ${pkg.package_no}</title>
        <style>
          @page { size: 4in 6in; margin: 0; }
          body { margin: 0; padding: 0; background: white; }
          .label-container { 
            width: 4in; height: 6in; 
            overflow: hidden;
          }
          .label-container svg { width: 4in; height: 6in; display: block; }
        </style>
      </head>
      <body>
        ${labelsHtml}
      </body>
    </html>
  `

  iframe.onload = () => {
    setTimeout(() => {
      if (iframe.contentWindow) {
        iframe.contentWindow.focus()
        iframe.contentWindow.print()
        setTimeout(() => document.body.removeChild(iframe), 1000)
      }
    }, 500)
  }

  const doc = iframe.contentWindow?.document
  if (doc) {
    doc.open()
    doc.write(html)
    doc.close()
  }
}

// Helper to check if column can be filtered (field is string)
const isStringField = (val: any): val is string => typeof val === 'string'

const resetFilters = () => {
  filters.value = {}
}

function wrapCsvValue(val: any, formatFn?: (v: any, r?: any) => string, row?: any, forceString: boolean = false) {
  let formatted = formatFn ? formatFn(val, row) : val
  formatted = formatted === void 0 || formatted === null ? '' : String(formatted)

  formatted = formatted.split('"').join('""')
  
  // Force Excel to treat as string if requested (e.g. for codes with leading zeros)
  if (forceString) {
    return `="${formatted}"`
  }
  return `"${formatted}"`
}

const exportTable = () => {
  // naive encoding to csv format
  const columnsToExport = columns.value.filter((col: QTableColumn) => col.name !== 'xActions')
  
  // Columns that should be forced as strings in Excel to preserve format (e.g. 00123)
  const stringCols = ['mat_sap_code', 're_code', 'lot_id', 'intake_lot_id', 'ingredient_id', 'po_number']

  const content = [columnsToExport.map((col) => wrapCsvValue(col.label))]
    .concat(
      filteredRows.value.map((row) =>
        columnsToExport
          .map((col) =>
            wrapCsvValue(
              typeof col.field === 'function'
                ? col.field(row)
                : row[col.field as keyof IngredientIntake],
              col.format,
              row,
              stringCols.includes(col.name)
            ),
          )
          .join(','),
      ),
    )
    .join('\r\n')

  const status = exportFile('ingredient-intake-export.csv', '\uFEFF' + content, 'text/csv')

  if (status !== true) {
    $q.notify({
      message: t('ingredient.downloadDenied'),
      color: 'negative',
      icon: 'warning',
    })
  }
}

// Import Logic
const fileInput = ref<HTMLInputElement | null>(null)

const importTable = () => {
  fileInput.value?.click()
}

const onFileSelected = async (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const selectedFile = target.files[0]
    if (selectedFile) {
      // Create FormData
      const formData = new FormData()
      formData.append('file', selectedFile)

      try {
        $q.loading.show({ message: t('ingredient.importingData') })
        
        const response = await fetch(`${appConfig.apiBaseUrl}/ingredient-intake-lists/bulk-import`, {
          method: 'POST',
          headers: getAuthHeader() as Record<string, string>, // Do not set Content-Type for FormData
          body: formData,
        })

      if (response.ok) {
        const result = await response.json()
        if (result.errors && result.errors.length > 0) {
           $q.notify({
            type: 'warning',
            message: `Imported ${result.imported_count} records with some errors.`,
            caption: result.errors[0], // Show first error
            timeout: 5000
          })
        } else {
           $q.notify({
            type: 'positive',
            message: `Successfully imported ${result.imported_count} records.`,
            position: 'top'
          })
        }
        fetchReceipts()
      } else {
        const err = await response.json()
        throw new Error(err.detail || 'Import failed')
      }
    } catch (error: any) {
      console.error('Import error:', error)
      $q.notify({
        type: 'negative',
        message: error.message || 'Failed to import CSV',
        position: 'top'
      })
    } finally {
      $q.loading.hide()
      // Reset input
      target.value = ''
    }
  }
}

}
// Closing brace added to fix unmatched opening in onFileSelected
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
          <q-btn icon="save" round flat text-color="white" @click="onSave" :loading="isSaving" title="Save Intake" />
          <q-btn icon="clear_all" round flat text-color="white" @click="onClear" title="Clear Form" />
        </div>
      </div>
    </div>
    <!-- Ingredient Intake Form -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <q-card class="shadow-1">
          <q-form class="q-pa-md">
            <!-- Row 1: Intake ID + Ingredient ID + MAT SAP + Re-Code -->
            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-3">
                <q-input
                  outlined
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
                  v-model="xMatSapCode"
                  :label="t('ingredient.matSapCode')"
                  readonly
                  bg-color="grey-2"
                />
              </div>
              <div class="col-12 col-md-3">
                <q-input outlined v-model="xReCode" :label="t('ingredient.reCode')" readonly bg-color="grey-2" />
              </div>
            </div>

            <!-- Row 1.5: Ingredient Name, Mfg Date, Expire Date -->
            <div class="row q-col-gutter-md q-mt-sm">
                <div class="col-12 col-md-6">
                     <q-input
                        outlined
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
              <div class="col-12 col-md-2">
                <q-input outlined v-model="manufacturingDate" :label="t('ingredient.manufacturingDate')" mask="##/##/####" placeholder="DD/MM/YYYY">
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
              <div class="col-12 col-md-2">
                <q-input outlined v-model="expireDate" :label="t('ingredient.expiryDate') + ' *'" mask="##/##/####" placeholder="DD/MM/YYYY">
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
            <div class="row q-col-gutter-md q-mt-sm">
              <div class="col-12 col-md-3">
                <q-select
                  outlined
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
                <q-input outlined v-model="lotNumber" :label="t('ingredient.lotNumber') + ' *'" />
              </div>
              <div class="col-12 col-md-3">
                <q-input outlined v-model="poNumber" :label="t('ingredient.poNumber')" />
              </div>
            </div>

            <div class="row q-col-gutter-md q-mt-sm">
              <div class="col-12 col-md-3">
                <q-input outlined v-model="intakeVol" :label="t('ingredient.intakeVolume') + ' *'" />
              </div>
              <div class="col-12 col-md-3">
                <q-input outlined v-model="packageVol" :label="t('ingredient.packageVol')" />
              </div>
              <div class="col-12 col-md-3">
                <q-input
                  outlined
                  v-model="numberOfPackages"
                  :label="t('ingredient.numPackages')"
                  readonly
                  bg-color="grey-2"
                  input-class="text-right"
                />
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
                      icon="settings"
                      color="primary"
                      unelevated
                      no-caps
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
                    <div class="row q-col-gutter-lg q-mb-md">
                      <div class="col-12 col-md-4">
                        <div class="text-subtitle2 q-mb-xs text-primary row items-center">
                          <q-icon name="info" class="q-mr-xs" />
                          General Info
                        </div>
                        <q-list bordered dense separator class="bg-white rounded-borders">
                          <q-item>
                            <q-item-section class="text-grey-7">{{ t('ingredient.intakeLotId') }}</q-item-section>
                            <q-item-section side class="text-weight-bold">{{ props.row.intake_lot_id }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">Material</q-item-section>
                            <q-item-section side>{{ props.row.material_description }}</q-item-section>
                          </q-item>
                          <q-item>
                            <q-item-section class="text-grey-7">RE Code</q-item-section>
                            <q-item-section side class="text-weight-bold text-blue-9">{{ props.row.re_code || '-' }}</q-item-section>
                          </q-item>
                        </q-list>
                      </div>

                      <div class="col-12 col-md-4">
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
                        </q-list>
                      </div>

                      <div class="col-12 col-md-4">
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
                    
                    <div v-else class="row q-col-gutter-sm">
                      <div v-for="pkg in [...props.row.packages].sort((a, b) => a.package_no - b.package_no)" :key="pkg.id || pkg.package_no" class="col-12">
                        <q-card flat bordered class="bg-white">
                          <q-item dense>
                            <q-item-section side>
                              <q-btn icon="print" flat round dense size="sm" color="primary" @click="printSinglePackageLabel(props.row, pkg)" />
                            </q-item-section>
                            <q-item-section avatar>
                              <q-avatar color="primary" text-color="white" size="xs">{{ pkg.package_no }}</q-avatar>
                            </q-item-section>
                            <q-item-section>
                              <q-item-label class="text-weight-bold">{{ pkg.weight.toFixed(4) }} kg</q-item-label>
                            </q-item-section>
                          </q-item>
                        </q-card>
                      </div>
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
                    By {{ h.update_by }} at {{ new Date(h.update_at).toLocaleString('en-GB') }}
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

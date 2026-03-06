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
  ext_date?: string
  reserv_no?: string
  stock_zone?: string
  material_type?: string
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
const extDate = ref('')
const reservNo = ref('')
const stockZone = ref('')
const materialType = ref('')
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

const testPrint1Page = () => {
  const mockRecord: any = {
    intake_lot_id: 'TEST-1PG',
    ingredient_name: 'TEST 1 PAGE',
    mat_sap_code: 'MAT-1',
    re_code: 'RE-1',
    lot_id: 'LOT-1',
    intake_date: new Date().toISOString(),
    expire_date: new Date().toISOString(),
    manufacturing_date: new Date().toISOString(),
    intake_vol: 10.0,
    package_intake: 1,
    intake_package_vol: 10.0,
    intake_by: 'tester'
  }
  printLabel(mockRecord)
}

// Temporary test function for 2-page print
const testPrint2Pages = () => {
  const mockRecord: any = {
    intake_lot_id: 'FIX-TEST-001',
    ingredient_name: 'TEST INGREDIENT 4x3',
    mat_sap_code: 'MAT12345',
    re_code: 'RE-TEST',
    lot_id: 'LOT-TEST-999',
    intake_date: new Date().toISOString(),
    expire_date: new Date().toISOString(),
    manufacturing_date: new Date().toISOString(),
    intake_vol: 50.0,
    package_intake: 2,
    intake_package_vol: 25.0,
    intake_by: user.value?.username || 'tester'
  }
  printLabel(mockRecord)
}

const columns = computed<QTableColumn[]>(() => [
  { name: 'expand', label: '', field: 'expand', align: 'center' },
  { name: 'intake_lot_id', align: 'center', label: t('ingredient.intakeLotId'), field: 'intake_lot_id', sortable: true },
  { name: 'intake_from', align: 'center', label: 'Intake From', field: 'intake_from', sortable: true },
  { name: 'intake_to', align: 'center', label: 'Intake To', field: 'intake_to', sortable: true },
  { name: 'lot_id', align: 'center', label: t('ingredient.lotId'), field: 'lot_id', sortable: true },
  { name: 'mat_sap_code', align: 'center', label: t('ingredient.matSapCode'), field: 'mat_sap_code', sortable: true },
  { name: 're_code', align: 'center', label: t('ingredient.reCode'), field: 're_code', sortable: true },
  { name: 'material_description', align: 'left', label: t('ingredient.materialDesc'), field: 'material_description', sortable: true },
  { name: 'intake_vol', align: 'center', label: t('ingredient.intakeVolume'), field: 'intake_vol', sortable: true, format: (val: number) => val?.toFixed(4) || '-' },
  { name: 'package_intake', align: 'center', label: 'Package of Intake', field: 'package_intake', sortable: true },
  { name: 'manufacturing_date', align: 'center', label: t('ingredient.mfgDate'), field: 'manufacturing_date', sortable: true, format: (val: string) => formatDate(val) },
  { name: 'expire_date', align: 'center', label: t('ingredient.expiryDate'), field: 'expire_date', sortable: true, format: (val: string) => formatDate(val) },
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
      ext_date: extDate.value ? formatDateToApi(extDate.value) : null,
      reserv_no: reservNo.value || null,
      stock_zone: stockZone.value || null,
      material_type: materialType.value || null,
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
  extDate.value = row.ext_date ? formatDateForInput(row.ext_date) : ''
  reservNo.value = row.reserv_no || ''
  stockZone.value = row.stock_zone || ''
  materialType.value = row.material_type || ''

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
  fetchAdjustments()

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
  extDate.value = ''
  reservNo.value = ''
  stockZone.value = ''
  materialType.value = ''
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

  const templateResponse = await fetch('/labels/ingredient_intake-label_4x3-r01.svg')
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

    // QR data: IntakeLotId|MatSapCode| |ReceiveDate|Q'Ty|Unit|MaterialType|MFG_Date|ExpDate
    const qrString = `${record.intake_lot_id}|${record.mat_sap_code || ''}| |${formatDate(record.intake_at)}|${currentPkgVol.toFixed(3)}|${record.uom || 'KG'}|${record.material_type || ''}|${formatDate(record.manufacturing_date)}|${formatDate(record.expire_date)}`

    // Generate QR codes locally
    const qrLarge = await generateQrDataUrl(qrString, 150)

    let formattedSvg = templateStr
      .replace(/\{\{IntakeLotId\}\}/g, record.intake_lot_id || '-')
      .replace(/\{\{ReCode\}\}/g, record.re_code || '-')
      .replace(/\{\{MatSapCode\}\}/g, record.mat_sap_code || '-')
      .replace(/\{\{Package\/Packages\}\}/g, `${i} / ${numPackages}`)
      .replace(/\{\{MfgDate\}\}/g, formatDate(record.manufacturing_date))
      .replace(/\{\{ExpDate\}\}/g, formatDate(record.expire_date))
      .replace(/\{\{ExtDate\}\}/g, formatDate(record.ext_date))
      .replace(/\{\{PackageVol\}\}/g, currentPkgVol.toFixed(4) || '0.0000')
      .replace(/\{\{UOM\}\}/g, record.uom || 'kg')
      .replace(/\{\{LodNo\}\}/g, record.lot_id || '-')
      .replace(/\{\{MaterialType\}\}/g, record.material_type || '-')
      .replace(/\{\{ReservNo\}\}/g, record.reserv_no || '-')
      .replace(/\{\{ReceiveDate\}\}/g, formatDate(record.intake_at))
      .replace(/\{\{StockZone\}\}/g, record.stock_zone || '-')
      .replace(/\{\{QRCode\}\}/g, `<image href="${qrLarge}" x="16.3" y="39.3" width="80" height="80" />`)

    // Replace fixed width/height in SVG with 100% so it scales to container via viewBox
    formattedSvg = formattedSvg.replace(/(<svg[\s\S]*?)width="[^"]*"/, '$1width="100%"')
                               .replace(/(<svg[\s\S]*?)height="[^"]*"/, '$1height="100%"')
    // Ensure SVG scales proportionally within the label
    if (!formattedSvg.includes('preserveAspectRatio')) {
      formattedSvg = formattedSvg.replace('<svg', '<svg preserveAspectRatio="xMidYMid meet"')
    }

    labelsHtml += `<div class="label-wrapper">${formattedSvg}</div>`
  }

  const html = `<html><head><style>
    * { margin:0; padding:0; outline:0; border:0; box-sizing:border-box; }
    @page { size: 4in 3in; margin: 0 !important; }
    html, body { width: 4in; height: 3in; margin: 0; padding: 0; background: white; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .label-wrapper { 
      width: 4in; 
      height: 3in; 
      display: block; 
      overflow: hidden; 
      position: relative; 
      page-break-after: always; 
      margin: 0;
      padding: 0;
      box-sizing: border-box; 
    }
    .label-wrapper:last-child { page-break-after: avoid; }
    .label-wrapper svg { width: 100%; height: 100%; display: block; object-fit: contain; }
    header, footer { display: none !important; }
  </style></head><body>${labelsHtml}</body></html>`.replace(/>\s+</g, '><').trim()

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
  const templateResponse = await fetch('/labels/ingredient_intake-label_4x3-r01.svg')
  const templateStr = await templateResponse.text()
  
  // QR data: IntakeLotId|MatSapCode| |ReceiveDate|Q'Ty|Unit|MaterialType|MFG_Date|ExpDate
  const qrString = `${record.intake_lot_id}|${record.mat_sap_code || ''}| |${formatDate(record.intake_at)}|${pkg.weight.toFixed(3)}|${record.uom || 'KG'}|${record.material_type || ''}|${formatDate(record.manufacturing_date)}|${formatDate(record.expire_date)}`
  const qrLarge = await generateQrDataUrl(qrString, 150)

  let formattedSvg = templateStr
    .replace(/\{\{IntakeLotId\}\}/g, record.intake_lot_id || '-')
    .replace(/\{\{ReCode\}\}/g, record.re_code || '-')
    .replace(/\{\{MatSapCode\}\}/g, record.mat_sap_code || '-')
    .replace(/\{\{Package\/Packages\}\}/g, `${pkg.package_no} / ${numPackages}`)
    .replace(/\{\{MfgDate\}\}/g, formatDate(record.manufacturing_date))
    .replace(/\{\{ExpDate\}\}/g, formatDate(record.expire_date))
    .replace(/\{\{ExtDate\}\}/g, formatDate(record.ext_date))
    .replace(/\{\{PackageVol\}\}/g, pkg.weight.toFixed(4) || '0.0000')
    .replace(/\{\{UOM\}\}/g, record.uom || 'kg')
    .replace(/\{\{LodNo\}\}/g, record.lot_id || '-')
    .replace(/\{\{MaterialType\}\}/g, record.material_type || '-')
    .replace(/\{\{ReservNo\}\}/g, record.reserv_no || '-')
    .replace(/\{\{ReceiveDate\}\}/g, formatDate(record.intake_at))
    .replace(/\{\{StockZone\}\}/g, record.stock_zone || '-')
    .replace(/\{\{QRCode\}\}/g, `<image href="${qrLarge}" x="16.3" y="39.3" width="80" height="80" />`)

  // Replace fixed width/height in SVG with 100%
  formattedSvg = formattedSvg.replace(/(<svg[\s\S]*?)width="[^"]*"/, '$1width="100%"')
                             .replace(/(<svg[\s\S]*?)height="[^"]*"/, '$1height="100%"')
  if (!formattedSvg.includes('preserveAspectRatio')) {
    formattedSvg = formattedSvg.replace('<svg', '<svg preserveAspectRatio="xMidYMid meet"')
  }

  const labelsHtml = `<div class="label-wrapper">${formattedSvg}</div>`
  
  // Create iframe for printing
  const iframe = document.createElement('iframe')
  iframe.style.display = 'none'
  document.body.appendChild(iframe)

  const html = `<html><head><style>
    * { margin:0; padding:0; outline:0; border:0; box-sizing:border-box; }
    @page { size: 4in 3in; margin: 0 !important; }
    html, body { width: 4in; height: 3in; margin: 0; padding: 0; background: white; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .label-wrapper { 
      width: 4in; 
      height: 3in; 
      display: block; 
      overflow: hidden; 
      position: relative; 
      page-break-after: always; 
      margin: 0;
      padding: 0;
      box-sizing: border-box; 
    }
    .label-wrapper:last-child { page-break-after: avoid; }
    .label-wrapper svg { width: 100%; height: 100%; display: block; object-fit: contain; }
    header, footer { display: none !important; }
  </style></head><body>${labelsHtml}</body></html>`.replace(/>\s+</g, '><').trim()

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

// ═══════════════════════════════════════════════════════════════════
// STOCK ADJUSTMENT
// ═══════════════════════════════════════════════════════════════════
const showAdjustDialog = ref(false)

// Report date range
const adjReportFrom = ref('')
const adjReportTo = ref('')

// Open stock adjustment dialog from intake list row
function openStockAdjustDialog(row: any) {
  adjSelectedReCode.value = row.re_code
  adjSelectedLotId.value = row.intake_lot_id
  adjNewRemainVol.value = null
  adjReason.value = ''
  adjRemark.value = ''
  adjBy.value = user.value?.username || 'operator'
  fetchAdjustments()
  showAdjustDialog.value = true
}

// Print stock adjustment report filtered by date range
function printAdjustmentReport() {
  let reportRows = adjustments.value
  if (adjReportFrom.value) {
    reportRows = reportRows.filter((r: any) => {
      const d = new Date(r.adjusted_at)
      return d >= new Date(adjReportFrom.value + 'T00:00:00')
    })
  }
  if (adjReportTo.value) {
    reportRows = reportRows.filter((r: any) => {
      const d = new Date(r.adjusted_at)
      return d <= new Date(adjReportTo.value + 'T23:59:59')
    })
  }

  const fromLabel = adjReportFrom.value || 'Beginning'
  const toLabel = adjReportTo.value || 'Now'

  const htmlContent = `
    <html><head><title>Stock Adjustment Report</title>
    <style>
      body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; color: #333; }
      h1 { color: #00695c; font-size: 22px; margin-bottom: 4px; }
      .subtitle { color: #666; font-size: 14px; margin-bottom: 16px; }
      table { width: 100%; border-collapse: collapse; font-size: 12px; }
      th { background: #00695c; color: white; padding: 8px 6px; text-align: left; }
      td { padding: 6px; border-bottom: 1px solid #ddd; }
      tr:nth-child(even) { background: #f5f5f5; }
      .increase { color: #2e7d32; font-weight: bold; }
      .decrease { color: #c62828; font-weight: bold; }
      .footer { margin-top: 16px; font-size: 11px; color: #999; text-align: right; }
      @media print { body { margin: 10px; } }
    </style></head><body>
    <h1>📋 Stock Adjustment Report</h1>
    <div class="subtitle">Period: ${fromLabel} — ${toLabel} &nbsp;|&nbsp; Total Records: ${reportRows.length}</div>
    <table>
      <thead>
        <tr>
          <th>Date/Time</th><th>Lot ID</th><th>SAP Code</th><th>RE Code</th>
          <th>Material</th><th>Type</th><th>Qty</th><th>Before</th><th>After</th>
          <th>Reason</th><th>Remark</th><th>By</th>
        </tr>
      </thead>
      <tbody>
        ${reportRows.map((r: any) => `
          <tr>
            <td>${formatDateTime(r.adjusted_at)}</td>
            <td>${r.intake_lot_id || ''}</td>
            <td>${r.mat_sap_code || ''}</td>
            <td>${r.re_code || ''}</td>
            <td>${r.material_description || ''}</td>
            <td class="${r.adjust_type === 'increase' ? 'increase' : 'decrease'}">
              ${r.adjust_type === 'increase' ? '↑ Increase' : '↓ Decrease'}
            </td>
            <td class="${r.adjust_type === 'increase' ? 'increase' : 'decrease'}">
              ${r.adjust_type === 'increase' ? '+' : '−'}${r.adjust_qty?.toFixed(3) || '0.000'}
            </td>
            <td>${r.prev_remain_vol?.toFixed(3) || ''}</td>
            <td>${r.new_remain_vol?.toFixed(3) || ''}</td>
            <td>${r.adjust_reason || ''}</td>
            <td>${r.remark || ''}</td>
            <td>${r.adjusted_by || ''}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
    <div class="footer">Printed: ${new Date().toLocaleString('en-GB', { timeZone: 'Asia/Bangkok' })}</div>
    </body></html>
  `

  const printWin = window.open('', '_blank')
  if (printWin) {
    printWin.document.write(htmlContent)
    printWin.document.close()
    printWin.focus()
    setTimeout(() => printWin.print(), 500)
  }
}

// Step 1: RE-Code selection (from active intake records only)
const activeReCodes = computed(() => {
  const codes = new Map<string, { re_code: string, material_description: string, mat_sap_code: string }>()
  rows.value
    .filter((r: any) => r.status === 'Active' && r.re_code)
    .forEach((r: any) => {
      if (!codes.has(r.re_code)) {
        codes.set(r.re_code, {
          re_code: r.re_code,
          material_description: r.material_description || '',
          mat_sap_code: r.mat_sap_code || '',
        })
      }
    })
  return Array.from(codes.values()).sort((a, b) => a.re_code.localeCompare(b.re_code))
})

const adjSelectedReCode = ref('')

// Step 2: Lot IDs filtered by selected RE-Code
const adjLotsForReCode = computed(() => {
  if (!adjSelectedReCode.value) return []
  return rows.value
    .filter((r: any) => r.status === 'Active' && r.re_code === adjSelectedReCode.value)
    .sort((a: any, b: any) => b.id - a.id)
})

const adjSelectedLotId = ref('')
const adjSelectedLot = computed(() => {
  if (!adjSelectedLotId.value) return null
  return rows.value.find((r: any) => r.intake_lot_id === adjSelectedLotId.value) || null
})

// Adjustment form — user enters target "New Adjust Value" directly
const adjNewRemainVol = ref<number | null>(null)
const adjReason = ref('')
const adjRemark = ref('')
const adjBy = ref(user.value?.username || 'operator')
const adjSubmitting = ref(false)

const adjReasonOptions = [
  'Physical Count',
  'Spillage / Damage',
  'Expired Write-off',
  'Quality Rejection',
  'Receiving Correction',
  'Transfer In',
  'Transfer Out',
  'Other',
]

// Computed summary values
const adjTotalIntake = computed(() => adjSelectedLot.value?.intake_vol ?? 0)
const adjRemaining = computed(() => adjSelectedLot.value?.remain_vol ?? 0)

// Auto-compute type and qty from new value vs current remaining
const adjComputedType = computed(() => {
  if (adjNewRemainVol.value === null || !adjSelectedLot.value) return null
  return adjNewRemainVol.value >= adjRemaining.value ? 'increase' : 'decrease'
})

const adjComputedQty = computed(() => {
  if (adjNewRemainVol.value === null || !adjSelectedLot.value) return 0
  return Math.abs(adjNewRemainVol.value - adjRemaining.value)
})

// Stock Overview: all active lots for the selected RE-Code
const stockOverviewLots = computed(() => {
  if (!adjSelectedReCode.value) return []
  return rows.value
    .filter((r: any) => r.status === 'Active' && r.re_code === adjSelectedReCode.value)
    .sort((a: any, b: any) => b.id - a.id)
})

const stockOverviewSummary = computed(() => {
  const lots = stockOverviewLots.value
  return {
    totalLots: lots.length,
    totalIntake: lots.reduce((sum: number, r: any) => sum + (r.intake_vol || 0), 0),
    totalRemaining: lots.reduce((sum: number, r: any) => sum + (r.remain_vol || 0), 0),
  }
})

// Adjustment history
const adjustments = ref<any[]>([])
const adjColumnFilters = ref<Record<string, string>>({})

const adjColumns = computed<QTableColumn[]>(() => [
  { name: 'adjusted_at', label: 'Date/Time', field: 'adjusted_at', align: 'center' as const, sortable: true, format: (val: any) => formatDateTime(val) },
  { name: 'intake_lot_id', label: 'Lot ID', field: 'intake_lot_id', align: 'left' as const, sortable: true },
  { name: 'mat_sap_code', label: 'SAP Code', field: 'mat_sap_code', align: 'left' as const, sortable: true },
  { name: 're_code', label: 'RE Code', field: 're_code', align: 'left' as const, sortable: true },
  { name: 'material_description', label: 'Material', field: 'material_description', align: 'left' as const, sortable: true },
  { name: 'adjust_type', label: 'Type', field: 'adjust_type', align: 'center' as const, sortable: true },
  { name: 'adjust_qty', label: 'Qty', field: 'adjust_qty', align: 'right' as const, sortable: true },
  { name: 'prev_remain_vol', label: 'Before', field: 'prev_remain_vol', align: 'right' as const, sortable: true },
  { name: 'new_remain_vol', label: 'After', field: 'new_remain_vol', align: 'right' as const, sortable: true },
  { name: 'adjust_reason', label: 'Reason', field: 'adjust_reason', align: 'left' as const, sortable: true },
  { name: 'remark', label: 'Remark', field: 'remark', align: 'left' as const, sortable: true },
  { name: 'adjusted_by', label: 'By', field: 'adjusted_by', align: 'center' as const, sortable: true },
])

const filteredAdjustments = computed(() => {
  let result = adjustments.value
  for (const [colName, filterVal] of Object.entries(adjColumnFilters.value)) {
    if (!filterVal) continue
    const needle = filterVal.toLowerCase()
    result = result.filter((row: any) => {
      let cellVal = ''
      if (colName === 'adjusted_at') {
        cellVal = formatDateTime(row[colName])
      } else {
        cellVal = String(row[colName] ?? '')
      }
      return cellVal.toLowerCase().includes(needle)
    })
  }
  return result
})

const fetchAdjustments = async () => {
  try {
    adjustments.value = await $fetch<any[]>(`${appConfig.apiBaseUrl}/stock-adjustments/?limit=500`)
  } catch (e) {
    console.error('Failed to fetch adjustments:', e)
  }
}

const resetAdjForm = () => {
  adjSelectedReCode.value = ''
  adjSelectedLotId.value = ''
  adjNewRemainVol.value = null
  adjReason.value = ''
  adjRemark.value = ''
}

const submitAdjustment = async () => {
  if (!adjSelectedLot.value || adjNewRemainVol.value === null || !adjReason.value) {
    $q.notify({ type: 'warning', message: 'Please fill all required fields' })
    return
  }

  if (adjNewRemainVol.value < 0) {
    $q.notify({ type: 'negative', message: 'New value cannot be negative' })
    return
  }

  const computedQty = adjComputedQty.value
  const computedType = adjComputedType.value

  if (computedQty === 0) {
    $q.notify({ type: 'info', message: 'No change — new value equals current remaining' })
    return
  }

  // Warn if large decrease (>20%)
  if (computedType === 'decrease') {
    const pct = (computedQty / (adjSelectedLot.value.remain_vol || 1)) * 100
    if (pct > 20) {
      const confirmed = await new Promise<boolean>((resolve) => {
        $q.dialog({
          title: '⚠️ Large Adjustment',
          message: `This will decrease by ${pct.toFixed(1)}% of remaining stock (${adjSelectedLot.value!.remain_vol.toFixed(3)} → ${adjNewRemainVol.value!.toFixed(3)} kg). Continue?`,
          cancel: true,
          persistent: true,
        }).onOk(() => resolve(true)).onCancel(() => resolve(false))
      })
      if (!confirmed) return
    }
  }

  adjSubmitting.value = true
  try {
    await $fetch(`${appConfig.apiBaseUrl}/stock-adjustments/`, {
      method: 'POST',
      body: {
        intake_lot_id: adjSelectedLotId.value,
        adjust_type: computedType,
        adjust_qty: computedQty,
        adjust_reason: adjReason.value,
        remark: adjRemark.value || null,
        adjusted_by: adjBy.value,
      },
    })
    $q.notify({ type: 'positive', message: 'Stock adjusted successfully', icon: 'check_circle' })
    resetAdjForm()
    fetchAdjustments()
    fetchReceipts()  // Refresh intake table to show updated remain_vol
  } catch (e: any) {
    $q.notify({ type: 'negative', message: e.data?.detail || 'Adjustment failed' })
  } finally {
    adjSubmitting.value = false
  }
}

// Watch RE-Code change → reset lot
watch(adjSelectedReCode, () => {
  adjSelectedLotId.value = ''
  adjNewRemainVol.value = null
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
                      color="teal-8"
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

    </div><!-- end intake tab -->

    <!-- ═══ STOCK ADJUSTMENT DIALOG ═══ -->
    <q-dialog v-model="showAdjustDialog" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card class="column" style="max-width: 100vw;">
        <!-- Dialog Header -->
        <q-card-section class="q-pa-sm bg-teal-8 text-white row items-center justify-between">
          <div class="row items-center q-gutter-sm">
            <q-icon name="tune" size="sm" />
            <div class="text-h6 text-weight-bold">Stock Adjustment</div>
            <q-badge v-if="adjSelectedLot" color="white" text-color="teal-9" class="text-weight-bold">
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
        <q-card-section class="q-pa-sm bg-teal-8 text-white row items-center">
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
                    :class="adjSelectedLotId === props.row.intake_lot_id ? 'bg-teal-1 text-weight-bold' : ''"
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
              <q-card flat bordered class="bg-teal-1 text-center q-pa-sm">
                <div class="text-caption text-grey-7">New Value</div>
                <div class="text-h6 text-weight-bold" :class="(adjNewRemainVol ?? adjRemaining) < 0 ? 'text-red-8' : 'text-teal-9'">
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
                color="teal-8" icon="check"
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
        <q-card-section class="q-pa-sm bg-teal-7 text-white row items-center justify-between">
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
            <q-tr :props="props" class="bg-teal-1">
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

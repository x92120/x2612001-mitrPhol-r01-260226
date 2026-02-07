<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import type { QTableColumn } from 'quasar'
import { useQuasar, exportFile } from 'quasar'
import { appConfig } from '~/appConfig/config'
import { useAuth } from '~/composables/useAuth'
import { useMQTT } from '~/composables/useMQTT'

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
  warehouse_location?: string
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
  po_number?: string
  manufacturing_date?: string
}

const $q = useQuasar()
const { getAuthHeader, user } = useAuth()

// MQTT Integration
const {
  connect: connectMQTT,
  disconnect: disconnectMQTT,
  isConnected: mqttConnected,
  connectionStatus,
  lastScan,
} = useMQTT()

const lotNumber = ref('')
const warehouseLocation = ref('')
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
const tempIngredientId = ref('')

// Editing state
const isEditing = ref(false)
const editId = ref<number | null>(null)
const originalRemainVol = ref<number | null>(null)
const originalStatus = ref<string>('Active')

// Watch for scans from ANY node in the network
watch(lastScan, (newScan) => {
  if (newScan && newScan.barcode) {
    // Update the barcode field
    ingredientId.value = newScan.barcode

    // If scanning while dialog is open, update temp field too
    if (showIngredientDialog.value) {
      tempIngredientId.value = newScan.barcode
    }

    // Trigger lookup logic
    lookupIngredient(newScan.barcode)

    $q.notify({
      type: 'info',
      message: `Intake scan from ${newScan.node_id}`,
      caption: `Barcode: ${newScan.barcode}`,
      icon: 'qr_code_scanner',
      position: 'top-right',
    })
  }
})

const columns: QTableColumn[] = [
  { name: 'id', align: 'center', label: 'ID', field: 'id', sortable: true },
  {
    name: 'intake_lot_id',
    align: 'center',
    label: 'Intake Lot ID',
    field: 'intake_lot_id',
    sortable: true,
  },
  {
    name: 'warehouse_location',
    align: 'center',
    label: 'From Warehouse',
    field: 'warehouse_location',
    sortable: true,
  },
  {
    name: 'lot_id',
    align: 'center',
    label: 'Lot ID',
    field: 'lot_id',
    sortable: true,
  },
  {
    name: 'mat_sap_code',
    align: 'center',
    label: 'MAT.SAP Code',
    field: 'mat_sap_code',
    sortable: true,
  },
  {
    name: 're_code',
    align: 'center',
    label: 'Re-Code',
    field: 're_code',
    sortable: true,
  },
  {
    name: 'material_description',
    align: 'left',
    label: 'Description',
    field: 'material_description',
    sortable: true,
  },
  {
    name: 'uom',
    align: 'center',
    label: 'UOM',
    field: 'uom',
    sortable: true,
  },
  {
    name: 'intake_vol',
    align: 'center',
    label: 'Intake Vol (kg)',
    field: 'intake_vol',
    sortable: true,
  },
  {
    name: 'remain_vol',
    align: 'center',
    label: 'Remain Vol (kg)',
    field: 'remain_vol',
    sortable: true,
    classes: 'text-negative text-weight-bold', // Red color
  },

  {
    name: 'intake_package_vol',
    align: 'center',
    label: 'Pkg Vol',
    field: 'intake_package_vol',
    sortable: true,
  },
  {
    name: 'package_intake',
    align: 'center',
    label: 'Pkgs',
    field: 'package_intake',
    sortable: true,
  },
  {
    name: 'expire_date',
    align: 'center',
    label: 'Expire Date',
    field: 'expire_date',
    sortable: true,
    format: (val: string) => (val ? val.split('T')[0] : '') || '',
  },
  {
    name: 'po_number',
    align: 'center',
    label: 'PO No.',
    field: 'po_number',
    sortable: true,
  },
  {
    name: 'manufacturing_date',
    align: 'center',
    label: 'Mfg Date',
    field: 'manufacturing_date',
    sortable: true,
    format: (val: string) => (val ? val.split('T')[0] : '') || '',
  },
  { name: 'status', align: 'center', label: 'Status', field: 'status', sortable: true },
  { name: 'xActions', align: 'center', label: 'Actions', field: 'xActions' },
]

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

// Fetch Receipt History
const fetchReceipts = async (isBackground = false) => {
  if (!isBackground) isLoading.value = true
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/ingredient-intake-lists/`, {
      headers: getAuthHeader() as Record<string, string>,
    })
    if (response.ok) {
      const newData = await response.json()
      if (JSON.stringify(newData) !== JSON.stringify(rows.value)) {
        rows.value = newData
      }
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
    xIngredientName.value = ''
    xMatSapCode.value = ''
    xReCode.value = ''
    return
  }

  try {
    // We'll use a new general lookup parameter handled by backend
    const response = await fetch(`${appConfig.apiBaseUrl}/ingredients/?lookup=${query}`, {
      headers: getHeaders(),
    })

    if (response.ok) {
      const ingredients = await response.json()
      if (ingredients.length > 0) {
        const ingredient = ingredients[0]
        xIngredientName.value = ingredient.name
        xMatSapCode.value = ingredient.mat_sap_code
        xReCode.value = ingredient.re_code || ''

        // Only update ingredientId if it's different and we are not currently typing it?
        // Actually, if we scanned a blind code, we want to swap it to the ID.
        // If we typed the ID, it stays the ID.
        if (ingredientId.value !== ingredient.ingredient_id) {
          ingredientId.value = ingredient.ingredient_id
        }

        // Set package volume from ingredient master
        packageVol.value = Number(ingredient.std_package_size || 25).toFixed(3)

        $q.notify({
          type: 'positive',
          message: `Found: ${ingredient.name} (Pkg: ${ingredient.std_package_size || 25}kg)`,
          position: 'top',
          timeout: 1000,
        })
      } else {
        // Don't clear immediately if typing?
        // But maybe we should clear the read-only fields
        xIngredientName.value = ''
        xMatSapCode.value = ''
        xReCode.value = ''
      }
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
    const response = await fetch(`${appConfig.apiBaseUrl}/ingredient-intake-next-id`)
    if (response.ok) {
      const data = await response.json()
      intakeLotId.value = data.next_id
    } else {
      // Fallback
      intakeLotId.value = 'Error generating ID'
    }
  } catch (e) {
    console.error('Failed to generate ID', e)
    intakeLotId.value = 'Network Error: ' + (e as any).message
  }
}

const isSaving = ref(false)

// Save Receipt (Create or Update)
const onSave = async () => {
  // Detailed Validation
  const missingFields: string[] = []
  if (!ingredientId.value && !xMatSapCode.value) missingFields.push('Ingredient ID')
  if (!lotNumber.value) missingFields.push('Lot Number')
  if (!warehouseLocation.value) missingFields.push('Warehouse Location')
  if (!intakeVol.value) missingFields.push('Intake Volume')
  if (!expireDate.value) missingFields.push('Expire Date')

  if (missingFields.length > 0) {
    $q.notify({
      type: 'negative',
      message: `Please enter data: ${missingFields.join(', ')}`,
      position: 'top',
    })
    return
  }

  // Logical Validation
  const rVol = parseFloat(intakeVol.value)
  if (isNaN(rVol) || rVol <= 0) {
    $q.notify({
      type: 'negative',
      message: 'Intake Volume must be a positive number',
      position: 'top',
    })
    return
  }

  if (packageVol.value) {
    const pVol = parseFloat(packageVol.value)
    if (isNaN(pVol) || pVol <= 0) {
      $q.notify({
        type: 'negative',
        message: 'Package Volume must be a positive number',
        position: 'top',
      })
      return
    }
  }

  $q.dialog({
    title: 'Confirm Save',
    message: isEditing.value
      ? 'Are you sure you want to update this intake record?'
      : 'Are you sure you want to save this ingredient intake?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    isSaving.value = true

    const payload = {
      intake_lot_id: intakeLotId.value,
      lot_id: lotNumber.value,
      warehouse_location: warehouseLocation.value,
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
      expire_date: expireDate.value ? new Date(expireDate.value).toISOString() : null,
      status: isEditing.value ? originalStatus.value : 'Active',
      intake_by: user.value?.username || 'cj',
      edit_by: user.value?.username || 'cj',
      manufacturing_date: manufacturingDate.value ? new Date(manufacturingDate.value).toISOString() : null,
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
            ? 'Ingredient intake updated successfully'
            : 'Ingredient intake saved successfully',
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
          message: `Error: ${error.detail || 'Save failed'}`,
          position: 'top',
        })
      }
    } catch (error) {
      console.error('Save error:', error)
      $q.notify({
        type: 'negative',
        message: 'Network error: Failed to save receipt',
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
  warehouseLocation.value = row.warehouse_location || ''
  xMatSapCode.value = row.mat_sap_code
  xReCode.value = row.re_code || ''
  intakeVol.value = row.intake_vol.toString()
  // remainVol removed
  packageVol.value = row.intake_package_vol ? row.intake_package_vol.toString() : ''
  numberOfPackages.value = row.package_intake ? row.package_intake.toString() : ''
  expireDate.value = row.expire_date ? row.expire_date.split('T')[0] || '' : ''
  manufacturingDate.value = row.manufacturing_date ? row.manufacturing_date.split('T')[0] || '' : ''
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
    title: 'Confirm Rejection',
    message: `Are you sure you want to reject intake record ${row.intake_lot_id}?`,
    cancel: true,
    persistent: true,
    prompt: {
      model: '',
      type: 'text',
      label: 'Reason for rejection (optional)',
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
        $q.notify({ type: 'warning', message: 'Record rejected' })
        fetchReceipts()
      } else {
        const err = await response.json()
        $q.notify({ type: 'negative', message: `Reject failed: ${err.detail || 'Unknown error'}` })
      }
    } catch (error) {
      console.error('Reject error:', error)
      $q.notify({ type: 'negative', message: 'Network error while rejecting' })
    }
  })
}

// Disconnect is handled by useMQTT composable

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

onMounted(() => {
  fetchReceipts()
  generateIntakeLotId() // Generate initial ID
  setTimeout(() => {
    connectMQTT()
  }, 100)

  // Auto-refresh every 5 seconds
  refreshInterval = setInterval(() => {
    fetchReceipts(true)
  }, 5000)
})

onUnmounted(() => {
  disconnectMQTT()
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
  warehouseLocation.value = ''
  originalRemainVol.value = null
  originalStatus.value = 'Active'
  generateIntakeLotId() // Get fresh ID after clear/save
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
        message: `Status updated to ${newStatus}`,
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
      message: 'Failed to update status',
    })
  }
}

// Print Label Function
const printLabel = (record: IngredientIntake) => {
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

  const numPackages = record.package_intake || 1
  let labelsHtml = ''

  for (let i = 1; i <= numPackages; i++) {
    // Construct full data object for QR
    const qrData = {
      intake_lot_id: record.intake_lot_id,
      lot_id: record.lot_id,
      mat_sap_code: record.mat_sap_code,
      re_code: record.re_code,
      intake_package_vol: record.intake_package_vol,
      package_no: i,
      total_packages: numPackages,
      expire_date: record.expire_date?.split('T')[0],
      intake_at: record.intake_at?.split('T')[0],
    }
    const qrString = encodeURIComponent(JSON.stringify(qrData))

    labelsHtml += `
      <div class="label-container">
        
        <!-- Top Part (4x4 inch) -->
        <div class="part-top">
          <div class="header">INGREDIENT INTAKE</div>
          
          <div class="main-info">
             <div class="field-item">
               <div class="label">Intake Lot ID</div>
               <div class="value-mono">${record.intake_lot_id}</div>
             </div>
             
             <div class="field-item">
               <div class="label">Ingredient Code</div>
               <!-- Swapped and resized emphasis -->
               <div class="value-huge text-primary">${record.re_code || '-'}</div>
               <div class="value small text-grey">${record.mat_sap_code}</div>
             </div>

             <div class="row">
               <div class="col">
                  <div class="label">Intake Vol</div>
                  <div class="value-huge">${record.intake_package_vol?.toFixed(2)} <span class="unit">kg</span></div>
               </div>
               <div class="col right">
                  <div class="label">Package</div>
                  <div class="value-large">${i} / ${numPackages}</div>
               </div>
             </div>

              <div class="row">
               <div class="col">
                  <div class="label">Expire Date</div>
                  <div class="value">${record.expire_date?.split('T')[0] || '-'}</div>
               </div>
               <div class="col right">
                  <div class="label">Supplier Lot</div>
                  <div class="value">${record.lot_id || '-'}</div>
               </div>
             </div>
          </div>

          <div class="qr-code-top">
             <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${qrString}" />
          </div>
        </div>

        <!-- Bottom Part (4x2 inch) -->
        <div class="part-bottom">
           <div class="field-item">
             <div class="label">Intake Lot ID</div>
             <div class="value-mono small">${record.intake_lot_id}</div>
           </div>
           
           <div class="row">
              <div class="col">
                 <div class="label">Material</div>
                 <div class="value large text-primary">${record.re_code || '-'}</div>
                 <div class="value small text-grey">${record.mat_sap_code}</div>
              </div>
              <div class="col right">
                 <div class="label">Weight</div>
                 <div class="value large">${record.intake_package_vol?.toFixed(2)} kg</div>
                 <div class="value text-grey" style="font-size: 14pt; margin-top: 5px;">${i} / ${numPackages}</div>
              </div>
           </div>

           <div class="qr-code-bottom">
             <img src="https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=${qrString}" />
          </div>
        </div>

      </div>
    `
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
            font-family: Arial, sans-serif;
            background: white;
            box-sizing: border-box;
          }
          .label-container {
            width: 4in;
            height: 6in;
            position: relative;
            box-sizing: border-box;
            border: 1px dotted #ccc; /* Guide for cutting/viewing */
            page-break-after: always;
            display: flex;
            flex-direction: column;
          }
          
          /* Top Part: 4x4 inch */
          .part-top {
            width: 100%;
            height: 4in;
            box-sizing: border-box;
            padding: 15px;
            border-bottom: 2px dashed #000; /* Tear-off line */
            position: relative;
          }

          /* Bottom Part: 4x2 inch */
          .part-bottom {
            width: 100%;
            height: 2in;
            box-sizing: border-box;
            padding: 10px 15px;
            position: relative;
            background-color: #f9f9f9; /* Subtle diff */
          }

          .header {
            text-align: center;
            font-weight: 900;
            font-size: 16pt;
            border-bottom: 2px solid #000;
            padding-bottom: 5px;
            margin-bottom: 10px;
            letter-spacing: 1px;
          }

          .field-item {
            margin-bottom: 10px;
          }

          .row {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
          }
          .col { flex: 1; }
          .col.right { text-align: right; }

          .label {
            font-size: 9pt;
            color: #555;
            text-transform: uppercase;
            font-weight: bold;
            margin-bottom: 2px;
          }
          
          .value { font-size: 12pt; font-weight: bold; color: #000; }
          .value.large { font-size: 18pt; }
          .value.small { font-size: 10pt; }
          
          .value-mono {
            font-family: 'Courier New', monospace;
            font-size: 14pt;
            font-weight: bold;
            color: #000;
            letter-spacing: -0.5px;
          }
          .value-mono.small { font-size: 11pt; }

          .value-huge {
            font-size: 32pt;
            font-weight: bold;
            line-height: 1;
          }
          .value-large {
            font-size: 24pt;
            font-weight: bold;
            line-height: 1;
          }
          .unit { font-size: 14pt; color: #666; font-weight: normal; }
          
          .text-grey { color: #666; }

          /* QR Codes Positioning - Adjusted to prevent overlap */
          .qr-code-top {
            position: absolute;
            top: 50px; /* Moved down slightly */
            right: 5px;
            width: 100px;
            height: 100px;
            z-index: 10;
          }
          .qr-code-bottom {
            position: absolute;
            top: 10px;
            right: 5px;
            width: 60px;
            height: 60px;
          }
          img { width: 100%; height: 100%; }
          
          /* Ensure text area does not overlap with QR */
          .main-info {
             width: 70%; /* Reserve 30% width on right for QR */
          }
          
          /* Specific bottom part adjustments */
          .part-bottom {
             display: flex;
             flex-direction: column;
             justify-content: center;
          }
          .part-bottom .row, .part-bottom .field-item {
             width: 75%; /* Limit width to avoid QR overlap */
          }

          @media print {
            .label-container { border: none; }
            .part-bottom { background-color: transparent; }
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
  const columnsToExport = columns.filter(col => col.name !== 'xActions')
  
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
      message: 'Browser denied file download...',
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
        $q.loading.show({ message: 'Importing data...' })
        
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
  <q-page class="q-pa-md" style="background-color: #f5f5f5">
    <!-- Ingredient Intake Form -->
    <div class="row q-mb-lg">
      <div class="col-12">
        <q-card class="shadow-1">
          <q-form class="q-pa-md">
            <!-- Row 1: Ingredient ID + Blind Code -->
            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-4">
                <q-input
                  outlined
                  v-model="ingredientId"
                  label="Scan/Type Ingredient Code *"
                  @keyup.enter="lookupIngredient(ingredientId)"
                >
                  <template v-slot:prepend>
                    <q-icon
                      name="circle"
                      :color="mqttConnected ? 'positive' : 'negative'"
                    />
                  </template>
                  <template v-slot:append>
                    <q-icon
                      name="qr_code_scanner"
                      class="cursor-pointer"
                      @click="openIngredientDialog"
                    />
                  </template>
                </q-input>
              </div>
              <div class="col-12 col-md-4">
                <q-input
                  outlined
                  v-model="xMatSapCode"
                  label="MAT.SAP Code"
                  readonly
                  bg-color="grey-2"
                />
              </div>
              <div class="col-12 col-md-4">
                 <!-- Re-Code with Settings Icon Wrapper -->
                <q-input outlined v-model="xReCode" label="Re-Code" readonly bg-color="grey-2" />
              </div>
            </div>

            <!-- Row 1.5: Ingredient Name -->
            <div class="row q-col-gutter-md q-mt-sm">
                <div class="col-12">
                     <q-input
                        outlined
                        v-model="xIngredientName"
                        label="Ingredient Name"
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
            </div>

            <!-- Row 3: Warehouse, Lot Number, Expire Date (swapped from row 2) -->
            <div class="row q-col-gutter-md q-mt-sm">
              <div class="col-12 col-md-4">
                <q-select
                  outlined
                  v-model="warehouseLocation"
                  :options="['WH-001', 'WH-002', 'WH-003', 'WH-Cooling', 'Re Claim from Process']"
                  label="Intake Warehouse Location *"
                  dropdown-icon="arrow_drop_down"
                >
                  <template v-slot:after>
                    <q-btn
                      icon="settings"
                      color="primary"
                      round
                      flat
                      to="/x12-WarehouseConfig"
                      title="Config Warehouse"
                    />
                  </template>
                </q-select>
              </div>
              <div class="col-12 col-md-4">
                <q-input outlined v-model="lotNumber" label="Lot Number *" />
              </div>
              <div class="col-12 col-md-4">
                <q-input outlined v-model="poNumber" label="PO Number" />
              </div>
            </div>

            <!-- New Row: Mfg Date, Expire Date -->
            <div class="row q-col-gutter-md q-mt-sm">
              <div class="col-12 col-md-4">
                <q-input outlined v-model="manufacturingDate" label="Manufacturing Date" type="date" stack-label />
              </div>
              <div class="col-12 col-md-4">
                <q-input outlined v-model="expireDate" label="Expire Date *" type="date" stack-label />
              </div>
            </div>

            <div class="row q-col-gutter-md q-mt-sm">
              <div class="col-12 col-md-3">
                <q-input
                  outlined
                  v-model="intakeLotId"
                  label="Ingredient Intake ID"
                  readonly
                  bg-color="grey-2"
                  hint="Auto-generated ID"
                />
              </div>
              <div class="col-12 col-md-4">
                <q-input outlined v-model="intakeVol" label="Intake Vol (kg) *" />
              </div>

              <!-- Remain Vol input removed -->
              <div class="col-12 col-md-3">
                <q-input outlined v-model="packageVol" label="Package Vol (kg)" />
              </div>
              <div class="col-12 col-md-2">
                <q-input
                  outlined
                  v-model="numberOfPackages"
                  label="Num of Packages"
                  readonly
                  bg-color="grey-2"
                  input-class="text-right"
                  hint="Auto-calculated"
                />
              </div>
            </div>

            <div class="q-mt-md">
              <q-btn
                :label="isEditing ? 'Update Intake' : 'Save Intake'"
                color="info"
                class="q-mr-md"
                style="min-width: 130px"
                @click="onSave"
                :loading="isSaving"
              />
              <q-btn label="Clear" color="grey" outline style="min-width: 130px" @click="onClear" />
            </div>
          </q-form>
        </q-card>
      </div>
    </div>

    <!-- Ingredient Intake Table -->
    <div class="row items-center justify-between q-mb-sm">
      <div class="text-h6">Ingredient Intake List</div>
      <div class="row items-center q-gutter-sm">
        <q-btn
          icon="refresh"
          color="primary"
          round
          flat
          dense
          @click="() => fetchReceipts()"
        >
          <q-tooltip>Refresh</q-tooltip>
        </q-btn>
        <q-btn
          icon="filter_alt_off"
          color="primary"
          round
          flat
          dense
          @click="resetFilters"
        >
          <q-tooltip>Reset Filters</q-tooltip>
        </q-btn>
        <q-btn
          icon="filter_alt"
          color="accent"
          round
          flat
          dense
          @click="showFilters = !showFilters"
        >
          <q-tooltip>{{ showFilters ? 'Hide Filters' : 'Show Filters' }}</q-tooltip>
        </q-btn>
        <q-btn
          icon="file_download"
          color="secondary"
          round
          flat
          dense
          @click="exportTable"
        >
          <q-tooltip>Export Excel</q-tooltip>
        </q-btn>
        <q-btn
          icon="file_upload"
          color="accent"
          round
          flat
          dense
          @click="importTable"
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
        <q-checkbox
          v-model="showAll"
          label="Show All (including Rejected/Cancelled)"
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

            <!-- Editable Status Chip -->
            <template v-slot:body-cell-status="props">
              <q-td :props="props">
                <div
                  :class="[
                    'text-white',
                    'row',
                    'flex-center',
                    'full-width',
                    'rounded-borders',
                    `bg-${getStatusColor(props.value)}`,
                  ]"
                  style="height: 36px; font-size: 14px"
                >
                  {{ props.value }}
                </div>
              </q-td>
            </template>

            <template v-slot:body-cell-xActions="props">
              <q-td align="center" :props="props">
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
                  <q-tooltip>Print Label</q-tooltip>
                </q-btn>
                <q-btn
                  icon="history"
                  color="primary"
                  unelevated
                  no-caps
                  dense
                  size="sm"
                  class="q-mr-xs"
                  @click="openDetailDialog(props.row)"
                >
                  <q-tooltip>View Detail & History</q-tooltip>
                </q-btn>
                <q-btn
                  icon="block"
                  color="negative"
                  unelevated
                  no-caps
                  dense
                  size="sm"
                  @click="onRejectIntake(props.row)"
                  :disable="props.row.status === 'Reject' || props.row.status === 'Cancelled'"
                >
                  <q-tooltip>Reject Record</q-tooltip>
                </q-btn>
              </q-td>
            </template>
          </q-table>
        </q-card>
      </div>
    </div>

    <!-- Ingredient Code Entry Dialog -->
    <q-dialog v-model="showIngredientDialog">
      <q-card style="min-width: 400px">
        <q-card-section class="bg-info text-white">
          <div class="text-h6">Enter Ingredient Code</div>
        </q-card-section>

        <q-card-section class="q-pt-md">
          <q-input
            v-model="tempIngredientId"
            label="Ingredient ID"
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
          <q-btn flat label="Cancel" color="grey" @click="cancelIngredientDialog" />
          <q-btn
            label="Confirm"
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
          <div class="text-h6">Intake Detail - {{ selectedRecord?.intake_lot_id }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="q-pt-md">
          <div class="row q-col-gutter-sm">
            <div class="col-6 text-weight-bold">Intake Lot ID:</div>
            <div class="col-6">{{ selectedRecord?.intake_lot_id }}</div>

            <div class="col-6 text-weight-bold">Lot ID:</div>
            <div class="col-6">{{ selectedRecord?.lot_id }}</div>

            <div class="col-6 text-weight-bold">MAT.SAP Code:</div>
            <div class="col-6">{{ selectedRecord?.mat_sap_code }}</div>

            <div class="col-6 text-weight-bold">Re-Code:</div>
            <div class="col-6">{{ selectedRecord?.re_code || '-' }}</div>

            <div class="col-6 text-weight-bold">Warehouse:</div>
            <div class="col-6">{{ selectedRecord?.warehouse_location }}</div>

            <div class="col-6 text-weight-bold">PO Number:</div>
            <div class="col-6">{{ selectedRecord?.po_number || '-' }}</div>

            <div class="col-6 text-weight-bold">Mfg Date:</div>
            <div class="col-6">{{ selectedRecord?.manufacturing_date?.split('T')[0] || '-' }}</div>

            <div class="col-6 text-weight-bold">Intake Volume:</div>
            <div class="col-6">{{ selectedRecord?.intake_vol }} kg</div>

            <div class="col-6 text-weight-bold">Remain Volume:</div>
            <div class="col-6 text-negative text-weight-bolder">
              {{ selectedRecord?.remain_vol }} kg
            </div>

            <div class="col-6 text-weight-bold">Package Vol:</div>
            <div class="col-6">{{ selectedRecord?.intake_package_vol || '-' }} kg</div>

            <div class="col-6 text-weight-bold">Packages:</div>
            <div class="col-6">{{ selectedRecord?.package_intake || '-' }}</div>

            <div class="col-6 text-weight-bold">Expire Date:</div>
            <div class="col-6">{{ selectedRecord?.expire_date?.split('T')[0] }}</div>

            <div class="col-6 text-weight-bold">Status:</div>
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

            <div class="col-6 text-weight-bold">Intake By:</div>
            <div class="col-6">{{ selectedRecord?.intake_by }}</div>

            <div class="col-6 text-weight-bold">Intake At:</div>
            <div class="col-6">
              {{ selectedRecord ? new Date(selectedRecord.intake_at).toLocaleString() : '' }}
            </div>

            <div class="col-6 text-weight-bold">Last Edited By:</div>
            <div class="col-6">{{ selectedRecord?.edit_by || '-' }}</div>

            <div class="col-6 text-weight-bold">Last Edited At:</div>
            <div class="col-6">
              {{
                selectedRecord?.edit_at ? new Date(selectedRecord.edit_at).toLocaleString() : '-'
              }}
            </div>
          </div>

          <!-- History Section -->
          <!-- History Section -->
          <div class="q-mt-lg">
            <div class="text-subtitle1 text-weight-bold q-mb-sm row items-center">
              <q-icon name="history" color="primary" class="q-mr-xs" />
              History of Changes
            </div>
            <div
              v-if="!selectedRecord?.history || selectedRecord.history.length === 0"
              class="text-grey-7 q-pl-sm"
            >
              No history found
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
                    By {{ h.update_by }} at {{ new Date(h.update_at).toLocaleString() }}
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
            label="Print Label"
            color="secondary"
            icon="print"
            @click="printLabel(selectedRecord!)"
          />
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

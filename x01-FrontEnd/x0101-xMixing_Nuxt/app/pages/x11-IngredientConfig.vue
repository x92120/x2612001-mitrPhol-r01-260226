<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { appConfig } from '~/appConfig/config'
import { useAuth } from '~/composables/useAuth'
import { useQrCode } from '~/composables/useQrCode'

interface Ingredient {
  id?: number
  mat_sap_code: string
  re_code?: string
  ingredient_id: string
  name: string
  unit: string
  Group?: string
  status: string
  creat_by: string
  update_by?: string
  std_package_size?: number
  std_prebatch_batch_size?: number
}

const $q = useQuasar()
const { getAuthHeader, user } = useAuth()

// --- State ---
const ingredients = ref<Ingredient[]>([])
const loading = ref(false)

const showDialog = ref(false)
const isEditing = ref(false)

// Helper for fetch headers
const getHeaders = (extraHeaders: Record<string, string> = {}) => {
  const authHeader = getAuthHeader() as Record<string, string>
  return { ...authHeader, ...extraHeaders }
}

// Fetch ingredients from database
const fetchIngredients = async () => {
  loading.value = true
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/ingredients/?limit=1000`, {
      headers: getHeaders(),
    })
    if (response.ok) {
      ingredients.value = await response.json()
    } else {
      $q.notify({ type: 'negative', message: 'Failed to fetch ingredients' })
    }
  } catch (error) {
    console.error('Fetch error:', error)
    $q.notify({ type: 'negative', message: 'Network error' })
  } finally {
    loading.value = false
  }
}

// Load data on mount
onMounted(() => {
  fetchIngredients()
  fetchIngredients()
})

const filters = ref<Record<string, string>>({})
const showFilters = ref(false)

const filteredIngredients = computed(() => {
  return ingredients.value.filter((row) => {
    return Object.keys(filters.value).every((key) => {
      const filterVal = filters.value[key]?.toLowerCase()
      if (!filterVal) return true
      const rowVal = String((row as any)[key] || '').toLowerCase()
      return rowVal.includes(filterVal)
    })
  })
})

const resetFilters = () => {
  filters.value = {}
}

const form = ref<Ingredient>({
  mat_sap_code: '',
  re_code: '',
  ingredient_id: '',
  name: '',
  unit: 'kg',
  Group: '',
  status: 'Active',
  creat_by: '',
  update_by: '',
  std_package_size: 25.0,
  std_prebatch_batch_size: 0.0,
})

const columns: QTableColumn[] = [
  {
    name: 'mat_sap_code',
    label: 'MAT.SAP Code',
    field: 'mat_sap_code',
    align: 'left',
    sortable: true,
  },
  {
    name: 're_code',
    label: 'Re-Code',
    field: 're_code',
    align: 'left',
    sortable: true,
  },
  {
    name: 'ingredient_id',
    label: 'Ingredient ID',
    field: 'ingredient_id',
    align: 'left',
    sortable: true,
  },
  {
    name: 'name',
    label: 'Ingredient Name',
    field: 'name',
    align: 'left',
    sortable: true,
  },
  {
    name: 'unit',
    label: 'Unit',
    field: 'unit',
    align: 'left',
    sortable: true,
  },
  {
    name: 'std_package_size',
    label: 'Batch Prepare Package Size',
    field: 'std_package_size',
    align: 'left',
    sortable: true,
  },
  {
    name: 'Group',
    label: 'Group',
    field: 'Group',
    align: 'left',
    sortable: true,
  },
  {
    name: 'status',
    label: 'Status',
    field: 'status',
    align: 'center',
    sortable: true,
  },
  {
    name: 'update_by',
    label: 'Edit By',
    field: 'update_by',
    align: 'left',
    sortable: true,
  },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' },
]

// --- Actions ---
const openAddDialog = () => {
  isEditing.value = false
  form.value = {
    mat_sap_code: '',
    re_code: '',
    ingredient_id: '',
    name: '',
    unit: 'kg',
    Group: '',
    status: 'Active',
    creat_by: '',
    update_by: '',
    std_package_size: 25.0,
    std_prebatch_batch_size: 0.0,
  }
  showDialog.value = true
}

const openEditDialog = (row: Ingredient) => {
  isEditing.value = true
  form.value = { ...row }
  showDialog.value = true
}

const { generateQrDataUrl } = useQrCode()

const printLabel = async (row: Ingredient) => {
  const existingIframe = document.getElementById('print-iframe')
  if (existingIframe) {
    document.body.removeChild(existingIframe)
  }

  const iframe = document.createElement('iframe')
  iframe.id = 'print-iframe'
  iframe.style.position = 'fixed'
  iframe.style.right = '0'
  iframe.style.bottom = '0'
  iframe.style.width = '1px'
  iframe.style.height = '1px'
  iframe.style.border = '0'
  iframe.style.opacity = '0.01'
  document.body.appendChild(iframe)

  const qrData = {
    id: row.ingredient_id,
    mat: row.mat_sap_code,
    re: row.re_code,
    name: row.name
  }
  // Generate QR code locally — no internet required
  const qrDataUrl = await generateQrDataUrl(JSON.stringify(qrData), 200)

  const html = `
    <html>
      <head>
        <title>Label ${row.re_code}</title>
         <style>
          @page { size: 4in 6in; margin: 0; }
          body { font-family: Arial, sans-serif; padding: 10px; }
          .label-container { width: 4in; height: 6in; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; border: 1px dashed #ccc; }
          .title { font-size: 24pt; font-weight: bold; margin-bottom: 20px; }
          .code { font-size: 40pt; font-weight: 900; margin-bottom: 20px; color: #000; }
          .sub { font-size: 14pt; color: #555; margin-bottom: 10px; }
          .qr { margin-top: 20px; width: 200px; height: 200px; }
        </style>
      </head>
      <body>
        <div class="label-container">
           <div class="title">INGREDIENT</div>
           <div class="code">${row.re_code || row.ingredient_id}</div>
           <div class="sub">${row.name}</div>
           <div class="sub">MAT: ${row.mat_sap_code}</div>
           <div class="sub">Std Pkg: ${row.std_package_size} kg</div>
           <img class="qr" src="${qrDataUrl}" />
        </div>
      </body>
    </html>
  `
  
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

const onDelete = (ingredientId: number) => {
  $q.dialog({
    title: 'Confirm',
    message: 'Are you sure you want to delete this ingredient?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      const response = await fetch(`${appConfig.apiBaseUrl}/ingredients/${ingredientId}`, {
        method: 'DELETE',
        headers: getHeaders(),
      })
      if (response.ok) {
        $q.notify({ type: 'positive', message: 'Ingredient deleted' })
        await fetchIngredients()
        showDialog.value = false
      } else {
        $q.notify({ type: 'negative', message: 'Failed to delete ingredient' })
      }
    } catch (error) {
      console.error('Delete error:', error)
      $q.notify({ type: 'negative', message: 'Network error' })
    }
  })
}

const onSave = async () => {
  if (!form.value.mat_sap_code || !form.value.name) {
    $q.notify({ type: 'warning', message: 'MAT.SAP Code and Name are required' })
    return
  }

  // Set creat_by if creating new
  if (!isEditing.value) {
    form.value.creat_by = user.value?.username || 'system'
  }
  form.value.update_by = user.value?.username || 'system'

  try {
    const url = isEditing.value
      ? `${appConfig.apiBaseUrl}/ingredients/${form.value.id}`
      : `${appConfig.apiBaseUrl}/ingredients/`

    const method = isEditing.value ? 'PUT' : 'POST'

    const response = await fetch(url, {
      method,
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(form.value),
    })

    if (response.ok) {
      $q.notify({
        type: 'positive',
        message: isEditing.value ? 'Ingredient updated' : 'Ingredient added',
      })
      showDialog.value = false
      await fetchIngredients()
    } else {
      const error = await response.json()
      $q.notify({
        type: 'negative',
        message: error.detail || 'Failed to save ingredient',
      })
    }
  } catch (error) {
    console.error('Save error:', error)
    $q.notify({ type: 'negative', message: 'Network error' })
  }
}
</script>

<template>
  <q-page class="q-pa-md">
    <q-card>
      <q-card-section class="bg-primary text-white row items-center justify-between">
        <div class="text-h6">Ingredient</div>
        <div class="row items-center q-gutter-sm">
          <q-btn
            icon="filter_alt_off"
            label="Reset"
            flat
            dense
            color="white"
            @click="resetFilters"
          />
          <q-btn
            icon="filter_alt"
            :label="showFilters ? 'Hide' : 'Show'"
            flat
            dense
            color="white"
            @click="showFilters = !showFilters"
          />
          <q-btn
            icon="refresh"
            flat
            round
            dense
            color="white"
            @click="fetchIngredients"
            title="Refresh List"
          />
          <q-btn
            label="Add Ingredient"
            color="white"
            text-color="primary"
            unelevated
            @click="openAddDialog"
          />
        </div>
      </q-card-section>

      <q-card-section>
        <q-table
          :rows="filteredIngredients"
          :columns="columns"
          row-key="mat_sap_code"
          :loading="loading"
          flat
          bordered
        >
          <template v-slot:header="props">
            <q-tr :props="props">
              <q-th
                v-for="col in props.cols"
                :key="col.name"
                :props="props"
                style="vertical-align: bottom"
              >
                <div v-if="showFilters && col.name !== 'actions'" class="q-pb-sm">
                  <q-input
                    v-model="filters[col.field]"
                    dense
                    outlined
                    bg-color="white"
                    placeholder="Search"
                    @click.stop
                  />
                </div>
                {{ col.label }}
              </q-th>
            </q-tr>
          </template>
          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-badge
                :color="props.row.status === 'Active' ? 'positive' : 'grey'"
                :label="props.row.status"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props" align="right">
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
                icon="edit"
                color="primary"
                unelevated
                no-caps
                dense
                size="sm"
                class="q-mr-xs"
                @click="openEditDialog(props.row)"
              >
                <q-tooltip>Edit</q-tooltip>
              </q-btn>
              <q-btn
                icon="delete"
                color="negative"
                unelevated
                no-caps
                dense
                size="sm"
                @click="onDelete(props.row.id)"
              >
                <q-tooltip>Delete</q-tooltip>
              </q-btn>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Add/Edit Dialog -->
    <q-dialog v-model="showDialog" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">{{ isEditing ? 'Edit Ingredient' : 'Add New Ingredient' }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-input
            v-model="form.mat_sap_code"
            label="MAT.SAP Code *"
            dense
            autofocus
            :readonly="isEditing"
            class="q-mb-md"
          />
          <q-input v-model="form.re_code" label="Re-Code" dense class="q-mb-md" />
          <q-input v-model="form.ingredient_id" label="Ingredient ID *" dense class="q-mb-md" />
          <q-input v-model="form.name" label="Ingredient Name *" dense class="q-mb-md" />
          <q-input v-model="form.unit" label="Unit" dense class="q-mb-md" />
          <q-input
            v-model.number="form.std_package_size"
            label="Batch Prepare Package Size (kg)"
            dense
            type="number"
            class="q-mb-md"
          />
          <q-input
            v-model.number="form.std_prebatch_batch_size"
            label="Standard Prebatch Batch Size (kg)"
            dense
            type="number"
            class="q-mb-md"
          />
          <q-input v-model="form.Group" label="Group (Colour/Flavor)" dense class="q-mb-md" />
          <q-select
            v-model="form.status"
            :options="['Active', 'Inactive']"
            label="Status"
            dense
            class="q-mb-md"
          />
        </q-card-section>

        <q-card-actions align="right" class="text-primary">
          <q-btn
            v-if="isEditing"
            flat
            label="Delete"
            color="negative"
            @click="onDelete(form.id!)"
          />
          <q-space />
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn flat label="Save" @click="onSave" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

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
  warehouse?: string
  status: string
  creat_by: string
  update_by?: string
  package_container_type?: string
}

const $q = useQuasar()
const { getAuthHeader, user } = useAuth()
const { t } = useI18n()

// --- State ---
const ingredients = ref<Ingredient[]>([])
const loading = ref(false)
const warehouses = ref<any[]>([])
const warehouseOptions = computed(() => warehouses.value.map(w => w.warehouse_id))

const containerTypes = ref<any[]>([])
const packageContainerTypeOptions = computed(() => containerTypes.value.map(ct => ct.name))

const showDialog = ref(false)
const showContainerTypeDialog = ref(false)
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
      $q.notify({ type: 'negative', message: t('ingConfig.failedFetch') })
    }
  } catch (error) {
    console.error('Fetch error:', error)
    $q.notify({ type: 'negative', message: t('ingConfig.networkError') })
  } finally {
    loading.value = false
  }
}

const fetchWarehouses = async () => {
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/warehouses/`, {
      headers: getHeaders(),
    })
    if (response.ok) {
      warehouses.value = await response.json()
    }
  } catch (error) {
    console.error('Fetch warehouses error:', error)
  }
}

const fetchContainerTypes = async () => {
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/package-container-types/`, {
      headers: getHeaders(),
    })
    if (response.ok) {
      containerTypes.value = await response.json()
    }
  } catch (error) {
    console.error('Fetch container types error:', error)
  }
}

// Load data on mount
onMounted(() => {
  fetchIngredients()
  fetchWarehouses()
  fetchContainerTypes()
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
  package_container_type: 'Bag',
})

const columns = computed((): QTableColumn[] => [
  { name: 'mat_sap_code', label: t('ingConfig.matSapCode'), field: 'mat_sap_code', align: 'left', sortable: true },
  { name: 're_code', label: t('ingConfig.reCode'), field: 're_code', align: 'left', sortable: true },
  { name: 'ingredient_id', label: t('ingConfig.ingredientId'), field: 'ingredient_id', align: 'left', sortable: true },
  { name: 'name', label: t('ingConfig.ingredientName'), field: 'name', align: 'left', sortable: true },
  { name: 'package_container_type', label: t('ingConfig.containerType'), field: 'package_container_type', align: 'left', sortable: true },
  { name: 'Group', label: t('ingConfig.group'), field: 'Group', align: 'left', sortable: true },
  { name: 'warehouse', label: t('ingConfig.warehouse'), field: 'warehouse', align: 'left', sortable: true },

  { name: 'update_by', label: t('ingConfig.editBy'), field: 'update_by', align: 'left', sortable: true },
  { name: 'actions', label: t('common.actions'), field: 'actions', align: 'right' },
])

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
    warehouse: '',
    status: 'Active',
    creat_by: '',
    update_by: '',
    std_package_size: 25.0,
    package_container_type: 'Bag',
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
           <div class="sub">Container: ${row.package_container_type || 'Bag'}</div>
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
    title: t('common.confirm'),
    message: t('ingConfig.confirmDelete'),
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      const response = await fetch(`${appConfig.apiBaseUrl}/ingredients/${ingredientId}`, {
        method: 'DELETE',
        headers: getHeaders(),
      })
      if (response.ok) {
        $q.notify({ type: 'positive', message: t('ingConfig.ingredientDeleted') })
        await fetchIngredients()
        showDialog.value = false
      } else {
        $q.notify({ type: 'negative', message: t('ingConfig.failedDelete') })
      }
    } catch (error) {
      console.error('Delete error:', error)
      $q.notify({ type: 'negative', message: t('ingConfig.networkError') })
    }
  })
}

const onSave = async () => {
  if (!form.value.mat_sap_code || !form.value.name) {
    $q.notify({ type: 'warning', message: t('ingConfig.matSapRequired') })
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
        message: isEditing.value ? t('ingConfig.ingredientUpdated') : t('ingConfig.ingredientAdded'),
      })
      showDialog.value = false
      await fetchIngredients()
    } else {
      const error = await response.json()
      $q.notify({
        type: 'negative',
        message: error.detail || t('ingConfig.failedSave'),
      })
    }
  } catch (error) {
    console.error('Save error:', error)
    $q.notify({ type: 'negative', message: t('ingConfig.networkError') })
  }
}

// --- Container Type Management ---
const containerTypeForm = ref({ id: null as number | null, name: '' })
const isEditingContainerType = ref(false)

const openContainerTypeManager = () => {
  showContainerTypeDialog.value = true
}

const editContainerType = (ct: any) => {
  containerTypeForm.value = { ...ct }
  isEditingContainerType.value = true
}

const resetContainerTypeForm = () => {
  containerTypeForm.value = { id: null, name: '' }
  isEditingContainerType.value = false
}

const onSaveContainerType = async () => {
  if (!containerTypeForm.value.name) return

  try {
    const isEdit = !!containerTypeForm.value.id
    const url = isEdit
      ? `${appConfig.apiBaseUrl}/package-container-types/${containerTypeForm.value.id}`
      : `${appConfig.apiBaseUrl}/package-container-types/`
    const method = isEdit ? 'PUT' : 'POST'

    const response = await fetch(url, {
      method,
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ name: containerTypeForm.value.name }),
    })

    if (response.ok) {
      $q.notify({ type: 'positive', message: 'Container type saved' })
      resetContainerTypeForm()
      await fetchContainerTypes()
    } else {
      const error = await response.json()
      $q.notify({ type: 'negative', message: error.detail || 'Save failed' })
    }
  } catch (error) {
    console.error('Save container type error:', error)
    $q.notify({ type: 'negative', message: 'Network error' })
  }
}

const onDeleteContainerType = async (id: number) => {
  $q.dialog({
    title: 'Confirm Delete',
    message: 'Are you sure you want to delete this container type?',
    cancel: true,
  }).onOk(async () => {
    try {
      const response = await fetch(`${appConfig.apiBaseUrl}/package-container-types/${id}`, {
        method: 'DELETE',
        headers: getHeaders(),
      })
      if (response.ok) {
        $q.notify({ type: 'positive', message: 'Container type deleted' })
        await fetchContainerTypes()
      } else {
        $q.notify({ type: 'negative', message: 'Delete failed' })
      }
    } catch (error) {
      console.error('Delete container type error:', error)
      $q.notify({ type: 'negative', message: 'Network error' })
    }
  })
}
</script>

<template>
  <q-page class="q-pa-md">
    <q-card>
      <q-card-section class="bg-primary text-white row items-center justify-between">
        <div class="text-h6">{{ t('ingConfig.title') }}</div>
        <div class="row items-center q-gutter-sm">
          <q-btn
            icon="filter_alt_off"
            :label="t('common.reset')"
            flat
            dense
            color="white"
            @click="resetFilters"
          />
          <q-btn
            icon="filter_alt"
            :label="showFilters ? t('common.close') : t('common.view')"
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
            :title="t('ingConfig.refreshList')"
          />
          <q-btn
            :label="t('ingConfig.addIngredient')"
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
                    :placeholder="t('common.search')"
                    @click.stop
                  />
                </div>
                {{ col.label }}
              </q-th>
            </q-tr>
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
                <q-tooltip>{{ t('ingConfig.printLabel') }}</q-tooltip>
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
                <q-tooltip>{{ t('common.edit') }}</q-tooltip>
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
                <q-tooltip>{{ t('common.delete') }}</q-tooltip>
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
          <div class="text-h6">{{ isEditing ? t('ingConfig.editIngredient') : t('ingConfig.addNewIngredient') }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-input
            v-model="form.mat_sap_code"
            :label="t('ingConfig.matSapCode') + ' *'"
            dense
            autofocus
            :readonly="isEditing"
            class="q-mb-md"
          />
          <q-input v-model="form.re_code" :label="t('ingConfig.reCode')" dense class="q-mb-md" />
          <q-input v-model="form.ingredient_id" :label="t('ingConfig.ingredientId') + ' *'" dense class="q-mb-md" />
          <q-input v-model="form.name" :label="t('ingConfig.ingredientName') + ' *'" dense class="q-mb-md" />
          <q-input v-model="form.unit" :label="t('ingConfig.unit')" dense class="q-mb-md" />
          
          <q-select
            v-model="form.package_container_type"
            :options="packageContainerTypeOptions"
            :label="t('ingConfig.containerType')"
            dense
            class="q-mb-md"
          >
            <template v-slot:after>
              <q-btn
                round
                dense
                flat
                icon="settings"
                color="primary"
                @click.stop="openContainerTypeManager"
              >
                <q-tooltip>Manage Container Types</q-tooltip>
              </q-btn>
            </template>
          </q-select>

          <q-input v-model="form.Group" :label="t('ingConfig.groupColorFlavor')" dense class="q-mb-md" />
          <q-select
            v-model="form.warehouse"
            :options="warehouseOptions"
            :label="t('ingConfig.warehouse')"
            dense
            class="q-mb-md"
          />
          <q-select
            v-model="form.status"
            :options="['Active', 'Inactive']"
            :label="t('common.status')"
            dense
            class="q-mb-md"
          />
        </q-card-section>

        <q-card-actions align="right" class="text-primary">
          <q-btn
            v-if="isEditing"
            flat
            :label="t('common.delete')"
            color="negative"
            @click="onDelete(form.id!)"
          />
          <q-space />
          <q-btn flat :label="t('common.cancel')" v-close-popup />
          <q-btn flat :label="t('common.save')" @click="onSave" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Container Type Management Dialog -->
    <q-dialog v-model="showContainerTypeDialog">
      <q-card style="min-width: 350px">
        <q-card-section class="bg-primary text-white row items-center">
          <div class="text-h6">Manage Container Types</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div class="row q-gutter-sm items-end q-mb-md">
            <q-input
              v-model="containerTypeForm.name"
              label="New Type Name"
              dense
              outlined
              class="col"
            />
            <q-btn
              :icon="isEditingContainerType ? 'save' : 'add'"
              :label="isEditingContainerType ? 'Update' : 'Add'"
              color="primary"
              @click="onSaveContainerType"
            />
            <q-btn
              v-if="isEditingContainerType"
              icon="cancel"
              flat
              dense
              bg-color="grey-2"
              @click="resetContainerTypeForm"
            />
          </div>

          <q-list bordered separator>
            <q-item v-for="ct in containerTypes" :key="ct.id">
              <q-item-section>
                {{ ct.name }}
              </q-item-section>
              <q-item-section side>
                <div class="row q-gutter-xs">
                  <q-btn icon="edit" flat round dense size="sm" color="blue" @click="editContainerType(ct)" />
                  <q-btn icon="delete" flat round dense size="sm" color="negative" @click="onDeleteContainerType(ct.id)" />
                </div>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

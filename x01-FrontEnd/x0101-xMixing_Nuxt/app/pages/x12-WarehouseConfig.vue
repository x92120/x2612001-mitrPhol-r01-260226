<script setup lang="ts">
import { ref } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'

interface Warehouse {
  id: string
  name: string
  description: string
}

const $q = useQuasar()
const { t } = useI18n()

// --- State ---
const warehouses = ref<Warehouse[]>([
  {
    id: 'WH-001',
    name: 'Raw Material Warehouse',
    description: 'Main storage for raw ingredients',
  },
  {
    id: 'WH-002',
    name: 'Packaging Warehouse',
    description: 'Storage for packaging materials',
  },
  {
    id: 'WH-Cooling',
    name: 'Cooling Storage',
    description: 'Temperature controlled storage for sensitive items',
  },
  {
    id: 'Re Claim',
    name: 'Re Claim from Process',
    description: 'Items reclaimed from the production line',
  },
])

const showDialog = ref(false)
const isEditing = ref(false)

const form = ref<Warehouse>({
  id: '',
  name: '',
  description: '',
})

const columns = computed((): QTableColumn[] => [
  { name: 'id', label: t('whConfig.warehouseId'), field: 'id', align: 'left', sortable: true },
  { name: 'name', label: t('whConfig.warehouseName'), field: 'name', align: 'left', sortable: true },
  { name: 'description', label: t('common.description'), field: 'description', align: 'left', sortable: true },
  { name: 'actions', label: t('common.actions'), field: 'actions', align: 'right' },
])

// --- Actions ---
const openAddDialog = () => {
  isEditing.value = false
  form.value = {
    id: '',
    name: '',
    description: '',
  }
  showDialog.value = true
}

const openEditDialog = (row: Warehouse) => {
  isEditing.value = true
  form.value = { ...row }
  showDialog.value = true
}

const onDelete = (id: string) => {
  $q.dialog({
    title: t('common.confirm'),
    message: t('whConfig.confirmDelete'),
    cancel: true,
    persistent: true,
  }).onOk(() => {
    warehouses.value = warehouses.value.filter((w) => w.id !== id)
    $q.notify({ type: 'positive', message: t('whConfig.warehouseDeleted') })
  })
}

const onSave = () => {
  if (!form.value.id || !form.value.name) {
    $q.notify({ type: 'warning', message: t('whConfig.idNameRequired') })
    return
  }

  if (isEditing.value) {
    const index = warehouses.value.findIndex((w) => w.id === form.value.id)
    if (index !== -1) {
      warehouses.value[index] = { ...form.value }
      $q.notify({ type: 'positive', message: t('whConfig.warehouseUpdated') })
    }
  } else {
    if (warehouses.value.some((w) => w.id === form.value.id)) {
      $q.notify({ type: 'negative', message: t('whConfig.warehouseIdExists') })
      return
    }
    warehouses.value.push({ ...form.value })
    $q.notify({ type: 'positive', message: t('whConfig.warehouseAdded') })
  }
  showDialog.value = false
}
</script>

<template>
  <q-page class="q-pa-md">
    <q-card>
      <q-card-section class="bg-primary text-white row items-center justify-between">
        <div class="text-h6">{{ t('whConfig.title') }}</div>
        <q-btn
          :label="t('whConfig.addWarehouse')"
          color="white"
          text-color="primary"
          unelevated
          @click="openAddDialog"
        />
      </q-card-section>

      <q-card-section>
        <q-table :rows="warehouses" :columns="columns" row-key="id" flat bordered>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                icon="edit"
                color="primary"
                flat
                round
                size="sm"
                @click="openEditDialog(props.row)"
              />
              <q-btn
                icon="delete"
                color="negative"
                flat
                round
                size="sm"
                @click="onDelete(props.row.id)"
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Add/Edit Dialog -->
    <q-dialog v-model="showDialog" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">{{ isEditing ? t('whConfig.editWarehouse') : t('whConfig.addNewWarehouse') }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-input
            v-model="form.id"
            :label="t('whConfig.warehouseId') + ' *'"
            dense
            autofocus
            :readonly="isEditing"
            class="q-mb-md"
          />
          <q-input v-model="form.name" :label="t('whConfig.warehouseName') + ' *'" dense class="q-mb-md" />
          <q-input v-model="form.description" :label="t('common.description')" type="textarea" dense />
        </q-card-section>

        <q-card-actions align="right" class="text-primary">
          <q-btn flat :label="t('common.cancel')" v-close-popup />
          <q-btn flat :label="t('common.save')" @click="onSave" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

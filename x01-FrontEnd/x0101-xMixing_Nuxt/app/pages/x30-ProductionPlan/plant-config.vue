<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { appConfig } from '~/appConfig/config'

interface Plant {
  plantID: string
  plantName: string
  plantCapacity: number
  plantDescription: string
}

const $q = useQuasar()

// --- State ---
const plants = ref<Plant[]>([])

const showDialog = ref(false)
const isEditing = ref(false)

const form = ref<Plant>({
  plantID: '',
  plantName: '',
  plantCapacity: 0,
  plantDescription: '',
})

const columns: QTableColumn[] = [
  { name: 'plantID', label: 'Plant ID', field: 'plantID', align: 'left', sortable: true },
  { name: 'plantName', label: 'Plant Name', field: 'plantName', align: 'left', sortable: true },
  {
    name: 'plantCapacity',
    label: 'Capacity (L)',
    field: 'plantCapacity',
    align: 'right',
    sortable: true,
  },
  {
    name: 'plantDescription',
    label: 'Description',
    field: 'plantDescription',
    align: 'left',
    sortable: true,
  },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'right' },
]

// --- API Functions ---
const fetchPlants = async () => {
  try {
    const response = await fetch(`${appConfig.apiBaseUrl}/plants/`)
    if (response.ok) {
      const data = await response.json()
      plants.value = data.map((p: any) => ({
        plantID: p.plant_id,
        plantName: p.plant_name,
        plantCapacity: p.plant_capacity,
        plantDescription: p.plant_description,
      }))
    }
  } catch (error) {
    console.error('Error fetching plants:', error)
    $q.notify({ type: 'negative', message: 'Failed to fetch plants' })
  }
}

// --- Actions ---
const openAddDialog = () => {
  isEditing.value = false
  form.value = { plantID: '', plantName: '', plantCapacity: 0, plantDescription: '' }
  showDialog.value = true
}

const openEditDialog = (row: Plant) => {
  isEditing.value = true
  form.value = { ...row }
  showDialog.value = true
}

const onDelete = (plantID: string) => {
  $q.dialog({
    title: 'Confirm',
    message: 'Are you sure you want to delete this plant?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      const response = await fetch(`${appConfig.apiBaseUrl}/plants/${plantID}`, {
        method: 'DELETE',
      })
      if (response.ok) {
        $q.notify({ type: 'positive', message: 'Plant deleted' })
        fetchPlants()
      } else {
        $q.notify({ type: 'negative', message: 'Failed to delete plant' })
      }
    } catch (error) {
      console.error('Error deleting plant:', error)
      $q.notify({ type: 'negative', message: 'Error deleting plant' })
    }
  })
}

const onSave = async () => {
  if (!form.value.plantID || !form.value.plantName) {
    $q.notify({ type: 'warning', message: 'ID and Name are required' })
    return
  }

  try {
    const payload = {
      plant_id: form.value.plantID,
      plant_name: form.value.plantName,
      plant_capacity: form.value.plantCapacity,
      plant_description: form.value.plantDescription,
      status: 'Active',
    }

    if (isEditing.value) {
      const response = await fetch(`${appConfig.apiBaseUrl}/plants/${form.value.plantID}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plant_name: form.value.plantName,
          plant_capacity: form.value.plantCapacity,
          plant_description: form.value.plantDescription,
          status: 'Active',
        }),
      })
      if (response.ok) {
        $q.notify({ type: 'positive', message: 'Plant updated' })
        fetchPlants()
      } else {
        const err = await response.json()
        $q.notify({ type: 'negative', message: err.detail || 'Failed to update plant' })
        return
      }
    } else {
      const response = await fetch(`${appConfig.apiBaseUrl}/plants/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (response.ok) {
        $q.notify({ type: 'positive', message: 'Plant added' })
        fetchPlants()
      } else {
        const err = await response.json()
        $q.notify({ type: 'negative', message: err.detail || 'Failed to add plant' })
        return
      }
    }
    showDialog.value = false
  } catch (error) {
    console.error('Error saving plant:', error)
    $q.notify({ type: 'negative', message: 'Error saving plant' })
  }
}

onMounted(() => {
  fetchPlants()
})
</script>

<template>
  <q-page class="q-pa-md">
    <q-card>
      <q-card-section class="bg-primary text-white row items-center justify-between">
        <div class="row items-center q-gutter-sm">
          <q-btn
            icon="arrow_back"
            color="white"
            text-color="primary"
            unelevated
            round
            @click="$router.push({ name: 'ProductionPlan' })"
          >
            <q-tooltip>Back to Production Plan</q-tooltip>
          </q-btn>
          <div class="text-h6">Plant Configuration</div>
        </div>
        <q-btn
          label="Add Plant"
          color="white"
          text-color="primary"
          unelevated
          @click="openAddDialog"
        />
      </q-card-section>

      <q-card-section>
        <q-table :rows="plants" :columns="columns" row-key="plantID" flat bordered>
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
                @click="onDelete(props.row.plantID)"
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
          <div class="text-h6">{{ isEditing ? 'Edit Plant' : 'Add New Plant' }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-input
            v-model="form.plantID"
            label="Plant ID *"
            dense
            autofocus
            :readonly="isEditing"
            class="q-mb-md"
          />
          <q-input v-model="form.plantName" label="Plant Name *" dense class="q-mb-md" />
          <q-input
            v-model.number="form.plantCapacity"
            label="Capacity"
            type="number"
            dense
            class="q-mb-md"
          />
          <q-input v-model="form.plantDescription" label="Description" type="textarea" dense />
        </q-card-section>

        <q-card-actions align="right" class="text-primary">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn flat label="Save" @click="onSave" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { QTableColumn } from 'quasar'
import { useQuasar } from 'quasar'
import { appConfig } from '~/appConfig/config'
import { useAuth } from '~/composables/useAuth'

interface ReportItem {
  ingredient_id: string
  ingredient_name: string
  total_intake_vol: number
  total_package_intake: number
  intake_count: number
}

const $q = useQuasar()
const { getAuthHeader } = useAuth()
const startDate = ref('')
const endDate = ref('')
const reportData = ref<ReportItem[]>([])
const loading = ref(false)
const columns: QTableColumn[] = [
  { name: 'ingredient_id', label: 'Ingredient ID', field: 'ingredient_id', sortable: true, align: 'left' },
  { name: 'ingredient_name', label: 'Ingredient Name', field: 'ingredient_name', sortable: true, align: 'left' },
  { 
    name: 'total_intake_vol', 
    label: 'Total Volume (kg)', 
    field: 'total_intake_vol', 
    sortable: true, 
    format: (val: number) => val.toFixed(2) 
  },
  { name: 'total_package_intake', label: 'Total Packages', field: 'total_package_intake', sortable: true },
  { name: 'intake_count', label: 'No. of Intakes', field: 'intake_count', sortable: true },
]

const fetchReport = async () => {
  if (!startDate.value || !endDate.value) {
    $q.notify({
      type: 'warning',
      message: 'Please select both start and end dates',
      position: 'top'
    })
    return
  }

  loading.value = true
  try {
    const response = await fetch(
      `${appConfig.apiBaseUrl}/reports/ingredient-intake-summary?start_date=${startDate.value}&end_date=${endDate.value}`,
      {
        headers: getAuthHeader() as Record<string, string>,
      }
    )

    if (response.ok) {
      reportData.value = await response.json()
    } else {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to fetch report')
    }
  } catch (error) {
    console.error('Report fetch error:', error)
    $q.notify({
      type: 'negative',
      message: 'Failed to load report data',
      position: 'top'
    })
  } finally {
    loading.value = false
  }
}

const grandTotalVolume = computed(() => {
  return reportData.value.reduce((acc, item) => acc + item.total_intake_vol, 0)
})

const grandTotalPackages = computed(() => {
  return reportData.value.reduce((acc, item) => acc + item.total_package_intake, 0)
})
</script>

<template>
  <q-page class="q-pa-md">
    <div class="text-h5 q-mb-md">Ingredient Intake Summary Report</div>

    <!-- Filters -->
    <q-card class="q-mb-md">
      <q-card-section>
        <div class="row q-col-gutter-md items-center">
          <div class="col-12 col-md-3">
            <q-input filled v-model="startDate" label="Start Date" type="date" stack-label />
          </div>
          <div class="col-12 col-md-3">
            <q-input filled v-model="endDate" label="End Date" type="date" stack-label />
          </div>
          <div class="col-12 col-md-2">
            <q-btn 
              color="primary" 
              icon="search" 
              label="Generate Report" 
              @click="fetchReport" 
              :loading="loading"
              class="full-width"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Report Table -->
    <q-table
      title="Summary by Ingredient"
      :rows="reportData"
      :columns="columns"
      row-key="ingredient_id"
      :loading="loading"
      flat
      bordered
      :pagination="{ rowsPerPage: 20 }"
    >
      <template v-slot:bottom-row>
        <q-tr class="bg-grey-2 text-weight-bold">
          <q-td colspan="2" class="text-right">Grand Total:</q-td>
          <q-td class="text-right">{{ grandTotalVolume.toFixed(2) }}</q-td>
          <q-td class="text-right">{{ grandTotalPackages }}</q-td>
          <q-td></q-td>
        </q-tr>
      </template>
    </q-table>
  </q-page>
</template>

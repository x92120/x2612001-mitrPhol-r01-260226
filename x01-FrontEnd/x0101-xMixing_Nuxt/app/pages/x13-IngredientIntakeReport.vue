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
const { t } = useI18n()
const startDate = ref('')
const endDate = ref('')
const reportData = ref<ReportItem[]>([])
const loading = ref(false)

const parseInputDate = (val: string | null | undefined) => {
  if (!val || val === '--/--/----') return null
  const parts = val.split('/')
  if (parts.length === 3 && parts[0] && parts[1] && parts[2]) {
    const day = parseInt(parts[0])
    const month = parseInt(parts[1]) - 1
    const year = parseInt(parts[2])
    const d = new Date(year, month, day)
    return isNaN(d.getTime()) ? null : d
  }
  const d = new Date(val)
  return isNaN(d.getTime()) ? null : d
}

const formatDateToApi = (val: string) => {
  const d = parseInputDate(val)
  if (!d) return ''
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
const columns = computed((): QTableColumn[] => [
  { name: 'ingredient_id', label: t('ingConfig.ingredientId'), field: 'ingredient_id', sortable: true, align: 'left' },
  { name: 'ingredient_name', label: t('ingConfig.ingredientName'), field: 'ingredient_name', sortable: true, align: 'left' },
  { name: 'total_intake_vol', label: t('report.totalVolume'), field: 'total_intake_vol', sortable: true, format: (val: number) => val.toFixed(2) },
  { name: 'total_package_intake', label: t('report.totalPackages'), field: 'total_package_intake', sortable: true },
  { name: 'intake_count', label: t('report.noIntakes'), field: 'intake_count', sortable: true },
])

const fetchReport = async () => {
  if (!startDate.value || !endDate.value) {
    $q.notify({
      type: 'warning',
      message: t('report.selectDates'),
      position: 'top'
    })
    return
  }

  loading.value = true
  try {
    const response = await fetch(
      `${appConfig.apiBaseUrl}/reports/ingredient-intake-summary?start_date=${formatDateToApi(startDate.value)}&end_date=${formatDateToApi(endDate.value)}`,
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
      message: t('report.failedLoad'),
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
    <div class="text-h5 q-mb-md">{{ t('report.title') }}</div>

    <!-- Filters -->
    <q-card class="q-mb-md">
      <q-card-section>
        <div class="row q-col-gutter-md items-center">
          <div class="col-12 col-md-3">
            <q-input filled v-model="startDate" :label="t('report.startDate')" mask="##/##/####" placeholder="DD/MM/YYYY">
              <template v-slot:append>
                <q-icon name="event" class="cursor-pointer">
                  <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                    <q-date v-model="startDate" mask="DD/MM/YYYY">
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
            <q-input filled v-model="endDate" :label="t('report.endDate')" mask="##/##/####" placeholder="DD/MM/YYYY">
              <template v-slot:append>
                <q-icon name="event" class="cursor-pointer">
                  <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                    <q-date v-model="endDate" mask="DD/MM/YYYY">
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
            <q-btn 
              color="primary" 
              icon="search" 
              :label="t('report.generateReport')" 
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
      :title="t('report.summaryByIngredient')"
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
          <q-td colspan="2" class="text-right">{{ t('report.grandTotal') }}</q-td>
          <q-td class="text-right">{{ grandTotalVolume.toFixed(2) }}</q-td>
          <q-td class="text-right">{{ grandTotalPackages }}</q-td>
          <q-td></q-td>
        </q-tr>
      </template>
    </q-table>
  </q-page>
</template>

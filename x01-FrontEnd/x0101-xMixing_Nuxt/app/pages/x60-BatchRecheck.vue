<script setup lang="ts">
import { ref } from 'vue'
import { useQuasar } from 'quasar'

const $q = useQuasar()

const scanQuery = ref('')
const isLoading = ref(false)
const currentBatch = ref<any>(null)

// Mock Data
const mockBatch = {
  batch_id: 'B-2025-001-01',
  plan_id: 'PLAN-2025-001',
  sku_id: 'S77CA4SN02',
  sku_name: 'Caramel Syrup Senorita',
  batch_size: 150.0,
  unit: 'kg',
  status: 'Production',
  created_at: '2025-01-14 10:00',
  plant: 'Mixing 1'
}

const historyLog = ref([
  { id: 1, batch_id: 'B-2025-001-00', sku_id: 'S77CA4SN02', check_time: '2025-01-14 09:30', status: 'Passed', checked_by: 'cj' }
])

const actualWeight = ref('')
const checkRemarks = ref('')

const onScan = () => {
    if(!scanQuery.value) return
    isLoading.value = true
    setTimeout(() => {
        currentBatch.value = { ...mockBatch, batch_id: scanQuery.value }
        actualWeight.value = ''
        checkRemarks.value = ''
        isLoading.value = false
        $q.notify({ type: 'positive', message: 'Batch Found' })
    }, 500)
}


const onPass = () => {
    if(!currentBatch.value) return
    $q.notify({ type: 'positive', message: 'Batch Marked as PASSED' })
    historyLog.value.unshift({
        id: Date.now(),
        batch_id: currentBatch.value.batch_id,
        sku_id: currentBatch.value.sku_id,
        check_time: new Date().toLocaleString(),
        status: 'Passed',
        checked_by: 'cj'
    })
    currentBatch.value = null
    scanQuery.value = ''
}

const onFail = () => {
    if(!currentBatch.value) return
    $q.notify({ type: 'negative', message: 'Batch Marked as FAILED' })
     historyLog.value.unshift({
        id: Date.now(),
        batch_id: currentBatch.value.batch_id,
        sku_id: currentBatch.value.sku_id,
        check_time: new Date().toLocaleString(),
        status: 'Failed',
        checked_by: 'cj'
    })
    currentBatch.value = null
    scanQuery.value = ''
}

</script>

<template>
  <q-page class="q-pa-md bg-grey-2">
    <!-- Header / Scan Section -->
    <q-card class="q-mb-md shadow-2 rounded-borders">
        <q-card-section class="row items-center q-col-gutter-md">
            <div class="col-12 col-md-3">
                <div class="text-h6 text-primary text-weight-bold">Batch Re-Check</div>
                <div class="text-caption text-grey-7">Verify finished batch weight and quality</div>
            </div>
            <div class="col-12 col-md-6">
                 <q-input 
                    outlined 
                    v-model="scanQuery" 
                    label="Scan Batch ID / QR Code" 
                    dense 
                    color="primary"
                    @keyup.enter="onScan"
                    autofocus
                 >
                    <template v-slot:prepend><q-icon name="qr_code_scanner" /></template>
                    <template v-slot:append>
                        <q-btn label="Search" color="primary" flat @click="onScan" :loading="isLoading" />
                    </template>
                 </q-input>
            </div>
        </q-card-section>
    </q-card>

    <!-- Main Content Grid -->
    <div class="row q-col-gutter-md">
        
        <!-- Left: Batch Info -->
        <div class="col-12 col-md-8">
            <q-card class="shadow-2 rounded-borders full-height">
                <q-card-section class="bg-blue-grey-1 text-weight-bold row items-center">
                    <q-icon name="info" class="q-mr-sm" size="sm" /> 
                    Batch Information
                    <q-space />
                    <q-chip v-if="currentBatch" :label="currentBatch.status" color="blue" text-color="white" size="sm" />
                </q-card-section>

                <q-card-section v-if="!currentBatch" class="text-center q-pa-xl text-grey-6 text-italic">
                    <q-icon name="fact_check" size="4rem" class="q-mb-sm" />
                    <div>Please scan a batch to view details</div>
                </q-card-section>

                <q-card-section v-else>
                    <div class="row q-col-gutter-lg">
                        <div class="col-12 col-sm-6">
                            <q-item-label caption>Batch ID</q-item-label>
                            <div class="text-h6 text-mono">{{ currentBatch.batch_id }}</div>
                        </div>
                        <div class="col-12 col-sm-6">
                            <q-item-label caption>Plan ID</q-item-label>
                            <div class="text-subtitle1">{{ currentBatch.plan_id }}</div>
                        </div>
                        <div class="col-12">
                            <q-item-label caption>SKU</q-item-label>
                            <div class="text-h5 text-primary text-weight-bold">{{ currentBatch.sku_name }}</div>
                            <div class="text-subtitle2 text-grey-7">{{ currentBatch.sku_id }}</div>
                        </div>
                        <div class="col-12 col-sm-6">
                            <q-item-label caption>Target Weight</q-item-label>
                            <div class="text-h4 text-weight-bolder">{{ currentBatch.batch_size }} <span class="text-h6 text-grey">kg</span></div>
                        </div>
                         <div class="col-12 col-sm-6">
                            <q-item-label caption>Plant / Line</q-item-label>
                            <div class="text-subtitle1">{{ currentBatch.plant }}</div>
                        </div>
                    </div>
                </q-card-section>

                <q-separator />

                <q-card-section v-if="currentBatch">
                    <div class="text-subtitle2 q-mb-sm">Verification</div>
                    <div class="row q-col-gutter-md items-end">
                        <div class="col-12 col-sm-4">
                            <q-input outlined v-model="actualWeight" label="Actual Weight (kg)" dense type="number" suffix="kg" />
                        </div>
                         <div class="col-12 col-sm-8">
                            <q-input outlined v-model="checkRemarks" label="Remarks / QC Note" dense />
                        </div>
                    </div>
                </q-card-section>

                <q-card-actions v-if="currentBatch" align="right" class="q-pa-md bg-grey-1">
                    <q-btn label="Fail / Reject" color="negative" icon="close" flat size="lg" @click="onFail" />
                    <q-space />
                    <q-btn label="Confirm Pass" color="positive" icon="check" unelevated size="lg" class="q-px-xl" @click="onPass" />
                </q-card-actions>
            </q-card>
        </div>

        <!-- Right: Recent History -->
        <div class="col-12 col-md-4">
            <q-card class="shadow-2 rounded-borders full-height">
                 <q-card-section class="bg-blue-grey-1 text-weight-bold">
                    <q-icon name="history" class="q-mr-sm" size="sm" /> 
                    Recent Checks
                </q-card-section>
                <q-list separator>
                    <q-item v-for="log in historyLog" :key="log.id">
                        <q-item-section>
                            <q-item-label class="text-weight-bold">{{ log.batch_id }}</q-item-label>
                            <q-item-label caption>{{ log.check_time }}</q-item-label>
                        </q-item-section>
                        <q-item-section side>
                            <q-chip :color="log.status === 'Passed' ? 'positive' : 'negative'" text-color="white" size="sm">
                                {{ log.status }}
                            </q-chip>
                        </q-item-section>
                    </q-item>
                    <q-item v-if="historyLog.length === 0">
                        <q-item-section class="text-grey text-center text-italic">No recent history</q-item-section>
                    </q-item>
                </q-list>
            </q-card>
        </div>
    </div>
  </q-page>
</template>

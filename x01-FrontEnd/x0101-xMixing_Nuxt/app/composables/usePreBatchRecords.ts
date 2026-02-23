/**
 * usePreBatchRecords — PreBatch CRUD, delete, auth
 */
import { ref, computed, watch } from 'vue'
import { appConfig } from '../appConfig/config'
import type { QTableColumn } from 'quasar'

export interface RecordDeps {
    $q: any
    getAuthHeader: () => Record<string, string>
    t: (key: string, params?: any) => string
    user: any
    formatDate: (date: any) => string
    // Cross-composable refs
    selectedBatch: any
    selectedReCode: any
    requireVolume: any
    selectableIngredients: any
    requestBatch: any
    // Functions
    fetchPrebatchItems: (batchId: string) => Promise<void>
    finalizeBatchPreparation: (batchId: number) => Promise<void>
}

export function usePreBatchRecords(deps: RecordDeps) {
    const { $q, getAuthHeader, t, formatDate } = deps

    // --- State ---
    const preBatchLogs = ref<any[]>([])
    const recordToDelete = ref<any>(null)
    const showDeleteDialog = ref(false)
    const deleteInput = ref('')
    const isPackageSizeLocked = ref(true)
    const showAuthDialog = ref(false)
    const authPassword = ref('')
    const selectedPreBatchLogs = ref<any[]>([])

    // --- Columns ---
    const prebatchColumns: QTableColumn[] = [
        { name: 'batch_id', align: 'left', label: 'Batch ID', field: 'batch_record_id', format: (val: string) => val.split('-').slice(0, 6).join('-'), classes: 'text-caption' },
        { name: 're_code', align: 'left', label: 'Ingredient', field: 're_code', sortable: true },
        { name: 'package_no', align: 'center', label: 'Pkg', field: 'package_no' },
        { name: 'net_volume', align: 'right', label: 'Net (kg)', field: 'net_volume', format: (val: any) => Number(val).toFixed(4) },
        { name: 'intake_lot_id', align: 'left', label: 'Intake Lot', field: 'intake_lot_id', sortable: true },
        { name: 'reprint', align: 'center', label: 'Print', field: 'id' },
        { name: 'actions', align: 'center', label: '', field: 'id' }
    ]

    // --- Computed ---
    const filteredPreBatchLogs = computed(() => preBatchLogs.value)

    const totalCompletedWeight = computed(() => {
        if (!deps.selectedBatch.value || !deps.selectedReCode.value) return 0
        const batchId = deps.selectedBatch.value.batch_id
        const ingLogs = preBatchLogs.value.filter(log =>
            log.re_code === deps.selectedReCode.value &&
            log.batch_record_id.startsWith(batchId)
        )
        return ingLogs.reduce((sum, log) => sum + (Number(log.net_volume) || 0), 0)
    })

    const completedCount = computed(() => {
        if (!deps.selectedBatch.value || !deps.selectedReCode.value) return 0
        const batchId = deps.selectedBatch.value.batch_id
        return preBatchLogs.value.filter(log =>
            log.re_code === deps.selectedReCode.value &&
            log.batch_record_id.startsWith(batchId)
        ).length
    })

    const nextPackageNo = computed(() => {
        if (!deps.selectedBatch.value || !deps.selectedReCode.value) return 1
        const batchId = deps.selectedBatch.value.batch_id
        const existingNos = preBatchLogs.value
            .filter(log => log.re_code === deps.selectedReCode.value && log.batch_record_id.startsWith(batchId))
            .map(log => Number(log.package_no))
            .sort((a, b) => a - b)
        let next = 1
        while (existingNos.includes(next)) {
            next++
        }
        return next
    })

    const preBatchSummary = computed(() => {
        const logs = filteredPreBatchLogs.value
        const totalNetWeight = logs.reduce((sum, log) => sum + (log.net_volume || 0), 0)
        const count = logs.length
        const targetW = deps.requireVolume.value || 0
        const errorVol = totalNetWeight - targetW
        return {
            count,
            totalNetWeight: totalNetWeight.toFixed(4),
            targetCount: deps.requestBatch.value || 0,
            targetWeight: targetW.toFixed(4),
            errorVolume: errorVol.toFixed(4),
            errorColor: errorVol > 0 ? 'text-red' : (errorVol < 0 ? 'text-orange' : 'text-green')
        }
    })

    // --- Functions ---
    const fetchPreBatchRecords = async () => {
        if (!deps.selectedBatch.value) return
        try {
            const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-recs/by-batch/${deps.selectedBatch.value.batch_id}`, {
                headers: getAuthHeader() as Record<string, string>
            })
            preBatchLogs.value = data
        } catch (error) {
            console.error('Error fetching prebatch records:', error)
        }
    }

    const executeDeletion = async (record: any) => {
        try {
            await $fetch(`${appConfig.apiBaseUrl}/prebatch-recs/${record.id}`, {
                method: 'DELETE',
                headers: getAuthHeader() as Record<string, string>
            })
            $q.notify({ type: 'positive', message: `Package #${record.package_no} cancelled. Inventory restored.`, icon: 'restore' })
            showDeleteDialog.value = false
            recordToDelete.value = null
            deleteInput.value = ''
            await fetchPreBatchRecords()
            if (deps.selectedBatch.value) {
                await deps.fetchPrebatchItems(deps.selectedBatch.value.batch_id)
            }
        } catch (err) {
            console.error('Error deleting record:', err)
            $q.notify({ type: 'negative', message: 'Failed to cancel record' })
        }
    }

    const onDeleteRecord = (record: any) => {
        recordToDelete.value = record
        deleteInput.value = ''
        showDeleteDialog.value = true
    }

    const onConfirmDeleteManual = async () => {
        if (!recordToDelete.value) return
        const val = deleteInput.value.trim()
        if (val === String(recordToDelete.value.package_no) || val === recordToDelete.value.batch_record_id) {
            await executeDeletion(recordToDelete.value)
        } else {
            $q.notify({ type: 'negative', message: 'Invalid input. Please scan the label or type the exact package number.', position: 'top' })
        }
    }

    const onDeleteScanEnter = async () => {
        if (!showDeleteDialog.value || !recordToDelete.value) return
        if (deleteInput.value === recordToDelete.value.batch_record_id) {
            await executeDeletion(recordToDelete.value)
        } else {
            $q.notify({ type: 'negative', message: `Invalid code! Expected: ${recordToDelete.value.batch_record_id}`, position: 'top', timeout: 3000 })
        }
    }

    const unlockPackageSize = () => {
        if (!isPackageSizeLocked.value) {
            isPackageSizeLocked.value = true
            return
        }
        authPassword.value = ''
        showAuthDialog.value = true
    }

    const verifyAuth = async () => {
        if (!deps.user.value || !authPassword.value) return
        try {
            const payload = {
                username_or_email: deps.user.value.username,
                password: authPassword.value
            }
            await $fetch(`${appConfig.apiBaseUrl}/auth/verify`, {
                method: 'POST',
                body: payload
            })
            isPackageSizeLocked.value = false
            showAuthDialog.value = false
            authPassword.value = ''
            $q.notify({ type: 'positive', message: 'Authorization successful' })
        } catch (err) {
            $q.notify({ type: 'negative', message: 'Invalid password. Authorization failed.' })
        }
    }

    // --- Watchers ---
    watch([preBatchLogs, () => deps.selectedBatch.value], ([logs, batch]) => {
        if (!logs || !batch) {
            deps.selectableIngredients.value.forEach((ing: any) => ing.isDone = false)
            return
        }
        let allDone = true
        deps.selectableIngredients.value.forEach((ing: any) => {
            const ingLogs = (logs as any[]).filter(l => l.re_code === ing.re_code && l.batch_record_id.startsWith(batch.batch_id))
            if (ingLogs.length > 0) {
                const maxPkg = Math.max(...ingLogs.map(l => l.package_no || 0))
                const totalPkgs = ingLogs[0]?.total_packages || 0
                if (maxPkg >= totalPkgs && totalPkgs > 0) {
                    ing.isDone = true
                } else {
                    ing.isDone = false
                    allDone = false
                }
            } else {
                ing.isDone = false
                allDone = false
            }
        })
        if (deps.selectableIngredients.value.length > 0 && allDone && !batch.batch_prepare) {
            deps.finalizeBatchPreparation(batch.id)
        }
    }, { deep: true })

    return {
        // State
        preBatchLogs,
        recordToDelete,
        showDeleteDialog,
        deleteInput,
        isPackageSizeLocked,
        showAuthDialog,
        authPassword,
        selectedPreBatchLogs,
        // Columns
        prebatchColumns,
        // Computed
        filteredPreBatchLogs,
        totalCompletedWeight,
        completedCount,
        nextPackageNo,
        preBatchSummary,
        // Functions
        fetchPreBatchRecords,
        executeDeletion,
        onDeleteRecord,
        onConfirmDeleteManual,
        onDeleteScanEnter,
        unlockPackageSize,
        verifyAuth,
    }
}

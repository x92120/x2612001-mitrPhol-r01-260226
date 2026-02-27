/**
 * usePreBatchIngredients — Ingredient requirements, expand/collapse, package plan
 */
import { ref, computed, watch } from 'vue'
import { appConfig } from '../appConfig/config'
import type { QTableColumn } from 'quasar'

export interface IngredientDeps {
    $q: any
    getAuthHeader: () => Record<string, string>
    t: (key: string, params?: any) => string
    // Cross-composable refs
    ingredients: any
    selectedProductionPlan: any
    selectedBatch: any
    selectedReCode: any
    selectedRequirementId: any
    selectedWarehouse: any
    isBatchSelected: any
    inventoryRows: any
    preBatchLogs: any
    requireVolume: any
    packageSize: any
    filteredInventory: any
    selectedInventoryItem: any
    selectedIntakeLotId: any
    // Functions from other composables
    updatePrebatchItemStatus: (batchId: string, reCode: string, status: number) => Promise<void>
}

export function usePreBatchIngredients(deps: IngredientDeps) {
    const { $q, getAuthHeader, t } = deps

    // --- State ---
    const prebatchItems = ref<any[]>([])
    const expandedIngredients = ref<string[]>([])
    const ingredientBatchDetail = ref<Record<string, any[]>>({})
    const expandedBatchRows = ref<string[]>([])

    // --- Functions ---
    const fetchPrebatchItems = async (batchId: string) => {
        try {
            const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-reqs/by-batch/${batchId}`, {
                headers: getAuthHeader() as Record<string, string>
            })
            prebatchItems.value = data
        } catch (error) {
            console.error('Error fetching prebatch requirements:', error)
            prebatchItems.value = []
        }
    }

    const updatePrebatchItemStatus = async (batchId: string, reCode: string, status: number) => {
        try {
            const req = prebatchItems.value.find((r: any) => r.re_code === reCode)
            if (!req) return
            await $fetch(`${appConfig.apiBaseUrl}/prebatch-reqs/${req.id}/status?status=${status}`, {
                method: 'PUT',
                headers: getAuthHeader() as Record<string, string>
            })
            await fetchPrebatchItems(batchId)
        } catch (error) {
            console.error('Error updating prebatch requirement status:', error)
        }
    }

    // --- Computed ---
    const selectableIngredients = computed(() => {
        if (!prebatchItems.value || prebatchItems.value.length === 0) return []
        const invList = deps.inventoryRows.value || []

        const mapped = prebatchItems.value.map((task: any, index: number) => {
            const ingInfo = deps.ingredients.value.find((i: any) => i.re_code === task.re_code)
            const stock = invList.find((r: any) => r.re_code === task.re_code)
            const warehouse = (task.wh && task.wh !== '-' ? task.wh : (stock?.warehouse_location || '-')).toUpperCase()

            const batchReq = deps.isBatchSelected.value
                ? (task.required_volume || 0)
                : (task.total_require || 0)
            const perBatch = task.per_batch || task.required_volume || 0

            return {
                index: index + 1,
                re_code: task.re_code,
                ingredient_name: task.ingredient_name || ingInfo?.name || task.re_code,
                std_package_size: ingInfo?.std_package_size || 0,
                package_container_type: ingInfo?.package_container_type || 'Bag',
                batch_require: batchReq,
                per_batch: perBatch,
                total_require: task.total_require ?? task.required_volume,
                total_packaged: task.total_packaged || 0,
                batch_count: task.batch_count || 1,
                from_warehouse: warehouse,
                isDisabled: deps.selectedWarehouse.value !== 'All' && warehouse !== deps.selectedWarehouse.value.toUpperCase(),
                isDone: task.status === 2,
                status: task.status,
                req_id: task.id,
                mat_sap_code: ingInfo?.mat_sap_code || ''
            }
        })

        // Apply filter by warehouse if not 'All'
        let filtered = mapped
        if (deps.selectedWarehouse.value && deps.selectedWarehouse.value !== 'All') {
            const whTarget = deps.selectedWarehouse.value.toUpperCase()
            filtered = mapped.filter(ing => ing.from_warehouse === whTarget)
        }

        return filtered
    })

    const ingredientsByWarehouse = computed(() => {
        const groups: Record<string, any[]> = {}
        for (const ing of selectableIngredients.value) {
            const wh = ing.from_warehouse || '-'
            if (!groups[wh]) groups[wh] = []
            groups[wh].push(ing)
        }
        return Object.entries(groups).sort((a, b) => {
            if (a[0] === '-') return 1
            if (b[0] === '-') return -1
            return a[0].localeCompare(b[0])
        })
    })

    // --- Expand/Collapse ---
    const toggleIngredientExpand = (reCode: string) => {
        const index = expandedIngredients.value.indexOf(reCode)
        if (index > -1) {
            expandedIngredients.value.splice(index, 1)
        } else {
            expandedIngredients.value.push(reCode)
            fetchIngredientBatchDetail(reCode)
        }
    }

    const isExpanded = (reCode: string) => expandedIngredients.value.includes(reCode)

    const fetchIngredientBatchDetail = async (reCode: string) => {
        if (!deps.selectedProductionPlan.value) return
        try {
            const data = await $fetch<any[]>(
                `${appConfig.apiBaseUrl}/prebatch-reqs/batches-by-ingredient/${deps.selectedProductionPlan.value}/${encodeURIComponent(reCode)}`,
                { headers: getAuthHeader() as Record<string, string> }
            )
            ingredientBatchDetail.value[reCode] = data
        } catch (error) {
            console.error('Error fetching ingredient batch detail:', error)
            ingredientBatchDetail.value[reCode] = []
        }
    }

    const toggleBatchRow = (key: string) => {
        const idx = expandedBatchRows.value.indexOf(key)
        if (idx >= 0) {
            expandedBatchRows.value.splice(idx, 1)
        } else {
            expandedBatchRows.value.push(key)
        }
    }

    const isBatchRowExpanded = (key: string) => expandedBatchRows.value.includes(key)

    const getPackagePlan = (batchId: string, reCode: string, requiredVolume: number) => {
        const ingInfo = deps.ingredients.value.find((i: any) => i.re_code === reCode)
        let pkgSize = ingInfo?.std_package_size || deps.packageSize.value || 0
        if (requiredVolume <= 0) return []
        if (pkgSize <= 0) pkgSize = requiredVolume
        const totalPkgs = Math.ceil(requiredVolume / pkgSize)
        const actuals = deps.preBatchLogs.value
            .filter((log: any) => log.re_code === reCode && log.batch_record_id.startsWith(batchId))
            .sort((a: any, b: any) => a.package_no - b.package_no)
        const packages: any[] = []
        let remain = requiredVolume
        for (let i = 1; i <= totalPkgs; i++) {
            const target = Math.min(remain, pkgSize)
            remain -= target
            const actual = actuals.find((a: any) => a.package_no === i)
            packages.push({
                pkg_no: i,
                target,
                actual: actual?.net_volume || null,
                status: actual ? 'done' : 'pending',
                log: actual || null
            })
        }
        return packages
    }

    const getIngredientLogs = (reCode: string) => {
        if (!deps.selectedBatch.value) return []
        return deps.preBatchLogs.value
            .filter((log: any) => log.re_code === reCode && log.batch_record_id.startsWith(deps.selectedBatch.value.batch_id))
            .sort((a: any, b: any) => a.package_no - b.package_no)
    }

    const getIngredientRowClass = (ing: any) => {
        if (ing.isDisabled) return 'bg-grey-3 text-grey-5 cursor-not-allowed'
        if (deps.selectedReCode.value === ing.re_code) return 'bg-orange-2 text-deep-orange-9 text-weight-bold cursor-pointer'
        if (ing.status === 2) return 'bg-green-1 text-green-9 cursor-pointer'
        if (ing.status === 1) return 'bg-amber-1 text-amber-9 cursor-pointer'
        return 'hover-bg-grey-1 cursor-pointer'
    }

    // --- Selection ---
    const onSelectIngredient = async (ing: any) => {
        if (ing.isDisabled) return
        deps.selectedReCode.value = ing.re_code
        deps.selectedRequirementId.value = ing.req_id
        if (ing.status === 0 && deps.selectedBatch.value) {
            await updatePrebatchItemStatus(deps.selectedBatch.value.batch_id, ing.re_code, 1)
        }
    }

    const updateRequireVolume = () => {
        if (deps.selectedReCode.value) {
            const ing = selectableIngredients.value.find(i => i.re_code === deps.selectedReCode.value)
            if (ing) {
                // Always use per_batch for scale target (single batch amount)
                deps.requireVolume.value = ing.per_batch || ing.batch_require || 0
                if (ing.std_package_size > 0) {
                    deps.packageSize.value = ing.std_package_size
                }
            }
        } else {
            deps.requireVolume.value = 0
        }
    }

    const onIngredientSelect = () => {
        if (deps.selectedReCode.value) {
            if (deps.filteredInventory.value.length > 0) {
                const firstItem = deps.filteredInventory.value[0]
                if (firstItem) {
                    deps.selectedInventoryItem.value = [firstItem]
                    deps.selectedIntakeLotId.value = firstItem.intake_lot_id
                    $q.notify({ type: 'positive', message: t('preBatch.autoSelectedFifo', { id: firstItem.intake_lot_id }), position: 'top', timeout: 1000 })
                }
            } else {
                deps.selectedInventoryItem.value = []
                deps.selectedIntakeLotId.value = ''
                $q.notify({ type: 'warning', message: t('preBatch.noInventoryFor', { id: deps.selectedReCode.value }), position: 'top', timeout: 1000 })
            }
        }
    }

    const onIngredientDoubleClick = (ingredient: any) => {
        if (ingredient && ingredient.total_require !== undefined) {
            deps.requireVolume.value = Number(ingredient.total_require.toFixed(3))
            if (ingredient.std_package_size) {
                deps.packageSize.value = Number(ingredient.std_package_size)
            }
            $q.notify({ type: 'positive', message: t('preBatch.initBatching', { id: ingredient.re_code }), position: 'top', timeout: 500 })
        }
    }

    // --- Watchers ---
    watch(selectableIngredients, (newList) => {
        if (deps.selectedReCode.value && !newList.some(i => i.re_code === deps.selectedReCode.value)) {
            deps.selectedReCode.value = ''
        }
    })

    return {
        // State
        prebatchItems,
        expandedIngredients,
        ingredientBatchDetail,
        expandedBatchRows,
        // Computed
        selectableIngredients,
        ingredientsByWarehouse,
        // Functions
        fetchPrebatchItems,
        updatePrebatchItemStatus,
        toggleIngredientExpand,
        isExpanded,
        fetchIngredientBatchDetail,
        toggleBatchRow,
        isBatchRowExpanded,
        getPackagePlan,
        getIngredientLogs,
        getIngredientRowClass,
        onSelectIngredient,
        updateRequireVolume,
        onIngredientSelect,
        onIngredientDoubleClick,
    }
}

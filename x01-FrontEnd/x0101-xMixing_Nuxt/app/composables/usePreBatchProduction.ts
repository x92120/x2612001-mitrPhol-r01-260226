/**
 * usePreBatchProduction — Plan/batch selection, filtering, navigation
 */
import { ref, computed, watch } from 'vue'
import { appConfig } from '../appConfig/config'

export interface ProductionDeps {
    $q: any
    getAuthHeader: () => Record<string, string>
    t: (key: string, params?: any) => string
    // Cross-composable refs (injected by page)
    ingredients: any
    prebatchItems: any
    inventoryRows: any
    requireVolume: any
    packageSize: any
    selectedReCode: any
    selectedRequirementId: any
    isBatchSelected: any
    selectedWarehouse: any
    // Functions from other composables
    fetchPrebatchItems: (batchId: string) => Promise<void>
    fetchPreBatchRecords: () => Promise<void>
    updatePrebatchItemStatus: (batchId: string, reCode: string, status: number) => Promise<void>
    updateRequireVolume: () => void
}

export function usePreBatchProduction(deps: ProductionDeps) {
    const { $q, getAuthHeader, t } = deps

    // --- State ---
    const selectedProductionPlan = ref('')
    const selectedBatchIndex = ref(0)
    const isLoading = ref(false)
    const productionPlans = ref<any[]>([])
    const planFilter = ref('All')
    const productionPlanOptions = computed(() => {
        const ids = productionPlans.value.map((plan: any) => plan.plan_id)
        return ['All', ...ids]
    })
    const allBatches = ref<any[]>([])
    const filteredBatches = ref<any[]>([])
    const ingredientOptions = ref<{ label: string, value: string }[]>([])
    const batchIngredients = ref<Record<string, any[]>>({})

    // --- Computed ---
    const filteredProductionPlans = computed(() => {
        const base = productionPlans.value.filter((p: any) => p.status !== 'Cancelled')
        if (planFilter.value === 'All') return base
        return base.filter((p: any) => p.plan_id === planFilter.value)
    })
    const batchIds = computed(() => filteredBatches.value.map((b: any) => b.batch_id))

    const selectedBatch = computed(() => {
        if (selectedBatchIndex.value >= 0 && filteredBatches.value.length > 0) {
            return filteredBatches.value[selectedBatchIndex.value]
        }
        return null
    })

    const selectedPlanDetails = computed(() => {
        return productionPlans.value.find(p => p.plan_id === selectedProductionPlan.value)
    })

    const structuredSkuList = computed(() => {
        const groups: Record<string, any> = {}
        const activePlans = productionPlans.value.filter(p =>
            !p.status || ['Active', 'In Progress', 'Released', 'Planned'].includes(p.status)
        )
        activePlans.forEach(plan => {
            const sku = plan.sku_id || 'No SKU'
            if (!groups[sku]) {
                groups[sku] = { sku, plans: [] }
            }
            const childBatches = (allBatches.value || [])
                .filter(b => b.plan_id === plan.id || b.batch_id.includes(plan.plan_id))
                .sort((a: any, b: any) => a.batch_id.localeCompare(b.batch_id))
            groups[sku].plans.push({ ...plan, batches: childBatches })
        })
        return Object.values(groups).sort((a: any, b: any) => a.sku.localeCompare(b.sku))
    })

    // --- Functions ---
    const fetchIngredients = async () => {
        try {
            const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/ingredients/`, {
                headers: getAuthHeader() as Record<string, string>
            })
            deps.ingredients.value = data
        } catch (e) {
            console.error('Error fetching ingredients', e)
        }
    }

    const fetchProductionPlans = async () => {
        try {
            isLoading.value = true
            const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/production-plans/`, {
                headers: getAuthHeader() as Record<string, string>
            })
            productionPlans.value = data
        } catch (error) {
            console.error('Error fetching production plans:', error)
            $q.notify({ type: 'negative', message: t('preBatch.errorLoadingPlans'), position: 'top' })
        } finally {
            isLoading.value = false
        }
    }

    const fetchBatchIds = async () => {
        try {
            const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/production-batches/`, {
                headers: getAuthHeader() as Record<string, string>
            })
            allBatches.value = data
            filterBatchesByPlan()
        } catch (error) {
            console.error('Error fetching batch IDs:', error)
        }
    }

    const filterBatchesByPlan = async () => {
        if (!selectedProductionPlan.value) {
            filteredBatches.value = []
            ingredientOptions.value = []
            return
        }
        const plan = productionPlans.value.find(p => p.plan_id === selectedProductionPlan.value)
        if (plan) {
            filteredBatches.value = allBatches.value
                .filter(batch => batch.sku_id === plan.sku_id || batch.batch_id.includes(plan.plan_id))
                .sort((a, b) => a.batch_id.localeCompare(b.batch_id))
            if (selectedBatchIndex.value >= filteredBatches.value.length) {
                selectedBatchIndex.value = 0
            }
            deps.updateRequireVolume()
        }
    }

    const onPlanShow = async (plan: any) => {
        selectedProductionPlan.value = plan.plan_id
        deps.isBatchSelected.value = false
        deps.selectedReCode.value = ''
        deps.selectedRequirementId.value = null
        try {
            const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-reqs/summary-by-plan/${plan.plan_id}`, {
                headers: getAuthHeader() as Record<string, string>
            })
            deps.prebatchItems.value = data.map((item: any) => ({
                id: item.id || null,
                re_code: item.re_code || '-',
                ingredient_name: item.ingredient_name || item.name || '-',
                total_require: item.total_required ?? item.required_volume ?? 0,
                total_packaged: item.total_packaged || 0,
                wh: item.wh || item.warehouse || '-',
                status: item.status ?? 0,
                batch_count: item.batch_count || 1,
                per_batch: item.per_batch || item.required_volume || 0,
                completed_batches: item.completed_batches || 0
            }))
        } catch (error) {
            console.error('Error fetching plan ingredient summary:', error)
            deps.prebatchItems.value = []
        }
        deps.fetchPreBatchRecords()
    }

    const onBatchSelect = async (plan: any, batch: any, index: number) => {
        selectedProductionPlan.value = plan.plan_id
        selectedBatchIndex.value = Number(index)
        deps.isBatchSelected.value = true
        filterBatchesByPlan()
        await deps.fetchPrebatchItems(batch.batch_id)
        await deps.fetchPreBatchRecords()
    }

    const onBatchExpand = async (batch: any) => {
        try {
            const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/prebatch-reqs/by-batch/${batch.batch_id}`, {
                headers: getAuthHeader() as Record<string, string>
            })
            batchIngredients.value[batch.batch_id] = data.map((req: any) => {
                const ingInfo = deps.ingredients.value.find((i: any) => i.re_code === req.re_code)
                return {
                    ...req,
                    wh: ingInfo?.warehouse || req.wh || '-',
                    ingredient_name: req.ingredient_name || ingInfo?.name || req.re_code
                }
            })
        } catch (error) {
            console.error('Error fetching batch ingredients:', error)
            batchIngredients.value[batch.batch_id] = []
        }
    }

    const onBatchIngredientClick = async (batch: any, req: any, plan: any) => {
        if (selectedProductionPlan.value !== plan.plan_id) {
            await onPlanShow(plan)
        }
        const batchIndex = filteredBatches.value.findIndex(b => b.batch_id === batch.batch_id)
        if (batchIndex >= 0) {
            await onBatchSelect(plan, { batch_id: batch.batch_id }, batchIndex)
        }
        deps.selectedReCode.value = req.re_code
        deps.selectedRequirementId.value = req.id
        deps.isBatchSelected.value = true
        deps.requireVolume.value = req.required_volume || 0
        const ingInfo = deps.ingredients.value.find((i: any) => i.re_code === req.re_code)
        if (ingInfo?.std_package_size && ingInfo.std_package_size > 0) {
            deps.packageSize.value = ingInfo.std_package_size
        }
        await deps.fetchPreBatchRecords()
    }

    const advanceToNextBatch = async (currentBatchId: string, reCode: string) => {
        const plan = productionPlans.value.find(p => p.plan_id === selectedProductionPlan.value)
        if (!plan || !plan.batches) return
        const currentIdx = plan.batches.findIndex((b: any) => b.batch_id === currentBatchId)
        if (currentIdx < 0) return
        for (let i = currentIdx + 1; i < plan.batches.length; i++) {
            const nextBatch = plan.batches[i]
            if (nextBatch.batch_prepare) continue
            if (!batchIngredients.value[nextBatch.batch_id]) {
                await onBatchExpand(nextBatch)
            }
            const nextReq = batchIngredients.value[nextBatch.batch_id]?.find((r: any) => r.re_code === reCode && r.status !== 2)
            if (nextReq) {
                await onBatchIngredientClick(nextBatch, nextReq, plan)
                $q.notify({ type: 'info', message: `Advanced to ${nextBatch.batch_id} for ${reCode}`, position: 'top', timeout: 2000 })
                return
            }
        }
        $q.notify({ type: 'positive', message: `All batches completed for ${reCode}!`, position: 'top', timeout: 3000 })
    }

    const finalizeBatchPreparation = async (batchId: number) => {
        try {
            await $fetch(`${appConfig.apiBaseUrl}/production-batches/${batchId}`, {
                method: 'PUT',
                body: { batch_prepare: true, status: 'Prepared' },
                headers: getAuthHeader() as Record<string, string>
            })
            $q.notify({ type: 'positive', message: t('preBatch.prepFinalized'), position: 'top' })
            await fetchBatchIds()
        } catch (e) {
            console.error('Failed to finalize batch preparation', e)
        }
    }

    const onSelectBatch = (index: number) => {
        selectedBatchIndex.value = index
    }

    // --- Watchers ---
    watch(selectedProductionPlan, () => {
        filterBatchesByPlan()
        deps.fetchPreBatchRecords()
    })

    watch(selectedBatchIndex, () => {
        deps.updateRequireVolume()
        deps.fetchPreBatchRecords()
    })

    return {
        // State
        selectedProductionPlan,
        selectedBatchIndex,
        isLoading,
        productionPlans,
        planFilter,
        productionPlanOptions,
        allBatches,
        filteredBatches,
        ingredientOptions,
        batchIngredients,
        // Computed
        filteredProductionPlans,
        batchIds,
        selectedBatch,
        selectedPlanDetails,
        structuredSkuList,
        // Functions
        fetchIngredients,
        fetchProductionPlans,
        fetchBatchIds,
        filterBatchesByPlan,
        onPlanShow,
        onBatchSelect,
        onBatchExpand,
        onBatchIngredientClick,
        advanceToNextBatch,
        finalizeBatchPreparation,
        onSelectBatch,
    }
}

/**
 * usePreBatchLabels — Label data, print/reprint, label dialogs
 */
import { ref, computed, watch } from 'vue'
import { appConfig } from '../appConfig/config'

export interface LabelDeps {
    $q: any
    getAuthHeader: () => Record<string, string>
    t: (key: string, params?: any) => string
    user: any
    formatDate: (date: any) => string
    generateLabelSvg: (template: string, data: any) => Promise<string>
    printLabel: (svg: string | string[]) => void
    // Cross-composable refs
    selectedBatch: any
    selectedReCode: any
    selectedRequirementId: any
    selectedProductionPlan: any
    selectedPlanDetails: any
    selectableIngredients: any
    ingredients: any
    requireVolume: any
    packageSize: any
    capturedScaleValue: any
    nextPackageNo: any
    requestBatch: any
    actualScaleValue: any
    currentPackageOrigins: any
    preBatchLogs: any
    selectedPreBatchLogs: any
    // Functions from other composables
    getPackagePlan: (batchId: string, reCode: string, requiredVolume: number) => any[]
    fetchPreBatchRecords: () => Promise<void>
    fetchPrebatchItems: (batchId: string) => Promise<void>
    updatePrebatchItemStatus: (batchId: string, reCode: string, status: number) => Promise<void>
    onBatchExpand: (batch: any) => Promise<void>
    onPlanShow: (plan: any) => Promise<void>
    advanceToNextBatch: (batchId: string, reCode: string) => Promise<void>
    getOriginDelta: () => number
    selectedIntakeLotId: any
    selectedInventoryItem: any
    productionPlans: any
}

export function usePreBatchLabels(deps: LabelDeps) {
    const { $q, getAuthHeader, t, generateLabelSvg, printLabel, formatDate } = deps

    // --- State ---
    const showLabelDialog = ref(false)
    const packageLabelId = ref('')
    const capturedScaleValue = ref(0)
    const renderedLabel = ref('')
    const showPackingBoxLabelDialog = ref(false)
    const renderedPackingBoxLabel = ref('')

    // --- Shared label-data helpers ---
    const buildLotStrings = (origins: any[] | undefined, fallbackLotId?: string, fallbackVol?: number) => ({
        Lot1: origins?.[0] ? `1. ${origins[0].intake_lot_id} / ${(origins[0].take_volume || 0).toFixed(4)} kg` : (fallbackLotId ? `1. ${fallbackLotId} / ${(fallbackVol ?? 0).toFixed(4)} kg` : ''),
        Lot2: origins?.[1] ? `2. ${origins[1].intake_lot_id} / ${(origins[1].take_volume || 0).toFixed(4)} kg` : '',
    })

    const buildLabelData = (opts: { batch: any, planId: string, plan: any, reCode: string, ingName: string, matSapCode: string, containerType?: string, netVol: number, totalVol: number, pkgNo: number | string, qrCode: string, timestamp: string, origins?: any[], fallbackLotId?: string }) => {
        const batchIdValue = opts.batch.batch_id || opts.batch.batchId || '-'
        const totalBatches = opts.plan?.num_batches || (opts.plan?.batches?.length) || '-'
        const batchMatch = batchIdValue.match(/-(\d+)$/)
        const currentBatchNo = batchMatch ? parseInt(batchMatch[1]) : '-'

        const skuFullName = opts.batch.sku_id ? `${opts.batch.sku_id} / ${opts.plan?.sku_name || opts.plan?.name || '-'}` : (opts.plan?.sku_name || '-');

        return {
            SKU: opts.batch.sku_id || '-',
            SKU_Name: opts.plan?.sku_name || opts.plan?.name || '-',
            "SKU / SKU_Name": skuFullName,
            PlanId: opts.planId || '-',
            BatchId: batchIdValue,
            "Batch_Number/No of Batch": totalBatches !== '-' ? `${currentBatchNo}/${totalBatches}` : currentBatchNo,
            IngredientID: opts.ingName || '-',
            Ingredient_ReCode: opts.reCode || '-',
            ContainerType: opts.containerType || 'Bag',
            mat_sap_code: opts.matSapCode || '-',
            PlanStartDate: opts.plan?.start_date || '-',
            PlanFinishDate: opts.plan?.finish_date || '-',
            PrepareDate: opts.timestamp.split(',')[0], // Use just the date part of the timestamp
            PlantId: opts.plan?.plant || '-',
            PlantName: '-',
            Timestamp: opts.timestamp,
            PackageSize: opts.netVol.toFixed(4),
            BatchRequireSize: opts.totalVol.toFixed(4),
            PackageNo: opts.pkgNo,
            QRCode: opts.qrCode,
            ...buildLotStrings(opts.origins, opts.fallbackLotId, opts.netVol),
        }
    }

    // --- Computed ---
    const labelDataMapping = computed(() => {
        if (!deps.selectedBatch.value || !deps.selectedReCode.value) return null
        const ing = deps.selectableIngredients.value.find((i: any) => i.re_code === deps.selectedReCode.value)
        const pkgNo = deps.nextPackageNo.value
        return buildLabelData({
            batch: deps.selectedBatch.value,
            planId: deps.selectedProductionPlan.value,
            plan: deps.selectedPlanDetails.value,
            reCode: deps.selectedReCode.value,
            ingName: ing?.ingredient_name || '-',
            matSapCode: ing?.mat_sap_code || '-',
            containerType: ing?.package_container_type || 'Bag',
            netVol: capturedScaleValue.value,
            totalVol: deps.requireVolume.value,
            pkgNo,
            qrCode: `${deps.selectedBatch.value.plan_id},${deps.selectedBatch.value.batch_id},${deps.selectedBatch.value.batch_id}${deps.selectedReCode.value}${String(pkgNo).padStart(2, '0')},${deps.selectedReCode.value},${capturedScaleValue.value}`,
            timestamp: formatDate(new Date().toISOString()),
            origins: deps.currentPackageOrigins.value.length > 0 ? deps.currentPackageOrigins.value : undefined,
        })
    })

    const packingBoxLabelDataMapping = computed(() => {
        if (!deps.selectedBatch.value || deps.selectedPreBatchLogs.value.length === 0) return null
        const totalWeight = deps.selectedPreBatchLogs.value.reduce((sum: number, row: any) => sum + (Number(row.net_volume) || 0), 0)
        const bagCount = deps.selectedPreBatchLogs.value.length
        return {
            BoxID: deps.selectedBatch.value.plan_id || '-',
            BatchID: deps.selectedBatch.value.batch_id || '-',
            BagCount: bagCount,
            NetWeight: totalWeight.toFixed(2),
            Operator: deps.user.value?.username || '-',
            Timestamp: new Date().toLocaleString('en-GB'),
            BoxQRCode: `${deps.selectedBatch.value.plan_id},${deps.selectedBatch.value.batch_id},BOX,${bagCount},${totalWeight.toFixed(2)}`
        }
    })

    // --- Functions ---
    const updateDialogPreview = async () => {
        if (labelDataMapping.value) {
            const svg = await generateLabelSvg('prebatch-label_4x3', labelDataMapping.value)
            renderedLabel.value = svg || ''
        }
    }

    const updatePackingBoxPreview = async () => {
        if (packingBoxLabelDataMapping.value) {
            const svg = await generateLabelSvg('packingbox-label_4x3', packingBoxLabelDataMapping.value)
            renderedPackingBoxLabel.value = svg || ''
        }
    }

    const openLabelDialog = () => {
        capturedScaleValue.value = deps.actualScaleValue.value
        if (deps.selectedBatch.value && deps.selectedReCode.value) {
            packageLabelId.value = `${deps.selectedBatch.value.batch_id}-${deps.selectedReCode.value}-${deps.nextPackageNo.value}`
        } else {
            packageLabelId.value = ''
        }
        showLabelDialog.value = true
    }

    const onPrintLabel = async () => {
        if (!deps.selectedBatch.value || !deps.selectedReCode.value) {
            $q.notify({ type: 'warning', message: 'Missing Batch or Ingredient selection' })
            return
        }
        try {
            const pkgNo = deps.nextPackageNo.value
            const totalPkgs = deps.requestBatch.value
            if (isNaN(pkgNo) || isNaN(totalPkgs)) {
                throw new Error('Invalid package numbers')
            }
            const ing = deps.ingredients.value.find((i: any) => i.re_code === deps.selectedReCode.value)
            const recordData = {
                req_id: deps.selectedRequirementId.value,
                batch_record_id: `${deps.selectedBatch.value.batch_id}-${deps.selectedReCode.value}-${pkgNo}`,
                plan_id: deps.selectedProductionPlan.value,
                re_code: deps.selectedReCode.value,
                package_no: pkgNo,
                total_packages: totalPkgs,
                net_volume: capturedScaleValue.value,
                total_volume: deps.requireVolume.value,
                total_request_volume: deps.requireVolume.value,
                intake_lot_id: deps.currentPackageOrigins.value[0]?.intake_lot_id || deps.selectedIntakeLotId.value,
                mat_sap_code: ing?.mat_sap_code || null,
                recode_batch_id: String(pkgNo).padStart(2, '0'),
                origins: deps.currentPackageOrigins.value
            }
            await $fetch(`${appConfig.apiBaseUrl}/prebatch-recs/`, {
                method: 'POST',
                body: recordData,
                headers: getAuthHeader() as Record<string, string>
            })
            if (labelDataMapping.value) {
                const svg = await generateLabelSvg('prebatch-label_4x3', labelDataMapping.value)
                if (svg) printLabel(svg)
            }
            $q.notify({ type: 'positive', message: t('preBatch.saveAndPrintSuccess'), position: 'top' })
            await deps.fetchPreBatchRecords()
            if (pkgNo >= totalPkgs) {
                $q.notify({ type: 'info', message: t('preBatch.allPkgsCompleted') })
                if (deps.selectedBatch.value) {
                    const doneBatchId = deps.selectedBatch.value.batch_id
                    const doneReCode = deps.selectedReCode.value
                    await deps.updatePrebatchItemStatus(doneBatchId, doneReCode, 2)
                    await deps.onBatchExpand({ batch_id: doneBatchId })
                    const plan = deps.productionPlans.value.find((p: any) => p.plan_id === deps.selectedProductionPlan.value)
                    if (plan) await deps.onPlanShow(plan)
                    await deps.advanceToNextBatch(doneBatchId, doneReCode)
                }
            }
            showLabelDialog.value = false
            deps.currentPackageOrigins.value = []
            deps.selectedIntakeLotId.value = ''
        } catch (error) {
            console.error('Error saving prebatch record:', error)
            $q.notify({ type: 'negative', message: 'Failed to save record' })
        }
    }

    const onReprintLabel = async (record: any) => {
        if (!record || !deps.selectedBatch.value) return
        try {
            const data = buildLabelData({
                batch: deps.selectedBatch.value,
                planId: record.plan_id || deps.selectedProductionPlan.value,
                plan: deps.selectedPlanDetails.value,
                reCode: record.re_code,
                ingName: record.ingredient_name || '-',
                matSapCode: record.mat_sap_code || '-',
                containerType: record.package_container_type || (deps.selectableIngredients.value.find((i: any) => i.re_code === record.re_code)?.package_container_type) || 'Bag',
                netVol: Number(record.net_volume),
                totalVol: Number(record.total_volume),
                pkgNo: record.package_no,
                qrCode: `${deps.selectedBatch.value.plan_id},${record.batch_record_id},${record.prebatch_id || ''},${record.re_code},${record.net_volume}`,
                timestamp: new Date(record.created_at || Date.now()).toLocaleString('en-GB'),
                origins: record.origins?.length > 0 ? record.origins : undefined,
                fallbackLotId: record.intake_lot_id,
            })
            const svg = await generateLabelSvg('prebatch-label_4x3', data)
            if (svg) {
                printLabel(svg)
                $q.notify({ type: 'info', message: 'Reprinting label...', position: 'top', timeout: 800 })
            }
        } catch (err) {
            console.error('Reprint failed:', err)
            $q.notify({ type: 'negative', message: 'Reprint failed' })
        }
    }

    const quickReprint = async (ing: any) => {
        if (!ing) return

        let logs = []
        // 1. Try filtering by selected batch prefix
        if (deps.selectedBatch.value) {
            const batchId = deps.selectedBatch.value.batch_id
            logs = deps.preBatchLogs.value.filter((l: any) => l.re_code === ing.re_code && l.batch_record_id.startsWith(batchId))
        }

        // 2. Fallback to any log matching this re_code in the plan
        if (logs.length === 0) {
            logs = deps.preBatchLogs.value.filter((l: any) => l.re_code === ing.re_code)
        }

        if (logs.length > 0) {
            // Find record with highest ID (latest created)
            const lastRecord = logs.reduce((prev: any, current: any) => (prev.id > current.id) ? prev : current)
            await onReprintLabel(lastRecord)
        } else {
            $q.notify({ type: 'warning', message: 'No records found to reprint' })
        }
    }

    const printAllPlanLabels = async (ing: any) => {
        if (!ing || !deps.selectedProductionPlan.value) return

        const logs = deps.preBatchLogs.value.filter((l: any) => l.re_code === ing.re_code)

        if (logs.length === 0) {
            $q.notify({ type: 'warning', message: 'No records found for this plan' })
            return
        }

        $q.notify({ type: 'info', message: `Generating ${logs.length} labels...`, position: 'top', timeout: 1500 })

        const allSvgs: string[] = []
        // Sort logs by batch and package number to print in logical order
        const sortedLogs = [...logs].sort((a, b) => {
            if (a.batch_record_id < b.batch_record_id) return -1
            if (a.batch_record_id > b.batch_record_id) return 1
            return a.package_no - b.package_no
        })

        for (const record of sortedLogs) {
            try {
                // Determine batch ID from batch_record_id (strip the suffix)
                const parts = record.batch_record_id.split('-')
                // Plan is plan-Line-X-YYYY-MM-DD-001 (6 parts)
                // Batch is plan-Line-X-YYYY-MM-DD-001-001 (7 parts)
                const batchId = parts.slice(0, 7).join('-')

                const data = buildLabelData({
                    batch: {
                        batch_id: batchId,
                        sku_id: deps.selectedPlanDetails.value?.sku_id || '-'
                    },
                    planId: record.plan_id || deps.selectedProductionPlan.value,
                    plan: deps.selectedPlanDetails.value,
                    reCode: record.re_code,
                    ingName: record.ingredient_name || ing.ingredient_name || '-',
                    matSapCode: record.mat_sap_code || '-',
                    containerType: record.package_container_type || (deps.selectableIngredients.value.find((i: any) => i.re_code === record.re_code)?.package_container_type) || 'Bag',
                    netVol: Number(record.net_volume),
                    totalVol: Number(record.total_volume),
                    pkgNo: record.package_no,
                    qrCode: `${deps.selectedProductionPlan.value},${record.batch_record_id},${record.prebatch_id || ''},${record.re_code},${record.net_volume}`,
                    timestamp: new Date(record.created_at || Date.now()).toLocaleString('en-GB'),
                    origins: record.origins?.length > 0 ? record.origins : undefined,
                    fallbackLotId: record.intake_lot_id,
                })
                const svg = await generateLabelSvg('prebatch-label_4x3', data)
                if (svg) allSvgs.push(svg)
            } catch (err) {
                console.error('Error generating label:', err)
            }
        }

        if (allSvgs.length > 0) {
            printLabel(allSvgs)
            $q.notify({ type: 'positive', message: `Printing ${allSvgs.length} labels`, position: 'top' })
        }
    }

    const printAllBatchLabels = async (batchId: string, reCode: string, requiredVolume: number) => {
        const packages = deps.getPackagePlan(batchId, reCode, requiredVolume)
        if (packages.length === 0) {
            $q.notify({ type: 'warning', message: 'No packages found for this batch' })
            return
        }
        const ing = deps.ingredients.value.find((i: any) => i.re_code === reCode)
        const plan = deps.selectedPlanDetails.value
        const batch = { batch_id: batchId, sku_id: plan?.sku_id || '-', plan_id: plan?.plan_id || deps.selectedProductionPlan.value }
        $q.notify({ type: 'info', message: `Generating ${packages.length} labels...`, position: 'top', timeout: 1500 })
        const allSvgs: string[] = []
        for (const pkg of packages) {
            try {
                const volume = pkg.actual !== null ? pkg.actual : pkg.target
                const data = buildLabelData({
                    batch,
                    planId: batch.plan_id,
                    plan,
                    reCode,
                    ingName: ing?.name || reCode,
                    matSapCode: ing?.mat_sap_code || '-',
                    containerType: (deps.selectableIngredients.value.find((i: any) => i.re_code === reCode)?.package_container_type) || ing?.package_container_type || 'Bag',
                    netVol: volume,
                    totalVol: requiredVolume,
                    pkgNo: `${pkg.pkg_no}/${packages.length}`,
                    qrCode: `${batch.plan_id},${batchId}-${reCode}-${pkg.pkg_no},${pkg.log?.prebatch_id || ''},${reCode},${volume}`,
                    timestamp: pkg.log ? new Date(pkg.log.created_at || Date.now()).toLocaleString('en-GB') : new Date().toLocaleString('en-GB'),
                    origins: pkg.log?.origins?.length > 0 ? pkg.log.origins : undefined,
                    fallbackLotId: pkg.log?.intake_lot_id,
                })
                const svg = await generateLabelSvg('prebatch-label_4x3', data)
                if (svg) allSvgs.push(svg)
            } catch (err) {
                console.error(`Error generating label #${pkg.pkg_no}:`, err)
            }
        }
        if (allSvgs.length > 0) {
            printLabel(allSvgs)
            $q.notify({ type: 'positive', message: `Printing ${allSvgs.length} labels`, position: 'top' })
        } else {
            $q.notify({ type: 'warning', message: 'No labels generated' })
        }
    }

    const onPrintPackingBoxLabel = async () => {
        if (!packingBoxLabelDataMapping.value) return
        if (renderedPackingBoxLabel.value) {
            printLabel(renderedPackingBoxLabel.value)
            $q.notify({ type: 'positive', message: 'Packing Box Label Sent to Printer' })
            showPackingBoxLabelDialog.value = false
            deps.selectedPreBatchLogs.value = []
        }
    }

    const onDone = async () => {
        if (!deps.selectedReCode.value) {
            $q.notify({ type: 'warning', message: 'Please select an ingredient first' })
            return
        }
        if (deps.requestBatch.value > 0) {
            // completedCount handled by records composable - check via preBatchLogs
        }
        const remainder = deps.getOriginDelta()
        if (remainder > 0.0001) {
            if (!deps.selectedIntakeLotId.value) {
                $q.notify({ type: 'negative', message: 'Please scan or select an Intake Lot ID to record the remaining weight', position: 'top' })
                return
            }
            const ing = deps.selectableIngredients.value.find((i: any) => i.re_code === deps.selectedReCode.value)
            deps.currentPackageOrigins.value.push({ intake_lot_id: deps.selectedIntakeLotId.value, mat_sap_code: ing?.mat_sap_code || null, take_volume: remainder })
        }
        if (deps.currentPackageOrigins.value.length === 0) {
            $q.notify({ type: 'negative', message: 'No volume recorded. Please weigh and scan lot.', position: 'top' })
            return
        }
        capturedScaleValue.value = deps.currentPackageOrigins.value.reduce((s: number, o: any) => s + o.take_volume, 0)
        openLabelDialog()
    }

    // --- Watchers ---
    watch(showLabelDialog, (val) => {
        if (val) updateDialogPreview()
    })

    watch(showPackingBoxLabelDialog, (val) => {
        if (val) updatePackingBoxPreview()
    })

    return {
        // State
        showLabelDialog,
        packageLabelId,
        capturedScaleValue,
        renderedLabel,
        showPackingBoxLabelDialog,
        renderedPackingBoxLabel,
        // Computed
        labelDataMapping,
        packingBoxLabelDataMapping,
        // Functions
        buildLotStrings,
        buildLabelData,
        updateDialogPreview,
        updatePackingBoxPreview,
        openLabelDialog,
        onPrintLabel,
        onReprintLabel,
        quickReprint,
        printAllPlanLabels,
        printAllBatchLabels,
        onPrintPackingBoxLabel,
        onDone,
    }
}

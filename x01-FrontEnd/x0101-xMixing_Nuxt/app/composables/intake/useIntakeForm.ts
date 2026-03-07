/**
 * Composable: Intake form — fields, scanner, lookup, save, edit, reject, clear
 */
import { ref, watch, nextTick, computed } from 'vue'
import { useQuasar } from 'quasar'
import { appConfig } from '~/appConfig/config'
import { useAuth } from '~/composables/useAuth'
import { formatDateForInput, formatDateToApi, type IngredientIntake } from '~/composables/intake/useIntakeHelpers'

export function useIntakeForm(
    rows: Ref<IngredientIntake[]>,
    fetchReceipts: () => Promise<void>,
    printLabel: (record: IngredientIntake) => Promise<void>,
) {
    const $q = useQuasar()
    const { getAuthHeader, user } = useAuth()
    const { t } = useI18n()

    const headers = () => getAuthHeader() as Record<string, string>
    const jsonHeaders = () => ({ ...headers(), 'Content-Type': 'application/json' })

    // ── Form Fields ──
    const ingredientCodeRef = ref<any>(null)
    const scannerReady = ref(true)
    const intakeFrom = ref('')
    const intakeTo = ref('')
    const lotNumber = ref('')
    const expireDate = ref('')
    const ingredientId = ref('')
    const xIngredientName = ref('')
    const xMatSapCode = ref('')
    const xReCode = ref('')
    const intakeVol = ref('')
    const packageVol = ref('')
    const numberOfPackages = ref('')
    const manufacturingDate = ref('')
    const poNumber = ref('')
    const intakeLotId = ref('')
    const extDate = ref('')
    const reservNo = ref('')
    const stockZone = ref('')
    const materialType = ref('')
    const showIngredientDialog = ref(false)
    const tempIngredientId = ref('')
    const isSaving = ref(false)

    // ── Editing State ──
    const isEditing = ref(false)
    const editId = ref<number | null>(null)
    const originalRemainVol = ref<number | null>(null)
    const originalStatus = ref<string>('Active')

    // ── Ingredient Lookup ──
    const allIngredients = ref<any[]>([])
    const ingredientOptions = ref<any[]>([])

    const fetchAllIngredients = async () => {
        try {
            allIngredients.value = await $fetch<any[]>(`${appConfig.apiBaseUrl}/ingredients/`, { headers: headers() })
        } catch (e) { console.error('Failed to fetch all ingredients:', e) }
    }

    const filterIngredients = (val: string, update: (cb: () => void) => void) => {
        if (val === '') {
            update(() => { ingredientOptions.value = allIngredients.value })
            return
        }
        update(() => {
            const needle = val.toLowerCase()
            ingredientOptions.value = allIngredients.value.filter(v =>
                (v.ingredient_id?.toLowerCase().includes(needle)) ||
                (v.name?.toLowerCase().includes(needle)) ||
                (String(v.mat_sap_code || '').toLowerCase().includes(needle))
            )
        })
    }

    const lookupIngredient = async (query: string) => {
        if (!query || query.length < 3) {
            xIngredientName.value = xMatSapCode.value = xReCode.value = ''
            return
        }
        try {
            const data = await $fetch<any[]>(`${appConfig.apiBaseUrl}/ingredients/?lookup=${query}`, { headers: headers() })
            if (data.length > 0) {
                const ing = data[0]
                xIngredientName.value = ing.name
                xMatSapCode.value = ing.mat_sap_code
                xReCode.value = ing.re_code || ''
                if (ingredientId.value !== ing.ingredient_id) {
                    ingredientId.value = ing.ingredient_id
                    intakeVol.value = ''
                    packageVol.value = Number(ing.std_package_size || 25).toFixed(4)
                    intakeFrom.value = 'Warehouse'
                }
                $q.notify({ type: 'positive', message: `Found: ${ing.name}`, position: 'top', timeout: 1000 })
            } else {
                xIngredientName.value = xMatSapCode.value = xReCode.value = ''
            }
        } catch (e) { console.error('Lookup error:', e) }
    }

    // ── Auto-lookup on type/scan ──
    let lookupTimeout: any = null
    watch(ingredientId, (newId) => {
        if (lookupTimeout) clearTimeout(lookupTimeout)
        lookupTimeout = setTimeout(() => { if (newId) lookupIngredient(newId) }, 500)
    })

    // ── Auto-calculate packages ──
    watch([intakeVol, packageVol], ([newVol, newPkg]) => {
        const vol = parseFloat(newVol)
        const pkg = parseFloat(newPkg)
        numberOfPackages.value = (!isNaN(vol) && !isNaN(pkg) && pkg > 0) ? Math.ceil(vol / pkg).toString() : ''
    })

    // ── Scanner ──
    const onScannerEnter = () => {
        const code = ingredientId.value?.trim()
        if (code) lookupIngredient(code)
    }

    const focusScannerInput = () => {
        nextTick(() => ingredientCodeRef.value?.focus())
    }

    // ── Generate Lot ID ──
    const generateIntakeLotId = async () => {
        try {
            const data = await $fetch<{ next_id: string }>(`${appConfig.apiBaseUrl}/ingredient-intake-next-id`)
            intakeLotId.value = data.next_id
        } catch (e: any) {
            console.error('Failed to generate ID', e)
            intakeLotId.value = 'Error: ' + e.message
        }
    }

    // ── Ingredient Dialog ──
    const openIngredientDialog = () => { tempIngredientId.value = ingredientId.value; showIngredientDialog.value = true }
    const confirmIngredientCode = () => {
        const val = tempIngredientId.value
        if (val) { ingredientId.value = val; showIngredientDialog.value = false; lookupIngredient(val) }
    }
    const cancelIngredientDialog = () => { tempIngredientId.value = ''; showIngredientDialog.value = false }

    // ── Status ──
    const statusOptions = ['Active', 'Hold', 'Reject']
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'Active': return 'positive'
            case 'Hold': return 'warning'
            case 'Reject': return 'negative'
            case 'Cancelled': return 'grey-7'
            default: return 'grey'
        }
    }

    const updateRecordStatus = async (row: IngredientIntake, newStatus: string) => {
        try {
            const response = await fetch(`${appConfig.apiBaseUrl}/ingredient-intake-lists/${row.id}`, {
                method: 'PUT', headers: jsonHeaders(),
                body: JSON.stringify({ ...row, status: newStatus, edit_by: user.value?.username || 'system' }),
            })
            if (response.ok) {
                $q.notify({ type: 'positive', message: `${t('ingredient.statusUpdated')} ${newStatus}`, timeout: 1000 })
                row.status = newStatus
                fetchReceipts()
            } else { throw new Error('Failed to update status') }
        } catch (e) {
            console.error('Error updating status:', e)
            $q.notify({ type: 'negative', message: t('ingredient.statusUpdateFailed') })
        }
    }

    // ── Clear Form ──
    const onClear = () => {
        isEditing.value = false; editId.value = null
        ingredientId.value = ''; lotNumber.value = ''; expireDate.value = ''; manufacturingDate.value = ''
        poNumber.value = ''; xIngredientName.value = ''; xMatSapCode.value = ''; xReCode.value = ''
        intakeVol.value = ''; packageVol.value = ''; numberOfPackages.value = ''
        intakeFrom.value = ''; intakeTo.value = ''
        extDate.value = ''; reservNo.value = ''; stockZone.value = ''; materialType.value = ''
        originalRemainVol.value = null; originalStatus.value = 'Active'
        generateIntakeLotId()
        focusScannerInput()
    }

    // ── Save (Create / Update) ──
    const onSave = async () => {
        const missingFields: string[] = []
        if (!ingredientId.value && !xMatSapCode.value) missingFields.push('Ingredient ID')
        if (!lotNumber.value) missingFields.push('Lot Number')
        if (!intakeFrom.value) missingFields.push('Intake From')
        if (!intakeVol.value) missingFields.push('Intake Volume')
        if (!expireDate.value) missingFields.push('Expire Date')

        if (missingFields.length) {
            $q.notify({ type: 'negative', message: `${t('ingredient.enterData')}: ${missingFields.join(', ')}`, position: 'top' })
            return
        }

        const rVol = parseFloat(intakeVol.value)
        if (isNaN(rVol) || rVol <= 0) {
            $q.notify({ type: 'negative', message: t('ingredient.volPositive'), position: 'top' })
            return
        }
        if (packageVol.value) {
            const pVol = parseFloat(packageVol.value)
            if (isNaN(pVol) || pVol <= 0) {
                $q.notify({ type: 'negative', message: t('ingredient.pkgPositive'), position: 'top' })
                return
            }
        }

        $q.dialog({
            title: t('ingredient.confirmSave'),
            message: isEditing.value ? t('ingredient.confirmSaveUpdate') : t('ingredient.confirmSaveNew'),
            cancel: true, persistent: true,
        }).onOk(async () => {
            isSaving.value = true
            const payload = {
                intake_lot_id: intakeLotId.value, lot_id: lotNumber.value,
                intake_from: intakeFrom.value, intake_to: intakeTo.value,
                mat_sap_code: xMatSapCode.value, re_code: xReCode.value,
                material_description: xIngredientName.value, uom: 'kg',
                intake_vol: parseFloat(intakeVol.value),
                remain_vol: isEditing.value && originalRemainVol.value !== null ? originalRemainVol.value : parseFloat(intakeVol.value),
                intake_package_vol: packageVol.value ? parseFloat(packageVol.value) : null,
                package_intake: numberOfPackages.value ? parseInt(numberOfPackages.value) : null,
                expire_date: expireDate.value ? formatDateToApi(expireDate.value) : null,
                status: isEditing.value ? originalStatus.value : 'Active',
                intake_by: user.value?.username || 'cj',
                edit_by: user.value?.username || 'cj',
                manufacturing_date: manufacturingDate.value ? formatDateToApi(manufacturingDate.value) : null,
                po_number: poNumber.value || null,
                ext_date: extDate.value ? formatDateToApi(extDate.value) : null,
                reserv_no: reservNo.value || null,
                stock_zone: stockZone.value || null,
                material_type: materialType.value || null,
            }

            try {
                const url = isEditing.value && editId.value
                    ? `${appConfig.apiBaseUrl}/ingredient-intake-lists/${editId.value}`
                    : `${appConfig.apiBaseUrl}/ingredient-intake-lists/`
                const method = isEditing.value && editId.value ? 'PUT' : 'POST'
                const response = await fetch(url, { method, headers: jsonHeaders(), body: JSON.stringify(payload) })

                if (response.ok) {
                    const savedRecord = await response.json()
                    $q.notify({
                        type: 'positive', icon: 'check_circle', position: 'top',
                        message: isEditing.value ? t('ingredient.updatedSuccess') : t('ingredient.savedSuccess'),
                    })
                    if (!isEditing.value) printLabel(savedRecord)
                    onClear()
                    await fetchReceipts()
                } else {
                    const error = await response.json()
                    $q.notify({ type: 'negative', message: `${t('common.error')}: ${error.detail || t('ingredient.saveFailed')}`, position: 'top' })
                }
            } catch (e) {
                console.error('Save error:', e)
                $q.notify({ type: 'negative', message: t('ingredient.networkError'), position: 'top' })
            } finally { isSaving.value = false }
        })
    }

    // ── Edit ──
    const onEdit = (row: IngredientIntake) => {
        isEditing.value = true; editId.value = row.id
        intakeLotId.value = row.intake_lot_id; lotNumber.value = row.lot_id
        intakeFrom.value = row.intake_from || ''; intakeTo.value = row.intake_to || ''
        xMatSapCode.value = row.mat_sap_code; xReCode.value = row.re_code || ''
        intakeVol.value = row.intake_vol.toString()
        packageVol.value = row.intake_package_vol ? row.intake_package_vol.toString() : ''
        numberOfPackages.value = row.package_intake ? row.package_intake.toString() : ''
        expireDate.value = row.expire_date ? formatDateForInput(row.expire_date) : ''
        manufacturingDate.value = row.manufacturing_date ? formatDateForInput(row.manufacturing_date) : ''
        poNumber.value = row.po_number || ''
        extDate.value = row.ext_date ? formatDateForInput(row.ext_date) : ''
        reservNo.value = row.reserv_no || ''; stockZone.value = row.stock_zone || ''
        materialType.value = row.material_type || ''
        lookupIngredient(row.mat_sap_code)
        originalRemainVol.value = row.remain_vol; originalStatus.value = row.status
    }

    // ── Reject ──
    const onRejectIntake = async (row: IngredientIntake) => {
        $q.dialog({
            title: t('ingredient.confirmReject'),
            message: `${t('ingredient.rejectPrompt')} ${row.intake_lot_id}?`,
            cancel: true, persistent: true,
            prompt: { model: '', type: 'text', label: t('ingredient.rejectReason'), outlined: true },
        }).onOk(async (remarks: string) => {
            try {
                const response = await fetch(`${appConfig.apiBaseUrl}/ingredient-intake-lists/${row.id}`, {
                    method: 'PUT', headers: jsonHeaders(),
                    body: JSON.stringify({ ...row, status: 'Reject', remarks: remarks || 'Rejected by user', edit_by: user.value?.username || 'system' }),
                })
                if (response.ok) {
                    $q.notify({ type: 'warning', message: t('ingredient.rejected') })
                    fetchReceipts()
                } else {
                    const err = await response.json()
                    $q.notify({ type: 'negative', message: `${t('ingredient.rejectFailed')}: ${err.detail || 'Unknown error'}` })
                }
            } catch (e) {
                console.error('Reject error:', e)
                $q.notify({ type: 'negative', message: t('ingredient.networkRejectError') })
            }
        })
    }

    return {
        // Form fields
        ingredientCodeRef, scannerReady, intakeFrom, intakeTo, lotNumber, expireDate,
        ingredientId, xIngredientName, xMatSapCode, xReCode,
        intakeVol, packageVol, numberOfPackages, manufacturingDate, poNumber, intakeLotId,
        extDate, reservNo, stockZone, materialType,
        showIngredientDialog, tempIngredientId, isSaving,
        isEditing, editId,
        // Ingredient lookup
        allIngredients, ingredientOptions, fetchAllIngredients, filterIngredients, lookupIngredient,
        // Actions
        onScannerEnter, focusScannerInput, generateIntakeLotId,
        openIngredientDialog, confirmIngredientCode, cancelIngredientDialog,
        statusOptions, getStatusColor, updateRecordStatus,
        onClear, onSave, onEdit, onRejectIntake,
    }
}

# SKU Master Step Management - Issue Fix

## Problem
When adding process steps to a SKU master, the steps are being added to ALL SKUs instead of just the selected SKU.

## Root Cause Analysis

The frontend code is correctly setting the `sku_id` when creating steps:
- Line 468: `stepForm.value = { ...stepForm.value, sku_id: skuId, ...}`
- Line 477: `stepForm.value = { ...stepForm.value, sku_id: skuId, ...}`

The backend is also correctly saving the `sku_id` field.

## Potential Issues

1. **Frontend Issue**: The `stepForm.value` might be retaining old data from previous operations
2. **Backend Issue**: The update endpoint might not be properly filtering by sku_id

## Solution

### Frontend Fix (x20-Sku.vue)

The issue is that `stepForm.value` uses spread operator `{...stepForm.value, ...}` which might carry over old sku_id values. We need to ensure a clean form state.

**Lines 461-469 (addStep function):**
```typescript
const addStep = (skuId: string) => {
  const steps = skuStepsMap.value[skuId] || []
  const maxPN = steps.length > 0 ? [...steps].sort((a,b) => b.phase_number.localeCompare(a.phase_number))[0]?.phase_number || 'p0000' : 'p0000'
  const nextVal = (parseInt(maxPN.substring(1)) || 0) + 10
  const pn = 'p' + nextVal.toString().padStart(4, '0')
  const phaseLink = skuPhases.value.find(p => (p.phase_id as any) === nextVal)?.phase_code || ''
  
  // FIX: Create a completely new object instead of spreading old stepForm
  stepForm.value = {
    sku_id: skuId,  // Explicitly set first
    phase_number: pn,
    phase_id: phaseLink,
    sub_step: 10,
    action: '',
    re_code: '',
    action_code: '',
    destination: '',
    require: 0,
    uom: 'kg',
    low_tol: 0.001,
    high_tol: 0.001,
    step_condition: '',
    agitator_rpm: 0,
    high_shear_rpm: 0,
    temperature: 0,
    temp_low: 0,
    temp_high: 0,
    step_time: 0,
    brix_sp: '',
    ph_sp: '',
    qc_temp: false,
    record_steam_pressure: false,
    record_ctw: false,
    operation_brix_record: false,
    operation_ph_record: false,
    master_step: true,
    step_id: undefined
  }
  editingStep.value = null
  showStepDialog.value = true
}
```

**Lines 472-481 (addStepToPhase function):**
```typescript
const addStepToPhase = (skuId: string, phaseNumber: string) => {
  const steps = skuStepsMap.value[skuId] || []
  const stepsInPhase = steps.filter(s => s.phase_number === phaseNumber)
  const nextSub = stepsInPhase.length > 0 ? Math.max(...stepsInPhase.map(s => s.sub_step)) + 10 : 10
  
  // FIX: Create a completely new object
  stepForm.value = {
    sku_id: skuId,  // Explicitly set first
    phase_number: phaseNumber,
    phase_id: stepsInPhase[0]?.phase_id || '',
    sub_step: nextSub,
    action: '',
    re_code: '',
    action_code: '',
    destination: '',
    require: 0,
    uom: 'kg',
    low_tol: 0.001,
    high_tol: 0.001,
    step_condition: '',
    agitator_rpm: 0,
    high_shear_rpm: 0,
    temperature: 0,
    temp_low: 0,
    temp_high: 0,
    step_time: 0,
    brix_sp: '',
    ph_sp: '',
    qc_temp: false,
    record_steam_pressure: false,
    record_ctw: false,
    operation_brix_record: false,
    operation_ph_record: false,
    master_step: stepsInPhase.length === 0,
    step_id: undefined
  }
  editingStep.value = null
  showStepDialog.value = true
  if (!expandedPhases.value[skuId]) expandedPhases.value[skuId] = []
  if (!expandedPhases.value[skuId].includes(phaseNumber)) expandedPhases.value[skuId].push(phaseNumber)
}
```

### Backend Validation (router_skus.py)

Add validation to ensure sku_id is not accidentally changed during updates:

**Lines 142-154 (update_sku_step function):**
```python
@router.put("/sku-steps/{step_id}", response_model=schemas.SkuStep)
def update_sku_step(step_id: int, step: schemas.SkuStepCreate, db: Session = Depends(get_db)):
    """Update SKU step."""
    db_step = db.query(models.SkuStep).filter(models.SkuStep.id == step_id).first()
    if db_step is None:
        raise HTTPException(status_code=404, detail="Step not found")
    
    # Prevent changing sku_id during update
    original_sku_id = db_step.sku_id
    
    for key, value in step.model_dump().items():
        # Skip sku_id to prevent accidental changes
        if key != 'sku_id':
            setattr(db_step, key, value)
    
    # Ensure sku_id remains unchanged
    db_step.sku_id = original_sku_id
    
    db.commit()
    db.refresh(db_step)
    return db_step
```

## Testing

After applying the fix:
1. Select SKU-A
2. Add a new step
3. Verify the step is only added to SKU-A
4. Select SKU-B
5. Add a new step
6. Verify the step is only added to SKU-B and NOT to SKU-A

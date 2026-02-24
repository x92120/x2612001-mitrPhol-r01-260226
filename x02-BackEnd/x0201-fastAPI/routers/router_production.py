"""
Production Router
=================
Production plans, batches, and related endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Optional
from datetime import datetime
import logging

import crud
import models
import schemas
from database import get_db

from pydantic import BaseModel
class RecheckBagRequest(BaseModel):
    box_id: str
    bag_barcode: str
    operator: str

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Production"])


# =============================================================================
# PRODUCTION PLAN ENDPOINTS
# =============================================================================

@router.get("/production-plans/", response_model=List[schemas.ProductionPlan])
def get_production_plans(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all production plans with their batches."""
    return crud.get_production_plans(db, skip=skip, limit=limit)

@router.get("/production-plans/{plan_id}", response_model=schemas.ProductionPlan)
def get_production_plan(plan_id: int, db: Session = Depends(get_db)):
    """Get a specific production plan by database ID."""
    db_plan = crud.get_production_plan(db, plan_id=plan_id)
    if not db_plan:
        raise HTTPException(status_code=404, detail="Production plan not found")
    return db_plan

@router.post("/production-plans/", response_model=schemas.ProductionPlan)
def create_production_plan(plan: schemas.ProductionPlanCreate, db: Session = Depends(get_db)):
    """Create a new production plan and its batches."""
    return crud.create_production_plan(db=db, plan_data=plan)

@router.put("/production-plans/{plan_id}", response_model=schemas.ProductionPlan)
def update_production_plan(plan_id: int, plan: schemas.ProductionPlanCreate, db: Session = Depends(get_db)):
    """Update a production plan."""
    db_plan = crud.update_production_plan(db, plan_id=plan_id, plan_update=plan)
    if not db_plan:
        raise HTTPException(status_code=404, detail="Production plan not found")
    return db_plan

@router.delete("/production-plans/{plan_id}")
def cancel_production_plan(plan_id: int, cancel_data: schemas.ProductionPlanCancel, db: Session = Depends(get_db)):
    """Cancel a production plan and its batches."""
    db_plan = crud.cancel_production_plan(
        db, 
        plan_id=plan_id, 
        comment=cancel_data.comment, 
        changed_by=cancel_data.changed_by
    )
    if not db_plan:
        raise HTTPException(status_code=404, detail="Production plan not found")
    return {"status": "success", "message": "Plan and batches cancelled"}


# =============================================================================
# PRODUCTION BATCH ENDPOINTS
# =============================================================================

@router.get("/production-batches/", response_model=List[schemas.ProductionBatch])
def get_production_batches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all production batches."""
    return crud.get_production_batches(db, skip=skip, limit=limit)

# NOTE: This must come BEFORE /production-batches/{batch_id} to avoid route conflict
@router.get("/production-batches/ready-to-deliver")
def get_ready_to_deliver(db: Session = Depends(get_db)):
    """Get batches that have at least one boxed warehouse but are not yet delivered."""
    batches = db.query(models.ProductionBatch).filter(
        (models.ProductionBatch.fh_boxed_at.isnot(None)) | (models.ProductionBatch.spp_boxed_at.isnot(None)),
    ).all()
    result = []
    for b in batches:
        result.append({
            "id": b.id,
            "batch_id": b.batch_id,
            "sku_id": b.sku_id,
            "plant": b.plant,
            "production": bool(b.production),
            "fh_boxed_at": b.fh_boxed_at.isoformat() if b.fh_boxed_at else None,
            "spp_boxed_at": b.spp_boxed_at.isoformat() if b.spp_boxed_at else None,
            "fh_delivered_at": b.fh_delivered_at.isoformat() if b.fh_delivered_at else None,
            "fh_delivered_by": b.fh_delivered_by,
            "spp_delivered_at": b.spp_delivered_at.isoformat() if b.spp_delivered_at else None,
            "spp_delivered_by": b.spp_delivered_by,
        })
    return result

@router.get("/production-batches/{batch_id}", response_model=schemas.ProductionBatch)
def get_production_batch(batch_id: int, db: Session = Depends(get_db)):
    """Get a specific production batch by database ID."""
    db_batch = crud.get_production_batch(db, batch_id=batch_id)
    if not db_batch:
        raise HTTPException(status_code=404, detail="Production batch not found")
    return db_batch

@router.put("/production-batches/{batch_id}", response_model=schemas.ProductionBatch)
def update_production_batch(batch_id: int, batch: schemas.ProductionBatchUpdate, db: Session = Depends(get_db)):
    """Update a production batch."""
    db_batch = crud.update_production_batch(db, batch_id=batch_id, batch_update=batch)
    if not db_batch:
        raise HTTPException(status_code=404, detail="Production batch not found")
    return db_batch

@router.patch("/production-batches/{batch_id}/status", response_model=schemas.ProductionBatch)
def update_production_batch_status(batch_id: int, status: str, db: Session = Depends(get_db)):
    """Quickly update batch status."""
    db_batch = crud.update_production_batch_status(db, batch_id=batch_id, status=status)
    if not db_batch:
        raise HTTPException(status_code=404, detail="Production batch not found")
    return db_batch

@router.get("/production-batches/by-batch-id/{batch_id_str}", response_model=schemas.ProductionBatch)
def get_production_batch_by_id_str(batch_id_str: str, db: Session = Depends(get_db)):
    """Get a specific production batch by its string ID (e.g. 20251112-01001)."""
    db_batch = db.query(models.ProductionBatch).filter(models.ProductionBatch.batch_id == batch_id_str).first()
    if not db_batch:
        raise HTTPException(status_code=404, detail="Production batch not found")
    return db_batch


# =============================================================================
# PREBATCH RECORD ENDPOINTS
# =============================================================================

@router.get("/prebatch-recs/summary/{batch_id}")
@router.get("/prebatch_recs/summary/{batch_id}")
def get_prebatch_records_summary(batch_id: str, db: Session = Depends(get_db)):
    """
    Returns a summary of prebatch records grouped by ingredient.
    Matches records by either batch_record_id prefix or plan_id.
    """
    # Try searching by full batch ID prefix first
    records = db.query(models.PreBatchRec).filter(
        models.PreBatchRec.batch_record_id.like(f"{batch_id}%")
    ).all()
    
    # If no records found, try searching by plan_id if the batch_id looks like a Plan ID
    # or find records where plan_id matches the prefix of the batch_id
    if not records:
        # Example batch_id: plan-Line-3-2026-02-07-003-003
        # Extract plan part: plan-Line-3-2026-02-07-003
        plan_part = "-".join(batch_id.split("-")[:-1]) if "-" in batch_id else batch_id
        records = db.query(models.PreBatchRec).filter(
            models.PreBatchRec.plan_id == plan_part
        ).all()
    
    summary = {}
    for r in records:
        if r.re_code not in summary:
            # Try to find ingredient name
            ing = db.query(models.Ingredient).filter(models.Ingredient.re_code == r.re_code).first()
            summary[r.re_code] = {
                "id": r.req_id,
                "re_code": r.re_code,
                "ingredient_name": ing.name if ing else r.re_code,
                "required_volume": r.total_volume or 0,
                "net_volume": 0,
                "package_count": 0,
                "total_packages": r.total_packages or 0,
                "wh": r.req.wh if r.req else "-",
                "status": 1
            }
        
        summary[r.re_code]["net_volume"] += r.net_volume or 0
        summary[r.re_code]["package_count"] += 1
        
        if r.package_no >= (r.total_packages or 0) and r.total_packages:
            summary[r.re_code]["status"] = 2

    return list(summary.values())

@router.get("/prebatch-recs/", response_model=List[schemas.PreBatchRec])
def get_prebatch_recs(skip: int = 0, limit: int = 100, wh: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all prebatch records."""
    return crud.get_prebatch_recs(db, skip=skip, limit=limit, wh=wh)

@router.get("/prebatch-reqs/by-batch/{batch_id}", response_model=List[schemas.PreBatchReq])
def get_prebatch_reqs_by_batch(batch_id: str, db: Session = Depends(get_db)):
    """Get prebatch requirements filtered by batch ID."""
    return crud.get_prebatch_reqs_by_batch(db, batch_id=batch_id)

@router.get("/prebatch-reqs/summary-by-plan/{plan_id}")
def get_prebatch_reqs_summary_by_plan(plan_id: str, db: Session = Depends(get_db)):
    """Get ingredient requirements summarized across all batches for a plan."""
    reqs = db.query(models.PreBatchReq).filter(models.PreBatchReq.plan_id == plan_id).all()
    
    # Pre-fetch warehouse from ingredients table by re_code
    re_codes = list(set(r.re_code for r in reqs if r.re_code))
    ing_wh_map: dict = {}
    if re_codes:
        ings = db.query(models.Ingredient.re_code, models.Ingredient.warehouse).filter(
            models.Ingredient.re_code.in_(re_codes)
        ).all()
        for ing in ings:
            if ing.re_code and ing.warehouse:
                ing_wh_map[ing.re_code] = ing.warehouse
    
    # Group by re_code and sum required_volume
    summary: dict = {}
    for req in reqs:
        if req.re_code not in summary:
            summary[req.re_code] = {
                "re_code": req.re_code,
                "ingredient_name": req.ingredient_name,
                "total_required": 0,
                "batch_count": 0,
                "per_batch": req.required_volume or 0,
                "wh": ing_wh_map.get(req.re_code, req.wh or "-"),
                "status": 0,  # 0=Pending, 1=InProgress, 2=Done
                "completed_batches": 0
            }
        summary[req.re_code]["total_required"] += req.required_volume or 0
        summary[req.re_code]["batch_count"] += 1
        if req.status == 2:
            summary[req.re_code]["completed_batches"] += 1
    
    # Determine status per ingredient
    for key in summary:
        s = summary[key]
        if s["completed_batches"] >= s["batch_count"] and s["batch_count"] > 0:
            s["status"] = 2  # All batches done
        elif s["completed_batches"] > 0:
            s["status"] = 1  # Some batches done
        s["total_required"] = round(s["total_required"], 4)
    
    return list(summary.values())

@router.get("/prebatch-reqs/batches-by-ingredient/{plan_id}/{re_code}")
def get_batches_for_ingredient(plan_id: str, re_code: str, db: Session = Depends(get_db)):
    """Get per-batch detail for a specific ingredient within a plan."""
    reqs = db.query(models.PreBatchReq).filter(
        models.PreBatchReq.plan_id == plan_id,
        models.PreBatchReq.re_code == re_code
    ).order_by(models.PreBatchReq.batch_id).all()
    
    result = []
    for req in reqs:
        # Sum actual volume from prebatch_recs for this batch + re_code
        recs = db.query(models.PreBatchRec).filter(
            models.PreBatchRec.batch_record_id.like(f"{req.batch_id}-{re_code}%")
        ).all()
        actual = sum(r.net_volume or 0 for r in recs)
        
        result.append({
            "batch_id": req.batch_id,
            "required_volume": req.required_volume or 0,
            "actual_volume": round(actual, 4),
            "status": req.status,  # 0=Wait, 1=Batch, 2=Done
            "req_id": req.id
        })
    
    return result

@router.put("/prebatch-reqs/{req_id}/status")
def update_prebatch_req_status_by_id(req_id: int, status: int, db: Session = Depends(get_db)):
    """Update the status of a prebatch requirement by its ID. 0=Pending, 1=In-Progress, 2=Completed."""
    req = db.query(models.PreBatchReq).filter(models.PreBatchReq.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    req.status = status
    db.commit()
    db.refresh(req)
    return {"id": req.id, "status": req.status}

@router.get("/prebatch-recs/by-batch/{batch_id}", response_model=List[schemas.PreBatchRec])
def get_prebatch_recs_by_batch(batch_id: str, db: Session = Depends(get_db)):
    """Get prebatch records filtered by batch ID."""
    return crud.get_prebatch_recs_by_batch(db, batch_id=batch_id)

@router.get("/prebatch-recs/by-plan/{plan_id}", response_model=List[schemas.PreBatchRec])
def get_prebatch_recs_by_plan(plan_id: str, db: Session = Depends(get_db)):
    """Get prebatch records filtered by production plan ID."""
    return crud.get_prebatch_recs_by_plan(db, plan_id=plan_id)

@router.post("/prebatch-recs/", response_model=schemas.PreBatchRec)
def create_prebatch_rec(record: schemas.PreBatchRecCreate, db: Session = Depends(get_db)):
    """Create a new prebatch record (transaction)."""
    return crud.create_prebatch_rec(db=db, record=record)

@router.delete("/prebatch-recs/{record_id}")
def delete_prebatch_rec(record_id: int, db: Session = Depends(get_db)):
    """Delete a prebatch record and revert inventory."""
    success = crud.delete_prebatch_rec(db, record_id=record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"status": "success"}


class PackingStatusUpdate(BaseModel):
    packing_status: int  # 0=Unpacked, 1=Packed
    packed_by: Optional[str] = None


@router.patch("/prebatch-recs/{record_id}/packing-status")
def update_packing_status(record_id: int, data: PackingStatusUpdate, db: Session = Depends(get_db)):
    """Update the packing status of a prebatch record (0=Unpacked, 1=Packed)."""
    rec = db.query(models.PreBatchRec).filter(models.PreBatchRec.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")

    rec.packing_status = data.packing_status
    if data.packing_status == 1:
        rec.packed_at = datetime.now()
        rec.packed_by = data.packed_by or "operator"
    else:
        rec.packed_at = None
        rec.packed_by = None

    db.commit()
    db.refresh(rec)
    return {
        "id": rec.id,
        "packing_status": rec.packing_status,
        "packed_at": rec.packed_at,
        "packed_by": rec.packed_by,
    }

# =============================================================================
# PACKING & DELIVERY ENDPOINTS
# =============================================================================

@router.patch("/production-batches/by-batch-id/{batch_id_str}/box-close")
def close_box(batch_id_str: str, data: schemas.BoxCloseRequest, db: Session = Depends(get_db)):
    """Mark a warehouse box as closed (Boxed) for a batch."""
    batch = db.query(models.ProductionBatch).filter(
        models.ProductionBatch.batch_id == batch_id_str
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    wh = data.wh.upper()
    now = datetime.now()
    if wh == "FH":
        batch.fh_boxed_at = now
    elif wh == "SPP":
        batch.spp_boxed_at = now
    else:
        raise HTTPException(status_code=400, detail=f"Invalid warehouse: {wh}. Must be FH or SPP.")

    db.commit()
    db.refresh(batch)
    return {
        "status": "success",
        "batch_id": batch.batch_id,
        "wh": wh,
        "boxed_at": now.isoformat(),
        "fh_boxed_at": batch.fh_boxed_at.isoformat() if batch.fh_boxed_at else None,
        "spp_boxed_at": batch.spp_boxed_at.isoformat() if batch.spp_boxed_at else None,
    }


@router.patch("/production-batches/by-batch-id/{batch_id_str}/deliver")
def deliver_batch(batch_id_str: str, data: schemas.DeliveryRequest, db: Session = Depends(get_db)):
    """Mark a batch warehouse as delivered. FH→SPP or SPP→Production Hall."""
    batch = db.query(models.ProductionBatch).filter(
        models.ProductionBatch.batch_id == batch_id_str
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    wh = data.wh.upper()
    now = datetime.now()
    operator = data.delivered_by or "operator"
    if wh == "FH":
        batch.fh_delivered_at = now
        batch.fh_delivered_by = operator
    elif wh == "SPP":
        batch.spp_delivered_at = now
        batch.spp_delivered_by = operator
    else:
        raise HTTPException(status_code=400, detail=f"Invalid warehouse: {wh}. Must be FH or SPP.")

    db.commit()
    db.refresh(batch)
    return {
        "status": "success",
        "batch_id": batch.batch_id,
        "wh": wh,
        "delivered_at": now.isoformat(),
        "delivered_by": operator,
    }





# =============================================================================
# DASHBOARD & ANALYTICS
# =============================================================================

@router.get("/production-stats/summary")
def get_production_summary_stats(db: Session = Depends(get_db)):
    """Get high-level production summary stats for dashboard."""
    total_plans = db.query(models.ProductionPlan).count()
    active_plans = db.query(models.ProductionPlan).filter(models.ProductionPlan.status == "In-Progress").count()
    completed_plans = db.query(models.ProductionPlan).filter(models.ProductionPlan.status == "Completed").count()
    
    total_batches = db.query(models.ProductionBatch).count()
    pending_batches = db.query(models.ProductionBatch).filter(models.ProductionBatch.status == "Created").count()
    
    # Simple count of records today
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    records_today = db.query(models.PreBatchRec).filter(models.PreBatchRec.created_at >= today_start).count()
    
    return {
        "plans": {
            "total": total_plans,
            "active": active_plans,
            "completed": completed_plans
        },
        "batches": {
            "total": total_batches,
            "pending": pending_batches
        },
        "records_today": records_today,
        "timestamp": datetime.now()
    }

# =============================================================================
# RE-CHECK / VERIFICATION LOGIC
# =============================================================================

@router.get("/prebatch-recs/recheck-box/{box_id}")
def get_recheck_box_details(box_id: str, db: Session = Depends(get_db)):
    """
    Get all bags for a box/batch with target volumes and tolerances for re-check.
    """
    # 1. Find all bags actually weighed for this box
    records = db.query(models.PreBatchRec).filter(
        models.PreBatchRec.batch_record_id.like(f"{box_id}%")
    ).all()

    if not records:
        # Maybe box_id is a partial or plan_id, try finding by plan_id
        records = db.query(models.PreBatchRec).filter(
            models.PreBatchRec.plan_id == box_id
        ).all()

    if not records:
        raise HTTPException(status_code=404, detail="No packing bags found for this Box ID")

    # Get Plan and SKU to find tolerances
    plan_id = records[0].plan_id
    plan = db.query(models.ProductionPlan).filter(models.ProductionPlan.plan_id == plan_id).first()
    sku_id = plan.sku_id if plan else None

    result_bags = []
    for r in records:
        # Get target from requirement
        req = db.query(models.PreBatchReq).filter(models.PreBatchReq.id == r.req_id).first()
        target_vol = req.required_volume if req else r.total_volume
        
        # Get tolerance from SKU steps
        tolerance = 0.05 # Default 50g if not found
        if sku_id:
            step = db.query(models.SkuStep).filter(
                models.SkuStep.sku_id == sku_id,
                models.SkuStep.re_code == r.re_code
            ).first()
            if step:
                # Use high_tol if available, else 1% of target
                tolerance = step.high_tol if step.high_tol > 0 else (target_vol * 0.01)

        result_bags.append({
            "id": r.id,
            "batch_record_id": r.batch_record_id,
            "re_code": r.re_code,
            "package_no": r.package_no,
            "total_packages": r.total_packages,
            "net_volume": r.net_volume,
            "target_volume": target_vol,
            "tolerance": tolerance,
            "status": r.recheck_status,
            "recheck_at": r.recheck_at,
            "recheck_by": r.recheck_by,
            "is_valid": abs((r.net_volume or 0) - (target_vol or 0)) <= tolerance
        })

    return {
        "box_id": box_id,
        "plan_id": plan_id,
        "sku_id": sku_id,
        "sku_name": plan.sku_name if plan else "Unknown",
        "total_bags": len(records),
        "bags": result_bags
    }

@router.post("/prebatch-recs/recheck-bag")
def verify_bag_scan(data: RecheckBagRequest, db: Session = Depends(get_db)):
    """
    Verify a single bag scan against a box.
    """
    # 1. Find the bag
    bag = db.query(models.PreBatchRec).filter(models.PreBatchRec.batch_record_id == data.bag_barcode).first()
    if not bag:
        raise HTTPException(status_code=404, detail=f"Bag barcode {data.bag_barcode} not found")

    # 2. Verify it belongs to the box (prefix match)
    if not bag.batch_record_id.startswith(data.box_id) and bag.plan_id != data.box_id:
        raise HTTPException(status_code=400, detail="Bag does not belong to this Box")

    # 3. Get target and tolerance
    req = db.query(models.PreBatchReq).filter(models.PreBatchReq.id == bag.req_id).first()
    target_vol = req.required_volume if req else bag.total_volume
    
    plan = db.query(models.ProductionPlan).filter(models.ProductionPlan.plan_id == bag.plan_id).first()
    tolerance = 0.05
    if plan:
        step = db.query(models.SkuStep).filter(
            models.SkuStep.sku_id == plan.sku_id,
            models.SkuStep.re_code == bag.re_code
        ).first()
        if step:
            tolerance = step.high_tol if step.high_tol > 0 else (target_vol * 0.01)

    # 4. Perform check
    is_ok = abs((bag.net_volume or 0) - (target_vol or 0)) <= tolerance

    # 5. Update Status
    bag.recheck_status = 1 if is_ok else 2
    bag.recheck_at = datetime.now()
    bag.recheck_by = data.operator
    db.commit()

    return {
        "status": "OK" if is_ok else "ERROR",
        "message": "Verify Success" if is_ok else "Weight Mismatch",
        "bag": {
            "re_code": bag.re_code,
            "batch_record_id": bag.batch_record_id,
            "actual": bag.net_volume,
            "target": target_vol,
            "tolerance": tolerance,
            "diff": (bag.net_volume or 0) - (target_vol or 0)
        }
    }

@router.patch("/production-batches/{batch_id}/release")
def release_batch_to_production(batch_id: str, db: Session = Depends(get_db)):
    """
    Final approval for a box/batch. 
    Only permits if all bags are re-checked OK.
    """
    batch = db.query(models.ProductionBatch).filter(models.ProductionBatch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    bags = db.query(models.PreBatchRec).filter(
        models.PreBatchRec.batch_record_id.like(f"{batch_id}%")
    ).all()

    if not bags:
        raise HTTPException(status_code=400, detail="No bags found for this batch to verify")

    all_ok = all(b.recheck_status == 1 for b in bags)
    
    if not all_ok:
        pending_count = sum(1 for b in bags if b.recheck_status != 1)
        raise HTTPException(
            status_code=400, 
            detail=f"Re-check incomplete. {pending_count} bag(s) still pending or have errors."
        )

    batch.ready_to_product = True
    batch.status = "Ready for Production"
    db.commit()

    return {"status": "success", "message": "Batch released to production"}


@router.post("/sync-prebatch-wh")
def sync_prebatch_warehouse(db: Session = Depends(get_db)):
    """Sync all prebatch_reqs.wh from ingredient master warehouse field.
    Also normalizes SSP→SPP and sets empty warehouses to MIX."""
    # Step 0: Normalize SSP → SPP everywhere
    r0a = db.execute(text("UPDATE ingredients SET warehouse = 'SPP' WHERE warehouse = 'SSP'"))
    r0b = db.execute(text("UPDATE prebatch_reqs SET wh = 'SPP' WHERE wh = 'SSP'"))
    # Step 1: Set empty ingredient warehouses to MIX
    r1 = db.execute(text("""
        UPDATE ingredients SET warehouse = 'MIX'
        WHERE warehouse IS NULL OR warehouse = ''
    """))
    # Step 2: Sync prebatch_reqs.wh from ingredient master
    r2 = db.execute(text("""
        UPDATE prebatch_reqs pr
        JOIN ingredients i ON pr.re_code = i.re_code
        SET pr.wh = i.warehouse
        WHERE i.warehouse IS NOT NULL AND i.warehouse != '' AND pr.wh != i.warehouse
    """))
    db.commit()
    return {
        "status": "success",
        "ssp_to_spp": r0a.rowcount + r0b.rowcount,
        "ingredients_set_to_mix": r1.rowcount,
        "prebatch_reqs_synced": r2.rowcount
    }

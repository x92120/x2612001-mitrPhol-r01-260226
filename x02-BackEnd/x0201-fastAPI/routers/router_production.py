"""
Production Router
=================
Production plans, batches, and related endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import logging

import crud
import models
import schemas
from database import get_db

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

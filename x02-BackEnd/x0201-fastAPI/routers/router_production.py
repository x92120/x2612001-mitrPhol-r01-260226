"""
Production Router
=================
Production plans, batches, and related endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
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

@router.post("/production-plans/", response_model=schemas.ProductionPlan)
def create_production_plan(plan: schemas.ProductionPlanCreate, db: Session = Depends(get_db)):
    """Create new production plan."""
    try:
        return crud.create_production_plan(db, plan_data=plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/production-plans/", response_model=List[schemas.ProductionPlan])
def get_production_plans(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all production plans with pagination."""
    skip = max(0, skip)
    limit = min(max(1, limit), 1000)
    return crud.get_production_plans(db, skip=skip, limit=limit)


@router.put("/production-plans/{plan_id}", response_model=schemas.ProductionPlan)
def update_production_plan(plan_id: int, plan: schemas.ProductionPlanCreate, db: Session = Depends(get_db)):
    """Update production plan."""
    try:
        updated = crud.update_production_plan(db, plan_id=plan_id, plan_update=plan)
        if updated is None:
            raise HTTPException(status_code=404, detail="Plan not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Database error")


@router.post("/production-plans/{plan_id}/cancel", response_model=schemas.ProductionPlan)
def cancel_production_plan(plan_id: int, cancel_data: schemas.ProductionPlanCancel = None, db: Session = Depends(get_db)):
    """Cancel a production plan and all its associated batches."""
    try:
        comment = cancel_data.comment if cancel_data else None
        changed_by = cancel_data.changed_by if cancel_data else "system"
        
        cancelled = crud.cancel_production_plan(db, plan_id=plan_id, comment=comment, changed_by=changed_by)
        if cancelled is None:
            raise HTTPException(status_code=404, detail="Plan not found")
        return cancelled
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/production-plans/{plan_id}/history")
def get_production_plan_history(plan_id: int, db: Session = Depends(get_db)):
    """Get history of changes for a production plan."""
    history = db.query(models.ProductionPlanHistory).filter(
        models.ProductionPlanHistory.plan_db_id == plan_id
    ).order_by(models.ProductionPlanHistory.changed_at.desc()).all()
    
    return [{
        "id": h.id,
        "action": h.action,
        "old_status": h.old_status,
        "new_status": h.new_status,
        "remarks": h.remarks,
        "changed_by": h.changed_by,
        "changed_at": h.changed_at
    } for h in history]


# =============================================================================
# PRODUCTION BATCH ENDPOINTS
# =============================================================================

@router.get("/production-batches/", response_model=List[schemas.ProductionBatch])
def get_production_batches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all production batches with pagination."""
    skip = max(0, skip)
    limit = min(max(1, limit), 1000)
    return crud.get_production_batches(db, skip=skip, limit=limit)


@router.get("/production-batches/ids", response_model=List[str])
def get_production_batch_ids(db: Session = Depends(get_db)):
    """Get unique list of all production batch IDs."""
    batches = db.query(models.ProductionBatch.batch_id).distinct().all()
    return [b[0] for b in batches]


@router.get("/pre-batches/", response_model=List[schemas.ProductionBatch])
def get_pre_batches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Alias for /production-batches/ used by frontend dashboard."""
    return get_production_batches(skip=skip, limit=limit, db=db)


@router.put("/production-batches/{batch_id}", response_model=schemas.ProductionBatch)
def update_production_batch(batch_id: int, batch: schemas.ProductionBatchUpdate, db: Session = Depends(get_db)):
    """Update production batch."""
    try:
        db_batch = crud.update_production_batch(db, batch_id=batch_id, batch_update=batch)
        if db_batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        return db_batch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Database error")


# =============================================================================
# PREBATCH RECORD ENDPOINTS
# =============================================================================

@router.get("/prebatch-records/", response_model=List[schemas.PrebatchRecord])
def get_prebatch_records(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all prebatch records."""
    return crud.get_prebatch_records(db, skip=skip, limit=limit)


@router.get("/prebatch-records/by-plan/{plan_id}", response_model=List[schemas.PrebatchRecord])
def get_prebatch_records_by_plan(plan_id: str, db: Session = Depends(get_db)):
    """Get prebatch records filtered by plan ID."""
    return db.query(models.PrebatchRecord).filter(models.PrebatchRecord.plan_id == plan_id).all()


@router.post("/prebatch-records/", response_model=schemas.PrebatchRecord)
def create_prebatch_record(record: schemas.PrebatchRecordCreate, db: Session = Depends(get_db)):
    """Create new prebatch record."""
    try:
        return crud.create_prebatch_record(db, record=record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Database error")


# =============================================================================
# REPORTING ENDPOINTS
# =============================================================================

@router.get("/reports/ingredient-intake-summary")
def get_ingredient_intake_summary(start_date: str, end_date: str, db: Session = Depends(get_db)):
    """Get summary of ingredient intakes grouped by ingredient, filtered by date range."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        results = db.query(
            models.IngredientIntakeList.mat_sap_code.label('ingredient_id'),
            func.sum(models.IngredientIntakeList.intake_vol).label('total_intake_vol'),
            func.sum(models.IngredientIntakeList.package_intake).label('total_package_intake'),
            func.count(models.IngredientIntakeList.id).label('intake_count')
        ).filter(
            func.date(models.IngredientIntakeList.intake_at) >= start,
            func.date(models.IngredientIntakeList.intake_at) <= end
        ).group_by(
            models.IngredientIntakeList.mat_sap_code
        ).all()
        
        return [{
            "ingredient_id": r.ingredient_id,
            "ingredient_name": r.ingredient_id,
            "total_intake_vol": float(r.total_intake_vol or 0),
            "total_package_intake": int(r.total_package_intake or 0),
            "intake_count": r.intake_count
        } for r in results]

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")

"""
Stock Adjustment Router
========================
Endpoints for creating and listing stock adjustments.
Atomically updates remain_vol in ingredient_intake_lists.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session  # type: ignore[import-untyped]

from database import get_db  # type: ignore[import-untyped]
import models  # type: ignore[import-untyped]
import schemas  # type: ignore[import-untyped]

router = APIRouter(prefix="/stock-adjustments", tags=["Stock Adjustments"])


@router.get("/", response_model=list[schemas.StockAdjustment])
def list_adjustments(
    skip: int = 0,
    limit: int = 200,
    intake_lot_id: str | None = None,
    db: Session = Depends(get_db),
):
    """List stock adjustments with optional lot filter."""
    q = db.query(models.StockAdjustment).order_by(models.StockAdjustment.adjusted_at.desc())
    if intake_lot_id:
        q = q.filter(models.StockAdjustment.intake_lot_id == intake_lot_id)
    return q.offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.StockAdjustment, status_code=201)
def create_adjustment(
    payload: schemas.StockAdjustmentCreate,
    db: Session = Depends(get_db),
):
    """Create a stock adjustment and atomically update remain_vol."""
    # 1. Look up the intake record
    intake = (
        db.query(models.IngredientIntakeList)
        .filter(models.IngredientIntakeList.intake_lot_id == payload.intake_lot_id)
        .first()
    )
    if not intake:
        raise HTTPException(status_code=404, detail=f"Lot '{payload.intake_lot_id}' not found")

    prev_vol = intake.remain_vol or 0.0

    # 2. Calculate new volume
    if payload.adjust_type == "increase":
        new_vol = prev_vol + payload.adjust_qty
    else:  # decrease
        new_vol = prev_vol - payload.adjust_qty
        if new_vol < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot decrease by {payload.adjust_qty}. Current remain_vol is {prev_vol}",
            )

    # 3. Update remain_vol atomically
    intake.remain_vol = new_vol

    # 4. Create adjustment record
    adj = models.StockAdjustment(
        intake_lot_id=payload.intake_lot_id,
        mat_sap_code=intake.mat_sap_code,
        re_code=intake.re_code,
        material_description=intake.material_description,
        adjust_type=payload.adjust_type,
        adjust_reason=payload.adjust_reason,
        adjust_qty=payload.adjust_qty,
        prev_remain_vol=prev_vol,
        new_remain_vol=new_vol,
        remark=payload.remark,
        adjusted_by=payload.adjusted_by,
    )
    db.add(adj)
    db.commit()
    db.refresh(adj)
    return adj


# ── Lot Lookup (for the adjustment form) ────────────────────────────────────

@router.get("/lot-lookup/{lot_id}", response_model=schemas.LotLookup)
def lookup_lot(lot_id: str, db: Session = Depends(get_db)):
    """Look up an intake lot for stock adjustment form auto-fill."""
    intake = (
        db.query(models.IngredientIntakeList)
        .filter(models.IngredientIntakeList.intake_lot_id == lot_id)
        .first()
    )
    if not intake:
        raise HTTPException(status_code=404, detail=f"Lot '{lot_id}' not found")
    return intake


@router.get("/lot-search", response_model=list[schemas.LotLookup])
def search_lots(q: str = "", limit: int = 20, db: Session = Depends(get_db)):
    """Search intake lots by lot_id, mat_sap_code, or re_code."""
    if not q:
        return (
            db.query(models.IngredientIntakeList)
            .filter(models.IngredientIntakeList.status == "Active")
            .order_by(models.IngredientIntakeList.id.desc())
            .limit(limit)
            .all()
        )
    needle = f"%{q}%"
    return (
        db.query(models.IngredientIntakeList)
        .filter(
            models.IngredientIntakeList.status == "Active",
            (
                models.IngredientIntakeList.intake_lot_id.ilike(needle)
                | models.IngredientIntakeList.mat_sap_code.ilike(needle)
                | models.IngredientIntakeList.re_code.ilike(needle)
            ),
        )
        .order_by(models.IngredientIntakeList.id.desc())
        .limit(limit)
        .all()
    )

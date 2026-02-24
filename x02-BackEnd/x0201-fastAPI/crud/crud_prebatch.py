import logging
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import List, Optional
import models
import schemas

logger = logging.getLogger(__name__)


def _populate_wh(records: List[models.PreBatchRec]) -> List[models.PreBatchRec]:
    """Populate the transient `wh` field from the eager-loaded PreBatchReq relationship."""
    for rec in records:
        rec.wh = rec.req.wh if rec.req else "-"
    return records


def _base_rec_query(db: Session):
    """Base query for PreBatchRec with eager-loaded relationships (single SQL query)."""
    return db.query(models.PreBatchRec).options(
        joinedload(models.PreBatchRec.req),
        selectinload(models.PreBatchRec.origins),
    )


# ---------------------------------------------------------------------------
# PreBatch Record CRUD
# ---------------------------------------------------------------------------

def get_prebatch_recs(db: Session, skip: int = 0, limit: int = 100, wh: Optional[str] = None) -> List[models.PreBatchRec]:
    """Get PreBatch records with pagination, optionally filtered by warehouse."""
    query = _base_rec_query(db)
    if wh and wh != "All Warehouse":
        query = query.filter(models.PreBatchReq.wh == wh)
    records = query.order_by(models.PreBatchRec.created_at.desc()).offset(skip).limit(limit).all()
    return _populate_wh(records)


def get_prebatch_recs_by_plan(db: Session, plan_id: str) -> List[models.PreBatchRec]:
    """Get PreBatch records for a specific plan."""
    records = _base_rec_query(db).filter(models.PreBatchRec.plan_id == plan_id).all()
    return _populate_wh(records)


def get_prebatch_recs_by_batch(db: Session, batch_id: str) -> List[models.PreBatchRec]:
    """Get PreBatch records for a specific batch (prefix match on batch_record_id)."""
    records = _base_rec_query(db).filter(
        models.PreBatchRec.batch_record_id.like(f"{batch_id}%")
    ).all()
    return _populate_wh(records)


def _deduct_inventory(db: Session, re_code: str, intake_lot_id: str, volume: float):
    """Deduct `volume` from the matching inventory lot."""
    inv = db.query(models.IngredientIntakeList).filter(
        models.IngredientIntakeList.intake_lot_id == intake_lot_id,
        models.IngredientIntakeList.re_code == re_code,
    ).first()
    if inv:
        inv.remain_vol = (inv.remain_vol or 0) - volume


def _restore_inventory(db: Session, re_code: str, intake_lot_id: str, volume: float):
    """Restore `volume` to the matching inventory lot."""
    inv = db.query(models.IngredientIntakeList).filter(
        models.IngredientIntakeList.intake_lot_id == intake_lot_id,
        models.IngredientIntakeList.re_code == re_code,
    ).first()
    if inv:
        inv.remain_vol = (inv.remain_vol or 0) + volume


def create_prebatch_rec(db: Session, record: schemas.PreBatchRecCreate) -> models.PreBatchRec:
    """Create a new PreBatch record (transaction) and update inventory."""
    try:
        record_data = record.dict(exclude={'origins'})
        db_record = models.PreBatchRec(**record_data)

        # Auto-format prebatch_id
        if not db_record.prebatch_id and db_record.recode_batch_id and db_record.re_code:
            batch_id_str = ""
            if db_record.req_id:
                req = db.query(models.PreBatchReq).filter(models.PreBatchReq.id == db_record.req_id).first()
                if req:
                    batch_id_str = req.batch_id
            if not batch_id_str and db_record.batch_record_id:
                batch_id_str = db_record.batch_record_id.split(f"-{db_record.re_code}")[0]
            if batch_id_str:
                db_record.prebatch_id = f"{batch_id_str}{db_record.re_code}{db_record.recode_batch_id}"

        db.add(db_record)
        db.flush()

        # Inventory deduction — multi-lot or single-lot
        if record.origins:
            for origin in record.origins:
                db.add(models.PreBatchRecFrom(
                    prebatch_rec_id=db_record.id,
                    intake_lot_id=origin.intake_lot_id,
                    mat_sap_code=origin.mat_sap_code,
                    take_volume=origin.take_volume,
                ))
                _deduct_inventory(db, db_record.re_code, origin.intake_lot_id, origin.take_volume)
        elif db_record.intake_lot_id:
            _deduct_inventory(db, db_record.re_code, db_record.intake_lot_id, db_record.net_volume or 0)

        # Update requirement status
        if db_record.req_id:
            req = db.query(models.PreBatchReq).filter(models.PreBatchReq.id == db_record.req_id).first()
            if req:
                if db_record.package_no and db_record.total_packages and db_record.package_no >= db_record.total_packages:
                    req.status = 2  # Completed
                elif req.status == 0:
                    req.status = 1  # In-Progress

                # Auto-finalize batch when ALL requirements are completed
                batch = req.batch
                if batch:
                    all_reqs = db.query(models.PreBatchReq).filter(models.PreBatchReq.batch_db_id == batch.id).all()
                    if all(r.status == 2 for r in all_reqs):
                        batch.batch_prepare = True
                        if batch.status in ("Created", "In-Progress"):
                            batch.status = "Prepared"

        db.commit()
        db.refresh(db_record)
        return db_record
    except IntegrityError as e:
        db.rollback()
        logger.error("Integrity error in create_prebatch_rec: %s", e)
        raise ValueError(f"Database integrity error: {e}")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("SQLAlchemy error in create_prebatch_rec: %s", e)
        raise RuntimeError(f"Database error: {e}")
    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error in create_prebatch_rec")
        raise RuntimeError(f"Unexpected error: {e}")


def delete_prebatch_rec(db: Session, record_id: int) -> bool:
    """Delete a PreBatch record and revert inventory consumption (supports multi-lot origins)."""
    try:
        db_record = db.query(models.PreBatchRec).filter(models.PreBatchRec.id == record_id).first()
        if not db_record:
            return False

        # 1. Restore inventory — prefer origins (multi-lot), fall back to single lot
        origins = db.query(models.PreBatchRecFrom).filter(
            models.PreBatchRecFrom.prebatch_rec_id == record_id
        ).all()

        if origins:
            for origin in origins:
                _restore_inventory(db, db_record.re_code, origin.intake_lot_id, origin.take_volume)
        elif db_record.intake_lot_id:
            _restore_inventory(db, db_record.re_code, db_record.intake_lot_id, db_record.net_volume or 0)

        # 2. Revert requirement status
        if db_record.req_id:
            req = db.query(models.PreBatchReq).filter(models.PreBatchReq.id == db_record.req_id).first()
            if req:
                req.status = 1  # Back to In-Progress

        # 3. Delete record (origins cascade via FK)
        db.delete(db_record)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error("Error deleting prebatch record %d: %s", record_id, e)
        return False


# ---------------------------------------------------------------------------
# PreBatch Requirement CRUD
# ---------------------------------------------------------------------------

def get_prebatch_reqs_by_batch(db: Session, batch_id: str) -> List[models.PreBatchReq]:
    """Get ingredient requirements for a specific batch."""
    return db.query(models.PreBatchReq).filter(models.PreBatchReq.batch_id == batch_id).all()


def update_prebatch_req_status(db: Session, batch_id: str, re_code: str, status: int) -> bool:
    """Update requirement status (0=Pending, 1=In-Progress, 2=Completed)."""
    req = db.query(models.PreBatchReq).filter(
        models.PreBatchReq.batch_id == batch_id,
        models.PreBatchReq.re_code == re_code,
    ).first()
    if req:
        req.status = status
        db.commit()
        return True
    return False


def get_prebatch_req(db: Session, req_id: int) -> Optional[models.PreBatchReq]:
    return db.query(models.PreBatchReq).filter(models.PreBatchReq.id == req_id).first()


def ensure_prebatch_reqs_for_batch(db: Session, batch_id: str) -> bool:
    """Ensure PreBatch requirements exist for a batch; create from SKU recipe if missing."""
    if db.query(models.PreBatchReq).filter(models.PreBatchReq.batch_id == batch_id).count() > 0:
        return True

    batch = db.query(models.ProductionBatch).filter(models.ProductionBatch.batch_id == batch_id).first()
    if not batch:
        return False

    sku = db.query(models.Sku).filter(models.Sku.sku_id == batch.sku_id).first()
    if not sku:
        return False

    std_batch_size = sku.std_batch_size or 0

    # Aggregate ingredient requirements from recipe steps
    ingredient_info: dict = {}
    for step in sku.steps:
        if not step.re_code:
            continue
        if step.re_code not in ingredient_info:
            ing = db.query(models.Ingredient).filter(models.Ingredient.re_code == step.re_code).first()
            ingredient_info[step.re_code] = {
                'qty': step.require or 0,
                'name': ing.name if ing else step.re_code,
            }
        else:
            ingredient_info[step.re_code]['qty'] += (step.require or 0)

    try:
        created = False
        for re_code, info in ingredient_info.items():
            req_vol = info['qty']
            if std_batch_size > 0:
                req_vol = (req_vol / std_batch_size) * batch.batch_size

            # Warehouse from ingredient master (primary), fallback to first inventory lot
            wh_loc = "-"
            ing = db.query(models.Ingredient.warehouse).filter(
                models.Ingredient.re_code == re_code
            ).first()
            if ing and ing[0]:
                wh_loc = ing[0]
            else:
                first_stock = db.query(models.IngredientIntakeList.warehouse_location).filter(
                    models.IngredientIntakeList.re_code == re_code
                ).first()
                if first_stock:
                    wh_loc = first_stock[0]

            db.add(models.PreBatchReq(
                batch_db_id=batch.id,
                plan_id=batch.plan.plan_id if batch.plan else "-",
                batch_id=batch.batch_id,
                re_code=re_code,
                ingredient_name=info['name'],
                required_volume=round(req_vol, 4),
                wh=wh_loc,
                status=0,
            ))
            created = True

        if created:
            db.commit()
            return True
    except Exception as e:
        db.rollback()
        logger.error("Error creating requirements for %s: %s", batch_id, e)
        return False

    return False

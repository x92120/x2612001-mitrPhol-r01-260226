from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import List, Optional
import models
import schemas

# PreBatch Record CRUD (formerly PB Log)
def get_prebatch_recs(db: Session, skip: int = 0, limit: int = 100, wh: Optional[str] = None) -> List[models.PreBatchRec]:
    """Get list of PreBatch records (transactions) with pagination, optionally filtered by warehouse"""
    query = db.query(
        models.PreBatchRec
    ).outerjoin(models.PreBatchReq, models.PreBatchRec.req_id == models.PreBatchReq.id)
    
    if wh and wh != "All Warehouse":
        query = query.filter(models.PreBatchReq.wh == wh)
        
    records = query.order_by(models.PreBatchRec.created_at.desc()).offset(skip).limit(limit).all()
    
    # Manually populate wh field from the joined relationship if needed
    # Since we use outerjoin and models.PreBatchRec has relationship 'req', 
    # SQLAlchemy might already have 'req' populated.
    for rec in records:
        if rec.req:
            rec.wh = rec.req.wh
        else:
            rec.wh = "-"
            
    return records

def create_prebatch_rec(db: Session, record: schemas.PreBatchRecCreate) -> models.PreBatchRec:
    """Create new PreBatch record (transaction) and update inventory"""
    try:
        db_record = models.PreBatchRec(**record.dict())
        db.add(db_record)
        
        # Update Inventory remain_vol
        if db_record.intake_lot_id:
            inventory_item = db.query(models.IngredientIntakeList).filter(
                models.IngredientIntakeList.intake_lot_id == db_record.intake_lot_id,
                models.IngredientIntakeList.re_code == db_record.re_code
            ).first()
            
            if inventory_item:
                consumed_vol = db_record.net_volume or 0
                inventory_item.remain_vol = (inventory_item.remain_vol or 0) - consumed_vol
        
        # Update Requirement Status
        if db_record.req_id:
            req = db.query(models.PreBatchReq).filter(models.PreBatchReq.id == db_record.req_id).first()
            if req:
                if db_record.package_no and db_record.total_packages and db_record.package_no >= db_record.total_packages:
                    req.status = 2  # Completed
                elif req.status == 0:
                    req.status = 1  # In-Progress
        
        db.commit()
        db.refresh(db_record)
        return db_record
    except IntegrityError as e:
        db.rollback()
        print(f"INTEGRITY ERROR in create_prebatch_rec: {e}")
        raise ValueError(f"Database integrity error: {str(e)}")
    except SQLAlchemyError as e:
        db.rollback()
        print(f"SQLALCHEMY ERROR in create_prebatch_rec: {e}")
        raise RuntimeError(f"Database error: {str(e)}")
    except Exception as e:
        db.rollback()
        print(f"UNEXPECTED ERROR in create_prebatch_rec: {e}")
        raise RuntimeError(f"Unexpected error: {str(e)}")

def delete_prebatch_rec(db: Session, record_id: int) -> bool:
    """Delete a PreBatch record and revert inventory consumption"""
    try:
        db_record = db.query(models.PreBatchRec).filter(models.PreBatchRec.id == record_id).first()
        if not db_record:
            return False
            
        # 1. Restore Inventory
        if db_record.intake_lot_id:
            inventory_item = db.query(models.IngredientIntakeList).filter(
                models.IngredientIntakeList.intake_lot_id == db_record.intake_lot_id,
                models.IngredientIntakeList.re_code == db_record.re_code
            ).first()
            
            if inventory_item:
                inventory_item.remain_vol = (inventory_item.remain_vol or 0) + (db_record.net_volume or 0)
        
        # 2. Revert Requirement Status if needed
        if db_record.req_id:
            req = db.query(models.PreBatchReq).filter(models.PreBatchReq.id == db_record.req_id).first()
            if req:
                # Set back to In-Progress (1)
                req.status = 1 
        
        # 3. Delete the record
        db.delete(db_record)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error deleting prebatch record {record_id}: {e}")
        return False

# PreBatch Requirement CRUD (formerly PB Task)
def get_prebatch_reqs_by_batch(db: Session, batch_id: str) -> List[models.PreBatchReq]:
    """Get ingredient requirements for a specific batch"""
    return db.query(models.PreBatchReq).filter(models.PreBatchReq.batch_id == batch_id).all()

def update_prebatch_req_status(db: Session, batch_id: str, re_code: str, status: int) -> bool:
    """Update requirement status (0=Pending, 1=In-Progress, 2=Completed)"""
    req = db.query(models.PreBatchReq).filter(
        models.PreBatchReq.batch_id == batch_id,
        models.PreBatchReq.re_code == re_code
    ).first()
    if req:
        req.status = status
        db.commit()
        return True
    return False

def get_prebatch_req(db: Session, req_id: int) -> Optional[models.PreBatchReq]:
    return db.query(models.PreBatchReq).filter(models.PreBatchReq.id == req_id).first()

def ensure_prebatch_reqs_for_batch(db: Session, batch_id: str) -> bool:
    """
    Ensure PreBatch requirements exist for a given batch. If not, create them based on the SKU recipe.
    Returns True if requirements were created or already existed.
    """
    # Check if requirements already exist
    existing_count = db.query(models.PreBatchReq).filter(models.PreBatchReq.batch_id == batch_id).count()
    if existing_count > 0:
        return True

    # Find the batch and plan
    batch = db.query(models.ProductionBatch).filter(models.ProductionBatch.batch_id == batch_id).first()
    if not batch:
        return False

    # Find SKU
    sku = db.query(models.Sku).filter(models.Sku.sku_id == batch.sku_id).first()
    if not sku:
        return False

    recipe_steps = sku.steps
    std_batch_size = sku.std_batch_size or 0
    
    ingredient_info = {}
    for step in recipe_steps:
        if not step.re_code:
            continue
        if step.re_code not in ingredient_info:
            ing = db.query(models.Ingredient).filter(models.Ingredient.re_code == step.re_code).first()
            ing_name = ing.name if ing else step.re_code
            ingredient_info[step.re_code] = {'qty_per_std': (step.require or 0), 'name': ing_name}
        else:
            ingredient_info[step.re_code]['qty_per_std'] += (step.require or 0)

    try:
        reqs_created = False
        for re_code, info in ingredient_info.items():
            req_vol = info['qty_per_std']
            if std_batch_size > 0:
                req_vol = (req_vol / std_batch_size) * batch.batch_size
            
            wh_loc = "-"
            # Try to populate default WH from Intake List (FIFO or just any)
            first_stock = db.query(models.IngredientIntakeList.warehouse_location).filter(
                models.IngredientIntakeList.re_code == re_code
            ).first()
            if first_stock:
                wh_loc = first_stock[0]

            db_req = models.PreBatchReq(
                batch_db_id=batch.id,
                plan_id=batch.plan.plan_id if batch.plan else "-", 
                batch_id=batch.batch_id,
                re_code=re_code,
                ingredient_name=info['name'],
                required_volume=round(req_vol, 4),
                wh=wh_loc,
                status=0
            )
            db.add(db_req)
            reqs_created = True
        
        if reqs_created:
            db.commit()
            return True
    except Exception as e:
        db.rollback()
        print(f"Error creating requirements for {batch_id}: {e}")
        return False
    
    return False

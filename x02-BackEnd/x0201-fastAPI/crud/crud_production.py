from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional, List
from datetime import date, datetime
import math
import models
import schemas

# Production Plan CRUD
def get_production_plans(db: Session, skip: int = 0, limit: int = 100) -> List[models.ProductionPlan]:
    return db.query(models.ProductionPlan).options(joinedload(models.ProductionPlan.batches)).order_by(models.ProductionPlan.created_at.desc()).offset(skip).limit(limit).all()

def create_production_plan(db: Session, plan_data: schemas.ProductionPlanCreate) -> models.ProductionPlan:
    try:
        # Calculate Number of Batches if Total Volume and Batch Size are provided
        num_batches = plan_data.num_batches
        if not num_batches and plan_data.total_volume and plan_data.batch_size and plan_data.batch_size > 0:
             num_batches = math.ceil(plan_data.total_volume / plan_data.batch_size)

        # Calculate Total Plan Volume
        total_plan_volume = 0
        if num_batches and plan_data.batch_size:
            total_plan_volume = num_batches * plan_data.batch_size

        # Generate plan_id
        # Format: plan-{plant}-{yyyy-mm-dd}-{nnn}
        today = date.today()
        date_str = today.strftime("%Y-%m-%d")
        plant_str = plan_data.plant.replace(" ", "") if plan_data.plant else "Unknown"
        
        # Count existing plans for today to generate sequence
        # We can loosely filter by date string in plan_id or query by start_date/created_at
        # A simple robust way is:
        count = db.query(models.ProductionPlan).filter(
            models.ProductionPlan.created_at >= datetime.combine(today, datetime.min.time()),
            models.ProductionPlan.created_at <= datetime.combine(today, datetime.max.time())
        ).count()
        
        sequence = count + 1
        plan_id_str = f"plan-{plant_str}-{date_str}-{sequence:03d}"

        db_plan = models.ProductionPlan(
            plan_id=plan_id_str,
            sku_id=plan_data.sku_id,
            sku_name=plan_data.sku_name,
            plant=plan_data.plant,
            total_volume=plan_data.total_volume,
            total_plan_volume=total_plan_volume,
            batch_size=plan_data.batch_size,
            num_batches=num_batches,
            start_date=plan_data.start_date,
            finish_date=plan_data.finish_date,
            status=plan_data.status,
            created_by=plan_data.created_by or "system"
        )
        db.add(db_plan)
        db.commit()
        db.refresh(db_plan)

        # Create history record for plan creation
        history = models.ProductionPlanHistory(
            plan_db_id=db_plan.id,
            action="create",
            old_status=None,
            new_status=plan_data.status,
            remarks="Plan created",
            changed_by=plan_data.created_by or "system"
        )
        db.add(history)
        db.commit()

        # Automatically Create Batches and Requirements
        if num_batches and num_batches > 0:
            # 1. Fetch SKU and its steps for the recipe
            sku = db.query(models.Sku).filter(models.Sku.sku_id == plan_data.sku_id).first()
            recipe_steps = sku.steps if sku else []
            std_batch_size = sku.std_batch_size if sku else 0

            for i in range(1, num_batches + 1):
                # Use format: plan_id-001
                batch_id_str = f"{plan_id_str}-{i:03d}"
                
                db_batch = models.ProductionBatch(
                    plan_id=db_plan.id,
                    batch_id=batch_id_str,
                    sku_id=plan_data.sku_id,
                    plant=plan_data.plant,
                    batch_size=plan_data.batch_size,
                    status="Created"
                )
                db.add(db_batch)
                db.flush() # Ensure db_batch.id is available

                # 2. Create requirements for each ingredient in the recipe
                # We group by re_code because a recipe might have the same ingredient in multiple steps
                ingredient_info = {} # {re_code: {'qty': total, 'name': name}}
                for step in recipe_steps:
                    if not step.re_code:
                        continue
                        
                    # Calculate volume for this step's contribution to the batch
                    step_req = step.require or 0
                    if std_batch_size and std_batch_size > 0:
                        step_req = (step_req / std_batch_size) * plan_data.batch_size
                    
                    if step.re_code not in ingredient_info:
                        ingredient_info[step.re_code] = {'qty': 0, 'name': step.ingredient_name or step.re_code}
                    
                    ingredient_info[step.re_code]['qty'] += step_req

                for re_code, info in ingredient_info.items():
                    req_vol = info['qty']
                    ing_name = info['name']

                    # Try to find a default warehouse from inventory
                    wh_loc = "-"
                    first_stock = db.query(models.IngredientIntakeList.warehouse_location).filter(
                        models.IngredientIntakeList.re_code == re_code
                    ).first()
                    if first_stock:
                        wh_loc = first_stock[0]

                    db_req = models.PreBatchReq(
                        batch_db_id=db_batch.id,
                        plan_id=db_plan.plan_id,
                        batch_id=batch_id_str,
                        re_code=re_code,
                        ingredient_name=ing_name,
                        required_volume=round(req_vol, 4),
                        wh=wh_loc,
                        status=0 # 0=Pending
                    )
                    db.add(db_req)
            
            db.commit()
            db.refresh(db_plan) # Refresh to get batches
            
        return db_plan

    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database integrity error: {str(e)}")
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Database error: {str(e)}")

def get_production_batches(db: Session, skip: int = 0, limit: int = 100) -> List[models.ProductionBatch]:
   return db.query(models.ProductionBatch).order_by(models.ProductionBatch.created_at.desc()).offset(skip).limit(limit).all()

def update_production_batch_status(db: Session, batch_id: int, status: str) -> Optional[models.ProductionBatch]:
    batch = db.query(models.ProductionBatch).filter(models.ProductionBatch.id == batch_id).first()
    if batch:
        batch.status = status
        db.commit()
        db.refresh(batch)
    return batch

def update_production_batch(db: Session, batch_id: int, batch_update: schemas.ProductionBatchUpdate) -> Optional[models.ProductionBatch]:
    batch = db.query(models.ProductionBatch).filter(models.ProductionBatch.id == batch_id).first()
    if batch:
        update_data = batch_update.dict(exclude_unset=True)
        # Filter out keys that don't match model attributes
        for key, value in update_data.items():
            if hasattr(batch, key) and key != 'id': # Prevent ID update
                setattr(batch, key, value)
        
        db.commit()
        db.refresh(batch)
    return batch

def update_production_plan(db: Session, plan_id: int, plan_update: schemas.ProductionPlanCreate) -> Optional[models.ProductionPlan]:
    plan = db.query(models.ProductionPlan).filter(models.ProductionPlan.id == plan_id).first()
    if plan:
        old_status = plan.status
        update_data = plan_update.dict(exclude_unset=True)
        # Filter out keys that don't match model attributes
        for key, value in update_data.items():
            if hasattr(plan, key) and key != 'id': # Prevent ID update
                setattr(plan, key, value)
        
        # Set updated_by
        plan.updated_by = plan_update.created_by or "system"
        
        # Create history record if status changed
        if old_status != plan.status:
            history = models.ProductionPlanHistory(
                plan_db_id=plan.id,
                action="update",
                old_status=old_status,
                new_status=plan.status,
                remarks="Plan updated",
                changed_by=plan_update.created_by or "system"
            )
            db.add(history)
        
        db.commit()
        db.refresh(plan)
    return plan

def cancel_production_plan(db: Session, plan_id: int, comment: Optional[str] = None, changed_by: Optional[str] = None) -> Optional[models.ProductionPlan]:
    """Cancel a production plan and all its batches"""
    plan = db.query(models.ProductionPlan).filter(models.ProductionPlan.id == plan_id).first()
    if not plan:
        return None
    
    old_status = plan.status
    plan.status = "Cancelled"
    
    # Cancel all batches
    for batch in plan.batches:
        batch.status = "Cancelled"
    
    # Create history record
    history = models.ProductionPlanHistory(
        plan_db_id=plan.id,
        action="cancel",
        old_status=old_status,
        new_status="Cancelled",
        remarks=comment,
        changed_by=changed_by or "system"
    )
    db.add(history)
    
    db.commit()
    db.refresh(plan)
    return plan

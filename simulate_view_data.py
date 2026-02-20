import sys
import os
from datetime import date
from sqlalchemy.orm import Session

# Add the backend directory to sys.path to import modules
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "x02-BackEnd", "x0201-fastAPI"))
sys.path.append(backend_dir)

import models
import schemas
import crud
from database import SessionLocal, engine

def simulate_data():
    db = SessionLocal()
    try:
        # 1. Create a dummy SKU if not exists
        sku_id = "SKU-CONCEPT-01-001"
        sku = db.query(models.Sku).filter(models.Sku.sku_id == sku_id).first()
        if not sku:
            print(f"Creating SKU {sku_id}...")
            sku = models.Sku(
                sku_id=sku_id,
                sku_name="Flavour Concept 01",
                description="Simulation SKU for UI testing",
                std_batch_size=100.0,
                uom="kg"
            )
            db.add(sku)
            db.flush()
            
            # Add some steps to the SKU
            steps = [
                models.SkuStep(sku_id=sku_id, re_code="ING-001", action="ADD", require=10.0, uom="kg", sub_step=1),
                models.SkuStep(sku_id=sku_id, re_code="ING-002", action="ADD", require=20.0, uom="kg", sub_step=2),
                models.SkuStep(sku_id=sku_id, re_code="ING-003", action="ADD", require=30.0, uom="kg", sub_step=3),
            ]
            db.add_all(steps)
            db.flush()

        # 2. Create Ingredients if not exists
        for re_code in ["ING-001", "ING-002", "ING-003"]:
            ing = db.query(models.Ingredient).filter(models.Ingredient.re_code == re_code).first()
            if not ing:
                print(f"Creating Ingredient {re_code}...")
                ing = models.Ingredient(
                    re_code=re_code,
                    ingredient_id=re_code,
                    name=f"Ingredient {re_code.split('-')[1]}",
                    unit="kg",
                    creat_by="SystemSim"
                )
                db.add(ing)
        db.flush()

        # 3. Create a Production Plan
        plan_id_str = f"plan-UI-SIM-{date.today()}-999"
        
        # Cleanup of any plan or batch that might conflict
        conflicting_batch_ids = [f"plan-Line-2-{date.today()}-001-001", f"plan-Line-2-{date.today()}-001-002",
                                f"{plan_id_str}-001", f"{plan_id_str}-002"]
        for bid in conflicting_batch_ids:
            b = db.query(models.ProductionBatch).filter(models.ProductionBatch.batch_id == bid).first()
            if b:
                print(f"Conflicts found for Batch ID {bid}. Cleaning up...")
                items = db.query(models.PreBatchItem).filter(models.PreBatchItem.batch_db_id == b.id).all()
                for item in items:
                    db.query(models.PreBatchScan).filter(models.PreBatchScan.item_id == item.id).delete()
                db.query(models.PreBatchItem).filter(models.PreBatchItem.batch_db_id == b.id).delete()
                db.delete(b)
        
        existing_plans = db.query(models.ProductionPlan).filter(models.ProductionPlan.plan_id == plan_id_str).all()
        for plan in existing_plans:
            print(f"Plan {plan.plan_id} (DB ID: {plan.id}) already exists. Deleting...")
            batches = db.query(models.ProductionBatch).filter(models.ProductionBatch.plan_id == plan.id).all()
            for b in batches:
                items = db.query(models.PreBatchItem).filter(models.PreBatchItem.batch_db_id == b.id).all()
                for item in items:
                    db.query(models.PreBatchScan).filter(models.PreBatchScan.item_id == item.id).delete()
                db.query(models.PreBatchItem).filter(models.PreBatchItem.batch_db_id == b.id).delete()
                db.delete(b)
            db.delete(plan)
        db.commit()

        print(f"Creating Plan {plan_id_str}...")
        plan_data = schemas.ProductionPlanCreate(
            sku_id=sku_id,
            sku_name="Flavour Concept 01",
            plant="Line-2",
            total_volume=200.0,
            batch_size=100,
            num_batches=2,
            start_date=date.today(),
            status="Created",
            created_by="SystemSim"
        )
        
        # Use existing CRUD to create plan and batches
        new_plan = crud.create_production_plan(db, plan_data)
        
        # 4. Create PreBatchItems (Require Ingredients) for each batch
        # recreate_tasks logic but simplified
        batches = db.query(models.ProductionBatch).filter(models.ProductionBatch.plan_id == new_plan.id).all()
        for batch in batches:
            print(f"Creating requirements for Batch {batch.batch_id}...")
            # SKU steps were created above
            sku_steps = db.query(models.SkuStep).filter(models.SkuStep.sku_id == sku_id).all()
            for step in sku_steps:
                req_vol = (step.require / 100.0) * batch.batch_size
                
                ing_name_suffix = step.re_code.split('-')[1] if '-' in step.re_code else step.re_code
                db_item = models.PreBatchItem(
                    batch_db_id=batch.id,
                    plan_id=new_plan.plan_id,
                    batch_id=batch.batch_id,
                    re_code=step.re_code,
                    ingredient_name=f"Ingredient {ing_name_suffix}",
                    required_volume=round(req_vol, 4),
                    wh="Flavour House",
                    status=0
                )
                db.add(db_item)
        
        db.commit()
        print("Successfully simulated data.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    simulate_data()

import sys
import os

# Add the FastAPI directory to sys.path so we can import modules
sys.path.append(os.path.abspath("./x02-BackEnd/x0201-fastAPI"))

from database import SessionLocal
import models
from crud import crud_prebatch as crud

def main():
    db = SessionLocal()
    try:
        print("Starting repopulation of prebatch_items...")
        
        # Get all production batches
        batches = db.query(models.ProductionBatch).all()
        total = len(batches)
        print(f"Found {total} total batches to check.")
        
        count_created = 0
        count_skipped = 0
        count_failed = 0
        
        for idx, batch in enumerate(batches):
            try:
                # Check if items already exist to avoid duplicate logs if possible,
                # though ensure_prebatch_items_for_batch also does this check.
                existing = db.query(models.PreBatchItem).filter(models.PreBatchItem.batch_id == batch.batch_id).count()
                
                if idx % 10 == 0:
                    print(f"[{idx}/{total}] Processing batch: {batch.batch_id}...")
                
                if crud.ensure_prebatch_items_for_batch(db, batch.batch_id):
                    # If it existed before, ensure_prebatch_items_for_batch returns True
                    if existing == 0:
                        count_created += 1
                    else:
                        count_skipped += 1
                else:
                    print(f"  - Failed to generate items for batch {batch.batch_id}")
                    count_failed += 1
                    
            except Exception as e:
                print(f"  - Error processing batch {batch.batch_id}: {e}")
                count_failed += 1
        
        print("\n" + "="*40)
        print(f"Repopulation Complete!")
        print(f"Total Batches Processed: {total}")
        print(f"New Batches Populated: {count_created}")
        print(f"Existing Batches (Skipped): {count_skipped}")
        print(f"Failed Batches: {count_failed}")
        print("="*40)
        
    finally:
        db.close()

if __name__ == "__main__":
    main()

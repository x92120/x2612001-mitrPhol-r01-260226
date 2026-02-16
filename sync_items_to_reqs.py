import sys
import os

# Add the FastAPI directory to sys.path
sys.path.append(os.path.abspath("./x02-BackEnd/x0201-fastAPI"))

from database import SessionLocal
from sqlalchemy import text

def main():
    db = SessionLocal()
    try:
        print("Syncing data from prebatch_items to prebatch_reqs...")
        
        # 1. Clear prebatch_reqs first to avoid duplicates if this is run again
        db.execute(text("DELETE FROM prebatch_reqs"))
        
        # 2. Sync data using SQL for efficiency
        sql = """
        INSERT INTO prebatch_reqs (
            batch_db_id, plan_id, batch_id, re_code, 
            ingredient_name, required_volume, wh, status
        )
        SELECT 
            batch_db_id, plan_id, batch_id, re_code, 
            ingredient_name, required_volume, wh, status
        FROM prebatch_items;
        """
        result = db.execute(text(sql))
        db.commit()
        
        print(f"Successfully synced {result.rowcount} records to prebatch_reqs.")
        
    except Exception as e:
        print(f"Error during sync: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()

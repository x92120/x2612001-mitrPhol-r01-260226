import sys
import os

# Add the FastAPI directory to sys.path
sys.path.append(os.path.abspath("./x02-BackEnd/x0201-fastAPI"))

from database import SessionLocal
from sqlalchemy import text

def main():
    db = SessionLocal()
    try:
        print("Simulating scan data from prebatch_reqs to prebatch_recs...")
        
        # 1. Clear prebatch_recs first to avoid duplicates/errors
        db.execute(text("DELETE FROM prebatch_recs"))
        
        # 2. Generate scan records (one per requirement, 100% completed)
        # Using CONCAT(batch_id, '-', re_code) for a unique batch_record_id
        sql = """
        INSERT INTO prebatch_recs (
            req_id, batch_record_id, plan_id, re_code, 
            package_no, total_packages, net_volume, total_volume, 
            total_request_volume, intake_lot_id
        )
        SELECT 
            id, CONCAT(batch_id, '-', re_code), plan_id, re_code,
            1, 1, required_volume, required_volume,
            required_volume, 'SIMULATED'
        FROM prebatch_reqs;
        """
        result = db.execute(text(sql))
        db.commit()
        
        print(f"Successfully created {result.rowcount} scan records in prebatch_recs.")
        
    except Exception as e:
        print(f"Error during simulation: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()

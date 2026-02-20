import pymysql
import os
import json
import uuid
import sys
from datetime import datetime

print("Connecting to DB...")
try:
    conn = pymysql.connect(host='127.0.0.1', port=3307, user='mixingcontrol', password='admin100', database='xMixingControl')
    print("Connected.")
    
    with conn.cursor() as cursor:
        plan_id = "TEST-PLAN-2026-02-20"
        batch_id = "TEST-BATCH-001"
        bag_id = f"{batch_id}-BAG-01"
        re_code = "SUGAR-01"
        
        # 1. Create a Plan if it doesn't exist
        cursor.execute("SELECT id FROM production_plans WHERE plan_id = %s", (plan_id,))
        plan_row = cursor.fetchone()
        if not plan_row:
            print("Creating test plan...")
            cursor.execute("""
                INSERT INTO production_plans (plan_id, sku_id, sku_name, plant, total_volume, batch_size, num_batches, status)
                VALUES (%s, 'SKU-TEST-01', 'Test Sweet Mix', 'Line 1', 500, 100, 5, 'Planned')
            """, (plan_id,))
            plan_db_id = cursor.lastrowid
        else:
            plan_db_id = plan_row[0]

        # 2. Create a Batch if it doesn't exist
        cursor.execute("SELECT id FROM production_batches WHERE batch_id = %s", (batch_id,))
        batch_row = cursor.fetchone()
        if not batch_row:
            print("Creating test batch...")
            cursor.execute("""
                INSERT INTO production_batches (plan_id, batch_id, sku_id, plant, batch_size, status)
                VALUES (%s, %s, 'SKU-TEST-01', 'Line 1', 100, 'Created')
            """, (plan_db_id, batch_id))
            batch_db_id = cursor.lastrowid
        else:
            batch_db_id = batch_row[0]

        # 3. Create a PreBatchReq if it doesn't exist
        cursor.execute("SELECT id FROM preBatch_reqs WHERE plan_id = %s AND re_code = %s", (plan_id, re_code))
        req_row = cursor.fetchone()
        if not req_row:
            print("Creating test requirement...")
            cursor.execute("""
                INSERT INTO preBatch_reqs (batch_db_id, plan_id, batch_id, re_code, ingredient_name, required_volume, status)
                VALUES (%s, %s, %s, %s, 'White Sugar', 25.5, 1)
            """, (batch_db_id, plan_id, batch_id, re_code))
            req_id = cursor.lastrowid
        else:
            req_id = req_row[0]

        # 4. Create the Bag Record
        cursor.execute("SELECT id FROM preBatch_recs WHERE batch_record_id = %s", (bag_id,))
        if not cursor.fetchone():
            print("Creating test bag record...")
            cursor.execute("""
                INSERT INTO preBatch_recs (req_id, batch_record_id, plan_id, re_code, package_no, total_packages, net_volume, total_volume, intake_lot_id)
                VALUES (%s, %s, %s, %s, 1, 1, 25.48, 25.5, 'LOT-999')
            """, (req_id, bag_id, plan_id, re_code))
            
        conn.commit()
        print(f"Sample data created! Batch: {batch_id}, Bag: {bag_id}")

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn.open:
        conn.close()

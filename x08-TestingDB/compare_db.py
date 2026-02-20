#!/usr/bin/env python3
import pymysql
import sys

# --- Connection Configurations ---
LOCAL_DB_CONFIG = {
    'host': '127.0.0.1', 'port': 3307, 'user': 'mixingcontrol', 'password': 'admin100', 'database': 'xMixingControl', 'connect_timeout': 5
}
REMOTE_DB_CONFIG = {
    'host': '152.42.166.150', 'port': 3306, 'user': 'mixingcontrol', 'password': 'admin100', 'database': 'xMixingControl', 'connect_timeout': 10
}

def connect_to_db(config, name):
    try:
        conn = pymysql.connect(**config)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to {name} database: {e}")
        return None

def get_db_info(conn):
    info = {}
    with conn.cursor() as cursor:
        cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                info[table] = count
            except Exception as e:
                info[table] = f"Error: {e}"
                
        cursor.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW'")
        views = [row[0] for row in cursor.fetchall()]
        for view in views:
            info[view] = "VIEW"
            
    return info

def main():
    print("--- Database Comparison (Local vs Remote) ---")
    
    print("\nConnecting to Local DB...")
    local_conn = connect_to_db(LOCAL_DB_CONFIG, "Local")
    if not local_conn:
        sys.exit(1)
        
    print("Connecting to Remote DB...")
    remote_conn = connect_to_db(REMOTE_DB_CONFIG, "Remote")
    if not remote_conn:
        print("\n⚠️ Cannot compare: Remote database is unreachable.")
        local_conn.close()
        sys.exit(1)

    print("\nFetching data...")
    local_info = get_db_info(local_conn)
    remote_info = get_db_info(remote_conn)
    
    local_conn.close()
    remote_conn.close()

    print("\n--- Comparison Results ---")
    
    all_tables = sorted(list(set(local_info.keys()) | set(remote_info.keys())))
    
    print(f"{'Table/View Name':<30} | {'Local Count':<15} | {'Remote Count':<15} | {'Status'}")
    print("-" * 80)
    
    diff_count = 0
    for table in all_tables:
        local_val = local_info.get(table, "MISSING")
        remote_val = remote_info.get(table, "MISSING")
        
        status = "✅ MATCH"
        if local_val == "MISSING" or remote_val == "MISSING":
            status = "❌ MISSING"
            diff_count += 1
        elif local_val != remote_val:
            if local_val == "VIEW" or remote_val == "VIEW":
                status = "⚠️ TYPE MISMATCH"
            else:
                status = "⚠️ DATA DIFF"
            diff_count += 1
            
        print(f"{table:<30} | {str(local_val):<15} | {str(remote_val):<15} | {status}")

    print("-" * 80)
    if diff_count == 0:
        print("✅ Databases are perfectly in sync (Structure & Row Counts).")
    else:
        print(f"⚠️ Found {diff_count} differences between the databases.")

if __name__ == "__main__":
    main()

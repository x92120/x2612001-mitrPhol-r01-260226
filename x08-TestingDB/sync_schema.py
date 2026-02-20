#!/usr/bin/env python3
import pymysql
import sys

# --- Connection Configurations ---

# Local Database (Source)
LOCAL_DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3307,
    'user': 'mixingcontrol',
    'password': 'admin100',
    'database': 'xMixingControl',
    'connect_timeout': 5
}

# Remote Database (Destination)
REMOTE_DB_CONFIG = {
    'host': '152.42.166.150',
    'port': 3306,
    'user': 'mixingcontrol',
    'password': 'admin100',
    'database': 'xMixingControl',
    'connect_timeout': 10
}

def connect_to_db(config, name):
    try:
        print(f"Connecting to {name} database ({config['host']}:{config['port']})...")
        conn = pymysql.connect(**config)
        print(f"✅ Successfully connected to {name}.")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to {name} database.")
        print(f"Error: {e}")
        return None

def main():
    print("--- Database Schema Sync (Local -> Remote) ---")
    
    # 1. Connect to Local source
    local_conn = connect_to_db(LOCAL_DB_CONFIG, "Local")
    if not local_conn:
        sys.exit(1)
        
    # 2. Extract schemas from Local
    local_schemas = {}
    try:
        with local_conn.cursor() as cursor:
            # Get list of tables
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                print("No tables found in the local database.")
                sys.exit(0)
                
            print(f"Found {len(tables)} tables to sync.")
            
            # Get SHOW CREATE TABLE for each
            for table in tables:
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                result = cursor.fetchone()
                # result[0] is table name, result[1] is the CREATE statement
                # We add 'IF NOT EXISTS' to make it safe to run multiple times
                create_stmt = result[1].replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1)
                local_schemas[table] = create_stmt
                
    except Exception as e:
        print(f"❌ Error reading from local database: {e}")
        local_conn.close()
        sys.exit(1)
    finally:
        local_conn.close()

    # 3. Connect to Remote destination
    remote_conn = connect_to_db(REMOTE_DB_CONFIG, "Remote")
    if not remote_conn:
        print("\n⚠️ Note: The remote connection failed. This might be due to a firewall, VPN requirement, or the server being offline.")
        sys.exit(1)

    # 4. Apply schemas to Remote
    print("\nApplying schemas to Remote database...")
    success_count = 0
    fail_count = 0
    
    try:
        with remote_conn.cursor() as cursor:
            # Temporarily disable foreign key checks to avoid creation order issues
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            for table, stmt in local_schemas.items():
                try:
                    cursor.execute(stmt)
                    print(f"  [OK] Table '{table}' synced.")
                    success_count += 1
                except Exception as e:
                    print(f"  [ERROR] Table '{table}' failed: {e}")
                    fail_count += 1
            
            # Re-enable foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            remote_conn.commit()
            
    except Exception as e:
        print(f"❌ Error writing to remote database: {e}")
        sys.exit(1)
    finally:
        remote_conn.close()

    print("\n--- Sync Complete ---")
    print(f"Total tables synced successfully: {success_count}")
    if fail_count > 0:
        print(f"Tables failed to sync: {fail_count}")

if __name__ == "__main__":
    main()

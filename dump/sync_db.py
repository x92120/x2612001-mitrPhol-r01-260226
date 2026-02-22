"""
Database Sync: Remote DB -> Cloud DB
Reads all tables from Remote DB and syncs structure + data to Cloud DB.
Uses PyMySQL with timeout settings.
"""
import pymysql
import sys
import os
from datetime import datetime

# Database configs
REMOTE_DB = {
    'host': '192.168.121.11',
    'port': 3306,
    'user': 'mixingcontrol',
    'password': 'admin100',
    'database': 'xMixingControl',
    'connect_timeout': 10,
    'read_timeout': 30,
    'write_timeout': 30,
}

CLOUD_DB = {
    'host': '152.42.166.150',
    'port': 3306,
    'user': 'mixingcontrol',
    'password': 'admin100',
    'database': 'xMixingControl',
    'connect_timeout': 10,
    'read_timeout': 30,
    'write_timeout': 30,
}

DUMP_DIR = os.path.join(os.path.dirname(__file__), '..', 'dump')
os.makedirs(DUMP_DIR, exist_ok=True)

def get_connection(config, name):
    print(f"  Connecting to {name} ({config['host']})...", end=' ', flush=True)
    conn = pymysql.connect(**config)
    print("OK")
    return conn

def get_tables(cursor):
    cursor.execute("SHOW TABLES")
    return [row[0] for row in cursor.fetchall()]

def get_create_table(cursor, table):
    cursor.execute(f"SHOW CREATE TABLE `{table}`")
    return cursor.fetchone()[1]

def get_table_data(cursor, table):
    cursor.execute(f"SELECT * FROM `{table}`")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return columns, rows

def dump_to_file(tables_sql, dump_path):
    """Save SQL dump to file"""
    with open(dump_path, 'w', encoding='utf-8') as f:
        f.write(f"-- Database dump: xMixingControl\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Source: Remote DB (192.168.121.11)\n\n")
        f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")
        f.write(tables_sql)
        f.write("\nSET FOREIGN_KEY_CHECKS=1;\n")
    print(f"  Dump saved to: {dump_path}")

def escape_value(val):
    if val is None:
        return 'NULL'
    elif isinstance(val, (int, float)):
        return str(val)
    elif isinstance(val, datetime):
        return f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'"
    elif isinstance(val, bytes):
        return f"X'{val.hex()}'"
    else:
        escaped = str(val).replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"

def main():
    print("=" * 60)
    print("Database Sync: Remote DB -> Cloud DB")
    print("=" * 60)
    
    # Step 1: Connect to Remote DB and dump
    print("\n[1/3] Reading from Remote DB...")
    try:
        remote_conn = get_connection(REMOTE_DB, "Remote")
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
    
    remote_cursor = remote_conn.cursor()
    tables = get_tables(remote_cursor)
    print(f"  Found {len(tables)} tables: {', '.join(tables)}")
    
    all_sql = ""
    table_data = {}
    
    for table in tables:
        print(f"  Reading: {table}...", end=' ', flush=True)
        create_sql = get_create_table(remote_cursor, table)
        columns, rows = get_table_data(remote_cursor, table)
        table_data[table] = (create_sql, columns, rows)
        
        # Build SQL
        all_sql += f"-- Table: {table}\n"
        all_sql += f"DROP TABLE IF EXISTS `{table}`;\n"
        all_sql += f"{create_sql};\n\n"
        
        if rows:
            col_names = ', '.join([f'`{c}`' for c in columns])
            for row in rows:
                values = ', '.join([escape_value(v) for v in row])
                all_sql += f"INSERT INTO `{table}` ({col_names}) VALUES ({values});\n"
            all_sql += "\n"
        
        print(f"{len(rows)} rows")
    
    remote_conn.close()
    
    # Step 2: Save dump file
    print("\n[2/3] Saving dump file...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dump_path = os.path.join(DUMP_DIR, f'xMixingControl_{timestamp}.sql')
    dump_to_file(all_sql, dump_path)
    
    # Step 3: Sync to Cloud DB
    print("\n[3/3] Syncing to Cloud DB...")
    try:
        cloud_conn = get_connection(CLOUD_DB, "Cloud")
    except Exception as e:
        print(f"FAILED to connect to Cloud: {e}")
        print("  Dump file saved. You can import manually.")
        sys.exit(1)
    
    cloud_cursor = cloud_conn.cursor()
    cloud_cursor.execute("SET FOREIGN_KEY_CHECKS=0")
    
    for table in tables:
        create_sql, columns, rows = table_data[table]
        print(f"  Syncing: {table}...", end=' ', flush=True)
        
        try:
            cloud_cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
            cloud_cursor.execute(create_sql)
            
            if rows:
                col_names = ', '.join([f'`{c}`' for c in columns])
                placeholders = ', '.join(['%s'] * len(columns))
                insert_sql = f"INSERT INTO `{table}` ({col_names}) VALUES ({placeholders})"
                
                # Insert in batches of 100
                batch_size = 100
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i+batch_size]
                    cloud_cursor.executemany(insert_sql, batch)
            
            cloud_conn.commit()
            print(f"{len(rows)} rows OK")
        except Exception as e:
            print(f"ERROR: {e}")
            cloud_conn.rollback()
    
    cloud_cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    cloud_conn.commit()
    cloud_conn.close()
    
    print("\n" + "=" * 60)
    print("Sync complete!")
    print(f"  Dump file: {dump_path}")
    print(f"  Tables synced: {len(tables)}")
    print("=" * 60)

if __name__ == '__main__':
    main()

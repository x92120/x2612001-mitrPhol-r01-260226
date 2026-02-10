import pymysql
import os

DB_USER = "mixingcontrol"
DB_PASSWORD = "admin100"
DB_HOST = "152.42.166.150"
DB_PORT = 3306
DB_NAME = "xMixingControl"

try:
    print(f"Connecting to {DB_HOST}...")
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        connect_timeout=10
    )
    print("Connection successful!")
    with conn.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        result = cursor.fetchone()
        print(f"Connected to database: {result}")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")

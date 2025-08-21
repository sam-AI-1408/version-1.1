# inspect_users.py
import sqlite3, os
DB_PATH = r"C:\Users\ADMIN\Desktop\AI\backend\data\sam_ai.db"   # <-- change if different
print("Checking DB path:", DB_PATH)
if not os.path.exists(DB_PATH):
    print("DB file not found.")
else:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    print("Tables:", cur.fetchall())
    try:
        cur.execute("PRAGMA table_info(users);")
        print("users table schema:", cur.fetchall())
    except Exception as e:
        print("PRAGMA users error:", e)
    try:
        cur.execute("SELECT id, username, password FROM users LIMIT 20;")
        rows = cur.fetchall()
        print("users rows (id, username, password):")
        for r in rows:
            print(r)
        if not rows:
            print("-> users table is empty.")
    except Exception as e:
        print("SELECT users failed:", e)
    conn.close()

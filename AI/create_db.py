# create_db.py
import sqlite3

DB_NAME = "sam_ai.db"

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Create users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1
)
""")

# Create tasks table
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (id)
    ALTER TABLE tasks ADD COLUMN is_done BOOLEAN DEFAULT 0;

)
""")

# Create quests table
cursor.execute("""
CREATE TABLE IF NOT EXISTS quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    xp_reward INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
""")

conn.commit()
conn.close()
print(f"Database '{DB_NAME}' created successfully.")


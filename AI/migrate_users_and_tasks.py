# migrate_users_and_tasks.py
"""
Idempotent migration helper for Sam AI.
Adds missing columns to `users` and `tasks` tables (password_hash, xp, strength, growth, is_done, xp, created_at).
Safe to run multiple times. Creates tables if they do not exist.
"""

from main_app import create_app
from backend.extentions import db
from sqlalchemy import text, inspect
import sys

app = create_app()

def ensure_table_exists_users():
    # create a safe minimal users table if not exists
    exists = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")).fetchone()
    if not exists:
        print("Creating 'users' table (minimal schema).")
        db.session.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                xp INTEGER DEFAULT 0,
                strength INTEGER DEFAULT 2000,
                growth INTEGER DEFAULT 2000
            )
        """))
        db.session.commit()
        return

def ensure_table_exists_tasks():
    exists = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")).fetchone()
    if not exists:
        print("Creating 'tasks' table (minimal schema).")
        db.session.execute(text("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                title TEXT,
                description TEXT,
                is_done INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.session.commit()
        return

def add_missing_columns(table, desired_columns):
    insp = inspect(db.engine)
    try:
        cols = [c['name'] for c in insp.get_columns(table)]
    except Exception as e:
        print(f"Error inspecting {table}: {e}")
        return

    for name, definition in desired_columns.items():
        if name not in cols:
            sql = f"ALTER TABLE {table} ADD COLUMN {name} {definition};"
            print(f"Adding column to {table}: {name} ({definition})")
            db.session.execute(text(sql))
            db.session.commit()
        else:
            print(f"Column '{name}' already exists in {table}.")

with app.app_context():
    print("Using DB:", db.engine.url)

    # Ensure tables exist
    ensure_table_exists_users()
    ensure_table_exists_tasks()

    # Ensure users columns exist
    desired_users = {
        "password_hash": "TEXT",
        "xp": "INTEGER DEFAULT 0",
        "strength": "INTEGER DEFAULT 2000",
        "growth": "INTEGER DEFAULT 2000"
    }
    add_missing_columns("users", desired_users)

    # Ensure tasks columns exist
    desired_tasks = {
        "is_done": "INTEGER DEFAULT 0",
        "xp": "INTEGER DEFAULT 0",
        "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP"
    }
    add_missing_columns("tasks", desired_tasks)

    # Show final schema summary
    insp = inspect(db.engine)
    print("Final users columns:", [c['name'] for c in insp.get_columns("users")])
    print("Final tasks columns:", [c['name'] for c in insp.get_columns("tasks")])

print("Migration script finished.")

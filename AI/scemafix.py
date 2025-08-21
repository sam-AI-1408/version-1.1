# schema_fix.py
import os
from sqlalchemy import text, inspect
from backend.extentions import db
from main_app import create_app

app = create_app()

def ensure_column(table: str, name: str, definition: str):
    insp = inspect(db.engine)
    cols = [c['name'] for c in insp.get_columns(table)]
    if name not in cols:
        sql = f"ALTER TABLE {table} ADD COLUMN {name} {definition};"
        print("Running:", sql)
        db.session.execute(text(sql))
        db.session.commit()
    else:
        print(f"Column '{name}' already exists in '{table}'.")

with app.app_context():
    print("Using DB:", db.engine.url)

    # Ensure table exists
    exists = db.session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
    ).fetchone()
    if not exists:
        print("Table 'tasks' not found. Creating with expected schema...")
        db.session.execute(text("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                title TEXT,
                description TEXT,
                is_done INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """))
        db.session.commit()
        print("Created 'tasks' table.")
    else:
        # Add missing columns idempotently
        ensure_column("tasks", "is_done", "INTEGER DEFAULT 0")
        ensure_column("tasks", "xp", "INTEGER DEFAULT 0")
        ensure_column("tasks", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")

    # Show final columns
    insp = inspect(db.engine)
    print("Final tasks columns:", [c['name'] for c in insp.get_columns("tasks")])

print("Schema fix complete.")

# migrate_add_users_created_at.py
from main_app import create_app
from backend.extentions import db
from sqlalchemy import inspect, text

app = create_app()

with app.app_context():
    print("Using DB:", db.engine.url)

    insp = inspect(db.engine)

    # Ensure users table exists (create minimal table if not)
    exists = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")).fetchone()
    if not exists:
        print("Table 'users' does not exist — creating minimal 'users' table.")
        db.session.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                xp INTEGER DEFAULT 0,
                strength INTEGER DEFAULT 2000,
                growth INTEGER DEFAULT 2000,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            )
        """))
        db.session.commit()
        print("Created 'users' table with created_at. Done.")
    else:
        # Check columns and add created_at if missing
        cols = [c['name'] for c in insp.get_columns('users')]
        print("Existing users columns:", cols)
        if 'created_at' not in cols:
            print("Adding 'created_at' column to users...")
            db.session.execute(text("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT (CURRENT_TIMESTAMP);"))
            db.session.commit()
            print("Added 'created_at'.")
        else:
            print("'created_at' already exists in users.")

        # show final schema
        cols2 = [c['name'] for c in inspect(db.engine).get_columns('users')]
        print("Final users columns:", cols2)

print("Migration finished.")


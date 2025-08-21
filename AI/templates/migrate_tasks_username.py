# migrate_tasks_username.py
from main_app import create_app
from backend.extentions import db
from sqlalchemy import text, inspect

app = create_app()

with app.app_context():
    insp = inspect(db.engine)
    cols = [c['name'] for c in insp.get_columns('tasks')]
    print("tasks columns:", cols)
    if 'username' not in cols:
        print("Adding 'username' column to tasks...")
        db.session.execute(text("ALTER TABLE tasks ADD COLUMN username TEXT;"))
        db.session.commit()
    else:
        print("'username' column already exists.")

    # Populate username using user_id -> users.username
    # Only overwrite NULL / empty usernames
    updated = db.session.execute(text("""
        UPDATE tasks
        SET username = (
            SELECT username FROM users WHERE users.id = tasks.user_id
        )
        WHERE (username IS NULL OR username = '') AND user_id IS NOT NULL;
    """))
    db.session.commit()
    print("Populated usernames for tasks from user_id (if any).")
    # sanity
    rows = db.session.execute(text("SELECT id, user_id, username, completed, is_done FROM tasks LIMIT 10")).fetchall()
    for r in rows:
        print(r)

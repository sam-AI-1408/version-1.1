# migrate_passwords.py
from main_app import create_app
from backend.extentions import db
from sqlalchemy import text, inspect
import hashlib

app = create_app()

def hash_pw(pw: str) -> str:
    # SHA256 fallback hashing (works with earlier auth fallback)
    return hashlib.sha256(pw.encode('utf-8')).hexdigest()

with app.app_context():
    insp = inspect(db.engine)
    cols = [c['name'] for c in insp.get_columns('users')]
    print("users columns:", cols)

    # Copy password -> password_hash if password_hash empty/null
    rows = db.session.execute(text("SELECT id, password, password_hash FROM users")).fetchall()
    updated = 0
    for r in rows:
        uid = r[0]
        old = r[1]
        ph = r[2]
        if (ph is None or ph == "") and old:
            new_hash = hash_pw(old)
            db.session.execute(text("UPDATE users SET password_hash = :h WHERE id = :id"),
                               {"h": new_hash, "id": uid})
            updated += 1
    if updated:
        db.session.commit()
    print(f"Updated {updated} user password_hash entries.")
    # show a couple rows
    print(db.session.execute(text("SELECT id, username, password_hash IS NOT NULL as has_hash FROM users")).fetchall())

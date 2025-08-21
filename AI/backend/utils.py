# backend/auth.py
"""
Authentication helpers for Sam AI (no blueprints).
Provides:
- register_user(username, password) -> bool
- login_user(username, password) -> bool
- get_user(username) -> User | None
- Optional: change_password(username, new_password)
"""

try:
    # Preferred: werkzeug provides safe password hashing with salting
    from werkzeug.security import generate_password_hash, check_password_hash
    _USE_WERKZEUG = True
except Exception:
    # Fallback: simple SHA256 (less ideal but works if werkzeug not installed)
    import hashlib
    _USE_WERKZEUG = False

    def generate_password_hash(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def check_password_hash(stored_hash: str, password: str) -> bool:
        return stored_hash == hashlib.sha256(password.encode("utf-8")).hexdigest()

from .extentions import db
from .models import User


def _hash_password(password: str) -> str:
    """Return password hash using werkzeug if available, else SHA256 fallback."""
    return generate_password_hash(password)


def _verify_password(stored_hash: str, password: str) -> bool:
    """Verify password against stored hash."""
    return check_password_hash(stored_hash, password)


def register_user(username: str, password: str) -> bool:
    """
    Create a new user. Returns True on success, False on failure (e.g., username exists).
    """
    username = (username or "").strip()
    if not username or not password:
        return False

    # prevent duplicate usernames
    if User.query.filter_by(username=username).first():
        return False

    user = User(username=username, password_hash=_hash_password(password))
    try:
        db.session.add(user)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def login_user(username: str, password: str) -> bool:
    """
    Verify login credentials. Returns True if ok, False otherwise.
    """
    if not username or not password:
        return False
    user = User.query.filter_by(username=username).first()
    if not user:
        return False
    return _verify_password(user.password_hash, password)


def get_user(username: str):
    """Return the User object or None."""
    if not username:
        return None
    return User.query.filter_by(username=username).first()


def change_password(username: str, new_password: str) -> bool:
    """Change user's password (returns True if changed)."""
    user = get_user(username)
    if not user or not new_password:
        return False
    user.password_hash = _hash_password(new_password)
    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False

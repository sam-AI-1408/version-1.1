# backend/auth.py
"""
Auth helpers using the shared SQLAlchemy `db` instance.

Functions:
- register_user(username, password) -> bool
- login_user(username, password) -> bool
"""

from backend import db
from sqlalchemy.exc import IntegrityError
# backend/models.py
from .extentions import db
# define User, Task, Quest, etc. using that db
from .models import User

def register_user(username, password):
    """
    Register a new user and create their XP row.
    Returns True on success, False on failure (e.g., username exists or invalid input).
    """
    username = (username or "").strip()
    if not username or not password:
        return False

    # import models lazily to avoid circular imports at module import time
    from .models import User, UserXP

    try:
        # quick duplicate check
        if User.query.filter_by(username=username).first():
            return False

        user = User(username=username)
        user.set_password(password)

        # create the XP row (if your models enforce uniqueness, this will also protect duplicates)
        xp_row = UserXP(username=username, xp=0, level=1)

        db.session.add(user)
        db.session.add(xp_row)
        db.session.commit()
        return True
    except IntegrityError:
        # unique constraint violation (username already exists)
        db.session.rollback()
        return False
    except Exception as e:
        # any other DB error — rollback and return False
        db.session.rollback()
        # Minimal logging to console for debugging during development
        print("register_user error:", repr(e))
        return False


def login_user(username, password):
    """
    Verify username & password. Returns True if valid, False otherwise.
    """
    username = (username or "").strip()
    if not username or not password:
        return False

    from .models import User

    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return False
        return user.check_password(password)
    except Exception as e:
        # on unexpected DB error, don't raise — return False and rollback if needed
        try:
            db.session.rollback()
        except Exception:
            pass
        print("login_user error:", repr(e))
        return False
def get_user(username: str) :
    """Return User instance or None."""
    return User.query.filter_by(username=username).first()
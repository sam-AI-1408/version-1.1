

from .extentions import db

def init_app(app):
    """
    Initialize backend modules and create tables.
    Import modules here (after db.init_app in create_app).
    """
    # db.init_app is called in create_app before this function is called.
    # Import modules now so models bind to the single db instance.
    # These imports should *not* execute expensive side-effects at import time.
    from . import models, auth, task_tracker, academic_tracker, quest_system, leveling  # noqa: F401

    # create DB tables if not present
    with app.app_context():
        db.create_all()

# backend/task_tracker.py
"""
Task tracker utilities for Sam AI (no blueprints).
Defines functions only — no top-level side-effect code (no award_xp calls at import time).
"""

from .extentions import db
from .models import Task, User
from .leveling import add_xp  # add_xp(username, amount) returns awarded amount

def add_task(username: str, title: str, description: str):
    """
    Create a new task and award XP for creating it.
    Returns (task_id, awarded_xp) on success, (None, 0) on failure.
    """
    t = Task(username=username, title=title, description=description)
    try:
        db.session.add(t)
        db.session.commit()
        # Award XP after committing the task
        awarded = add_xp(username, 10)
        return t.id, awarded
    except Exception:
        db.session.rollback()
        return None, 0

def get_tasks(username: str):
    """
    Return a list of Task objects for the user (most recent first).
    """
    return Task.query.filter_by(username=username).order_by(Task.created_at.desc()).all()

def complete_task(task_id: int, username: str):
    """
    Mark a task completed and award XP (if not already completed).
    Returns True/False.
    """
    t = Task.query.get(task_id)
    if not t or t.username != username:
        return False
    if not t.completed:
        t.completed = True
        try:
            db.session.commit()
            add_xp(username, 10)
            return True
        except Exception:
            db.session.rollback()
            return False
    return False

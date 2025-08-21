# backend/quest_system.py
"""
Quest system using SQLAlchemy Quest model and backend.leveling.add_xp.

Functions:
- create_sample_quests(username)
- create_quest(username, title, description="", reward_xp=20)
- start_quest(username, quest_id, duration_minutes)
- complete_quest(username, quest_id) -> True/False
- get_remaining_time(username, quest_id) -> seconds remaining or None
- get_quests(username) -> list of dicts
"""

from datetime import datetime, timezone, timedelta
from backend import db
from backend.leveling import add_xp
from .models import Quest
# backend/models.py
from .extentions import db
# define User, Task, Quest, etc. using that db

def create_sample_quests(username):
    """Create a couple of example quests for a new user (won't duplicate)."""
    username = (username or "").strip()
    if not username:
        return []
    sample = [
        {"title": "Study for 1 hour", "description": "Focus session", "reward_xp": 50},
        {"title": "Complete Python module", "description": "Finish module exercises", "reward_xp": 50},
    ]
    created_ids = []
    try:
        for s in sample:
            # Avoid duplicates by title for same user
            existing = Quest.query.filter_by(username=username, title=s["title"]).first()
            if existing:
                created_ids.append(existing.id)
                continue
            q = Quest(
                username=username,
                title=s["title"],
                description=s.get("description"),
                reward_xp=s.get("reward_xp", 20),
                completed=False,
                created_at=datetime.utcnow()
            )
            db.session.add(q)
            db.session.flush()  # get id
            created_ids.append(q.id)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("create_sample_quests error:", repr(e))
    return created_ids

def create_quest(username, title, description="", reward_xp=20):
    username = (username or "").strip()
    title = (title or "").strip()
    if not username or not title:
        return None
    try:
        q = Quest(
            username=username,
            title=title,
            description=description,
            reward_xp=int(reward_xp),
            completed=False,
            created_at=datetime.utcnow()
        )
        db.session.add(q)
        db.session.commit()
        return q.id
    except Exception as e:
        db.session.rollback()
        print("create_quest error:", repr(e))
        return None

def start_quest(username, quest_id, duration_minutes):
    """
    Start a quest timer by setting start_time and duration_seconds.
    duration_minutes may be float or int.
    Returns True on success, False otherwise.
    """
    try:
        q = Quest.query.get(quest_id)
        if not q or q.username != username:
            return False
        # convert minutes -> seconds
        try:
            seconds = int(float(duration_minutes) * 60)
        except Exception:
            return False
        q.start_time = datetime.utcnow()
        q.duration_seconds = seconds
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print("start_quest error:", repr(e))
        return False

def complete_quest(username, quest_id):
    """
    Mark quest complete if its timer has finished (or it has no duration but not completed).
    Awards reward_xp to the user on success.
    Returns True on success, False otherwise.
    """
    try:
        q = Quest.query.get(quest_id)
        if not q or q.username != username:
            return False
        if q.completed:
            return False

        # If a duration is set, require that enough time has passed
        if q.duration_seconds and q.start_time:
            elapsed = (datetime.utcnow() - q.start_time).total_seconds()
            if elapsed < q.duration_seconds:
                return False

        # mark completed and award XP
        q.completed = True
        db.session.commit()

        try:
            add_xp(username, int(q.reward_xp or 0))
        except Exception as e:
            # XP awarding failure should not rollback the completion — log
            print("Warning: add_xp failed in complete_quest:", repr(e))

        return True
    except Exception as e:
        db.session.rollback()
        print("complete_quest error:", repr(e))
        return False

def get_remaining_time(username, quest_id):
    """
    Return seconds remaining (int) for a quest timer, or None if no timer set.
    If timer expired, returns 0.
    """
    try:
        q = Quest.query.get(quest_id)
        if not q or q.username != username:
            return None
        if not q.start_time or not q.duration_seconds:
            return None
        elapsed = (datetime.utcnow() - q.start_time).total_seconds()
        remaining = int(q.duration_seconds - elapsed)
        return max(0, remaining)
    except Exception as e:
        print("get_remaining_time error:", repr(e))
        return None

def get_quests(username):
    """
    Return list of quests for the user as dicts for templates:
    {
      "id": int,
      "title": str,
      "description": str,
      "reward_xp": int,
      "completed": bool,
      "start_time": ISO string or None,
      "duration_seconds": int or None,
      "remaining_seconds": int or None,
      "created_at": ISO string
    }
    """
    username = (username or "").strip()
    if not username:
        return []
    try:
        rows = Quest.query.filter_by(username=username).order_by(Quest.created_at.desc()).all()
        out = []
        for r in rows:
            remaining = None
            if r.start_time and r.duration_seconds:
                elapsed = (datetime.utcnow() - r.start_time).total_seconds()
                remaining = max(0, int(r.duration_seconds - elapsed))
            out.append({
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "reward_xp": int(r.reward_xp or 0),
                "completed": bool(r.completed),
                "start_time": r.start_time.isoformat() if r.start_time else None,
                "duration_seconds": int(r.duration_seconds) if r.duration_seconds else None,
                "remaining_seconds": remaining,
                "created_at": r.created_at.isoformat() if r.created_at else None
            })
        return out
    except Exception as e:
        print("get_quests error:", repr(e))
        return []

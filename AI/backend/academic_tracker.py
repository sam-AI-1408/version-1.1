# backend/academic_tracker.py
"""
Academic tracker helpers.

Functions:
- start_study_session(username, subject) -> session_id | None
- end_study_session(session_id) -> {"ok": True, "hours": float, "xp_awarded": int} | {"ok": False, "error": str}
- get_study_sessions(username) -> list of (subject, hours, date_iso)
- get_active_session(username) -> session dict or None
"""

from datetime import datetime
from backend import db
from backend.leveling import add_xp
from .models import AcademicLog
# backend/models.py
from .extentions import db
# define User, Task, Quest, etc. using that db

def start_study_session(username, subject):
    username = (username or "").strip()
    subject = (subject or "").strip()
    if not username or not subject:
        return None

    # Prevent multiple active sessions for the same user/subject
    active = AcademicLog.query.filter_by(username=username, end_time=None).first()
    if active:
        # return existing active session id instead of creating a duplicate
        return active.id

    session_rec = AcademicLog(
        username=username,
        subject=subject,
        hours=0.0,
        date=datetime.utcnow(),
        start_time=datetime.utcnow(),
        end_time=None
    )
    try:
        db.session.add(session_rec)
        db.session.commit()
        return session_rec.id
    except Exception as e:
        db.session.rollback()
        print("start_study_session error:", repr(e))
        return None

def end_study_session(session_id):
    if not session_id:
        return {"ok": False, "error": "missing session_id"}

    rec = AcademicLog.query.get(session_id)
    if not rec:
        return {"ok": False, "error": "session not found"}
    if rec.end_time is not None:
        return {"ok": False, "error": "session already ended"}
    if rec.start_time is None:
        return {"ok": False, "error": "session has no start_time"}

    try:
        rec.end_time = datetime.utcnow()
        duration_hours = (rec.end_time - rec.start_time).total_seconds() / 3600.0
        rec.hours = round(duration_hours, 2)

        xp_to_award = max(0, int(duration_hours * 5))  # 5 XP per hour

        if xp_to_award > 0:
            try:
                add_xp(rec.username, xp_to_award)
            except Exception as e:
                # don't abort the session if XP awarding fails; log for dev
                print("Warning: add_xp failed in end_study_session:", repr(e))

        db.session.commit()
        return {"ok": True, "hours": rec.hours, "xp_awarded": xp_to_award}
    except Exception as e:
        db.session.rollback()
        print("end_study_session error:", repr(e))
        return {"ok": False, "error": str(e)}

def get_study_sessions(username):
    username = (username or "").strip()
    if not username:
        return []

    try:
        rows = AcademicLog.query.filter_by(username=username).order_by(AcademicLog.date.desc()).all()
        result = []
        for r in rows:
            date_iso = r.date.isoformat() if hasattr(r.date, "isoformat") else str(r.date)
            result.append((r.subject, float(r.hours), date_iso))
        return result
    except Exception as e:
        print("get_study_sessions error:", repr(e))
        return []

def get_active_session(username):
    """
    Return the active (not yet ended) session for the user as a dict:
    {"id": id, "subject": subject, "start_time": iso} or None.
    """
    username = (username or "").strip()
    if not username:
        return None
    try:
        rec = AcademicLog.query.filter_by(username=username, end_time=None).first()
        if not rec:
            return None
        return {
            "id": rec.id,
            "subject": rec.subject,
            "start_time": rec.start_time.isoformat() if rec.start_time else None
        }
    except Exception as e:
        print("get_active_session error:", repr(e))
        return None

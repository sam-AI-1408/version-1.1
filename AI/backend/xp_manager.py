# xp_manager.py
from datetime import date
from backend import db
from backend.models import User

DAILY_XP_MAX = 100

def reset_daily_if_needed(user: User):
    """Reset user's daily_xp if last_daily_reset is not today."""
    today = date.today()
    if user.last_daily_reset != today:
        user.daily_xp = 0
        user.last_daily_reset = today

def award_xp(user: User, amount: int):
    """
    Award XP to user enforcing daily cap.
    Returns the actual awarded amount.
    """
    if user is None:
        raise ValueError("No user provided to award_xp")

    reset_daily_if_needed(user)
    current_daily = user.daily_xp or 0
    remaining = DAILY_XP_MAX - current_daily
    if remaining <= 0:
        awarded = 0
    else:
        awarded = min(amount, remaining)
        user.daily_xp = current_daily + awarded
        user.xp = (user.xp or 0) + awarded

    db.session.commit()
    return awarded

# backend/leveling.py
"""
Leveling / player stats helpers using the shared `db` instance from backend.
Provides:
- PlayerStats model (player-specific XP, level, and stats)
- get_player, get_xp, get_level, add_xp, reset_player
"""

from datetime import datetime
from backend import db
# backend/models.py
from .extentions import db
# define User, Task, Quest, etc. using that db

# ------------------------
# Database Model
# ------------------------
class PlayerStats(db.Model):
    __tablename__ = "player_stats"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=0)
    strength = db.Column(db.Integer, default=1)
    memory = db.Column(db.Integer, default=1)
    stamina = db.Column(db.Integer, default=1)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PlayerStats {self.username} xp={self.xp} lvl={self.level}>"

# ------------------------
# Internal Helpers
# ------------------------
def _ensure_player(username):
    """
    Return the PlayerStats row for username, creating it if necessary.
    """
    username = (username or "").strip()
    if not username:
        return None

    player = PlayerStats.query.filter_by(username=username).first()
    if not player:
        player = PlayerStats(username=username, xp=0, level=0, strength=1, memory=1, stamina=1)
        try:
            db.session.add(player)
            db.session.commit()
        except Exception:
            db.session.rollback()
            # Re-query to avoid race conditions where another thread created it
            player = PlayerStats.query.filter_by(username=username).first()
    return player

# ------------------------
# Public Functions
# ------------------------
def get_player(username):
    """Return PlayerStats or None if username invalid."""
    return _ensure_player(username)

def get_xp(username):
    p = _ensure_player(username)
    return p.xp if p else 0

def get_level(username):
    p = _ensure_player(username)
    return p.level if p else 0

def _xp_needed_for_next_level(level):
    """
    XP curve: (level + 1) * 100 XP required to reach next level.
    Example: level 0 -> need 100 for level 1, level 1 -> need 200 for level 2, etc.
    Adjust this function to tweak progression speed.
    """
    return (level + 1) * 100

def add_xp(username, xp_to_add):
    """
    Add XP to user, handle level-ups and stat increases.
    Returns a dict: {"ok": True, "xp": new_xp, "level": new_level, "levels_gained": n}
    """
    if not username or xp_to_add is None:
        return {"ok": False, "error": "invalid input"}

    try:
        player = _ensure_player(username)
        if player is None:
            return {"ok": False, "error": "could not create player record"}

        # Ensure xp_to_add is int
        try:
            xp_to_add = int(xp_to_add)
        except Exception:
            xp_to_add = 0

        if xp_to_add == 0:
            return {"ok": True, "xp": player.xp, "level": player.level, "levels_gained": 0}

        player.xp = int(player.xp) + xp_to_add

        levels_gained = 0
        # Level up loop (handles multiple level-ups in one add)
        while player.xp >= _xp_needed_for_next_level(player.level):
            # consume the XP required for next level
            required = _xp_needed_for_next_level(player.level)
            # It's simpler to increment level and not subtract XP (we keep total XP tracking),
            # but if you want to subtract required XP, change logic here.
            player.level += 1
            levels_gained += 1
            _increase_stats(player)

        player.updated_at = datetime.utcnow()
        db.session.commit()
        return {"ok": True, "xp": player.xp, "level": player.level, "levels_gained": levels_gained}
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        return {"ok": False, "error": str(e)}

def _increase_stats(player):
    """
    Increase player stats when leveling up. Customize distribution here.
    """
    player.strength = (player.strength or 0) + 1
    player.memory = (player.memory or 0) + 1
    player.stamina = (player.stamina or 0) + 1

def reset_player(username):
    """
    Reset a player's stats and XP to starting values.
    """
    player = _ensure_player(username)
    if not player:
        return False
    player.xp = 0
    player.level = 0
    player.strength = 1
    player.memory = 1
    player.stamina = 1
    player.updated_at = datetime.utcnow()
    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False

# backend/models.py
from . import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
from backend import db  #


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<User {self.username}>"


class UserXP(db.Model):
    __tablename__ = "user_xp"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(
        db.String(100),
        db.ForeignKey("users.username", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    xp = db.Column(db.Integer, default=0, nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserXP {self.username} xp={self.xp} lvl={self.level}>"


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(
        db.String(100),
        db.ForeignKey("users.username", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_done = db.Column(db.Boolean, default=False, nullable=False)
    xp = db.Column(db.Integer, default=10, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Task {self.id} {self.title} by {self.username}>"


class AcademicLog(db.Model):
    __tablename__ = "academic_logs"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(
        db.String(100),
        db.ForeignKey("users.username", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject = db.Column(db.String(100), nullable=False)
    hours = db.Column(db.Float, default=0.0, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)

    def __repr__(self):
        return f"<AcademicLog {self.username} {self.subject} {self.hours}h>"


class Quest(db.Model):
    __tablename__ = "quests"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(
        db.String(100),
        db.ForeignKey("users.username", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    reward_xp = db.Column(db.Integer, default=20, nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Optional timer fields (start_time is when quest timer started,
    # duration_seconds is total required duration in seconds)
    start_time = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f"<Quest {self.id} {self.title} by {self.username} completed={self.completed}>"

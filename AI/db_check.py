# db_check.py
from sqlalchemy import inspect
from backend.extentions import db
from main_app import create_app

app = create_app()
with app.app_context():
    print("Engine URL:", db.engine.url)
    insp = inspect(db.engine)
    print("tasks columns:", [c['name'] for c in insp.get_columns('tasks')])

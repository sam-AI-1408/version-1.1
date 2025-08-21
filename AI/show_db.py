# show_db.py
import os, importlib
# adjust if your create_app is in a different module
from main_app import create_app

app = create_app()
print("FLASK APP created.")
print("SQLALCHEMY_DATABASE_URI:", app.config.get("SQLALCHEMY_DATABASE_URI"))
print("instance_path:", getattr(app, "instance_path", None))
# Also print the DB file path we set earlier
try:
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    print("DB URI:", uri)
    if uri.startswith("sqlite:///"):
        print("Resolved DB path:", uri.replace("sqlite:///", ""))
except Exception as e:
    print("Couldn't read DB URI:", e)

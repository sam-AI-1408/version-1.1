# seed_user_app.py
from main_app import create_app

app = create_app()

with app.app_context():
    import backend.auth as auth
    username = "testuser"
    password = "testpass123"
    ok = auth.register_user(username, password)
    print("register_user returned:", ok)
    u = auth.get_user(username)
    print("get_user returned:", u)
    # print the stored password_hash (first 60 chars to avoid console spam)
    if u:
        print("stored password_hash:", getattr(u, "password_hash", None)[:120])
    else:
        print("User not found after register.")

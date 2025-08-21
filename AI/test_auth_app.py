# test_auth_app.py
from main_app import create_app

app = create_app()

with app.app_context():
    import backend.auth as auth
    username = "testuser"
    plain = "testpass123"

    u = auth.get_user(username)
    print("get_user:", u)
    if u:
        print("stored password_hash (preview):", getattr(u, "password_hash", None)[:120])

    ok = auth.login_user(username, plain)
    print("login_user returned:", ok)

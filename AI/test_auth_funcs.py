# test_auth_funcs.py
from importlib import import_module
print("Importing backend.auth ...")
try:
    auth = import_module("backend.auth")
    print("backend.auth imported from:", auth.__file__)
    print("exports:", [n for n in dir(auth) if not n.startswith("_")])
except Exception as e:
    print("Import failed:", e)
    raise

# Try calling functions if present
username = "debug_test_user"
password = "password123"
print("\nFunctions found:")
if hasattr(auth, "get_user"):
    print("get_user exists")
if hasattr(auth, "register_user"):
    print("register_user exists. Trying to register (may fail if user exists)...")
    ok = auth.register_user(username, password)
    print("register_user returned:", ok)
if hasattr(auth, "login_user"):
    print("login_user exists. Trying to login with test creds...")
    ok2 = auth.login_user(username, password)
    print("login_user returned:", ok2)
else:
    print("login_user not found; implement it.")

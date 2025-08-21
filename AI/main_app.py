# main_app.py (REWRITE)
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, current_app

# backend single DB handle and initializer
from backend import db, init_app as backend_init_app

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_DIR = os.path.join(BASE_DIR, "backend", "data")
DB_PATH = os.path.join(DB_DIR, "sam_ai.db")
os.makedirs(DB_DIR, exist_ok=True)


def create_app():
    app = Flask(__name__, instance_relative_config=False)

    # Secret: prefer environment variable; fallback for dev
    app.secret_key = os.environ.get("SAM_AI_SECRET", "hameed_change_this_for_prod")

    # Use absolute SQLite path (three slashes + absolute path)
    abs_db_path = DB_PATH.replace("\\", "/")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{abs_db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize DB with app
    db.init_app(app)

    # Let backend package perform its initialization inside app context (models import / create_all)
    with app.app_context():
        try:
            backend_init_app(app)
        except Exception as e:
            # Bubble error with informative message
            print("[ERROR] backend.init_app failed:", e)
            raise

    # ---------------- Routes ----------------

    @app.route("/")
    def home():
        # Show login by default if exists
        print("[DEBUG] Home accessed. Registered endpoints:", sorted(app.view_functions.keys()))
        if "login" in app.view_functions:
            return redirect(url_for("login"))
        return "Login endpoint not found. Available endpoints: " + ", ".join(sorted(app.view_functions.keys()))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            from backend import auth
            try:
                success = auth.register_user(username, password)
            except Exception as e:
                current_app.logger.exception("auth.register_user failed")
                success = False

            if success:
                flash("Registered successfully. Please login.", "success")
                return redirect(url_for("login"))
            return render_template("register.html", error="Username exists or invalid input")
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            raw_username = request.form.get("username")
            raw_password = request.form.get("password")
            username = (raw_username or "").strip()
            password = raw_password or ""

            from backend import auth as _auth_mod
            auth = _auth_mod

            # Helpful debug prints for dev (remove in prod)
            print("DEBUG(web): /login POST received", {"username": username, "has_password": bool(password)})
            try:
                user_obj = auth.get_user(username)
                print("DEBUG(web): auth.get_user returned:", user_obj)
            except Exception as e:
                print("DEBUG(web): auth.get_user raised:", type(e).__name__, e)

            try:
                ok = auth.login_user(username, password)
            except Exception as e:
                print("DEBUG(web): auth.login_user raised:", type(e).__name__, e)
                ok = False

            print(f"DEBUG(web): auth.login_user returned: {ok}")

            if ok:
                session["username"] = username
                session.permanent = True
                return redirect(url_for("dashboard"))

            return render_template("login.html", error="Invalid credentials (check console for debug)")

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.pop("username", None)
        return redirect(url_for("login"))

    @app.route("/dashboard")
    def dashboard():
        username = session.get("username")
        if not username:
            return redirect(url_for("login"))

        # Lazy imports
        try:
            import backend.auth as auth
            from backend import task_tracker, academic_tracker, quest_system, leveling
        except Exception as e:
            current_app.logger.exception("Failed importing backend modules for dashboard")
            raise

        user = auth.get_user(username)
        if not user:
            session.pop("username", None)
            return redirect(url_for("login"))

        # fetch raw backend data (may be model objects or dicts)
        try:
            raw_tasks = task_tracker.get_tasks(username) if hasattr(task_tracker, "get_tasks") else []
            level = leveling.get_level(username) if hasattr(leveling, "get_level") else 1
            xp = leveling.get_xp(username) if hasattr(leveling, "get_xp") else 0
            quests = quest_system.get_quests(username) if hasattr(quest_system, "get_quests") else []
            raw_study_sessions = academic_tracker.get_study_sessions(username) if hasattr(academic_tracker, "get_study_sessions") else []
        except Exception:
            current_app.logger.exception("Server error fetching dashboard data")
            return "Server error fetching dashboard data", 500

        # ---------------- Normalise tasks -> list[dict] ----------------
        tasks_list = []
        try:
            for t in raw_tasks or []:
                if isinstance(t, dict):
                    tasks_list.append({
                        "id": t.get("id"),
                        "title": t.get("title", ""),
                        "description": t.get("description", ""),
                        "is_done": bool(t.get("is_done", False)),
                        "xp": int(t.get("xp", 10)),
                    })
                else:
                    tasks_list.append({
                        "id": getattr(t, "id", None),
                        "title": getattr(t, "title", "") or "",
                        "description": getattr(t, "description", "") or "",
                        "is_done": bool(getattr(t, "is_done", False)),
                        "xp": int(getattr(t, "xp", 10) or 10),
                    })
        except Exception:
            current_app.logger.exception("Failed normalizing tasks")
            tasks_list = []

        # ---------------- Normalise study sessions -> list[dict] ----------------
        sessions_list = []
        try:
            for s in raw_study_sessions or []:
                if isinstance(s, dict):
                    sessions_list.append({
                        "id": s.get("id"),
                        "subject": s.get("subject", ""),
                        "hours": float(s.get("hours") or 0),
                        "date": s.get("date"),
                    })
                else:
                    d = getattr(s, "date", None)
                    sessions_list.append({
                        "id": getattr(s, "id", None),
                        "subject": getattr(s, "subject", "") or "",
                        "hours": float(getattr(s, "hours", 0) or 0),
                        "date": d.isoformat() if d is not None else None,
                    })
        except Exception:
            current_app.logger.exception("Failed normalizing study sessions")
            sessions_list = []

        # ---------------- Optional: Aggregate academic hours by subject if you still need that ----------------
        academics_by_subject = {}
        try:
            for rec in sessions_list:
                subj = rec.get("subject")
                hrs = float(rec.get("hours", 0) or 0)
                if subj:
                    academics_by_subject[subj] = academics_by_subject.get(subj, 0) + hrs
        except Exception:
            academics_by_subject = {}

        # ---------------- Build single initial-state object for client ----------------
        state = {
            "user": {"username": username},
            "stats": {"xp": int(xp or 0), "level": int(level or 1)},
            "tasks": tasks_list,
            "academics": sessions_list,
        }

        # Render template with normalized serializable structures (and the convenience 'state')
        return render_template(
            "dashboard.html",
            username=username,
            user=user,
            tasks=tasks_list,             # normalized for template
            level=level,
            xp=xp,
            quests=quests,
            academics=sessions_list,      # normalized sessions list
            academics_by_subject=academics_by_subject,
            state=state                   # single object to inject with |tojson
        )

    # ------------ API: state ------------
    @app.route("/api/state")
    def api_state():
        if "username" not in session:
            return jsonify({"ok": False, "error": "unauthenticated"}), 401
        username = session["username"]

        try:
            import backend.auth as auth
            from backend import task_tracker, leveling, quest_system, academic_tracker
        except Exception as e:
            current_app.logger.exception("api_state import fail")
            return jsonify({"ok": False, "error": f"import_error: {e}"}), 500

        user = auth.get_user(username)
        if not user:
            session.pop("username", None)
            return jsonify({"ok": False, "error": "user_not_found"}), 401

        tasks = []
        xp = 0
        level = 1
        try:
            if hasattr(task_tracker, "get_tasks"):
                raw = task_tracker.get_tasks(username) or []
                for t in raw:
                    if isinstance(t, dict):
                        tasks.append({
                            "id": t.get("id"),
                            "title": t.get("title"),
                            "description": t.get("description"),
                            "is_done": bool(t.get("is_done")),
                            "xp": int(t.get("xp", 10)),
                        })
                    else:
                        tasks.append({
                            "id": getattr(t, "id", None),
                            "title": getattr(t, "title", ""),
                            "description": getattr(t, "description", ""),
                            "is_done": bool(getattr(t, "is_done", False)),
                            "xp": int(getattr(t, "xp", 10)),
                        })
            if hasattr(leveling, "get_xp"):
                xp = int(leveling.get_xp(username) or 0)
            if hasattr(leveling, "get_level"):
                level = int(leveling.get_level(username) or 1)
        except Exception:
            current_app.logger.exception("api_state fetch error")
            return jsonify({"ok": False, "error": "fetch_error"}), 500

        return jsonify({
            "ok": True,
            "user": {"username": username},
            "stats": {"xp": xp, "level": level},
            "tasks": tasks
        })

    # alias to refresh
    @app.route("/api/state/refresh")
    def api_state_refresh():
        return api_state()

    # ------------ API: tasks ------------
    @app.route("/api/tasks", methods=["GET", "POST"])
    def api_tasks():
        if "username" not in session:
            return jsonify({"ok": False, "error": "unauthenticated"}), 401
        username = session["username"]

        from backend import task_tracker, leveling, db as _db
        from backend.models import Task

        if request.method == "GET":
            raw = task_tracker.get_tasks(username) if hasattr(task_tracker, "get_tasks") else []
            tasks = []
            for t in raw:
                if isinstance(t, dict):
                    tasks.append({
                        "id": t.get("id"),
                        "title": t.get("title", ""),
                        "description": t.get("description", ""),
                        "is_done": bool(t.get("is_done")),
                        "xp": int(t.get("xp", 10)),
                    })
                else:
                    tasks.append({
                        "id": getattr(t, "id", None),
                        "title": getattr(t, "title", ""),
                        "description": getattr(t, "description", ""),
                        "is_done": bool(getattr(t, "is_done", False)),
                        "xp": int(getattr(t, "xp", 10)),
                    })
            return jsonify({"ok": True, "tasks": tasks})

        # POST = add task
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        if not title:
            return jsonify({"ok": False, "error": "title_required"}), 400

        try:
            if hasattr(task_tracker, "add_task"):
                # If task_tracker.add_task returns awarded xp or task object, handle gracefully
                res = task_tracker.add_task(username, title, description)
                # if module returns xp or task, don't assume anything; return success
                awarded = None
                if isinstance(res, (int, float)):
                    awarded = int(res)
                # after adding, fetch authoritative total xp if possible
                total_xp = None
                if hasattr(leveling, "get_xp"):
                    try:
                        total_xp = int(leveling.get_xp(username) or 0)
                    except Exception:
                        total_xp = None
                resp = {"ok": True}
                if awarded is not None:
                    resp["awarded_xp"] = awarded
                if total_xp is not None:
                    resp["total_xp"] = total_xp
                return jsonify(resp)
            else:
                t = Task(username=username, title=title, description=description, is_done=False, xp=10)
                _db.session.add(t)
                _db.session.commit()
                # return totals
                total_xp = None
                from backend import leveling as _lev
                if hasattr(_lev, "get_xp"):
                    try:
                        total_xp = int(_lev.get_xp(username) or 0)
                    except Exception:
                        total_xp = None
                resp = {"ok": True}
                if total_xp is not None:
                    resp["total_xp"] = total_xp
                return jsonify(resp)
        except Exception:
            current_app.logger.exception("api_tasks POST failed")
            return jsonify({"ok": False, "error": "server_error"}), 500

    @app.route("/api/tasks/<int:task_id>/complete", methods=["POST"])
    def api_complete_task(task_id):
        if "username" not in session:
            return jsonify({"ok": False, "error": "unauthenticated"}), 401
        username = session["username"]

        from backend import db as _db, leveling
        from backend.models import Task

        task = Task.query.get(task_id)
        if not task or task.username != username:
            return jsonify({"ok": False, "error": "not_found_or_forbidden"}), 404

        awarded = 0
        try:
            if not getattr(task, "is_done", False):
                task.is_done = True
                _db.session.add(task)
                _db.session.commit()
                awarded = int(getattr(task, "xp", 10))
                if hasattr(leveling, "add_xp"):
                    try:
                        leveling.add_xp(username, awarded)
                    except Exception:
                        current_app.logger.exception("leveling.add_xp failed on task complete")
            else:
                awarded = 0
        except Exception:
            _db.session.rollback()
            current_app.logger.exception("api_complete_task DB failure")
            return jsonify({"ok": False, "error": "db_error"}), 500

        total_xp = 0
        if hasattr(leveling, "get_xp"):
            try:
                total_xp = int(leveling.get_xp(username) or 0)
            except Exception:
                total_xp = 0

        return jsonify({"ok": True, "awarded_xp": awarded, "total_xp": total_xp})

    # ------------ API: academic ------------
    # single implementation used by both HTML form route (below) and API route
    def _process_academic_log(username, subject, hours):
        from backend import leveling, db as _db
        from backend.models import AcademicLog

        try:
            hours = float(hours)
        except Exception:
            hours = 0.0
        if not subject or hours <= 0:
            raise ValueError("invalid_input")

        rec = AcademicLog(username=username, subject=subject, hours=hours, date=datetime.utcnow())
        _db.session.add(rec)

        awarded = int(hours * 5)
        if hasattr(leveling, "add_xp"):
            try:
                leveling.add_xp(username, awarded)
            except Exception:
                current_app.logger.exception("leveling.add_xp failed")

        try:
            _db.session.commit()
        except Exception:
            _db.session.rollback()
            raise

        total_xp = None
        if hasattr(leveling, "get_xp"):
            try:
                total_xp = int(leveling.get_xp(username) or 0)
            except Exception:
                total_xp = None

        return awarded, total_xp

    @app.route("/add_academic", methods=["POST"])
    def add_academic():
        # HTML form endpoint (keeps old behaviour)
        if "username" not in session:
            return redirect(url_for("login"))
        username = session["username"]
        subject = request.form.get("subject", "").strip()
        hours = request.form.get("hours", 0)
        try:
            awarded, total_xp = _process_academic_log(username, subject, hours)
        except ValueError:
            flash("Provide subject and hours.", "error")
            return redirect(url_for("dashboard"))
        except Exception:
            current_app.logger.exception("add_academic failed")
            flash("Server error logging study session.", "error")
            return redirect(url_for("dashboard"))

        flash(f"Logged {hours}h of {subject}. +{awarded} XP", "success")
        return redirect(url_for("dashboard"))

    @app.route("/api/academic", methods=["GET", "POST"])
    def api_academic():
        if "username" not in session:
            return jsonify({"ok": False, "error": "unauthenticated"}), 401
        username = session["username"]

        from backend.models import AcademicLog

        if request.method == "GET":
            try:
                rows = AcademicLog.query.filter_by(username=username).order_by(AcademicLog.date.desc()).limit(50).all()
                out = []
                for r in rows:
                    out.append({
                        "id": getattr(r, "id", None),
                        "subject": getattr(r, "subject", ""),
                        "hours": float(getattr(r, "hours", 0)),
                        "date": getattr(r, "date", None).isoformat() if getattr(r, "date", None) else None
                    })
                # return totals too
                total_xp = None
                from backend import leveling as _lev
                if hasattr(_lev, "get_xp"):
                    try:
                        total_xp = int(_lev.get_xp(username) or 0)
                    except Exception:
                        total_xp = None
                return jsonify({"ok": True, "sessions": out, "total_xp": total_xp})
            except Exception:
                current_app.logger.exception("api_academic GET failed")
                return jsonify({"ok": False, "error": "server_error"}), 500

        # POST
        data = request.get_json(silent=True) or {}
        subject = (data.get("subject") or "").strip()
        try:
            hours = float(data.get("hours") or 0)
        except Exception:
            hours = 0.0

        if not subject or hours <= 0:
            return jsonify({"ok": False, "error": "invalid_input"}), 400

        try:
            awarded, total = _process_academic_log(username, subject, hours)
            return jsonify({"ok": True, "awarded_xp": awarded, "total_xp": total})
        except ValueError:
            return jsonify({"ok": False, "error": "invalid_input"}), 400
        except Exception:
            current_app.logger.exception("api_academic POST failed")
            return jsonify({"ok": False, "error": "server_error"}), 500

    # ------------ Optional: simple quests API (example) ------------
    @app.route("/api/complete_quest", methods=["POST"])
    def api_complete_quest():
        if "username" not in session:
            return jsonify({"ok": False, "error": "unauthenticated"}), 401
        username = session["username"]
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"ok": False, "error": "missing_title"}), 400

        # Attempt to delegate to backend.quest_system if available
        try:
            from backend import quest_system, leveling
            res = None
            if hasattr(quest_system, "complete_quest"):
                res = quest_system.complete_quest(username, title)
            awarded = 0
            if isinstance(res, (int, float)):
                awarded = int(res)
            else:
                # fallback award
                awarded = 10
                if hasattr(leveling, "add_xp"):
                    try:
                        leveling.add_xp(username, awarded)
                    except Exception:
                        current_app.logger.exception("leveling.add_xp failed for quest")
            total_xp = None
            if hasattr(leveling, "get_xp"):
                try:
                    total_xp = int(leveling.get_xp(username) or 0)
                except Exception:
                    total_xp = None
            resp = {"ok": True, "awarded_xp": awarded}
            if total_xp is not None:
                resp["total_xp"] = total_xp
            return jsonify(resp)
        except Exception:
            current_app.logger.exception("api_complete_quest failed")
            return jsonify({"ok": False, "error": "server_error"}), 500

    # ------------ debug helpers ------------
    @app.route("/_debug_session")
    def _debug_session():
        return jsonify({k: session.get(k) for k in session.keys()})

    @app.route("/_debug_auto_login")
    def _debug_auto_login():
        session["username"] = "testuser"
        session.permanent = True
        return redirect(url_for("dashboard"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="127.0.0.1", port=5000)

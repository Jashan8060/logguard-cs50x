"""
LogGuard - CS50x Final Project
A Precision FMCSA Hours of Service (HOS) Driver Log Validator & Visualizer.

Built with Python, FastAPI, Uvicorn, SQLite, and Vanilla Modern CSS/JavaScript.
Inspired by commercial fleet safety monitoring platforms.
"""

from fastapi import FastAPI, Request, Form, File, UploadFile, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from werkzeug.security import generate_password_hash, check_password_hash
from contextlib import asynccontextmanager
from functools import wraps
import jinja2
import csv
import io
import os
from datetime import datetime, timedelta

from database import get_db, init_db, seed_demo_data
from compliance import HOSRuleEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure SQLite Database is initialized and seeded on startup
    db_file = os.path.join(os.path.dirname(__file__), "logguard.db")
    if not os.path.exists(db_file):
        init_db()
        seed_demo_data()
    yield


app = FastAPI(title="LogGuard", version="1.0", lifespan=lifespan)

# Session Middleware for signed session cookies
SECRET_KEY = os.environ.get("SECRET_KEY", "cs50x-logguard-super-secret-key-2026")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Mount Static Files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup Jinja2 Templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))



# --- Format Filters & Helpers for Jinja2 Templates ---
def format_duration(seconds):
    if seconds is None:
        return "0h 00m"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes:02d}m"


def status_badge(status):
    mapping = {
        'COMPLIANT': 'badge-success',
        'WARNING': 'badge-warning',
        'VIOLATION': 'badge-danger'
    }
    return mapping.get(status, 'badge-secondary')


templates.env.filters["format_duration"] = format_duration
templates.env.filters["status_badge"] = status_badge


# Flash message helpers for Starlette session
def flash(request: Request, message: str, category: str = "info"):
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append((category, message))


@jinja2.pass_context
def get_flashed_messages(context, with_categories: bool = True):
    req: Request = context.get("request")
    if not req or "_messages" not in req.session:
        return []
    messages = req.session.pop("_messages", [])
    if with_categories:
        return messages
    return [m[1] for m in messages]


templates.env.globals["get_flashed_messages"] = get_flashed_messages


@jinja2.pass_context
def custom_url_for(context, name: str, **path_params):
    if name == "static":
        filename = path_params.get("filename") or path_params.get("path")
        return f"/static/{filename}"
    route_map = {
        "index": "/",
        "login": "/login",
        "register": "/register",
        "logout": "/logout",
        "dashboard": "/dashboard",
        "new_log": "/logs/new",
        "upload_csv_log": "/logs/upload",
        "manage_drivers": "/drivers",
        "audit": "/audit"
    }
    if name in route_map:
        return route_map[name]
    if name == "view_log" and "log_id" in path_params:
        return f"/logs/{path_params['log_id']}"
    req: Request = context.get("request")
    if req:
        try:
            return req.url_for(name, **path_params)
        except Exception:
            pass
    return f"/{name}"


templates.env.globals["url_for"] = custom_url_for

# Monkey-patch Request helpers so templates can highlight active nav tab & access query params
Request.endpoint = property(
    lambda self: getattr(self.scope.get("endpoint"), "__name__", "") or (self.scope.get("route").name if self.scope.get("route") else "")
)
Request.args = property(lambda self: self.query_params)


def render(request: Request, name: str, context: dict = None):
    ctx = {
        "request": request,
        "session": request.session,
        **(context or {})
    }
    return templates.TemplateResponse(request=request, name=name, context=ctx)


def is_authenticated(request: Request) -> bool:
    return "user_id" in request.session


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return render(request, "login.html")


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return render(request, "login.html")


@app.post("/login")
async def login_post(request: Request):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    db.close()

    if user and check_password_hash(user["password_hash"], password):
        request.session.clear()
        request.session["user_id"] = user["id"]
        request.session["username"] = user["username"]
        request.session["full_name"] = user["full_name"]
        request.session["role"] = user["role"]
        flash(request, f"Welcome back, {user['full_name']}!", "success")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    flash(request, "Invalid username or password. (Demo: demo / cs50x2026!)", "danger")
    return render(request, "login.html")


@app.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    return render(request, "register.html")


@app.post("/register")
async def register_post(request: Request):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    full_name = str(form.get("full_name", "")).strip()
    password = str(form.get("password", ""))
    confirm = str(form.get("confirm_password", ""))

    if not username or not full_name or not password:
        flash(request, "All fields are required.", "danger")
        return render(request, "register.html")

    if password != confirm:
        flash(request, "Passwords do not match.", "danger")
        return render(request, "register.html")

    db = get_db()
    try:
        hashed_pw = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            (username, hashed_pw, full_name, "Safety Officer")
        )
        db.commit()
        db.close()
        flash(request, "Account registered successfully! Please log in.", "success")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    except Exception:
        db.close()
        flash(request, "Username already exists. Please choose another.", "danger")
        return render(request, "register.html")


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    flash(request, "You have been signed out.", "info")
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)



@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_authenticated(request):
        flash(request, "Please log in to access this page.", "warning")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    user_id = request.session["user_id"]
    db = get_db()

    drivers = db.execute("SELECT * FROM drivers WHERE user_id = ? ORDER BY name ASC", (user_id,)).fetchall()

    logs = db.execute(
        """SELECT l.*, d.name as driver_name, d.license_number
           FROM daily_logs l
           JOIN drivers d ON l.driver_id = d.id
           WHERE d.user_id = ?
           ORDER BY l.log_date DESC, l.id DESC LIMIT 15""",
        (user_id,)
    ).fetchall()

    violations = db.execute(
        """SELECT v.*, d.name as driver_name, l.log_date
           FROM violations v
           JOIN daily_logs l ON v.daily_log_id = l.id
           JOIN drivers d ON l.driver_id = d.id
           WHERE d.user_id = ?
           ORDER BY v.id DESC LIMIT 10""",
        (user_id,)
    ).fetchall()

    total_logs = len(logs)
    violation_logs = sum(1 for log in logs if log["status"] == "VIOLATION")
    compliant_logs = sum(1 for log in logs if log["status"] == "COMPLIANT")
    total_violations = len(violations)
    db.close()

    return render(
        request,
        "dashboard.html",
        {
            "drivers": drivers,
            "logs": logs,
            "violations": violations,
            "total_logs": total_logs,
            "compliant_logs": compliant_logs,
            "violation_logs": violation_logs,
            "total_violations": total_violations
        }
    )


@app.get("/drivers", response_class=HTMLResponse)
async def drivers_get(request: Request):
    if not is_authenticated(request):
        flash(request, "Please log in to access this page.", "warning")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    user_id = request.session["user_id"]
    db = get_db()
    drivers = db.execute(
        """SELECT d.*, COUNT(l.id) as log_count,
                  SUM(CASE WHEN l.status = 'VIOLATION' THEN 1 ELSE 0 END) as violation_count
           FROM drivers d
           LEFT JOIN daily_logs l ON d.id = l.driver_id
           WHERE d.user_id = ?
           GROUP BY d.id
           ORDER BY d.name ASC""",
        (user_id,)
    ).fetchall()
    db.close()

    return render(request, "drivers.html", {"drivers": drivers})


@app.post("/drivers")
async def drivers_post(request: Request):
    if not is_authenticated(request):
        flash(request, "Please log in to access this page.", "warning")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    user_id = request.session["user_id"]
    form = await request.form()
    name = str(form.get("name", "")).strip()
    license_num = str(form.get("license_number", "")).strip()
    city = str(form.get("terminal_city", "Dallas, TX")).strip()

    if name and license_num:
        db = get_db()
        db.execute(
            "INSERT INTO drivers (user_id, name, license_number, terminal_city) VALUES (?, ?, ?, ?)",
            (user_id, name, license_num, city)
        )
        db.commit()
        db.close()
        flash(request, f"Driver {name} registered successfully.", "success")
        return RedirectResponse(url="/drivers", status_code=status.HTTP_302_FOUND)

    flash(request, "Name and CDL Number are required.", "danger")
    return RedirectResponse(url="/drivers", status_code=status.HTTP_302_FOUND)



@app.get("/logs/new", response_class=HTMLResponse)
async def new_log_get(request: Request):
    if not is_authenticated(request):
        flash(request, "Please log in to access this page.", "warning")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    user_id = request.session["user_id"]
    db = get_db()
    drivers = db.execute("SELECT * FROM drivers WHERE user_id = ? ORDER BY name ASC", (user_id,)).fetchall()
    db.close()
    return render(request, "log_entry.html", {"drivers": drivers, "now_date": datetime.now().strftime("%Y-%m-%d")})


@app.post("/logs/new")
async def new_log_post(request: Request):
    if not is_authenticated(request):
        flash(request, "Please log in to access this page.", "warning")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    user_id = request.session["user_id"]
    db = get_db()
    drivers = db.execute("SELECT * FROM drivers WHERE user_id = ? ORDER BY name ASC", (user_id,)).fetchall()

    form = await request.form()
    driver_id = form.get("driver_id")
    log_date = form.get("log_date")
    notes = form.get("notes", "")

    statuses = form.getlist("duty_status[]")
    starts = form.getlist("start_time[]")
    ends = form.getlist("end_time[]")
    locations = form.getlist("location[]")
    odometers = form.getlist("odometer[]")

    if not driver_id or not log_date or not statuses:
        flash(request, "Driver, date, and at least one status interval are required.", "danger")
        db.close()
        return render(request, "log_entry.html", {"drivers": drivers})

    events = []
    for i in range(len(statuses)):
        st_str = f"{log_date} {starts[i]}:00"
        et_str = f"{log_date} {ends[i]}:00"
        if ends[i] == "24:00" or ends[i] == "23:59":
            et_str = f"{log_date} 23:59:59"

        events.append({
            "duty_status": statuses[i],
            "start_time": st_str,
            "end_time": et_str,
            "location": locations[i] if i < len(locations) else "Terminal",
            "odometer": float(odometers[i]) if i < len(odometers) and odometers[i] else 0.0
        })

    # Run Rule Engine
    engine = HOSRuleEngine()
    result = engine.evaluate_events(events)

    status_flag = "COMPLIANT" if result["compliant"] else "VIOLATION"
    v_count = len(result["violations"])

    # Insert Daily Log
    cursor = db.cursor()
    cursor.execute(
        """INSERT INTO daily_logs (driver_id, log_date, total_drive_sec, total_on_duty_sec,
                                   total_off_duty_sec, total_sleeper_sec, violation_count, status, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (driver_id, log_date, result["totals"]["D"], result["totals"]["ON"],
         result["totals"]["OFF"], result["totals"]["SB"], v_count, status_flag, notes)
    )
    log_id = cursor.lastrowid

    # Insert Events
    for ev in events:
        st = datetime.fromisoformat(ev["start_time"])
        et = datetime.fromisoformat(ev["end_time"])
        dur = max(0, int((et - st).total_seconds()))
        cursor.execute(
            """INSERT INTO log_events (daily_log_id, duty_status, start_time, end_time, duration_sec, location, odometer)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (log_id, ev["duty_status"], ev["start_time"], ev["end_time"], dur, ev["location"], ev["odometer"])
        )

    # Insert Violations
    for v in result["violations"]:
        cursor.execute(
            """INSERT INTO violations (daily_log_id, rule_code, severity, description, event_timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (log_id, v["rule_code"], v["severity"], v["description"], v["timestamp"])
        )

    db.commit()
    db.close()
    flash(request, f"Log for {log_date} analyzed: {v_count} violation(s) identified.", "success" if v_count == 0 else "warning")
    return RedirectResponse(url=f"/logs/{log_id}", status_code=status.HTTP_302_FOUND)


@app.post("/logs/upload")
async def upload_csv_log(request: Request):
    if not is_authenticated(request):
        flash(request, "Please log in to access this page.", "warning")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    form = await request.form()
    driver_id = form.get("driver_id")
    log_date = form.get("log_date")
    csv_file: UploadFile = form.get("csv_file")

    if not csv_file or not driver_id or not log_date:
        flash(request, "Driver, date, and CSV file are required.", "danger")
        return RedirectResponse(url="/logs/new", status_code=status.HTTP_302_FOUND)

    try:
        content = await csv_file.read()
        stream = io.StringIO(content.decode("utf-8"), newline=None)
        reader = csv.DictReader(stream)

        events = []
        for row in reader:
            events.append({
                "duty_status": row.get("duty_status", "OFF").strip().upper(),
                "start_time": row.get("start_time", "").strip(),
                "end_time": row.get("end_time", "").strip(),
                "location": row.get("location", "Terminal").strip(),
                "odometer": float(row.get("odometer", 0) or 0),
                "notes": row.get("notes", "")
            })

        if not events:
            flash(request, "CSV contains no valid event records.", "danger")
            return RedirectResponse(url="/logs/new", status_code=status.HTTP_302_FOUND)

        engine = HOSRuleEngine()
        result = engine.evaluate_events(events)

        status_flag = "COMPLIANT" if result["compliant"] else "VIOLATION"
        v_count = len(result["violations"])

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO daily_logs (driver_id, log_date, total_drive_sec, total_on_duty_sec,
                                       total_off_duty_sec, total_sleeper_sec, violation_count, status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (driver_id, log_date, result["totals"]["D"], result["totals"]["ON"],
             result["totals"]["OFF"], result["totals"]["SB"], v_count, status_flag, f"Uploaded via CSV ({csv_file.filename})")
        )
        log_id = cursor.lastrowid

        for ev in events:
            st = datetime.fromisoformat(ev["start_time"])
            et = datetime.fromisoformat(ev["end_time"])
            dur = max(0, int((et - st).total_seconds()))
            cursor.execute(
                """INSERT INTO log_events (daily_log_id, duty_status, start_time, end_time, duration_sec, location, odometer)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (log_id, ev["duty_status"], ev["start_time"], ev["end_time"], dur, ev["location"], ev["odometer"])
            )

        for v in result["violations"]:
            cursor.execute(
                """INSERT INTO violations (daily_log_id, rule_code, severity, description, event_timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (log_id, v["rule_code"], v["severity"], v["description"], v["timestamp"])
            )

        db.commit()
        db.close()
        flash(request, f"CSV successfully imported! Found {v_count} violation(s).", "success" if v_count == 0 else "warning")
        return RedirectResponse(url=f"/logs/{log_id}", status_code=status.HTTP_302_FOUND)

    except Exception as e:
        flash(request, f"CSV Parsing Error: {str(e)}", "danger")
        return RedirectResponse(url="/logs/new", status_code=status.HTTP_302_FOUND)


@app.get("/logs/{log_id}", response_class=HTMLResponse)
async def view_log(request: Request, log_id: int):
    if not is_authenticated(request):
        flash(request, "Please log in to access this page.", "warning")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    user_id = request.session["user_id"]
    db = get_db()

    log = db.execute(
        """SELECT l.*, d.name as driver_name, d.license_number, d.terminal_city
           FROM daily_logs l
           JOIN drivers d ON l.driver_id = d.id
           WHERE l.id = ? AND d.user_id = ?""",
        (log_id, user_id)
    ).fetchone()

    if not log:
        db.close()
        flash(request, "Log not found or unauthorized.", "danger")
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    events = db.execute(
        "SELECT * FROM log_events WHERE daily_log_id = ? ORDER BY start_time ASC",
        (log_id,)
    ).fetchall()

    violations = db.execute(
        "SELECT * FROM violations WHERE daily_log_id = ? ORDER BY event_timestamp ASC",
        (log_id,)
    ).fetchall()
    db.close()

    # Prepare JSON serializable events for client-side HTML5 canvas DOT graph
    events_json = []
    for ev in events:
        events_json.append({
            "status": ev["duty_status"],
            "start": ev["start_time"],
            "end": ev["end_time"],
            "duration": ev["duration_sec"],
            "location": ev["location"]
        })

    return render(
        request,
        "log_detail.html",
        {
            "log": log,
            "events": events,
            "violations": violations,
            "events_json": events_json
        }
    )


@app.get("/audit", response_class=HTMLResponse)
async def audit(request: Request):
    if not is_authenticated(request):
        flash(request, "Please log in to access this page.", "warning")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    user_id = request.session["user_id"]
    db = get_db()

    violations = db.execute(
        """SELECT v.*, d.name as driver_name, d.license_number, l.log_date, l.id as log_id
           FROM violations v
           JOIN daily_logs l ON v.daily_log_id = l.id
           JOIN drivers d ON l.driver_id = d.id
           WHERE d.user_id = ?
           ORDER BY v.created_at DESC""",
        (user_id,)
    ).fetchall()
    db.close()

    # Rule breakdown stats
    rule_counts = {}
    for v in violations:
        rc = v["rule_code"]
        rule_counts[rc] = rule_counts.get(rc, 0) + 1

    return render(request, "audit.html", {"violations": violations, "rule_counts": rule_counts})


# --- REST API Endpoint for Realtime Validation ---
@app.post("/api/evaluate")
async def api_evaluate(request: Request):
    data = await request.json()
    events = data.get("events", [])
    engine = HOSRuleEngine()
    result = engine.evaluate_events(events)
    return JSONResponse(content=result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)


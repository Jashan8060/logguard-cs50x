# LOGGUARD: FMCSA Driver Log Compliance & 24-Hour Visualizer

#### Harvard University &bull; CS50x: Introduction to Computer Science
#### Final Project Submission
#### Jashandeep Singh
#### Singhjashandeep8060@gmail.com
#### GitHub- https://github.com/Jashan8060

---

### Video Demo
- **YouTube Demo URL:** [https://youtu.be/10n5bD5CScA](https://youtu.be/10n5bD5CScA)

---

## 1. Project Overview & Motivation

In the commercial freight and logistics transportation industry, heavy truck drivers in the United States operate under stringent Federal Motor Carrier Safety Administration (**FMCSA**) regulations known as **Hours of Service (HOS)** (codified in **49 CFR § 395**). These federal safety statutes exist to prevent driver fatigue by mandating strict limits on maximum continuous driving time, overall daily duty shift windows, and required rest intervals.

Commercial carriers are legally obligated to record every status change into one of four standardized duty states:
1. **OFF**: Off Duty (Rest / Home)
2. **SB**: Sleeper Berth (Rest in Vehicle Sleeper Unit)
3. **D**: Driving (Operating the Commercial Motor Vehicle)
4. **ON**: On Duty, Not Driving (Pre-trip inspection, loading/unloading cargo, fueling)

While modern trucking uses Electronic Logging Devices (ELDs), fleets and safety compliance officers frequently need an independent, deterministic tool to audit daily logs, detect violations before DOT audits, and visualize driver shifts on the traditional 24-hour Department of Transportation (DOT) stepped graph grid.

**LogGuard** was designed and built as a full-stack, educational web platform that allows dispatchers and safety managers to:
1. Register commercial drivers with CDL identification and terminal locations.
2. Ingest daily duty status event streams through an interactive time-interval editor or via direct ELD CSV file upload.
3. Automatically evaluate logs against core federal compliance rules using a custom stateful interval algorithm.
4. Render an interactive, stepped HTML5 Canvas visualization of the traditional 24-hour 4-line DOT log sheet.
5. Track fleet compliance posture across a real-time safety audit radar.

---

## 2. Distinctiveness and Complexity

### Distinctiveness
Unlike standard CS50 web applications (such as basic e-commerce carts, to-do lists, or generic social networks), **LogGuard** tackles a specialized, real-world regulatory domain. It solves a genuine computational problem: transforming raw, non-uniform time-interval series into chronological state transitions, calculating running duty accumulation windows across multiple rests, and generating precise regulatory violation reports with down-to-the-minute overage calculations.

Furthermore, LogGuard adheres to a modern **dark-mode-first glassmorphism design system** featuring ambient backdrop lighting, responsive data cards, and a custom HTML5 canvas graph visualizer that recreates official paper/digital DOT log sheets.

### Complexity & Algorithmic Design
The technical centerpiece of LogGuard is [`compliance.py`](compliance.py), an educational FMCSA property-carrying compliance engine implemented without heavy external machine learning libraries. It models:
- **10-Hour Shift Reset Logic:** Detects when a driver accumulates 10 or more consecutive hours in `OFF` or `SB`, cleanly resetting the 11-hour driving and 14-hour shift clocks.
- **The 14-Hour Consecutive Duty Window (49 CFR § 395.3(a)(2)):** Tracks the exact second the driver first comes on-duty and flags any driving operations occurring past the 14th consecutive calendar hour, regardless of breaks taken in-between.
- **The 11-Hour Maximum Driving Limit (49 CFR § 395.3(a)(1)):** Computes cumulative driving duration within the shift window and warns or issues critical violation flags when driving exceeds 11.0 cumulative hours.
- **The 30-Minute Rest Break Requirement (49 CFR § 395.3(a)(3)(ii)):** Validates that no more than 8 continuous hours of driving occur without an interruption of at least 30 consecutive minutes of non-driving time (`OFF`, `SB`, or `ON`).
- **Interactive Canvas Rendering Engine:** In [`static/js/chart.js`](static/js/chart.js), raw timestamp intervals are mapped onto high-DPI canvas coordinates across 24 vertical hourly columns (with 15-minute sub-ticks) and 4 horizontal status tiers, drawing stepped path transitions and blue driving highlight zones.

---

## 3. Project File Structure & Responsibilities

```
logguard-cs50x/
│
├── app.py                  # Main FastAPI application with Uvicorn, routing, sessions, and CRUD endpoints
├── compliance.py           # Pure Python FMCSA HOS Rule Engine with stateful interval math
├── database.py             # SQLite connection wrapper, schema initializer, and demo seeder
├── schema.sql              # Relational database schema with 5 tables and foreign key cascade rules
├── sample_data.csv         # Ready-to-use ELD driver duty status CSV for upload testing
├── requirements.txt        # Python package dependencies (Flask, Werkzeug, pytest)
├── README.md               # CS50x final project documentation
│
├── static/
│   ├── css/
│   │   └── style.css       # Full custom design system: dark mode, glassmorphism, flex/grid
│   └── js/
│       ├── app.js          # Client-side helpers (auto-dismissing alerts, Lucide icon updates)
│       └── chart.js        # HTML5 Canvas 24-hour stepped DOT graph visualizer
│
└── templates/
    ├── base.html           # Master layout with navigation bar, ambient glow, and flash messages
    ├── login.html          # Authentication page with one-click demo credentials autofill
    ├── register.html       # Safety officer account registration form
    ├── dashboard.html      # Central dashboard with fleet KPI cards, logs table, and safety radar
    ├── drivers.html        # Commercial driver roster and driver creation form
    ├── log_entry.html      # Dual-mode validation interface (Interactive form + CSV dropzone)
    ├── log_detail.html     # Detailed log inspection view featuring the 24-hour Canvas graph
    └── audit.html          # Fleet safety audit report categorizing violations by rule code
```

---

## 4. Database Schema Design

The SQLite database (`logguard.db`) is structured with relational integrity:
1. `users`: Stores registered safety officers with salted, hashed passwords (`werkzeug.security`).
2. `drivers`: Commercial drivers linked to user accounts via `user_id`.
3. `daily_logs`: Represents a 24-hour duty record containing cumulative seconds for driving, on-duty, off-duty, and sleeper berth, plus the compliance status (`COMPLIANT`, `VIOLATION`).
4. `log_events`: Granular intervals linking to `daily_logs` with `duty_status`, `start_time`, `end_time`, `duration_sec`, `location`, and `odometer`.
5. `violations`: Records each identified infraction with `rule_code`, `severity`, `description`, and `event_timestamp`.

---

## 5. Installation and Setup Instructions

### Prerequisites
- Python 3.9 or newer
- `pip` (Python package installer)

### Step 1: Clone or Navigate to the Directory
```bash
cd logguard-cs50x
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Initialize Database and Seed Demo Records
Running `database.py` will initialize the SQLite schema and pre-populate realistic sample data:
```bash
python database.py
```
*Creates default demo credentials:*
- **Username:** `demo`
- **Password:** `cs50x2026!`

### Step 4: Launch the Web Application (FastAPI + Uvicorn)
```bash
python app.py
# Or directly run Uvicorn:
uvicorn app:app --reload --port 8000
```
Open your web browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 6. How to Test and Grade the Project

1. **Log In:** Navigate to the login screen and click the **"Demo Account"** quick-fill pill to instantly populate `demo` / `cs50x2026!`.
2. **Review Dashboard:** Inspect the Fleet KPIs and explore pre-loaded logs:
   - Click **"Inspect"** on Marcus Vance's log (October 21) to observe a **100% Compliant** shift.
   - Click **"Inspect"** on Elena Rostova's log (October 22) to observe **11-Hour Drive** and **14-Hour Window** violations highlighted in red on the DOT Canvas visualizer.
3. **Upload CSV:** Click **"Validate Log"**, switch to the **"Upload CSV Log"** tab, select driver Marcus Vance, and upload the packaged `sample_data.csv`. Watch the compliance engine parse each row, calculate durations, and generate the 24-hour canvas graph.
4. **Interactive Entry:** In the **"Interactive Entry"** tab, dynamically add or remove duty status intervals to test edge cases.
5. **Safety Radar Audit:** Visit **"Audit Radar"** in the top navigation bar to view aggregate violation metrics grouped by federal rule code.

## This is a demo version of a complete SAAS product I am building, you can request a demo of the full product with access to all features including SMS/Email integrations, AI summaries, and more by contacting me at Singhjashandeep8060@gmail.com

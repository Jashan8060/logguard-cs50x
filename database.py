"""
Database helper module for LogGuard (CS50x Final Project).
Utilizes SQLite with Python's built-in sqlite3 library.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "logguard.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print("Database initialized successfully.")


def seed_demo_data():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Create Default Demo User
    demo_user = cursor.execute("SELECT id FROM users WHERE username = 'demo'").fetchone()
    if not demo_user:
        hashed_pw = generate_password_hash("cs50x2026!")
        cursor.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            ("demo", hashed_pw, "CS50x Evaluator", "Safety Director")
        )
        user_id = cursor.lastrowid
    else:
        user_id = demo_user["id"]

    # 2. Create Demo Drivers
    d1 = cursor.execute("SELECT id FROM drivers WHERE name = 'Marcus Vance'").fetchone()
    if not d1:
        cursor.execute(
            "INSERT INTO drivers (user_id, name, license_number, terminal_city) VALUES (?, ?, ?, ?)",
            (user_id, "Marcus Vance", "TX-9048123A", "Dallas, TX")
        )
        driver1_id = cursor.lastrowid
    else:
        driver1_id = d1["id"]

    d2 = cursor.execute("SELECT id FROM drivers WHERE name = 'Elena Rostova'").fetchone()
    if not d2:
        cursor.execute(
            "INSERT INTO drivers (user_id, name, license_number, terminal_city) VALUES (?, ?, ?, ?)",
            (user_id, "Elena Rostova", "IL-4491028B", "Chicago, IL")
        )
        driver2_id = cursor.lastrowid
    else:
        driver2_id = d2["id"]

    # 3. Create Sample Logs if empty
    from compliance import HOSRuleEngine
    engine = HOSRuleEngine()

    existing_logs = cursor.execute("SELECT COUNT(*) as count FROM daily_logs").fetchone()["count"]
    if existing_logs == 0:
        base_date = datetime.now().date()

        # Log 1: Marcus Vance - Compliant Shift
        log1_date = (base_date - timedelta(days=1)).strftime("%Y-%m-%d")
        events1 = [
            {"duty_status": "OFF", "start_time": f"{log1_date} 00:00:00", "end_time": f"{log1_date} 06:00:00", "location": "Dallas Terminal", "odometer": 105200.0},
            {"duty_status": "ON",  "start_time": f"{log1_date} 06:00:00", "end_time": f"{log1_date} 06:30:00", "location": "Dallas Yard", "odometer": 105200.0},
            {"duty_status": "D",   "start_time": f"{log1_date} 06:30:00", "end_time": f"{log1_date} 10:30:00", "location": "I-35 N Hillsboro", "odometer": 105440.0},
            {"duty_status": "OFF", "start_time": f"{log1_date} 10:30:00", "end_time": f"{log1_date} 11:15:00", "location": "Rest Area Waco", "odometer": 105440.0},
            {"duty_status": "D",   "start_time": f"{log1_date} 11:15:00", "end_time": f"{log1_date} 15:45:00", "location": "I-35 S Temple", "odometer": 105710.0},
            {"duty_status": "ON",  "start_time": f"{log1_date} 15:45:00", "end_time": f"{log1_date} 16:15:00", "location": "Austin Dock", "odometer": 105710.0},
            {"duty_status": "SB",  "start_time": f"{log1_date} 16:15:00", "end_time": f"{log1_date} 23:59:59", "location": "Austin Truckstop", "odometer": 105710.0}
        ]

        eval1 = engine.evaluate_events(events1)
        cursor.execute(
            """INSERT INTO daily_logs (driver_id, log_date, total_drive_sec, total_on_duty_sec, total_off_duty_sec, total_sleeper_sec, violation_count, status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (driver1_id, log1_date, eval1["totals"]["D"], eval1["totals"]["ON"], eval1["totals"]["OFF"], eval1["totals"]["SB"], len(eval1["violations"]), "COMPLIANT", "Flawless interstate route from Dallas to Austin.")
        )
        log1_id = cursor.lastrowid

        for ev in events1:
            st = datetime.fromisoformat(ev["start_time"])
            et = datetime.fromisoformat(ev["end_time"])
            dur = int((et - st).total_seconds())
            cursor.execute(
                """INSERT INTO log_events (daily_log_id, duty_status, start_time, end_time, duration_sec, location, odometer)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (log1_id, ev["duty_status"], ev["start_time"], ev["end_time"], dur, ev["location"], ev["odometer"])
            )

        # Log 2: Elena Rostova - Violation Shift (11h Driving & 14h Duty Window exceeded)
        log2_date = base_date.strftime("%Y-%m-%d")
        events2 = [
            {"duty_status": "OFF", "start_time": f"{log2_date} 00:00:00", "end_time": f"{log2_date} 05:00:00", "location": "Gary Terminal", "odometer": 218400.0},
            {"duty_status": "ON",  "start_time": f"{log2_date} 05:00:00", "end_time": f"{log2_date} 05:30:00", "location": "Gary Yard (Pre-trip)", "odometer": 218400.0},
            {"duty_status": "D",   "start_time": f"{log2_date} 05:30:00", "end_time": f"{log2_date} 11:30:00", "location": "I-80 W Des Moines", "odometer": 218760.0},
            {"duty_status": "OFF", "start_time": f"{log2_date} 11:30:00", "end_time": f"{log2_date} 12:00:00", "location": "Travel Plaza", "odometer": 218760.0},
            {"duty_status": "D",   "start_time": f"{log2_date} 12:00:00", "end_time": f"{log2_date} 18:00:00", "location": "I-80 W Omaha", "odometer": 219120.0},
            {"duty_status": "D",   "start_time": f"{log2_date} 18:00:00", "end_time": f"{log2_date} 20:30:00", "location": "Lincoln Outskirts", "odometer": 219270.0},
            {"duty_status": "ON",  "start_time": f"{log2_date} 20:30:00", "end_time": f"{log2_date} 21:00:00", "location": "Lincoln Depot", "odometer": 219270.0},
            {"duty_status": "OFF", "start_time": f"{log2_date} 21:00:00", "end_time": f"{log2_date} 23:59:59", "location": "Lincoln Hotel", "odometer": 219270.0}
        ]

        eval2 = engine.evaluate_events(events2)
        cursor.execute(
            """INSERT INTO daily_logs (driver_id, log_date, total_drive_sec, total_on_duty_sec, total_off_duty_sec, total_sleeper_sec, violation_count, status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (driver2_id, log2_date, eval2["totals"]["D"], eval2["totals"]["ON"], eval2["totals"]["OFF"], eval2["totals"]["SB"], len(eval2["violations"]), "VIOLATION", "Severe over-hours driving due to unrecorded weather delay.")
        )
        log2_id = cursor.lastrowid

        for ev in events2:
            st = datetime.fromisoformat(ev["start_time"])
            et = datetime.fromisoformat(ev["end_time"])
            dur = int((et - st).total_seconds())
            cursor.execute(
                """INSERT INTO log_events (daily_log_id, duty_status, start_time, end_time, duration_sec, location, odometer)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (log2_id, ev["duty_status"], ev["start_time"], ev["end_time"], dur, ev["location"], ev["odometer"])
            )

        for v in eval2["violations"]:
            cursor.execute(
                """INSERT INTO violations (daily_log_id, rule_code, severity, description, event_timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (log2_id, v["rule_code"], v["severity"], v["description"], v["timestamp"])
            )

    conn.commit()
    conn.close()
    print("Demo data seeded successfully.")


if __name__ == "__main__":
    init_db()
    seed_demo_data()

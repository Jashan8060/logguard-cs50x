-- Schema for LogGuard CS50x Final Project
-- SQLite Relational Database

DROP TABLE IF EXISTS violations;
DROP TABLE IF EXISTS log_events;
DROP TABLE IF EXISTS daily_logs;
DROP TABLE IF EXISTS drivers;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT DEFAULT 'Safety Manager',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE drivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    license_number TEXT NOT NULL,
    terminal_city TEXT DEFAULT 'Dallas, TX',
    timezone TEXT DEFAULT 'America/Chicago',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE daily_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER NOT NULL,
    log_date TEXT NOT NULL, -- YYYY-MM-DD
    total_drive_sec INTEGER DEFAULT 0,
    total_on_duty_sec INTEGER DEFAULT 0,
    total_off_duty_sec INTEGER DEFAULT 0,
    total_sleeper_sec INTEGER DEFAULT 0,
    violation_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'COMPLIANT', -- 'COMPLIANT', 'WARNING', 'VIOLATION'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (driver_id) REFERENCES drivers (id) ON DELETE CASCADE,
    UNIQUE(driver_id, log_date)
);

CREATE TABLE log_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    daily_log_id INTEGER NOT NULL,
    duty_status TEXT NOT NULL CHECK(duty_status IN ('OFF', 'SB', 'D', 'ON')),
    start_time TEXT NOT NULL, -- ISO8601 or YYYY-MM-DD HH:MM:SS
    end_time TEXT NOT NULL,
    duration_sec INTEGER NOT NULL,
    location TEXT DEFAULT 'Highway Terminal',
    odometer REAL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (daily_log_id) REFERENCES daily_logs (id) ON DELETE CASCADE
);

CREATE TABLE violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    daily_log_id INTEGER NOT NULL,
    rule_code TEXT NOT NULL, -- 'US_11H_DRIVE', 'US_14H_WINDOW', 'US_30M_BREAK'
    severity TEXT NOT NULL,  -- 'CRITICAL', 'WARNING'
    description TEXT NOT NULL,
    event_timestamp TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (daily_log_id) REFERENCES daily_logs (id) ON DELETE CASCADE
);

CREATE INDEX idx_logs_driver ON daily_logs(driver_id);
CREATE INDEX idx_events_log ON log_events(daily_log_id);
CREATE INDEX idx_violations_log ON violations(daily_log_id);

"""
LogGuard - FMCSA Hours of Service (HOS) Educational Rule Engine
Standard Public Domain Regulations (49 CFR § 395) for Property-Carrying CMVs.

Designed for CS50x Final Project:
Demonstrates stateful interval analysis, time-series accumulation,
and boundary condition validation in Python.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class HOSViolation:
    def __init__(self, rule_code: str, severity: str, description: str, timestamp: datetime):
        self.rule_code = rule_code        # e.g., 'US_11H_DRIVE', 'US_14H_WINDOW', 'US_30M_BREAK'
        self.severity = severity          # 'CRITICAL', 'WARNING'
        self.description = description
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_code": self.rule_code,
            "severity": self.severity,
            "description": self.description,
            "timestamp": self.timestamp.isoformat()
        }


class HOSRuleEngine:
    """
    Evaluates a chronological sequence of driver duty status intervals
    against core FMCSA property-carrying regulations.
    
    Duty Status Codes:
      - 'OFF': Off Duty
      - 'SB' : Sleeper Berth
      - 'D'  : Driving
      - 'ON' : On Duty (Not Driving)
    """

    MAX_DRIVING_SEC = 11 * 3600              # 11 Hours maximum driving
    MAX_DUTY_WINDOW_SEC = 14 * 3600          # 14 Hours consecutive shift window
    MAX_DRIVE_BEFORE_BREAK_SEC = 8 * 3600    # 8 Hours driving before mandatory 30m break
    MIN_QUALIFYING_BREAK_SEC = 30 * 60       # 30 Minutes break
    MIN_RESET_REST_SEC = 10 * 3600           # 10 Hours rest to reset shift clocks

    def __init__(self):
        pass

    def evaluate_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes a list of event dictionaries sorted chronologically:
        [
            {
                "duty_status": "OFF"|"SB"|"D"|"ON",
                "start_time": datetime object or ISO string,
                "end_time": datetime object or ISO string,
                "location": str,
                "odometer": float
            }, ...
        ]
        
        Returns summary metrics and list of HOSViolation objects.
        """
        violations: List[HOSViolation] = []

        # Totals in seconds
        totals = {
            "OFF": 0,
            "SB": 0,
            "D": 0,
            "ON": 0
        }

        if not events:
            return {
                "totals": totals,
                "violations": [],
                "compliant": True
            }

        # Normalize and ensure datetime objects
        normalized_events = []
        for e in events:
            st = e["start_time"]
            et = e["end_time"]
            if isinstance(st, str):
                st = datetime.fromisoformat(st.replace("Z", ""))
            if isinstance(et, str):
                et = datetime.fromisoformat(et.replace("Z", ""))

            duration_sec = max(0, int((et - st).total_seconds()))
            status = e["duty_status"].upper()

            normalized_events.append({
                "status": status,
                "start_time": st,
                "end_time": et,
                "duration_sec": duration_sec,
                "location": e.get("location", "Unknown"),
                "odometer": e.get("odometer", 0)
            })

            if status in totals:
                totals[status] += duration_sec

        # Sort chronologically by start_time
        normalized_events.sort(key=lambda x: x["start_time"])

        # Shift State Trackers
        shift_start_time: Optional[datetime] = None
        shift_drive_sec = 0
        drive_sec_since_break = 0

        for i, ev in enumerate(normalized_events):
            status = ev["status"]
            st = ev["start_time"]
            et = ev["end_time"]
            duration = ev["duration_sec"]

            # 1. Check for 10-Hour Shift Reset
            # If the driver has completed >= 10 consecutive hours in OFF or SB
            if status in ("OFF", "SB") and duration >= self.MIN_RESET_REST_SEC:
                # Reset Shift Clocks
                shift_start_time = None
                shift_drive_sec = 0
                drive_sec_since_break = 0
                continue

            # 2. Check for 30-Minute Break Satisfaction
            # Any continuous break of >= 30 min in OFF, SB, or ON-Duty resets driving-since-break
            if status in ("OFF", "SB", "ON") and duration >= self.MIN_QUALIFYING_BREAK_SEC:
                drive_sec_since_break = 0

            # 3. Shift Initialization
            # First ON or Driving status starts the 14-hour clock
            if status in ("D", "ON") and shift_start_time is None:
                shift_start_time = st

            # 4. Driving Evaluation
            if status == "D":
                # A. 14-Hour Duty Window Check
                if shift_start_time is not None:
                    elapsed_from_start = (st - shift_start_time).total_seconds()
                    if elapsed_from_start >= self.MAX_DUTY_WINDOW_SEC:
                        violations.append(HOSViolation(
                            rule_code="US_14H_WINDOW",
                            severity="CRITICAL",
                            description=(
                                f"14-Hour Duty Window Exceeded: Driving logged after the 14th consecutive "
                                f"hour from shift start ({shift_start_time.strftime('%H:%M')})."
                            ),
                            timestamp=st
                        ))
                    elif (elapsed_from_start + duration) > self.MAX_DUTY_WINDOW_SEC:
                        overage_mins = int((elapsed_from_start + duration - self.MAX_DUTY_WINDOW_SEC) / 60)
                        violations.append(HOSViolation(
                            rule_code="US_14H_WINDOW",
                            severity="CRITICAL",
                            description=(
                                f"14-Hour Duty Window Exceeded: Shift ended {overage_mins} minutes beyond the "
                                f"14-hour window from shift start ({shift_start_time.strftime('%H:%M')})."
                            ),
                            timestamp=shift_start_time + timedelta(seconds=self.MAX_DUTY_WINDOW_SEC)
                        ))

                # B. 11-Hour Maximum Driving Check
                potential_drive = shift_drive_sec + duration
                if shift_drive_sec >= self.MAX_DRIVING_SEC:
                    violations.append(HOSViolation(
                        rule_code="US_11H_DRIVE",
                        severity="CRITICAL",
                        description=(
                            f"11-Hour Driving Limit Exceeded: Driver logged driving while already at "
                            f"{shift_drive_sec / 3600:.2f} hours for this shift."
                        ),
                        timestamp=st
                    ))
                elif potential_drive > self.MAX_DRIVING_SEC:
                    overage_mins = int((potential_drive - self.MAX_DRIVING_SEC) / 60)
                    violations.append(HOSViolation(
                        rule_code="US_11H_DRIVE",
                        severity="CRITICAL",
                        description=(
                            f"11-Hour Driving Limit Exceeded: Accumulated {potential_drive / 3600:.2f} hours of "
                            f"driving ({overage_mins} min over 11h limit)."
                        ),
                        timestamp=st + timedelta(seconds=(self.MAX_DRIVING_SEC - shift_drive_sec))
                    ))

                # C. 30-Minute Rest Break Check
                potential_drive_since_break = drive_sec_since_break + duration
                if potential_drive_since_break > self.MAX_DRIVE_BEFORE_BREAK_SEC:
                    over_hours = potential_drive_since_break / 3600
                    violations.append(HOSViolation(
                        rule_code="US_30M_BREAK",
                        severity="WARNING",
                        description=(
                            f"30-Minute Break Required: Driving reached {over_hours:.2f} hours without a "
                            f"qualifying 30-minute rest break."
                        ),
                        timestamp=st + timedelta(seconds=max(0, self.MAX_DRIVE_BEFORE_BREAK_SEC - drive_sec_since_break))
                    ))

                # Accrue drive times
                shift_drive_sec += duration
                drive_sec_since_break += duration

            elif status == "ON":
                # On duty does not reset driving, but counts toward shift and can satisfy 30m break if >= 30m
                pass

        return {
            "totals": totals,
            "violations": [v.to_dict() for v in violations],
            "compliant": len(violations) == 0
        }

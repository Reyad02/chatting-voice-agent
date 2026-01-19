from googleapiclient.errors import HttpError
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json
import uuid
import re
from typing import Optional

SESSIONS_FILE = "chat_sessions.json"

def to_rfc3339(dt_str: str, timezone: str):
    """
    Converts 'YYYY-MM-DDTHH:MM:SS' → RFC3339 with timezone
    """
    dt = datetime.fromisoformat(dt_str)
    dt = dt.replace(tzinfo=ZoneInfo(timezone))
    return dt.isoformat()

def create_event(
    service,
    summary,
    description,
    start_datetime,
    end_datetime,
    timezone,
    repeat="never",          # never, everyday, every_week, every_month
    reminder="15 minutes",              # dict from UI
    method="popup"
):
    # print("Creating event on Google Calendar...")
    # print(summary, description, start_datetime, end_datetime, timezone, repeat, reminder, method)
    
    reminder = reminder.lower().strip()
    unit_map = {
        "min": "minutes",
        "mins": "minutes",
        "minute": "minutes",
        "minutes": "minutes",

        "hr": "hours",
        "hrs": "hours",
        "hour": "hours",
        "hours": "hours",

        "day": "days",
        "days": "days",

        "week": "weeks",
        "weeks": "weeks",
    }
    match  = re.match(r"(\d+)\s+([a-zA-Z]+)", reminder)
    if match:
        value = int(match.group(1))
        raw_unit = match.group(2)
        unit = unit_map.get(raw_unit)
        if unit:
            reminder = f"{value} {unit}"

        
    try:
        event = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_datetime,
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end_datetime,
                "timeZone": timezone,
            }
        }

        # ---------- Reminder handling ----------
        if reminder:
            reminder_parts = reminder.split()
            reminder = {
                "value": int(reminder_parts[0]),
                "unit": reminder_parts[1],  # minutes, hours, days, weeks
            }
            UNIT_TO_MINUTES = {
                "minutes": 1,
                "hours": 60,
                "days": 1440,
                "weeks": 10080
            }

            minutes = reminder["value"] * UNIT_TO_MINUTES[reminder["unit"]]

            # method = "popup" if reminder["type"] == "notification" else "email"

            event["reminders"] = {
                "useDefault": False,
                "overrides": [
                    {
                        "method": method,
                        "minutes": minutes
                    }
                ]
            }

        # ---------- Repeat / stamp ----------
        if repeat == "everyday":
            event["recurrence"] = ["RRULE:FREQ=DAILY"]
        elif repeat == "every_week":
            event["recurrence"] = ["RRULE:FREQ=WEEKLY"]
        elif repeat == "every_month":
            event["recurrence"] = ["RRULE:FREQ=MONTHLY"]

        created_event = service.events().insert(
            calendarId="primary",
            body=event
        ).execute()
        # print(f"Event created: {created_event.get('htmlLink')}")
        return created_event

    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

# def update_event_by_title_date(
#     event: dict,
#     # summary: Optional[str] = None,
#     # date: Optional[str] = None,
#     new_summary: Optional[str] = None,
#     description: Optional[str] = None,
#     start_datetime: Optional[str] = None,
#     end_datetime: Optional[str] = None,
#     timezone: Optional[str] = None,
#     repeat: Optional[str] = None,
#     reminder: Optional[str] = None,
#     method: Optional[str] = None
# ):
#     try:    
#         if new_summary:
#             event["summary"] = new_summary

#         if description:
#             event["description"] = description

#         if start_datetime:
#             event["start"]["dateTime"] = start_datetime

#         if end_datetime:
#             event["end"]["dateTime"] = end_datetime

#         if timezone:
#             event["start"]["timeZone"] = timezone
#             event["end"]["timeZone"] = timezone

#         if reminder:
#             reminder = reminder.lower().strip()
#             unit_map = {
#                 "min": "minutes",
#                 "mins": "minutes",
#                 "minute": "minutes",
#                 "minutes": "minutes",
#                 "hr": "hours",
#                 "hrs": "hours",
#                 "hour": "hours",
#                 "hours": "hours",
#                 "day": "days",
#                 "days": "days",
#                 "week": "weeks",
#                 "weeks": "weeks",
#             }

#             match = re.match(r"(\d+)\s+([a-zA-Z]+)", reminder)
#             if match:
#                 value = int(match.group(1))
#                 raw_unit = match.group(2)
#                 unit = unit_map.get(raw_unit)

#                 UNIT_TO_MINUTES = {
#                     "minutes": 1,
#                     "hours": 60,
#                     "days": 1440,
#                     "weeks": 10080
#                 }

#                 minutes = value * UNIT_TO_MINUTES[unit]

#                 event["reminders"] = {
#                     "useDefault": False,
#                     "overrides": [
#                         {
#                             "method": method if method else event["reminders"]["overrides"][0]["method"],
#                             "minutes": minutes
#                         }
#                     ]
#                 }

#         if repeat:
#             if repeat == "never":
#                 event.pop("recurrence", None)
#             elif repeat == "everyday":
#                 event["recurrence"] = ["RRULE:FREQ=DAILY"]
#             elif repeat == "every_week":
#                 event["recurrence"] = ["RRULE:FREQ=WEEKLY"]
#             elif repeat == "every_month":
#                 event["recurrence"] = ["RRULE:FREQ=MONTHLY"]

#         return event

#     except Exception as e:
#         return {
#             "status": "error",
#             "error": str(e)
#         }
# def create_event(service, summary, description, start_datetime, end_datetime, timezone):
#     try: 
#         # print("Creating event on Google Calendar...")
#         event = {
#             'summary': summary,
#             'description': description,
#             'colorId': '6',
#             'start': {
#                 'dateTime': start_datetime,
#                 'timeZone': timezone,
#             },
#             'end': {
#                 'dateTime': end_datetime,
#                 'timeZone': timezone,
#             }
#         }
    
#         created_event = service.events().insert(calendarId='primary', body=event).execute()
#         # print(f"Event created: {created_event.get('htmlLink')}")
#         return created_event
#     except HttpError as error:
#         print(f"An error occurred: {error}")
        
def load_sessions():
    """Load all chat sessions from file."""
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_sessions(sessions):
    """Save all chat sessions to file."""
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=2)

def get_or_create_session(sessions, session_id=None):
    """Return existing session if found, otherwise create a new one."""
    if session_id and session_id in sessions:
        return session_id
    new_id = session_id or str(uuid.uuid4())
    sessions[new_id] = []
    return new_id
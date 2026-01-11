from googleapiclient.errors import HttpError
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json
import uuid

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

        return created_event

    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

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
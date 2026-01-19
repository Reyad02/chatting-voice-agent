from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from datetime import datetime
# from zoneinfo import ZoneInfo 
import numpy as np
 
from dotenv import dotenv_values
import json
from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
from utils.helpers import  create_event, load_sessions, save_sessions, get_or_create_session
from utils.google_calender_auth import get_credentials
# from typing import Optional

env_vars = dotenv_values(".env")
OPENAI_API_KEY = env_vars.get("OPENAI_API_KEY")

# def get_embedding(text: str):
#     response = openai_client.embeddings.create(
#         model="text-embedding-3-small",
#         input=text
#     )
#     return response.data[0].embedding

# def cosine_similarity(a, b):
#     a = np.array(a)
#     b = np.array(b)
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# def semantic_match(query, text, threshold=0.6):
#     q_emb = get_embedding(query)
#     t_emb = get_embedding(text)
#     score = cosine_similarity(q_emb, t_emb)
#     return score >= threshold, score

meal_list = [
        {
            'date': '2026-01-16', 
            'time': '08:30', 
            'meal_type': 'breakfast', 
            'title': 'Oatmeal with Banana and Honey', 
            'description': 'A bowl of oatmeal topped with sliced banana and a drizzle of honey', 
            'calories': 350, 
            'id': 1
        }, 
        {
            'date': '2026-01-16', 
            'time': '12:30', 
            'meal_type': 'lunch', 
            'title': 'rice & chicken', 
            'description': 'A bowl of rice and chicken curry', 
            'calories': 500, 
            'id': 2
        }
    ]
recipe_list = []
reminder_list = []
event_list = [
    {
        'kind': 'calendar#event', 
        'etag': '"3537114599200510"', 
        'id': 'c1o2si7t698qeog2k3qn6roti4', 
        'status': 'confirmed', 
        'htmlLink': 'https://www.google.com/calendar/event?eid=YzFvMnNpN3Q2OThxZW9nMmszcW42cm90aTQgYWxtb21lbnJleWFkMDJAbQ', 
        'created': '2026-01-16T09:54:59.000Z', 
        'updated': '2026-01-16T09:54:59.600Z', 
        'summary': 'Weekly Team Sync – Project Alpha Update', 
        'description': 'Team reviews progress on Project Alpha, discusses blockers and challenges, assigns next actions, and aligns on priorities for the upcoming week.',
        'creator': {'email': 'almomenreyad02@gmail.com', 'self': True}, 
        'organizer': {'email': 'almomenreyad02@gmail.com', 'self': True}, 
        'start': {'dateTime': '2026-01-16T15:00:00+06:00', 'timeZone': 'Asia/Dhaka'},
        'end': {'dateTime': '2026-01-16T16:00:00+06:00', 'timeZone': 'Asia/Dhaka'},
        'iCalUID': 'c1o2si7t698qeog2k3qn6roti4@google.com', 
        'sequence': 0, 
        'reminders': 
            {
                'useDefault': False, 
                'overrides': [{'method': 'email', 'minutes': 60}]
            }, 
        'eventType': 'default',
        'date': '2026-01-16'
    },
    {
        'kind': 'calendar#event', 
        'etag': '"3537115931493726"', 
        'id': 'bahalmlc2datvm4vrm9le9j6kk', 
        'status': 'confirmed', 
        'htmlLink': 'https://www.google.com/calendar/event?eid=YmFoYWxtbGMyZGF0dm00dnJtOWxlOWo2a2sgYWxtb21lbnJleWFkMDJAbQ', 
        'created': '2026-01-16T10:06:05.000Z', 
        'updated': '2026-01-16T10:06:05.746Z', 
        'summary': 'testing meeting', 
        'description': 'how to increase sell', 
        'creator': {'email': 'almomenreyad02@gmail.com', 'self': True}, 
        'organizer': {'email': 'almomenreyad02@gmail.com', 'self': True}, 
        'start': {'dateTime': '2026-01-16T18:00:00+06:00', 'timeZone': 'Asia/Dhaka'}, 
        'end': {'dateTime': '2026-01-16T19:00:00+06:00', 'timeZone': 'Asia/Dhaka'},
        'iCalUID': 'bahalmlc2datvm4vrm9le9j6kk@google.com', 
        'sequence': 0, 
        'reminders': 
            {
                'useDefault': False, 
                'overrides': [{'method': 'email', 'minutes': 30}]
            }, 
        'eventType': 'default',
        'date': '2026-01-16'
    }    
]
note_list = []


def build_response(
    session_id: str,
    ai_message: str,
    meals=None,
    lists=None,
    reminders=None,
    events=None,
    recipes=None
):
    return {
        "session_id": session_id,
        "ai_message": ai_message,
        "meals": meals or [],
        "lists": lists or [],
        "reminders": reminders or [],
        "events": events or [],
        "recipes": recipes or []
    }

# def find_events(start_datetime: str, end_datetime: str, timezone: str):
#     try:
#         creds = get_credentials()
#         service = build("calendar", "v3", credentials=creds)

#         start_rfc3339 = to_rfc3339(start_datetime, timezone)
#         end_rfc3339 = to_rfc3339(end_datetime, timezone)
#         events_result = service.events().list(
#             calendarId="primary",
#             timeMin=start_rfc3339,
#             timeMax=end_rfc3339,
#             # q=query,
#             singleEvents=True,
#             orderBy="startTime",
#             timeZone=timezone
#         ).execute()

#         events = events_result.get("items", [])
#         # print(events)
#         # print(f"Found {len(events)} events.")
#         # print(events)

#         return {
#             "status": "success",
#             "count": len(events),
#             "events": [
#                 {
#                     "event_id": e["id"],
#                     "summary": e.get("summary"),
#                     "start": e["start"].get("dateTime"),
#                     "end": e["end"].get("dateTime")
#                 }
#                 for e in events
#             ]
#         }

#     except HttpError as error:
#         return {"status": "error", "error": str(error)}

def schedule_event(summary: str, description:str, start_datetime:str, end_datetime:str, timezone:str, repeat:str="never", reminder:str="15 minutes", method:str="popup"):
    try:
        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)
        event=create_event(service, summary=summary, description=description, start_datetime=start_datetime, end_datetime=end_datetime, timezone=timezone, repeat=repeat, reminder=reminder, method=method)
       
        dateTime = event['start'].get('dateTime')
        date = dateTime.split("T")[0]
        event["date"] = date
        event_list.append(event)
        print("Event scheduled:", event)
        # Here you would typically save the meeting to a database or file
        return {"status": "Meeting scheduled successfully", "event": event}
    except Exception as e:
        return {"status": "Error scheduling meeting", "error": str(e)}

# def update_event(
#     summary: str,
#     date: str,
#     new_summary: Optional[str] = None,
#     description: Optional[str] = None,
#     start_datetime: Optional[str] = None,
#     end_datetime: Optional[str] = None,
#     timezone: Optional[str] = None,
#     repeat: Optional[str] = None,
#     reminder: Optional[str] = None,
#     method: Optional[str] = None,
# ):
#     print(summary, date, new_summary, description, start_datetime, end_datetime, timezone, repeat, reminder, method)
#     try:
#         creds = get_credentials()
#         service = build("calendar", "v3", credentials=creds)

#         # ---------- 1. Find matching event ----------
#         best_match = None
#         best_score = 0.0

#         for e in event_list:
#             e_date = e["start"]["dateTime"].split("T")[0]
#             if e_date == date:
#                 matched, score = semantic_match(
#                     summary, e.get("summary", ""), threshold=0.6
#                 )
#                 if matched and score > best_score:
#                     best_match = e
#                     best_score = score

#         if not best_match:
#             return {
#                 "status": "error",
#                 "message": f"No event found on {date} with summary '{summary}'"
#             }

#         event_id = best_match["id"]
#         event = best_match
        
#         # print("Found event to update:", event)
#         updated_event = update_event_by_title_date(
#             event,
#             new_summary=new_summary,
#             description=description,
#             start_datetime=start_datetime,
#             end_datetime=end_datetime,
#             timezone=timezone,
#             repeat=repeat,
#             reminder=reminder,
#             method=method,
#         )

#         # print("Updated event data:", updated_event)

#         updated_event = service.events().update(
#             calendarId="primary",
#             eventId=event_id,
#             body=event
#         ).execute()
        
#         # event must be store in the database
  
#         print("Event updated:", updated_event)
        
#         return {"status": "Meeting updated successfully", "event": updated_event}


#     except Exception as e:
#         return {
#             "status": "error",
#             "error": str(e)
#         }

# def delete_event(summary: str, date: str):
#     try:
#         creds = get_credentials()
#         service = build("calendar", "v3", credentials=creds)
        
#         best_match = None
#         best_score = 0.0

#         for e in event_list:
#             e_date = e["start"]["dateTime"].split("T")[0]
#             if e_date == date:
#                 matched, score = semantic_match(
#                     summary, e.get("summary", ""), threshold=0.6
#                 )
#                 if matched and score > best_score:
#                     best_match = e
#                     best_score = score

#         if not best_match:
#             return {
#                 "status": "error",
#                 "message": f"No event found on {date} with summary '{summary}'"
#             }

#         event_id = best_match["id"]
#         # event = best_match

#         service.events().delete(
#             calendarId="primary",
#             eventId=event_id
#         ).execute()
        
#         # event must be removed from the database
#         event_list.remove(best_match)

#         # print(f"Event of {summary} on {date} deleted.")
#         return {"status": "Event deleted successfully", "event": best_match}

#     except Exception as e:
#         return {"status": "error", "error": str(e)}
    
def save_list(title: str, items: list):
    note = {
        "title": title,
        "items": items,
    }
    
    note_list.append(note)
    # Here you would typically save the lists to a database or file
    return {"status": "List saved successfully", "list": note}

def add_meal(date: str, time: str, meal_type: str, title: str, description: str, calories: float):
    meal_entry = {
        "date": date,
        "time": time,
        "meal_type": meal_type,
        "title": title,
        "description": description,
        "calories": calories
    }
    
    # meal_entry["id"] = len(meal_list) + 1
    
    meal_list.append(meal_entry)
    print(meal_list)
    # Here you would typically save the meal_entry to a database or file
    return {"status": "Meal added successfully", "meal": meal_entry}

def add_recipe(recipe_name: str, meal_type: str, cooking_time: float, description: str, ratings: float):
    recipe_entry = {
        "recipe_name": recipe_name,
        "meal_type": meal_type,
        "cooking_time": cooking_time,
        "description": description,
        "ratings": ratings
    }
    
    # Here you would typically save the recipe_entry to a database or file
    recipe_list.append(recipe_entry)
    return {"status": "Recipe added successfully", "recipe": recipe_entry} 

def add_reminders(title: str, time: str):
    reminder_entry = {
        "title": title,
        "time": time
    }
    
    # Here you would typically save the reminder_entry to a database or file
    reminder_list.append(reminder_entry)
    return {"status": "Reminder added successfully", "reminder": reminder_entry}

# def delete_meal(date: str, meal_type: str, title: str):
#     best_match = None
#     best_score = 0.0
    
#     for meal in meal_list:
#         if meal["date"] == date and meal["meal_type"] == meal_type:
#             semantic_match_result, score = semantic_match(title, meal["title"], threshold=0.6)
#             print(semantic_match_result, score)
#             if semantic_match_result and score > best_score:
#                 best_match = meal
#                 best_score = score

#     if best_match is None:
#         return {"status": f"Meal not found using the date {date}, meal type {meal_type}, and title {title}"}
    
#     # Here you would typically delete the meal from a database or file
#     meal_list.remove(best_match)
#     print(meal_list)
#     return {"status": "Meal deleted successfully", "meal": best_match}
 
# def update_meal(
#     date: str,
#     meal_type: str,
#     title: str,
#     new_date: Optional[str] = None,
#     new_time: Optional[str] = None,
#     new_meal_type: Optional[str] = None,
#     new_title: Optional[str] = None,
#     new_description: Optional[str] = None,
#     new_calories: Optional[float] = None
# ):
#     best_match = None
#     best_score = 0.0
    
#     for meal in meal_list:
#         if meal["date"] == date and meal["meal_type"] == meal_type:
#             semantic_match_result, score = semantic_match(title, meal["title"], threshold=0.6)
#             if semantic_match_result and score > best_score:
#                 best_match = meal
#                 best_score = score
    
#     if best_match is None:
#         return {"status": f"Meal not found using the date {date}, meal type {meal_type}, and title {title}"}
    
#     if new_date is not None:
#         best_match["date"] = new_date
#     if new_time is not None:
#         best_match["time"] = new_time
#     if new_meal_type is not None:
#         best_match["meal_type"] = new_meal_type
#     if new_title is not None:
#         best_match["title"] = new_title
#     if new_description is not None:
#         best_match["description"] = new_description
#     if new_calories is not None:
#         best_match["calories"] = new_calories

#     print(meal_list)
#     # Here you would typically update the meal in a database or file

#     return {
#         "status": "Meal updated successfully",
#         "meal": best_match
#     }

tools = [
    {
        "type": "function",
        "name": "schedule_event",
        "description": "Schedule a meeting with specified description, start_datetime, end_datetime, and timezone.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary" :{
                    "type": "string",
                    "description": "Summary of the meeting"
                },
                "description": {
                    "type": "string",
                    "description": "Description of the meeting"
                },
                "start_datetime": {
                    "type": "string",
                    "description": "Start date and time of the meeting in ISO 8601 format"
                },
                "end_datetime": {
                    "type": "string",
                    "description": "End date and time of the meeting in ISO 8601 format"
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone of the meeting"
                },
                "repeat": {
                    "type": "string",
                    "description": "Repeat frequency of the meeting (never, everyday, every_week, every_month)",
                    "enum": ["never", "everyday", "every_week", "every_month"]
                },
                "reminder": {
                    "type": "string",
                    "description": "Reminder time before the meeting (e.g., 15 minutes). The format is '<number> <unit>' where unit can be minutes, hours, days, or weeks.",
                },
                "method": {
                    "type": "string",
                    "description": "Reminder method (e.g., popup, email)",
                    "enum": ["popup", "email"]
                }
            },
            "required": ["summary", "description", "start_datetime", "end_datetime", "timezone"],
            "additionalProperties": False,
        },
        # "strict": True,
    },
    # {
    #     "type": "function",
    #     "name": "update_event",
    #     "description": "Update an existing calendar event identified by summary and date with new details.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "summary": {
    #                 "type": "string",
    #                 "description": "Summary of the existing event to be updated"
    #             },
    #             "date": {
    #                 "type": "string",
    #                 "description": "Date of the existing event in YYYY-MM-DD format"
    #             },
    #             "new_summary" :{
    #                 "type": "string",
    #                 "description": "New summary of the event"
    #             },
    #             "description": {
    #                 "type": "string",
    #                 "description": "New description of the event"
    #             },
    #             "start_datetime": {
    #                 "type": "string",
    #                 "description": "New start date and time of the event in ISO 8601 format"
    #             },
    #             "end_datetime": {
    #                 "type": "string",
    #                 "description": "New end date and time of the event in ISO 8601 format"
    #             },
    #             "timezone": {
    #                 "type": "string",
    #                 "description": "New timezone of the event"
    #             },
    #             "repeat": {
    #                 "type": "string",
    #                 "description": "New repeat frequency of the event (never, everyday, every_week, every_month)",
    #                 "enum": ["never", "everyday", "every_week", "every_month"]
    #             },
    #             "reminder": {
    #                 "type": "string",
    #                 "description": "New reminder time before the event (e.g., 15 minutes). The format is '<number> <unit>' where unit can be minutes, hours, days, or weeks.",
    #             },
    #             "method": {
    #                 "type": "string",
    #                 "description": "New reminder method (e.g., popup, email)",
    #                 "enum": ["popup", "email"]
    #             }
    #         },
    #         "required": ["summary", "date"],
    #         "additionalProperties": False,
    #     }
    # },
    # {
    #   "type": "function",
    #   "name": "delete_event",
    #     "description": "Delete a calendar event identified by summary and date.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "summary": {
    #                 "type": "string",
    #                 "description": "Summary of the event to be deleted"
    #             },
    #             "date": {
    #                 "type": "string",
    #                 "description": "Date of the event to be deleted in YYYY-MM-DD format"
    #             }
    #         },
    #         "required": ["summary", "date"],
    #         "additionalProperties": False,
    #     } 
    # },
    {
        "type": "function",
        "name": "save_list",
        "description": "Save a note with specified title and item list.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the note"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of items in the note"
                }
            },
            "required": ["title", "items"],
            "additionalProperties": False,
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "add_reminders",
        "description": "Add a reminder with specified title and time.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the note"
                },
                "time": {
                    "type": "string",
                    "description": "Time of the reminder in format",
                    "enum": ["today", "this week", "next week", "this month"]
                }
            },
            "required": ["title", "time"],
            "additionalProperties": False,
        },
        "strict": True
    },
    # {
    #     "type": "function",
    #     "name": "find_events",
    #     "description": "Find calendar events by date/time and optional title keywords.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "start_datetime": { "type": "string" },
    #             "end_datetime": { "type": "string" },
    #             "timezone": { "type": "string" },
    #             "query": {
    #                 "type": "string",
    #                 "description": "Optional meeting title or keywords"
    #             }
    #         },
    #         "required": ["start_datetime", "end_datetime", "timezone"],
    #         "additionalProperties": False
    #     },
    #     # "strict": False
    # },
    {
        "type": "function",
        "name": "add_meal",
        "description": "Add meal to the meal tracker by date, time, meal type, title, meal description, and calories.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": { "type": "string", "description": "Date in YYYY-MM-DD format" },
                "time": { "type": "string", "description": "Time in HH:MM format " },
                "meal_type": { "type": "string", "enum": ["breakfast", "lunch", "dinner"] },
                "title": { "type": "string" },
                "description": { "type": "string" },
                "calories": { "type": "number" }
            },
            "required": ["date", "time", "meal_type", "title", "description", "calories"],
            "additionalProperties": False
        },
        "strict": False
    },
    # {
    #     "type": "function",
    #     "name": "delete_meal",
    #     "description": "Delete meal from the meal tracker by date, meal type, and title.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "date": { "type": "string", "description": "Date in YYYY-MM-DD format" },
    #             "meal_type": { "type": "string", "enum": ["breakfast", "lunch", "dinner"] },
    #             "title": { "type": "string" }
    #         },
    #         "required": ["date", "meal_type", "title"],
    #         "additionalProperties": False
    #     },
    #     "strict": False
    # },
    # {
    #     "type": "function",
    #     "name": "update_meal",
    #     "description": "Update meal in the meal tracker by date, meal type, and title with new details.",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "date": { "type": "string", "description": "Date in YYYY-MM-DD format" },
    #             "meal_type": { "type": "string", "enum": ["breakfast", "lunch", "dinner"] },
    #             "title": { "type": "string" },
    #             "new_date": { "type": "string", "description": "New date in YYYY-MM-DD format" },
    #             "new_time": { "type": "string", "description": "New time in HH:MM format" },
    #             "new_meal_type": { "type": "string", "enum": ["breakfast", "lunch", "dinner"] },
    #             "new_title": { "type": "string" },
    #             "new_description": { "type": "string" },
    #             "new_calories": { "type": "number" }
    #         },
    #         "required": ["date", "meal_type", "title"],
    #         "additionalProperties": False
    #     },
    #     "strict": False
    # },
    {
        "type": "function",
        "name": "add_recipe",
        "description": "Add recipe to the meal tracker by recipe name, meal type, cooking time, description, and ratings.",
        "parameters": {
            "type": "object",
            "properties": {
                "recipe_name": { "type": "string", "description": "Name of the recipe" },
                "meal_type": { "type": "string", "enum": ["breakfast", "lunch", "dinner"] },
                "cooking_time": { "type": "number", "description": "Cooking time in minutes" },
                "description": { "type": "string" },
                "ratings": { "type": "number","description": "Ratings of the recipe out of 5" }
            },
            "required": ["recipe_name", "meal_type", "cooking_time", "description", "ratings"],
            "additionalProperties": False
        },
        "strict": False
    }
]


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str

app = FastAPI()
openai_client = OpenAI(api_key=OPENAI_API_KEY)

@app.post("/chat")
def chat(request: ChatRequest):
    sessions = load_sessions()
    session_id = get_or_create_session(sessions, request.session_id)

    conversation_text = ""
    for m in sessions[session_id]:
        conversation_text += f"User: {m['user_message']}\nAI: {m['ai_message']}\n"
    conversation_text += f"User: {request.message}\nAI:"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    system_prompt = f"""You are a smart AI assistant.
                You can chat normally with the user.
                Current server date & time: {now}
                
                If the user wants to know about their calendar events, then use the 'find_events' tool. Ask for date/time range and optional title keywords if not provided.
                
                If the user wants to schedule a meeting but does not provide all 
                required details (summary, description, start_datetime, end_datetime, timezone, repeat, reminder, method) — ask follow-up questions. 
                
                VALID timezone examples:
                - Asia/Dhaka (Bangladesh)
                - Asia/Kolkata (India)
                - Europe/London (UK)
                - America/New_York (USA)
                - America/Los_Angeles (USA)
                
                In their scheduling time if you find any existing events during that time, inform the user and ask for a different time.
                
                After gathering all necessary information, use the 'schedule_event' tool 
                to schedule the meeting.
                
                If the user gives an important point like "remind me", 
                "note this", "save this", "remember this", treat it as a note 
                and call save_note.

                Only call the tool when all information is ready.
                Do NOT guess missing details.
                """

    response = openai_client.responses.create(
        model="gpt-4.1-2025-04-14",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": conversation_text}
        ],
        tools=tools
    )
    
    output = response.output_text
    
    meals = []
    lists = []
    reminders = []
    events = []
    recipes = []
    
    tool_call = None
    for item in response.output:
        if item.type == "function_call":
            tool_call = item
            break

    if tool_call:
        tool_name = tool_call.name
        tool_args = json.loads(tool_call.arguments)

        if tool_name == "schedule_event":
            # existing_events = find_events(tool_args["start_datetime"], tool_args["end_datetime"], tool_args["timezone"])
            # if existing_events["count"] > 0:
            #     events_list = "\n".join(
            #         [f"- {e['summary']} from {e['start']} to {e['end']}" for e in existing_events["events"]]
            #     )
            #     # print(events_list)
            #     result  = f"There are already events scheduled during this time:\n{events_list}\nPlease choose a different time."
            # else:
                result = schedule_event(
                    summary=tool_args["summary"],
                    description=tool_args["description"],
                    start_datetime=tool_args["start_datetime"],
                    end_datetime=tool_args["end_datetime"],
                    timezone=tool_args["timezone"],
                    repeat=tool_args.get("repeat" , "never"),
                    reminder=tool_args.get("reminder", "15 minutes"),
                    method=tool_args.get("method", "popup")
                )
                print("Event scheduled:", result)
                # result = scheduled_event["event"]
                events.append(result["event"])
                    
        # elif tool_name == "find_events":
        #     result = find_events(tool_args["start_datetime"], tool_args["end_datetime"], tool_args["timezone"])
            
        # elif tool_name == "update_event":
        #     result = update_event(
        #         summary=tool_args["summary"],
        #         date=tool_args["date"],
        #         new_summary=tool_args.get("new_summary"),
        #         description=tool_args.get("description"),
        #         start_datetime=tool_args.get("start_datetime"),
        #         end_datetime=tool_args.get("end_datetime"),
        #         timezone=tool_args.get("timezone"),
        #         repeat=tool_args.get("repeat"),
        #         reminder=tool_args.get("reminder"),
        #         method=tool_args.get("method")
        #     )
        #     # if result["status"] == "success":
        #     #     events.append(result["event"])
        
        # elif tool_name == "delete_event":
        #     result = delete_event(
        #         summary=tool_args["summary"],
        #         date=tool_args["date"]
        #     )
                       
        elif tool_name == "save_list":
            result = save_list(
                title=tool_args["title"],
                items=tool_args["items"]
            )
            lists.append(result["list"])
            
        elif tool_name == "add_meal":
            result = add_meal(
                date=tool_args["date"],
                time=tool_args["time"],
                meal_type=tool_args["meal_type"],
                title=tool_args["title"],
                description=tool_args["description"],
                calories=tool_args["calories"]
            )
            meals.append(result["meal"])
            # print("Meal added:", result)
        
        # elif tool_name == "delete_meal":
        #     result = delete_meal(
        #         date=tool_args["date"],
        #         meal_type=tool_args["meal_type"],
        #         title=tool_args["title"]
        #     )
            
        # elif tool_name == "update_meal":
        #     result = update_meal(
        #         date=tool_args["date"],
        #         meal_type=tool_args["meal_type"],
        #         title=tool_args["title"],
        #         new_date=tool_args.get("new_date"),
        #         new_time=tool_args.get("new_time"),
        #         new_meal_type=tool_args.get("new_meal_type"),
        #         new_title=tool_args.get("new_title"),
        #         new_description=tool_args.get("new_description"),
        #         new_calories=tool_args.get("new_calories")
        #     )
        #     # if result["meal"] :
        #     #     meals.append(result["meal"])
        
        #     # print(meal_list)
            
        elif tool_name == "add_recipe":
            result = add_recipe(
                recipe_name=tool_args["recipe_name"],
                meal_type=tool_args["meal_type"],
                cooking_time=tool_args["cooking_time"],
                description=tool_args["description"],
                ratings=tool_args["ratings"]
            )
            recipes.append(result["recipe"])
            # print("Recipe added:", result)       
         
        elif tool_name == "add_reminders":
            result = add_reminders(
                title=tool_args["title"],
                time=tool_args["time"]
            )
            reminders.append(result["reminder"])
               
        final_response = openai_client.responses.create(
            model="gpt-4.1-2025-04-14",
            # input=f"Action completed: {result}"
            input=[
                {"role": "system", "content": """Never mention the tool call or action in your response to the user. If any conflict in event or meeting scheduling, just only say please choose a different time. never mention that 'you will provide free times or something'. 
                never tell user that you can update or delete anything. Just only show the results that you have done."""},
                {"role": "user", "content": f"Action completed: {result}"}
            ],
        )
        
        output = output + "\n" + final_response.output_text 
            
        # print(note_storage_list)
        
    conversation_entry = {
        "user_message": request.message,
        "ai_message": output,
    }
    
    sessions[session_id].append(conversation_entry)
    save_sessions(sessions)
    
    # return {
    #     "session_id": session_id,
    #     "response": output
    # }
    
    return build_response(
        session_id=session_id,
        ai_message=output,
        meals=meals,
        lists=lists,
        reminders=reminders,
        events=events,
        recipes=recipes
)

from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from datetime import datetime
from zoneinfo import ZoneInfo  
from dotenv import dotenv_values
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from utils.helpers import to_rfc3339, create_event, load_sessions, save_sessions, get_or_create_session
from utils.google_calender_auth import get_credentials

env_vars = dotenv_values(".env")
OPENAI_API_KEY = env_vars.get("OPENAI_API_KEY")

note_storage_list = []

def find_events(start_datetime: str, end_datetime: str, timezone: str):
    try:
        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)

        start_rfc3339 = to_rfc3339(start_datetime, timezone)
        end_rfc3339 = to_rfc3339(end_datetime, timezone)
        events_result = service.events().list(
            calendarId="primary",
            timeMin=start_rfc3339,
            timeMax=end_rfc3339,
            # q=query,
            singleEvents=True,
            orderBy="startTime",
            timeZone=timezone
        ).execute()

        events = events_result.get("items", [])
        # print(f"Found {len(events)} events.")
        # print(events)

        return {
            "status": "success",
            "count": len(events),
            "events": [
                {
                    "event_id": e["id"],
                    "summary": e.get("summary"),
                    "start": e["start"].get("dateTime"),
                    "end": e["end"].get("dateTime")
                }
                for e in events
            ]
        }

    except HttpError as error:
        return {"status": "error", "error": str(error)}

def schedule_meeting(summary:str, description:str, start_datetime:str, end_datetime:str, timezone:str):
    try:
        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)
        meeting=create_event(service, summary=summary, description=description, start_datetime=start_datetime, end_datetime=end_datetime, timezone=timezone)
        return {"status": "Meeting scheduled successfully", "message": meeting}
    except Exception as e:
        return {"status": "Error scheduling meeting", "error": str(e)}

def save_note(content: str):
    note = {
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    note_storage_list.append(note)
    return {"status": "Note saved successfully", "note": note}

tools = [
    {
        "type": "function",
        "name": "schedule_meeting",
        "description": "Schedule a meeting with specified summary, description, start_datetime, end_datetime, and timezone.",
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
                }
            },
            "required": ["summary", "description", "start_datetime", "end_datetime", "timezone"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "save_note",
        "description": "Save a note with specified content and tags.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Content of the note"
                }
            },
            "required": ["content"],
            "additionalProperties": False,
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "find_events",
        "description": "Find calendar events by date/time and optional title keywords.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_datetime": { "type": "string" },
                "end_datetime": { "type": "string" },
                "timezone": { "type": "string" },
                "query": {
                    "type": "string",
                    "description": "Optional meeting title or keywords"
                }
            },
            "required": ["start_datetime", "end_datetime", "timezone"],
            "additionalProperties": False
        },
        # "strict": False
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
                required details (summary, description, start_datetime, end_datetime, timezone) — ask follow-up questions. 
                
                VALID timezone examples:
                - Asia/Dhaka (Bangladesh)
                - Asia/Kolkata (India)
                - Europe/London (UK)
                - America/New_York (USA)
                - America/Los_Angeles (USA)
                
                In their scheduling time if you find any existing events during that time, inform the user and ask for a different time.
                
                After gathering all necessary information, use the 'schedule_meeting' tool 
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
    
    tool_call = None
    for item in response.output:
        if item.type == "function_call":
            tool_call = item
            break

    if tool_call:
        tool_name = tool_call.name
        tool_args = json.loads(tool_call.arguments)

        if tool_name == "schedule_meeting":
            existing_events = find_events(tool_args["start_datetime"], tool_args["end_datetime"], tool_args["timezone"])
            if existing_events["count"] > 0:
                events_list = "\n".join(
                    [f"- {e['summary']} from {e['start']} to {e['end']}" for e in existing_events["events"]]
                )
                # print(events_list)
                result  = f"There are already events scheduled during this time:\n{events_list}\nPlease choose a different time."
            else:
                    
                scheduled_meeting = schedule_meeting(
                    summary=tool_args["summary"],
                    description=tool_args["description"],
                    start_datetime=tool_args["start_datetime"],
                    end_datetime=tool_args["end_datetime"],
                    timezone=tool_args["timezone"]
                )
                result = scheduled_meeting["message"]
                    
        elif tool_name == "find_events":
            result = find_events(tool_args["start_datetime"], tool_args["end_datetime"], tool_args["timezone"])
            
        elif tool_name == "save_note":
            result = save_note(
                content=tool_args["content"]
            )
            
        final_response = openai_client.responses.create(
            model="gpt-4.1-2025-04-14",
            input=f"Action completed: {result}"
        )
        
        output = output + "\n" + final_response.output_text 
            
        # print(note_storage_list)
    
    conversation_entry = {
        "user_message": request.message,
        "ai_message": output,
    }
    
    sessions[session_id].append(conversation_entry)
    save_sessions(sessions)
    
    return {
        "session_id": session_id,
        "response": output
    }
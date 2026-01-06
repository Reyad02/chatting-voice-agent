from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from datetime import datetime
from dotenv import dotenv_values
import json
import uuid
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]

env_vars = dotenv_values(".env")
OPENAI_API_KEY = env_vars.get("OPENAI_API_KEY")

schedule_meeting_list = []
note_storage_list = []

SESSIONS_FILE = "chat_sessions.json"

def get_credentials():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    print("Google Calendar credentials obtained.")
    return creds

def create_event(service, summary, description, start_datetime, end_datetime, timezone):
    try: 
        print("Creating event on Google Calendar...")
        event = {
            'summary': summary,
            'description': description,
            'colorId': '6',
            'start': {
                'dateTime': start_datetime,
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_datetime,
                'timeZone': timezone,
            }
        }
    
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {created_event.get('htmlLink')}")
        return created_event
    except HttpError as error:
        print(f"An error occurred: {error}")


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

def schedule_meeting(summary:str, description:str, start_datetime:str, end_datetime:str, timezone:str):
    try:
        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)
        meeting=create_event(service, summary=summary, description=description, start_datetime=start_datetime, end_datetime=end_datetime, timezone=timezone)
        # meeting = {
        #     "date": date,
        #     "time": time,
        #     "title": title,
        # }
        # schedule_meeting_list.append(meeting)
        return {"status": "Meeting scheduled successfully", "meeting": meeting}
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
                
                If the user wants to schedule a meeting but does not provide all 
                required details (summary, description, start_datetime, end_datetime, timezone) — ask follow-up questions. After 
                gathering all necessary information, use the 'schedule_meeting' tool 
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
            result = schedule_meeting(
                summary=tool_args["summary"],
                description=tool_args["description"],
                start_datetime=tool_args["start_datetime"],
                end_datetime=tool_args["end_datetime"],
                timezone=tool_args["timezone"]
            )
            
        elif tool_name == "save_note":
            result = save_note(
                content=tool_args["content"]
            )
            
        final_response = openai_client.responses.create(
            model="gpt-4.1-2025-04-14",
            input=f"Action completed: {result}"
        )
        
        output = output + "\n" + final_response.output_text 
            
        print(schedule_meeting_list)
        print(note_storage_list)
    
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
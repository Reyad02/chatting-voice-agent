from logging import getLogger
from pathlib import Path
from datetime import datetime
import autogen
from autogen.agentchat.realtime_agent import RealtimeAgent, WebSocketAudioAdapter
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import dotenv_values
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from utils.helpers import to_rfc3339
from utils.google_calender_auth import get_credentials


# def find_events(start_datetime: str, end_datetime: str, timezone: str, query: str | None = None):
#     try:
#         creds = get_credentials()
#         service = build("calendar", "v3", credentials=creds)

#         print(start_datetime, end_datetime, timezone, query)
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
#         print(f"Found {len(events)} events.")
#         print(events)

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

# def create_event(service, summary, description, start_datetime, end_datetime, timezone):
#     try: 
#         print("Creating event on Google Calendar...")
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
#         print(f"Event created: {created_event.get('htmlLink')}")
#         return created_event
#     except HttpError as error:
#         print(f"An error occurred: {error}")


env_vars = dotenv_values(".env")
OPENAI_API_KEY = env_vars.get("OPENAI_API_KEY")

# print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")

realtime_config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    file_location=Path(__file__).parent,
    filter_dict={
        "tags": ["gpt-4o-mini-realtime"],
    }
)

for config in realtime_config_list:
    config["voice"] = "echo"
    config["api_key"] = OPENAI_API_KEY 

# Voice options:
    # alloy
    # ash
    # ballad
    # coral
    # echo
    # fable
    # nova
    # onyx
    # sage
    # shimmer

# print({
#     "realtime_config_list": realtime_config_list
# })

realtime_llm_config = {
    "timeout": 900,
    "config_list": realtime_config_list,
    "temperature": 0.8,
}

app = FastAPI()

schedule_meeting_list = []
note_storage_list = []

app = FastAPI()

@app.get("/", response_class=JSONResponse)
async def index_page() -> dict[str, str]:
    return {"message": "WebSocket Audio Stream Server is running!"}

app.mount(
    "/static", StaticFiles(directory="static"), name="static"
)

templates = Jinja2Templates(directory="templates")

@app.get("/start-chat/", response_class=HTMLResponse)
async def start_chat(request: Request) -> HTMLResponse:
    """Endpoint to return the HTML page for audio chat."""
    port = request.url.port
    return templates.TemplateResponse("chat.html", {"request": request, "port": port})


@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket) -> None:
    """Handle WebSocket connections providing audio stream and OpenAI."""
    await websocket.accept()

    logger = getLogger("uvicorn.error")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")


    audio_adapter = WebSocketAudioAdapter(websocket, logger=logger)
    system_prompt = f"""You are a smart AI assistant. Your name is Breya.
                You can chat normally with the user.
                Current server date & time: {now}
                
                User will share their emotions, feelings, daily activities, and thoughts with you through voice messages.
                You need to be a good listener and provide empathetic responses.
                Based on the user's input, you can suggest activities, coping strategies, or just be there to listen.
                Your goal is to support the user emotionally and mentally.
                """
    # system_prompt = "You are a smart AI assistant.
    #             You can chat normally with the user.
    #             Current server date & time: {now}
                
    #             If the user wants to schedule a meeting but does not provide all 
    #             required details (summary, description, start_datetime, end_datetime, timezone) — ask follow-up questions. 
                
    #             VALID timezone examples:
    #             - Asia/Dhaka (Bangladesh)
    #             - Europe/London (UK)
    #             - America/New_York (USA)
                
    #             After gathering all necessary information, use the 'schedule_meeting' tool 
    #             to schedule the meeting.
                
    #             If the user gives an important point like "remind me", 
    #             "note this", "save this", "remember this", treat it as a note 
    #             and call save_note.

    #             Only call the tool when all information is ready.
    #             Do NOT guess missing details.
    #             "
    realtime_agent = RealtimeAgent(
        name="Assistant Bot",
        system_message=system_prompt,
        llm_config=realtime_llm_config,
        audio_adapter=audio_adapter,
        logger=logger,
    )

    # @realtime_agent.register_realtime_function(
    #     name="schedule_meeting", description=" schedule a meeting in google calendar with time, date, and title"
    # )
    # def schedule_meeting(summary:str, description:str, start_datetime:str, end_datetime:str, timezone:str) -> str:
    #     logger.info("<-- Calling schedule_meeting function -->")
    #     creds = get_credentials()
    #     service = build("calendar", "v3", credentials=creds) 
    #     existing_events = find_events(start_datetime, end_datetime, timezone)
    #     if existing_events["count"] > 0:
    #         events_list = "\n".join(
    #             [f"- {e['summary']} from {e['start']} to {e['end']}" for e in existing_events["events"]]
    #         )
    #         return f"There are already events scheduled during this time:\n{events_list}\nPlease choose a different time."
    #     meeting = create_event(service, summary=summary, description=description, start_datetime=start_datetime, end_datetime=end_datetime, timezone=timezone)
    #     logger.info(f"<-- Calling schedule_meeting function for {summary} {start_datetime} {end_datetime} -->")
    #     return f"Meeting scheduled successfully. {meeting.get('htmlLink')}"

    # @realtime_agent.register_realtime_function(
    #     name="save_note", description="Save a note with specified content and tags."
    # )
    # def save_note(content: str, tags: list) -> str:
    #     note = {
    #         "content": content,
    #         "tags": tags
    #     }
    #     note_storage_list.append(note)
    #     logger.info(f"<-- Calling save_note function with content: {content} and tags: {tags} -->")
    #     return "Note saved successfully."
   
    await realtime_agent.run()

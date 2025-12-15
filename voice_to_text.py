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
    system_prompt = f"""You are a smart AI assistant.
                You can chat normally with the user.
                Current server date & time: {now}
                
                If the user wants to schedule a meeting but does not provide all 
                required details (date, time, title) — ask follow-up questions. After 
                gathering all necessary information, use the 'schedule_meeting' tool 
                to schedule the meeting.
                
                If the user gives an important point like "remind me", 
                "note this", "save this", "remember this", treat it as a note 
                and call save_note.

                Only call the tool when all information is ready.
                Do NOT guess missing details.
                """
    realtime_agent = RealtimeAgent(
        name="Assistant Bot",
        system_message=system_prompt,
        llm_config=realtime_llm_config,
        audio_adapter=audio_adapter,
        logger=logger,
    )

    @realtime_agent.register_realtime_function(
        name="schedule_meeting", description=" schedule a meeting in google calendar with time, date, and title"
    )
    def schedule_meeting(date: str, time: str, title: str) -> str:
        logger.info("<-- Calling get_weather function -->")
        meeting = {
            "date": date,
            "time": time,
            "title": title
        }
        schedule_meeting_list.append(meeting)
        logger.info(f"<-- Calling schedule_meeting function for {date} {time} {title} -->")
        return "Meeting scheduled successfully."

    @realtime_agent.register_realtime_function(
        name="save_note", description="Save a note with specified content and tags."
    )
    def save_note(content: str, tags: list) -> str:
        note = {
            "content": content,
            "tags": tags
        }
        note_storage_list.append(note)
        logger.info(f"<-- Calling save_note function with content: {content} and tags: {tags} -->")
        return "Note saved successfully."
    await realtime_agent.run()

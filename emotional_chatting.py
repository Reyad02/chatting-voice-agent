from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from datetime import datetime
from dotenv import dotenv_values
import json
import uuid
import os

env_vars = dotenv_values(".env")
OPENAI_API_KEY = env_vars.get("OPENAI_API_KEY")

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str

app = FastAPI()
openai_client = OpenAI(api_key=OPENAI_API_KEY)

SESSIONS_FILE = "emotional_chat.json"

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

@app.post("/chat")
def chat(request: ChatRequest):
    sessions = load_sessions()
    session_id = get_or_create_session(sessions, request.session_id)

    conversation_text = ""
    for m in sessions[session_id]:
        conversation_text += f"User: {m['user_message']}\nAI: {m['ai_message']}\n"
    conversation_text += f"User: {request.message}\nAI:"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    system_prompt = f"""You are a smart AI assistant. Your name is Breya.
                You can chat normally with the user.
                Current server date & time: {now}
                
                Based on the user message, emotion you  need to respond accordingly.
                If the user seems sad, respond with empathy and encouragement.
                If the user seems happy, share in their joy and positivity.
                If the user seems anxious, provide calming advice and reassurance.
                Your goal is to support the user emotionally and mentally.
                """

    
    response = openai_client.responses.create(
        model="gpt-5.2",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": conversation_text}
        ],
    )
    
    output = response.output_text
    
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
    
    
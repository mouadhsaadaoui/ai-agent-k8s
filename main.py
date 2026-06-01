from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import requests
from typing import Dict, List

app = FastAPI()

OLLAMA_URL = "http://ollama-service:11434"
SAFE_COMMANDS = {
    "get pods": ["kubectl", "get", "pods", "-n", "ai-platform"],
    "get services": ["kubectl", "get", "services", "-n", "ai-platform"],
    "get deployments": ["kubectl", "get", "deployments", "-n", "ai-platform"],
    "get nodes": ["kubectl", "get", "nodes"],
}
def execute_kubectl(command: str):

    cmd = SAFE_COMMANDS.get(command)

    if not cmd:
        return {
            "error": "Command not allowed"
        }

    try:
        result = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            text=True
        )

        return {
            "output": result
        }

    except subprocess.CalledProcessError as e:
        return {
            "error": e.output
        }
# ---------------------------
# MEMORY STORE (simple MVP)
# ---------------------------
memory: Dict[str, List[dict]] = {}

# ---------------------------
# REQUEST MODEL
# ---------------------------
class ChatRequest(BaseModel):
    session_id: str
    message: str

# ---------------------------
# MEMORY FUNCTIONS
# ---------------------------
def get_history(session_id: str):
    return memory.get(session_id, [])

def save_message(session_id: str, role: str, message: str):
    if session_id not in memory:
        memory[session_id] = []

    memory[session_id].append({
        "role": role,
        "message": message
    })

# ---------------------------
# AGENT ROUTER (CORE LOGIC)
# ---------------------------
def agent_router(message: str):
    msg = message.lower()

    if "history" in msg:
        return "memory"

    if (
   	 "pods" in msg or
    	"services" in msg or
    	"deployments" in msg or
    	"nodes" in msg
    ):
    	return "tool"

    return "llm"

# ---------------------------
# LLM CALL
# ---------------------------
def call_llm(prompt: str):
    return requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": "tinyllama",
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    ).json()

# ---------------------------
# MAIN CHAT ENDPOINT
# ---------------------------
@app.post("/chat")
def chat(req: ChatRequest):

    # 1. Save user message
    save_message(req.session_id, "user", req.message)

    # 2. Decide action
    action = agent_router(req.message)

    # -----------------------
    # MEMORY MODE
    # -----------------------
    if action == "memory":
        history = get_history(req.session_id)
        return {
            "type": "memory",
            "history": history
        }

    # -----------------------
    # TOOL MODE (placeholder)
    # -----------------------
    if action == "tool":

    user_msg = req.message.lower()

    selected_command = None

    if "pods" in user_msg:
        selected_command = "get pods"

    elif "services" in user_msg:
        selected_command = "get services"

    elif "deployments" in user_msg:
        selected_command = "get deployments"

    elif "nodes" in user_msg:
        selected_command = "get nodes"

    result = execute_kubectl(selected_command)

    save_message(req.session_id, "assistant", str(result))

    return {
        "type": "tool",
        "command": selected_command,
        "result": result
    }
    # -----------------------
    # LLM MODE
    # -----------------------
    history = get_history(req.session_id)

    # build context (VERY IMPORTANT STEP)
    context = "\n".join(
        [f"{m['role']}: {m['message']}" for m in history]
    )

    final_prompt = f"""
You are an AI assistant.

Conversation history:
{context}

User:
{req.message}
"""

    llm_response = call_llm(final_prompt)

    answer = llm_response.get("response", "")

    save_message(req.session_id, "assistant", answer)

    return {
        "type": "llm",
        "response": answer,
        "session_id": req.session_id
    }

# ---------------------------
# HEALTH CHECK
# ---------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

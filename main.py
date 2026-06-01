from fastapi import FastAPI
from pydantic import BaseModel
import requests
from typing import Dict, List


app = FastAPI()

OLLAMA_URL = "http://ollama-service.ai-platform.svc.cluster.local:11434"

# ---------------------------
# KUBERNETES CLIENT INIT
# ---------------------------



# ---------------------------
# MEMORY STORE
# ---------------------------
memory: Dict[str, List[dict]] = {}


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
# KUBERNETES FUNCTIONS (NO KUBECTL)
# ---------------------------


# ---------------------------
# ROUTER
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
    try:
        return requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "tinyllama",
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        ).json()
    except Exception as e:
        return {"error": str(e)}


# ---------------------------
# CHAT ENDPOINT
# ---------------------------
@app.post("/chat")
def chat(req: ChatRequest):

    # save user message
    save_message(req.session_id, "user", req.message)

    action = agent_router(req.message)

    # -----------------------
    # MEMORY MODE
    # -----------------------
    if action == "memory":
        return {
            "type": "memory",
            "history": get_history(req.session_id)
        }

    # -----------------------
    # TOOL MODE
    # -----------------------
    # -----------------------
    if action == "tool":

    	user_msg = req.message.lower()

    	if "pods" in user_msg:
            selected_command = "get pods"

    	elif "services" in user_msg:
            selected_command = "get services"

    	elif "deployments" in user_msg:
            selected_command = "get deployments"

    	elif "nodes" in user_msg:
            selected_command = "get nodes"

    	else:
            return {
                "type": "tool",
                "error": "No valid kubernetes resource matched"
        }

    	tool_response = requests.post(
            "http://ai-tool-agent.ai-platform.svc.cluster.local:8000/execute",
            json={"command": selected_command}
    	)

    	result = tool_response.json()

    	save_message(req.session_id, "assistant", str(result))

    	return {
        "type": "tool",
        "result": result
    }
    # -----------------------
    # LLM MODE
    # -----------------------
    history = get_history(req.session_id)

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

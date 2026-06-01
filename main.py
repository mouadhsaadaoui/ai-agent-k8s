from fastapi import FastAPI
from pydantic import BaseModel
import requests
import redis
import json
from typing import Dict, List

app = FastAPI()

# ---------------------------
# SERVICES
# ---------------------------
OLLAMA_URL = "http://ollama-service.ai-platform.svc.cluster.local:11434"
TOOL_AGENT_URL = "http://ai-tool-agent.ai-platform.svc.cluster.local:8000/execute"

# Redis (memory service)
r = redis.Redis(
    host="redis.ai-platform.svc.cluster.local",
    port=6379,
    decode_responses=True
)

# ---------------------------
# REQUEST MODEL
# ---------------------------
class ChatRequest(BaseModel):
    session_id: str
    message: str


# ---------------------------
# MEMORY (REDIS)
# ---------------------------
def get_history(session_id: str):
    key = f"chat:{session_id}"
    data = r.lrange(key, 0, -1)
    return [json.loads(x) for x in data]


def save_message(session_id: str, role: str, message: str):
    key = f"chat:{session_id}"
    r.rpush(key, json.dumps({
        "role": role,
        "message": message
    }))


# ---------------------------
# ROUTER
# ---------------------------
def agent_router(message: str):
    msg = message.lower()

    if "history" in msg:
        return "memory"

    if any(x in msg for x in ["pods", "services", "deployments", "nodes"]):
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
# TOOL CALL
# ---------------------------
def call_tool(command: str):
    return requests.post(
        TOOL_AGENT_URL,
        json={"command": command},
        timeout=30
    ).json()


# ---------------------------
# TOOL DECISION
# ---------------------------
def extract_command(message: str):
    msg = message.lower()

    if "pods" in msg:
        return "get pods"
    if "services" in msg:
        return "get services"
    if "deployments" in msg:
        return "get deployments"
    if "nodes" in msg:
        return "get nodes"

    return None


# ---------------------------
# CHAT ENDPOINT
# ---------------------------
@app.post("/chat")
def chat(req: ChatRequest):

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
    if action == "tool":

        command = extract_command(req.message)

        if not command:
            return {
                "type": "tool",
                "error": "No valid kubernetes command matched"
            }

        tool_result = call_tool(command)

        # final reasoning step (important for "agentic" feel)
        history = get_history(req.session_id)

        context = "\n".join(
            [f"{m['role']}: {m['message']}" for m in history]
        )

        final_prompt = f"""
You are an AI system managing Kubernetes.

Conversation:
{context}

Tool output:
{tool_result}

User request:
{req.message}

Give a clear final answer.
"""

        final = call_llm(final_prompt)
        answer = final.get("response", "")

        save_message(req.session_id, "assistant", answer)

        return {
            "type": "agent-chain",
            "tool_used": command,
            "response": answer
        }

    # -----------------------
    # LLM MODE
    # -----------------------
    history = get_history(req.session_id)

    context = "\n".join(
        [f"{m['role']}: {m['message']}" for m in history]
    )

    prompt = f"""
You are an AI assistant.

Conversation:
{context}

User:
{req.message}
"""

    llm_response = call_llm(prompt)
    answer = llm_response.get("response", "")

    save_message(req.session_id, "assistant", answer)

    return {
        "type": "llm",
        "response": answer
    }


# ---------------------------
# HEALTH
# ---------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

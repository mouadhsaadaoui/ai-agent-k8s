from fastapi import FastAPI
from pydantic import BaseModel
import requests
from typing import Dict, List

from kubernetes import client, config

app = FastAPI()

OLLAMA_URL = "http://ollama-service.ai-platform.svc.cluster.local:11434"

# ---------------------------
# KUBERNETES CLIENT INIT
# ---------------------------
config.load_incluster_config()

v1 = client.CoreV1Api()
apps = client.AppsV1Api()


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
def get_pods():
    pods = v1.list_namespaced_pod(namespace="ai-platform")
    return [p.metadata.name for p in pods.items]


def get_services():
    svcs = v1.list_namespaced_service(namespace="ai-platform")
    return [s.metadata.name for s in svcs.items]


def get_deployments():
    deps = apps.list_namespaced_deployment(namespace="ai-platform")
    return [d.metadata.name for d in deps.items]


def get_nodes():
    nodes = v1.list_node()
    return [n.metadata.name for n in nodes.items]


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
    if action == "tool":

        user_msg = req.message.lower()

        if "pods" in user_msg:
            result = get_pods()

        elif "services" in user_msg:
            result = get_services()

        elif "deployments" in user_msg:
            result = get_deployments()

        elif "nodes" in user_msg:
            result = get_nodes()

        else:
            return {
                "type": "tool",
                "error": "No valid kubernetes resource matched"
            }

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

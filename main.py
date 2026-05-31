from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

app = FastAPI(
    title="AI Agent API",
    description="Kubernetes AI Agent using Ollama",
    version="1.0.0"
)

OLLAMA_URL = "http://ollama-service.ai-platform.svc.cluster.local:11434"


class ChatRequest(BaseModel):
    prompt: str


@app.post("/chat")
def chat(request: ChatRequest):

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "tinyllama",
                "prompt": request.prompt,
                "stream": False
            },
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

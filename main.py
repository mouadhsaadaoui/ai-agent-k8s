from fastapi import FastAPI
import requests

app = FastAPI()

OLLAMA_URL = "http://ollama-service.ai-platform.svc.cluster.local:11434"

@app.post("/chat")
def chat(prompt: str):
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": "tinyllama",
            "prompt": prompt,
            "stream": False
        }
    )
    return response.json()

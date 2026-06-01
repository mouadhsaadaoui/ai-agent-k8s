from fastapi import FastAPI
from kubernetes import client, config
from pydantic import BaseModel

app = FastAPI()

# load cluster config (inside Kubernetes)
config.load_incluster_config()

v1 = client.CoreV1Api()
apps = client.AppsV1Api()


class CommandRequest(BaseModel):
    command: str


@app.post("/execute")
def execute(req: CommandRequest):

    cmd = req.command

    if cmd == "get pods":
        pods = v1.list_namespaced_pod(namespace="ai-platform")
        return [p.metadata.name for p in pods.items]

    elif cmd == "get services":
        svcs = v1.list_namespaced_service(namespace="ai-platform")
        return [s.metadata.name for s in svcs.items]

    elif cmd == "get deployments":
        deps = apps.list_namespaced_deployment(namespace="ai-platform")
        return [d.metadata.name for d in deps.items]

    elif cmd == "get nodes":
        nodes = v1.list_node()
        return [n.metadata.name for n in nodes.items]

    return {"error": "command not allowed"}

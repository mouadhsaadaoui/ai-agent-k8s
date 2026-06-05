# ai-agent-k8s
A Kubernetes-native AI agent combining tool-use orchestration, local LLM inference, secure Kubernetes tool execution, and automated CI/CD pipelines.

---

## Project Overview

This project demonstrates how an AI agent can be deployed and operated using modern cloud-native infrastructure.

The platform integrates:
* Single-agent architecture with tool routing
* Local LLM inference using Ollama
* Kubernetes-native tool execution
* Redis-based conversational memory
* Automated CI/CD with GitHub Actions

The goal of the project is to bridge DevOps, Kubernetes, and AI infrastructure engineering.

---

# Architecture

```
User
 ↓
AI-Agent (FastAPI Orchestrator)
 ↓
Intent Router
 ├── Tool-Agent → Kubernetes operations
 ├── Ollama    → LLM inference
 └── Redis     → Session memory
```

---

# Core Components

## AI-Agent
Central orchestrator responsible for:
* Request routing
* Conversation handling
* LLM interaction
* Tool invocation based on intent

---

## Tool-Agent
Dedicated service responsible for:
* Kubernetes API operations
* Cluster resource queries
* Secure RBAC-based execution

Examples:
* Get pods
* Get services
* Get deployments
* Get nodes

---

## Ollama
Local LLM inference service running inside Kubernetes.

Used for:
* Natural language understanding
* Response generation
* AI reasoning workflows

---

## Redis
Provides short-term memory and session persistence for conversations.

---

# Kubernetes Infrastructure

The platform is fully deployed on Kubernetes using:
* Deployments
* Services
* RBAC
* Persistent Volumes
* Horizontal Pod Autoscaler (HPA)
* Namespaces

---

# CI/CD Pipeline

The project includes a fully automated CI/CD workflow using GitHub Actions and a self-hosted runner connected to the private cluster.

### Pipeline Flow
1. Push code to GitHub
2. GitHub Actions starts pipeline
3. Docker image is built
4. Image pushed to GitHub Container Registry (GHCR)
5. Kubernetes deployment updated automatically

---

# Security
* RBAC-controlled service accounts
* Internal service-to-service communication
* Kubernetes API access instead of direct kubectl execution
* Isolated namespace deployment

---

# Example Request

```bash
curl -X POST http://<SERVICE-IP>:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user1",
    "message": "show me pods"
  }'
```

---

# Technologies Used
* Kubernetes
* Docker
* FastAPI
* Python
* Redis
* Ollama
* GitHub Actions
* GHCR
* Kubernetes Python Client

---

# Future Improvements
* LLM-based intelligent routing
* Long-term vector memory
* Streaming AI responses
* Observability with Prometheus & Grafana
* Multi-agent architecture with specialized sub-agents

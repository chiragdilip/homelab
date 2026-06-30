#!/usr/bin/env python3
"""HTTP API for the agent. Run: uvicorn server:app --host 0.0.0.0 --port 8080

POST /ask  {"q": "are all nodes ready?", "approve": false}
  -> {"answer": "...", "actions": [{"tool": "...", "args": {...}}]}

Mutating tools (write_file, run_shell) only execute when "approve": true.
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from agent import Agent

app = FastAPI(title="Homelab Agent")
agent = Agent()


class Ask(BaseModel):
    q: str
    approve: bool = False


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": agent.cfg["model"], "ollama": agent.cfg["ollama_host"]}


@app.post("/ask")
def ask(body: Ask) -> dict:
    return agent.run(body.q, approve=body.approve)

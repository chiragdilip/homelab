#!/usr/bin/env python3
"""Local homelab agent — runs entirely on the Jetson against a local Ollama server.

The loop:
  1. Send conversation + tool schemas to the local model.
  2. If the model asks to call tools, run them locally and feed results back.
  3. Repeat until the model returns a plain answer (or max_iterations is hit).

No data leaves the machine: the model is local (Ollama) and the tools only touch
the local homelab.
"""
from __future__ import annotations

import sys
from pathlib import Path

import ollama
import yaml

import tools

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def dispatch_tool(name: str, args: dict, cfg: dict) -> str:
    """Run a requested tool, enforcing the safety policy."""
    impl = tools.TOOL_IMPLS.get(name)
    if impl is None:
        return f"ERROR: unknown tool '{name}'."
    try:
        return impl(**(args or {}))
    except TypeError as e:
        return f"ERROR: bad arguments for {name}: {e}"


def run_once(client: ollama.Client, cfg: dict, messages: list[dict]) -> str:
    """Drive one user request to completion, handling tool calls."""
    for _ in range(cfg.get("max_iterations", 8)):
        resp = client.chat(
            model=cfg["model"],
            messages=messages,
            tools=tools.TOOL_SCHEMAS,
            options={"temperature": cfg.get("temperature", 0.1)},
        )
        msg = resp["message"]
        messages.append(msg)

        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            return msg.get("content", "").strip()

        # Execute each requested tool and append its result.
        for call in tool_calls:
            fn = call["function"]
            name = fn["name"]
            args = fn.get("arguments", {}) or {}
            print(f"  \033[2m↪ calling {name}({args})\033[0m", file=sys.stderr)
            result = dispatch_tool(name, args, cfg)
            messages.append({"role": "tool", "name": name, "content": result})

    return "(stopped: hit max tool-call iterations)"


def main() -> None:
    cfg = load_config()
    client = ollama.Client(host=cfg["ollama_host"])
    messages: list[dict] = [{"role": "system", "content": cfg["system_prompt"]}]

    print(f"Local homelab agent — model={cfg['model']} host={cfg['ollama_host']}")
    print("Type a request (or 'exit'). All processing is local.\n")

    while True:
        try:
            user = input("you › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user.lower() in {"exit", "quit"}:
            break
        if not user:
            continue
        messages.append({"role": "user", "content": user})
        answer = run_once(client, cfg, messages)
        print(f"\nagent › {answer}\n")


if __name__ == "__main__":
    main()

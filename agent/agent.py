#!/usr/bin/env python3
"""Core agent: a local tool-calling loop over Ollama, plus a CLI.

The Agent class is reused by server.py (HTTP API). Mutating tools (write_file,
run_shell) are gated: they need allow_mutations + either approval (API) or an
interactive y/N confirm (CLI).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Optional

import ollama
import yaml

import tools

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    # Env overrides — handy in-cluster.
    cfg["ollama_host"] = os.environ.get("OLLAMA_HOST", cfg["ollama_host"])
    cfg["model"] = os.environ.get("AGENT_MODEL", cfg["model"])
    if os.environ.get("AGENT_WORKSPACE"):
        cfg.setdefault("filesystem", {})["workspace"] = os.environ["AGENT_WORKSPACE"]
    return cfg


class Agent:
    def __init__(self, cfg: Optional[dict] = None):
        self.cfg = cfg or load_config()
        tools.init(self.cfg)
        self.client = ollama.Client(host=self.cfg["ollama_host"])

    def _dispatch(self, name: str, args: dict, approve: bool,
                  confirm: Optional[Callable[[str, dict], bool]]) -> str:
        impl = tools.TOOL_IMPLS.get(name)
        if impl is None:
            return f"ERROR: unknown tool '{name}'."
        if name in tools.MUTATING:
            safety = self.cfg.get("safety", {})
            if not safety.get("allow_mutations", False):
                return f"BLOCKED: mutations disabled; cannot run '{name}'."
            if safety.get("require_approval", True) and not approve:
                if confirm is not None and confirm(name, args):
                    pass  # interactively approved
                else:
                    return (f"BLOCKED: '{name}' needs approval. "
                            f"Re-send with approve=true to execute.")
        try:
            return impl(**(args or {}))
        except TypeError as e:
            return f"ERROR: bad arguments for {name}: {e}"
        except Exception as e:  # noqa: BLE001 - surface tool errors to the model
            return f"ERROR: {name} failed: {e}"

    def run(self, question: str, approve: bool = False,
            confirm: Optional[Callable[[str, dict], bool]] = None) -> dict:
        messages = [
            {"role": "system", "content": self.cfg["system_prompt"]},
            {"role": "user", "content": question},
        ]
        actions: list[dict] = []
        for _ in range(self.cfg.get("max_iterations", 10)):
            resp = self.client.chat(
                model=self.cfg["model"], messages=messages,
                tools=tools.TOOL_SCHEMAS,
                options={
                    "temperature": self.cfg.get("temperature", 0.1),
                    "num_ctx": self.cfg.get("num_ctx", 2048),
                },
            )
            msg = resp["message"]
            messages.append(msg)
            calls = msg.get("tool_calls")
            if not calls:
                return {"answer": (msg.get("content") or "").strip(), "actions": actions}
            for call in calls:
                fn = call["function"]
                name, args = fn["name"], (fn.get("arguments") or {})
                result = self._dispatch(name, args, approve, confirm)
                actions.append({"tool": name, "args": args})
                messages.append({"role": "tool", "name": name, "content": result})
        return {"answer": "(stopped: hit max iterations)", "actions": actions}


def _cli_confirm(name: str, args: dict) -> bool:
    ans = input(f"  ⚠ approve {name}({args})? [y/N] ").strip().lower()
    return ans == "y"


def main() -> None:
    agent = Agent()
    print(f"Full homelab agent — model={agent.cfg['model']} host={agent.cfg['ollama_host']}")
    print("Type a request ('exit' to quit). Mutations will prompt for approval.\n")
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
        result = agent.run(user, confirm=_cli_confirm)
        if result["actions"]:
            names = ", ".join(a["tool"] for a in result["actions"])
            print(f"  \033[2m↪ tools used: {names}\033[0m", file=sys.stderr)
        print(f"\nagent › {result['answer']}\n")


if __name__ == "__main__":
    main()

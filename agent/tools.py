"""Tools the agent can call. All run locally against the homelab.

Each tool has:
  - a JSON schema (so the model knows how to call it), collected in TOOL_SCHEMAS
  - a Python implementation, registered in TOOL_IMPLS

Read-only tools run freely. The single mutating path (run_shell) is gated by an
allowlist + interactive confirmation in agent.py.
"""
from __future__ import annotations

import shutil
import subprocess


def _run(cmd: list[str], timeout: int = 30) -> str:
    """Run a local command and return combined stdout/stderr as text."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return out.strip() or f"(no output, exit code {proc.returncode})"
    except FileNotFoundError:
        return f"ERROR: '{cmd[0]}' not found on this host."
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {timeout}s."


# --- Read-only tool implementations ----------------------------------------

def get_nodes() -> str:
    """List k3s cluster nodes with status, roles and IPs."""
    return _run(["kubectl", "get", "nodes", "-o", "wide"])


def get_pods(namespace: str = "all") -> str:
    """List pods. namespace='all' shows every namespace."""
    if namespace == "all":
        return _run(["kubectl", "get", "pods", "-A"])
    return _run(["kubectl", "get", "pods", "-n", namespace])


def node_metrics() -> str:
    """Show live CPU/memory usage per node (needs metrics-server)."""
    return _run(["kubectl", "top", "nodes"])


def describe(kind: str, name: str, namespace: str = "default") -> str:
    """Describe a Kubernetes resource (read-only): kind e.g. pod/node/deployment."""
    return _run(["kubectl", "describe", kind, name, "-n", namespace])


def ping_host(host: str) -> str:
    """Ping a homelab host to check reachability (5 packets)."""
    if not shutil.which("ping"):
        return "ERROR: ping not available."
    return _run(["ping", "-c", "5", host], timeout=20)


# --- Tool registry ----------------------------------------------------------

TOOL_IMPLS = {
    "get_nodes": get_nodes,
    "get_pods": get_pods,
    "node_metrics": node_metrics,
    "describe": describe,
    "ping_host": ping_host,
}

# OpenAI/Ollama-style function schemas the model sees.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_nodes",
            "description": "List k3s cluster nodes with status, roles, and IPs.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pods",
            "description": "List pods, optionally for one namespace (default: all namespaces).",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Namespace to list, or 'all' for every namespace.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "node_metrics",
            "description": "Live CPU/memory usage per node.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe",
            "description": "Describe a Kubernetes resource (read-only).",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "description": "e.g. pod, node, deployment"},
                    "name": {"type": "string"},
                    "namespace": {"type": "string", "description": "default: 'default'"},
                },
                "required": ["kind", "name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ping_host",
            "description": "Ping a homelab host (5 packets) to check reachability.",
            "parameters": {
                "type": "object",
                "properties": {"host": {"type": "string", "description": "hostname or IP"}},
                "required": ["host"],
            },
        },
    },
]

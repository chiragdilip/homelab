"""Tools the agent can call.

Categories:
  - cluster (read-only): get_nodes, get_pods, node_metrics, describe
  - network (read-only): ping_host
  - internet (read-only): web_search, web_fetch
  - filesystem: list_dir, read_file (read-only), write_file (MUTATING)
  - system: run_shell (MUTATING)

Mutating tools are listed in MUTATING and are gated by the Agent (approval +
allowlist). Filesystem access is confined to the configured workspace unless
allow_outside_workspace is set.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import requests

# Populated by Agent via init(); holds the loaded config dict.
_CFG: dict = {}


def init(cfg: dict) -> None:
    global _CFG
    _CFG = cfg
    Path(_workspace()).mkdir(parents=True, exist_ok=True)


# --- helpers ---------------------------------------------------------------

def _workspace() -> Path:
    return Path(_CFG.get("filesystem", {}).get("workspace", "/workspace"))


def _resolve(path: str) -> Path:
    """Resolve a path, confining it to the workspace unless explicitly allowed."""
    base = _workspace().resolve()
    p = Path(path)
    p = (p if p.is_absolute() else base / p).resolve()
    if not _CFG.get("filesystem", {}).get("allow_outside_workspace", False):
        if p != base and base not in p.parents:
            raise ValueError(f"path '{p}' is outside the workspace '{base}'")
    return p


def _run(cmd: list[str], timeout: int = 30) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        out = (proc.stdout or "") + (proc.stderr or "")
        return out.strip() or f"(no output, exit code {proc.returncode})"
    except FileNotFoundError:
        return f"ERROR: '{cmd[0]}' not found."
    except subprocess.TimeoutExpired:
        return f"ERROR: timed out after {timeout}s."


# --- cluster (read-only) ---------------------------------------------------

def get_nodes() -> str:
    return _run(["kubectl", "get", "nodes", "-o", "wide"])


def get_pods(namespace: str = "all") -> str:
    if namespace == "all":
        return _run(["kubectl", "get", "pods", "-A"])
    return _run(["kubectl", "get", "pods", "-n", namespace])


def node_metrics() -> str:
    return _run(["kubectl", "top", "nodes"])


def describe(kind: str, name: str, namespace: str = "default") -> str:
    return _run(["kubectl", "describe", kind, name, "-n", namespace])


def ping_host(host: str) -> str:
    if not shutil.which("ping"):
        return "ERROR: ping not available."
    return _run(["ping", "-c", "5", host], timeout=20)


# --- internet (read-only) --------------------------------------------------

def web_search(query: str, max_results: int = 5) -> str:
    if not _CFG.get("internet", {}).get("enabled", False):
        return "BLOCKED: internet access disabled in config."
    try:
        from ddgs import DDGS
    except ImportError:
        return "ERROR: ddgs not installed."
    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        return f"ERROR: search failed: {e}"
    if not hits:
        return "(no results)"
    return "\n".join(f"- {h.get('title')} — {h.get('href')}\n  {h.get('body')}" for h in hits)


def web_fetch(url: str) -> str:
    if not _CFG.get("internet", {}).get("enabled", False):
        return "BLOCKED: internet access disabled in config."
    limit = int(_CFG.get("internet", {}).get("fetch_max_chars", 6000))
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "homelab-agent"})
        r.raise_for_status()
    except Exception as e:
        return f"ERROR: fetch failed: {e}"
    text = r.text
    return text[:limit] + ("\n…(truncated)" if len(text) > limit else "")


# --- filesystem ------------------------------------------------------------

def list_dir(path: str = ".") -> str:
    try:
        p = _resolve(path)
    except ValueError as e:
        return f"BLOCKED: {e}"
    if not p.exists():
        return f"ERROR: '{p}' does not exist."
    return "\n".join(sorted(
        f"{'d' if c.is_dir() else '-'} {c.name}" for c in p.iterdir()
    )) or "(empty)"


def read_file(path: str) -> str:
    try:
        p = _resolve(path)
    except ValueError as e:
        return f"BLOCKED: {e}"
    if not p.is_file():
        return f"ERROR: '{p}' is not a file."
    return p.read_text(errors="replace")[:20000]


def write_file(path: str, content: str) -> str:
    """MUTATING — gated by the Agent."""
    try:
        p = _resolve(path)
    except ValueError as e:
        return f"BLOCKED: {e}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"wrote {len(content)} bytes to {p}"


# --- system ----------------------------------------------------------------

def run_shell(command: str) -> str:
    """MUTATING — gated by the Agent (approval + allowlist)."""
    allowlist = _CFG.get("shell_allowlist", [])
    if allowlist and not any(command.strip().startswith(pfx) for pfx in allowlist):
        return f"BLOCKED: '{command}' is not in shell_allowlist."
    return _run(["bash", "-lc", command], timeout=60)


# --- registry --------------------------------------------------------------

MUTATING = {"write_file", "run_shell"}

TOOL_IMPLS = {
    "get_nodes": get_nodes,
    "get_pods": get_pods,
    "node_metrics": node_metrics,
    "describe": describe,
    "ping_host": ping_host,
    "web_search": web_search,
    "web_fetch": web_fetch,
    "list_dir": list_dir,
    "read_file": read_file,
    "write_file": write_file,
    "run_shell": run_shell,
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_nodes",
        "description": "List k3s cluster nodes with status, roles, and IPs.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_pods",
        "description": "List pods, optionally for one namespace (default all).",
        "parameters": {"type": "object", "properties": {
            "namespace": {"type": "string", "description": "namespace or 'all'"}}}}},
    {"type": "function", "function": {
        "name": "node_metrics",
        "description": "Live CPU/memory per node.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "describe",
        "description": "Describe a Kubernetes resource (read-only).",
        "parameters": {"type": "object", "properties": {
            "kind": {"type": "string"}, "name": {"type": "string"},
            "namespace": {"type": "string"}}, "required": ["kind", "name"]}}},
    {"type": "function", "function": {
        "name": "ping_host",
        "description": "Ping a homelab host (5 packets).",
        "parameters": {"type": "object", "properties": {
            "host": {"type": "string"}}, "required": ["host"]}}},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Search the internet (DuckDuckGo). Returns titles, URLs, snippets.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "web_fetch",
        "description": "Fetch the contents of a URL (truncated).",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "list_dir",
        "description": "List a directory within the workspace.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "default '.'"}}}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a file within the workspace.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Write a file within the workspace. MUTATING — requires approval.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "run_shell",
        "description": "Run a shell command on the Jetson. MUTATING — requires approval; subject to allowlist.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"}}, "required": ["command"]}}},
]

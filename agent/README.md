# Local homelab agent (Jetson Orin Nano)

A fully local, tool-using agent. The LLM runs on the Jetson via **Ollama** (GPU),
the agent loop runs on the Jetson, and its tools query your own k3s cluster.
**No data leaves your network** — no external API, no telemetry.

```
Ollama (local LLM, GPU) ──tool-calling──> agent.py ──> kubectl / ping (local homelab)
```

## Prerequisites on the Jetson

1. **JetPack 6 / Ubuntu 22.04** flashed and on the network.
2. **Ollama on the GPU.** Two options — the containerized one is recommended on
   Jetson (optimized CUDA build, reproducible).

   **Option A — optimized container (recommended).** Uses dusty-nv's Jetson image.
   This board is JetPack 6.1+ → L4T **r36.4.x**, so the tag is `r36.4.0`:
   ```bash
   # NVIDIA runtime must be active in Docker (JetPack provides nvidia-container-toolkit).
   docker run -d --runtime nvidia --name ollama --restart unless-stopped \
     -v ollama:/root/.ollama -p 11434:11434 dustynv/ollama:r36.4.0
   ```
   (Or via jetson-containers, which auto-selects the tag:
   `jetson-containers run -d --name ollama -v ollama:/root/.ollama -p 11434:11434 $(autotag ollama)`)

   The container publishes the API on `11434`, which is what `config.yaml` already
   points at — so the agent connects unchanged.

   **Option B — native install** (installer detects JetPack and builds with CUDA):
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```
3. **A model** (good at tool-calling; ~4.7 GB):
   ```bash
   # container:
   docker exec -it ollama ollama pull qwen2.5:7b   # or qwen2.5:3b if RAM is tight
   # native:
   ollama pull qwen2.5:7b
   ```
4. **kubectl + kubeconfig** so the agent can see the cluster:
   ```bash
   sudo curl -L "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/arm64/kubectl" -o /usr/local/bin/kubectl
   sudo chmod +x /usr/local/bin/kubectl
   mkdir -p ~/.kube && scp root@192.168.2.19:/etc/rancher/k3s/k3s.yaml ~/.kube/config
   sed -i 's#127.0.0.1#192.168.2.19#' ~/.kube/config
   kubectl get nodes        # verify
   ```
5. **Python deps:**
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

## Run

```bash
python3 agent.py
```

Then ask things like:
- "Are all cluster nodes ready?"
- "Show me CPU and memory usage per node."
- "List pods in kube-system and tell me if any are not running."
- "Can the agent reach the Pi at 192.168.2.19?"

## Configuration — `config.yaml`

| Key | Meaning |
|-----|---------|
| `model` / `ollama_host` | which local model, and the local Ollama URL |
| `max_iterations`        | cap on tool-call loops per request (safety) |
| `temperature`           | low = deterministic (good for ops) |
| `allow_shell` / `shell_allowlist` | gate for any future mutating/shell tool |
| `system_prompt`         | the agent's persona/instructions |

## Adding tools

Edit `tools.py`: add a function, register it in `TOOL_IMPLS`, and add a matching
JSON schema to `TOOL_SCHEMAS`. Keep new tools read-only unless you wire them through
the confirmation/allowlist path.

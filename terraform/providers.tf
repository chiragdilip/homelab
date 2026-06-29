provider "proxmox" {
  endpoint = var.proxmox_endpoint
  # Use an API token (recommended). Format: "user@realm!token-id=uuid"
  api_token = var.proxmox_api_token
  insecure  = var.proxmox_insecure

  # SSH is required by bpg/proxmox for some operations (e.g. uploading files,
  # certain disk actions). It connects to the Proxmox node as root.
  ssh {
    agent    = true
    username = "root"
  }
}

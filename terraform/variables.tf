# ---------------------------------------------------------------------------
# Proxmox connection
# ---------------------------------------------------------------------------

variable "proxmox_endpoint" {
  description = "Proxmox API endpoint, e.g. https://192.168.1.10:8006/"
  type        = string
}

variable "proxmox_api_token" {
  description = "Proxmox API token in the form user@realm!token-id=uuid"
  type        = string
  sensitive   = true
}

variable "proxmox_insecure" {
  description = "Skip TLS verification (true for self-signed Proxmox certs)"
  type        = bool
  default     = true
}

variable "proxmox_node" {
  description = "Name of the Proxmox node to create the VMs on (e.g. pve)"
  type        = string
}

# ---------------------------------------------------------------------------
# VM template / image
# ---------------------------------------------------------------------------

variable "template_vm_id" {
  description = "VMID of the cloud-init template to clone the workers from"
  type        = number
}

variable "datastore_id" {
  description = "Datastore for VM disks (e.g. local-lvm)"
  type        = string
  default     = "local-lvm"
}

variable "network_bridge" {
  description = "Proxmox network bridge to attach the VMs to"
  type        = string
  default     = "vmbr0"
}

# ---------------------------------------------------------------------------
# Worker node sizing & identity
# ---------------------------------------------------------------------------

variable "worker_count" {
  description = "Number of k3s worker VMs to create"
  type        = number
  default     = 2
}

variable "worker_name_prefix" {
  description = "Hostname/name prefix for workers; index is appended (k3s-worker-1, ...)"
  type        = string
  default     = "k3s-worker"
}

variable "worker_vmid_base" {
  description = "First VMID; workers get worker_vmid_base + index (e.g. 201, 202)"
  type        = number
  default     = 200
}

variable "worker_cores" {
  description = "vCPU cores per worker"
  type        = number
  default     = 1
}

variable "worker_memory" {
  description = "RAM per worker in MB"
  type        = number
  default     = 4096
}

variable "worker_disk_size" {
  description = "Disk size per worker in GB"
  type        = number
  default     = 32
}

# ---------------------------------------------------------------------------
# Networking (cloud-init)
# ---------------------------------------------------------------------------

variable "worker_ip_base" {
  description = "Static IP CIDRs per worker, index-aligned with worker_count. Leave empty for DHCP."
  type        = list(string)
  default     = ["192.168.1.201/24", "192.168.1.202/24"]
}

variable "gateway" {
  description = "Default gateway for the workers"
  type        = string
  default     = "192.168.1.1"
}

variable "ci_user" {
  description = "cloud-init default user created on the workers"
  type        = string
  default     = "ubuntu"
}

variable "ssh_public_keys" {
  description = "SSH public keys to inject via cloud-init (for Ansible access)"
  type        = list(string)
  default     = []
}

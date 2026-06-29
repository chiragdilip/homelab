# k3s worker VMs on Proxmox.
# The control plane lives on the Pi 5 (DietPi) and is configured by Ansible,
# so it is intentionally NOT managed here.

resource "proxmox_virtual_environment_vm" "worker" {
  count = var.worker_count

  name      = "${var.worker_name_prefix}-${count.index + 1}"
  node_name = var.proxmox_node
  vm_id     = var.worker_vmid_base + count.index + 1

  description = "k3s worker node ${count.index + 1} (managed by Terraform)"
  tags        = ["terraform", "k3s", "worker"]

  # Clone from the cloud-init template.
  clone {
    vm_id = var.template_vm_id
    full  = true
  }

  agent {
    enabled = true
  }

  cpu {
    cores = var.worker_cores
    type  = "host"
  }

  memory {
    dedicated = var.worker_memory
  }

  disk {
    datastore_id = var.datastore_id
    interface    = "scsi0"
    size         = var.worker_disk_size
  }

  network_device {
    bridge = var.network_bridge
  }

  initialization {
    datastore_id = var.datastore_id

    # Merged with the user_account-generated user-data; installs qemu-guest-agent.
    vendor_data_file_id = proxmox_virtual_environment_file.worker_vendor_data.id

    # Static IPs get no DHCP-provided DNS, so we must set resolvers explicitly.
    dns {
      servers = var.dns_servers
    }

    ip_config {
      ipv4 {
        address = length(var.worker_ip_base) > count.index ? var.worker_ip_base[count.index] : "dhcp"
        gateway = length(var.worker_ip_base) > count.index ? var.gateway : null
      }
    }

    user_account {
      username = var.ci_user
      keys     = var.ssh_public_keys
    }
  }

  # Let Proxmox-side changes to the cloud image not force replacement.
  lifecycle {
    ignore_changes = [
      clone,
    ]
  }
}

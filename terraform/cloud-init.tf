# Custom cloud-init "vendor-data" for the workers.
#
# This is the VENDOR-DATA slot, which cloud-init MERGES with the user-data that
# `user_account {}` (in main.tf) generates. So the ubuntu user, SSH key, IP and
# DNS stay intact — we only ADD package installation on top.
#
# Uploaded as a "snippet" to the `local` datastore. NOTE: the datastore must have
# the "Snippets" content type enabled (Datacenter -> Storage -> local -> Edit ->
# Content -> tick Snippets) or this upload fails.

resource "proxmox_virtual_environment_file" "worker_vendor_data" {
  content_type = "snippets"
  datastore_id = var.snippets_datastore
  node_name    = var.proxmox_node

  source_raw {
    file_name = "k3s-worker-vendor.yaml"
    data      = <<-EOT
      #cloud-config
      # Installs the QEMU guest agent so Proxmox/Terraform can read the VM's IP.
      # Without this, `apply` hangs at "Still creating..." waiting for the agent.
      packages:
        - qemu-guest-agent
      runcmd:
        - systemctl enable --now qemu-guest-agent
    EOT
  }
}

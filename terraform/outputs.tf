output "worker_names" {
  description = "Names of the created worker VMs"
  value       = proxmox_virtual_environment_vm.worker[*].name
}

output "worker_vm_ids" {
  description = "Proxmox VMIDs of the workers"
  value       = proxmox_virtual_environment_vm.worker[*].vm_id
}

output "worker_ipv4_addresses" {
  description = "IPv4 addresses reported by the guest agent (needs qemu-guest-agent running)"
  value       = proxmox_virtual_environment_vm.worker[*].ipv4_addresses
}

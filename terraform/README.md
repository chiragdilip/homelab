# Terraform — k3s worker VMs on Proxmox

Provisions the **2 k3s worker nodes** as VMs on Proxmox, cloned from a cloud-init
template. The **control plane** runs on the Pi 5 (DietPi) and is handled by Ansible,
not Terraform.

Provider: [`bpg/proxmox`](https://registry.terraform.io/providers/bpg/proxmox/latest/docs).

## Prerequisites

### 1. Proxmox API token

On the Proxmox host (or UI → Datacenter → Permissions → API Tokens):

```bash
pveum user add terraform@pve
pveum aclmod / -user terraform@pve -role Administrator   # tighten later
pveum user token add terraform@pve terraform --privsep 0
```

Copy the resulting `user@realm!token-id=uuid` into `proxmox_api_token`.

### 2. Cloud-init template

Create a template VM once; Terraform clones it. Example with Ubuntu cloud image:

```bash
cd /var/lib/vz/template
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
qm create 9000 --name ubuntu-2404-cloud --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk 9000 noble-server-cloudimg-amd64.img local-lvm
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
qm set 9000 --ide2 local-lvm:cloudinit
qm set 9000 --boot c --bootdisk scsi0 --serial0 socket --vga serial0
qm set 9000 --agent enabled=1
qm template 9000
```

Put `9000` (or your VMID) into `template_vm_id`.

## Usage

```bash
cp terraform.tfvars.example terraform.tfvars   # then edit
terraform init
terraform plan
terraform apply
```

Get the worker IPs (qemu-guest-agent must be running in the guest) for the next stage:

```bash
terraform output worker_ipv4_addresses
```

These feed into the Ansible inventory to install k3s agents that join the Pi control plane.

## Files

| File | Purpose |
|------|---------|
| `versions.tf`   | Terraform & provider version constraints |
| `providers.tf`  | Proxmox provider (API token + SSH) config |
| `variables.tf`  | All inputs |
| `main.tf`       | Worker VM resources (`count = worker_count`) |
| `outputs.tf`    | Worker names, VMIDs, IPs |
| `terraform.tfvars.example` | Template for your local `terraform.tfvars` |

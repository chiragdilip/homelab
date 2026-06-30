# Ansible — install k3s on the cluster

Configures the existing machines (Pi control plane + Terraform-built worker VMs)
and installs k3s: a **server** on the Pi, **agents** on the workers.

Ansible is agentless (SSH only) and stateless — re-running is safe (idempotent).

## Prerequisites

- Ansible installed on your Mac: `brew install ansible`
- SSH key `~/.ssh/id_homelab` works for the `ubuntu` user on both workers
  (installed by the Terraform/cloud-init stage).
- SSH access to the Pi as the user set in `inventory/hosts.yml`.
- Fill in the Pi's `ansible_host` and `ansible_user` in `inventory/hosts.yml`.

## Usage

Run everything from inside this directory (so `ansible.cfg` is picked up):

```bash
cd ansible

# 1. Confirm Ansible can reach every node
ansible all -m ping

# 2. Install k3s (server on Pi, agents on workers)
ansible-playbook playbooks/install-k3s.yml
```

## Verify the cluster

On the Pi (control plane):

```bash
sudo k3s kubectl get nodes -o wide
```

You should see 3 Ready nodes: `k3s-control`, `k3s-worker-1`, `k3s-worker-2`.

## Layout

| Path | Purpose |
|------|---------|
| `ansible.cfg`               | Project config (inventory path, SSH key, become) |
| `inventory/hosts.yml`            | The nodes, grouped into `control_plane` / `workers` |
| `inventory/group_vars/all.yml`   | Shared vars (k3s version, API URL) — must sit next to the inventory to auto-load |
| `playbooks/install-k3s.yml` | Two plays: server, then agents join |

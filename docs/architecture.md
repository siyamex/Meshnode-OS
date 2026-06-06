# meshnode OS — Architecture

## Overview

meshnode OS turns a set of ordinary Linux PCs into a single application
platform using three layered technologies stacked on top of Debian 12:

```
┌──────────────────────────────────────────────────────────────────┐
│  User traffic  (HTTP/HTTPS)                                       │
└────────────────────────────┬─────────────────────────────────────┘
                             │ port 80 / 443
               ┌─────────────▼──────────────┐
               │   Traefik v3  (global mode) │  ← one per node
               │   health-checks + routing   │
               └─────────────┬──────────────┘
                             │ overlay network: meshnet
    ┌────────────────────────┼────────────────────────┐
    │                        │                        │
┌───▼────┐             ┌─────▼──┐             ┌───────▼──┐
│ node-1 │             │ node-2 │   …         │  node-N  │
│ Docker │◄──ZeroTier──│ Docker │             │  Docker  │
└───┬────┘    mesh     └───┬────┘             └─────┬────┘
    └────────────────────── Docker Swarm ───────────┘
                    (control plane + scheduling)
                              +
                    Portainer CE  (web GUI, manager node)
                              +
                    meshnode-wizard  (first-boot, port 8088)
```

---

## Component roles

### ZeroTier (mesh VPN)
- Creates a flat L3 network across nodes even when they're on different ISPs
  or behind NAT — no port forwarding required.
- Each node gets a stable mesh IP (e.g. `10.x.x.x`) that Docker Swarm and
  Traefik use to communicate.
- The wizard joins the network and detects the mesh IP before cluster formation.
- Docker Swarm's `--advertise-addr` and `swarm join` always use the mesh IP,
  never the LAN IP, so nodes can move networks without breaking the cluster.

### Docker Swarm
- The "brain" of the cluster: distributes service replicas across nodes,
  restarts failed containers, rebalances after a node comes back online.
- Overlay networks (`meshnet`) allow containers on different nodes to
  communicate as if they were on the same machine.
- `max_replicas_per_node: 1` on services ensures real cross-node redundancy.
- Manager nodes hold the cluster state (Raft consensus); workers run workloads.

### Traefik v3 (edge router)
- Runs in **global mode** (one instance on every node) so any node can accept
  inbound traffic.
- Discovers services automatically via Docker Swarm service labels:
  `traefik.enable=true` opts a service in.
- Health-checks every backend every 10 seconds; removes a dead replica from
  rotation within one check interval (~30 s worst-case failover).
- Dashboard available on port 8080 (restrict this on public networks).

### Portainer CE (web GUI)
- Runs on the manager node; the **Portainer agent** runs on every node.
- Agent → server communication happens over the `agent_network` overlay.
- Provides a UI for deploying stacks, viewing containers, checking logs,
  and monitoring cluster health — no CLI required.

### meshnode-wizard (first-boot)
- FastAPI app on port 8088.
- Runs once: on the live ISO, or once after a Calamares disk install.
- Guards itself with `ConditionPathExists=!/etc/meshnode/.firstboot-done`.
- Writes `/etc/meshnode/config.yaml` with hostname, interface, ZeroTier
  network ID, mesh IP, and cluster role.
- After `cluster/create` or `cluster/join`, writes the done flag and calls
  `systemctl disable meshnode-wizard.service`.

### Calamares (disk installer)
- Graphical Qt installer launched via `sudo start-installer`.
- Copies the live squashfs to the target disk, configures users, locale,
  keyboard, GRUB bootloader (BIOS + UEFI).
- A post-install `shellprocess` removes `.firstboot-done` from the installed
  system so the wizard runs exactly once on the first real boot.

---

## Data flow: cluster join

```
Node 1 (manager)                    Node 2 (worker)
──────────────────                  ──────────────────
1. Wizard runs
2. ZeroTier join ──────────────────── 1. Wizard runs
3. Swarm init                        2. ZeroTier join
   advertise-addr = mesh-IP1         3. Decode join code
4. Generate join code:                  token = SWMTKN-...
   base64({token, ip})                  ip    = mesh-IP1
5. Display join code              ──► 4. docker swarm join
                                         --token SWMTKN-...
                                         mesh-IP1:2377
                                      5. Node Ready ✓
```

---

## Network ports

| Port | Protocol | Service | Notes |
|------|----------|---------|-------|
| 80 | TCP | Traefik HTTP | User-facing traffic |
| 443 | TCP | Traefik HTTPS | TLS (Phase 7 stretch goal) |
| 8080 | TCP | Traefik dashboard | Restrict on public networks |
| 8088 | TCP | meshnode-wizard | First-boot only |
| 9000 | TCP | Portainer web GUI | Restrict on public networks |
| 2377 | TCP | Docker Swarm mgmt | Manager only, internal |
| 7946 | TCP+UDP | Docker Swarm gossip | Node-to-node, internal |
| 4789 | UDP | VXLAN overlay | Container networking |
| 9993 | UDP | ZeroTier | NAT traversal |

---

## Config files on each node

```
/etc/meshnode/
├── config.yaml           ← written by the wizard
│     hostname: node-1
│     interface: eth0
│     zerotier_network_id: 8056c2e21c000001
│     mesh_ip: 10.x.x.x
│     cluster_role: manager | worker
│     join_code: eyJ...    ← manager only
└── .firstboot-done       ← created after wizard completes
```

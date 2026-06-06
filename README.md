# meshnode OS

**Boot the ISO on each PC, join them once, and your website runs everywhere
with automatic failover — no Kubernetes PhD required.**

meshnode OS is a lightweight, installable Linux distribution (Debian 12 base)
that turns ordinary PCs — even on different networks — into a self-healing
Docker Swarm cluster managed from a web GUI.

---

## How it works

```
          Visitors
              |
    ┌─────────▼─────────┐
    │  Traefik  (edge)  │  health-checks + load-balances on port 80/443
    └────┬──────────────┘
         │  (runs on every node)
    ┌────▼────┐  ZeroTier mesh VPN  ┌────▼────┐
    │ node-1  │◄───────────────────►│ node-2  │
    │ Docker  │  (works across ISPs)│ Docker  │
    └─────────┘                     └─────────┘
           └──── Docker Swarm ────────┘
                 (schedules, restarts, rebalances)
                      +
               Portainer (web GUI)
```

**Boot → wizard → cluster → deploy → failover.** That's the whole flow.

---

## Quick start (build the ISO)

> Requires a Debian 12 or Ubuntu 22.04 host (or WSL2). See [docs/install.md](docs/install.md).

```bash
# Install build tools (once)
sudo apt install -y live-build debootstrap squashfs-tools xorriso \
    isolinux syslinux-common grub-pc-bin grub-efi-amd64-bin mtools

# Build
git clone https://github.com/siyamex/Meshnode-OS.git
cd Meshnode-OS
make iso        # produces meshnode-os-0.1.0.iso  (~10-20 min first run)
make test       # boot it in QEMU
```

---

## User journey (after booting the ISO)

| Step | Action |
|------|--------|
| 1 | Flash `meshnode-os-0.1.0.iso` to USB with [Balena Etcher](https://etcher.balena.io/) |
| 2 | Boot PC #1 → open `http://<ip>:8088` → set hostname, join ZeroTier, **Create cluster** |
| 3 | Copy the **join code** from the wizard's done screen |
| 4 | Boot PC #2 the same way → open its wizard → **Join existing cluster** → paste join code |
| 5 | Open **Portainer** at `http://<ip>:9000` — both nodes visible |
| 6 | Deploy the sample website: `sudo deploy-website` |
| 7 | Power off PC #1 → website still loads from PC #2 ✅ |
| — | To install permanently: `sudo start-installer` then `Ctrl+Alt+F7` |

---

## What's inside

| Layer | Technology |
|-------|-----------|
| Base OS | Debian 12 (Bookworm), x86-64 |
| Container runtime | Docker CE |
| Orchestrator | Docker Swarm |
| Mesh network | ZeroTier |
| Edge router | Traefik v3 |
| Web GUI | Portainer CE |
| Setup wizard | FastAPI + HTMX |
| Disk installer | Calamares |
| Boot splash | Plymouth (meshnode theme) |

---

## Build phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Repo scaffold + minimal bootable ISO | ✅ Done |
| 1 | Bake in Docker CE + ZeroTier | ✅ Done |
| 2 | First-boot setup wizard (4 steps) | ✅ Done |
| 3 | Cluster formation (Swarm init/join + join code) | ✅ Done |
| 4 | Auto-deploy Portainer CE + Traefik v3 | ✅ Done |
| 5 | Sample website + failover proof | ✅ Done |
| 6 | Calamares graphical disk installer | ✅ Done |
| 7 | Branding, finalized docs, v0.1.0 release | ✅ **Done — v0.1.0** |

---

## Docs

- [Building the ISO / WSL2 setup](docs/install.md)
- [Architecture deep-dive](docs/architecture.md)
- [Phase 5 failover test](docs/failover-test.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Full specification](SPEC.md)

---

## Stretch goals (post v1)

- HTTPS via Traefik + Let's Encrypt
- Self-hosted mesh controller (Headscale — no ZeroTier account needed)
- Database replication module (PostgreSQL / MariaDB Galera)
- 3-node quorum guidance to avoid split-brain
- ARM64 / Raspberry Pi image
- `curl … | sh` one-line installer for existing Linux machines

---

## License

MIT — see [LICENSE](LICENSE) if present, otherwise consider it open.
Built with [Claude Code](https://claude.ai/code).

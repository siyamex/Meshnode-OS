# meshnode OS

**Boot the ISO on each PC, join them once, and your website runs everywhere with automatic failover — no Kubernetes PhD required.**

meshnode OS is a lightweight Debian 12-based Linux distribution that turns ordinary PCs — even on different physical networks — into a single Docker Swarm cluster with automatic failover, managed entirely from a web GUI.

## Quick start

See [docs/install.md](docs/install.md) for full build-host requirements and step-by-step instructions.

```bash
# On a Debian/Ubuntu host (or WSL2):
make iso          # build meshnode-os-0.1.0.iso
make test         # boot it in QEMU
```

## How it works

1. Flash the ISO to a USB, boot PC #1, run the setup wizard.
2. Boot PC #2, join the cluster with the printed join code.
3. Deploy your app via Portainer — it runs on both nodes automatically.
4. Pull the power on PC #1 — the site keeps running from PC #2. Done.

## Project status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Repo scaffold + minimal bootable ISO | ✅ Done |
| 1 | Bake in Docker + ZeroTier | ✅ Done |
| 2 | First-boot wizard | ✅ Done |
| 3 | Cluster formation | ✅ In progress |
| 3 | Cluster formation | Pending |
| 4 | Auto-deploy Portainer + Traefik | Pending |
| 5 | Sample app + failover proof | Pending |
| 6 | Calamares disk installer | Pending |
| 7 | Branding + release | Pending |

See [SPEC.md](SPEC.md) for the full specification and [CHANGELOG.md](CHANGELOG.md) for change history.

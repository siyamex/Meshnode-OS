# Build Prompt — "meshnode OS" (a Linux-based clustered failover OS)

> **How to use this file:** Paste the whole thing into your coding agent
> (Claude Code, Cursor, Aider, etc.) as the opening message. Then say
> *"Start with Phase 0."* Work one phase at a time. After each phase, the agent
> should stop, show you how to test it, and wait for your "go" before the next.
> Keep this file in the repo as `SPEC.md` so the agent can re-read it anytime.

---

## ROLE & WORKING STYLE (instructions to the agent)

You are a senior Linux systems + DevOps engineer building a small, focused
operating system. Work like this:

- **Work in phases.** Complete one phase fully, prove it works, then stop and
  wait for my approval before starting the next.
- **Every phase must be testable.** End each phase with exact commands I can run
  to verify it, including how to boot/test in a VM.
- **Be decisive, but flag big forks.** Pick sensible defaults; only ask me when a
  choice is expensive to reverse.
- **Idempotent & re-runnable.** All setup scripts must be safe to run twice.
- **No secrets in the repo.** Use env files / first-boot prompts for anything secret.
- **Comment generously.** I am learning; explain non-obvious commands inline.
- **Keep a CHANGELOG.md and update SPEC.md** if we change decisions.

---

## 1. PROJECT VISION

Build **meshnode OS**: a lightweight Linux distribution that turns ordinary PCs —
even on *different physical networks* — into a single cluster that runs the same
app(s) on all of them with **automatic failover**. If one machine dies, the
others keep serving and users notice nothing. The whole thing is managed from a
**web GUI**, and new machines join by booting the ISO and answering a short
first-boot wizard.

**One-sentence pitch:** "Boot the ISO on each PC, join them once, and your
website runs everywhere with automatic failover — no Kubernetes PhD required."

This is NOT a hand-written kernel. It is a **custom Debian-based image** that
bundles proven open-source tools — exactly how Proxmox, CapRover and Umbrel work.

---

## 2. GOALS & NON-GOALS

**Goals**
- A bootable, installable ISO based on Debian 12 (Bookworm), x86-64.
- After install, machine is a ready "node": Docker + mesh networking present.
- A first-boot **web wizard** to set hostname, join the mesh, and form/join the cluster.
- Auto-deploy a web GUI (Portainer) and an edge router (Traefik) for failover.
- Deploy a sample website running one replica per node; survive a node going down.
- Clear docs so a non-expert can flash, boot, and cluster two PCs in < 30 min.

**Non-goals (v1)**
- No custom kernel or kernel modules.
- No multi-cloud, no auto-scaling, no billing.
- No built-in database replication UI (documented manually; stretch goal).
- ARM / Raspberry Pi support is a stretch goal, not v1.

---

## 3. TARGET USER EXPERIENCE (the story to build toward)

1. User downloads `meshnode-os.iso`, flashes it to a USB with Balena Etcher.
2. Boots PC #1 → graphical installer (Calamares) → installs to disk → reboots.
3. On first boot, a browser-accessible **setup wizard** appears (printed URL on
   the console, e.g. `http://<ip>:8088`). User: sets hostname, pastes a ZeroTier
   network ID, and chooses **"Create new cluster."**
4. Wizard finishes; it prints a **join code** and a GUI URL.
5. User boots PC #2 the same way, opens its wizard, chooses **"Join existing
   cluster,"** pastes the join code. Done.
6. User opens **Portainer GUI**, deploys their website (or the bundled sample).
7. User powers off PC #1 → website still loads from PC #2. ✅ Failover proven.

---

## 4. ARCHITECTURE

```
                 Visitors / domain name
                          |
                ┌─────────▼─────────┐
                │  Traefik  (edge)  │  health-checks + load-balances, port 80/443
                └─────────┬─────────┘
                          |  (runs on every node)
        ┌─────────────────┴─────────────────┐
        |                                    |
   ┌────▼────┐         ZeroTier         ┌────▼────┐
   │ node-1  │◄─────── mesh VPN ───────►│ node-2  │   (same app, 1 replica each)
   │ Docker  │   (works across nets)    │ Docker  │
   └────┬────┘                          └────┬────┘
        └──────────────┬────────────────────┘
                Docker Swarm  =  the "OS brain"
            (schedules apps, restarts/relocates on failure)
                          +
                 Portainer  =  web GUI
                          +
            meshnode-wizard = first-boot setup web app
```

---

## 5. TECHNOLOGY CHOICES (use these unless you hit a hard wall)

| Layer            | Choice                    | Why |
|------------------|---------------------------|-----|
| Base OS          | **Debian 12 (Bookworm)**  | Stable, minimal, great ISO tooling |
| ISO build tool   | **Debian `live-build`**   | Mature, well-documented custom ISOs |
| Graphical installer | **Calamares**          | Friendly install-to-disk on the live image |
| Container runtime| **Docker CE**             | Ubiquitous, simple |
| Orchestrator     | **Docker Swarm**          | Built into Docker; ideal for a few nodes |
| Mesh network     | **ZeroTier** (self-host option: Headscale/ZeroTier OSS) | Connects nodes across different networks with zero firewall config |
| Edge router      | **Traefik v3**            | Auto-discovers Swarm services, health-aware routing |
| Web GUI          | **Portainer CE**          | Mature cluster GUI, fast win |
| Setup wizard     | **FastAPI (Python) + plain HTML/HTMX** | Tiny, easy to template into the image |
| Config store     | `/etc/meshnode/` (YAML/env) | Single source of truth on each node |

> If `live-build` + Calamares proves painful, acceptable fallbacks are:
> `mkosi`, or a preseeded Debian `netinst`. Tell me before switching.

---

## 6. TARGET REPOSITORY STRUCTURE

```
meshnode-os/
├── SPEC.md                  # this document
├── README.md
├── CHANGELOG.md
├── Makefile                 # `make iso`, `make test`, `make clean`
├── build/
│   └── live-build/          # live-build config (auto/, config/)
│       ├── config/package-lists/meshnode.list.chroot
│       ├── config/includes.chroot/      # files baked into the image
│       └── config/hooks/                # build-time hooks (install docker, etc.)
├── wizard/                  # the first-boot setup web app
│   ├── app/                 # FastAPI app
│   ├── templates/
│   ├── static/
│   └── meshnode-wizard.service   # systemd unit
├── node/                    # runtime scripts baked into the OS
│   ├── meshnode-firstboot.sh
│   ├── join-mesh.sh
│   ├── cluster-init.sh
│   └── cluster-join.sh
├── stack/                   # Swarm stacks deployed after clustering
│   ├── portainer.yml
│   ├── traefik.yml
│   └── website-example.yml
└── docs/
    ├── install.md
    ├── architecture.md
    └── troubleshooting.md
```

> Reuse the existing `stack/portainer.yml`, `stack/traefik.yml`, and
> `stack/website-example.yml` from my earlier "meshnode" starter kit — they
> already work; adapt as needed.

---

## 7. BUILD PHASES (the heart of this — do them in order)

### Phase 0 — Repo + minimal bootable ISO
- Scaffold the repo above. Add `Makefile` with `make iso`.
- Use `live-build` to produce a **plain Debian 12 live ISO** (no extras yet).
- **Test:** `make iso` produces `meshnode-os.iso`; it boots in QEMU to a login.
- **Document** the build-host requirements (Debian/Ubuntu host, `live-build`,
  `qemu-system-x86`) in `docs/install.md`.

### Phase 1 — Bake in the runtime (Docker + ZeroTier)
- Build hooks install **Docker CE** and **ZeroTier** into the image.
- Services enabled but inert until configured.
- **Test:** boot ISO; `docker --version` and `zerotier-cli info` both work offline.

### Phase 2 — First-boot wizard (network + mesh)
- Build the **FastAPI wizard** at `wizard/`. On first boot a systemd unit starts
  it and prints its URL on the console (TTY message).
- Screens: (a) set hostname, (b) confirm/choose the network interface, (c) paste
  ZeroTier network ID and join, (d) show the node's mesh IP.
- Persist answers to `/etc/meshnode/config.yaml`.
- **Test:** in a VM, open the wizard from the host browser, join a real ZeroTier
  net, confirm a mesh IP appears.

### Phase 3 — Cluster formation
- Extend the wizard with a choice: **Create new cluster** or **Join existing**.
  - *Create*: run `docker swarm init --advertise-addr <mesh-ip>`, create the
    `meshnet` overlay network, and display a **join code** (the swarm worker token
    + manager mesh IP, base64-packed for easy copy/paste).
  - *Join*: accept a join code and run the corresponding `docker swarm join`.
- **Test:** two VMs on the same ZeroTier net; VM1 creates, VM2 joins;
  `docker node ls` on VM1 shows both nodes `Ready`.

### Phase 4 — Auto-deploy GUI + edge
- After a cluster is created, the wizard deploys `stack/portainer.yml` and
  `stack/traefik.yml`. Wizard's final screen links the Portainer URL.
- **Test:** open Portainer in browser; it shows both nodes.

### Phase 5 — Deploy a real app + prove failover
- Deploy `stack/website-example.yml`: `replicas: 2`, `max_replicas_per_node: 1`,
  Traefik labels for health-checked routing.
- **Test:** site loads via either node's IP. **Power off one VM** → site still
  loads. Power it back on → replica rebalances. This is the money shot — record it.

### Phase 6 — Calamares installer + persistence
- Add **Calamares** to the live image so users can install to disk.
- Ensure first-boot wizard runs once after install, not on every boot
  (flag file at `/etc/meshnode/.firstboot-done`).
- **Test:** install to a VM disk, reboot, wizard runs once, second reboot skips it.

### Phase 7 — Branding, docs, release
- Boot splash + wizard branding (name/logo placeholders OK).
- Finalize `README.md`, `docs/install.md`, `docs/troubleshooting.md`.
- `make iso` produces a versioned `meshnode-os-vX.Y.Z.iso`; tag a release.

---

## 8. KEY COMPONENT SPECS

**First-boot wizard (FastAPI)**
- Binds `0.0.0.0:8088`. Prints URL to TTY1 via the systemd unit / `/etc/issue`.
- Endpoints (suggested): `GET /` (status), `POST /hostname`, `POST /mesh/join`,
  `POST /cluster/create`, `POST /cluster/join`, `GET /done`.
- Reads/writes `/etc/meshnode/config.yaml`. Never stores the join token on disk
  in plaintext beyond what Swarm already keeps.
- Detects mesh IP from `zerotier-cli listnetworks` (parse the assigned addr).
- After `cluster/create` or `cluster/join` succeeds, write
  `/etc/meshnode/.firstboot-done`.

**systemd units**
- `meshnode-wizard.service` — runs the wizard until first-boot completes, then
  is disabled by the wizard.
- Ensure `docker.service` and `zerotier-one.service` are enabled at boot.

**Networking rules**
- Always use the **ZeroTier mesh IP** for `--advertise-addr` / join, never the LAN IP.
- Document the ZeroTier ports the user may need to allow if behind strict NAT.

---

## 9. CODING CONVENTIONS / CONSTRAINTS

- Bash: `set -euo pipefail`, functions, clear echo prefixes (`>>`, `!!`).
- Python: type hints, FastAPI, no heavyweight deps; one small `requirements.txt`.
- All runtime config under `/etc/meshnode/`. All logs to journald.
- Scripts must succeed if re-run (guard with checks/flags).
- The OS must fully function **offline after first boot** (no internet needed to
  keep the cluster running; only initial image pulls need internet).

---

## 10. TESTING STRATEGY

- **Build:** `make iso` on a Debian/Ubuntu host.
- **Single-node boot:** QEMU boots the ISO to login + services up.
- **Two-node cluster:** two QEMU VMs (or VirtualBox) both joined to one ZeroTier
  network; run the full wizard on each.
- **Failover test:** deploy sample site, kill one VM, confirm site stays up.
- **Install test:** Calamares install to a virtual disk; verify first-boot-once.
- (Stretch) GitHub Actions job that runs `make iso` and boots it headless in QEMU.

---

## 11. DEFINITION OF DONE (v1)

- [ ] `make iso` reliably builds a bootable, installable ISO.
- [ ] Fresh install → first-boot wizard → mesh joined → cluster formed.
- [ ] Portainer + Traefik auto-deployed and reachable.
- [ ] Sample website runs one replica per node and survives a node failure.
- [ ] Docs let a newcomer cluster two PCs in under 30 minutes.

---

## 12. STRETCH GOALS (after v1)

- HTTPS via Traefik + Let's Encrypt (real domain).
- A **database replication module** (PostgreSQL streaming replication or MariaDB
  Galera) deployable from the wizard, with a clear "your data syncs now" toggle.
- Replace Portainer with a custom branded dashboard.
- Self-hosted mesh controller (Headscale) baked in, so no external ZeroTier acct.
- 3rd-node quorum guidance / `qdevice` to avoid split-brain.
- ARM64 / Raspberry Pi image.
- `curl … | sh` one-line installer for existing Linux machines (non-ISO path).

---

## 13. KICKOFF MESSAGE (say this to the agent after pasting the above)

> "Acknowledge the spec, then start **Phase 0**: scaffold the repo structure from
> Section 6, write the `Makefile` and a minimal `live-build` config that produces
> a plain bootable Debian 12 live ISO, and give me the exact commands to build it
> and boot it in QEMU. Don't start Phase 1 until I confirm Phase 0 boots."

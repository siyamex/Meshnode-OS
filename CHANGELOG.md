# Changelog

All notable changes to meshnode OS are documented here.
Format: `## [version] — YYYY-MM-DD` with sections Added / Changed / Fixed.

---

## [0.1.0-phase4] — 2026-06-04

### Added
- `stack/portainer.yml` — Portainer CE + agent Swarm stack. Agent runs globally
  (one per node), server runs on the manager; GUI on port 9000.
- `stack/traefik.yml` — Traefik v3 Swarm stack. Runs globally (one per node)
  on ports 80/443/8080; uses Docker Swarm mode for service discovery via labels;
  requires the `meshnet` external overlay (created in Phase 3).
- `wizard/app/meshnode.py`: `deploy_stack()` and `get_stack_services()` helpers.
  `STACKS_DIR = /opt/meshnode-stacks` path constant.

### Changed
- `wizard/app/main.py`: `POST /cluster/create` now deploys the portainer and
  traefik stacks after swarm init. Deploy errors are non-fatal — saved to config
  and shown in the UI so stacks can be redeployed manually.
- `wizard/templates/step6.html`: manager done-screen now shows clickable
  Portainer and Traefik dashboard URLs, deploy error warnings, and properly
  associated `<label for>` + `title` on the join-code textarea.
- `wizard/static/style.css`: added `.url-card`, `.url-card__label`,
  `.url-card__link`, `.url-card__note`, `.field--top`.
- `Makefile`: `make iso` now rsyncs `stack/` into
  `config/includes.chroot/opt/meshnode-stacks/` so stacks are baked into the image.

---

## [0.1.0-phase3] — 2026-06-04

### Added
- `wizard/app/meshnode.py`: `docker_swarm_init`, `docker_swarm_join`,
  `docker_get_worker_token`, `docker_create_overlay_network`, `get_swarm_state`,
  `generate_join_code`, `parse_join_code`, `mark_firstboot_done` — all Swarm
  cluster helpers. Join code is base64url(JSON{token, ip}), padding-stripped.
- `wizard/app/main.py`: new routes — `POST /step/4/confirm` (saves mesh IP,
  advances to step 5), `GET /step/5` (cluster choice), `GET /step/5/join`
  (join form), `POST /cluster/create` (swarm init + meshnet overlay),
  `POST /cluster/join` (swarm join via join code), `GET /step/6` (done).
  `_current_step` extended to 6 steps. After cluster/create or cluster/join
  succeeds, writes `/etc/meshnode/.firstboot-done` and disables the wizard
  service.
- `wizard/templates/step5.html` — two-card cluster choice (Create / Join).
- `wizard/templates/step5_join.html` — join code paste form.
- `wizard/templates/step6.html` — done page: shows join code for manager,
  success message for worker.

### Changed
- `wizard/templates/base.html` — progress bar extended from 4 to 6 steps.
- `wizard/templates/step4.html` — added "Continue to cluster setup →" button
  that POSTs to `/step/4/confirm` once the mesh IP appears.
- `wizard/static/style.css` — added `.btn--top`, `.choice-grid`, `.choice-btn`,
  `textarea`, `.join-code-box`, `.back-link`, `.next-hint`; added
  `will-change: transform` to `.spinner` to avoid Paint on animation frames.

---

## [0.1.0-phase2] — 2026-06-04

### Added
- `wizard/app/main.py` — FastAPI app, 4-step setup wizard on port 8088.
- `wizard/app/meshnode.py` — helpers: config YAML R/W, ZeroTier join/status,
  network interface enumeration via `ip -o link show`.
- `wizard/templates/` — Jinja2 templates: base layout + step1–step4.
- `wizard/static/style.css` — minimal dark-theme CSS, no framework.
- `wizard/requirements.txt` — fastapi, uvicorn, jinja2, pyyaml, python-multipart.
- `wizard/meshnode-wizard.service` — systemd unit; starts wizard on boot
  (skipped after `/etc/meshnode/.firstboot-done` exists); prints wizard URL to TTY1.
- `build/live-build/config/hooks/0030-install-wizard.hook.chroot` — installs
  Python 3, creates venv, installs pip deps, installs+enables systemd unit,
  pre-creates `/etc/meshnode/`.
- `build/live-build/config/includes.chroot/etc/issue` — shows wizard URL at
  the login prompt using agetty's `\4{iface}` IP escape.
- `.gitignore` — excludes ISO, live-build output dirs, and the includes.chroot/opt/
  copy (which the Makefile generates from `wizard/`).

### Changed
- `Makefile`: `make iso` now rsyncs `wizard/` into
  `config/includes.chroot/opt/meshnode-wizard/` before running `lb build`.

---

## [0.1.0-phase1] — 2026-06-04

### Added
- `build/live-build/config/hooks/0010-install-docker.hook.chroot` — chroot hook
  that adds the Docker CE apt repo and installs docker-ce, docker-ce-cli,
  containerd.io, docker-buildx-plugin, docker-compose-plugin; enables
  `docker.service` at boot; adds the `user` account to the `docker` group.
- `build/live-build/config/hooks/0020-install-zerotier.hook.chroot` — chroot hook
  that adds the ZeroTier apt repo and installs zerotier-one; enables
  `zerotier-one.service` at boot (not joined to any network yet).
- `gnupg` added to `meshnode.list.chroot` (required for GPG key import in hooks).

### Changed
- `Makefile`: `make iso` now chmods all `*.hook.*` files before building so
  the executable bit is set even when editing from Windows.

---

## [0.1.0-phase0] — 2026-06-04

### Added
- Initial repo scaffold matching the structure in SPEC.md §6.
- `Makefile` with `make iso`, `make test`, and `make clean` targets.
- `build/live-build/auto/config` — live-build configuration for a minimal
  Debian 12 (Bookworm) x86-64 iso-hybrid image (BIOS + UEFI).
- `build/live-build/config/package-lists/meshnode.list.chroot` — minimal
  package set for Phase 0 (curl, openssh-server, vim, htop, net-tools, iproute2).
- Stub directories with `.gitkeep` for all future components
  (wizard/, node/, stack/, hooks, includes.chroot).
- `docs/install.md` — build-host requirements, WSL2 setup, `make iso` walkthrough,
  QEMU boot verification commands.
- `docs/architecture.md` and `docs/troubleshooting.md` stubs.
- `SPEC.md` — full project specification.
- `README.md` — project overview and phase status table.

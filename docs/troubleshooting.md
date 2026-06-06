# meshnode OS — Troubleshooting

For build-time errors (ISO build, QEMU boot), also see [install.md](install.md).

---

## Wizard

**Wizard URL not showing on the console / can't reach port 8088**

```bash
# Is the service running?
systemctl status meshnode-wizard
# If failed, check logs:
journalctl -u meshnode-wizard -n 50

# What IP does the node have?
ip addr show
# Use that IP in your browser: http://<ip>:8088
```

**Wizard skipped on first boot (firstboot-done flag exists from live session)**

The Calamares `shellprocess` module removes `.firstboot-done` during install.
If you manually installed without Calamares, remove it yourself:

```bash
sudo rm -f /etc/meshnode/.firstboot-done
sudo systemctl enable --now meshnode-wizard.service
```

**Wizard won't advance past hostname (hostnamectl fails)**

```bash
# Check that systemd-hostnamed is running
systemctl status systemd-hostnamed
# Try setting manually:
sudo hostnamectl set-hostname node-1
```

---

## ZeroTier

**`zerotier-cli info` returns "Error connecting to the ZeroTier service"**

```bash
sudo systemctl start zerotier-one
sudo systemctl enable zerotier-one
sudo zerotier-cli info
# Expected: 200 info <nodeID> <version> ONLINE
```

**Joined network but no mesh IP (status stays REQUESTING_CONFIGURATION)**

1. Go to **my.zerotier.com → Networks → your-network-id → Members**.
2. Find this node's ZeroTier address and tick **Authorized**.
3. Wait ~10 seconds; the wizard's step 4 auto-refreshes.

**ZeroTier status shows ACCESS_DENIED**

Your ZeroTier account's network is set to private (default). You must
authorize each new member manually — see above.

**Behind strict NAT (no connection to ZeroTier planet servers)**

Allow outbound UDP port 9993 on your router/firewall. ZeroTier uses this
for its NAT-traversal protocol. Most home routers allow this by default.

---

## Docker Swarm

**`docker swarm init` fails with "could not choose an IP address"**

The wizard passes `--advertise-addr <mesh-ip>`. If the mesh IP is blank,
ZeroTier hasn't assigned one yet. Go back to step 4 and wait for the IP.

**Worker can't join: "Error response from daemon: rpc error"**

1. Confirm the manager is reachable on port 2377 from the worker's mesh IP:
   ```bash
   nc -zv <manager-mesh-ip> 2377
   ```
2. Check that the Docker daemon is running on the manager:
   ```bash
   sudo systemctl status docker
   ```
3. Confirm the join token hasn't expired (tokens are valid indefinitely
   unless explicitly rotated).

**`docker node ls` shows a node as `Down` after reboot**

Normal — Swarm marks nodes Down if they don't heartbeat for ~5 seconds.
The node re-joins automatically when Docker starts on it. Wait ~30 seconds
after the node boots.

---

## Traefik

**Port 80 returns "Bad Gateway" or no response**

```bash
# Is Traefik running?
docker stack services traefik
# All replicas should show X/X

# Does it see the website service?
# (On the manager node)
docker service inspect website --pretty | grep -A5 Labels
# Should show traefik.enable=true labels
```

**Traefik dashboard (port 8080) not reachable**

Traefik runs in `global` mode — one replica per node. The dashboard is
reachable on any node's mesh IP:8080. Check:
```bash
docker stack services traefik   # replicas = N/N?
ss -tlnp | grep 8080            # is the port open?
```

---

## Portainer

**Can't reach Portainer (port 9000)**

Portainer runs on manager nodes only. Use the manager's mesh IP.

```bash
docker stack services portainer
# portainer_portainer should show 1/1
# portainer_agent should show N/N (one per node)
```

**Portainer is locked (5-minute admin setup window expired)**

```bash
# Remove the Portainer data volume and redeploy
docker stack rm portainer
docker volume rm portainer_portainer_data
docker stack deploy --compose-file /opt/meshnode-stacks/portainer.yml portainer
# Open http://<ip>:9000 within 5 minutes to create the admin account
```

**Portainer shows only 1 node (agent not working)**

```bash
# Check agent logs
docker service logs portainer_agent --tail 30
# Common fix: ensure agent_network overlay is healthy
docker network ls | grep agent_network
```

---

## Calamares / installer

**`sudo start-installer` returns "calamares not found"**

The ISO was built without Phase 6 packages. Rebuild with `make iso` after
confirming `calamares` is in `config/package-lists/meshnode.list.chroot`.

**Calamares window doesn't appear (black screen on TTY7)**

```bash
# Check if X started
ps aux | grep Xorg
# If not: try running without KVM (remove -enable-kvm from make test)
# Or switch TTY manually: Ctrl+Alt+F7
```

**Installer fails at "unpackfs" step (squashfs not found)**

The squashfs path `/run/live/medium/live/filesystem.squashfs` is only
present when booted from the ISO (live-boot mounts it). This will fail
if you try to run Calamares on an already-installed system.

---

## Plymouth / boot splash

**Boot splash doesn't appear (just text scrolling)**

Check that `quiet splash` is in the kernel command line:
```bash
cat /proc/cmdline | grep splash
```
If not present, the ISO was built without Phase 7 changes. Rebuild with
`make iso`.

**Plymouth theme not set on the installed system**

```bash
sudo plymouth-get-default-theme   # should print: meshnode
sudo update-initramfs -u -k all   # rebuild initramfs with correct theme
sudo update-grub                  # ensure splash is in GRUB cmdline
```

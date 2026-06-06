# meshnode OS — Phase 5 Failover Test

This is the "money shot" test: deploy the sample website across both nodes,
kill one node, and confirm the site keeps serving.

## Prerequisites

- Phase 0–4 complete: two-node cluster running, Portainer and Traefik deployed.
- Both VMs/PCs powered on and joined to the ZeroTier mesh.
- Internet access for the initial `traefik/whoami` image pull.

---

## Step 1 — Deploy the sample website

On the **manager node**, run:

```bash
sudo deploy-website
# or manually:
sudo docker stack deploy --compose-file /opt/meshnode-stacks/website-example.yml website
```

Wait ~30 seconds for the image to pull, then confirm both replicas are running:

```bash
docker stack services website
# Expected output:
# ID        NAME               MODE        REPLICAS  IMAGE
# abc123    website_website    replicated  2/2       traefik/whoami:latest
```

`2/2` means one replica is running on each node. If you see `1/2` for more
than 60 seconds, check `docker service ps website` for placement errors.

---

## Step 2 — Confirm the site loads from both nodes

Pick up both nodes' mesh IPs from `/etc/meshnode/config.yaml` or `zerotier-cli listnetworks`.

```bash
# Hit node-1 through Traefik on port 80:
curl http://<node-1-mesh-ip>/

# Expected response (container hostname reveals which node served it):
# Hostname: website_website.1.xk4m2a9p0h8z...
# IP: 10.x.x.x
# RemoteAddr: 10.x.x.x:XXXXX
# GET / HTTP/1.1
# Host: <node-1-mesh-ip>
# ...

# Hit node-2:
curl http://<node-2-mesh-ip>/

# Expected: different Hostname (different container)
# Hostname: website_website.2.ab7nq1r3c5...
```

Each node's Traefik instance routes to the local replica. Both nodes respond
with **different container hostnames** — that confirms 2 independent replicas
are running.

---

## Step 3 — Kill node-1

Power off the first node:

```bash
# Inside node-1 VM, or just force-close the VM window:
sudo poweroff
```

---

## Step 4 — Confirm failover (within ~30 seconds)

On **node-2**, watch Docker Swarm detect the failure:

```bash
# Swarm marks the dead node as Down
watch docker node ls
# → node-1   Down   Drain  (none)
# → node-2   Ready  Active Leader

# The website replica count drops to 1/2 (expected — max_replicas_per_node: 1
# means Swarm correctly refuses to schedule a second replica on node-2)
docker stack services website
# → website_website  replicated  1/2  traefik/whoami:latest
```

**Hit node-2's IP — the site is still up:**

```bash
curl http://<node-2-mesh-ip>/
# → Hostname: website_website.1.xk4m2a9p0h8z...   ← still responding
# → IP: 10.x.x.x
```

> **Why 1/2 and not 2/2?**
> `max_replicas_per_node: 1` prevents Docker from running two copies on the
> surviving node. This is intentional — it ensures replicas are spread across
> nodes (real redundancy), not doubled up on one. In a 3-node cluster you'd
> have 2/2 after one failure.

---

## Step 5 — Restore and rebalance

Power node-1 back on. After it rejoins the mesh and Swarm (~60–90 seconds):

```bash
docker node ls
# → node-1   Ready  Active  (none)
# → node-2   Ready  Active  Leader

docker stack services website
# → website_website  replicated  2/2  traefik/whoami:latest
```

Docker Swarm automatically reschedules the second replica onto node-1.
Both nodes are serving again. ✅

---

## Troubleshooting

**`0/2` replicas after deploy**
The image pull may be slow or ZeroTier isn't reachable. Check:
```bash
docker service ps website --no-trunc
# Look for error messages in the CURRENT STATE column
```

**`curl` returns "Connection refused" on both IPs**
Traefik may still be starting. Wait 60 s and retry, or check:
```bash
docker stack services traefik
# Should show REPLICAS = 2/2 (global mode, one per node)
```

**`curl` to node-1's IP never works after failover**
Expected — Traefik on node-1 is also dead. Requests must go through node-2's IP.
In a production setup, a floating IP or DNS failover (e.g. Cloudflare proxied)
handles directing users to a live node automatically.

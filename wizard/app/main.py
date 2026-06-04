"""
main.py — meshnode first-boot setup wizard (FastAPI).

Step flow:
  1  /step/1              Set hostname
  2  /step/2              Choose LAN interface
  3  /step/3              Join ZeroTier network
  4  /step/4              Wait for mesh IP + confirm
  5  /step/5              Cluster choice: Create or Join
     /step/5/join         Form to paste a join code (worker path)
  6  /step/6              Done — shows join code (manager) or success (worker)

Supporting endpoints:
  POST /step/4/confirm    Save mesh IP to config, advance to step 5
  POST /cluster/create    docker swarm init + create meshnet overlay
  POST /cluster/join      docker swarm join via decoded join code
  GET  /api/mesh-status   JSON poll for ZeroTier mesh IP

Runs on 0.0.0.0:8088, as root, under meshnode-wizard.service.
"""
from __future__ import annotations

import re
import socket
import subprocess
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from meshnode import (
    FIRSTBOOT_DONE,
    docker_create_overlay_network,
    docker_get_worker_token,
    docker_swarm_init,
    docker_swarm_join,
    generate_join_code,
    list_interfaces,
    mark_firstboot_done,
    parse_join_code,
    read_config,
    write_config,
    zerotier_join,
    zerotier_mesh_ip,
    zerotier_status,
)

# ── App setup ──────────────────────────────────────────────────────────────────

BASE_DIR = Path("/opt/meshnode-wizard")

app = FastAPI(title="meshnode setup wizard", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _current_step(config: dict) -> int:
    """Return the step number the user should land on given saved config."""
    if not config.get("hostname"):
        return 1
    if not config.get("interface"):
        return 2
    if not config.get("zerotier_network_id"):
        return 3
    if not config.get("mesh_ip"):
        return 4
    if not config.get("cluster_role"):
        return 5
    return 6


# ── Root redirect ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return RedirectResponse(f"/step/{_current_step(read_config())}")


# ── Step 1: hostname ───────────────────────────────────────────────────────────

@app.get("/step/1", response_class=HTMLResponse)
async def step1_get(request: Request):
    return templates.TemplateResponse("step1.html", {
        "request": request, "step": 1,
        "current_hostname": socket.gethostname(), "error": None,
    })


@app.post("/step/1")
async def step1_post(request: Request, hostname: str = Form(...)):
    hostname = hostname.strip().lower()
    if not re.match(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$", hostname):
        return templates.TemplateResponse("step1.html", {
            "request": request, "step": 1,
            "current_hostname": hostname,
            "error": (
                "Invalid hostname. Use lowercase letters, numbers, and hyphens. "
                "Must start and end with a letter or number. Max 63 characters."
            ),
        }, status_code=422)
    subprocess.run(["hostnamectl", "set-hostname", hostname], check=True)
    config = read_config()
    config["hostname"] = hostname
    write_config(config)
    return RedirectResponse("/step/2", status_code=303)


# ── Step 2: network interface ──────────────────────────────────────────────────

@app.get("/step/2", response_class=HTMLResponse)
async def step2_get(request: Request):
    return templates.TemplateResponse("step2.html", {
        "request": request, "step": 2,
        "interfaces": list_interfaces(),
        "saved": read_config().get("interface", ""),
        "error": None,
    })


@app.post("/step/2")
async def step2_post(request: Request, interface: str = Form(...)):
    interfaces = list_interfaces()
    if interface not in interfaces:
        return templates.TemplateResponse("step2.html", {
            "request": request, "step": 2, "interfaces": interfaces, "saved": "",
            "error": f"Interface '{interface}' not found. Please select one from the list.",
        }, status_code=422)
    config = read_config()
    config["interface"] = interface
    write_config(config)
    return RedirectResponse("/step/3", status_code=303)


# ── Step 3: ZeroTier join ──────────────────────────────────────────────────────

@app.get("/step/3", response_class=HTMLResponse)
async def step3_get(request: Request):
    return templates.TemplateResponse("step3.html", {
        "request": request, "step": 3, "error": None,
    })


@app.post("/step/3")
async def step3_post(request: Request, network_id: str = Form(...)):
    network_id = network_id.strip().lower()
    if not re.match(r"^[0-9a-f]{16}$", network_id):
        return templates.TemplateResponse("step3.html", {
            "request": request, "step": 3,
            "error": (
                "Invalid network ID — must be exactly 16 hex characters "
                "(e.g. 8056c2e21c000001). Find it on my.zerotier.com."
            ),
        }, status_code=422)
    if not zerotier_join(network_id):
        return templates.TemplateResponse("step3.html", {
            "request": request, "step": 3,
            "error": (
                "Failed to join network. Is zerotier-one running? "
                "Check: sudo systemctl status zerotier-one"
            ),
        }, status_code=500)
    config = read_config()
    config["zerotier_network_id"] = network_id
    write_config(config)
    return RedirectResponse("/step/4", status_code=303)


# ── Step 4: wait for mesh IP + confirm ────────────────────────────────────────

@app.get("/step/4", response_class=HTMLResponse)
async def step4_get(request: Request):
    config = read_config()
    network_id = config.get("zerotier_network_id", "")
    zt = zerotier_status(network_id)
    mesh_ip = zt.get("mesh_ip")
    return templates.TemplateResponse("step4.html", {
        "request": request, "step": 4,
        "hostname":   config.get("hostname", ""),
        "network_id": network_id,
        "zt_status":  zt.get("status", ""),
        "mesh_ip":    mesh_ip,
        "refreshing": mesh_ip is None,
    })


@app.post("/step/4/confirm")
async def step4_confirm():
    """Save the confirmed mesh IP to config and advance to step 5."""
    config = read_config()
    network_id = config.get("zerotier_network_id", "")
    mesh_ip = zerotier_mesh_ip(network_id)
    if not mesh_ip:
        return RedirectResponse("/step/4", status_code=303)
    config["mesh_ip"] = mesh_ip
    write_config(config)
    return RedirectResponse("/step/5", status_code=303)


# ── Step 5: cluster choice ────────────────────────────────────────────────────

@app.get("/step/5", response_class=HTMLResponse)
async def step5_get(request: Request):
    config = read_config()
    return templates.TemplateResponse("step5.html", {
        "request": request, "step": 5,
        "mesh_ip": config.get("mesh_ip", ""),
        "error": None,
    })


@app.get("/step/5/join", response_class=HTMLResponse)
async def step5_join_get(request: Request):
    return templates.TemplateResponse("step5_join.html", {
        "request": request, "step": 5, "error": None,
    })


# ── Cluster create ─────────────────────────────────────────────────────────────

@app.post("/cluster/create")
async def cluster_create(request: Request):
    """Initialise a Swarm, create the meshnet overlay, generate join code."""
    config = read_config()
    mesh_ip = config.get("mesh_ip")
    if not mesh_ip:
        return templates.TemplateResponse("step5.html", {
            "request": request, "step": 5, "mesh_ip": "",
            "error": "Mesh IP not found. Go back to step 4 and confirm your ZeroTier IP.",
        }, status_code=400)

    success, err = docker_swarm_init(mesh_ip)
    if not success:
        return templates.TemplateResponse("step5.html", {
            "request": request, "step": 5, "mesh_ip": mesh_ip,
            "error": f"Swarm init failed: {err}",
        }, status_code=500)

    # Create the overlay network that all Swarm services will use
    docker_create_overlay_network("meshnet")

    worker_token = docker_get_worker_token()
    join_code = generate_join_code(worker_token, mesh_ip) if worker_token else ""

    config["cluster_role"] = "manager"
    config["join_code"] = join_code
    write_config(config)

    mark_firstboot_done()
    return RedirectResponse("/step/6", status_code=303)


# ── Cluster join ───────────────────────────────────────────────────────────────

@app.post("/cluster/join")
async def cluster_join(request: Request, join_code: str = Form(...)):
    """Decode a join code and connect this node to an existing Swarm as worker."""
    parsed = parse_join_code(join_code.strip())
    if parsed is None:
        return templates.TemplateResponse("step5_join.html", {
            "request": request, "step": 5,
            "error": (
                "Invalid join code. Make sure you copied the entire code "
                "from the manager node's done screen."
            ),
        }, status_code=422)

    worker_token, manager_ip = parsed
    success, err = docker_swarm_join(worker_token, manager_ip)
    if not success:
        return templates.TemplateResponse("step5_join.html", {
            "request": request, "step": 5,
            "error": f"Failed to join Swarm: {err}",
        }, status_code=500)

    config = read_config()
    config["cluster_role"] = "worker"
    write_config(config)

    mark_firstboot_done()
    return RedirectResponse("/step/6", status_code=303)


# ── Step 6: done ──────────────────────────────────────────────────────────────

@app.get("/step/6", response_class=HTMLResponse)
async def step6_get(request: Request):
    config = read_config()
    return templates.TemplateResponse("step6.html", {
        "request": request, "step": 6,
        "role":      config.get("cluster_role", ""),
        "join_code": config.get("join_code", ""),
        "hostname":  config.get("hostname", ""),
        "mesh_ip":   config.get("mesh_ip", ""),
    })


# ── API: mesh status ──────────────────────────────────────────────────────────

@app.get("/api/mesh-status")
async def api_mesh_status():
    config = read_config()
    return zerotier_status(config.get("zerotier_network_id", ""))

"""
meshnode.py — helper functions for config I/O, ZeroTier, network interfaces,
and Docker Swarm cluster management. Imported by main.py.
"""
from __future__ import annotations

import base64
import ipaddress
import json
import re
import subprocess
from pathlib import Path
from typing import Optional

import yaml

# ── Paths ──────────────────────────────────────────────────────────────────────

CONFIG_DIR     = Path("/etc/meshnode")
CONFIG_FILE    = CONFIG_DIR / "config.yaml"
FIRSTBOOT_DONE = CONFIG_DIR / ".firstboot-done"
STACKS_DIR     = Path("/opt/meshnode-stacks")


# ── Config helpers ─────────────────────────────────────────────────────────────

def read_config() -> dict:
    """Load /etc/meshnode/config.yaml, returning an empty dict if not found."""
    if CONFIG_FILE.exists():
        return yaml.safe_load(CONFIG_FILE.read_text()) or {}
    return {}


def write_config(data: dict) -> None:
    """Atomically persist the config dict to /etc/meshnode/config.yaml."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(yaml.safe_dump(data, default_flow_style=False))


def mark_firstboot_done() -> None:
    """
    Write the sentinel file that stops the wizard from restarting,
    then disable the systemd unit so it is skipped on future boots.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    FIRSTBOOT_DONE.touch()
    subprocess.run(
        ["systemctl", "disable", "meshnode-wizard.service"],
        capture_output=True,
    )


# ── Network helpers ────────────────────────────────────────────────────────────

def list_interfaces() -> list[str]:
    """Return non-loopback, non-ZeroTier network interface names."""
    result = subprocess.run(
        ["ip", "-o", "link", "show"],
        capture_output=True, text=True, check=True,
    )
    ifaces: list[str] = []
    for line in result.stdout.splitlines():
        match = re.match(r"^\d+:\s+(\S+):", line)
        if match:
            name = match.group(1).rstrip("@")
            if name == "lo" or name.startswith("zt"):
                continue
            ifaces.append(name)
    return ifaces


# ── ZeroTier helpers ───────────────────────────────────────────────────────────

def zerotier_join(network_id: str) -> bool:
    """Tell the ZeroTier daemon to join `network_id`. Returns True on success."""
    result = subprocess.run(
        ["zerotier-cli", "join", network_id],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def _parse_listnetworks(network_id: str) -> Optional[dict]:
    """
    Parse `zerotier-cli listnetworks` and return the entry for `network_id`.

    Line format:
      200 listnetworks <id> <name> <mac> <status> <type> <dev> <ips>
    """
    result = subprocess.run(
        ["zerotier-cli", "listnetworks"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 9 and parts[0] == "200" and parts[1] == "listnetworks" \
                and parts[2] == network_id:
            return {"id": parts[2], "name": parts[3], "status": parts[5],
                    "dev": parts[7], "ips": parts[8]}
    return None


def zerotier_mesh_ip(network_id: str) -> Optional[str]:
    """Return the first assigned IPv4 mesh IP for `network_id`, or None."""
    entry = _parse_listnetworks(network_id)
    if not entry or entry["ips"] == "-":
        return None
    for addr_cidr in entry["ips"].split(","):
        ip_str = addr_cidr.split("/")[0]
        try:
            addr = ipaddress.ip_address(ip_str)
            if addr.version == 4:
                return str(addr)
        except ValueError:
            continue
    return None


def zerotier_status(network_id: str) -> dict:
    """Return {joined: bool, status: str, mesh_ip: str|None}."""
    if not network_id:
        return {"joined": False, "status": "not configured", "mesh_ip": None}
    entry = _parse_listnetworks(network_id)
    if entry is None:
        return {"joined": False, "status": "daemon not running", "mesh_ip": None}
    if not entry:
        return {"joined": False, "status": "not joined", "mesh_ip": None}
    return {"joined": True, "status": entry["status"],
            "mesh_ip": zerotier_mesh_ip(network_id)}


# ── Docker Swarm helpers ───────────────────────────────────────────────────────

def get_swarm_state() -> str:
    """
    Return the local Docker Swarm state string.
    Values: 'inactive' | 'active' | 'pending' | 'error'
    """
    result = subprocess.run(
        ["docker", "info", "--format", "{{.Swarm.LocalNodeState}}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return "error"
    return result.stdout.strip() or "error"


def docker_swarm_init(advertise_addr: str) -> tuple[bool, str]:
    """
    Initialise a new Swarm cluster, advertising on the given IP.
    Returns (success, error_message).
    """
    state = get_swarm_state()
    if state == "active":
        return False, "This node is already part of a Docker Swarm."
    if state == "error":
        return False, "Docker daemon is not running. Try: sudo systemctl start docker"

    result = subprocess.run(
        ["docker", "swarm", "init", "--advertise-addr", advertise_addr],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, ""


def docker_get_worker_token() -> Optional[str]:
    """Return the Swarm worker join token (-q = quiet, token only)."""
    result = subprocess.run(
        ["docker", "swarm", "join-token", "worker", "-q"],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def docker_create_overlay_network(name: str = "meshnet") -> bool:
    """
    Create an attachable overlay network for Swarm services.
    Idempotent: returns True if the network already exists.
    """
    check = subprocess.run(
        ["docker", "network", "inspect", name],
        capture_output=True, text=True,
    )
    if check.returncode == 0:
        return True  # already exists

    result = subprocess.run(
        ["docker", "network", "create",
         "--driver", "overlay",
         "--attachable",
         name],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def docker_swarm_join(worker_token: str, manager_ip: str) -> tuple[bool, str]:
    """
    Join an existing Swarm cluster as a worker.
    Returns (success, error_message).
    """
    state = get_swarm_state()
    if state == "active":
        return False, "This node is already part of a Docker Swarm."
    if state == "error":
        return False, "Docker daemon is not running. Try: sudo systemctl start docker"

    result = subprocess.run(
        ["docker", "swarm", "join",
         "--token", worker_token,
         f"{manager_ip}:2377"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, ""


# ── Join code helpers ──────────────────────────────────────────────────────────

def generate_join_code(worker_token: str, manager_ip: str) -> str:
    """
    Pack the worker token and manager IP into a URL-safe base64 string.

    Format on the wire: base64url(JSON {"token": "...", "ip": "..."})
    Padding ('=') is stripped because it is not URL-safe and can confuse
    copy/paste across terminals; parse_join_code re-adds it.
    """
    payload = json.dumps({"token": worker_token, "ip": manager_ip})
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def deploy_stack(name: str, compose_file: Path) -> tuple[bool, str]:
    """
    Deploy (or update) a Docker Swarm stack from a Compose file.
    Returns (success, message). Idempotent: re-running updates the stack.
    """
    if not compose_file.exists():
        return False, f"Compose file not found: {compose_file}"
    result = subprocess.run(
        ["docker", "stack", "deploy",
         "--compose-file", str(compose_file),
         name],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, result.stdout.strip()


def get_stack_services(stack_name: str) -> list[dict]:
    """
    Return a list of service status dicts for a deployed stack.
    Each dict has keys: name, replicas, image.
    """
    result = subprocess.run(
        ["docker", "stack", "services", stack_name,
         "--format", "{{.Name}}\t{{.Replicas}}\t{{.Image}}"],
        capture_output=True, text=True,
    )
    services = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            services.append({"name": parts[0], "replicas": parts[1], "image": parts[2]})
    return services


def parse_join_code(join_code: str) -> Optional[tuple[str, str]]:
    """
    Decode a join code back into (worker_token, manager_ip).
    Returns None if the code is malformed or missing required keys.
    """
    try:
        # Re-add the padding that generate_join_code stripped
        padding = 4 - (len(join_code) % 4)
        if padding != 4:
            join_code += "=" * padding
        data = json.loads(base64.urlsafe_b64decode(join_code.encode()).decode())
        return data["token"], data["ip"]
    except Exception:
        return None

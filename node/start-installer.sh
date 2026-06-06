#!/bin/bash
# node/start-installer.sh
#
# Launch the Calamares graphical disk installer on display :1 / TTY7.
# Baked into the image as /usr/local/bin/start-installer via hook 0040.
#
# Usage: sudo start-installer
#   Switch to the graphical session: Ctrl+Alt+F7
#   Return to the console:           Ctrl+Alt+F1

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "!! Must be run as root. Try: sudo start-installer" >&2
    exit 1
fi

# ── Pre-flight checks ─────────────────────────────────────────────────────────

if ! command -v calamares &>/dev/null; then
    echo "!! calamares not found. This ISO may not have the installer baked in." >&2
    exit 1
fi

if ! command -v startx &>/dev/null; then
    echo "!! startx not found. Install xinit: sudo apt install xinit" >&2
    exit 1
fi

# ── Check if already running ──────────────────────────────────────────────────

if pgrep -x calamares &>/dev/null; then
    echo ">> Calamares is already running."
    echo ">> Switch to it with: Ctrl+Alt+F7"
    exit 0
fi

# ── Launch ────────────────────────────────────────────────────────────────────

echo ""
echo ">> Starting meshnode OS installer..."
echo ">> Switch to the graphical display with: Ctrl+Alt+F7"
echo ">> Return to this console with:          Ctrl+Alt+F1"
echo ""

# startx reads /root/.xinitrc which runs openbox + calamares.
# -- separates startx args from X server args.
# :1  = use display :1 (avoids conflict if :0 is in use)
# vt7 = attach to virtual terminal 7
exec startx /root/.xinitrc -- :1 vt7

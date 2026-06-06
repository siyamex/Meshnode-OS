#!/bin/sh
# /root/.xinitrc — X session launched by start-installer.
# Starts openbox as a minimal window manager, then runs Calamares.
# When Calamares exits (install done or cancelled), X shuts down.
openbox &
exec calamares

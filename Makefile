SHELL   := /bin/bash
VERSION ?= 0.1.0

# The directory that contains the live-build config tree
LB_DIR  := build/live-build

# Final ISO name placed at the repo root
ISO_OUT := meshnode-os-$(VERSION).iso

# live-build names its output file predictably
LB_ISO  := $(LB_DIR)/live-image-amd64.hybrid.iso

.PHONY: iso test clean help

## Build the meshnode OS ISO (must run on Debian/Ubuntu or WSL2 — see docs/install.md)
iso:
	@echo ">> Building meshnode OS $(VERSION)..."
	@echo ">> Working dir: $(LB_DIR)"
	# Ensure auto/config and all hooks are executable — bits lost when editing from Windows.
	chmod +x $(LB_DIR)/auto/config
	find $(LB_DIR)/config/hooks -name '*.hook.*' -exec chmod +x {} \;
	# Sync the wizard source into includes.chroot so live-build bakes it into
	# /opt/meshnode-wizard/ on the live image. rsync --delete removes stale files
	# if you rename or remove wizard files between builds.
	mkdir -p $(LB_DIR)/config/includes.chroot/opt/meshnode-wizard
	rsync -a --delete wizard/ $(LB_DIR)/config/includes.chroot/opt/meshnode-wizard/
	# Wipe any previous partial build so lb build starts clean.
	# '|| true' prevents failure when there is nothing to clean yet.
	cd $(LB_DIR) && sudo lb clean 2>/dev/null || true
	# lb config reads auto/config (which in turn calls 'lb config noauto ...')
	# and writes all configuration files into config/.
	cd $(LB_DIR) && sudo lb config
	# lb build: debootstrap → chroot hooks → binary assembly → ISO writing.
	# This downloads ~400 MB on first run; subsequent runs reuse the cache.
	cd $(LB_DIR) && sudo lb build
	@echo ">> Copying ISO to project root..."
	cp $(LB_ISO) $(ISO_OUT)
	@echo ""
	@echo ">> SUCCESS: $(ISO_OUT)"
	@echo ">> To test: make test"

## Boot the built ISO in QEMU (requires qemu-system-x86 and KVM)
test:
	@if [ ! -f "$(ISO_OUT)" ]; then \
	  echo "!! ISO not found: $(ISO_OUT). Run 'make iso' first."; \
	  exit 1; \
	fi
	@echo ">> Booting $(ISO_OUT) in QEMU..."
	@echo ">> Login: user / live  (or root with no password)"
	@echo ">> Press Ctrl-A then X to quit QEMU"
	# -enable-kvm: use hardware virtualisation (fast). Remove if KVM is unavailable.
	# -net user:   NAT so the VM can reach the internet without extra setup.
	# -nographic:  serial console only; remove to get a graphical window.
	qemu-system-x86_64 \
	  -m 2048 \
	  -cdrom $(ISO_OUT) \
	  -boot d \
	  -enable-kvm \
	  -net nic \
	  -net user \
	  -nographic

## Remove all build artifacts (full purge of live-build cache)
clean:
	@echo ">> Cleaning live-build artifacts (this may take a moment)..."
	cd $(LB_DIR) && sudo lb clean --purge 2>/dev/null || true
	rm -f $(ISO_OUT)
	@echo ">> Clean complete."

## Show available targets
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/^## //' | \
	  awk 'BEGIN{FS="\n"} {print "  " $$1}'
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "  iso     Build the ISO (run on Linux/WSL2)"
	@echo "  test    Boot ISO in QEMU"
	@echo "  clean   Remove build artifacts"

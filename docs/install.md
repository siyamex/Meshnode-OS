# meshnode OS — Build & Install Guide

## Build-host requirements

`live-build` is a Debian/Ubuntu tool. You **cannot** run `make iso` natively on
Windows. Choose one of the two paths below.

---

### Option A — WSL2 (recommended for Windows users)

WSL2 gives you a full Linux kernel under Windows with near-native performance.

**1. Enable WSL2 and install Ubuntu 22.04**

Open PowerShell as Administrator and run:

```powershell
wsl --install -d Ubuntu-22.04
```

Restart when prompted, then open the Ubuntu terminal and create your user account.

**2. Expose the project directory inside WSL2**

Your Windows `D:\projects\os` directory is automatically mounted at
`/mnt/d/projects/os` inside WSL2. You can work directly there, but for best
performance clone the repo into the WSL2 filesystem:

```bash
# Inside WSL2 terminal:
cp -r /mnt/d/projects/os ~/meshnode-os
cd ~/meshnode-os
```

**3. Install build dependencies**

```bash
sudo apt update && sudo apt install -y \
    live-build \
    debootstrap \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-common \
    grub-pc-bin \
    grub-efi-amd64-bin \
    mtools
```

**4. Build the ISO**

```bash
make iso
# Takes 10–20 minutes on first run (downloads ~400 MB of Debian packages).
# Subsequent builds are faster because apt cache is reused.
```

**5. Find the ISO**

```bash
ls -lh meshnode-os-0.1.0.iso
```

Copy it back to Windows if needed:

```bash
cp meshnode-os-0.1.0.iso /mnt/d/projects/os/
```

---

### Option B — Native Debian/Ubuntu host (or VM)

If you already have Debian 12 or Ubuntu 22.04+:

```bash
sudo apt update && sudo apt install -y \
    live-build \
    debootstrap \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-common \
    grub-pc-bin \
    grub-efi-amd64-bin \
    mtools

cd /path/to/meshnode-os
make iso
```

---

## Testing the ISO in QEMU

### Install QEMU

```bash
# Debian/Ubuntu (same host or WSL2):
sudo apt install -y qemu-system-x86 qemu-kvm
```

### Boot the ISO

```bash
make test
```

This runs:
```bash
qemu-system-x86_64 \
  -m 2048 \
  -cdrom meshnode-os-0.1.0.iso \
  -boot d \
  -enable-kvm \
  -net nic -net user \
  -nographic
```

**Controls:** `Ctrl-A` then `X` to exit QEMU.

**Login credentials (Phase 0 live image defaults):**
- Username: `user`, Password: `live`
- Or: `root` with no password

### Phase 0 verification checklist

Once booted to a login prompt, run:

```bash
# Confirm you're on Debian 12 Bookworm:
cat /etc/os-release | grep -E "^(NAME|VERSION)"

# Confirm the network tools package landed:
which ip && ip addr show

# Confirm SSH server is present (will be available in later phases):
systemctl status ssh --no-pager
```

All three should succeed without errors. That's Phase 0 passing.

---

## Booting from a USB stick (real hardware)

Use [Balena Etcher](https://etcher.balena.io/) on any OS to flash the
`meshnode-os-*.iso` to a USB drive. The image is a hybrid ISO so it boots from
both USB and CD/DVD on BIOS and UEFI systems.

---

## Troubleshooting

See [troubleshooting.md](troubleshooting.md) for common build and boot errors.

### Common build issues

**`debootstrap` fails with "gpg: no valid OpenPGP data found"**
```bash
sudo apt install --reinstall debian-archive-keyring
```

**`lb build` fails with "E: ... already mounted"**
```bash
cd build/live-build && sudo lb clean --purge && cd ../.. && make iso
```

**QEMU: "Could not access KVM kernel module"**  
Remove `-enable-kvm` from the `test` target in the Makefile, or enable
hardware virtualisation in your BIOS/UEFI settings.

# DGX Spark Recovery -- Factory Reset Guide

## Prerequisites

Before you begin, gather the following:

- **USB flash drive**: 32 GB or larger, USB 3.0+ recommended
- **External display**: HDMI or DisplayPort (the DGX Spark has HDMI out)
- **USB keyboard**: Wired USB keyboard (Bluetooth will not work at UEFI level)
- **Mac** (for creating the bootable USB): Your Minisforum or any macOS machine
- **Internet connection**: For downloading the recovery image (~15-25 GB)
- **Time**: Allow 1-2 hours for the full process

## Step 1: Download the Recovery Image

1. Open a browser and navigate to:
   ```
   https://nvidia.com/en-us/drivers/dgx-spark-recovery-software/
   ```

2. Sign in with your NVIDIA Developer account (create one free if you do not have one).

3. Download the **DGX Spark Recovery Image** (`.img` or `.iso` file). The file is large (15-25 GB), so ensure you have sufficient disk space.

4. Note the download location. For this guide, we assume:
   ```
   ~/Downloads/dgx-spark-recovery.img
   ```

5. Verify the checksum if NVIDIA provides one:
   ```bash
   shasum -a 256 ~/Downloads/dgx-spark-recovery.img
   ```
   Compare against the published SHA-256 hash on the download page.

## Step 2: Create Bootable USB on macOS

NVIDIA provides a macOS script for creating the bootable USB. If they provide one, use it. Otherwise, follow the manual method below.

### Option A: NVIDIA-Provided macOS Script

If the download page includes a macOS helper script (e.g., `create-recovery-usb-macos.sh`):

```bash
# Make executable
chmod +x ~/Downloads/create-recovery-usb-macos.sh

# Run with the image path and target disk
# IMPORTANT: Identify your USB disk first (see identification step below)
sudo ~/Downloads/create-recovery-usb-macos.sh \
  --image ~/Downloads/dgx-spark-recovery.img \
  --target /dev/diskN
```

### Option B: Manual Method (dd)

1. **Insert the USB drive** into your Mac.

2. **Identify the USB disk**:
   ```bash
   diskutil list
   ```

   Look for your USB drive. It will appear as `/dev/diskN` (e.g., `/dev/disk4`). Identify it by size (32 GB or whatever your drive is). **Triple-check you have the right disk -- dd will destroy all data on the target.**

   Example output:
   ```
   /dev/disk4 (external, physical):
      #:                       TYPE NAME                    SIZE       IDENTIFIER
      0:     FDisk_partition_scheme                        *32.0 GB    disk4
      1:             Windows_FAT_32 USB_DRIVE               32.0 GB    disk4s1
   ```

3. **Unmount the USB drive** (do NOT eject):
   ```bash
   diskutil unmountDisk /dev/diskN
   ```

4. **Write the recovery image**:
   ```bash
   # Replace diskN with your actual disk number
   # Use rdiskN (raw disk) for significantly faster writes
   sudo dd if=~/Downloads/dgx-spark-recovery.img of=/dev/rdiskN bs=4m status=progress
   ```

   This will take 10-30 minutes depending on USB speed. Do not interrupt the process.

5. **Eject the USB drive** when complete:
   ```bash
   diskutil eject /dev/diskN
   ```

### Option C: Using Balena Etcher (GUI Alternative)

1. Download Balena Etcher from https://www.balena.io/etcher/
2. Open Etcher
3. Select the recovery `.img` file
4. Select the USB drive
5. Click "Flash!"

## Step 3: Connect Peripherals to DGX Spark

1. **Connect the USB keyboard** to one of the DGX Spark's USB-A ports.
2. **Connect the external display** via HDMI.
3. **Insert the bootable USB drive** into another USB-A port.
4. **Ensure power is connected** but the unit is powered off.

## Step 4: Enter UEFI/BIOS Setup

1. **Power on** the DGX Spark.

2. **Immediately and repeatedly press the UEFI access key**. Try these in order:
   - `Esc` (most common for NVIDIA systems)
   - `Del`
   - `F2`
   - `F12` (boot menu directly)

3. You should see the **UEFI/BIOS Setup Utility** screen.

4. If you miss it and the system boots to the locked OS login, power off (hold power button 10 seconds) and try again.

## Step 5: Configure UEFI Settings

Once in the UEFI setup:

### 5a: Restore Defaults
1. Navigate to **Exit** tab (or **Save & Exit**).
2. Select **Restore Defaults** or **Load Optimized Defaults**.
3. Confirm with **Yes**.

### 5b: Enable Secure Boot
1. Navigate to **Security** tab (or **Boot** tab).
2. Find **Secure Boot**.
3. Set to **Enabled**.
4. If prompted, select **Standard** or **Default Keys** mode.

### 5c: Set Boot Override to USB
1. Navigate to **Boot** tab.
2. Look for **Boot Override** or **Boot Option Priorities**.
3. Select your USB drive from the list (it may appear as the drive's brand name or "UEFI: USB Device").
4. Alternatively, navigate to **Save & Exit** > **Boot Override** and select the USB drive.

### 5d: Save and Exit
1. Select **Save Changes and Exit**.
2. Confirm with **Yes**.
3. The system will reboot and boot from the USB drive.

## Step 6: Run the Recovery Process

Once booted from USB, the recovery environment will load:

1. **Select language** if prompted.

2. **Select recovery option**: Choose **Factory Reset** or **Full System Restore** (not "Repair" -- you want a clean slate).

3. **Confirm disk selection**: The installer will show the internal 4 TB NVMe. Confirm this is the target.

4. **WARNING**: This will **erase all data** on the DGX Spark's internal storage. Confirm to proceed.

5. **Wait for the recovery process** to complete. This typically takes 20-45 minutes. The system will:
   - Format the internal NVMe
   - Install DGX OS (Ubuntu-based)
   - Install NVIDIA drivers and CUDA toolkit
   - Install NVIDIA container runtime
   - Configure system defaults

6. **Do NOT power off or remove the USB** during this process.

7. When prompted, **remove the USB drive** and press Enter to reboot.

## Step 7: Initial System Setup (First Boot)

After reboot, you will see the DGX OS first-time setup:

1. **Select your timezone**: e.g., America/New_York, America/Los_Angeles, etc.

2. **Create your user account**:
   - **Username**: Choose something consistent. Recommendation: `newwaveclaw` (same as Minisforum for simplicity).
   - **Full name**: Your name
   - **Password**: Choose a strong password. **Write it down and store securely.**

   ```
   Recommended: Use a password manager. You will need this password for SSH and sudo.
   ```

3. **Configure network** if prompted:
   - The DGX Spark should auto-detect Ethernet via DHCP.
   - Verify it gets `192.168.1.158` (or check your router's DHCP leases).

4. **Complete setup** and log in to the desktop (if GUI) or shell.

## Step 8: Verify the Recovery

Open a terminal on the DGX Spark and run:

```bash
# Check OS version
cat /etc/os-release

# Check NVIDIA driver
nvidia-smi

# Expected output should show:
#   - GB10 GPU
#   - Driver version
#   - CUDA version
#   - 128 GB memory (unified)

# Check disk
df -h
# Should show ~4 TB on the root filesystem (or partitioned)

# Check network
ip addr show
# Should show 192.168.1.158 (or similar) on the Ethernet interface

# Check hostname
hostname
```

## Step 9: Configure SSH Access

```bash
# On the DGX Spark:

# Ensure SSH server is installed and running
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable --now ssh

# Verify SSH is running
sudo systemctl status ssh

# Configure SSH hardening (optional but recommended)
sudo tee -a /etc/ssh/sshd_config.d/hardening.conf << 'EOF'
PermitRootLogin no
PasswordAuthentication yes
MaxAuthTries 5
ClientAliveInterval 300
ClientAliveCountMax 3
EOF

sudo systemctl restart ssh
```

Now test SSH from the Minisforum:
```bash
# On the Minisforum (192.168.1.157):
ssh newwaveclaw@192.168.1.158

# If this works, set up SSH key auth for convenience:
ssh-copy-id newwaveclaw@192.168.1.158
```

## Step 10: Install Tailscale on DGX Spark

```bash
# On the DGX Spark:

# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Start and authenticate
sudo tailscale up

# This will print an authentication URL. Open it in a browser,
# log in to your Tailscale account, and authorize the device.

# Verify Tailscale connectivity
tailscale status

# You should see both devices:
#   100.79.80.119   minisforum    newwaveclaw@...
#   100.x.x.x      dgx-spark     newwaveclaw@...

# Note the DGX Spark's Tailscale IP for future reference
tailscale ip -4
```

## Step 11: Verify Cross-Machine Connectivity

```bash
# From Minisforum, ping DGX via LAN:
ping -c 3 192.168.1.158

# From Minisforum, ping DGX via Tailscale:
ping -c 3 <DGX_TAILSCALE_IP>

# From DGX, ping Minisforum via LAN:
ping -c 3 192.168.1.157

# From DGX, ping Minisforum via Tailscale:
ping -c 3 100.79.80.119

# Test SSH over Tailscale:
ssh newwaveclaw@<DGX_TAILSCALE_IP>
```

## Step 12: Post-Recovery Housekeeping

```bash
# On the DGX Spark:

# Update all packages
sudo apt update && sudo apt upgrade -y

# Verify NVIDIA container toolkit is installed (needed for NemoClaw)
dpkg -l | grep nvidia-container-toolkit

# If not installed:
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker

# Install Docker if not already present
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
# Log out and back in for group membership to take effect

# Verify Docker can see the GPU
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

## Troubleshooting

### USB drive not showing in boot menu
- Try a different USB port (use USB-A, not USB-C if possible).
- Recreate the USB drive using a different method (try Etcher if dd failed).
- Ensure the USB was not removed prematurely during creation.

### Recovery fails midway
- Re-flash the USB drive and try again.
- Try a different USB drive (some drives have bad sectors).
- Ensure the DGX Spark has stable power throughout.

### No display output
- Try both HDMI and DisplayPort if available.
- Try a different cable.
- The DGX Spark may take 30-60 seconds to show output on cold boot.

### Network not detected after recovery
- Check the Ethernet cable is firmly connected.
- Try: `sudo dhclient -v` to manually request DHCP.
- Check router to see if the MAC address was assigned a different IP.

### nvidia-smi not working after recovery
- Reboot the system first: `sudo reboot`
- If still failing: `sudo apt install --reinstall nvidia-driver-xxx` (replace xxx with the version from DGX OS).

---

**Next step**: Proceed to `02_MINISFORUM_UPGRADE.md` to upgrade the Minisforum control plane.

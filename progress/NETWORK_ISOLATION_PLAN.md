# Network Isolation Plan: NewFire AI Homelab

**Date:** April 6, 2026
**Status:** Ready to execute
**Estimated time:** 30-45 minutes

---

## Table of Contents

1. [Network Topology Diagram](#1-network-topology-diagram)
2. [Subnet Scheme](#2-subnet-scheme)
3. [Step-by-Step: GL.iNet Admin Panel Configuration](#3-step-by-step-glinet-admin-panel-configuration)
4. [Firewall Rules (GUI + CLI Backup)](#4-firewall-rules-gui--cli-backup)
5. [Static IPs / DHCP Reservations](#5-static-ips--dhcp-reservations)
6. [Verification Checklist](#6-verification-checklist)
7. [Troubleshooting](#7-troubleshooting)
8. [Rollback Plan](#8-rollback-plan)

---

## 1. Network Topology Diagram

### BEFORE (Current State - Flat / Shared Network)

```
                        INTERNET (ISP)
                            |
                     [ Fios Router ]
                    192.168.1.0/24
                   /       |        \
                  /        |         \
         Personal      Brazil       GL.iNet Travel Router
         Devices       Router         192.168.8.1
        (phones,     (second AP)        /         \
         laptops,                      /           \
         TV, etc.)              Minisforum       DGX Spark
                                X1 Pro 370
                              (192.168.8.x)   (192.168.8.x)

    PROBLEM: All devices share connectivity. A breach of the homelab
    could pivot to personal devices. Personal devices can reach homelab.
```

### AFTER (Isolated Homelab Subnet)

```
                        INTERNET (ISP)
                            |
                     [ Fios Router ]
                    192.168.1.0/24
                   /       |        \
                  /        |         \
         Personal      Brazil       GL.iNet Travel Router
         Devices       Router       WAN: 192.168.1.x (from Fios DHCP)
        (phones,     (second AP)    LAN: 192.168.10.0/24  <-- NEW SUBNET
         laptops,                       |
         TV, etc.)                      |
                                   [ FIREWALL ]
                             DROP all inbound from
                              192.168.1.0/24
                                   |
                          +--------+--------+
                          |                 |
                     Minisforum         DGX Spark
                     X1 Pro 370
                   192.168.10.10      192.168.10.20
                  (Control Plane)    (GPU Compute)
                          |                 |
                          +--------+--------+
                                   |
                          [ Tailscale / OpenZiti ]
                          Overlay for admin SSH
                          (your Mac connects here)

    RESULT:
      - Homelab can reach internet (outbound through Fios) ... YES
      - Personal devices can reach homelab .................. NO  (blocked)
      - Fios/Brazil devices can scan/probe homelab .......... NO  (blocked)
      - You can SSH in via Tailscale/OpenZiti ............... YES (overlay)
```

### Key Isolation Principle

The GL.iNet router performs **NAT** (Network Address Translation) between its WAN
(Fios side, 192.168.1.0/24) and its LAN (homelab side, 192.168.10.0/24). This means:

- **Outbound (homelab to internet):** Traffic is NATed through the GL.iNet WAN IP.
  The Fios router sees all homelab traffic as coming from a single IP (the GL.iNet
  WAN address). This works by default.

- **Inbound (Fios/personal to homelab):** NAT **already blocks** unsolicited inbound
  connections by default. Devices on the Fios network cannot initiate connections to
  192.168.10.x addresses because those addresses do not exist on the Fios subnet.
  We will add explicit firewall rules as defense-in-depth.

---

## 2. Subnet Scheme

| Network        | Subnet            | Gateway        | Purpose                  |
|----------------|--------------------|----------------|--------------------------|
| Fios (home)    | 192.168.1.0/24     | 192.168.1.1    | Personal devices, internet uplink |
| Brazil Router  | 192.168.1.0/24 (bridged) or own subnet | varies | Personal devices (second AP) |
| GL.iNet WAN    | 192.168.1.x (DHCP from Fios) | 192.168.1.1 | Uplink to internet via Fios |
| **GL.iNet LAN**| **192.168.10.0/24**| **192.168.10.1**| **Homelab isolated subnet** |

### Static IP Assignments

| Device              | IP Address       | MAC Address        | Hostname        | Role            |
|---------------------|------------------|--------------------|-----------------|-----------------|
| GL.iNet Router      | 192.168.10.1     | (router itself)    | glinet-gw       | Gateway         |
| Minisforum X1 Pro   | 192.168.10.10    | (find via `ip link`)| minisforum     | Control Plane   |
| DGX Spark           | 192.168.10.20    | (find via `ip link`)| dgx-spark      | GPU Compute     |
| DHCP Pool (spare)   | 192.168.10.100-199 | ---              | ---             | Future devices  |

> **Why 192.168.10.0/24?** It avoids conflict with the Fios router (192.168.1.0/24)
> and the GL.iNet default (192.168.8.0/24). Clean separation, easy to remember.

---

## 3. Step-by-Step: GL.iNet Admin Panel Configuration

### Prerequisites

- Laptop/Mac connected to the GL.iNet router (via WiFi or Ethernet)
- GL.iNet admin password
- Know the MAC addresses of both homelab machines (get them first; see Step 0)

---

### Step 0: Gather MAC Addresses

Before changing anything, SSH into each machine and record its MAC address.

**On Minisforum (via Tailscale SSH):**

```bash
ip link show | grep -A1 'state UP'
# Look for the interface connected to the GL.iNet (usually eth0 or enp*)
# Record the MAC address (e.g., aa:bb:cc:dd:ee:f1)
```

**On DGX Spark (via Tailscale SSH):**

```bash
ip link show | grep -A1 'state UP'
# Record the MAC address (e.g., aa:bb:cc:dd:ee:f2)
```

Write these down. You will need them for DHCP reservations.

---

### Step 1: Change the GL.iNet LAN Subnet

1. Open a browser and go to **http://192.168.8.1**
2. Log in with your admin password
3. Navigate to **NETWORK** (left sidebar) --> **LAN**
4. Under **LAN Settings / Basic Settings:**
   - Change **IP Address** from `192.168.8.1` to `192.168.10.1`
   - Set **Netmask** to `255.255.255.0`
5. Under **DHCP Server** settings:
   - Set **Start IP** to `192.168.10.100`
   - Set **End IP** to `192.168.10.199`
   - Set **Lease Time** to `86400` (24 hours) or leave default
6. Click **Apply**

> **WARNING:** After applying, you will lose connection to the router. Reconnect
> to the GL.iNet WiFi/Ethernet and access the admin panel at the NEW address:
> **http://192.168.10.1**

---

### Step 2: Verify WAN Connection

1. Go to **http://192.168.10.1** and log in
2. Navigate to **INTERNET** (left sidebar)
3. Confirm the WAN interface shows:
   - **Protocol:** DHCP (getting an IP from Fios)
   - **IP Address:** Something in `192.168.1.x` range
   - **Gateway:** `192.168.1.1`
   - **Status:** Connected
4. If not connected, verify the Ethernet cable from GL.iNet WAN port to Fios router

---

### Step 3: Set Up DHCP Reservations (Static IPs)

1. Navigate to **NETWORK** --> **LAN**
2. Scroll down to **Address Reservation** section
3. Click **Add** to create a new reservation:

   **Reservation 1 (Minisforum):**
   - **MAC Address:** `<MAC from Step 0>`
   - **IP Address:** `192.168.10.10`
   - **Hostname:** `minisforum` (optional, if the field exists)
   - Click **Apply** or **Save**

   **Reservation 2 (DGX Spark):**
   - **MAC Address:** `<MAC from Step 0>`
   - **IP Address:** `192.168.10.20`
   - **Hostname:** `dgx-spark` (optional)
   - Click **Apply** or **Save**

4. **Reboot both machines** (or restart their network interfaces) so they pick up the new IPs:

   ```bash
   # On each machine via Tailscale SSH:
   sudo dhclient -r && sudo dhclient
   # Or:
   sudo systemctl restart NetworkManager
   # Or simply:
   sudo reboot
   ```

5. Verify each machine got its assigned IP:

   ```bash
   ip addr show | grep 192.168.10
   ```

---

### Step 4: Configure Firewall (GL.iNet Admin Panel)

The GL.iNet admin panel has a simplified firewall interface. By default, NAT already
blocks unsolicited inbound traffic from the WAN side. But we want to be explicit.

1. Navigate to **FIREWALL** (left sidebar)
2. Check these settings:

   **Open Ports on Router:**
   - Ensure **no ports are forwarded** from WAN to LAN
   - Delete any existing port forward rules (unless you specifically need them)
   - There should be ZERO port forwards listed

   **DMZ:**
   - Ensure DMZ is **disabled** (DMZ exposes a LAN device to all WAN traffic)

3. If your GL.iNet firmware version (v4.x) has a **Firewall Rules** or **Traffic Rules** section:
   - Ensure the default WAN-to-LAN policy is **REJECT** or **DROP**
   - This is usually the default on GL.iNet routers

---

### Step 5: Advanced Firewall via LuCI (Defense-in-Depth)

The GL.iNet admin panel is limited for custom firewall rules. For explicit blocking,
use the LuCI (OpenWrt) interface:

1. Navigate to **SYSTEM** --> **Advanced Settings** (or **More Settings** --> **Advanced**)
2. Click to enter the **LuCI** interface
3. Log in (same password as GL.iNet admin panel)

#### 5a. Verify Zone Configuration

4. In LuCI, go to **Network** --> **Firewall**
5. You should see two zones:
   - **lan** zone: Input: ACCEPT, Output: ACCEPT, Forward: ACCEPT
   - **wan** zone: Input: REJECT, Output: ACCEPT, Forward: REJECT
6. Verify the **wan --> lan** forwarding is set to **REJECT** (this is default)
7. Verify **Masquerading** is enabled on the **wan** zone (this is NAT)

#### 5b. Add Custom Firewall Rules

8. In LuCI, go to **Network** --> **Firewall** --> **Custom Rules** tab
9. Add the following rules at the bottom of the text box:

```bash
# ============================================================
# NewFire Homelab Isolation Rules
# Block ALL inbound traffic from Fios/personal subnet
# ============================================================

# Block any traffic from Fios subnet (192.168.1.0/24) destined for homelab LAN
iptables -I FORWARD -s 192.168.1.0/24 -d 192.168.10.0/24 -j DROP

# Block any traffic from common home subnets (defense-in-depth)
iptables -I FORWARD -s 192.168.0.0/24 -d 192.168.10.0/24 -j DROP
iptables -I FORWARD -s 192.168.2.0/24 -d 192.168.10.0/24 -j DROP

# Block any INPUT to the router itself from the upstream Fios subnet
# (except DHCP, which the router needs to get its WAN IP)
iptables -I INPUT -s 192.168.1.0/24 -p tcp -j DROP
iptables -I INPUT -s 192.168.1.0/24 -p udp --dport 1:66 -j DROP
iptables -I INPUT -s 192.168.1.0/24 -p udp --dport 69:65535 -j DROP
# (UDP port 67-68 is DHCP -- we leave that open so the GL.iNet can get its WAN IP)

# Log any blocked attempts (optional, for debugging -- check with `logread`)
iptables -I FORWARD -s 192.168.1.0/24 -d 192.168.10.0/24 -j LOG --log-prefix "HOMELAB-BLOCK: " --log-level 4
```

10. Click **Submit** to save
11. Click **Save & Apply** on the main Firewall page

> **Note:** These custom rules persist across reboots on GL.iNet routers.

---

## 4. Firewall Rules (CLI Backup via SSH)

If the LuCI custom rules interface is not available, you can SSH into the GL.iNet
router directly and add the rules manually.

### SSH into the GL.iNet Router

```bash
ssh root@192.168.10.1
# Password is the same as the admin panel password
```

### Add Firewall Rules

```bash
# View current rules
iptables -L -n -v

# Add blocking rules
iptables -I FORWARD -s 192.168.1.0/24 -d 192.168.10.0/24 -j DROP
iptables -I FORWARD -s 192.168.0.0/24 -d 192.168.10.0/24 -j DROP
iptables -I FORWARD -s 192.168.2.0/24 -d 192.168.10.0/24 -j DROP

# Block input to router from upstream (except DHCP)
iptables -I INPUT -s 192.168.1.0/24 -p tcp -j DROP
iptables -I INPUT -s 192.168.1.0/24 -p udp --dport 1:66 -j DROP
iptables -I INPUT -s 192.168.1.0/24 -p udp --dport 69:65535 -j DROP
```

### Make Rules Persistent

To persist rules across reboots, add them to the GL.iNet custom firewall script:

```bash
# Edit the custom firewall script
vi /etc/firewall.user
```

Add the same iptables rules from above into that file. They will be executed
each time the firewall restarts.

Alternatively, if using the newer firmware:

```bash
# Check if this path exists on your model
cat /etc/config/firewall
# Look for the "custom rules" section and add there
```

### Verify Rules Are Active

```bash
iptables -L FORWARD -n -v | head -20
iptables -L INPUT -n -v | head -20
```

You should see the DROP rules at the top of each chain.

---

## 5. Static IPs / DHCP Reservations

### Option A: DHCP Reservation on GL.iNet (Recommended)

Already covered in Step 3 above. The router assigns a fixed IP based on MAC address.

### Option B: Static IP on the Machines Themselves

If DHCP reservation does not work on your GL.iNet model, configure static IPs
directly on each Ubuntu machine.

**On Minisforum X1 Pro (via Tailscale SSH):**

```bash
# Find the network interface name
ip link show
# Usually: eth0, enp1s0, eno1, or similar

# Create a netplan config for static IP
sudo tee /etc/netplan/01-homelab-static.yaml << 'NETPLAN_EOF'
network:
  version: 2
  ethernets:
    enp1s0:                    # <-- CHANGE to your actual interface name
      dhcp4: no
      addresses:
        - 192.168.10.10/24
      routes:
        - to: default
          via: 192.168.10.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 1.1.1.1
          - 192.168.10.1
NETPLAN_EOF

# Apply (WARNING: this will change the IP immediately)
sudo netplan apply
```

**On DGX Spark (via Tailscale SSH):**

```bash
sudo tee /etc/netplan/01-homelab-static.yaml << 'NETPLAN_EOF'
network:
  version: 2
  ethernets:
    enp1s0:                    # <-- CHANGE to your actual interface name
      dhcp4: no
      addresses:
        - 192.168.10.20/24
      routes:
        - to: default
          via: 192.168.10.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 1.1.1.1
          - 192.168.10.1
NETPLAN_EOF

sudo netplan apply
```

> **Note:** If the machines use NetworkManager instead of netplan, use `nmcli` instead:
>
> ```bash
> # Find connection name
> nmcli con show
>
> # Set static IP (replace "Wired connection 1" with actual name)
> sudo nmcli con mod "Wired connection 1" \
>   ipv4.method manual \
>   ipv4.addresses 192.168.10.10/24 \
>   ipv4.gateway 192.168.10.1 \
>   ipv4.dns "8.8.8.8,1.1.1.1"
>
> sudo nmcli con up "Wired connection 1"
> ```

---

## 6. Verification Checklist

Run these tests **after completing all configuration steps**.

### Test 1: Homelab Machines Can Reach the Internet

```bash
# On Minisforum (via Tailscale SSH):
ping -c 3 8.8.8.8                    # Should succeed
ping -c 3 google.com                 # Should succeed (DNS works)
curl -s https://api.openrouter.ai    # Should get a response (API access works)
docker pull hello-world              # Should succeed (Docker Hub access works)

# On DGX Spark (via Tailscale SSH):
ping -c 3 8.8.8.8                    # Should succeed
ping -c 3 google.com                 # Should succeed
```

### Test 2: Homelab Machines Have Correct IPs

```bash
# On Minisforum:
ip addr show | grep 192.168.10       # Should show 192.168.10.10

# On DGX Spark:
ip addr show | grep 192.168.10       # Should show 192.168.10.20
```

### Test 3: Homelab Machines Can Reach Each Other

```bash
# From Minisforum:
ping -c 3 192.168.10.20              # Should succeed (reach DGX Spark)

# From DGX Spark:
ping -c 3 192.168.10.10              # Should succeed (reach Minisforum)
```

### Test 4: Personal Devices CANNOT Reach Homelab

From a personal device on the Fios network (phone, laptop connected to Fios WiFi):

```bash
# From personal laptop on Fios (192.168.1.x):
ping 192.168.10.10                   # Should FAIL (timeout / no route)
ping 192.168.10.20                   # Should FAIL (timeout / no route)
ping 192.168.10.1                    # Should FAIL (timeout / no route)

# Try to access GL.iNet admin panel from Fios network:
curl http://192.168.10.1             # Should FAIL (connection refused/timeout)

# Try SSH:
ssh newwaveclaw@192.168.10.10        # Should FAIL (timeout)
```

> **Expected behavior:** These should all time out or return "no route to host."
> Since the homelab is on a different subnet (192.168.10.x) behind the GL.iNet NAT,
> the Fios router does not know how to route to it. Even if someone adds a static
> route on the Fios router, the iptables rules on the GL.iNet will DROP the traffic.

### Test 5: Tailscale / OpenZiti Still Works

```bash
# From your Mac (via Tailscale):
ssh newwaveclaw@100.79.80.119        # Should succeed (Tailscale IP for Minisforum)
ssh newwave-dgx@100.88.112.5         # Should succeed (Tailscale IP for DGX Spark)

# Verify services are accessible via Tailscale:
curl http://100.79.80.119:18789      # OpenClaw gateway
curl http://100.79.80.119:9080       # APISIX
curl http://100.88.112.5:3000        # OpenHands
```

### Test 6: Verify Firewall Rules Are Active (on GL.iNet)

```bash
# SSH into GL.iNet router:
ssh root@192.168.10.1

# Check iptables rules:
iptables -L FORWARD -n -v | grep DROP
# Should show rules blocking 192.168.1.0/24 --> 192.168.10.0/24

iptables -L INPUT -n -v | grep DROP
# Should show rules blocking input from 192.168.1.0/24

# Check for any blocked traffic in logs:
logread | grep "HOMELAB-BLOCK"
# If someone tried to reach the homelab from Fios, you will see log entries here
```

### Quick Verification Summary

| Test | Expected Result | Pass? |
|------|----------------|-------|
| Minisforum pings 8.8.8.8 | Success | [ ] |
| DGX Spark pings 8.8.8.8 | Success | [ ] |
| Minisforum pings google.com | Success | [ ] |
| Minisforum has IP 192.168.10.10 | Yes | [ ] |
| DGX Spark has IP 192.168.10.20 | Yes | [ ] |
| Minisforum pings DGX Spark | Success | [ ] |
| Personal device pings 192.168.10.10 | Timeout/Fail | [ ] |
| Personal device pings 192.168.10.1 | Timeout/Fail | [ ] |
| Tailscale SSH to Minisforum | Success | [ ] |
| Tailscale SSH to DGX Spark | Success | [ ] |
| OpenClaw accessible via Tailscale | Success | [ ] |
| No port forwards exist on GL.iNet | Confirmed | [ ] |
| iptables DROP rules active | Confirmed | [ ] |

---

## 7. Troubleshooting

### "I can't reach the GL.iNet admin panel after changing the subnet"

- Disconnect and reconnect to the GL.iNet WiFi
- Your device should get a new IP in the 192.168.10.x range via DHCP
- Try http://192.168.10.1 in your browser
- If still unreachable, hard reset: hold the GL.iNet reset button for 10 seconds
  (this resets to factory defaults at 192.168.8.1)

### "Homelab machines lost internet after the change"

1. Check that the GL.iNet WAN is connected to the Fios router
2. On the GL.iNet admin panel, go to INTERNET and verify WAN has an IP
3. On the homelab machines, check their default gateway:
   ```bash
   ip route | grep default
   # Should show: default via 192.168.10.1
   ```
4. If using static IPs (Option B), verify the gateway is set to 192.168.10.1

### "Homelab machines can't reach each other"

- Both machines must be on the same 192.168.10.0/24 subnet
- Verify with `ip addr show` on each machine
- Check that there are no host-level firewall rules blocking:
  ```bash
  sudo ufw status
  # If UFW is active, ensure it allows traffic from 192.168.10.0/24
  sudo ufw allow from 192.168.10.0/24
  ```

### "Tailscale stopped working"

- Tailscale works independently of the LAN subnet change
- Verify Tailscale is running: `sudo tailscale status`
- If Tailscale lost connection, it may need internet access to re-establish:
  ```bash
  sudo systemctl restart tailscaled
  ```

### "Docker containers can't pull images"

- This means outbound internet is broken
- Check DNS resolution: `nslookup docker.io`
- If DNS fails, check /etc/resolv.conf or set DNS explicitly on the GL.iNet DHCP

---

## 8. Rollback Plan

If something goes wrong and you need to undo everything quickly:

### Quick Rollback (Reset GL.iNet to defaults)

1. Hold the **Reset** button on the GL.iNet router for **10 seconds**
2. Router resets to factory defaults (192.168.8.1, DHCP enabled)
3. Reconnect to the GL.iNet WiFi
4. Access admin panel at http://192.168.8.1
5. Both homelab machines will get 192.168.8.x addresses via DHCP again

### If You Used Static IPs on the Machines

```bash
# On each machine (via Tailscale SSH):
sudo rm /etc/netplan/01-homelab-static.yaml
sudo netplan apply
# Or for NetworkManager:
sudo nmcli con mod "Wired connection 1" ipv4.method auto
sudo nmcli con up "Wired connection 1"
```

### Remove Custom Firewall Rules

```bash
# SSH into GL.iNet:
ssh root@192.168.10.1  # (or 192.168.8.1 if reset)

# Flush custom rules
iptables -D FORWARD -s 192.168.1.0/24 -d 192.168.10.0/24 -j DROP
iptables -D FORWARD -s 192.168.0.0/24 -d 192.168.10.0/24 -j DROP
iptables -D FORWARD -s 192.168.2.0/24 -d 192.168.10.0/24 -j DROP

# Or just restart the firewall to reload defaults:
/etc/init.d/firewall restart
```

---

## Execution Order (Do This Tomorrow)

```
1. [ ] Gather MAC addresses from both machines (Step 0)
2. [ ] Change GL.iNet LAN subnet to 192.168.10.0/24 (Step 1)
3. [ ] Reconnect to GL.iNet at new address 192.168.10.1
4. [ ] Verify WAN/internet still works (Step 2)
5. [ ] Add DHCP reservations for Minisforum and DGX Spark (Step 3)
6. [ ] Restart networking on both machines to pick up new IPs
7. [ ] Verify static IPs assigned correctly (Test 2)
8. [ ] Remove any port forwards / disable DMZ (Step 4)
9. [ ] Add iptables rules via LuCI or SSH (Step 5)
10. [ ] Run full verification checklist (Section 6)
11. [ ] Celebrate. Homelab is isolated!
```

---

## References

- [GL.iNet Firewall Docs (v4)](https://docs.gl-inet.com/router/en/4/interface_guide/firewall/)
- [GL.iNet LAN Configuration (v4)](https://docs.gl-inet.com/router/en/4/interface_guide/lan/)
- [GL.iNet Static IP Guide](https://docs.gl-inet.com/router/en/4/tutorials/manually_configure_static_ip/)
- [GL.iNet Advanced Settings / LuCI](https://docs.gl-inet.com/router/en/4/interface_guide/advanced_settings/)
- [GL.iNet Guest Network Isolation](https://docs.gl-inet.com/router/en/4/interface_guide/guest_network/)
- [GL.iNet NAT Settings](https://docs.gl-inet.com/router/en/4/interface_guide/nat_settings/)
- [GL.iNet Forum: Isolated Network Discussion](https://forum.gl-inet.com/t/isolated-network-for-devices/44537)
- [GL.iNet Forum: DHCP Reservation](https://forum.gl-inet.com/t/dhcp-reservation-and-or-static-ip/59050)

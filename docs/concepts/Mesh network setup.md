---
tags: [concept]
---
# Mesh network setup

Every node joins one BATMAN-adv mesh over 802.11 IBSS (ad-hoc). The mesh is started by hand with a
`start-mesh.sh` script on each node, not at boot. These settings must match on every node:

| Setting | Value |
|---|---|
| IBSS SSID | `robot-mesh` |
| Channel | 1 (2412 MHz), `fixed-freq` |
| Routing algorithm | `BATMAN_IV` (the default) |
| Regulatory domain | `IN` |
| Subnet | `192.168.123.0/24` on `bat0` |

| Node | `bat0` address | Wi-Fi interface | Scripts |
|---|---|---|---|
| Laptop (explorer side) | 192.168.123.1 | `wlp0s20f3` | `~/demo_com/start-mesh.sh`, `stop-mesh.sh` |
| Moving Pi 4 ([[Receiver (external)]]) | 192.168.123.2 | `wlan0` | `~/demo_com/start-mesh.sh` on the Pi |
| Pi Zero 2 W (repeater, `ssh node1@192.168.123.3`) | 192.168.123.3 | `wlan0` | `~/demo/` on the Zero; source in `~/demo_com/pi-zero-2w/` on the laptop |
| spare | 192.168.123.4 | `wlan0` | |

Repeater walk tests: [[Relay field tests 2026-10-17]].

## Time sync
The laptop's chrony serves time to `192.168.123.0/24` (`allow`, `local stratum 10 orphan`). The Pis have
no RTC, so each `start-mesh.sh` syncs its clock from 192.168.123.1 at the end. Why this needs to be
explicit: [[Known limitations]] #21.

## Pi Zero 2 W scripts
The Zero runs Raspberry Pi OS Lite 64-bit (Debian 13 Trixie, kernel 6.18, NetworkManager,
systemd-timesyncd, batman-adv 2025.4). `iw`, `batctl` and `rfkill` are preinstalled but live in
`/usr/sbin`, which isn't on a normal user's PATH, so always run the scripts with `sudo`.

`sudo ./start-mesh.sh [NODE_IP]`:
- checks that the Wi-Fi chip supports IBSS and that `batman-adv` loads
- releases `wlan0` from NetworkManager and wpa_supplicant
- runs `rfkill unblock wifi`, because Raspberry Pi OS blocks Wi-Fi until a country is set
- **scans for the live `robot-mesh` IBSS cell and joins its BSSID.** brcmfmac doesn't merge IBSS
  cells, so the Zero must join the existing cell's BSSID. That BSSID is random and changes whenever
  the laptop restarts its mesh, so it can't be hardcoded. `FALLBACK_BSSID` is used only when the
  scan finds nothing.
- turns off brcmfmac power save
- recreates `bat0` with a fixed MAC (`wlan0`'s with the locally-administered bit set), so the other
  nodes' ARP caches stay valid across restarts, then sends a gratuitous ARP
- refuses an address another node already has (iputils `arping -D`)
- waits up to 120 s for the laptop, printing the best TQ. A new `bat0` starts with an empty
  originator table and BATMAN IV rebuilds TQ from one OGM per second. Ping works once TQ to the
  laptop is around 150, which took 27–95 s in tests
- syncs the clock through systemd-timesyncd and a runtime drop-in
  (`/run/systemd/timesyncd.conf.d/mesh.conf`). It waits for an actual reply from the laptop,
  because `NTPSynchronized` can still be `yes` from an earlier internet sync

The `wlan0` maximum MTU is 1500, so batman-adv fragments full-size frames on the Zero.

If it is run over SSH on `wlan0` or `bat0`, it detaches itself and logs to `/tmp/start-mesh.log`,
so losing the session doesn't stop it halfway. `stop-mesh.sh` removes `bat0`, puts `wlan0` back in
managed mode, removes the timesyncd drop-in, restarts wpa_supplicant and hands `wlan0` back to
NetworkManager.

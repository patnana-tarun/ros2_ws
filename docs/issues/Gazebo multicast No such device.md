---
tags: [issue]
---
# Gazebo multicast No such device

**Symptom.** During a sim run, the launch terminal keeps printing:

```
Exception sending a multicast message: No such device
```

It repeats about once a second until Gazebo restarts. It doesn't come from any ROS node and
doesn't appear in `~/.ros/log`.

**Cause.** Gazebo's own transport (gz-transport, also used by `ros_gz_bridge`) finds its peers
by multicasting to 239.255.0.7 on every IPv4 interface that existed when it started. This
laptop's internet comes from a phone (vivo, RNDIS) tethered over USB (`enx1e7d49cca061`,
10.144.47.x, default route). The tether drops and comes back every few minutes. On 2026-10-18,
after about 23 h of uptime, the phone was on USB device number 31, and `journalctl` showed 6
removals between 10:50 and 11:02. Each reconnect creates a new interface index, even though the
name and IP stay the same. Linux records the index when the socket picks its multicast
interface, so Gazebo's socket keeps pointing at the old index, and every send fails with
`ENODEV` ("No such device").

**Effect.** Not noticeable so far. All gz traffic used `bat0` (192.168.123.1), and `/clock` and
`/scan` each had exactly one publisher. But this shows that the sim depends on `bat0`: Gazebo
uses it as its address, and ROS discovery goes through the server on 192.168.123.1
([[Discovery server not running]]). Gazebo's discovery multicast also goes out over the mesh.

**Check first** if a similar network or discovery error shows up:

```bash
journalctl --since "-1h" | grep "enx.*'removed'"   # tether flaps
journalctl -k | grep "vivo"                         # USB re-enumerations
ip -br addr
```

**Possible fixes (not applied: it has no effect on runs yet).**
- `GZ_IP=127.0.0.1` for the Gazebo launch, so gz-transport uses only loopback.
- A different cable or port, or the phone's Wi-Fi hotspot instead of USB tethering.
- Restarting the sim clears it until the next drop.

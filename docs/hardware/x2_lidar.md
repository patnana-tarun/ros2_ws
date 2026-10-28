---
tags: [robot]
source: src/explorer_bringup/explorer_bringup/x2_lidar.py
---
# x2_lidar

Pure-Python driver for the **YDLIDAR X2**: serial packets → `/scan`
(`sensor_msgs/LaserScan`, frame `laser_frame`, 360 beams, ~7 Hz). Written because the vendor
`ydlidar_ros2_driver` needs the YDLidar-SDK built from source and isn't packaged for Jazzy;
it can still be used with `lidar:=ydlidar` if built.

## The X2's packets
The X2 takes no commands: powered (and its motor switched on through DTR) it spins and
streams at 115200 baud, little-endian:

| Bytes | Field | Meaning |
|-------|-------|---------|
| 2 | `AA 55` | header |
| 1 | CT | bit 0 = 1: first packet of a new turn (carries one zero sample) |
| 1 | LSN | number of samples |
| 2 | FSA | first sample's angle: (FSA >> 1) / 64 degrees |
| 2 | LSA | last sample's angle, same coding |
| 2 | CS | XOR of all 16-bit words of the packet except CS |
| 2 × LSN | Si | distance = Si / 4 mm; 0 = no return |

Angles are spread evenly from FSA to LSA, then corrected per sample (the X2 is a
triangulation sensor): `angle += atan(21.8 × (155.3 − d) / (155.3 × d))` degrees, d in mm.
The correction is −5.5° at 0.5 m, −6.8° at 1 m and −7.9° at 8 m, so it matters. The X2 turns
**clockwise**; angles are clockwise from the X2's zero mark.

## What the node does
- Reads the port every 5 ms, finds headers, checks each packet's checksum; on a bad packet it
  drops two bytes and searches again (resync), so noise costs one packet, not the scan.
- Collects one turn (between two start packets) and publishes it as a scan of `beams` fixed
  bins, keeping the nearest point per bin. Every scan has the same size, which SLAM Toolbox
  needs. Empty bins are `inf`. Turns with fewer than `beams`/4 points are dropped.
- Converts to ROS angles (counter-clockwise, −180°..180°): `angle_ros = −angle_x2 + angle_offset_deg`.
- Stamps the scan with the time its turn started; `scan_time` = measured turn time.
- Reconnects after an unplug; warns every 5 s if no scans come (wrong port, motor off).

## Parameters (`config/robot.yaml`)
| Name | Default | Meaning |
|------|---------|---------|
| `port` | `/dev/ttyUSB1` (launch: `lidar_port`) | device or pyserial URL |
| `beams` | 360 | bins per scan (1°); the X2 gives ~430 points per turn at 7 Hz |
| `range_min`, `range_max` | 0.12, 8.0 | m; outside → not used (SLAM uses up to 7.5 m) |
| `inverted` | true | clockwise X2 → counter-clockwise ROS |
| `angle_offset_deg` | 0.0 | turns the scan so 0° = robot forward; calibrate ([[Hardware bring-up]], step 5) |
| `motor_dtr` | true | DTR level that runs the motor; flip if the X2 doesn't spin |
| `frame_id` | `laser_frame` | URDF frame at the LiDAR, 79 mm ahead of `base_footprint` |

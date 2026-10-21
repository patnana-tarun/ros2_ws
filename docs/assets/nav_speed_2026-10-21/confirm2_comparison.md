# Comparison

Folders: /home/shadows/ros2_ws/tools/rover_mcp/runs/20261021_044543_exp_navspeed_confirm2

| metric | base (n=3) | cand (n=3) |
|---|---|---|
| final coverage % | 95.03 ± 0.06  (95, 95, 95.1) | 95.10 ± 0.10  (95.1, 95, 95.2) |
| minutes to stop | 10.42 ± 0.95  (11.5, 9.75, 10) | 9.62 ± 2.63  (7.91, 12.7, 8.3) |
| xte mean cm (all) | 2.07 ± 0.15  (2.2, 1.9, 2.1) | 1.67 ± 0.06  (1.7, 1.6, 1.7) |
| heading dev mean deg | 7.80 ± 0.79  (8.7, 7.5, 7.2) | 5.43 ± 0.25  (5.2, 5.7, 5.4) |
| large deviation % (all) | 2.90 ± 1.22  (4.3, 2.1, 2.3) | 1.23 ± 0.06  (1.3, 1.2, 1.2) |
| large deviation % (tunnel) | 3.03 ± 1.55  (4.6, 3, 1.5) | 1.30 ± 0.40  (1.7, 0.9, 1.3) |
| rotation events | 1.67 ± 0.58  (2, 2, 1) | 1.00 ± 0.00  (1, 1, 1) |
| stall episodes | 0.00 ± 0.00  (0, 0, 0) | 0.00 ± 0.00  (0, 0, 0) |
| stuck % of time | 2.00 ± 0.35  (2.4, 1.8, 1.8) | 3.77 ± 2.81  (1.9, 7, 2.4) |
| turn on spot % of time | 10.73 ± 1.27  (10.1, 12.2, 9.9) | 6.57 ± 0.71  (5.8, 7.2, 6.7) |
| reverse m | 4.89 ± 0.95  (5.84, 3.95, 4.87) | 5.11 ± 3.56  (1.68, 8.79, 4.85) |
| distance m | 55.60 ± 1.27  (55.9, 54.2, 56.7) | 58.07 ± 12.54  (50.3, 72.5, 51.4) |
| goals reached | 13.00 ± 1.73  (12, 15, 12) | 4.33 ± 0.58  (4, 5, 4) |
| goals given up | 2.00 ± 1.73  (4, 1, 1) | 1.33 ± 1.53  (1, 3, 0) |
| no-progress cancels | 0.33 ± 0.58  (1, 0, 0) | 0.33 ± 0.58  (0, 1, 0) |
| plans through unknown | 2.67 ± 2.31  (0, 4, 4) | 27.00 ± 44.17  (2, 78, 1) |

## Runs

| run | stop | minutes | coverage % |
|---|---|---|---|
| base_1 | reached_95 | 11.5 | 95.0 |
| base_2 | reached_95 | 9.8 | 95.0 |
| base_3 | reached_95 | 10.0 | 95.1 |
| cand_1 | reached_95 | 7.9 | 95.1 |
| cand_2 | reached_95 | 12.7 | 95.0 |
| cand_3 | reached_95 | 8.3 | 95.2 |

Definitions: tools/rover_mcp/rosview.py docstring (same as validate.py). n < 3 per arm is a hint, not a confirmed result.

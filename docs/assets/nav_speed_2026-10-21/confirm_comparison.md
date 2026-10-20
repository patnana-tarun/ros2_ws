# Comparison

Folders: /home/shadows/ros2_ws/tools/rover_mcp/runs/20261021_023719_exp_navspeed_confirm

| metric | base (n=3) | cand (n=3) |
|---|---|---|
| final coverage % | 64.47 ± 37.88  (77.9, 21.7, 93.8) | 93.60 ± 2.77  (95.1, 90.4, 95.3) |
| minutes to stop | 8.10 ± 4.16  (9.31, 3.46, 11.5) | 10.71 ± 1.31  (12, 9.35, 10.8) |
| xte mean cm (all) | 2.33 ± 0.06  (2.3, 2.4, 2.3) | 2.03 ± 0.23  (1.9, 2.3, 1.9) |
| heading dev mean deg | 8.53 ± 0.21  (8.3, 8.7, 8.6) | 7.07 ± 1.10  (7, 8.2, 6) |
| large deviation % (all) | 2.80 ± 0.66  (2.9, 2.1, 3.4) | 1.97 ± 1.22  (1.7, 3.3, 0.9) |
| large deviation % (tunnel) | 3.07 ± 0.51  (2.5, 3.2, 3.5) | 1.90 ± 0.79  (1.3, 2.8, 1.6) |
| rotation events | 2.00 ± 2.00  (2, 0, 4) | 1.33 ± 1.53  (3, 0, 1) |
| stall episodes | 0.00 ± 0.00  (0, 0, 0) | 0.00 ± 0.00  (0, 0, 0) |
| stuck % of time | 4.80 ± 1.55  (4.7, 6.4, 3.3) | 8.53 ± 10.64  (3, 20.8, 1.8) |
| turn on spot % of time | 11.33 ± 1.15  (11.3, 10.2, 12.5) | 6.83 ± 0.60  (7.4, 6.9, 6.2) |
| reverse m | 5.09 ± 0.44  (4.63, 5.13, 5.5) | 5.52 ± 2.07  (5.74, 3.35, 7.48) |
| distance m | 40.59 ± 23.86  (49.1, 13.7, 59) | 59.53 ± 18.76  (69.1, 37.9, 71.5) |
| goals reached | 9.00 ± 4.58  (10, 4, 13) | 31.33 ± 26.56  (16, 62, 16) |
| goals given up | 1.00 ± 1.00  (1, 0, 2) | 1.33 ± 0.58  (1, 2, 1) |
| no-progress cancels | 0.00 ± 0.00  (0, 0, 0) | 0.33 ± 0.58  (1, 0, 0) |
| plans through unknown | 0.33 ± 0.58  (1, 0, 0) | 1.00 ± 1.00  (2, 1, 0) |

## Runs

| run | stop | minutes | coverage % |
|---|---|---|---|
| base_1 | stuck_after_most | 9.3 | 77.9 |
| base_2 | complete | 3.5 | 21.7 |
| base_3 | stuck_after_most | 11.5 | 93.8 |
| cand_1 | reached_95 | 12.0 | 95.1 |
| cand_2 | stuck_after_most | 9.4 | 90.4 |
| cand_3 | reached_95 | 10.8 | 95.3 |

Definitions: tools/rover_mcp/rosview.py docstring (same as validate.py). n < 3 per arm is a hint, not a confirmed result.

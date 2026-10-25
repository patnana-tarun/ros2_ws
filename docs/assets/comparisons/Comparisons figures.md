---
tags: [moc]
---
# Comparisons figures

Charts for [[Comparisons]], one per entry. All drawn by `make_figures.py` (this folder).

- **cmp_ekf_rate.png**: EKF at 10 Hz vs 30 Hz: startup-turn overshoot per run
  ![[cmp_ekf_rate.png|400]]
- **cmp_frontier_selection.png**: frontier selection: original TAD vs depth-first vs depth-first + filter, explored area over time
  ![[cmp_frontier_selection.png|400]]
- **cmp_inflation_bt.png**: inflation and recovery settings: goals reached in 5 min
  ![[cmp_inflation_bt.png|400]]
- **cmp_nav_speed.png**: nav-speed changes vs the rotation-shim baseline: time to 95 % and early stops
  ![[cmp_nav_speed.png|400]]
- **cmp_odometry_fusion.png**: wheel odometry alone vs EKF (wheels + gyro): turn error
  ![[cmp_odometry_fusion.png|400]]
- **cmp_planner_pooled.png**: NavFn vs Smac Lattice, pooled: path shape and coverage
  ![[cmp_planner_pooled.png|400]]
- **cmp_rock_climbing.png**: bogie-first vs rocker-first: tallest rock crossed
  ![[cmp_rock_climbing.png|400]]
- **cmp_startup_hang.png**: Nav2/SLAM startup hangs before and after the delayed lifecycle startup
  ![[cmp_startup_hang.png|400]]
- **cmp_tf_rates.png**: TF rates on the robot and on the mesh, by setup
  ![[cmp_tf_rates.png|400]]
- **cmp_track_width.png**: commanded vs real turn for each sim track width
  ![[cmp_track_width.png|400]]

"""
Spawn point for cave.sdf: a random safe place, or a checked manual one (user's request,
2026-10-25: the demo should not start from (0, 0) every time).

Reads config/cave_clearance.npz (scripts/make_cave_clearance.py): per 0.1 m cell, the distance to
the nearest wall, boulder or stalagmite, 0 where the cell is rock or unreachable.
  random  a cell with >= random_clearance (0.6 m: room to turn round), and a random heading
  manual  x, y, yaw as given if the cell there has >= manual_clearance (0.3 m); otherwise the
          nearest cell with >= random_clearance, heading kept
Another world than cave.sdf: x, y, yaw as given, unchecked.

demo_record.launch.py calls choose(). From a shell it prints launch arguments for any sim launch:
    ros2 launch explorer_exploration tunnel_reverse.launch.py $(ros2 run explorer_exploration spawn_point random)
    ros2 launch explorer_exploration tunnel_reverse.launch.py $(ros2 run explorer_exploration spawn_point 9.0 -1.5 1.57)
"""

import math
import os
import random
import sys

import numpy as np
from ament_index_python.packages import get_package_share_directory

RANDOM_CLEARANCE = 0.6
MANUAL_CLEARANCE = 0.3


def load_clearance():
    path = os.path.join(get_package_share_directory('explorer_exploration'), 'config',
                        'cave_clearance.npz')
    f = np.load(path)
    return f['clear_cm'] / 100.0, float(f['res']), float(f['x0']), float(f['y0'])


def choose(mode, x=0.0, y=0.0, yaw=0.0, world='cave.sdf', seed=None):
    """(x, y, yaw, note) for mode 'random' or 'manual'."""
    if os.path.basename(world) != 'cave.sdf':
        return x, y, yaw, f'spawn at ({x:.2f}, {y:.2f}) unchecked: safe places are only known for cave.sdf'
    clear, res, x0, y0 = load_clearance()
    # plain floats: numpy scalars end up in the launch params file as objects ROS cannot parse
    cx = lambda j: round(float(x0 + j * res), 2)
    cy = lambda i: round(float(y0 + i * res), 2)
    safe = np.argwhere(clear >= RANDOM_CLEARANCE)
    if mode == 'random':
        rng = random.Random(seed)
        i, j = safe[rng.randrange(len(safe))]
        yaw = round(rng.uniform(-math.pi, math.pi), 2)
        return cx(j), cy(i), yaw, f'random spawn at ({cx(j):.2f}, {cy(i):.2f}), heading {math.degrees(yaw):.0f} deg'
    i, j = int(round((y - y0) / res)), int(round((x - x0) / res))
    c = clear[i, j] if 0 <= i < clear.shape[0] and 0 <= j < clear.shape[1] else 0.0
    if c >= MANUAL_CLEARANCE:
        return x, y, yaw, f'spawn at ({x:.2f}, {y:.2f}), {c:.2f} m from the nearest rock'
    i, j = min(safe, key=lambda p: (p[0] - i) ** 2 + (p[1] - j) ** 2)
    why = 'in rock or unreachable' if c == 0 else f'only {c:.2f} m from rock'
    return cx(j), cy(i), yaw, (f'({x:.2f}, {y:.2f}) is {why}: moved to the nearest safe place '
                               f'({cx(j):.2f}, {cy(i):.2f})')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--ros-args')]
    if args and args[0] == 'random':
        x, y, yaw, note = choose('random', seed=int(args[1]) if len(args) > 1 else None)
    elif len(args) >= 2:
        x, y, yaw, note = choose('manual', float(args[0]), float(args[1]),
                                 float(args[2]) if len(args) > 2 else 0.0)
    else:
        print('usage: spawn_point random [SEED] | spawn_point X Y [YAW]', file=sys.stderr)
        sys.exit(2)
    print(f'spawn_point: {note}', file=sys.stderr)
    print(f'x:={x:.2f} y:={y:.2f} yaw:={yaw:.2f}')


if __name__ == '__main__':
    main()

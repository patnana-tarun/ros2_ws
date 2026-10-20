# rover MCP server

Lets Claude Code run, watch, judge and tune the explorer in Gazebo + RViz. Design, metrics and
the loop: `docs/concepts/Tuning loop.md`. Step-by-step protocol: `.claude/skills/rover-tune/SKILL.md`.

## Setup (once)
```bash
cd ~/ros2_ws/tools/rover_mcp
python3 -m venv --system-site-packages .venv
.venv/bin/pip install "mcp>=1.9,<2" python-xlib mss
```
`~/ros2_ws/.mcp.json` registers it as `rover`; Claude Code asks to approve it on the next start.

## Files
| File | Role |
|---|---|
| `run.sh`, `simenv.sh` | entry point; isolated env (domain 90, localhost, GZ partition `rover_mcp`, no snap vars) |
| `server.py` | the MCP tools |
| `rosview.py` | live ROS watcher: samples, metrics, health alerts, map render |
| `x11win.py` | window capture and XTEST mouse/keyboard |
| `simproc.py` | start/stop launches, partition-based cleanup |
| `experiment.py`, `compare.py` | A/B harness from a YAML spec; per-arm comparison |
| `mcp_call.py` | call the tools from a shell: `mcp_call.py 'sim_start {}' 'observe {"seconds":60}' 'sim_stop'` |
| `runs/` | one folder per sim or experiment (git-ignored) |

Watch a sim started by hand: `source tools/rover_mcp/simenv.sh` before `ros2 launch …`.

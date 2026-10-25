"""
Demo recorder: records the Gazebo and RViz windows side by side into one MP4, as a backup video
for the review demo (user's request, 2026-10-24).

Waits for both windows, tiles them (Gazebo left half, RViz right half of the work area), then
runs ffmpeg with one x11grab input per window, each scaled and padded to half the output, and
stacks them. x11grab records screen pixels, so keep both windows uncovered while recording.
Encodes on the GPU (h264_nvenc) when it works, else libx264 ultrafast, to leave the CPU to the sim.
The MP4 is fragmented, so even a killed recording is playable. Ctrl-C stops it cleanly.

    ros2 run explorer_exploration demo_recorder                         # ~/demo_recordings/
    ros2 run explorer_exploration demo_recorder --layout screen         # whole screen instead
    ros2 run explorer_exploration demo_recorder --no-tile --rviz-title ' - RViz$'
"""

import argparse
import ctypes
import ctypes.util
import datetime
import os
import re
import signal
import subprocess
import time

# xwininfo -root -tree line: 0x4400022 "Gazebo Sim": ("gz-sim-gui" "Gazebo GUI")  1920x1011+14+49  +0+69
LINE = re.compile(r'^\s*(0x[0-9a-f]+) "(.*)": \("([^"]*)" "[^"]*"\)\s+(\d+)x(\d+)[+-]-?\d+[+-]-?\d+\s+\+?(-?\d+)\+?(-?\d+)')


def windows():
    out = subprocess.run(['xwininfo', '-root', '-tree'], capture_output=True, text=True).stdout
    for line in out.splitlines():
        m = LINE.match(line)
        if m and m.group(3) != 'mutter-x11-frames':
            wid, title, _, w, h, x, y = m.groups()
            yield {'id': int(wid, 16), 'title': title, 'w': int(w), 'h': int(h), 'x': int(x), 'y': int(y)}


def find(pattern):
    """Biggest client window whose title matches (hidden helper windows are tiny)."""
    hits = [w for w in windows() if re.search(pattern, w['title']) and w['w'] > 100 and w['h'] > 100]
    return max(hits, key=lambda w: w['w'] * w['h']) if hits else None


def geometry(wid):
    out = subprocess.run(['xwininfo', '-id', hex(wid)], capture_output=True, text=True).stdout
    g = {k: int(re.search(rf'{k}:\s+(-?\d+)', out).group(1))
         for k in ('Absolute upper-left X', 'Absolute upper-left Y', 'Width', 'Height')}
    return {'x': g['Absolute upper-left X'], 'y': g['Absolute upper-left Y'], 'w': g['Width'], 'h': g['Height']}


def work_area():
    out = subprocess.run(['xprop', '-root', '_NET_WORKAREA'], capture_output=True, text=True).stdout
    nums = [int(n) for n in re.findall(r'\d+', out.split('=')[-1])][:4]
    return nums if len(nums) == 4 else [0, 0, 1920, 1080]


class _ClientMessage(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int), ('serial', ctypes.c_ulong), ('send_event', ctypes.c_int),
                ('display', ctypes.c_void_p), ('window', ctypes.c_ulong),
                ('message_type', ctypes.c_ulong), ('format', ctypes.c_int),
                ('data', ctypes.c_long * 5), ('pad', ctypes.c_long * 16)]


def tile(wins_and_rects):
    """Un-maximise each window and move/resize it (libX11 through ctypes, no wmctrl/xdotool)."""
    x11 = ctypes.cdll.LoadLibrary(ctypes.util.find_library('X11'))
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XInternAtom.restype = ctypes.c_ulong
    x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    x11.XDefaultRootWindow.restype = ctypes.c_ulong
    x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x11.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.c_void_p]
    x11.XMoveResizeWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
                                      ctypes.c_uint, ctypes.c_uint]
    dpy = x11.XOpenDisplay(None)
    if not dpy:
        return
    root = x11.XDefaultRootWindow(dpy)
    state = x11.XInternAtom(dpy, b'_NET_WM_STATE', 0)
    max_h = x11.XInternAtom(dpy, b'_NET_WM_STATE_MAXIMIZED_HORZ', 0)
    max_v = x11.XInternAtom(dpy, b'_NET_WM_STATE_MAXIMIZED_VERT', 0)
    for win, (x, y, w, h) in wins_and_rects:
        ev = _ClientMessage(type=33, send_event=1, window=win['id'], message_type=state, format=32)
        ev.data[0], ev.data[1], ev.data[2], ev.data[3] = 0, max_h, max_v, 1   # 0 = remove
        x11.XSendEvent(dpy, root, 0, (1 << 19) | (1 << 20), ctypes.byref(ev))  # SubstructureRedirect|Notify
        x11.XMoveResizeWindow(dpy, win['id'], x, y, w, h)
    x11.XFlush(dpy)
    x11.XCloseDisplay(dpy)


def encoder():
    test = subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=s=256x256:d=0.2',
                           '-c:v', 'h264_nvenc', '-f', 'null', '-'], capture_output=True)
    if test.returncode == 0:
        return ['-c:v', 'h264_nvenc', '-preset', 'p4', '-cq', '23']
    return ['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23']


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out-dir', default=os.path.expanduser('~/demo_recordings'))
    ap.add_argument('--layout', choices=('side', 'screen'), default='side',
                    help='side: Gazebo | RViz stacked; screen: the whole screen')
    ap.add_argument('--gazebo-title', default=r'^Gazebo Sim\b', help='Gazebo window title (regex)')
    ap.add_argument('--rviz-title', default=r'demo_view\.rviz.* - RViz$', help='RViz window title (regex)')
    ap.add_argument('--no-tile', action='store_true', help='do not move/resize the windows')
    ap.add_argument('--width', type=int, default=1920, help='output width (side layout)')
    ap.add_argument('--height', type=int, default=1080, help='output height (side layout)')
    ap.add_argument('--fps', type=int, default=25)
    ap.add_argument('--wait', type=float, default=180.0, help='wait this long for the windows (s)')
    ap.add_argument('--settle', type=float, default=3.0, help='pause after tiling before recording (s)')
    args, _ = ap.parse_known_args()        # ignore --ros-args from ros2 launch

    stop = [False]
    signal.signal(signal.SIGINT, lambda *_: stop.__setitem__(0, True))
    signal.signal(signal.SIGTERM, lambda *_: stop.__setitem__(0, True))
    display = os.environ.get('DISPLAY', ':0')
    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, datetime.datetime.now().strftime('demo_%Y%m%d_%H%M%S.mp4'))
    log = lambda s: print(f'demo_recorder: {s}', flush=True)

    if args.layout == 'screen':
        x, y, w, h = 0, 0, args.width, args.height
        inputs = ['-f', 'x11grab', '-draw_mouse', '0', '-framerate', str(args.fps),
                  '-video_size', f'{w}x{h}', '-i', f'{display}+{x},{y}']
        filt = []
    else:
        t_end, gz, rv = time.monotonic() + args.wait, None, None
        while not stop[0] and time.monotonic() < t_end and not (gz and rv):
            gz, rv = find(args.gazebo_title), find(args.rviz_title)
            if not (gz and rv):
                time.sleep(1.0)
        if not (gz and rv):
            log(f'windows not found (gazebo: {bool(gz)}, rviz: {bool(rv)}); nothing recorded')
            return
        if not args.no_tile:
            ax, ay, aw, ah = work_area()
            # leave room for the window frames (title bar ~37 px, borders ~14 px under mutter)
            tile([(gz, (ax, ay, aw // 2, ah - 40)), (rv, (ax + aw // 2, ay, aw // 2, ah - 40))])
        time.sleep(args.settle)
        half = args.width // 2
        inputs, filt = [], []
        for i, win in enumerate((gz, rv)):
            g = geometry(win['id'])
            g['w'], g['h'] = g['w'] // 2 * 2, g['h'] // 2 * 2
            log(f'{win["title"]}: {g["w"]}x{g["h"]} at ({g["x"]},{g["y"]})')
            inputs += ['-f', 'x11grab', '-draw_mouse', '0', '-framerate', str(args.fps),
                       '-video_size', f'{g["w"]}x{g["h"]}', '-i', f'{display}+{g["x"]},{g["y"]}']
            filt.append(f'[{i}:v]scale={half}:{args.height}:force_original_aspect_ratio=decrease,'
                        f'pad={half}:{args.height}:(ow-iw)/2:(oh-ih)/2[v{i}]')
        filt = ['-filter_complex', ';'.join(filt) + ';[v0][v1]hstack=inputs=2[out]', '-map', '[out]']

    cmd = (['ffmpeg', '-loglevel', 'error', '-y'] + inputs + filt + encoder() +
           ['-pix_fmt', 'yuv420p', '-movflags', '+frag_keyframe+empty_moov', path])
    # own session: the terminal's Ctrl-C reaches us, and we stop ffmpeg with 'q' so it finishes the file
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE, start_new_session=True)
    log(f'recording to {path} (Ctrl-C to stop)')
    t0 = time.monotonic()
    while not stop[0] and ff.poll() is None:
        time.sleep(0.5)
    if ff.poll() is None:
        try:
            ff.communicate(b'q', timeout=10)
        except subprocess.TimeoutExpired:
            ff.kill()
    log(f'stopped after {time.monotonic() - t0:.0f} s: {path}')


if __name__ == '__main__':
    main()

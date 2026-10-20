"""X11 window access for the rover MCP server: find Gazebo / RViz windows, capture them, and send
mouse and keyboard input through XTEST (no xdotool needed).

Capture first reads the window's own pixels (works while it is covered, thanks to GNOME's
compositor); if that comes back blank (some GL windows), it raises the window and grabs the
screen region instead. Input always raises the window first, because XTEST input goes to
whatever is under the real pointer: it moves the user's mouse.
"""
import io
import time

import mss
from PIL import Image, ImageStat
from Xlib import X, XK, display
from Xlib.ext import xtest
from Xlib.protocol import event

import re

# exact title patterns: a plain substring also matched e.g. a VS Code window titled "Gazebo and RViz…"
ALIASES = {
    'gazebo': r'^Gazebo Sim\b',
    'gz': r'^Gazebo Sim\b',
    'rviz': r'(^| - )RViz$',
    'rviz2': r'(^| - )RViz$',
}

_d = None


def dpy():
    global _d
    if _d is None:
        _d = display.Display()
    return _d


def _atom(name):
    return dpy().intern_atom(name)


def _prop(win, name, kind=X.AnyPropertyType):
    try:
        p = win.get_full_property(_atom(name), kind)
        return None if p is None else p.value
    except Exception:
        return None


def _title(win):
    v = _prop(win, '_NET_WM_NAME', _atom('UTF8_STRING'))
    if v is None:
        try:
            v = win.get_wm_name()
        except Exception:
            v = None
    if isinstance(v, bytes):
        v = v.decode('utf-8', 'replace')
    return v or ''


def _geometry(win):
    g = win.get_geometry()
    t = win.translate_coords(dpy().screen().root, 0, 0)
    return -t.x, -t.y, g.width, g.height


def list_windows():
    root = dpy().screen().root
    ids = _prop(root, '_NET_CLIENT_LIST') or []
    out = []
    for wid in ids:
        w = dpy().create_resource_object('window', wid)
        try:
            x, y, wd, ht = _geometry(w)
            viewable = w.get_attributes().map_state == X.IsViewable
        except Exception:
            continue
        pid = _prop(w, '_NET_WM_PID')
        out.append({'id': wid, 'title': _title(w), 'x': x, 'y': y, 'w': wd, 'h': ht,
                    'viewable': viewable, 'pid': int(pid[0]) if pid is not None and len(pid) else None})
    return out


def find(target):
    """target: 'gazebo', 'rviz', 'desktop', a title substring, or a window id ('0x...' or int)."""
    if str(target).lower() in ('desktop', 'screen', 'root'):
        return None
    wins = list_windows()
    t = str(target)
    if t.lower().startswith('0x') or t.isdigit():
        wid = int(t, 0)
        hits = [w for w in wins if w['id'] == wid]
    elif t.lower() in ALIASES:
        hits = [w for w in wins if re.search(ALIASES[t.lower()], w['title'])]
    else:
        hits = [w for w in wins if t.lower() in w['title'].lower()]
    if not hits:
        raise LookupError(f'no window matching {target!r}; open windows: '
                          + '; '.join(repr(w['title']) for w in wins if w['title']))
    return max(hits, key=lambda w: w['w'] * w['h'])


def activate(info):
    """Ask the window manager to raise and focus the window (pager-style request, honoured by mutter)."""
    d = dpy()
    root = d.screen().root
    w = d.create_resource_object('window', info['id'])
    ev = event.ClientMessage(window=w, client_type=_atom('_NET_ACTIVE_WINDOW'),
                             data=(32, [2, X.CurrentTime, 0, 0, 0]))
    root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
    d.flush()
    time.sleep(0.35)
    info.update(dict(zip(('x', 'y', 'w', 'h'), _geometry(w))))


def _blank(img):
    st = ImageStat.Stat(img.convert('L').resize((64, 64)))
    return st.stddev[0] < 2.0


def _grab_region(x, y, w, h):
    with mss.mss() as s:
        shot = s.grab({'left': x, 'top': y, 'width': w, 'height': h})
        return Image.frombytes('RGB', shot.size, shot.bgra, 'raw', 'BGRX')


def capture(target, raise_window=False):
    """Returns (PIL image, window info or None for the desktop, method)."""
    info = find(target)
    if info is None:
        with mss.mss() as s:
            m = s.monitors[0]
        return _grab_region(m['left'], m['top'], m['width'], m['height']), None, 'screen'
    if not raise_window and info['viewable']:
        try:
            w = dpy().create_resource_object('window', info['id'])
            raw = w.get_image(0, 0, info['w'], info['h'], X.ZPixmap, 0xffffffff)
            img = Image.frombytes('RGB', (info['w'], info['h']), raw.data, 'raw', 'BGRX')
            if not _blank(img):
                return img, info, 'window'
        except Exception:
            pass
    activate(info)
    return _grab_region(info['x'], info['y'], info['w'], info['h']), info, 'screen-region'


def encode(img, max_width=1400, quality=80):
    """Scale down to max_width and JPEG-encode. Returns (bytes, scale)."""
    scale = 1.0
    if img.width > max_width:
        scale = max_width / img.width
        img = img.resize((max_width, round(img.height * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=quality)
    return buf.getvalue(), scale


# ---------------------------------------------------------------- input
def _move_abs(x, y):
    xtest.fake_input(dpy(), X.MotionNotify, x=int(x), y=int(y))
    dpy().sync()


def _button(b, down):
    xtest.fake_input(dpy(), X.ButtonPress if down else X.ButtonRelease, b)
    dpy().sync()


BUTTONS = {'left': 1, 'middle': 2, 'right': 3}


def click(info, x, y, button='left', count=1):
    activate(info)
    _move_abs(info['x'] + x, info['y'] + y)
    time.sleep(0.05)
    for _ in range(count):
        _button(BUTTONS[button], True)
        time.sleep(0.03)
        _button(BUTTONS[button], False)
        time.sleep(0.08)


def drag(info, x1, y1, x2, y2, button='left', steps=25, modifiers=()):
    activate(info)
    _move_abs(info['x'] + x1, info['y'] + y1)
    time.sleep(0.05)
    for m in modifiers:
        _key(m, True)
    _button(BUTTONS[button], True)
    for i in range(1, steps + 1):
        _move_abs(info['x'] + x1 + (x2 - x1) * i / steps, info['y'] + y1 + (y2 - y1) * i / steps)
        time.sleep(0.015)
    _button(BUTTONS[button], False)
    for m in reversed(modifiers):
        _key(m, False)


def scroll(info, x, y, clicks):
    """clicks > 0 scrolls up (zoom in in Gazebo/RViz), < 0 down."""
    activate(info)
    _move_abs(info['x'] + x, info['y'] + y)
    b = 4 if clicks > 0 else 5
    for _ in range(abs(int(clicks))):
        _button(b, True)
        _button(b, False)
        time.sleep(0.03)


KEYNAMES = {'ctrl': 'Control_L', 'control': 'Control_L', 'shift': 'Shift_L', 'alt': 'Alt_L',
            'super': 'Super_L', 'enter': 'Return', 'return': 'Return', 'esc': 'Escape',
            'escape': 'Escape', 'tab': 'Tab', 'space': 'space', 'backspace': 'BackSpace',
            'delete': 'Delete', 'up': 'Up', 'down': 'Down', 'left': 'Left', 'right': 'Right',
            'pageup': 'Prior', 'pagedown': 'Next', 'home': 'Home', 'end': 'End'}


def _keycode(name):
    sym = XK.string_to_keysym(KEYNAMES.get(name.lower(), name))
    if sym == 0 and len(name) == 1:
        sym = ord(name)
    code = dpy().keysym_to_keycode(sym)
    if not code:
        raise ValueError(f'unknown key {name!r}')
    return code


def _key(name, down):
    xtest.fake_input(dpy(), X.KeyPress if down else X.KeyRelease, _keycode(name))
    dpy().sync()


def key_combo(info, combo):
    """combo like 'ctrl+s', 'Escape', 'shift+Tab'."""
    activate(info)
    parts = combo.split('+')
    for p in parts:
        _key(p, True)
        time.sleep(0.02)
    for p in reversed(parts):
        _key(p, False)


def type_text(info, text):
    activate(info)
    for ch in text:
        name = {' ': 'space', '\n': 'Return', '\t': 'Tab'}.get(ch, ch)
        sym = XK.string_to_keysym(name) or ord(ch)
        code = dpy().keysym_to_keycode(sym)
        if not code:
            continue
        shift = dpy().keycode_to_keysym(code, 0) != sym
        if shift:
            _key('shift', True)
        xtest.fake_input(dpy(), X.KeyPress, code)
        xtest.fake_input(dpy(), X.KeyRelease, code)
        dpy().sync()
        if shift:
            _key('shift', False)
        time.sleep(0.01)

---
tags: [issue]
---
# GUI crashes in VS Code terminal

**Symptom.** The launch starts, but Gazebo's window and RViz never open. A few seconds later the
whole launch shuts down. The log shows:

```
gz sim gui: symbol lookup error: /snap/core20/current/lib/x86_64-linux-gnu/libpthread.so.0:
undefined symbol: __libc_pthread_init, version GLIBC_PRIVATE
```

The same command works from a normal terminal, so it looks as if the launch only works
sometimes.

**Cause.** VS Code is installed as a snap. Its integrated terminal inherits the snap's GTK and
locale variables (`GTK_PATH`, `GTK_EXE_PREFIX`, `LOCPATH`, `GIO_MODULE_DIR`, …), which point into
`/snap/code/…`. `gz sim gui` and `rviz2` then load the snap's old `libpthread` and die. The
Gazebo launch has `on_exit_shutdown: true` ([[Gazebo simulation]]), so when Gazebo dies,
everything else stops too.

**Fix.** Launch from a normal terminal (Ctrl+Alt+T). Or, in the VS Code terminal, first run:

```bash
unset GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE LOCPATH GIO_MODULE_DIR GSETTINGS_SCHEMA_DIR \
      GDK_PIXBUF_MODULE_FILE GDK_PIXBUF_MODULEDIR
export XDG_DATA_DIRS=$XDG_DATA_DIRS_VSCODE_SNAP_ORIG XDG_CONFIG_DIRS=$XDG_CONFIG_DIRS_VSCODE_SNAP_ORIG
```

**Verified 2026-10-15.** With the variables set, 1 of 1 GUI launches crashed as above. With them
unset, all 28 GUI launches that day opened Gazebo and RViz.

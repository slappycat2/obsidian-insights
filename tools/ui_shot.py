"""Photograph the Tk setup screen, and dump the geometry of every widget in it.

A development aid, not part of the package: ``tools/`` sits outside ``src/``,
so hatchling never sees it and the wheel is unaffected.

    uv run python tools/ui_shot.py                     # -> tools/_shots/
    uv run python tools/ui_shot.py out.png out.txt     # explicit paths

The screenshot is for judging how the screen looks; the widget dump is for
everything a screenshot is bad at -- exact widths, alignment, which cell a
widget really landed in. Both come from one run of the real ``SetupScreen``,
not a mock.

Two things here are load-bearing:

* **It cannot write your config.** ``V_CHK_DATA_DIR`` is redirected to a scratch
  directory holding a *copy* of CONFIG.yaml before ``vault_check`` is imported --
  ``v_chk_paths`` resolves DATA_ROOT once, at import time, so redirecting later
  would be too late. The screen is then dismissed with ``on_cancel()``, never
  ``on_save_and_run()``, and ``show()`` returning False is the proof that nothing
  was saved.

* **DPI scaling has to be undone.** The app is not DPI-aware, so Tk reports
  logical pixels while ImageGrab works in physical ones. On a 150% display the
  naive grab lands 1.5x away from the window and photographs whatever is behind
  it -- which is both wrong and none of our business. See ``dpi_scale()``.

The window appears on screen for about a second and takes focus. There is no
way around that: Tk has to map a window before it can be measured or captured.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Redirect DATA_ROOT before vault_check is imported -- see the module docstring.
_scratch = Path(tempfile.mkdtemp(prefix="v_chk_ui_shot_"))
_real_cfg = REPO_ROOT / "CONFIG.yaml"
if _real_cfg.exists():
    shutil.copy2(_real_cfg, _scratch / "CONFIG.yaml")
os.environ["V_CHK_DATA_DIR"] = str(_scratch)

from PIL import ImageGrab                                    # noqa: E402

from vault_check.v_chk_setup import SysConfig                # noqa: E402
from vault_check.v_chk_setupscreen import SetupScreen        # noqa: E402


def dpi_scale() -> float:
    """Physical pixels per Tk pixel, or 1.0 off Windows.

    HORZRES is the virtualised screen width a non-DPI-aware process is shown;
    DESKTOPHORZRES is the real one. Their ratio is the scaling factor, and it
    reads correctly *without* making this process DPI-aware -- which matters,
    because becoming aware would change how Tk renders the very screen we are
    trying to photograph.
    """
    if sys.platform != "win32":
        return 1.0

    import ctypes

    HORZRES, DESKTOPHORZRES = 8, 118
    dc = ctypes.windll.user32.GetDC(0)
    try:
        logical = ctypes.windll.gdi32.GetDeviceCaps(dc, HORZRES)
        physical = ctypes.windll.gdi32.GetDeviceCaps(dc, DESKTOPHORZRES)
    finally:
        ctypes.windll.user32.ReleaseDC(0, dc)
    return physical / logical if logical else 1.0


def describe(widget, depth: int = 0, lines: list | None = None) -> list:
    """One line per widget: class, geometry, and whatever it carries."""
    if lines is None:
        lines = []
    try:
        geo = (f"x={widget.winfo_x():<5} y={widget.winfo_y():<5} "
               f"w={widget.winfo_width():<5} h={widget.winfo_height():<5}")
        bits = []
        for opt in ("text", "font", "background", "foreground", "state", "values"):
            try:
                value = widget.cget(opt)
            except Exception:
                continue
            if value not in ("", None):
                bits.append(f"{opt}={value!r}")
        lines.append(f"{'  ' * depth}{widget.winfo_class():<12} {geo} {' '.join(bits)}")
    except Exception as exc:                        # a bad widget must not kill the dump
        lines.append(f"{'  ' * depth}<undumpable: {exc}>")
    for child in widget.winfo_children():
        describe(child, depth + 1, lines)
    return lines


def main() -> int:
    if len(sys.argv) > 1:
        png_path, txt_path = Path(sys.argv[1]), Path(sys.argv[2])
    else:
        out = REPO_ROOT / "tools" / "_shots"
        out.mkdir(parents=True, exist_ok=True)
        png_path, txt_path = out / "setup_screen.png", out / "setup_screen.txt"

    screen = SetupScreen(SysConfig())
    root = screen.root

    def capture() -> None:
        root.update()
        root.attributes("-topmost", True)            # nothing may overlap the grab
        root.lift()
        root.update()

        x, y = root.winfo_rootx(), root.winfo_rooty()
        w, h = root.winfo_width(), root.winfo_height()
        s = dpi_scale()
        bbox = (round(x * s), round(y * s), round((x + w) * s), round((y + h) * s))

        ImageGrab.grab(bbox=bbox).save(png_path)
        txt_path.write_text("\n".join(describe(root)), encoding="utf-8")

        print(f"window   : {root.winfo_geometry()}   dpi scale {s}")
        print(f"captured : {png_path}")
        print(f"tree     : {txt_path}")

        screen.on_cancel()                           # closes without saving

    root.after(900, capture)                         # fires once mainloop is running
    saved = screen.show()

    if saved:                                        # should be unreachable
        print("ERROR: the screen reported a save; CONFIG.yaml may have been written "
              f"into {_scratch}", file=sys.stderr)
        return 1
    print(f"show() returned False -- nothing was saved (scratch: {_scratch})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

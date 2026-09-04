"""Find and launch the spreadsheet application, on every platform.

Three things live here because they are the only platform-specific decisions
the app makes about the spreadsheet program, and they were previously spread
across SysConfig, the setup screen and the CLI:

* ``default_spreadsheet_app()`` -- what to suggest on a fresh install.
* ``validate_app()`` -- whether what the user typed can be launched.
* ``launch_command()`` / ``open_workbook()`` -- how to launch it.

**A blank application path means "use the system default handler"**: the
Windows shell association, ``open`` on macOS, ``xdg-open`` on Linux. That is
the safe default everywhere and it is what a fresh install falls back to when
nothing recognisable is found. On macOS an application is a ``.app`` bundle,
which is a *directory*, and it is launched with ``open -a``; on Linux the usual
name is a bare command on ``PATH`` rather than a path. All three forms validate.

Every function takes ``system`` so tests can drive the other platforms' branches
from any machine; it defaults to ``platform.system()``.
"""

import os
import platform
import shutil
import subprocess
from pathlib import Path

#: Probed in order on Windows; the first that exists is the default.
WINDOWS_CANDIDATES = (
    "C:/Program Files/Microsoft Office/root/Office16/EXCEL.EXE",
    "C:/Program Files (x86)/Microsoft Office/root/Office16/EXCEL.EXE",
    "C:/Program Files/LibreOffice/program/scalc.exe",
)

#: Probed in order on macOS. These are directories -- application bundles.
DARWIN_CANDIDATES = (
    "/Applications/Microsoft Excel.app",
    "/Applications/Numbers.app",
    "/Applications/LibreOffice.app",
)

#: Looked up on PATH in order on Linux (and any other Unix).
LINUX_CANDIDATES = ("libreoffice", "soffice", "localc")


def _system(system):
    return system or platform.system()


def is_app_bundle(app: str, system=None) -> bool:
    """True when ``app`` names a macOS application bundle directory."""
    if _system(system) != "Darwin" or not app:
        return False
    path = Path(app.strip())
    return path.name.endswith(".app") and path.is_dir()


def default_spreadsheet_app(system=None, which=shutil.which) -> str:
    """The spreadsheet program to suggest on this platform, or ``""``.

    Blank is a valid answer: it means the workbook is handed to whatever the
    desktop associates with ``.xlsx``.
    """
    system = _system(system)

    if system == "Windows":
        for candidate in WINDOWS_CANDIDATES:
            if Path(candidate).is_file():
                return candidate
        return ""

    if system == "Darwin":
        for candidate in DARWIN_CANDIDATES:
            if Path(candidate).is_dir():
                return candidate
        return ""

    for candidate in LINUX_CANDIDATES:
        if which(candidate):
            return candidate
    return ""


def validate_app(app, system=None, which=shutil.which) -> tuple[bool, str]:
    """Whether ``app`` can be launched. Returns ``(ok, message)``.

    Accepts: blank (system default), an existing file, a ``.app`` bundle on
    macOS, or a bare command that resolves on ``PATH``.
    """
    system = _system(system)

    if app is None or not str(app).strip():
        return True, ""

    app = str(app).strip()
    path = Path(app)

    if is_app_bundle(app, system):
        return True, ""

    if path.exists():
        if not path.is_file():
            if system == "Darwin":
                return False, "Executable path must be a file or a .app bundle"
            return False, "Executable path must be a file"
        # os.access(X_OK) is meaningful on POSIX and vacuous on Windows, where
        # any readable file passes -- so it is only asked where it can say no.
        if system != "Windows" and not os.access(path, os.X_OK):
            return False, "File is not executable"
        return True, ""

    # Not a path on disk. A bare name such as ``libreoffice`` is fine if the
    # shell could find it. Anything with a separator was meant as a path.
    if os.sep not in app and "/" not in app and which(app):
        return True, ""

    return False, "Executable file does not exist"


def launch_command(app: str, workbook: str, system=None) -> list[str] | None:
    """The argv that opens ``workbook`` with ``app``.

    ``None`` means "use os.startfile()", which is the Windows way to hand a
    file to its associated program and has no argv form.
    """
    system = _system(system)
    app = (app or "").strip()

    if not app:
        if system == "Windows":
            return None
        if system == "Darwin":
            return ["open", workbook]
        return ["xdg-open", workbook]

    if is_app_bundle(app, system):
        return ["open", "-a", app, workbook]

    return [app, workbook]


def open_workbook(app: str, workbook: str, system=None) -> int | None:
    """Launch the workbook. Returns the child's pid, or None for os.startfile().

    :raises OSError: the program could not be started (FileNotFoundError when
        ``app`` names nothing launchable). The workbook is already on disk by
        the time this is called, so callers should report rather than fail.
    """
    command = launch_command(app, workbook, system)
    if command is None:
        os.startfile(workbook)  # noqa: S606 -- Windows only; guarded above
        return None
    return subprocess.Popen(command).pid

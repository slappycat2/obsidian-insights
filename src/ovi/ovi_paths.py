"""Filesystem anchors for ovi.

Two distinct kinds of location, deliberately resolved differently:

* **Package assets** -- logos, icons and the logging configs. These ship with
  the code and are found relative to this module, so they work whether ovi is
  run from a source checkout or an installed wheel.

* **Writable data** -- CONFIG.yaml, generated workbooks, batch files and logs.
  These must never be written inside the package, since a pip-installed package
  may live in a read-only site-packages. See _resolve_data_root().

Nothing here depends on the current working directory. Do not reintroduce
Path.cwd(); ovi is launched from PyCharm, from a console script and from
pytest, none of which agree on what the working directory is.

Layout::

    <repo>/                      <- DATA_ROOT, for a source checkout
    |-- CONFIG.yaml              <- CONFIG_FILE
    |-- data/                    <- DATA_DIR
    |   |-- batch_files/         <- BATCH_DIR    (ovi_<vault>_NNNN.yaml handoff)
    |   +-- workbooks/           <- WORKBOOK_DIR (ovi_<vault>_NNNN.xlsx output)
    |-- logs/                    <- LOG_DIR
    +-- src/ovi/         <- PACKAGE_DIR
        |-- assets/              <- ASSETS_DIR
        +-- logging_configs/     <- LOGGING_CONFIG_DIR
"""

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Package assets (read-only, shipped with the code)
# --------------------------------------------------------------------------

PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "assets"
LOGGING_CONFIG_DIR = PACKAGE_DIR / "logging_configs"

# Capitalisation must match the filenames on disk exactly: macOS and Linux
# filesystems are case-sensitive, Windows is not, so a mismatch here is a bug
# that only shows up for other people.
LOGO_SPLASH = ASSETS_DIR / "SwenLogo200.png"
LOGO_SETUP = ASSETS_DIR / "SwenLogo300.png"      # declared but currently unused
ICON_WINDOW = ASSETS_DIR / "swenlogo.ico"
BANNER = ASSETS_DIR / "ovi_banner.png"
AREA51 = ASSETS_DIR / "area51.png"


# --------------------------------------------------------------------------
# Writable data
# --------------------------------------------------------------------------

#: Environment variable that overrides where generated data is written.
#: This is how the test suite redirects everything into a tmp_path.
DATA_DIR_ENV_VAR = "OVI_DATA_DIR"


def _resolve_data_root() -> Path:
    """Decide where CONFIG.yaml, workbooks and logs live.

    1. ``OVI_DATA_DIR`` when set -- how tests isolate themselves.
    2. The repository root, when running from a source checkout (detected by
       pyproject.toml sitting two levels above the package). Keeps the familiar
       behaviour of generated output landing next to the code.
    3. ``~/.ovi`` otherwise, for a genuinely installed copy where the package
       directory may not be writable.
    """
    override = os.environ.get(DATA_DIR_ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()

    checkout_root = PACKAGE_DIR.parent.parent
    if (checkout_root / "pyproject.toml").is_file():
        return checkout_root

    return Path.home() / ".ovi"


DATA_ROOT = _resolve_data_root()

CONFIG_FILE = DATA_ROOT / "CONFIG.yaml"
DATA_DIR = DATA_ROOT / "data"
BATCH_DIR = DATA_DIR / "batch_files"
WORKBOOK_DIR = DATA_DIR / "workbooks"
LOG_DIR = DATA_ROOT / "logs"

#: Directories created on demand rather than being required in the repository.
RUNTIME_DIRS = (DATA_DIR, BATCH_DIR, WORKBOOK_DIR, LOG_DIR)


def ensure_runtime_dirs() -> None:
    """Create the generated-output directories if they do not already exist."""
    for directory in RUNTIME_DIRS:
        directory.mkdir(parents=True, exist_ok=True)

"""Entry point for the Obsidian Vault Health Check.

    python main.py --help
    python main.py                      # analyse the vault last opened in Obsidian
    python main.py "D:/Vaults/MyVault"  # analyse a specific vault

The application modules live in vault_check/src/ and import each other by bare
module name, so that directory has to be importable. Adding it to sys.path here
keeps `python main.py` working from any working directory.

(Phase 2 of the cleanup replaces this shim with a real installable package and
a `v-chk` console command; at that point this file becomes a one-liner.)
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "vault_check" / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from v_chk import main  # noqa: E402  (import must follow the sys.path setup)

if __name__ == "__main__":
    main()

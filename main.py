"""Entry point for the Obsidian Vault Health Check.

    python main.py --help
    python main.py                      # analyse the vault last opened in Obsidian
    python main.py "D:/Vaults/MyVault"  # analyse a specific vault

Equivalent to the `v-chk` command that `uv sync` installs; this file exists so
the project can also be run straight from a source checkout without installing.
"""

from vault_check.v_chk import main

if __name__ == "__main__":
    main()

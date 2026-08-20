"""Obsidian Vault Health Check -- analyse an Obsidian vault into a spreadsheet."""

__version__ = "1.0.0"

# Number of slots in the sys_cfg['ctot'] counter list. Every module that builds
# a fresh ctot must agree on this, or the Summary tab indexes off the end.
CTOT_SLOTS = 14

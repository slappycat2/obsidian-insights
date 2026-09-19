# The subprocess contract

How a program drives `ovi`. The Obsidian plugin in `plugin/` is the first such program; anything
else that wants a workbook without a terminal or a window works the same way. The contract is
what `ovi --json` promises; the rest of the command line is for people.

## The command

```
ovi --json [-x] [-d LEVEL] [--skip-folders NAMES] [--max-value-links N] [--max-tag-links N]
           [--spreadsheet-app PATH] VAULT_PATH
```

| Part | Meaning |
|---|---|
| `--json` | One JSON object per line on stdout (below). Implies `--headless`: no window is ever opened. Cannot be combined with `--init`. |
| `VAULT_PATH` | The folder to scan. Required in practice: it is what lets a first run create its configuration (see *First run*). Any directory; one with no `.obsidian` folder is scanned with a warning in the log. |
| `-x` / `--do-not-open` | Write the workbook and stop. Without it, ovi launches the spreadsheet application itself and reports the outcome in the `done` event. |
| `-d LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Affects the log file and stderr, never stdout. |
| `--skip-folders NAMES` | Folder names to leave out of the scan, comma-separated -- the setup screen's *Directories to Ignore*. Matched as the setup screen matches them. |
| `--max-value-links N` | Most `FileNN` link columns on the Values tab; `0` is unlimited. |
| `--max-tag-links N` | The same for the Tags tab. |
| `--spreadsheet-app PATH` | Program to open the workbook with. An empty string means the system's default handler for `.xlsx`. A path that does not validate is a `ConfigIncomplete` error. |

The four setting flags apply **to this run only**. When the run creates the configuration (first
run), they are saved as part of it; on a machine that already has a `CONFIG.yaml` they are not
written back, so a program's settings never silently rewrite a setup the user completed on the
command line. A program that wants its settings honoured passes them every time.

## Environment

| Variable | Why |
|---|---|
| `OVI_DATA_DIR` | **Required.** Where `CONFIG.yaml`, `data/batch_files/`, `data/workbooks/` and `logs/` live. ovi resolves this once at import time, so it cannot be a flag. Without it ovi uses `~/.ovi`, or the checkout root when run from a source tree -- either may be shared with the user's own command-line runs, which is fine but should be a decision, not an accident. |
| `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1` | Keeps stderr and the log readable when a path or a note name is not ASCII. Stdout is ASCII regardless (see below). |

A program launched from a desktop icon on macOS or Linux does not inherit the shell's `PATH`.
When `--spreadsheet-app` is a bare command (`libreoffice`) or blank (which resolves to `xdg-open`
or `open`), the caller must make sure those are reachable from the `PATH` it passes.

## stdout: events

Every line on stdout is one JSON object with an `event` field. Nothing else is ever written
there. Lines are ASCII (non-ASCII characters are `\uXXXX`-escaped) and flushed as they are
produced, so progress arrives live through a pipe. A consumer must ignore events and fields it
does not know.

### `progress`

One per pipeline stage, in order. Five today.

```json
{"event": "progress", "percent": 20, "text": "Gathering Vault Statistics..."}
```

### `done`

Exactly one, last, on success. Exit code 0.

```json
{"event": "done", "ok": true,
 "workbook": "C:\\Users\\me\\.ovi\\data\\workbooks\\ovi_MyVault_0007.xlsx",
 "batch": "C:\\Users\\me\\.ovi\\data\\batch_files\\ovi_MyVault_0007.yaml",
 "vault": "D:\\Vaults\\MyVault",
 "vault_name": "MyVault - (D:\\Vaults)",
 "version": "1.4.0",
 "ctot": [565, 12, 3, 550, 0, 400, 120, 550, 9, 1830, 150, 41, 17, 4, 2],
 "opened": true}
```

| Field | Meaning |
|---|---|
| `workbook` | Absolute path of the `.xlsx` that was written. |
| `batch` | The YAML handoff file beside it, holding the complete harvested data (`wb_data`) and the packed configuration -- useful for anything that wants the numbers without opening the workbook. |
| `vault`, `vault_name` | The folder scanned and its display name. |
| `version` | The engine version that produced the workbook. |
| `ctot` | The Area51 tab's counters, indexed as in `CLAUDE.md`: `0` md files seen, `2` files skipped by folder, `3` files analysed, `13` empty notes, `14` bases, and so on. Length is `ovi.CTOT_SLOTS`. |
| `opened` | `true` if the spreadsheet application was launched, `false` if launching failed (the log says why; the workbook exists regardless), `null` when `-x` was given. |

### `error`

Exactly one, last, on failure. Exit code 1.

```json
{"event": "error", "ok": false, "kind": "WorkbookLocked",
 "message": "Unable to save workbook ...ovi_MyVault_0007.xlsx: it is open in another program. Close it and run again."}
```

| `kind` | When |
|---|---|
| `ConfigIncomplete` | No configuration and no `VAULT_PATH`; or an override -- `--spreadsheet-app` -- that does not validate; or the configuration could not be written. |
| `VaultNotFound` | `VAULT_PATH` is not an existing, readable directory. Click usually catches this first, as a usage error (below). |
| `WorkbookLocked` | The target `.xlsx` is open in another program. Windows only in practice; POSIX overwrites an open file without complaint. With filename sequencing on (the default) this is rare, since every run aims at a new number, and the number is not reused -- the next run writes the next one. With it off every run aims at the same file, so this is what a run gets whenever the previous workbook is still open; it is reported before the vault is scanned, and the old workbook is left as it was. |
| `Unexpected` | Anything else. The message is `ExceptionType: text`; the traceback is on stderr and in the log. |

## stderr and exit codes

stderr carries the human log at `WARNING` and above (whatever `-d` says, the stderr handler is
fixed at `WARNING`; `-d` governs the log file). It is for showing to a person when something went
wrong, not for parsing.

| Exit | Meaning |
|---|---|
| 0 | `done` was emitted. |
| 1 | `error` was emitted. |
| 2 | Usage error -- an unknown flag, a negative link limit, a `VAULT_PATH` that does not exist. Click reports it on stderr and **no JSON is written**. A consumer that sees exit 2 with an empty stdout should show stderr. |

## First run

ovi's configuration is normally created by the Tk setup screen. A `--json` run can never show it,
so when there is no `CONFIG.yaml` -- or one whose vault or spreadsheet application no longer
validates -- and a `VAULT_PATH` was given, ovi writes the configuration itself from the defaults,
the named vault and the setting flags, then carries on. A saved spreadsheet application that no
longer exists is replaced by the platform default (Excel, LibreOffice or Numbers where found,
otherwise blank) with a warning in the log. With no `VAULT_PATH` there is nothing to build a
configuration around, and the run ends with a `ConfigIncomplete` error whose message says so.

## Where things land

Under `$OVI_DATA_DIR`:

```
CONFIG.yaml
data/batch_files/ovi_<vault>_NNNN.yaml
data/workbooks/ovi_<vault>_NNNN.xlsx
logs/ovi.log                              rotating, 3 MB x 50
```

`<vault>` is the vault folder's name reduced to `[A-Za-z0-9._-]`, and `NNNN` counts per vault
from `0000`, one past the highest number present in either directory. The setup screen's **Use
filename Sequencing?** box turns the number off: the pair is then `ovi_<vault>.yaml` and
`ovi_<vault>.xlsx`, overwritten by every run. It is a saved setting with no flag of its own, which
is one more reason the `done` event names the exact files and a program should read those rather
than predict them.

## Versions and compatibility

`ovi --version` prints `Obsidian Insights, version X.Y.Z`. This contract exists from **1.4.0**;
a consumer should check for at least that before its first run and say so plainly if the engine is
older.

Adding an event or a field is not a breaking change, which is why consumers ignore what they do
not know. Removing or renaming one, changing an exit code, or changing what a flag means is a
MINOR version bump called out in `CHANGELOG.md`, as `docs/VERSIONING.md` provides for the command
line generally.

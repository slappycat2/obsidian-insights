# Obsidian Insights, the plugin

Builds an [Obsidian Insights](https://github.com/slappycat2/obsidian-insights) workbook of the
vault you have open, from a ribbon icon or the command palette, with a settings page inside
Obsidian. Windows, macOS and Linux; desktop only.

The plugin does not scan anything itself. It runs the Obsidian Insights engine, `ovi`, installed on
your computer, and shows its progress and result. One codebase, one workbook format, whether you
start it from Obsidian or from a terminal. What passes between the two is written down in
[docs/PLUGIN-CONTRACT.md](../docs/PLUGIN-CONTRACT.md).

Nothing is written into the vault except the plugin's own settings file, which every plugin has.
The workbook and the engine's files go to a data folder outside it (`~/.ovi` by default).

## Install

**1. The engine.** Needs [uv](https://docs.astral.sh/uv/); it installs Python for you.

```bash
uv tool install git+https://github.com/slappycat2/obsidian-insights
ovi --version
```

That puts `ovi` in `~/.local/bin` (`%USERPROFILE%\.local\bin\ovi.exe` on Windows), which is
where the plugin looks first. Upgrade later with `uv tool upgrade obsidian-insights`.

**2. The plugin.** Until it is in the community list, copy `main.js`, `manifest.json` and
`styles.css` from a release into `<vault>/.obsidian/plugins/obsidian-insights/`, then enable it
under *Settings → Community plugins*.

**3. Point the plugin at the engine.** Open the plugin's settings and press **Detect**; it fills in
the path. **Test** runs `ovi --version` and shows what it found. If you launched Obsidian from the
Dock or a desktop icon and Detect finds nothing, give the full path: `which ovi` in a terminal
prints it.

## Use

Click the table icon in the ribbon, or run **Obsidian Insights: Build workbook for this vault**
from the command palette. A notice shows the engine's progress; when it finishes the workbook
opens in your spreadsheet application, or is left where it is if you turn that off. Two more
commands: **Open last workbook** and **Open output folder**.

The first build on a computer where `ovi` has never been set up creates the engine's
configuration from the plugin's settings. No setup screen appears.

## Settings

| Setting | What it does |
|---|---|
| Engine executable | The `ovi` command. Blank searches the usual places; Detect fills it in. |
| Data folder | Where the engine keeps its configuration, workbooks, batch files and log. `~` is your home folder. Never inside the vault. |
| Folders to ignore | Folder names to leave out of the scan, comma-separated. Warns about names that are not top-level folders of this vault. |
| Values tab / Tags tab: most link columns | Caps the `FileNN` columns; 0 means as many as the vault needs. |
| Open the workbook after building | Off leaves it on disk; *Open last workbook* opens it later. |
| Spreadsheet application | Blank means whatever opens `.xlsx` on this computer. On macOS an application bundle, on Linux a command such as `libreoffice` also works. |
| Engine log level | How much goes into `logs/ovi.log` under the data folder. |
| Timeout | Stops a run that takes longer. |

Settings are per vault, as with every plugin, so two vaults can ignore different folders. They
are passed to the engine on every build and never written into the engine's own `CONFIG.yaml`
once that exists, so a setup you did on the command line is left alone.

## When it goes wrong

A failed build shows a notice and a dialog with the reason, the engine's last messages, the path
of its log and a Copy button. The usual ones:

- **The engine was not found.** Install it (above), then press Detect. If Obsidian was started from
  a desktop icon its `PATH` is short; the full path in the setting always works.
- **The workbook is open in another program** (Windows). Close it and build again. Numbers are not
  reused: the next build writes the next one.
- **The engine rejected the command line.** The installed engine predates the plugin.
  `uv tool upgrade obsidian-insights`.

## Developing

```bash
cd plugin
npm install
npm run dev                      # rebuild main.js on every change
npm run build                    # type-check, then one minified build
npm run install-local -- "<vault>"          # copy the three files into a vault
OBSIDIAN_PLUGIN_DIR="<vault>/.obsidian/plugins/obsidian-insights" npm run dev   # or build straight into it
```

With the *Hot Reload* community plugin installed in the vault, a rebuild is picked up without
restarting Obsidian. On Windows use the copy script rather than a symlink.

For the engine, `uv tool install --editable .` from the repository root installs your working
copy as `ovi`, or set the engine path to `.venv\Scripts\ovi.exe` inside the checkout. Setting the
data folder to the checkout shares output with command-line runs.

CI type-checks and builds the plugin on every push and checks that `manifest.json`,
`versions.json` and `package.json` agree on the version. The parts only a real Obsidian can
exercise are listed in [docs/PLATFORM-CHECKLIST.md](../docs/PLATFORM-CHECKLIST.md).

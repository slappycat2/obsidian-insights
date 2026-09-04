# Obsidian Insights

[![tests](https://github.com/slappycat2/obsidian-insights/actions/workflows/tests.yml/badge.svg)](https://github.com/slappycat2/obsidian-insights/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)

Turn an [Obsidian](https://obsidian.md) vault into a spreadsheet of everything that is in it:
every **property**, every **value**, every **tag**, plus duplicate notes, broken frontmatter, code
blocks, installed plugins and more, each row linked back to the note it came from.

**Read-only, and nothing leaves your machine.** Obsidian Insights reads your `.md` files, writes an
`.xlsx` workbook next to itself, and does nothing else. It never modifies the vault, installs
nothing into it, and makes no network connection of any kind.

![The Summary tab of a generated workbook](https://raw.githubusercontent.com/slappycat2/obsidian-insights/master/img/summ_screen.png)

## What you get

A workbook with one tab per subject, each a filterable table:

| Tab | What it lists |
|---|---|
| **Summary** | Vault statistics at a glance |
| **Properties** / **Values** | Every property, every value, how often each is used, and links to the notes that use it |
| **Tags** | Every tag, frontmatter and inline, with usage counts and links |
| **Files** | Every note, with whether each property was frontmatter or inline and whether it was upper-cased |
| **Xyml** | Notes whose frontmatter did not parse, with a likely reason |
| **Duplicates** | Notes that share a name in different folders |
| **Code** | Every code block, with the plugin it belongs to |
| **Plugins** / **QuickAdd** | Installed plugins, enabled or not, and QuickAdd's configuration |
| **Templates** / **Nests** | Templater templates and plugin-managed nested data |

Because it reads the files directly rather than through Obsidian, it finds what Obsidian's own
views hide: mistyped property names, tags that exist in one note only, properties ending in a
colon, emoji in names. Common issues are highlighted.

## Requirements

- **Python 3.13** and [uv](https://docs.astral.sh/uv/). `uv` installs Python for you if needed.
- **tkinter**, for the setup screen and progress splash. A uv-managed Python has it. If you use the
  system Python on Linux install `python3-tk` (Debian/Ubuntu) or `python3-tkinter` (Fedora); on
  Homebrew, `brew install python-tk@3.13`.
- **A spreadsheet application** to open the result, or none: leave the application blank in setup
  and the workbook opens with whatever your desktop associates with `.xlsx`. Tested targets are
  Excel (Windows and Mac), LibreOffice Calc (24.8 or newer for the Summary tab's dynamic-array
  formulas) and Numbers.
- **A desktop session for the first run.** Setup is a small window. After that, `--headless` works
  from a script or over SSH.

## Install and run

```bash
git clone https://github.com/slappycat2/obsidian-insights.git
cd obsidian-insights
uv sync
uv run ovi
```

On the first run a setup screen appears:

1. Pick a vault. The dropdown lists the vaults Obsidian knows about, or browse to any folder.
2. Confirm the spreadsheet application, or leave it blank for the system default.
3. Leave everything else as it is.

Click **Save & Run**. The vault is scanned, a new sequentially numbered workbook is written, and it
opens. From then on `uv run ovi` skips setup; `uv run ovi --setup` brings it back.

`python main.py [...]` works identically if you would rather not use the installed command.

### Usage

```bash
uv run ovi                          # the vault last opened in Obsidian
uv run ovi "D:/Vaults/MyVault"      # a specific vault, whether or not Obsidian knows it
uv run ovi --setup                  # change settings
uv run ovi --do-not-open            # build the workbook but do not launch the spreadsheet
uv run ovi --headless --do-not-open # no windows at all, for scripting
uv run ovi --init                   # delete generated config, batch files and workbooks
uv run ovi --help                   # all options
```

### Where things land

Running from a checkout, workbooks go to `data/workbooks/`, the handoff files to
`data/batch_files/`, logs to `logs/` and the configuration to `CONFIG.yaml`, all inside the
checkout. An installed copy uses `~/.ovi/` instead. Set `OVI_DATA_DIR` to put them anywhere else.

### Platform notes

- **Windows.** Excel is found automatically when it is installed in the usual place.
- **macOS.** Pick an application bundle (`Microsoft Excel.app`, `Numbers.app`) with Browse, or
  leave the field blank. Numbers does not support the `UNIQUE`/`FILTER` formulas the Summary tab
  uses, so those counts show as errors there; every other tab is fine.
- **Linux.** Obsidian's vault list is read from the .deb/AppImage, Flatpak and Snap locations.
  `libreoffice`, `soffice` or `localc` on `PATH` is found automatically. `obsidian://` links from
  the workbook need the Obsidian URL handler registered, which the Flatpak and .deb do.

## Development

```bash
uv sync              # install the project plus dev dependencies
uv run pytest        # run the test suite (~10s, no Obsidian install needed)
```

The tests build throwaway vaults in a temp directory, so they never touch a real vault. CI runs
them on Windows, macOS and Linux, then builds the wheel and checks its contents. A manual checklist
for the parts only a real desktop can exercise is in `docs/PLATFORM-CHECKLIST.md`.

Bugs and ideas go on the [issue tracker](https://github.com/slappycat2/obsidian-insights/issues).
`CHANGELOG.md` records what changed in each version.

<details>
<summary>Running from PyCharm</summary>

Point the project interpreter at the `.venv` that `uv sync` creates
(*Settings → Project → Python Interpreter*).

- **PyCharm never calls uv.** The Run button executes the venv's Python directly, so after changing
  `pyproject.toml` you must run `uv sync` yourself or you will get an `ImportError`.
- Set your run configuration's **Script** to `main.py` in the project root. The working directory
  does not matter: all paths resolve from the package location.

</details>

## About

I wrote this while learning Python and object-oriented design, coming from a functional
background, so if you read the code, please be kind. It works surprisingly well, and I hope it is
not just me.

If you are new to Obsidian, you may also like my one-page
[Obsidian Markdown Cheat Sheet](https://github.com/slappycat2/Obsidian-Markdown-Cheat-Sheet).

If it saves you an afternoon, consider buying me a coffee:

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/Z8Z71B3VAA)

## License

[MIT](LICENSE). "Corrupt" frontmatter, throughout, means whatever PyYAML 6.0.2 cannot `safe_load`.

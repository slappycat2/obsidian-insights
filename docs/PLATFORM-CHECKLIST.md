# Platform checklist

What CI cannot see. The suite runs on Windows, macOS and Linux and now exercises every platform
branch in the code, including a real `--headless` run with no Obsidian installed. But nobody has
opened the setup screen on a Mac, or clicked an `obsidian://` link from LibreOffice, and those are
the things this list is for. Run it once per platform before a release that claims support, and
again whenever the setup screen, the splash, the launcher or the link format changes.

Each item says what a pass looks like. Note the OS version, Python source (uv-managed or system)
and the spreadsheet application's version with the results.

## Both platforms

- [ ] `uv sync && uv run ovi --version` prints `Obsidian Insights, version X.Y.Z`.
- [ ] `uv run pytest` is green.
- [ ] **First run, Obsidian never opened here.** Rename or move Obsidian's config folder aside, then
      `uv run ovi`. Pass: the setup screen opens with an empty vault dropdown and a working Browse
      button; the log contains one warning naming the folders it looked in; no traceback.
- [ ] **Setup screen.** Opens centred, comes to the front once, and then *stops* floating above
      other windows. Has the window icon (the logo). Can be resized; nothing is clipped at the
      bottom, and the Save & Run / Cancel buttons are visible without resizing.
- [ ] **Browse for a vault** returns a folder; the vault registers and the dropdown gains it.
- [ ] **Blank application field** validates (green tick), Save & Run proceeds, and the workbook
      opens in whatever the desktop associates with `.xlsx`.
- [ ] **Splash** paints fully (logo, title, version, progress bar) and is not a blank rectangle.
- [ ] **Non-ASCII vault path** (a folder with an accent or emoji in its name) scans, writes a
      workbook whose name is ASCII-sanitised, and `CONFIG.yaml` reads back correctly on the next run.
- [ ] **`--headless --do-not-open`** after setup writes a workbook and exits 0 with no window.
- [ ] **Locked workbook.** With the previous workbook open in the spreadsheet app, run again.
      Pass on macOS/Linux: a new numbered workbook is written (the old one is never overwritten).
      Pass on Windows: the retry dialog appears, and Cancel exits 1 with a one-line message.
- [ ] **Links.** From the Properties tab, click a `FileNN` link. Pass: Obsidian opens that note.
      From the Duplicates tab, click a link; pass: the right one of the two same-named notes opens.
      Try a note whose name has a space and an accent.
- [ ] **Fonts.** Tab titles render in Impact where it is installed and in the fallback (Arial or
      Liberation Sans) where it is not; body text is readable and column widths are sensible.

## macOS

- [ ] **Browse for the application** starts in `/Applications`, offers `Microsoft Excel.app` and
      `Numbers.app` as single items, and picking one validates (green tick).
- [ ] The workbook opens in the chosen app via `open -a`.
- [ ] **Excel for Mac:** every tab renders; the Summary tab's unique counts show numbers, not
      `#NAME?`; `obsidian://` links open Obsidian.
- [ ] **Numbers:** the workbook opens (Numbers imports `.xlsx`). Expected degradation: the Summary
      tab's `UNIQUE`/`FILTER` cells show errors and `obsidian://` links do not open. Everything
      else readable.
- [ ] **Icon** shows in the Dock/window for the setup screen (PNG via `iconphoto`).
- [ ] The setup screen does not stay above other apps after it has appeared.

## Linux

- [ ] **Python source.** With the system Python and no `python3-tk`, `uv run ovi --headless
      --do-not-open <vault>` (after setup was done elsewhere or with a copied `CONFIG.yaml`)
      still runs; `uv run ovi` without a config exits 1 with a message naming `python3-tk`.
- [ ] **Obsidian install type.** Note which: .deb/AppImage (`~/.config/obsidian`), Flatpak
      (`~/.var/app/md.obsidian.Obsidian/config/obsidian`) or Snap
      (`~/snap/obsidian/current/.config/obsidian`). Pass: the setup dropdown lists the vaults.
- [ ] **LibreOffice Calc** is found automatically when `libreoffice` or `soffice` is on `PATH`
      (the default field shows the bare command). Version 24.8 or newer: Summary unique counts
      show numbers. Older: `#NAME?` there, everything else fine. Record the version.
- [ ] Blank application field opens the workbook via `xdg-open`.
- [ ] `obsidian://` links from Calc open Obsidian. If not, check
      `xdg-mime query default x-scheme-handler/obsidian`; the AppImage often does not register.
- [ ] **Wayland:** the splash may not be centred (the compositor ignores client positioning for
      override-redirect windows). It must still be fully visible.
- [ ] **HiDPI:** the setup screen is readable and nothing is clipped; resizing works.
- [ ] **Case sensitivity:** a vault containing `Note.md` and `note.md` in the same folder lists both
      on the Files tab and neither on Duplicates.

## Reporting

File anything that fails as an issue with the platform, the checklist line, and the log from
`logs/ovi.log` at `-d DEBUG`. A pass on both platforms closes the "Verify output in LibreOffice
Calc, Google Sheets and on macOS" item in `docs/BACKLOG.md`.

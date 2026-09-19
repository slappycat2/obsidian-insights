"""Command line entry point for Obsidian Insights.

Pipeline, in order:

    SysConfig          -- resolve configuration and choose a vault
    VaultScan          -- walk the vault, harvest properties/tags/code blocks
    NewWb              -- turn that data into per-tab cell definitions
    ExcelExporter      -- render the .xlsx and (optionally) open it

Each stage hands off to the next through a YAML batch file under
``data/batch_files/`` rather than in memory; see CLAUDE.md.
"""

import json
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

import click

from ovi import __version__
from ovi import ovi_launch as launch
from ovi import ovi_paths as paths
from ovi.ovi_build import VaultScan
from ovi.ovi_logger import DEFAULT_LOG_LEVEL, logger, make_logger
from ovi.ovi_setup import (ConfigIncompleteError, SetupCancelledError,
                                     SysConfig, VaultNotFoundError)
from ovi.ovi_wb_setup import WbDataDef
from ovi.ovi_wb_tabs import NewWb
from ovi.ovi_xl import ExcelExporter, WorkbookLockedError, wait_until_unlocked

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

#: (status text, percent complete) for each stage of run_pipeline().
PHASES = (
    ("Initializing Obsidian Insights...",       10),
    ("Gathering Vault Statistics...",           20),
    ("Building Workbook Tab Structure...",      50),
    ("Generating Workbook...",                  70),
    ("Done. Launching workbook application...", 100),
)


#: What run_pipeline() reports through: (status text, percent complete).
#: log_progress() and SplashScreen.update_status() both have this shape.
ProgressFn = Callable[[str, int], None]


def log_progress(text: str, percent: int) -> None:
    """Progress reporter for headless runs; mirrors SplashScreen.update_status."""
    logger.info("[%3d%%] %s", percent, text)


# ---------------------------------------------------------------------------
# --json: one event per line on stdout, for a program driving ovi
#
# The Obsidian plugin spawns ``ovi --json`` and reads these. Logging goes to
# stderr and the log file, never stdout, so stdout stays parseable. The
# contract -- events, fields, exit codes -- is documented in
# docs/PLUGIN-CONTRACT.md; consumers ignore fields and events they do not
# know, and a change to what is here is a MINOR bump called out in
# CHANGELOG.md.
# ---------------------------------------------------------------------------

def emit_event(**event) -> None:
    """Write one JSON event line to stdout and flush it.

    ASCII-only output (json.dumps's default) keeps the line intact whatever
    the console encoding is; the consumer's JSON parser restores the
    characters. The flush is what makes progress arrive live through a pipe.
    """
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def json_progress(text: str, percent: int) -> None:
    """Progress reporter for --json runs: one event line per stage."""
    emit_event(event="progress", percent=percent, text=text)


def error_kind(exc: BaseException) -> str:
    """The ``kind`` a --json consumer switches on: the class name minus ``Error``."""
    return type(exc).__name__.removesuffix("Error")


def report_failure(exc: Exception, json_mode: bool, kind: str | None = None) -> NoReturn:
    """Stop with the failure reported the way this run was asked to report.

    --json: one ``error`` event and exit 1. Otherwise Click's own one-line
    ``Error: ...`` on stderr, also exit 1, exactly as before --json existed.
    """
    if json_mode:
        emit_event(event="error", ok=False, kind=kind or error_kind(exc), message=str(exc))
        raise SystemExit(1)
    raise click.ClickException(str(exc)) from exc


def run_pipeline(sys_cfg_obj: SysConfig, progress: ProgressFn = log_progress,
                 interactive: bool = False, prompt_parent=None) -> ExcelExporter:
    """Run all four processing stages and return the exporter.

    Requires no GUI, which is what makes this callable from tests.

    :param sys_cfg_obj: a fully configured SysConfig.
    :param progress: callable(text, percent) -- SplashScreen.update_status or
        log_progress.
    :param interactive: True when a user is present to answer a Retry/Cancel
        prompt for a locked workbook; False raises WorkbookLockedError instead.
    :param prompt_parent: the window that prompt belongs to -- the splash, when
        there is one.
    """
    progress(*PHASES[0])

    # With filename sequencing off, this run replaces the workbook the last one
    # wrote and opened, so it is usually still open. Ask now, before the scan,
    # rather than after all the work. A numbered run aims at a name that does
    # not exist yet and has nothing to ask.
    if not sys_cfg_obj.sys_cfg.get('bool_file_seq', True):
        wait_until_unlocked(WbDataDef(sys_cfg_obj).sys_pn_wbs,
                            interactive=interactive, prompt_parent=prompt_parent)

    progress(*PHASES[1])
    scan_obj = VaultScan(sys_cfg_obj)

    progress(*PHASES[2])
    nwb_obj = NewWb(scan_obj)

    progress(*PHASES[3])
    exporter = ExcelExporter(nwb_obj.wbd_obj, interactive=interactive,
                             prompt_parent=prompt_parent)
    exporter.export()

    progress(*PHASES[4])
    return exporter


def run_with_splash(sys_cfg_obj: SysConfig) -> ExcelExporter:
    """Run the pipeline behind the Tk splash screen.

    The splash owns the Tk main loop, so the work happens inside an ``after()``
    callback. Any exception is captured and re-raised once the loop exits --
    otherwise a failure would leave the splash on screen forever.
    """
    # Imported here, not at module scope: this is the only path that needs
    # Tk, and a --headless run must work on a Python built without it.
    from ovi.ovi_splash import SplashScreen

    splash = SplashScreen(sys_cfg_obj.sys_pn_lg2, sys_cfg_obj.sys_splash_bg)
    outcome = {}

    def work():
        try:
            outcome["exporter"] = run_pipeline(sys_cfg_obj, progress=splash.update_status,
                                               interactive=True, prompt_parent=splash)
            time.sleep(1)  # let the user register the final status line
        except Exception as exc:  # noqa: BLE001 -- re-raised below
            outcome["error"] = exc
        finally:
            splash.destroy()

    splash.update_status("Starting Obsidian Insights...", 0)
    splash.after(500, work)
    splash.mainloop()

    if "error" in outcome:
        raise outcome["error"]

    return outcome["exporter"]


def open_workbook(exporter: ExcelExporter, quiet: bool = False) -> bool:
    """Launch the configured spreadsheet application on the new workbook.

    A blank application means the system default handler. Failure to launch
    is reported, not raised: the workbook is already on disk, and that is the
    result the user asked for.

    :param quiet: keep stdout clean -- a --json run reports the outcome in
        its ``done`` event instead, and the log has the detail.
    :return: whether the application was launched.
    """
    app = exporter.sys_pn_wb_exec or ""
    logger.info('Opening workbook "%s" in %s...',
                exporter.sys_pn_wbs, app or "the system default application")
    try:
        pid = launch.open_workbook(app, exporter.sys_pn_wbs)
    except OSError as exc:
        logger.error("Could not open the workbook with %r: %s", app, exc)
        if not quiet:
            click.echo(f"Could not open the workbook with {app or 'the system default'}: {exc}\n"
                       f"Open it yourself, or fix the application path with `ovi --setup`.")
        return False
    logger.info("Opened workbook. Process id: %s", pid)
    return True


def reset_generated_files(assume_yes: bool = False) -> None:
    """Delete CONFIG.yaml plus every generated batch file and workbook.

    Log files are deliberately left alone -- they are the only record of what
    happened on previous runs. Deleting CONFIG.yaml means the setup screen will
    appear on the next run.

    A workbook open in Excel cannot be deleted, and that is an allowed outcome
    rather than an error: it is reported, the exit code stays 0, and the file
    keeps its sequence number -- WbDataDef.get_next_bat() numbers past whatever
    survives, so the next run does not aim at a workbook that is still locked.
    """
    targets = [p for p in (paths.CONFIG_FILE,) if p.exists()]
    targets += sorted(paths.BATCH_DIR.glob("*.yaml"))
    # '~$name.xlsx' is Excel's owner file for an open workbook, not ovi output.
    # Listing one only to fail on it puts a second, confusing line in the report.
    targets += sorted(p for p in paths.WORKBOOK_DIR.glob("*.xlsx")
                      if not p.name.startswith("~$"))

    if not targets:
        click.echo("Nothing to reset -- no config, batch files or workbooks found.")
        return

    click.echo(f"This will permanently delete {len(targets)} file(s):")
    for target in targets[:10]:
        click.echo(f"  {target}")
    if len(targets) > 10:
        click.echo(f"  ... and {len(targets) - 10} more")

    if not assume_yes and not click.confirm("Proceed?", default=False):
        click.echo("Aborted -- nothing was deleted.")
        return

    deleted = 0
    kept = 0
    for target in targets:
        try:
            target.unlink()
            deleted += 1
        except OSError as exc:
            kept += 1
            click.echo(f"Could not delete {target}: {exc}")

    summary = f"Reset complete -- {deleted} file(s) deleted"
    if kept:
        summary += f", {kept} in use and kept"
    click.echo(f"{summary}.")

    if kept:
        click.echo("The file(s) left behind keep their sequence numbers; "
                   "the next run will number past them.")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="Obsidian Insights")
@click.option("-i", "--init", "do_init", is_flag=True,
              help="Delete CONFIG.yaml, batch files and workbooks, then exit.")
@click.option("-s", "--setup", "force_setup", is_flag=True,
              help="Show the setup screen before running.")
@click.option("-x", "--do-not-open", is_flag=True,
              help="Create the workbook but do not launch the spreadsheet app.")
@click.option("-q", "--no-splash", is_flag=True,
              help="Run without the graphical splash screen.")
@click.option("--headless", is_flag=True,
              help="Never open a window. Implies --no-splash. If setup is required, "
                   "a VAULT_PATH lets the configuration be created from the "
                   "defaults; without one the run fails rather than prompting.")
@click.option("-y", "--yes", "assume_yes", is_flag=True,
              help="Skip the confirmation prompt for --init.")
@click.option("-d", "--debug-level", default=DEFAULT_LOG_LEVEL, show_default=True,
              type=click.Choice(LOG_LEVELS, case_sensitive=False),
              help="Logging verbosity.")
@click.option("--skip-folders", "skip_folders", default=None, metavar="NAMES",
              help="Folder names to leave out of the scan, comma-separated -- the "
                   "setup screen's \"Directories to Ignore\". For this run only.")
@click.option("--max-value-links", "max_value_links", default=None, metavar="N",
              type=click.IntRange(min=0),
              help="Most link columns on the Values tab; 0 means unlimited. For this run only.")
@click.option("--max-tag-links", "max_tag_links", default=None, metavar="N",
              type=click.IntRange(min=0),
              help="Most link columns on the Tags tab; 0 means unlimited. For this run only.")
@click.option("--spreadsheet-app", "spreadsheet_app", default=None, metavar="PATH",
              help="Program to open the workbook with. An empty string means the "
                   "system default. For this run only.")
@click.option("--json", "json_mode", is_flag=True,
              help="Report progress and the result as one JSON object per line on "
                   "stdout, for a program driving ovi. Implies --headless.")
@click.argument("vault_path", required=False,
                type=click.Path(exists=True, file_okay=False, readable=True,
                                path_type=Path))
def cli(do_init, force_setup, do_not_open, no_splash, headless, assume_yes,
        debug_level, skip_folders, max_value_links, max_tag_links, spreadsheet_app,
        json_mode, vault_path):
    """Analyse an Obsidian vault and produce a spreadsheet of its properties,
    values and tags.

    VAULT_PATH is optional. When omitted, the vault last opened in Obsidian is
    used. It does not have to be a vault Obsidian knows about: any directory is
    accepted, and one that is missing a .obsidian folder is scanned anyway, with
    a warning in the log.

    On a machine that has never been set up, a --headless run with a VAULT_PATH
    creates the configuration from the defaults instead of asking for the setup
    screen.

    The vault is only ever read -- ovi never writes to it.
    """
    make_logger(debug_level)

    if json_mode:
        if do_init:
            raise click.UsageError("--json cannot be combined with --init.")
        headless = True

    if do_init:
        reset_generated_files(assume_yes=assume_yes)
        return

    # Absent flags leave the configuration alone; an empty --spreadsheet-app
    # is a value (the system default), so the test is for None.
    overrides = {key: value for key, value in (
        ("skip_rel_str", skip_folders),
        ("link_lim_vals", max_value_links),
        ("link_lim_tags", max_tag_links),
        ("sys_pn_wb_exec", spreadsheet_app),
    ) if value is not None}

    try:
        sys_cfg_obj = SysConfig(
            force_setup=force_setup,
            interactive=not headless,
            vault_path_override=str(vault_path) if vault_path else None,
            setting_overrides=overrides,
        )
    except SetupCancelledError:
        # Not an error: the user closed the dialog on purpose. Say so plainly
        # and stop, rather than reporting a failure or -- as before -- going on
        # to build a workbook they never asked for.
        click.echo("Setup cancelled. No workbook was created.")
        raise SystemExit(1)
    except (ConfigIncompleteError, VaultNotFoundError) as exc:
        report_failure(exc, json_mode)

    try:
        if no_splash or headless:
            exporter = run_pipeline(sys_cfg_obj,
                                    progress=json_progress if json_mode else log_progress,
                                    interactive=not headless)
        else:
            exporter = run_with_splash(sys_cfg_obj)
    except WorkbookLockedError as exc:
        report_failure(exc, json_mode)
    except Exception as exc:  # noqa: BLE001 -- re-raised unless a program is listening
        if not json_mode:
            raise
        # A program is reading stdout: it needs one parseable line rather than
        # a traceback. The traceback still goes to stderr and the log file.
        logger.exception("Unexpected failure while building the workbook")
        report_failure(exc, json_mode, kind="Unexpected")

    if json_mode:
        opened = None if do_not_open else open_workbook(exporter, quiet=True)
        emit_event(event="done", ok=True,
                   workbook=exporter.sys_pn_wbs, batch=exporter.sys_pn_batch,
                   vault=sys_cfg_obj.dir_vault, vault_name=sys_cfg_obj.vault_name,
                   version=__version__, ctot=list(exporter.sys_cfg["ctot"]),
                   opened=opened)
        return

    click.echo(f"Workbook written to {exporter.sys_pn_wbs}")

    if not do_not_open:
        open_workbook(exporter)


def main() -> None:
    """Console entry point."""
    cli()


if __name__ == "__main__":
    main()

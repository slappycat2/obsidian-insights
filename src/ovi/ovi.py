"""Command line entry point for Obsidian Insights.

Pipeline, in order:

    SysConfig          -- resolve configuration and choose a vault
    VaultScan          -- walk the vault, harvest properties/tags/code blocks
    NewWb              -- turn that data into per-tab cell definitions
    ExcelExporter      -- render the .xlsx and (optionally) open it

Each stage hands off to the next through a YAML batch file under
``data/batch_files/`` rather than in memory; see CLAUDE.md.
"""

import time
from pathlib import Path

import click

from ovi import __version__
from ovi import ovi_launch as launch
from ovi import ovi_paths as paths
from ovi.ovi_build import VaultScan
from ovi.ovi_logger import DEFAULT_LOG_LEVEL, logger, make_logger
from ovi.ovi_setup import (ConfigIncompleteError, SetupCancelledError,
                                     SysConfig, VaultNotFoundError)
from ovi.ovi_wb_tabs import NewWb
from ovi.ovi_xl import ExcelExporter, WorkbookLockedError

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

#: (status text, percent complete) for each stage of run_pipeline().
PHASES = (
    ("Initializing Obsidian Insights...",       10),
    ("Gathering Vault Statistics...",           20),
    ("Building Workbook Tab Structure...",      50),
    ("Generating Workbook...",                  70),
    ("Done. Launching workbook application...", 100),
)


def log_progress(text: str, percent: int) -> None:
    """Progress reporter for headless runs; mirrors SplashScreen.update_status."""
    logger.info("[%3d%%] %s", percent, text)


def run_pipeline(sys_cfg_obj: SysConfig, progress=log_progress,
                 interactive: bool = False) -> ExcelExporter:
    """Run all four processing stages and return the exporter.

    Requires no GUI, which is what makes this callable from tests.

    :param sys_cfg_obj: a fully configured SysConfig.
    :param progress: callable(text, percent) -- SplashScreen.update_status or
        log_progress.
    :param interactive: True when a user is present to answer a Retry/Cancel
        prompt for a locked workbook; False raises WorkbookLockedError instead.
    """
    progress(*PHASES[0])

    progress(*PHASES[1])
    scan_obj = VaultScan(sys_cfg_obj)

    progress(*PHASES[2])
    nwb_obj = NewWb(scan_obj)

    progress(*PHASES[3])
    exporter = ExcelExporter(nwb_obj.wbd_obj, interactive=interactive)
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
                                               interactive=True)
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


def open_workbook(exporter: ExcelExporter) -> None:
    """Launch the configured spreadsheet application on the new workbook.

    A blank application means the system default handler. Failure to launch
    is reported, not raised: the workbook is already on disk, and that is the
    result the user asked for.
    """
    app = exporter.sys_pn_wb_exec or ""
    logger.info('Opening workbook "%s" in %s...',
                exporter.sys_pn_wbs, app or "the system default application")
    try:
        pid = launch.open_workbook(app, exporter.sys_pn_wbs)
    except OSError as exc:
        logger.error("Could not open the workbook with %r: %s", app, exc)
        click.echo(f"Could not open the workbook with {app or 'the system default'}: {exc}\n"
                   f"Open it yourself, or fix the application path with `ovi --setup`.")
        return
    logger.info("Opened workbook. Process id: %s", pid)


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
              help="Never open a window. Implies --no-splash and fails, rather "
                   "than prompting, if setup is required.")
@click.option("-y", "--yes", "assume_yes", is_flag=True,
              help="Skip the confirmation prompt for --init.")
@click.option("-d", "--debug-level", default=DEFAULT_LOG_LEVEL, show_default=True,
              type=click.Choice(LOG_LEVELS, case_sensitive=False),
              help="Logging verbosity.")
@click.argument("vault_path", required=False,
                type=click.Path(exists=True, file_okay=False, readable=True,
                                path_type=Path))
def cli(do_init, force_setup, do_not_open, no_splash, headless, assume_yes,
        debug_level, vault_path):
    """Analyse an Obsidian vault and produce a spreadsheet of its properties,
    values and tags.

    VAULT_PATH is optional. When omitted, the vault last opened in Obsidian is
    used. It does not have to be a vault Obsidian knows about: any directory is
    accepted, and one that is missing a .obsidian folder is scanned anyway, with
    a warning in the log.

    The vault is only ever read -- ovi never writes to it.
    """
    make_logger(debug_level)

    if do_init:
        reset_generated_files(assume_yes=assume_yes)
        return

    try:
        sys_cfg_obj = SysConfig(
            force_setup=force_setup,
            interactive=not headless,
            vault_path_override=str(vault_path) if vault_path else None,
        )
    except SetupCancelledError:
        # Not an error: the user closed the dialog on purpose. Say so plainly
        # and stop, rather than reporting a failure or -- as before -- going on
        # to build a workbook they never asked for.
        click.echo("Setup cancelled. No workbook was created.")
        raise SystemExit(1)
    except (ConfigIncompleteError, VaultNotFoundError) as exc:
        raise click.ClickException(str(exc)) from exc

    try:
        if no_splash or headless:
            exporter = run_pipeline(sys_cfg_obj, interactive=not headless)
        else:
            exporter = run_with_splash(sys_cfg_obj)
    except WorkbookLockedError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Workbook written to {exporter.sys_pn_wbs}")

    if not do_not_open:
        open_workbook(exporter)


def main() -> None:
    """Console entry point."""
    cli()


if __name__ == "__main__":
    main()

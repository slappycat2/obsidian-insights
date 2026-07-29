"""Command line entry point for the Obsidian Vault Health Check.

Pipeline, in order:

    SysConfig          -- resolve configuration and choose a vault
    VaultHealthCheck   -- walk the vault, harvest properties/tags/code blocks
    NewWb              -- turn that data into per-tab cell definitions
    ExcelExporter      -- render the .xlsx and (optionally) open it

Each stage hands off to the next through a YAML batch file under
``data/batch_files/`` rather than in memory; see CLAUDE.md.
"""

import time
from pathlib import Path
from subprocess import Popen

import click

import v_chk_paths as paths
import v_chk_splash as v_splash
from v_chk_build import VaultHealthCheck
from v_chk_logger import DEFAULT_LOG_LEVEL, logger, make_logger
from v_chk_setup import ConfigIncompleteError, SysConfig, VaultNotFoundError
from v_chk_wb_tabs import NewWb
from v_chk_xl import ExcelExporter

__version__ = "0.2.9"

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

#: (status text, percent complete) for each stage of run_pipeline().
PHASES = (
    ("Initializing Vault Health Check...",      10),
    ("Gathering Vault Statistics...",           20),
    ("Building Workbook Tab Structure...",      50),
    ("Generating Workbook...",                  70),
    ("Done. Launching workbook application...", 100),
)


def log_progress(text: str, percent: int) -> None:
    """Progress reporter for headless runs; mirrors SplashScreen.update_status."""
    logger.info("[%3d%%] %s", percent, text)


def run_pipeline(sys_cfg_obj: SysConfig, progress=log_progress) -> ExcelExporter:
    """Run all four processing stages and return the exporter.

    Requires no GUI, which is what makes this callable from tests.

    :param sys_cfg_obj: a fully configured SysConfig.
    :param progress: callable(text, percent) -- SplashScreen.update_status or
        log_progress.
    """
    progress(*PHASES[0])

    progress(*PHASES[1])
    vhc_obj = VaultHealthCheck(sys_cfg_obj)

    progress(*PHASES[2])
    nwb_obj = NewWb(vhc_obj)

    progress(*PHASES[3])
    exporter = ExcelExporter(nwb_obj.wbd_obj)
    exporter.export()

    progress(*PHASES[4])
    return exporter


def run_with_splash(sys_cfg_obj: SysConfig) -> ExcelExporter:
    """Run the pipeline behind the Tk splash screen.

    The splash owns the Tk main loop, so the work happens inside an ``after()``
    callback. Any exception is captured and re-raised once the loop exits --
    otherwise a failure would leave the splash on screen forever.
    """
    splash = v_splash.SplashScreen(sys_cfg_obj.sys_pn_lg2, sys_cfg_obj.sys_splash_bg)
    outcome = {}

    def work():
        try:
            outcome["exporter"] = run_pipeline(sys_cfg_obj, progress=splash.update_status)
            time.sleep(1)  # let the user register the final status line
        except Exception as exc:  # noqa: BLE001 -- re-raised below
            outcome["error"] = exc
        finally:
            splash.destroy()

    splash.update_status("Starting Vault Health Check...", 0)
    splash.after(500, work)
    splash.mainloop()

    if "error" in outcome:
        raise outcome["error"]

    return outcome["exporter"]


def open_workbook(exporter: ExcelExporter) -> None:
    """Launch the configured spreadsheet application on the new workbook."""
    logger.info('Opening workbook "%s" in %s...',
                exporter.sys_pn_wbs, exporter.sys_pn_wb_exec)
    pid = Popen([exporter.sys_pn_wb_exec, exporter.sys_pn_wbs]).pid
    logger.info("Opened workbook. Process id: %s", pid)


def reset_generated_files(assume_yes: bool = False) -> None:
    """Delete CONFIG.yaml plus every generated batch file and workbook.

    Log files are deliberately left alone -- they are the only record of what
    happened on previous runs. Deleting CONFIG.yaml means the setup screen will
    appear on the next run.
    """
    targets = [p for p in (paths.CONFIG_FILE,) if p.exists()]
    targets += sorted(paths.BATCH_DIR.glob("*.yaml"))
    targets += sorted(paths.WORKBOOK_DIR.glob("*.xlsx"))

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
    for target in targets:
        try:
            target.unlink()
            deleted += 1
        except OSError as exc:
            click.echo(f"Could not delete {target}: {exc}")

    click.echo(f"Reset complete -- {deleted} file(s) deleted.")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="Obsidian Vault Check")
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
    used. It must be a vault Obsidian knows about, because the vault list is
    read from obsidian.json.

    The vault is only ever read -- v_chk never writes to it.
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
    except (ConfigIncompleteError, VaultNotFoundError) as exc:
        raise click.ClickException(str(exc)) from exc

    if no_splash or headless:
        exporter = run_pipeline(sys_cfg_obj)
    else:
        exporter = run_with_splash(sys_cfg_obj)

    click.echo(f"Workbook written to {exporter.sys_pn_wbs}")

    if not do_not_open:
        open_workbook(exporter)


def main() -> None:
    """Console entry point."""
    cli()


if __name__ == "__main__":
    main()

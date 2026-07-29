import time
from subprocess import Popen

import click

from v_chk_setup import SysConfig
from v_chk_build import VaultHealthCheck
from v_chk_wb_tabs import NewWb
from v_chk_xl import ExcelExporter
from v_chk_logger import logger
import v_chk_logger
import v_chk_splash as v_splash
from pathlib import Path

# Init globals w/a temp default
CLI_INIT = False                # True will delete all xlsx, batch and log files
CLI_SETUP = False               # True will force run Setup Screen
CLI_DO_NOT_OPEN = False             # True will Create the xlsx file but will not open it
CLI_NO_SPLASH = False               # True will suppress the splash progress screen
CLI_VAULT_PATH = ''                       # Must be a valid Vault ID; If not set, the last Open/Default vault is used.
CLI_DEBUG_LEVEL = 'INFO'
CLI_LOG_STR = ''

@click.command()
@click.version_option("0.2.9", prog_name="Obsidian Vault Check")
@click.option("-i", "--init", is_flag=True)
@click.option("-s", "--setup", is_flag=True)
@click.option("-x", "--do-not-open", is_flag=True)
@click.option("-q", "--no-splash", is_flag=True)
@click.option("-d", "--debug-level", default="INFO")
@click.argument(
    "vault_path",
    type=click.Path(
        exists=True,
        file_okay=False,
        readable=True,
        path_type=Path,
    ),
)

def cli(init, setup, do_not_open, no_splash, debug_level, vault_path):
    global CLI_INIT, CLI_SETUP, CLI_DO_NOT_OPEN, CLI_NO_SPLASH, CLI_DEBUG_LEVEL, CLI_VAULT_PATH
    log_str = (f"init={init}, setup={setup}, do_not_open={do_not_open}, no_splash={no_splash}"
               f", debug_level={debug_level}, vault_path={vault_path}")
    click.echo(f"log_str={log_str}")
    # Init globals w/a temp default
    CLI_INIT = init  # True will delete all xlsx, batch and log files
    CLI_SETUP = setup  # True will force run Setup Screen
    CLI_DO_NOT_OPEN = do_not_open  # True will Create the xlsx file but will not open it
    CLI_NO_SPLASH = no_splash  # True will suppress the splash progress screen
    CLI_DEBUG_LEVEL = debug_level
    CLI_VAULT_PATH = vault_path  # Must be a valid Vault ID; If not set, the last Open/Default vault is used.
    CLI_LOG_STR = ''



def init(self):
    global CLI_INIT
    if CLI_INIT:
        # Todo: Uncomment below and make it a CLI option (--init?)
        try:
            os.remove(self.sys_pn_cfg)
            logger.info(f"\n\n***REMOVED {self.sys_pn_cfg}***\n\n\n")
        except FileNotFoundError:
            pass
        except Exception as e:
            raise e

def main():
    global CLI_INIT_FLG
    v_chk_logger.make_logger()
    sys_cfg_obj = SysConfig()

    splash = v_splash.SplashScreen(sys_cfg_obj.sys_pn_lg2, sys_cfg_obj.sys_splash_bg)
    splash.update_status("Starting Vault Health Check...", 0)
    splash.after(500, lambda: run_main(splash, sys_cfg_obj))
    splash.mainloop()

def run_main(splash: v_splash.SplashScreen, sys_cfg_obj: SysConfig) -> None:
    # Initialize configuration
    phase_txt = [
        "Initializing Vault Health Check..."
        , "Gathering Vault Statistics..."
        , "Building Workbook Tab Structure..."
        , "Generating Workbook..."
        , "Done. Launching workbook application..."
    ]
    phase_pct = [10, 20, 50, 70, 100]
    splash.update_status(phase_txt[0], phase_pct[0])

    # VaultHealthCheck  -  Gathering Vault Statistics...
    splash.update_status(phase_txt[1], phase_pct[1])
    vhc_obj = VaultHealthCheck(sys_cfg_obj)

    # NewWb             - Building Workbook Tab Structure...
    splash.update_status(phase_txt[2], phase_pct[2])
    nwb_obj = NewWb(vhc_obj)

    # ExcelExporter     - Generating Workbook...
    splash.update_status(phase_txt[3], phase_pct[3])
    exp_obj = ExcelExporter(nwb_obj.wbd_obj)
    exp_obj.export()

    # Done. Launching workbook application...
    splash.update_status(phase_txt[4], phase_pct[4])
    time.sleep(1)

    splash.destroy()

    if OPEN_ON_CREATE:
        logger.info(f'Opening workbook "{exp_obj.sys_pn_wbs}" in {exp_obj.sys_pn_wb_exec}...')
        pid = Popen([exp_obj.sys_pn_wb_exec, exp_obj.sys_pn_wbs]).pid
        logger.info(f"Opened workbook. Process id: {pid}")

if __name__ == "__main__":
    cli()
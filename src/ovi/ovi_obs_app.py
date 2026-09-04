import os
import platform
from datetime import  datetime
from pathlib import Path
from dataclasses import dataclass, field

from ovi import CTOT_SLOTS
from ovi.ovi_json_file import JsonFile
from ovi.ovi_logger import logger


def candidate_config_dirs(system: str | None = None, home: Path | None = None,
                          env=None) -> list[Path]:
    """Where Obsidian keeps ``obsidian.json`` on this platform, most likely first.

    Linux has three common installs that each keep their own config: the .deb
    and AppImage under ``~/.config``, Flatpak under ``~/.var/app``, Snap under
    ``~/snap``. ``$XDG_CONFIG_HOME`` is honoured when set. Any system that is
    not Windows or macOS takes the Linux list.

    Pure function -- pass ``system``, ``home`` and ``env`` to drive another
    platform's branch from a test.
    """
    system = system or platform.system()
    home = Path(home) if home else Path.home()
    env = os.environ if env is None else env

    if system == "Windows":
        appdata = env.get("APPDATA")
        base = Path(appdata) if appdata else home / "AppData" / "Roaming"
        return [base / "obsidian"]

    if system == "Darwin":
        return [home / "Library" / "Application Support" / "obsidian"]

    dirs = []
    xdg = env.get("XDG_CONFIG_HOME")
    if xdg:
        dirs.append(Path(xdg) / "obsidian")
    dirs += [
        home / ".config" / "obsidian",
        home / ".var" / "app" / "md.obsidian.Obsidian" / "config" / "obsidian",
        home / "snap" / "obsidian" / "current" / ".config" / "obsidian",
    ]
    return dirs


def find_obsidian_json(system: str | None = None, home: Path | None = None,
                       env=None) -> Path | None:
    """The first ``obsidian.json`` that exists, or None when Obsidian has never run here."""
    for directory in candidate_config_dirs(system, home, env):
        candidate = directory / "obsidian.json"
        if candidate.is_file():
            return candidate
    return None


@dataclass
class ObsidianApp:
    """
    ObsidianApp class is a placeholder for the currently installed Obsidian
     application settings and related methods.
    sys_vlts contains a dictionary of all known vaults and their settings from
    previous runs. However, each time ovi is run, a check must be done to only use
     vaults that currently exist in obsidian.json.
    Currently, it does not contain any methods or attributes.
    possible platforms: Linux, Darwin, Windows
    """

    sys_vlts            : dict = field(default_factory=dict)
    cur_vlts            : dict = field(default_factory=dict)
    pn_obs_json         : str = ''
    dflt_vault_name     : str = ''
    obs_os              : str = platform.system()
    # sys_obs_vaults_open : list = field(default_factory=list)

    def load_current_obs_vaults(self):
        """Read the vaults Obsidian knows about into ``cur_vlts``.

        Never raises. A machine where Obsidian has not run (or keeps its config
        somewhere unexpected) simply yields no vaults and no default, and the
        caller falls through to CONFIG.yaml, a VAULT_PATH on the command line,
        or the setup screen's folder picker. Raising here used to kill the app
        before setup could open, even with an explicit vault path given.
        """
        self.cur_vlts = {}
        self.dflt_vault_name = ""

        json_path = find_obsidian_json(self.obs_os)
        if json_path is None:
            searched = ", ".join(str(d) for d in candidate_config_dirs(self.obs_os))
            logger.warning("obsidian.json not found (looked in: %s); no vaults are "
                           "known from Obsidian. Pick a folder in setup or pass a "
                           "vault path on the command line.", searched)
            self.pn_obs_json = ""
            return

        self.pn_obs_json = str(json_path)
        obs_json_obj = JsonFile(self.pn_obs_json)
        if obs_json_obj.err_msg:
            logger.warning("ObsidianApp: %s", obs_json_obj.err_msg)
            return

        vaults_dict = (obs_json_obj.json_data or {}).get('vaults') or {}
        if not vaults_dict:
            logger.warning("ObsidianApp: no vaults listed in %s", json_path)
            return

        any_valid_vault_name = ""
        for vault_id, vault_dict in vaults_dict.items():
            if 'path' not in vault_dict:
                continue
            v_dir = Path(vault_dict['path']).expanduser()

            if not v_dir.is_dir():
                # Unmounted drive, stale entry, another machine's path.
                logger.info("ObsidianApp: skipping vault %s -- folder not found: %s",
                            vault_id, v_dir)
                continue
            v_name = f'{v_dir.name} - ({v_dir.parent})'
            if v_name in self.sys_vlts:
                self.cur_vlts[v_name] = self.sys_vlts[v_name]
            else:
                v_rec_dict = self.vault_pack(vlt_name=v_name, src_v_dict={}, dst_v_dict={})
                v_rec_dict['vault_id']  = vault_id
                v_rec_dict['dir_vault'] = str(v_dir)
                self.cur_vlts[v_name] = v_rec_dict

            any_valid_vault_name = v_name

            # The last 'open' vault will be True, even if Obsidian is not currently open.
            if vault_dict.get('open'):
                self.dflt_vault_name = v_name

        if not self.dflt_vault_name:
            self.dflt_vault_name = any_valid_vault_name  # force a default, in case one isn't OPEN

        if not self.cur_vlts:
            logger.warning("ObsidianApp: none of the vaults in %s exist on this machine",
                           json_path)
            return

        self.sys_vlts.update(self.cur_vlts)

    @staticmethod
    def vault_pack(vlt_name: str, src_v_dict: dict, dst_v_dict: dict) -> dict:
        dst_v_dict['vault_name']         = src_v_dict.get('vault_name', vlt_name)
        dst_v_dict['vault_id']           = src_v_dict.get('vault_id', '')
        dst_v_dict['dir_vault']          = src_v_dict.get('dir_vault', '')
        dst_v_dict['sys_pn_batch']       = src_v_dict.get('sys_pn_batch', '')
        dst_v_dict['sys_pn_wbs']         = src_v_dict.get('sys_pn_wbs', '')
        dst_v_dict['dir_templates']      = src_v_dict.get('dir_templates', '')
        dst_v_dict['skip_rel_str']       = src_v_dict.get('skip_rel_str', '')
        dst_v_dict['skip_abs_lst']       = src_v_dict.get('skip_abs_lst', [])
        dst_v_dict['dirs_dot']           = src_v_dict.get('dirs_dot', [])
        dst_v_dict['ctot']               = src_v_dict.get('ctot', [0] * CTOT_SLOTS)
        dst_v_dict['bool_shw_notes']     = src_v_dict.get('bool_shw_notes', True)
        dst_v_dict['bool_rel_paths']     = src_v_dict.get('bool_rel_paths', True)
        dst_v_dict['bool_summ_rows']     = src_v_dict.get('bool_summ_rows', True)
        dst_v_dict['bool_unused_1']      = src_v_dict.get('bool_unused_1',  False)
        dst_v_dict['bool_unused_2']      = src_v_dict.get('bool_unused_2',  False)
        dst_v_dict['bool_unused_3']      = src_v_dict.get('bool_unused_3',  False)
        dst_v_dict['link_lim_vals']      = src_v_dict.get('link_lim_vals', 0)
        dst_v_dict['link_lim_tags']      = src_v_dict.get('link_lim_tags', 0)
        dst_v_dict['ovi_date']         = src_v_dict.get('ovi_date',
                                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        return dst_v_dict

def main() -> None:
    pass

if __name__ == '__main__':
    main()




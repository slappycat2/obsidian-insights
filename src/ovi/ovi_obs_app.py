import os
import platform
from datetime import  datetime
from pathlib import Path
from dataclasses import dataclass, field

from ovi import CTOT_SLOTS
from ovi.ovi_json_file import JsonFile
from ovi.ovi_logger import logger

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
        dir_obs_cfg = Path.home()
        dir_obs_cfg_str = str(dir_obs_cfg)
        self.cur_vlts = {}

        if self.obs_os == 'Windows':
            dir_obs_cfg_str = os.getenv('APPDATA', '')

        obs_json_locs = {
              'Linux':   f'{dir_obs_cfg_str}/.config/obsidian/'
            , 'Darwin':  f'{dir_obs_cfg_str}/Library/Application Support/obsidian/'
            , 'Windows': f'{dir_obs_cfg_str}/obsidian/'
        }

        # load obsidian json file
        dir_obs_json = obs_json_locs[self.obs_os]
        self.pn_obs_json = f"{dir_obs_json}obsidian.json"
        obs_json_obj = JsonFile(self.pn_obs_json)
        if obs_json_obj.err_msg:
            raise Exception(f"ObsidianApp: {obs_json_obj.err_msg}")

        obs_json_dict = obs_json_obj.json_data
        if 'vaults' not in obs_json_dict:
            raise Exception(f"ObsidianApp: No vaults found in obsidian.json at {dir_obs_json}")

        vaults_dict = obs_json_dict['vaults']

        self.dflt_vault_name = ""
        any_valid_vault_name = ""
        for vault_id, vault_dict in vaults_dict.items():
            if 'path' in vault_dict:
                v_dir = Path(vault_dict['path'])

                if not v_dir.is_dir():
                    continue                    # if the vault dir doesn't exist, skip it
                v_name = f'{v_dir.name} - ({v_dir.parent})'
                # v_record = [vault_id, str(v_dir)]
                if v_name not in self.sys_vlts:
                    v_rec_dict = self.vault_pack(vlt_name=v_name, src_v_dict={}, dst_v_dict={})
                    v_rec_dict['vault_id']  = vault_id
                    v_rec_dict['dir_vault'] = str(v_dir)
                    self.cur_vlts[v_name] = v_rec_dict
                else:
                    self.cur_vlts[v_name].deepcopy(self.sys_vlts[v_name])

                any_valid_vault_name = v_name

                # The last 'open' vault will be True, even if Obsidian is not currently open.
                if 'open' in vault_dict and vault_dict['open']:
                    self.dflt_vault_name = v_name
                    # self.sys_vlts_open.append(v_name)

        if not self.dflt_vault_name:
            self.dflt_vault_name = any_valid_vault_name  # force a default, in case one isn't OPEN

        if not self.cur_vlts:
            raise Exception(f"ObsidianApp: No Vaults with a 'path' key in obsidian.json")
        else:
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




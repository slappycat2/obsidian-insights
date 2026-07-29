import os
import yaml
import json
import platform
from pathlib import Path, PurePath
from datetime import datetime
from tkinter import messagebox
from dataclasses import dataclass, field

from v_chk_obs_app import ObsidianApp
from v_chk_setupscreen import SetupScreen
from v_chk_logger import logger

CLI_INIT_FLG = False


@dataclass
class SysConfig:
    sys_cfg:                 dict = field(default_factory=dict)
    sys_id:                  str  = 'v_chk'
    sys_ver:                 str  = '0.2.9'
    sys_dir_sys:             str  = field(default=None)
    sys_dir_dat:             str  = field(default=None)
    sys_dir_bat:             str  = field(default=None)
    sys_dir_wbs:             str  = field(default=None)
    sys_dir_log:             str  = field(default=None)
    sys_dir_img:             str  = field(default=None)
    sys_pn_cfg:              str  = field(default=None)
    sys_pn_lg2:              str  = field(default=None)
    sys_pn_lg3:              str  = field(default=None)
    sys_pn_ico:              str  = field(default=None)
    sys_pn_bnr:              str  = field(default=None)
    sys_pn_a51:              str  = field(default=None)
    sys_splash_bg:           str  = field(default=None)
    sys_pn_batch:            str  = field(default=None)
    sys_pn_wbs:              str  = field(default=None)
    sys_pn_wb_exec:          str  = field(default=None)
    sys_vlts:                dict = field(default_factory=dict)
    cur_vlts:                dict = field(default_factory=dict)
    sys_tab_seq:             list = field(default_factory=list)
    sys_cfg_os:              str  = field(default=None)
    vault_name:              str  = field(default=None)
    vault_id:                str  = field(default=None)
    dir_vault:               str  = field(default=None)
    dir_templates:           str  = field(default=None)
    skip_rel_str:            str  = field(default=None)
    skip_abs_lst:            list = field(default_factory=list)
    dirs_dot:                list = field(default_factory=list)
    ctot:                    list = field(default_factory=list)
    bool_shw_notes:          bool = field(default=True)
    bool_rel_paths:          bool = field(default=True)
    bool_summ_rows:          bool = field(default=True)
    bool_unused_1:           bool = field(default=False)
    bool_unused_2:           bool = field(default=False)
    bool_unused_3:           bool = field(default=False)
    link_lim_vals:           int  = field(default=0)
    link_lim_tags:           int  = field(default=0)
    v_chk_date:              str  = field(default=None)
    sys_init:                bool = field(default=False)

    def __post_init__(self):
        self.sys_cfg_os     = platform.system()
        self.v_chk_date     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.set_path_vars()
        # self.sys_dir_sys    = f"{Path.cwd()}"
        # self.sys_dir_dat    = f'{PurePath(self.sys_dir_sys + "/data")}'
        # self.sys_dir_bat    = f'{PurePath(self.sys_dir_sys + "/data/batch_files")}'
        # self.sys_dir_wbs    = f'{PurePath(self.sys_dir_sys + "/data/workbooks")}'
        # self.sys_dir_log    = f'{PurePath(self.sys_dir_sys + "/data/logs")}'
        # self.sys_dir_img    = f'{PurePath(self.sys_dir_sys + "/img")}'
#
        # self.sys_pn_cfg     = f'{PurePath(self.sys_dir_sys + "/CONFIG.yaml")}'
        # self.sys_pn_lg2     = f'{PurePath(self.sys_dir_img + "/swenlogo200.png")}'  # splash
        # self.sys_pn_lg3     = f'{PurePath(self.sys_dir_img + "/swenlogo300.png")}'  # setup
        # self.sys_pn_ico     = f'{PurePath(self.sys_dir_img + "/swenlogo.ico")}'     # window icon
        # self.sys_pn_bnr     = f'{PurePath(self.sys_dir_img + "/v_chkBanner2.png")}'
        # self.sys_pn_a51     = f'{PurePath(self.sys_dir_img + "/area51.png")}'

        self.sys_splash_bg  = f"#800000"                            # #800000 = Maroon

        self.o_app = ObsidianApp(sys_vlts=self.sys_vlts)

        self.o_app.load_current_obs_vaults()

        self.cur_vlts           = self.o_app.cur_vlts  # deepcopy?
        self.sys_vlts           = self.o_app.sys_vlts
        self.vault_name         = self.o_app.dflt_vault_name
        self.vault_id           = self.sys_vlts[self.vault_name]['vault_id']
        self.dir_vault          = self.sys_vlts[self.vault_name]['dir_vault']
        self.dir_templates      = self.sys_vlts[self.vault_name]['dir_templates']
        self.skip_rel_str       = self.sys_vlts[self.vault_name]['skip_rel_str']
        self.skip_abs_lst       = self.sys_vlts[self.vault_name]['skip_abs_lst']
        self.dirs_dot           = self.sys_vlts[self.vault_name]['dirs_dot']
        self.sys_tab_seq = ['pros', 'vals', 'tags', 'file',
                            'code', 'xyml', 'dups', 'tmpl',
                            'nest', 'plug', 'summ', 'ar51']

        self.sys_pn_wb_exec = self.get_dflt_wb_exec(self.sys_cfg_os)

        self.chk_cli_flgs()

        if os.path.exists(self.sys_pn_cfg):
            self.load_config(self.sys_pn_cfg)
            self.sys_init = True
            if not self.chk_fields_on_load():
                self.run_setup_ui()
        else:
            # Config.YAML doesn't exist, so create dirs, and show setup screen
            self.make_v_chk_dirs([self.sys_dir_dat
                                , self.sys_dir_bat
                                , self.sys_dir_wbs
                                , self.sys_dir_log
                                ])
            self.run_setup_ui()

    def run_setup_ui(self):
        SetupScreen(self).show()
        self.save_config()

    def set_path_vars(self):
        self.sys_dir_sys    = f"{Path.cwd()}"
        self.sys_dir_dat    = f'{PurePath(self.sys_dir_sys + "/data")}'
        self.sys_dir_bat    = f'{PurePath(self.sys_dir_sys + "/data/batch_files")}'
        self.sys_dir_wbs    = f'{PurePath(self.sys_dir_sys + "/data/workbooks")}'
        self.sys_dir_log    = f'{PurePath(self.sys_dir_sys + "/data/logs")}'
        self.sys_dir_img    = f'{PurePath(self.sys_dir_sys + "/img")}'

        self.sys_pn_cfg     = f'{PurePath(self.sys_dir_sys + "/CONFIG.yaml")}'
        self.sys_pn_lg2     = f'{PurePath(self.sys_dir_img + "/swenlogo200.png")}'  # splash
        self.sys_pn_lg3     = f'{PurePath(self.sys_dir_img + "/swenlogo300.png")}'  # setup
        self.sys_pn_ico     = f'{PurePath(self.sys_dir_img + "/swenlogo.ico")}'     # window icon
        self.sys_pn_bnr     = f'{PurePath(self.sys_dir_img + "/v_chkBanner2.png")}'
        self.sys_pn_a51     = f'{PurePath(self.sys_dir_img + "/area51.png")}'

    def make_v_chk_dirs(self, path_lst: str or list) -> None:
        """
            Checks if the given directory or list of directories exists, and creates them if they do not.
            :param path_lst: A single path as a string or a list of directory paths.
            :return: None
        """
        if isinstance(path_lst, list):
            for p in path_lst:
                self.make_v_chk_dirs(p)
            return
        if os.path.isdir(path_lst):
            return
        os.makedirs(path_lst)

    def get_dflt_wb_exec(self, cfg_os):
        # Todo - Needs testing on all platforms
        wb_exec = ""
        common_execs = {
              'Linux': ['scalc']
            , 'Darwin': ['open -a Numbers.app ']
            , 'Windows': ['C:/Program Files/Microsoft Office/root/Office16/EXCEL.EXE', 'C:/Program Files/LibreOffice/program/scalc.exe']
         }

        for wb_app in common_execs[cfg_os]:
            if cfg_os != 'Windows':
                wb_exec = wb_app
                break
            elif Path(wb_app).exists():
                wb_exec = wb_app
                break

        return wb_exec

    def chk_fields_on_load(self) -> bool:
        dir_vault_valid, _ = self.validate_dir_vault(self.dir_vault)
        wb_exec_valid, _ = self.validate_sys_pn_wb_exec(self.sys_pn_wb_exec)
        return dir_vault_valid and wb_exec_valid

    def get_templates_dir(self) -> str or None:
        template_cfg_file = f"{self.dir_vault}/.obsidian/plugins/templater-obsidian/data.json"
        try:
            if os.path.isfile(template_cfg_file):
                with open(template_cfg_file, 'r') as f:
                    template_cfg_json = f.read()
                template_cfg = json.loads(template_cfg_json)
                templates_path = Path(self.dir_vault).joinpath(template_cfg['templates_folder'])
                return f"{templates_path}"
        except (FileNotFoundError, KeyError):
            return None
        except Exception as e:
            raise Exception(f"ConfigSys: Error in get_templates_dir: {e}")
        else:
            return None

    def get_dot_dirs(self, op_sys: str, dir_start: str) -> list:
        """
        Returns a list of all "hidden" directories (those starting w/period, eg. '.obsidian')
        immediately under a given directory.
        :param op_sys:
        :param dir_start:
        :return dirs_dot:
        """
        dirs_dit = []
        dsep = '/'
        if op_sys == 'Windows':
            dsep = '\\'
        dirs_dot = [f.name for f in os.scandir(dir_start) if
                         f.is_dir() and f.path.startswith(f"{dir_start}{dsep}.")]
        return dirs_dot

    def get_skip_abs_lst(self, skip_rel_str: str, dir_start: str) -> list:
        """
        Returns a list of all directories to be skipped from the vault health check based
        on the comma separated list provided by the user during setup.
        :param skip_rel_str:
        :param dir_start:
        :return skip_abs_lst:
        """
        skip_abs_lst = []
        dirs = [d.strip() for d in skip_rel_str.split(',') if d.strip()]
        for dir_name in dirs:
            dname = Path(dir_start).joinpath(dir_name)
            skip_abs_lst += [str(dname)]

        return skip_abs_lst

    def read_config(self, pn_file: str) -> dict:
        cfg_data = {}
        try:
            with open(pn_file, 'r') as file:
                cfg_data = yaml.safe_load(file)
        except FileNotFoundError:
                pass
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read {pn_file}: {str(e)}")
            raise Exception(f"Failed to read {pn_file}: {str(e)}")

        return cfg_data

    def load_config(self, pn_file:str) -> None:
        self.sys_cfg = self.read_config(pn_file)
        self.cfg_unpack()

    def write_config(self, pn_file, cfg_data):
        try:
            with open(pn_file, 'w') as file:
                yaml.dump(cfg_data, file, default_flow_style=False)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save {pn_file}: {str(e)}")
            return False

    def save_config(self, sys_pn_cfg: str = sys_pn_cfg) -> bool:
        self.cfg_pack()
        ret = self.write_config(self.sys_pn_cfg, self.sys_cfg)
        return ret

    def cfg_pack(self):
        # path = Path(self.dir_templates.strip())
        # if not path.exists() or not path.is_dir() or self.dir_templates == '':
        self.dir_templates     = self.get_templates_dir()
        self.dirs_dot          = self.get_dot_dirs(self.sys_cfg_os, self.dir_vault)
        self.skip_abs_lst      = self.get_skip_abs_lst(self.skip_rel_str, self.dir_vault)

        self.sys_cfg = {
              'sys_id':             self.sys_id
            , 'sys_ver':            self.sys_ver
            , 'sys_dir_sys':        self.sys_dir_sys
            , 'sys_dir_dat':        self.sys_dir_dat
            , 'sys_dir_bat':        self.sys_dir_bat
            , 'sys_dir_wbs':        self.sys_dir_wbs
            , 'sys_dir_log':        self.sys_dir_log
            , 'sys_dir_img':        self.sys_dir_img
            , 'sys_pn_cfg':         self.sys_pn_cfg
            , 'sys_pn_wb_exec':     self.sys_pn_wb_exec
            , 'sys_pn_batch':       self.sys_pn_batch
            , 'sys_pn_wbs':         self.sys_pn_wbs
            , 'sys_tab_seq':        self.sys_tab_seq
            , 'sys_cfg_os':         self.sys_cfg_os
            , 'cur_vlts':           self.cur_vlts
            , 'sys_vlts':           self.sys_vlts
            , 'sys_pn_lg2':         self.sys_pn_lg2
            , 'sys_pn_lg3':         self.sys_pn_lg3
            , 'sys_pn_ico':         self.sys_pn_ico
            , 'sys_pn_bnr':         self.sys_pn_bnr
            , 'sys_pn_a51':         self.sys_pn_a51
            , 'sys_splash_bg':      self.sys_splash_bg

            , 'vault_name':         self.vault_name
            , 'vault_id':           self.vault_id
            , 'dir_vault':          self.dir_vault
            , 'dir_templates':      self.dir_templates
            , 'skip_rel_str':       self.skip_rel_str
            , 'skip_abs_lst':       self.skip_abs_lst
            , 'dirs_dot':           self.dirs_dot
            , 'ctot':               self.ctot
            , 'bool_shw_notes':     self.bool_shw_notes
            , 'bool_rel_paths':     self.bool_rel_paths
            , 'bool_summ_rows':     self.bool_summ_rows
            , 'bool_unused_1':      self.bool_unused_1
            , 'bool_unused_2':      self.bool_unused_2
            , 'bool_unused_3':      self.bool_unused_3
            , 'link_lim_vals':      self.link_lim_vals
            , 'link_lim_tags':      self.link_lim_tags
            , 'v_chk_date':         self.v_chk_date
        }

        # self.sys_cfg['sys_cfg'] = self.sys_cfg

    def cfg_unpack(self):
        self.sys_id             = self.sys_cfg.get('sys_id',            'v_chk')
        self.sys_ver            = self.sys_cfg.get('sys_ver',           '0.2.9')
        self.set_path_vars()
        # self.sys_dir_sys        = self.sys_cfg.get('sys_dir_sys',       f"{Path.cwd()}/")
        # self.sys_dir_dat        = self.sys_cfg.get('sys_dir_dat',       f"{self.sys_dir_sys}/data/")
        # self.sys_dir_bat        = self.sys_cfg.get('sys_dir_bat',       f"{self.sys_dir_sys}/data/batch_files/")
        # self.sys_dir_wbs        = self.sys_cfg.get('sys_dir_wbs',       f"{self.sys_dir_sys}/data/workbooks/")
        # self.sys_dir_log        = self.sys_cfg.get('sys_dir_log',       f"{self.sys_dir_sys}/data/logs/")
        # self.sys_dir_img        = self.sys_cfg.get('sys_dir_img',       f"{self.sys_dir_sys}/img")
        # self.sys_pn_cfg         = self.sys_cfg.get('sys_pn_cfg',        f"{self.sys_dir_sys}/CONFIG.yaml")
        # self.sys_pn_lg2         = self.sys_cfg.get('sys_pn_lg2',        f"{self.sys_dir_img}/swenlogo200.png" )
        # self.sys_pn_lg3         = self.sys_cfg.get('sys_pn_lg3',        f"{self.sys_dir_img}/swenlogo300.png" )
        # self.sys_pn_ico         = self.sys_cfg.get('sys_pn_ico',        f"{self.sys_dir_img}/swenlogo.ico"    )
        # self.sys_pn_bnr         = self.sys_cfg.get('sys_pn_bnr',        f"{self.sys_dir_img}/v_chkBanner2.png")
        # self.sys_pn_a51         = self.sys_cfg.get('sys_pn_a51',        f"{self.sys_dir_img}/area51.png"      )
        self.sys_splash_bg      = self.sys_cfg.get('sys_splash_bg',     f"#800000")
        self.sys_pn_wb_exec     = self.sys_cfg.get('sys_pn_wb_exec',    '')
        self.sys_pn_batch       = self.sys_cfg.get('sys_pn_batch',      '')
        self.sys_pn_wbs         = self.sys_cfg.get('sys_pn_wbs',        '')
        self.sys_tab_seq        = self.sys_cfg.get('sys_tab_seq',       ['pros', 'vals', 'tags', 'file',
                                                                        'code', 'xyml', 'dups', 'tmpl',
                                                                        'nest', 'plug', 'summ', 'ar51'])
        self.sys_cfg_os         = self.sys_cfg.get('sys_cfg_os',        platform.system())
        self.sys_vlts           = self.sys_cfg.get('sys_vlts',          {})
        self.cur_vlts           = self.sys_cfg.get('cur_vlts',          {})

        self.vault_name         = self.sys_cfg.get('vault_name',        '')
        self.vault_id           = self.sys_cfg.get('vault_id',          '')
        self.dir_vault          = self.sys_cfg.get('dir_vault',         '')
        self.dir_templates      = self.sys_cfg.get('dir_templates',     '')
        self.skip_rel_str       = self.sys_cfg.get('skip_rel_str',      '')
        self.skip_abs_lst       = self.sys_cfg.get('skip_abs_lst',      [])
        self.dirs_dot           = self.sys_cfg.get('dirs_dot',          [])
        self.ctot               = self.sys_cfg.get('ctot',              [0] * 13)
        self.bool_shw_notes     = self.sys_cfg.get('bool_shw_notes',    True)
        self.bool_rel_paths     = self.sys_cfg.get('bool_rel_paths',    True)
        self.bool_summ_rows     = self.sys_cfg.get('bool_summ_rows',    True)
        self.bool_unused_1      = self.sys_cfg.get('bool_unused_1',     False)
        self.bool_unused_2      = self.sys_cfg.get('bool_unused_2',     False)
        self.bool_unused_3      = self.sys_cfg.get('bool_unused_3',     False)
        self.link_lim_vals      = self.sys_cfg.get('link_lim_vals',     0)
        self.link_lim_tags      = self.sys_cfg.get('link_lim_tags',     0)
        self.v_chk_date         = self.sys_cfg.get('v_chk_date',        '')

    @staticmethod
    def validate_vault_id(vault_id):
        if not vault_id or not vault_id.strip():
            return False, "Vault ID cannot be empty"
        if len(vault_id.strip()) < 1:
            return False, "Vault ID must be at least 1 character"
        return True, ""

    @staticmethod
    def validate_dir_vault(dir_vault):
        if not dir_vault or not dir_vault.strip():
            return False, "Vault path cannot be empty"
        path = Path(dir_vault.strip())
        if not path.exists():
            return False, "Vault path does not exist"
        if not path.is_dir():
            return False, "Vault path must be a directory"
        return True, ""

    @staticmethod
    def validate_skip_rel_str(skip_rel_str, dir_vault):
        if not skip_rel_str or not skip_rel_str.strip():
            return True, ""
        if not dir_vault or not dir_vault.strip():
            return False, "Vault path must be set first"
        dir_vault_obj = Path(dir_vault.strip())
        if not dir_vault_obj.exists():
            return False, "Vault path must be valid first"
        dirs = [d.strip() for d in skip_rel_str.split(',') if d.strip()]
        if not dirs:
            return True, ""
        for dir_name in dirs:
            found = False
            for root, dirs_list, files in os.walk(dir_vault_obj):
                if dir_name in dirs_list:
                    found = True
                    break
            if not found:
                return False, f"X"
        return True, ""

    @staticmethod
    def validate_sys_pn_wb_exec(sys_pn_wb_exec):
        if not sys_pn_wb_exec or not sys_pn_wb_exec.strip():
            return False, "Executable path cannot be empty"
        path = Path(sys_pn_wb_exec.strip())
        if not path.exists():
            return False, "Executable file does not exist"
        if not path.is_file():
            return False, "Executable path must be a file"
        if not os.access(path, os.X_OK):
            return False, "File is not executable"
        return True, ""

def main() -> None:


    sys_cfg_obj = SysConfig()

    if sys_cfg_obj.sys_init:
        SetupScreen(sys_cfg_obj).show()

if __name__ == '__main__':
    main()

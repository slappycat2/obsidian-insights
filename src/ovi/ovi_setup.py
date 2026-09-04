import os
import yaml
import json
import platform
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

from ovi import __version__, CTOT_SLOTS
from ovi import ovi_paths as paths
from ovi import ovi_launch as launch
from ovi.ovi_obs_app import ObsidianApp
from ovi.ovi_logger import logger, make_logger

try:
    from ovi.ovi_setupscreen import SetupScreen
except ImportError as _tk_missing:      # no tkinter on this Python build
    # Debian/Ubuntu split it into python3-tk, Homebrew into python-tk@3.x.
    # A --headless run with a valid CONFIG.yaml never needs it, so the
    # import must not be fatal; run_setup_ui() says what to install.
    SetupScreen = None
    TK_IMPORT_ERROR = _tk_missing
else:
    TK_IMPORT_ERROR = None

#: Workbook tabs, in render order. Single source of truth -- this was
#: previously duplicated between __post_init__ and cfg_unpack.
DEFAULT_TAB_SEQ = ('pros', 'vals', 'tags', 'file',
                   'code', 'xyml', 'dups', 'tmpl',
                   'nest', 'plug', 'qadd', 'summ', 'ar51')


class ConfigIncompleteError(RuntimeError):
    """Raised when configuration is unusable and setup cannot be shown."""


class VaultNotFoundError(ValueError):
    """Raised when a requested vault path is not a usable directory.

    It no longer means "Obsidian does not know this folder" -- any directory can
    be scanned now, and register_vault_dir() builds the record for one Obsidian
    has never opened.
    """


class SetupCancelledError(RuntimeError):
    """Raised when the user dismisses the setup screen without saving.

    Not a failure -- the user said no. It exists so the caller cannot mistake a
    cancelled dialog for a completed one and go on to build a workbook, which
    is exactly what used to happen.
    """


@dataclass
class SysConfig:
    sys_cfg:                 dict = field(default_factory=dict)
    sys_id:                  str  = 'ovi'
    sys_ver:                 str  = __version__
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
    ovi_date:              str  = field(default=None)
    sys_init:                bool = field(default=False)

    # Runtime behaviour, not persisted to CONFIG.yaml.
    #: When False, never open a Tk window; raise ConfigIncompleteError instead.
    #: Required for --headless runs and for pytest.
    interactive:             bool = field(default=True)
    #: When True, always show the setup screen even if config is valid (--setup).
    force_setup:             bool = field(default=False)
    #: Vault path from the command line; overrides the vault in CONFIG.yaml.
    vault_path_override:     str  = field(default=None)

    def __post_init__(self):
        self.sys_cfg_os     = platform.system()
        self.ovi_date     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.set_path_vars()
        paths.ensure_runtime_dirs()

        self.sys_splash_bg  = "#800000"                             # #800000 = Maroon

        self.o_app = ObsidianApp(sys_vlts=self.sys_vlts)

        self.o_app.load_current_obs_vaults()

        self.cur_vlts           = self.o_app.cur_vlts  # deepcopy?
        self.sys_vlts           = self.o_app.sys_vlts
        # No obsidian.json, or none of its vaults on this machine, leaves no
        # default. That is not fatal: CONFIG.yaml, a VAULT_PATH argument or the
        # setup screen's folder picker can all still name one.
        if self.o_app.dflt_vault_name:
            self.apply_vault(self.o_app.dflt_vault_name)
        self.sys_tab_seq = list(DEFAULT_TAB_SEQ)

        self.sys_pn_wb_exec = self.get_dflt_wb_exec(self.sys_cfg_os)

        config_exists = os.path.exists(self.sys_pn_cfg)
        if config_exists:
            self.load_config(self.sys_pn_cfg)
            self.sys_init = True

        # An explicit vault on the command line beats whatever CONFIG.yaml says.
        if self.vault_path_override:
            self.select_vault_by_path(self.vault_path_override)

        if self.force_setup or not config_exists or not self.chk_fields_on_load():
            self.run_setup_ui()

    def apply_vault(self, vault_name: str) -> None:
        """Point this config at one of the vaults known from obsidian.json."""
        vault_rec = self.sys_vlts[vault_name]

        self.vault_name    = vault_name
        self.vault_id      = vault_rec['vault_id']
        self.dir_vault     = vault_rec['dir_vault']
        self.dir_templates = vault_rec['dir_templates']
        self.skip_rel_str  = vault_rec['skip_rel_str']
        self.skip_abs_lst  = vault_rec['skip_abs_lst']
        self.dirs_dot      = vault_rec['dirs_dot']

    def find_vault_by_path(self, vault_path) -> str | None:
        """Return the name of the vault stored at ``vault_path``, or None.

        Vault records are keyed by display name, but the same folder can be
        spelled several ways -- forward slashes from the folder picker, a
        different case, a relative path -- so the match is made on the resolved
        path rather than on the key.
        """
        target = Path(vault_path).expanduser().resolve()

        for vault_name, vault_rec in self.sys_vlts.items():
            known = vault_rec.get('dir_vault', '')
            if known and Path(known).expanduser().resolve() == target:
                return vault_name

        return None

    def register_vault_dir(self, vault_path) -> str:
        """Add a folder to the vault lists, whether or not Obsidian knows it.

        The vault list is read from obsidian.json, so a folder that has never
        been opened in Obsidian has no record to select -- which used to make it
        unscannable. This builds the missing record, and is what lets both the
        setup screen and the command line accept any directory.

        Idempotent: a folder already known under any name is returned unchanged
        rather than duplicated.

        :return: the display name the vault is registered under.
        :raises VaultNotFoundError: the path is not an existing directory.
        """
        valid, msg = self.validate_dir_vault(str(vault_path))
        if not valid:
            raise VaultNotFoundError(f"{vault_path}: {msg}")

        known_name = self.find_vault_by_path(vault_path)
        if known_name:
            return known_name

        v_dir = Path(vault_path).expanduser().resolve()
        # The same formula ObsidianApp uses, so a folder registered here is
        # indistinguishable in the dropdown from one Obsidian reported -- and
        # collision-free, since one folder can only ever produce one name.
        v_name = f'{v_dir.name} - ({v_dir.parent})'

        v_rec_dict = ObsidianApp.vault_pack(vlt_name=v_name, src_v_dict={}, dst_v_dict={})
        # Obsidian's URI scheme takes either the vault id or the vault name, so
        # the folder name is the one usable stand-in for an id we do not have.
        # An empty vault_id would leave every hyperlink in the workbook dead for
        # good; the folder name makes them inert only while Obsidian does not
        # know this folder, and they start working the moment it is opened there.
        v_rec_dict['vault_id']  = v_dir.name
        v_rec_dict['dir_vault'] = str(v_dir)

        # apply_vault() reads sys_vlts and the setup screen reads cur_vlts, so
        # the record has to be in both -- as one object, which is how
        # ObsidianApp leaves them too.
        self.sys_vlts[v_name] = v_rec_dict
        self.cur_vlts[v_name] = v_rec_dict

        has_obs_dir, _ = self.check_obsidian_dir(str(v_dir))
        if not has_obs_dir:
            logger.warning("%s has no .obsidian folder; scanning it anyway", v_dir)

        logger.info("Vault registered by folder: %s", v_name)
        return v_name

    def select_vault_by_path(self, vault_path) -> None:
        """Select a vault by filesystem path, as passed on the command line.

        A folder Obsidian has never opened is registered on the spot, so the
        path does not have to name a vault from obsidian.json.

        :raises VaultNotFoundError: if the path is not an existing directory.
        """
        vault_name = self.find_vault_by_path(vault_path) or self.register_vault_dir(vault_path)

        logger.info("Vault selected from command line: %s", vault_name)
        self.apply_vault(vault_name)
        # Every downstream stage reads the packed sys_cfg dict rather than these
        # attributes, so it has to be rebuilt or the run would silently analyse
        # whatever vault CONFIG.yaml names.
        self.cfg_pack()

    def run_setup_ui(self):
        """Show the Tk setup screen, and let the user decline.

        In non-interactive mode there is nobody to answer the dialog, so raise
        instead of hanging on a window that will never be dismissed.

        :raises ConfigIncompleteError: running non-interactively.
        :raises SetupCancelledError: the user cancelled or closed the window.
        """
        if not self.interactive:
            raise ConfigIncompleteError(
                f"Configuration at {self.sys_pn_cfg} is missing or invalid, and "
                f"ovi is running non-interactively. Run it once without "
                f"--headless to complete setup."
            )

        if SetupScreen is None:
            raise ConfigIncompleteError(
                f"Configuration at {self.sys_pn_cfg} is missing or invalid, and the "
                f"setup screen needs tkinter, which this Python does not have "
                f"({TK_IMPORT_ERROR}). Install it (Debian/Ubuntu: python3-tk; "
                f"Fedora: python3-tkinter; Homebrew: python-tk@3.13) or use a "
                f"uv-managed Python, then run again."
            )

        # The screen writes the config itself when the user saves, so there is
        # nothing to persist here -- and nothing *should* be persisted when they
        # cancel. This used to call save_config() unconditionally, so dismissing
        # the dialog still wrote a config and the run continued.
        if not SetupScreen(self).show():
            raise SetupCancelledError("Setup was cancelled; nothing was changed.")

    def set_path_vars(self):
        """Populate every path attribute from ovi_paths.

        These stay as ``str`` (not Path) because downstream code concatenates
        them with ``+``, e.g. WbDataDef.get_last_bat().
        """
        self.sys_dir_sys    = str(paths.DATA_ROOT)
        self.sys_dir_dat    = str(paths.DATA_DIR)
        self.sys_dir_bat    = str(paths.BATCH_DIR)
        self.sys_dir_wbs    = str(paths.WORKBOOK_DIR)
        self.sys_dir_log    = str(paths.LOG_DIR)
        self.sys_dir_img    = str(paths.ASSETS_DIR)

        self.sys_pn_cfg     = str(paths.CONFIG_FILE)
        self.sys_pn_lg2     = str(paths.LOGO_SPLASH)   # splash
        self.sys_pn_lg3     = str(paths.LOGO_SETUP)    # setup
        self.sys_pn_ico     = str(paths.ICON_WINDOW)   # window icon
        self.sys_pn_bnr     = str(paths.BANNER)
        self.sys_pn_a51     = str(paths.AREA51)

    @staticmethod
    def get_dflt_wb_exec(cfg_os):
        """The spreadsheet program to suggest on a fresh install; blank means
        the system default handler. See ovi_launch."""
        return launch.default_spreadsheet_app(cfg_os)

    def chk_fields_on_load(self) -> bool:
        dir_vault_valid, _ = self.validate_dir_vault(self.dir_vault)
        wb_exec_valid, _ = self.validate_sys_pn_wb_exec(self.sys_pn_wb_exec)
        return dir_vault_valid and wb_exec_valid

    def get_templates_dir(self):
        """Locate the Templater plugin's templates folder for this vault.

        :return: absolute path as a str, or None when the Templater plugin is
            not installed or has no templates_folder configured. Callers must
            handle None -- most vaults do not have Templater.
        """
        if not self.dir_vault:
            return None

        template_cfg_file = Path(self.dir_vault) / ".obsidian/plugins/templater-obsidian/data.json"

        if not template_cfg_file.is_file():
            return None

        try:
            template_cfg = json.loads(template_cfg_file.read_text(encoding="utf-8"))
            return str(Path(self.dir_vault) / template_cfg['templates_folder'])
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            logger.debug("No Templater templates folder for %s: %s", self.dir_vault, e)
            return None
        except Exception as e:
            raise Exception(f"ConfigSys: Error in get_templates_dir: {e}")

    @staticmethod
    def get_dot_dirs(op_sys: str, dir_start: str) -> list:
        """
        Returns a list of all "hidden" directories (those starting w/period, eg. '.obsidian')
        immediately under a given directory.
        :param op_sys: kept for the callers' sake; the name test needs no separator.
        :param dir_start:
        :return dirs_dot:
        """
        if not dir_start or not Path(dir_start).is_dir():
            return []
        return [entry.name for entry in os.scandir(dir_start)
                if entry.is_dir() and entry.name.startswith('.')]

    def get_skip_abs_lst(self, skip_rel_str: str, dir_start: str) -> list:
        """
        Returns a list of all directories to be skipped from the vault scan based
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
            with open(pn_file, 'r', encoding='utf-8') as file:
                cfg_data = yaml.safe_load(file)
        except FileNotFoundError:
                pass
        except Exception as e:
            logger.error("Failed to read %s: %s", pn_file, e)
            raise RuntimeError(f"Failed to read {pn_file}: {e}") from e

        return cfg_data or {}

    def load_config(self, pn_file:str) -> None:
        self.sys_cfg = self.read_config(pn_file)
        self.cfg_unpack()

    def write_config(self, pn_file, cfg_data):
        try:
            # UTF-8 and LF explicitly: the platform defaults are cp1252 and
            # CRLF on Windows, so a config carrying a non-ASCII vault path
            # would otherwise be unreadable on the next machine.
            with open(pn_file, 'w', encoding='utf-8', newline='\n') as file:
                yaml.dump(cfg_data, file, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            logger.error("Failed to save %s: %s", pn_file, e)
            return False

    def save_config(self) -> bool:
        self.cfg_pack()
        return self.write_config(self.sys_pn_cfg, self.sys_cfg)

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
            , 'ovi_date':         self.ovi_date
        }

        # self.sys_cfg['sys_cfg'] = self.sys_cfg

    def cfg_unpack(self):
        self.sys_id             = self.sys_cfg.get('sys_id',            'ovi')
        # CONFIG.yaml files written before the rename to Obsidian Insights
        # carry the old id; honour them so output filenames switch over
        # without an --init.
        if self.sys_id == 'v_chk':
            self.sys_id = 'ovi'
        # The version is always the running code's, never the one restored from
        # CONFIG.yaml -- otherwise the first config a machine writes pins the
        # reported version forever. A config written by 0.2.9 really was making
        # 0.3.0 report itself as 0.2.9. What lands back in CONFIG.yaml is
        # therefore "the version that last wrote this file".
        self.sys_ver            = __version__
        # Paths are always recomputed from ovi_paths rather than restored from
        # CONFIG.yaml, so a config file written on another machine (or before
        # the project moved) still resolves correctly.
        self.set_path_vars()
        self.sys_splash_bg      = self.sys_cfg.get('sys_splash_bg',     "#800000")
        self.sys_pn_wb_exec     = self.sys_cfg.get('sys_pn_wb_exec',    '')
        self.sys_pn_batch       = self.sys_cfg.get('sys_pn_batch',      '')
        self.sys_pn_wbs         = self.sys_cfg.get('sys_pn_wbs',        '')
        self.sys_tab_seq        = self.sys_cfg.get('sys_tab_seq',       list(DEFAULT_TAB_SEQ))
        # Like the paths above, the OS is a fact about this machine, not a
        # setting: a config carried over from Windows must not make a Mac
        # think it is Windows.
        self.sys_cfg_os         = platform.system()
        self.sys_vlts           = self.sys_cfg.get('sys_vlts',          {})
        self.cur_vlts           = self.sys_cfg.get('cur_vlts',          {})

        self.vault_name         = self.sys_cfg.get('vault_name',        '')
        self.vault_id           = self.sys_cfg.get('vault_id',          '')
        self.dir_vault          = self.sys_cfg.get('dir_vault',         '')
        self.dir_templates      = self.sys_cfg.get('dir_templates',     '')
        self.skip_rel_str       = self.sys_cfg.get('skip_rel_str',      '')
        self.skip_abs_lst       = self.sys_cfg.get('skip_abs_lst',      [])
        self.dirs_dot           = self.sys_cfg.get('dirs_dot',          [])
        self.ctot               = self.sys_cfg.get('ctot',              [0] * CTOT_SLOTS)
        self.bool_shw_notes     = self.sys_cfg.get('bool_shw_notes',    True)
        self.bool_rel_paths     = self.sys_cfg.get('bool_rel_paths',    True)
        self.bool_summ_rows     = self.sys_cfg.get('bool_summ_rows',    True)
        self.bool_unused_1      = self.sys_cfg.get('bool_unused_1',     False)
        self.bool_unused_2      = self.sys_cfg.get('bool_unused_2',     False)
        self.bool_unused_3      = self.sys_cfg.get('bool_unused_3',     False)
        self.link_lim_vals      = self.sys_cfg.get('link_lim_vals',     0)
        self.link_lim_tags      = self.sys_cfg.get('link_lim_tags',     0)
        self.ovi_date         = self.sys_cfg.get('ovi_date',        '')

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
    def check_obsidian_dir(dir_vault):
        """Report whether a folder holds a .obsidian directory. Never an error.

        A folder without one analyses perfectly well -- every vault the test
        suite builds lacks it -- so this must stay out of validate_dir_vault(),
        which gates whether the setup screen opens at all. What is actually lost
        is named in the message: get_templates_dir() finds no Templater config
        and PluginMan finds no manifests, so both of those tabs come out empty
        and are dropped, and obsidian:// links need Obsidian to know the folder.

        :return: (True, "") when .obsidian is there, else (False, warning text).
            A blank path returns (False, "") -- validate_dir_vault() is already
            saying it is unusable, and a second complaint would be noise.
        """
        if not dir_vault or not dir_vault.strip():
            return False, ""
        if (Path(dir_vault.strip()) / ".obsidian").is_dir():
            return True, ""
        return False, ("⚠ No .obsidian folder here — this may not be an Obsidian vault.\n"
                       "    It will still be scanned, but the Plugins and Templates tabs\n"
                       "    will be empty and the workbook's links may not open.")

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

        # One walk for all of them. This runs on every keystroke in the setup
        # screen, and it used to walk the whole vault once per name entered.
        present = set()
        for _, dirs_list, _ in os.walk(dir_vault_obj):
            present.update(dirs_list)

        missing = [d for d in dirs if d not in present]
        if missing:
            # Was "X", which told the user nothing about which name was wrong.
            return False, f"No folder named {', '.join(repr(d) for d in missing)}"
        return True, ""

    @staticmethod
    def validate_sys_pn_wb_exec(sys_pn_wb_exec):
        """Blank is valid and means the system default handler. See ovi_launch."""
        return launch.validate_app(sys_pn_wb_exec)

def main() -> None:
    """Open the setup screen on its own: ``python src/ovi_setup.py``.

    Constructing SysConfig with force_setup=True shows the screen and saves
    whatever is entered, regardless of whether CONFIG.yaml already validates.
    """
    make_logger()
    SysConfig(force_setup=True)


if __name__ == '__main__':
    main()

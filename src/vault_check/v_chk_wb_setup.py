import re

from pathlib import Path, PurePath
import yaml

from vault_check.v_chk_logger import logger

# Anything outside this set is replaced in the vault name before it goes into a
# filename. Two reasons: the name comes from a folder on someone else's disk and
# may legally hold characters this platform's filenames may not, and seq_nums()
# feeds the same stub to glob, where '[', '*' and '?' would be read as patterns.
_UNSAFE_IN_FILENAME = re.compile(r'[^A-Za-z0-9._-]+')


def safe_name_part(name: str) -> str:
    """Reduce a vault name to something that can sit inside a filename.

    Returns '' for a name that survives as nothing at all, which callers treat as
    "no vault segment" rather than writing a file with a bare separator in it.
    """
    return _UNSAFE_IN_FILENAME.sub('_', (name or '').strip()).strip('._-')


class WbDataDef:
    def __init__(self, sys_obj):
        self.sys_cfg = sys_obj.sys_cfg

        self.sys_pn_cfg     = self.sys_cfg['sys_pn_cfg']

        self.sys_id         = self.sys_cfg.get('sys_id','v_chk')
        self.file_stub      = self.build_file_stub()
        self.sys_dir_bat    = self.sys_cfg['sys_dir_bat']
        self.sys_dir_wbs    = self.sys_cfg['sys_dir_wbs']
        self.sys_dir_img    = self.sys_cfg['sys_dir_img']
        self.wb_tabs        = {}
        self.wb_data        = {}

        self.sys_pn_batch = None
        self.sys_pn_wbs = None
        self.sys_pn_batch = None
        self.sys_pn_wbs = None
        self.tab_def = None
        self.summ = None

        self.obs_props = {}
        self.obs_atags = {}
        self.obs_xyaml = {}
        self.obs_nests = {}
        self.obs_dupfn = {}
        self.obs_files = {}
        self.obs_tmplt = {}
        self.obs_datav = {}
        self.obs_plugs = {}
        self.pros = {}
        self.vals = {}
        self.tags = {}
        self.xyml = {}
        self.dups = {}
        self.file = {}
        self.tmpl = {}
        self.code = {}
        self.nest = {}
        self.plug = {}
        self.qadd = {}
        self.ar51 = {}
        self.plugin_id_def = {
                  'mapWithTag': 'Metadata Menu'
                , 'kindle-sync': 'Kindle Highlights'
                , 'NestedDictionary': 'Unknown Plugin'
        }
        self.xyml_descs = {
                     # 123456789 1 2345678 2 2345678 3 2345678 4 2345678 5 2345678 6 2345678 7 2345678 8
              'BadY': ["Invalid Properties"            , 'Cannot Load Frontmatter-Check YAML Markdown syntax.']
            , 'NoFm': ['No Properties'                 , 'Not a problem, if intentional.']
            , 'MtFm': ['YAML loaded, but empty' , 'Not a problem, if intentional.']
            , 'ErrY': ["YAML error"             , 'An Unknown Error occurred trying to process Frontmatter.']
            , 'NonD': ['YAML formatting error'  , 'Invalid Frontmatter--Not in dictionary format']
        }
        self.wb_def = {
              'sys_cfg': self.sys_cfg
            , 'wb_tabs': self.wb_tabs
            , 'wb_data': self.wb_data
        }

        self.get_last_bat()     # just so we have the name of the bat file

    def wb_def_pack(self):
        self.wb_def = {
              'sys_cfg': self.sys_cfg
            , 'wb_tabs': self.wb_tabs
            , 'wb_data': self.wb_data
        }

    def build_file_stub(self) -> str:
        """The leading part of every generated filename: '<sys_id>_<vault name>'.

        Naming the vault keeps one vault's batch files and workbooks distinguishable
        from another's, and makes the numbering per-vault rather than global.

        The vault's *folder* name is what goes in, not sys_cfg['vault_name'] -- that
        one is a display label built for the setup screen's dropdown, of the form
        'work - (D:/Vaults)', and sanitising it produces a filename nobody wants to
        read. Two vaults sharing a folder name therefore share a stub; they still get
        their own sequence numbers, so nothing is overwritten. A vault that sanitises
        away to nothing falls back to the bare sys_id.
        """
        dir_vault = self.sys_cfg.get('dir_vault') or ''
        vault_part = safe_name_part(Path(dir_vault).name if dir_vault else '')

        if not vault_part:
            vault_part = safe_name_part(self.sys_cfg.get('vault_name', ''))

        return f'{self.sys_id}_{vault_part}' if vault_part else self.sys_id

    def seq_nums(self, directory: str, ext: str) -> list[int]:
        r"""Every sequence number this vault's <ext> files in <directory> carry.

        The glob can be built from file_stub because safe_name_part() has already
        reduced it to [A-Za-z0-9._-], but the glob alone is not enough: a vault
        whose name sanitises away to nothing falls back to the bare sys_id (see
        build_file_stub), and that stub is a prefix of every other stub. The
        fullmatch is what keeps another vault's v_chk_work_0000.yaml from
        donating its 0000 to plain v_chk. \d{4,} rather than four digits so the
        count survives run 10000.
        """
        pattern = re.compile(rf'{re.escape(self.file_stub)}_(\d{{4,}})')
        matches = (pattern.fullmatch(p.stem)
                   for p in Path(directory).glob(f'{self.file_stub}_*{ext}'))

        return [int(m.group(1)) for m in matches if m]

    def get_last_bat(self):
        """Sets the name of the latest (most recent) batch file for this vault.

        "Latest" is the highest sequence number rather than the newest timestamp,
        so it agrees with get_next_bat() by construction -- a batch file restored
        from a backup no longer outranks a genuinely later one on ctime. With no
        batch files at all the name falls back to _0000, a path that need not
        exist; read_wb_data() is what reports it if it does not.
        """
        last_num = max(self.seq_nums(self.sys_dir_bat, '.yaml'), default=0)
        latest_file = f'{PurePath(f"{self.sys_dir_bat}/{self.file_stub}_{last_num:04d}.yaml")}'

        self.sys_pn_batch = latest_file
        self.sys_pn_wbs = f"{self.sys_dir_wbs}/{Path(latest_file).stem}.xlsx"
        self.sys_pn_wbs = f"{PurePath(self.sys_pn_wbs)}"
        logger.debug(f"ConfigData: Read Last Config file: {self.sys_pn_batch}")
        self.sys_cfg['sys_pn_batch'] = self.sys_pn_batch
        self.sys_cfg['sys_pn_wbs'] = self.sys_pn_wbs

        return

    def get_next_bat(self):
        """Returns the name of the next available yaml config file
        using the path filename stub_provided.

        One past the highest number still on disk in *either* generated
        directory. The workbooks are consulted because the two can fall out of
        step: --init deletes the batch file but cannot delete a workbook Excel
        is holding open, and numbering from the batch files alone would then
        hand the next run a number whose .xlsx already exists -- which
        save_workbook() answers with a modal retry dialog, even under
        --headless. Gaps are deliberately not refilled, for the same reason.
        """
        batch_num = max([-1] + self.seq_nums(self.sys_dir_bat, '.yaml')
                             + self.seq_nums(self.sys_dir_wbs, '.xlsx')) + 1
        c_file = f"{self.sys_dir_bat}/{self.file_stub}_{batch_num:04d}.yaml"
        logger.debug(f"ConfigData: Next Config file: {c_file}")

        self.sys_pn_batch = c_file
        self.sys_pn_wbs = f"{self.sys_dir_wbs}/{Path(c_file).stem}.xlsx"
        self.sys_cfg['sys_pn_batch'] = f'{PurePath(self.sys_pn_batch)}'
        self.sys_cfg['sys_pn_wbs'] = f'{PurePath(self.sys_pn_wbs)}'

        logger.debug(f"ConfigData: Init Next Config file: {self.sys_pn_batch}")

        # Init everything except cfg, as this is a new file...
        self.tab_def = {}
        self.pros = {'tab_def': self.tab_def}
        self.vals = {'tab_def': self.tab_def}
        self.tags = {'tab_def': self.tab_def}
        self.xyml = {'tab_def': self.tab_def}
        self.dups = {'tab_def': self.tab_def}
        self.file = {'tab_def': self.tab_def}
        self.tmpl = {'tab_def': self.tab_def}
        self.code = {'tab_def': self.tab_def}
        self.nest = {'tab_def': self.tab_def}
        self.plug = {'tab_def': self.tab_def}
        self.qadd = {'tab_def': self.tab_def}
        self.summ = {'tab_def': self.tab_def}
        self.ar51 = {'tab_def': self.tab_def}

        self.wb_tabs = {
              'pros': self.pros
            , 'vals': self.tags
            , 'tags': self.tags
            , 'xyml': self.xyml
            , 'dups': self.dups
            , 'file': self.file
            , 'tmpl': self.tmpl
            , 'code': self.code
            , 'nest': self.nest
            , 'plug': self.plug
            # 'summ' must stay last but one: DefSumm reads the other tabs'
            # finished tab_cd_fixed_summ, so every tab has to be built before it.
            , 'qadd': self.qadd
            , 'summ': self.summ
            , 'ar51': self.ar51
            , 'init': {}
        }
        self.obs_props = {}
        self.obs_atags = {}
        self.obs_files = {}
        self.wb_data = {
              'obs_props': self.obs_props
            , 'obs_atags': self.obs_atags
            , 'obs_files': self.obs_files
        }
        self.wb_def = {
              'sys_cfg': self.sys_cfg
            , 'wb_tabs': self.wb_tabs
            , 'wb_data': self.wb_data
        }

        return

    def write_bat_data(self) -> None:
        if not self.sys_pn_batch:
            self.get_next_bat()

        try:
            with open(self.sys_pn_batch, 'w') as yaml_file:
                yaml.dump({
                    'wb_def':     self.wb_def
                }
                    , stream=yaml_file, sort_keys=False
                )
            return

        except Exception as e:
            msg = f"WbDataDef:write_bat_data ({self.sys_pn_batch}): Error in Save Config: {e})"
            logger.critical(msg)
            raise SystemExit(msg)

    def read_wb_data(self):
        if self.sys_pn_batch == '' or self.sys_pn_batch is None:
            self.get_last_bat()
            logger.debug(f"ConfigData-read_config: Loaded last config file: {self.sys_pn_batch}")
        else:
            logger.debug(f"ConfigData-read_config: Reading Config file: {self.sys_pn_batch}")
            pass
        try:
            with open(self.sys_pn_batch, 'r') as file_y:
                bat_data = file_y.read()

            wb_def_temp = yaml.safe_load(bat_data)
            wb_def_temp = wb_def_temp.get('wb_def', {})

        except Exception as e:
            raise Exception(f"ConfigData: Error reading config file ({self.sys_pn_batch}) Error : {e}")

        return wb_def_temp

def main() -> None:
    pass

if __name__ == '__main__':
    main()


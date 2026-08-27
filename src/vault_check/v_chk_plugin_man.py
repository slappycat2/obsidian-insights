from pathlib import Path
import json

from vault_check.v_chk_json_file import JsonFile
from vault_check.v_chk_logger import logger

class PluginMan:
    def __init__(self, v_path=None):
        self.v_path = v_path
        self.id                 = ''
        self.name               = ''
        self.version            = ''
        self.minAppVersion      = ''
        self.description        = ''
        self.author             = ''
        self.authorUrl          = ''
        self.helpUrl            = ''
        self.plugin_dir         = ''
        self.plugs_lib = {}
        self.obs_plugs = {}
        self.known_plug_sigs = {
              'dataview': 'dataview'
            , 'dataviewjs': 'dataview'
            , 'button': 'buttons'
            , 'gevent': 'google-calendar'
            , 'ccard': 'folder-note-plugin'
            , 'leaflet': 'leaflet'
            , 'mermaid': 'mermaid-tools'
            , 'todoist': 'todoist-sync-plugin'
            , 'tracker': 'obsidian-tracker'
        }
        if self.v_path is not None:
            self.get_plugs_lib()
            self.get_obs_plugs()

    def __getitem__(self, key):
        return self.plugs_lib[key]
    def __setitem__(self, key, value):
        self.plugs_lib[key] = value
    def __delitem__(self, key):
        del self.plugs_lib[key]
    def __contains__(self, key):
        return key in self.plugs_lib
    def __len__(self):
        return len(self.plugs_lib)
    def __iter__(self):
        return iter(self.plugs_lib)
    def __str__(self):
        return str(self.plugs_lib)
    def __repr__(self):
        return repr(self.plugs_lib)
    def __call__(self):
        return self.plugs_lib

    def get_name(self, cb_sig):
        cb_sig = cb_sig.lower()
        cb_name = ''
        if cb_sig in self.known_plug_sigs:
            try:
                cb_sig = self.known_plug_sigs[cb_sig]
                cb_name  = self.plugs_lib[cb_sig]['name']
            except KeyError:
                pass
            except Exception as e:
                logger.error(f"PluginMan:get_name Unexpected Error: {e}")
                raise Exception(f"PluginMan: {e}")
        return cb_name

    def get_plugin_sig_list(self, plug_id):
        plugin_sig_list = []
        for sig, sig_plug_id in self.known_plug_sigs.items():
            if plug_id == sig_plug_id:
                plugin_sig_list.append(sig)
        return plugin_sig_list

    def get_obs_plugs(self):
        self.obs_plugs = {}
        for plugin_id, a_plugin_dict in self.plugs_lib.items():
            a_plugin_list = [''] * 10
            a_plugin_list[0] = plugin_id
            a_plugin_list[1] = a_plugin_dict.setdefault('name', '')
            a_plugin_list[2] = a_plugin_dict.setdefault('enabled', '')
            a_plugin_list[3] = a_plugin_dict.setdefault('version', '')
            a_plugin_list[4] = a_plugin_dict.setdefault('minAppVersion', '')
            a_plugin_list[5] = a_plugin_dict.setdefault('author', '')
            a_plugin_list[6] = a_plugin_dict.setdefault('authorUrl', '')
            a_plugin_list[7] = a_plugin_dict.setdefault('isDesktopOnly', '')
            a_plugin_list[8] = a_plugin_dict.setdefault('description', '')
            a_plugin_list[9] = a_plugin_dict.setdefault('plugin_sig_list', '')
            self.obs_plugs[plugin_id] = {plugin_id: a_plugin_list}

        return self.obs_plugs

    def get_plugs_lib(self):
        o_path = f"{self.v_path}/.obsidian/"
        v_path = f"{o_path}plugins/"
        v_path_obj = Path(v_path)
        cp_json = f"{o_path}community-plugins.json"
        enabled_plugins = []

        # A vault folder Obsidian has never opened has no .obsidian directory at
        # all, which is expected rather than broken -- it just means no plugins,
        # and the Plugins tab is dropped as empty. Reporting the missing
        # community-plugins.json as an ERROR made every such scan look like a
        # failure. A .obsidian that exists but cannot be read still does.
        if not Path(o_path).is_dir():
            logger.debug(f"PluginMan: no .obsidian folder under {self.v_path}; no plugins to read")
            return

        # First, load the the list of enabled plugins from community_plugins.json
        enabled_plugins_obj = JsonFile(cp_json)
        if enabled_plugins_obj.err_msg:
            logger.error(f"PluginMan: get_plugs_lib-Error: {enabled_plugins_obj.err_msg}")

        enabled_plugins = enabled_plugins_obj.json_data

        # Now, load the plugin descriptions from each manifest.json files
        #   These are the INSTALLED plugins.
        self.plugs_lib = {}
        plugin_dir = ''
        for mj_file in v_path_obj.rglob("manifest.json"):
            try:
                plugin_dir = mj_file.parent.name
                with open(mj_file, 'r', encoding='utf8') as f:
                    mj_data = json.load(f)
                    mj_data['plugin_dir'] = plugin_dir
                    mj_data['plugin_sig_list'] = self.get_plugin_sig_list(mj_data['id'])

                    if mj_data['id'] in enabled_plugins:
                        mj_data['enabled'] = True
                    else:
                        mj_data['enabled'] = False

                    logger.debug(f"Created obj: {mj_data['id']: <30} {mj_data['name']}")
                    self.plugs_lib[mj_data['id']] = mj_data

            except Exception as e:
                logger.critical(f"PluginMan:get_plugs_lib - plugin_dir: {plugin_dir}  mj_file: {mj_file}")
                raise Exception(f"PluginMan: get_plugs_lib-Error: {e}")

def main() -> None:
    pass

if __name__ == '__main__':
    main()




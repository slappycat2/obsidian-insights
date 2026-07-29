import re
import copy
from pathlib import Path
from typing import Any

import yaml

from vault_check.v_chk_wb_setup import WbDataDef
from vault_check.v_chk_plugin_man import PluginMan
from vault_check.v_chk_logger import logger

class VaultHealthCheck:   # WbConfig
    def __init__(self, sys_obj):
        self.wbd_obj = WbDataDef(sys_obj)
        self.dbug = False
        # self.dbug = 'FUN - Frequently Used Notes.md'

        self.key_stack = []
        # self.wbd_obj = WbxDataDef()

        self.wbd_obj.get_next_bat()     # this initials wb_data
        self.plugin_id_def = self.wbd_obj.plugin_id_def
        self.wb_def = self.wbd_obj.wb_def

        self.sys_cfg = self.wb_def.get('sys_cfg', {})

        # dir_templates is None whenever the Templater plugin is not installed
        # in this vault, so it cannot be handed straight to Path().
        templates_dir = self.sys_cfg.get('dir_templates') or None
        self.dir_templates = Path(templates_dir) if templates_dir else None

        self.isTemplate = False
        self.wb_data = self.wb_def.get('wb_data', {})
        self.obs_props = self.wb_data.get('obs_props', {})
        self.obs_atags = self.wb_data.get('obs_atags', {})
        self.obs_xyaml = self.wb_data.get('obs_xyaml', {})
        self.obs_dupfn = self.wb_data.get('obs_dupfn', {})
        self.obs_files = self.wb_data.get('obs_files', {})
        self.obs_tmplt = self.wb_data.get('obs_tmplt', {})
        self.obs_codes = self.wb_data.get('obs_codes', {})
        self.obs_nests = self.wb_data.get('obs_nests', {})
        self.obs_plugs = self.wb_data.get('obs_plugs', {})

        self.rgx_boundary = re.compile('^---\\s*$', re.MULTILINE)
        # re.MULTILINE is essential: the leading ^ is meant to anchor an inline
        # field to the start of a *line* ("rating:: 5"). Without the flag it
        # anchored to the start of the whole body, so the only inline fields
        # ever found were bracketed ones ("[rating:: 5]").
        self.rgx_body_pros = re.compile('(^|(\\[))([)([A-Za-z0-9_]+)[:]{2}(.*?)(\\]?\\]?)($|\\])',
                                        re.MULTILINE)
        self.rgx_tag_pattern = re.compile(r'[^|\w]#(\w+)', re.MULTILINE)
        self.rgx_noTZdatePattern = re.compile(r"([0-9]{4})[-\/]([0-1]?[0-9]{1})[-\/]([0-3])?([0-9]{1})(\s+)([0-9]{2}:[0-9]{2}:[0-9]{2})(.*)", re.MULTILINE)
        self.rgx_code_blocks = re.compile(r'^`{3}[\s\S]*?^`{3}', re.MULTILINE)
        self.rgx_code_inline = re.compile(r'`[^`]*`', re.MULTILINE)
        self.rgx_templater_strs = r"<%[\*]?\s*.*?\s*%>"
        self.rgx_wikilinks = re.compile(r"\[\[.*?\]\]", re.MULTILINE)

        self.filepath = ""
        self.prop_loc_F_I = "F"
        self.actual_prop_key = ""
        self.plugin_id = ""
        self.ctot = [0] * 13

        plugin_lib = PluginMan(self.sys_cfg['dir_vault'])
        self.obs_plugs = plugin_lib.get_obs_plugs()

        self.process_vault()

    def process_vault(self):
        logger.info(f"Starting Health Check on vault: {self.sys_cfg['vault_name']}...")

        v_path_obj = Path(self.sys_cfg['dir_vault'])
        for md_file in v_path_obj.rglob("*.md"):
            self.ctot[0] += 1

            # md_file and BASE_DIR are WindowsPath objects, not a strings!
            if self.dbug and str(md_file.name) != self.dbug:
                # we're debugging a single file and this isn't it!
                logger.warning(f"dbug is on: Skipping_file: {md_file} is not equal to {self.dbug}")
                continue

            self.isTemplate = False
            if self.dir_templates and self.is_subdirectory(md_file, self.dir_templates):
                self.isTemplate = True
                self.ctot[1] += 1
                # right now, support for templates is not implemented.
                # this will require a special decoding of the markdown
                # without using PyYaml, since they would not load properly
                # otherwise it will like all be invalid properties...
                continue

            x_dir_test = False
            for x_dir in md_file.parts:
                if x_dir in self.sys_cfg['skip_rel_str']:
                    x_dir_test = True
                    continue  # this only exits this for loop
            if x_dir_test:
                self.ctot[2] += 1
                # logger.debug(f"Skipping file: {md_file} is in skip_rel_str")
                continue # this gets the next file...

            logger.info(f"Running health check on: {md_file}")

            md_pname = str(md_file)
            self.process_md_file(md_pname)

        # Vault Processing Complete! Write to wb_def

        self.wb_def['wb_data']['obs_props'] = self.obs_props
        self.wb_def['wb_data']['obs_xyaml'] = self.obs_xyaml
        self.wb_def['wb_data']['obs_dupfn'] = self.obs_dupfn
        self.wb_def['wb_data']['obs_files'] = self.obs_files
        self.wb_def['wb_data']['obs_tmplt'] = self.obs_tmplt
        self.wb_def['wb_data']['obs_codes'] = self.obs_codes
        self.wb_def['wb_data']['obs_nests'] = self.obs_nests
        self.wb_def['wb_data']['obs_plugs'] = self.obs_plugs

        self.ctot[11] = self.get_max_links(self.obs_props)
        self.ctot[12] = self.get_max_links(self.obs_atags)

        self.sys_cfg['ctot'] = self.ctot

        # Vault processing complete! Get wb tab defs,
        self.wbd_obj.write_bat_data()

        logger.info(f"Vault ({self.sys_cfg['dir_vault']}) processing complete.")

        return

    def process_md_file(self, filepath):
        self.filepath = filepath

        self.upd_obs_props(self.obs_dupfn, 'dupfn', Path(filepath).name, filepath)
        self.ctot[3] += 1
        self.parse_file()

    def parse_file(self):
        self.plugin_id = ""
        with open(self.filepath, 'r', encoding='utf-8') as file:
            full_content = file.read()

        content = self.rgx_code_blocks.sub('', full_content)
        content = self.strip_inline_code(content)
        content = self.strip_templater_strs(content)

        y_text, x_text = self.split_file(content)
        if len(y_text) == 0 and len(x_text) == 0:
            self.ctot[10] += 1
            self.upd_obs_props(self.obs_xyaml, 'NoFm', self.filepath, self.filepath)

        if len(y_text) != 0:
            self.plugin_id = ''.join([pid for pid in self.plugin_id_def if pid in y_text])
            if self.plugin_id == "NestedDictionary":  # YAML with the word NestedDictionary is okay!
                self.ctot[4] += 1
                self.plugin_id = ""
            self.prop_loc_F_I = "F"
            self.ctot[5] += 1
            self.process_yaml(y_text)

        if len(x_text) != 0:
            self.prop_loc_F_I = "I"
            self.ctot[6] += 1
            self.process_body(x_text)

        self.process_code_blocks(full_content)

    def process_body(self, body_text):
        body_text = "".join(body_text)
        # strip code from text
        # body_text = re.sub(self.rgx_code_blocks, '', body_text)
        # body_text = re.sub(self.rgx_code_inline, '', body_text)

        match_pros = list(self.rgx_body_pros.finditer(body_text))

        # body pros
        for idx, match in enumerate(match_pros):
            m = match_pros[idx].group()

            # logger.debug(f"process_body m={m}  len: {len(m.split('::'))}")

            k, v = m.split("::")
            k = k.strip()
            v = v.strip()
            if k.startswith("["):
                k = k[1:]
            if v.endswith("]"):
                v = v[:-1]
            # if k.endswith(":"):
            #     k = k[:-1]

            self.upd_val(k, v)

        # body tags
        body_tags = self.get_tags_list(body_text)

        for tag in body_tags:
            if tag.isnumeric():
                continue
            else:
                self.upd_val("tags", tag)

        return

    def process_yaml(self, front_text):
        data: dict[Any, Any] = {}
        try:
            data = yaml.safe_load(front_text) or {}
            if not isinstance(data, dict):
                self.upd_obs_props(self.obs_xyaml, 'NonD', f"{self.filepath}", self.filepath)
                return

        except yaml.YAMLError as e:
            logger.debug(f"v_chk_build:process_yaml (BadY) Error in YAML: {self.filepath} {e}")
            self.upd_obs_props(self.obs_xyaml, 'BadY', self.filepath, self.filepath)
            return

        except Exception as e:
            logger.error(f"v_chk_build:process_yaml (ErrY) Unknown YAML: {self.filepath} {e}")
                # e = unhashable type: 'dict'
            self.upd_obs_props(self.obs_xyaml, 'ErrY', self.filepath, self.filepath)
            return

        if data:
            self.unpack_yaml(None, data)
        else:
            self.upd_obs_props(self.obs_xyaml, 'MtFm', self.filepath, self.filepath)
        return

        # new version here

    def unpack_yaml(self, key_passed, a_yaml_dict):
        # For nested dictionaries, this will run reciprocally
        obs_prop_key = ""
        slash = ""

        if key_passed is None:
            obs_prop_key = ""  # otherwise, we get a "/" appended to all keys
        else:
            # if len(self.key_stack) == 1:
            slash = "/"
            for ks in self.key_stack:
                obs_prop_key = f"{obs_prop_key}{ks}{slash}"
                slash = "/"

        # process yaml dictionary
        for key, value in a_yaml_dict.items():
            self.actual_prop_key = key
            key = key.lower()
            if self.actual_prop_key == key:
                self.actual_prop_key = ""

            if isinstance(value, list) and len(value) == 0:
                value = None

            # An unquoted wikilink in a block sequence:
            #     related:
            #       - [[Some Note]]
            # parses as [[['Some Note']]] -- list, list, list, scalar. The
            # innermost-list test is what separates it from an ordinary flow
            # sequence such as "- [alpha, beta]", which parses as
            # [['alpha', 'beta']]. Without that test the branch fired on both,
            # rebuilt the value from value[0][0] alone, and silently discarded
            # every element after the first.
            if (isinstance(value, list) and len(value) == 1
                    and isinstance(value[0], list) and len(value[0]) == 1
                    and isinstance(value[0][0], list) and len(value[0][0]) == 1):
                value = f"[[{value[0][0][0]}]]"

            if isinstance(value, dict):
                # nested dicts not allowed in Obsidian, so this must be a plugin
                self.key_stack.append(key)
                if self.plugin_id is None or self.plugin_id == "":
                    # but no id tag was found using plugin_id_defs in process_yaml
                    self.plugin_id = 'NestedDictionary'
                self.unpack_yaml(key, value)
                self.key_stack.pop()
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        # nested dicts not allowed in Obsidian--this must be a plugin
                        self.key_stack.append(key)
                        if self.plugin_id is None or self.plugin_id == "":
                            # but no id tag was found using plugin_id_defs in process_yaml
                            self.plugin_id = 'NestedDictionary'

                        self.unpack_yaml(key, item)
                        self.key_stack.pop()
                        continue
                    else:
                        self.upd_val(f"{obs_prop_key}{key}", item)
            else:
                # otherwise, the value is a single string, bool, etc.
                self.upd_val(f"{obs_prop_key}{key}", value)
        return

    def upd_val(self, k, v):
        # logger.debug(f"v_chk_build:upd_val {k=}: {v=}")

        # Normalise the value FIRST. Downstream it is used as a dictionary key,
        # and YAML happily produces lists and dicts, which are unhashable.
        if isinstance(v, list) and len(v) == 1 and isinstance(v[0], list):
            # An unquoted wikilink: "- [[Some Note]]" parses as [['Some Note']].
            v = self.convert_list_to_str(v)
        elif isinstance(v, (list, dict, set)):
            # Any other collection, e.g. "aliases: [one, two]".
            v = self.flatten_unhashable(v)

        if k == "tags" and isinstance(v, str):
            v = v.lower()

        # Whether a value is plugin-managed is a question about *where it sits*,
        # not about the file it sits in: key_stack is non-empty only while
        # unpack_yaml is recursing through a nested dict, which Obsidian does
        # not allow and a plugin therefore wrote.
        #
        # This used to test self.plugin_id, which parse_file sets by scanning
        # the whole frontmatter for a known plugin name. That routed every
        # property in the file -- genuine top-level ones, and inline "key:: value"
        # ones from the body -- into obs_nests, so a note carrying a kindle-sync
        # block lost its real author and tags from the Properties and Tags tabs
        # entirely. It also fired on any note that merely mentioned a plugin
        # name inside a value. plugin_id still names the bucket; it no longer
        # decides what goes in it.
        if self.key_stack:
            # Here, we're passing in a subset of obs_nests, the set for this plugin, only
            if v is None or v == "":
                v = "(-None-)"
            self.upd_obs_nests(self.obs_nests, k, v, self.filepath)
            # Deliberately not added to obs_files: plugin-managed data has its
            # own tab and should not inflate the vault tabs.
            return

        if k == "tags":
            self.upd_obs_props(self.obs_atags, v, v, self.filepath) # Note k is not used here...
        else:
            self.upd_obs_props(self.obs_props, k, v, self.filepath)

        self.upd_obs_files(self.obs_files, k, v, self.filepath)

        return

    def upd_obs_files(self, o_files, ukey, uval, fkey):
        logger.debug(f"v_chk_build:upd_obs_files {ukey=}, {uval=}")
        self.ctot[7] += 1
        ukey = ukey.lower()
        fkey = f"{fkey}|{self.prop_loc_F_I}"    # (F)frontmatter or (I)inline indicator

        o_files.setdefault(fkey, {ukey: [self.actual_prop_key]})    # First, make sure fkey exists...
        o_files[fkey].setdefault(ukey,  [self.actual_prop_key])     # Then, make sure ukey exists...
        o_files[fkey][ukey].append(uval)                            # Then update it

        return

    def upd_obs_nests(self, o_files, ukey, uval, fkey):
        logger.debug(f"v_chk_build:upd_obs_nests {ukey=}, {uval=}, {fkey=}")
        self.ctot[8] += 1
        ukey = ukey.lower()
        fkey = f"{self.plugin_id}|{fkey}"

        o_files.setdefault(fkey, {ukey: []})    # First, make sure fkey exists...
        o_files[fkey].setdefault(ukey,  [])     # Then, make sure ukey exists...
        o_files[fkey][ukey].append(uval)        # Then update it

        return

    def upd_obs_props(self, obs_dict, ukey, uval, filepath):
        logger.debug(f"v_chk_build:upd_obs_props {ukey=}, {uval=}, {filepath=}")
        self.ctot[9] += 1
        f_list = []

        # f_list = obs_dict.setdefault(ukey, {uval: []})
        if ukey in obs_dict:
            k_dict = obs_dict[ukey]
        else:
            k_dict = {uval: []}
            obs_dict[ukey] = k_dict
        # we have to get the existing files list, before we can append to it...
        if uval in k_dict:  # fails with [[sbc def]] being made a list [['abc def']] see links in
                            # 'FUN - Frequently Used Notes' in o2_new. This is a valid link, too!
            f_list = k_dict[uval]

        f_list.append(filepath)
        obs_dict[ukey][uval] = f_list

        return

    def process_code_blocks(self, content):
        cb_list = self.extract_codeblocks(content)
        for cb in cb_list:
            cb_sig = self.extract_codeblock_info(cb)
            # file_cb_sig = f"{self.filepath}|{cb_sig}"
            self.upd_obs_props(self.obs_codes, self.filepath, cb_sig, cb)

    def strip_templater_strs(self, markdown_text):
        clean_text = re.sub(self.rgx_templater_strs, "", markdown_text)
        return clean_text

    def strip_wikilinks(self, markdown_text):
        clean_text = re.sub(self.rgx_wikilinks, "", markdown_text)
        return clean_text

    def strip_codeblocks(self, markdown_text):
        return re.sub(self.rgx_code_blocks, "", markdown_text)

    def strip_inline_code(self, markdown_text):
        return re.sub(r"`[^`]*`", "", markdown_text)

    def get_tags_list(self, markdown_text):
        temp_content = copy.deepcopy(markdown_text)
        temp_content = self.strip_codeblocks(temp_content)
        temp_content = self.strip_inline_code(temp_content)
        temp_content = self.strip_templater_strs(temp_content)
        temp_content = self.strip_wikilinks(temp_content)
        tag_list = set(self.rgx_tag_pattern.findall(temp_content))
        return tag_list

    @staticmethod
    def flatten_unhashable(value):
        """Render a list/dict/set YAML value as text so it can key a dict.

        Obsidian shows multi-value properties comma-separated, so a list is
        joined the same way rather than dumped with its Python brackets.
        """
        if isinstance(value, (list, set)):
            return ", ".join(str(item) for item in value)
        return str(value)

    def convert_list_to_str(self, wlink):
        logger.debug(f"v_chk_build:convert_list_to_str:started <{wlink=}>")

        # This is very brute force, but I haven't got  a better way right now
        wlink = f"{wlink}"  # make sure it's a string this will destroy lists!!!
        wlink = wlink.replace("{'", "")
        wlink = wlink.replace("'}", "")
        wlink = wlink.replace("['", "[")  # remove inner single quotes                        [['tests']]
        wlink = wlink.replace("']", "]")
        wlink = wlink.replace('["', '[')  # remove inner double quotes                         [["tests"]]
        wlink = wlink.replace('"]', ']')
        wlink = wlink.replace('"[', '[')  # Cleanup this scenario:                            ["[tests]"]"
        wlink = wlink.replace(']"', ']')  # which will result in:                           [[tests]]
        # At the time of this writing, there are no "lists" of links, but just in case
        # the linter created one, it would likely be like [[[one link]]] and I don't want that!
        wlink = wlink.replace("[[[", "[[")  # Just in case, clean up List of links              [[[tests]]]
        wlink = wlink.replace("]]]", "]]")  # which will result in:                           [[tests]]
        # lastly, let's forces quotes around all [[]]
        wlink = wlink.replace("[[", '"[[')  # remove inner single quotes                        [['tests']]
        wlink = wlink.replace("]]", ']]"')
        logger.debug(f"v_chk_build:convert_list_to_str:done    <{wlink=}>")
        return wlink

    def split_file(self, content):
        file_text = "".join(content)
        yaml_match = list(self.rgx_boundary.finditer(file_text))

        if len(yaml_match) < 2:
            self.upd_obs_props(self.obs_xyaml, 'NoFm', self.filepath, self.filepath)
            return "", file_text

        start, end = yaml_match[0].end(), yaml_match[1].start()
        yaml_text = file_text[start:end].strip()  # Extract YAML content only
        body_text = file_text[end:]

        return yaml_text, body_text

    @staticmethod
    def extract_codeblock_info(a_codeblock) -> str:
        """
        Extracts detailed information from a code block input.

        This function processes the input `a_codeblock`, which could either be a string or a list of strings,
        and extracts the type and action details of the code block. The type of the code block (e.g.,
        BUTTON, DATAVIEW) is derived from the first line of the input, while the action associated with
        the code block is obtained from subsequent details.

        :param a_codeblock: A code block representation that could either be a string or an iterable list
                     of strings. If a list is provided, it is concatenated into a single string.
        :type a_codeblock: list[str] | str
        :return: A tuple containing the code block type (`str`) and the associated action (`str`) as
                 parsed from the input.
        :rtype: tuple[str, str]
        """
        if isinstance(a_codeblock, list):
            a_codeblock = '\n'.join(map(str, a_codeblock)) # might need to raise a Typeerror here

        # cb_sig = cb_action = None
        cb_sig = a_codeblock.split('\n')[0].strip('`').upper()  # 1st line (w/o ```)
        cb_sig.upper()

        # if cb_sig is None or cb_sig == '':
        #     cb_sig = 'CodeBlock'

        # if cb_action is None or cb_action == '':
        #     cb_action = 'Undefined'

        return cb_sig

    def extract_codeblocks(self, some_md_content) -> list:
        """
        Extracts all code blocks from the given content within triple backticks (```).

        This function searches for all occurrences of fenced code blocks (enclosed
        by triple backticks) in the provided content.

        :param some_md_content: The string content from which code blocks should be extracted.
        :return: A list of code blocks identified in the provided content.
        :rtype: list
        """
        return re.findall(self.rgx_code_blocks, some_md_content)

    @staticmethod
    def is_subdirectory(child, parent):
        return parent in child.parents

    @staticmethod
    def  get_max_links(obs_dict):
        pmax = 0
        for key1, val1 in obs_dict.items():
            for key2, val2 in val1.items():
                if pmax < len(val2):
                    pmax = len(val2)

        return pmax

def main() -> None:
    pass

if __name__ == '__main__':
    main()

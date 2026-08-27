"""Harvest the QuickAdd plugin's own configuration for the QuickAdd tab.

QuickAdd stores everything it does -- captures, templates, macros and the steps
inside them -- in ``.obsidian/plugins/quickadd/data.json``. Nothing else in v_chk
reads a plugin's settings; ``PluginMan`` reads only manifests and the enabled
list, so it can say a plugin exists but not what it is configured to do.

The file is a tree and a worksheet is a table, so it is flattened to one row per
key. Three separate nestings have to survive that:

* a ``Multi`` choice holds a nested ``choices`` list,
* a ``Macro`` choice holds ``macro.commands``, an *ordered* list of steps,
* a ``NestedChoice`` command embeds a whole further choice.

Order is carried by ``Seq``, a single monotonic counter over the whole traversal,
so a filtered or re-sorted sheet can still be put back in QuickAdd's own order.
Parentage is carried by repeating the parent's *name* on every row beneath it.
QuickAdd's GUIDs are deliberately not surfaced -- a step that references another
choice by id is resolved to that choice's name instead.
"""

import json
from pathlib import Path

from vault_check.v_chk_logger import logger

#: The plugin this module knows how to read, as it appears in its manifest.
QUICK_ADD_ID = 'quickadd'

#: Keys that carry structure rather than settings. They are consumed by the walk
#: itself and must not also appear as Config rows: the id pair because ids are
#: deliberately not surfaced, the rest because each becomes rows of its own.
_STRUCTURAL_KEYS = frozenset({
    'id', 'choiceId', 'name', 'type', 'choices', 'macro', 'commands', 'choice',
})

#: Printed for a setting that is configured but holds nothing -- an empty list or
#: an empty dict. Without it such a key produces no row at all (a dict) or a
#: blank cell (a list), and both read as "not configured" rather than "empty".
EMPTY_MARK = '(empty)'

SECTION_CHOICE = 'Choice'
SECTION_STEP = 'Step'
SECTION_CONFIG = 'Config'
SECTION_SETTING = 'Setting'


class QuickAddData:
    """Flatten a vault's QuickAdd configuration into ``obs_qadd``.

    :param dir_vault: the vault root.
    :param plugin_lib: the ``PluginMan`` already built for this vault. It is
        passed in rather than constructed because it has just read every
        manifest in the vault and there is no reason to do that twice.

    ``obs_qadd`` is empty -- and the tab is therefore dropped by
    ``ExcelExporter.initialize_all_tabs()`` -- unless QuickAdd is both installed
    and enabled.
    """

    def __init__(self, dir_vault, plugin_lib):
        self.dir_vault = dir_vault
        self.plugin_lib = plugin_lib
        self.seq = 0
        self.rows = []
        self.names_by_id = {}
        self.obs_qadd = {}

        data = self.read_data_file()
        if data:
            self.build_rows(data)
            self.obs_qadd = self.pack_rows()

    # ------------------------------------------------------------------ input

    def plugin_dir(self):
        """The folder QuickAdd is installed in, or None if it is not usable here.

        Both halves of "installed and enabled" are answered by ``PluginMan``:
        an entry exists in ``plugs_lib`` only if a manifest was found, and
        ``enabled`` is True only if the id is in ``community-plugins.json``.

        The *folder* is taken from the manifest entry rather than assumed equal
        to the plugin id -- ``PluginMan`` records the two separately because
        they are not required to match.
        """
        entry = self.plugin_lib.plugs_lib.get(QUICK_ADD_ID) if self.plugin_lib else None

        if not entry:
            logger.debug("QuickAddData: QuickAdd is not installed in %s", self.dir_vault)
            return None

        if not entry.get('enabled'):
            logger.debug("QuickAddData: QuickAdd is installed but not enabled in %s", self.dir_vault)
            return None

        return entry.get('plugin_dir') or QUICK_ADD_ID

    def read_data_file(self):
        """Load QuickAdd's data.json, or return {} if there is nothing to read.

        encoding='utf-8' is not incidental: choice names are routinely emoji, and
        the platform default would raise on them.
        """
        plugin_dir = self.plugin_dir()
        if plugin_dir is None:
            return {}

        data_file = Path(self.dir_vault) / '.obsidian' / 'plugins' / plugin_dir / 'data.json'

        if not data_file.is_file():
            logger.debug("QuickAddData: no data.json at %s", data_file)
            return {}

        try:
            return json.loads(data_file.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.debug("QuickAddData: could not read %s: %s", data_file, e)
            return {}
        except Exception as e:
            raise Exception(f"QuickAddData: Error reading {data_file}: {e}")

    # ------------------------------------------------------------------- walk

    def build_rows(self, data):
        """Walk data.json, appending one row per choice, step, config key and setting."""
        choices = data.get('choices') or []

        # First pass: every choice's name against its id, so a step that points at
        # another choice by id can be rendered as that choice's name.
        self.map_names(choices)

        for choice in choices:
            self.walk_choice(choice, 0, '', SECTION_CHOICE)

        # Everything that is not a choice is a plugin-level setting.
        settings = {k: v for k, v in data.items() if k != 'choices'}
        for key, value in self.flatten(settings):
            self.add_row(SECTION_SETTING, 0, '', '', '', key, value)

    def map_names(self, choices):
        """Recursively record {id: name} for every choice, nested or embedded."""
        for choice in choices:
            self.names_by_id[choice.get('id')] = choice.get('name')

            if choice.get('choices'):
                self.map_names(choice['choices'])

            for command in self.commands_of(choice):
                embedded = command.get('choice')
                if embedded:
                    self.names_by_id[embedded.get('id')] = embedded.get('name')

    @staticmethod
    def commands_of(choice):
        """The ordered command list of a Macro choice; empty for anything else."""
        return (choice.get('macro') or {}).get('commands') or []

    def walk_choice(self, choice, level, parent, section):
        """Emit a choice, its settings, its child choices and its macro steps."""
        name = choice.get('name', '')
        self.add_row(section, level, parent, name, choice.get('type', ''), '', '')
        self.add_config(choice, level + 1, name)

        for child in choice.get('choices') or []:
            self.walk_choice(child, level + 1, name, SECTION_CHOICE)

        for command in self.commands_of(choice):
            self.walk_command(command, level + 1, name)

    def walk_command(self, command, level, parent):
        """Emit one macro step.

        A NestedChoice command and the choice embedded in it are the same thing
        said twice -- same name, and the command carries no settings of its own
        worth a second row. So the step takes the embedded choice's *type*, and
        the embedded choice's settings are attributed to the step. Emitting both
        would add a duplicate row per nested step and a spurious extra level.
        """
        embedded = command.get('choice')
        name = command.get('name', '')
        c_type = embedded.get('type', '') if embedded else command.get('type', '')

        # A 'Choice' step points at another choice by id; show where it goes.
        detail = ''
        if command.get('type') == 'Choice':
            detail = self.names_by_id.get(command.get('choiceId'), '')

        self.add_row(SECTION_STEP, level, parent, name, c_type, '', detail)
        self.add_config(command, level + 1, name)

        if embedded:
            self.add_config(embedded, level + 1, name)

    def add_config(self, source, level, owner):
        """Emit a Config row for every leaf setting of one record."""
        for key, value in self.flatten(source):
            self.add_row(SECTION_CONFIG, level, owner, '', '', key, value)

    def flatten(self, source, prefix=''):
        """Leaf (dotted key, value) pairs, skipping the structural keys.

        Nested dicts become dotted paths -- ``folder.enabled``. List items get an
        index suffix so their order is stated rather than implied, and a dict
        inside a list is JSON-encoded rather than exploded: QuickAdd only puts
        one there in a UserScript's free-form settings, where the shape is the
        script author's business and not a schema v_chk should pretend to know.

        An empty container is reported rather than skipped. Recursing into an
        empty dict yields nothing, so ``globalVariables: {}`` would otherwise
        vanish from a sheet whose whole point is that it omits nothing.
        """
        pairs = []
        for key, value in source.items():
            if key in _STRUCTURAL_KEYS:
                continue

            full_key = f"{prefix}{key}"

            if isinstance(value, dict):
                if not value:
                    pairs.append((full_key, EMPTY_MARK))
                else:
                    pairs.extend(self.flatten(value, f"{full_key}."))
            elif isinstance(value, list):
                if not value:
                    pairs.append((full_key, EMPTY_MARK))
                else:
                    for idx, item in enumerate(value):
                        if isinstance(item, (dict, list)):
                            item = json.dumps(item, ensure_ascii=False)
                        pairs.append((f"{full_key}[{idx}]", item))
            else:
                pairs.append((full_key, value))

        return pairs

    # ----------------------------------------------------------------- output

    def add_row(self, section, level, parent, name, c_type, key, value):
        self.seq += 1
        # Slot 0 is the RowId, which ExcelExporter overwrites with the sheet row
        # number. It is carried here so the list is already in column order.
        self.rows.append([0, self.seq, section, level, parent, name, c_type, key, value])

    def pack_rows(self):
        """Wrap the rows in the two-level shape ``ExcelExporter.export_tab()`` unpacks.

        It iterates ``{outer: {inner: row_list}}``, so a tab whose rows have no
        natural two-part key uses the same key twice -- obs_plugs does this with
        the plugin id. The key here is the sequence number, zero-padded so the
        dict's insertion order, the YAML file's order and the sheet's order are
        all the same order.
        """
        return {f"{row[1]:05d}": {f"{row[1]:05d}": row} for row in self.rows}


def main() -> None:
    pass


if __name__ == '__main__':
    main()

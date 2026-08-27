"""The QuickAdd tab reads the plugin's own data.json.

Nothing else in the suite builds an .obsidian/plugins tree -- every other test
vault has no .obsidian at all, so PluginMan only ever takes its early return.
These tests therefore construct the plugin folder themselves.

Row layout, which the DefQadd column order and the export_tab 'qadd' branch both
depend on:

    [RowId, Seq, Section, Level, Parent, Name, Type, Key, Value]
"""

import json

import pytest

from vault_check.v_chk_plugin_man import PluginMan
from vault_check.v_chk_quick_add import EMPTY_MARK, QuickAddData

ROWID, SEQ, SECTION, LEVEL, PARENT, NAME, TYPE, KEY, VALUE = range(9)

QUICK_ADD_DATA = {
    "choices": [
        {
            "id": "multi-1", "name": "Periodic", "type": "Multi",
            "command": True, "collapsed": True,
            "choices": [
                {"id": "tpl-1", "name": "Weekly", "type": "Template",
                 "templatePath": "t/weekly.md",
                 "folder": {"enabled": True, "folders": []}},
                {"id": "tpl-2", "name": "Monthly", "type": "Template",
                 "templatePath": "t/monthly.md"},
            ],
        },
        {
            "id": "macro-1", "name": "Add Note", "type": "Macro", "command": True,
            "macro": {"id": "m-1", "name": "Add Note Macro", "commands": [
                {"id": "cmd-1", "name": "Pause", "type": "Wait", "time": 400},
                {"id": "cmd-2", "name": "Hand off", "type": "Choice",
                 "choiceId": "tpl-1"},
                {"id": "cmd-3", "name": "Log it", "type": "NestedChoice",
                 "choice": {"id": "cap-1", "name": "Log it", "type": "Capture",
                            "captureTo": "log.md"}},
            ]},
        },
    ],
    "version": "2.12.3",
    "templateFolderPath": "t",
    "globalVariables": {},
}


@pytest.fixture
def quickadd_vault(make_vault):
    """Build a vault with a QuickAdd plugin folder in it.

    make_vault writes text at arbitrary relative paths, so the JSON goes in as
    one line -- it dedents and lstrips content, which pretty-printed JSON would
    notice.
    """

    def _build(data=QUICK_ADD_DATA, installed=True, enabled=True,
               plugin_dir="quickadd", manifest_id="quickadd"):
        files = {"note.md": "Body.\n"}

        if installed:
            base = f".obsidian/plugins/{plugin_dir}"
            files[f"{base}/manifest.json"] = json.dumps(
                {"id": manifest_id, "name": "QuickAdd", "version": "2.12.3",
                 "minAppVersion": "1.0.0", "author": "Christian B. B. Houmann",
                 "isDesktopOnly": False, "description": "Quickly add content."})
            if data is not None:
                files[f"{base}/data.json"] = json.dumps(data, ensure_ascii=False)

        files[".obsidian/community-plugins.json"] = json.dumps(
            [manifest_id] if enabled else [])

        return make_vault(files, name="QuickAddVault")

    return _build


def harvest(vault):
    """The flattened rows, unwrapped from the two-level export_tab shape."""
    lib = PluginMan(str(vault))
    qadd = QuickAddData(str(vault), lib)
    return [next(iter(inner.values())) for inner in qadd.obs_qadd.values()]


def find(rows, section, name):
    return next(r for r in rows if r[SECTION] == section and r[NAME] == name)


# ---------------------------------------------------------------------------
# Installed and enabled -- the gate
# ---------------------------------------------------------------------------

def test_a_vault_without_quickadd_yields_nothing(make_vault):
    """An empty sink is how the tab gets dropped, so it must not be an error."""
    vault = make_vault({"note.md": "Body.\n"})

    assert harvest(vault) == []


def test_installed_but_not_enabled_yields_nothing(quickadd_vault):
    """QuickAdd present on disk but absent from community-plugins.json.

    No real vault on this machine is in that state, so only a fixture can pin
    it -- and 'installed and enabled' was the requirement.
    """
    assert harvest(quickadd_vault(enabled=False)) == []


def test_enabled_but_no_data_file_yields_nothing(quickadd_vault):
    assert harvest(quickadd_vault(data=None)) == []


def test_unreadable_data_file_yields_nothing_rather_than_raising(quickadd_vault):
    vault = quickadd_vault()
    data_file = vault / ".obsidian" / "plugins" / "quickadd" / "data.json"
    data_file.write_text("{ this is not json", encoding="utf-8")

    assert harvest(vault) == []


def test_the_plugin_folder_need_not_match_the_manifest_id(quickadd_vault):
    """PluginMan records the folder separately because they can differ, and the
    harvester follows the folder -- not a hard-coded 'quickadd'."""
    rows = harvest(quickadd_vault(plugin_dir="quickadd-1.2.3"))

    assert find(rows, "Choice", "Periodic")[TYPE] == "Multi"


# ---------------------------------------------------------------------------
# Parentage and ordering -- the shape that was asked for
# ---------------------------------------------------------------------------

def test_seq_numbers_every_row_in_traversal_order(quickadd_vault):
    """Seq is the whole sequencing scheme: it is what puts a filtered or
    re-sorted sheet back into QuickAdd's own order."""
    rows = harvest(quickadd_vault())

    assert [r[SEQ] for r in rows] == list(range(1, len(rows) + 1))


def test_a_multi_choices_children_follow_it_in_order(quickadd_vault):
    rows = harvest(quickadd_vault())
    children = [r for r in rows if r[SECTION] == "Choice" and r[PARENT] == "Periodic"]

    assert [r[NAME] for r in children] == ["Weekly", "Monthly"]
    assert children[0][SEQ] < children[1][SEQ]
    assert children[0][LEVEL] == 1


def test_macro_steps_keep_the_order_they_run_in(quickadd_vault):
    rows = harvest(quickadd_vault())
    steps = [r for r in rows if r[SECTION] == "Step"]

    assert [r[NAME] for r in steps] == ["Pause", "Hand off", "Log it"]
    assert [r[SEQ] for r in steps] == sorted(r[SEQ] for r in steps)


def test_the_parent_name_is_repeated_on_every_row_beneath_it(quickadd_vault):
    rows = harvest(quickadd_vault())

    # config of a nested child, a macro step, and a step's own config
    assert find(rows, "Choice", "Weekly")[PARENT] == "Periodic"
    assert find(rows, "Step", "Pause")[PARENT] == "Add Note"
    weekly_cfg = [r for r in rows if r[SECTION] == "Config" and r[PARENT] == "Weekly"]
    assert weekly_cfg, "a child choice's settings must name the child as their parent"
    assert all(r[NAME] == "" for r in weekly_cfg)


def test_a_top_level_choice_has_no_parent(quickadd_vault):
    rows = harvest(quickadd_vault())

    assert find(rows, "Choice", "Periodic")[PARENT] == ""
    assert find(rows, "Choice", "Periodic")[LEVEL] == 0


# ---------------------------------------------------------------------------
# Ids are not surfaced
# ---------------------------------------------------------------------------

def test_a_choice_step_shows_the_target_by_name_not_by_id(quickadd_vault):
    """'Hand off' points at tpl-1 by id; the sheet must say 'Weekly'."""
    assert find(harvest(quickadd_vault()), "Step", "Hand off")[VALUE] == "Weekly"


def test_no_row_anywhere_exposes_a_quickadd_id(quickadd_vault):
    rows = harvest(quickadd_vault())
    ids = {"multi-1", "tpl-1", "tpl-2", "macro-1", "m-1",
           "cmd-1", "cmd-2", "cmd-3", "cap-1"}

    assert not [r for r in rows if ids & {str(c) for c in r}]
    assert not [r for r in rows if r[KEY] in ("id", "choiceId")]


# ---------------------------------------------------------------------------
# Flattening
# ---------------------------------------------------------------------------

def test_a_nested_choice_step_is_one_row_not_two(quickadd_vault):
    """The command and the choice embedded in it share a name. Emitting both
    duplicated every nested step and invented a level that is not there."""
    rows = harvest(quickadd_vault())
    log_it = [r for r in rows if r[NAME] == "Log it"]

    assert len(log_it) == 1
    assert log_it[0][SECTION] == "Step"
    # the step carries the embedded choice's type, not "NestedChoice"
    assert log_it[0][TYPE] == "Capture"
    # ...and the embedded choice's settings are attributed to the step
    assert any(r[PARENT] == "Log it" and r[KEY] == "captureTo" and r[VALUE] == "log.md"
               for r in rows)


def test_nested_settings_become_dotted_keys(quickadd_vault):
    rows = harvest(quickadd_vault())
    keys = {r[KEY] for r in rows if r[PARENT] == "Weekly"}

    assert "folder.enabled" in keys
    assert "templatePath" in keys


def test_an_empty_container_is_reported_rather_than_dropped(quickadd_vault):
    """An empty list renders blank and an empty dict recurses to nothing, so
    both would read as 'not configured' instead of 'configured, empty'."""
    rows = harvest(quickadd_vault())

    empty_list = next(r for r in rows if r[KEY] == "folder.folders")
    empty_dict = next(r for r in rows if r[KEY] == "globalVariables")

    assert empty_list[VALUE] == EMPTY_MARK
    assert empty_dict[VALUE] == EMPTY_MARK


def test_plugin_level_settings_are_their_own_section(quickadd_vault):
    rows = harvest(quickadd_vault())
    settings = {r[KEY]: r[VALUE] for r in rows if r[SECTION] == "Setting"}

    assert settings["version"] == "2.12.3"
    assert settings["templateFolderPath"] == "t"
    assert all(r[PARENT] == "" for r in rows if r[SECTION] == "Setting")


def test_emoji_in_choice_names_survive(quickadd_vault):
    """Names are routinely emoji; reading data.json without encoding='utf-8'
    would raise on a Windows default codepage."""
    data = json.loads(json.dumps(QUICK_ADD_DATA))
    data["choices"][0]["name"] = "📆 Periodic"
    rows = harvest(quickadd_vault(data=data))

    assert find(rows, "Choice", "📆 Periodic")[TYPE] == "Multi"
    assert any(r[PARENT] == "📆 Periodic" for r in rows)


def test_the_two_level_shape_export_tab_unpacks_is_preserved(quickadd_vault):
    """export_tab iterates {outer: {inner: row}}, and the sheet's row order is
    this dict's insertion order."""
    vault = quickadd_vault()
    qadd = QuickAddData(str(vault), PluginMan(str(vault)))

    for outer, inner in qadd.obs_qadd.items():
        assert list(inner.keys()) == [outer]
        assert len(next(iter(inner.values()))) == 9

    assert list(qadd.obs_qadd) == sorted(qadd.obs_qadd)

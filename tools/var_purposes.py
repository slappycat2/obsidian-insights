"""Purpose text for tools/var_dictionary.py.

Resolution order is authored > the source's own comment > a pattern rule >
a derived description, and every row records which one it got so nothing in the
workbook reads as more certain than it is.

Editing this file is the way to improve the dictionary: move an entry up to
AUTHORED and it stops being a guess.
"""
import re

# ---------------------------------------------------------------- authored --
# Written after reading the code and CLAUDE.md. Keyed "Owner.name", or "name"
# where the name is unambiguous across the package.
AUTHORED = {
# --- package-level ---------------------------------------------------------
"__version__": "The single source of truth for the version. pyproject declares dynamic=['version'] and hatchling reads it from here; the CLI --version, the splash, SysConfig.sys_ver and both Summary tab strings all derive from it. Never type a version literal anywhere else.",
"CTOT_SLOTS": "How many slots the ctot counter list has. Stated once here; v_chk_build, v_chk_setup, v_chk_obs_app, v_chk_wb_tabs and tests/conftest all import it, and they must agree or DefAr51 indexes off the end of the list.",
"LOG_LEVELS": "The -d/--debug-level choices accepted on the command line.",
"PHASES": "Names of the four pipeline stages, used for the splash screen's progress text.",
"ACTIVE_LOG_CONFIG": "Which JSON/YAML logging dictConfig under logging_configs/ is live. Swap this to change handlers without touching code.",
"DEFAULT_LOG_LEVEL": "Log level used when the CLI does not override it.",
"logger": "The one logger every module imports. make_logger(level) configures it once, from cli().",
"pil_logger": "Pillow's own logger, held separately so its chatter can be silenced independently of ours.",
"LOG_RECORD_BUILTIN_ATTRS": "The stock LogRecord attribute names, so the JSON formatter can tell built-in fields from extras a caller passed in.",

# --- paths (v_chk_paths.py) ------------------------------------------------
"PACKAGE_DIR": "The installed package directory, resolved from __file__. Root for every *asset* path, which is why running from any working directory works and why Path.cwd() must never come back.",
"DATA_ROOT": "Root for everything *writable*. Resolution order: $V_CHK_DATA_DIR, then the repo root when running from a source checkout (detected via pyproject.toml), then ~/.v_chk. Resolved once at import time, which is why tests set the env var before importing vault_check.",
"DATA_DIR_ENV_VAR": "Name of the environment variable that redirects DATA_ROOT. The seam the test suite uses.",
"ASSETS_DIR": "Package assets (logos, banner, area51 image) — read-only, ships in the wheel.",
"LOGGING_CONFIG_DIR": "Where the JSON/YAML logging dictConfigs live.",
"DATA_DIR": "Writable data root for generated output.",
"BATCH_DIR": "Where the per-run wb_def YAML batch files are written. Stale files here are the first thing to check when a run produces odd output.",
"WORKBOOK_DIR": "Where generated .xlsx workbooks are written.",
"LOG_DIR": "Where rotating logs are written (3 MB, 50 backups).",
"CONFIG_FILE": "Absolute path to CONFIG.yaml under DATA_ROOT.",
"RUNTIME_DIRS": "The directories ensure_runtime_dirs() creates on startup.",
"LOGO_SETUP": "Logo image shown on the setup screen.",
"LOGO_SPLASH": "Logo image shown on the splash screen.",
"BANNER": "Banner image rendered into the workbook.",
"AREA51": "Image rendered on the Area51 tab.",
"ICON_WINDOW": "Window icon (.ico) for the Tk windows.",

# --- fonts / rendering constants -------------------------------------------
"DISPLAY_FONT": "The tab-title typeface (Impact), resolved once at module import. An .xlsx cell names exactly one font with no fallback list, so display_font() checks what is actually installed and returns None when it is absent.",
"TITLE_FONT": "The module-level font used for every tab title and subtitle. Tab subclasses must never name a font themselves.",
"FONT_SUFFIXES": "Filename suffixes tried when probing the OS for an installed font.",
"FALLBACK_FONT": "Arial — what a cell gets when display_font() returns None. Present on Windows and macOS, and substituted by metric-compatible Liberation Sans on Linux, where Impact is not an OS font.",
"_UNSAFE_IN_FILENAME": "Everything safe_name_part() strips out of a vault name. Two reasons, not one: the name is a folder on someone else's disk, and get_last_bat() feeds the same stub to glob, where [, * and ? would be read as a pattern.",
"DEFAULT_TAB_SEQ": "The default render order and inclusion list for tabs. sys_cfg['sys_tab_seq'] overrides it.",
"SPLASH_Test": "Debug flag that keeps the splash screen up for inspection.",

# --- SysConfig: system settings --------------------------------------------
"SysConfig.sys_id": "Application id ('v_chk'). Prefixes every generated filename and is the fallback stub when a vault name sanitises away to nothing.",
"SysConfig.sys_ver": "Running version, always taken from __version__ rather than from CONFIG.yaml — otherwise the first config a machine writes would pin the version forever.",
"SysConfig.sys_cfg": "The packed settings dict. THIS is what every downstream stage reads, not the attributes. Any attribute changed after load_config() must be followed by cfg_pack() or the change is silently ignored.",
"SysConfig.sys_cfg_os": "platform.system() — decides where obsidian.json lives and how dot-directories are found.",
"SysConfig.sys_dir_sys": "System/base directory for the install.",
"SysConfig.sys_dir_dat": "Writable data directory (DATA_ROOT).",
"SysConfig.sys_dir_bat": "Directory holding the YAML batch files that carry wb_def between stages.",
"SysConfig.sys_dir_wbs": "Directory holding generated workbooks.",
"SysConfig.sys_dir_log": "Directory holding rotating logs.",
"SysConfig.sys_dir_img": "Directory holding the image assets used in the workbook.",
"SysConfig.sys_pn_cfg": "Full path to CONFIG.yaml.",
"SysConfig.sys_pn_wb_exec": "Full path to the spreadsheet executable that ExcelExporter Popens when the workbook is finished. Validated by validate_sys_pn_wb_exec(); this is the field the setup screen's Full Path box edits.",
"SysConfig.sys_pn_batch": "Full path to this run's batch file, allocated sequentially per vault as v_chk_<vault>_NNNN.yaml.",
"SysConfig.sys_pn_wbs": "Full path to this run's workbook, sharing the batch file's sequence number.",
"SysConfig.sys_tab_seq": "Which tabs to render and in what order. ExcelExporter rewrites it to the surviving list after dropping empty tabs.",
"SysConfig.sys_vlts": "Every vault Obsidian knows about, parsed from its obsidian.json.",
"SysConfig.cur_vlts": "Per-vault settings for the vaults currently configured — the dict the setup screen swaps in and out as you change the dropdown.",
"SysConfig.sys_pn_lg2": "Path to the setup-screen logo.",
"SysConfig.sys_pn_lg3": "Path to the splash-screen logo.",
"SysConfig.sys_pn_ico": "Path to the window icon.",
"SysConfig.sys_pn_bnr": "Path to the workbook banner image.",
"SysConfig.sys_pn_a51": "Path to the Area51 tab image.",
"SysConfig.sys_splash_bg": "Splash screen background colour (#800000, maroon).",
"SysConfig.sys_init": "Set by -i/--init: delete CONFIG.yaml, batch files and workbooks. Prompts first.",
"SysConfig.interactive": "False under --headless. Makes run_setup_ui() raise ConfigIncompleteError rather than block on a window nobody can answer.",
"SysConfig.force_setup": "Set by -s/--setup: show the setup screen even when CONFIG.yaml already validates.",
"SysConfig.vault_path_override": "A vault path given on the command line, which wins over the one in CONFIG.yaml.",
"SysConfig.o_app": "The ObsidianApp instance that discovers vaults; vault discovery is delegated to it rather than done here.",
"SysConfig.v_chk_date": "Timestamp of this run, stamped into the workbook.",
"SysConfig.ctot": "The counter list rendered on the Area51 tab. Incremented all through v_chk_build.",

# --- SysConfig: per-vault settings -----------------------------------------
"SysConfig.vault_name": "Name of the vault being scanned. Also the key into cur_vlts and, sanitised, part of every generated filename.",
"SysConfig.vault_id": "Obsidian's own id for the vault, used to build obsidian:// hyperlinks that open the right vault.",
"SysConfig.dir_vault": "Absolute path to the vault root. Everything is rglob'd from here.",
"SysConfig.dir_templates": "The Templater folder. Files under it are harvested into obs_tmplt and deliberately kept out of every other sink.",
"SysConfig.skip_rel_str": "Comma-separated folder names to ignore, as typed on the setup screen. Issue #17 proposes renaming this to skip_abs_lst_user.",
"SysConfig.skip_abs_lst": "skip_rel_str resolved to absolute paths — what the walk actually tests against.",
"SysConfig.dirs_dot": "Dot-directories found in the vault (.obsidian and friends), excluded from the walk.",
"SysConfig.bool_shw_notes": "Show Notes checkbox: whether explanatory note text is rendered on each tab.",
"SysConfig.bool_rel_paths": "Use Full Paths in Links checkbox. Issue #14 proposes a third option, note name only.",
"SysConfig.bool_summ_rows": "Whether summary rows are included.",
"SysConfig.bool_unused_1": "Reserved. Wired to the disabled 'For Future Use-1' checkbox on the setup screen.",
"SysConfig.bool_unused_2": "Reserved. Wired to the disabled 'For Future Use-2' checkbox.",
"SysConfig.bool_unused_3": "Reserved. No widget on the screen at all.",
"SysConfig.link_lim_vals": "Cap on FileNN hyperlink columns on the Values tab. 0 means unlimited; the real count is min(this, ctot[11]). Issue #8 asks for truncation to be shown when it bites.",
"SysConfig.link_lim_tags": "Same cap for the Tags tab, against ctot[12].",

# --- VaultHealthCheck: the harvest ----------------------------------------
"obs_props": "Frontmatter and inline properties: {key: {value: [filepath, ...]}}. Feeds the Properties and Values tabs.",
"obs_atags": "Tags found in note bodies, same {key: {value: [paths]}} shape. Feeds the Tags tab.",
"obs_xyaml": "Notes whose frontmatter is not usable, classified rather than dropped: BadY, NoFm, MtFm, ErrY, NonD. Feeds the Possible Issues tab.",
"obs_dupfn": "Filenames that occur more than once in the vault. Feeds the Duplicates tab.",
"obs_files": "Per-file view, {filepath|F-or-I: {key: [values]}} — F for frontmatter, I for inline. The only place original key casing survives.",
"obs_tmplt": "Templater files. Harvested, but deliberately reaches only the Templates tab; kept out of properties, tags, files, nested-plugin data, code blocks, duplicates and the bad-YAML tab.",
"obs_codes": "Code blocks found in note bodies, by language/signature. Feeds the Code tab and helps map signatures to plugins.",
"obs_nests": "Nested YAML, treated as plugin-managed data: {plugin_id|filepath: {key: [values]}}. Obsidian does not allow nested frontmatter dicts, so a nested dict means a plugin wrote it.",
"obs_plugs": "Installed plugins read from .obsidian/plugins/*/manifest.json plus community-plugins.json. Feeds the Plugins tab.",
"obs_empty": "Plain list of paths to notes whose raw text is whitespace only. The one sink that is not a nested dict; ExcelExporter turns it into a set so the Xyml tab can print '(empty file)' instead of a lookup that reads blank.",
"obs_datav": "Dataview-style data. Issue #12 covers task shorthand fields.",
"VaultHealthCheck.key_stack": "Tracks how deep unpack_yaml() currently is inside a nested dict. The routing decision is structural — upd_val() tests whether this is non-empty. It must never go back to testing plugin_id, which is a whole-file text scan and swallowed a plugin-touched note's genuine top-level properties.",
"VaultHealthCheck.plugin_id": "Which plugin a nested block is attributed to. Names the bucket only; it does not decide routing.",
"VaultHealthCheck.plugin_id_def": "Fallback bucket name when no plugin can be identified — 'NestedDictionary'.",
"VaultHealthCheck.actual_prop_key": "The property key with its original casing preserved. Everything else is lowercased for grouping; this is surfaced only on the Files tab.",
"VaultHealthCheck.prop_loc_F_I": "Whether a property came from Frontmatter or Inline text.",
"VaultHealthCheck.isTemplate": "Whether the file currently being parsed lives under the Templater folder. Gates it out of every sink but obs_tmplt, and makes record_yaml_issue() a no-op, since Templater syntax is not valid YAML.",
"VaultHealthCheck.filepath": "Path of the file currently being parsed.",
"VaultHealthCheck.dbug": "Local verbose-logging switch for the parser.",
"rgx_fm_open": r"Anchors the opening frontmatter delimiter to the top of the file: \A﻿?\s*---[ \t]*$. The leading \s* skips a BOM and the blank line a stripped Templater block leaves, but cannot cross non-whitespace. This is the v0.4.0 fix: the boundary search previously took the first two ^---$ matches wherever they fell, so Markdown horizontal rules and setext underlines looked like delimiters.",
"rgx_boundary": "Finds the closing frontmatter delimiter, once rgx_fm_open has matched at the top.",
"rgx_body_pros": "Finds inline `key:: value` properties in the body. Needs re.MULTILINE; its absence is pinned as a regression in the test suite.",
"rgx_tag_pattern": "Finds #tags in the body, with the guard that stops a wikilink pipe reading as a tag.",
"rgx_code_blocks": "Fenced code blocks, stripped from the body after the frontmatter split — strip them first and a fence at the top of a note promotes a body rule to line 1.",
"rgx_code_inline": "Inline `code` spans, stripped so their contents are not harvested as properties or tags.",
"rgx_wikilinks": "Obsidian [[wikilinks]].",
"rgx_templater_strs": "Templater tags, stripped before parsing.",
"rgx_noTZdatePattern": "Matches a timezone suffix on a datetime string. Excel has no timezone-aware datetime, so it is stripped. Compiled once at startup as of v0.4.1.",
"ExcelExporter.rgx_noTZdateReplace": "Replacement text for the timezone strip.",

# --- WbDataDef: the handoff ------------------------------------------------
"wb_def": "The whole handoff between stages, and the only thing that crosses them. Exactly three keys: sys_cfg, wb_data, wb_tabs. Written to a YAML batch file and re-read from disk by each stage, so anything added to it must be yaml.dump-able.",
"wb_data": "The harvested vault data inside wb_def — every obs_* sink.",
"WbDataDef.wb_tabs": "Per-tab definitions inside wb_def, keyed by 4-character tab id. Adding or renaming a tab has to be done here as well as in four other places.",
"WbDataDef.xyml_descs": "Maps each bad-frontmatter code (BadY, NoFm, MtFm, ErrY, NonD) to its display text. 'Not a problem, if intentional' is deliberate: the tool identifies things worth reviewing, not necessarily errors.",
"WbDataDef.plugin_id_def": "Default bucket for nested YAML that cannot be attributed to a plugin.",
"WbDataDef.file_stub": "Base filename for this run: sys_id joined to the vault name run through safe_name_part(). Makes the batch sequence per-vault, so scanning a second vault starts again at _0000.",

# --- NewTab / the tab system ----------------------------------------------
"NewTab.tab_id": "The 4-character tab id (pros, vals, tags, file, code, xyml, dups, tmpl, nest, plug, summ, ar51). A mismatch anywhere raises or silently drops the tab.",
"NewTab.tab_def": "The complete cell-level definition of one tab, built by a DefXxxx subclass and consumed by ExcelExporter.",
"NewTab.tab_name": "Display name shown on the sheet tab.",
"NewTab.tab_title": "Title rendered at the top of the sheet.",
"NewTab.data_src": "Which obs_* sink this tab reads. A tab whose data_src is empty is dropped rather than rendered.",
"NewTab.tbl_name": "Excel table name, always tbl_<tab_id>.",
"NewTab.tbl_hdr_row": "Row the table header sits on.",
"NewTab.tbl_beg_col": "First column of the table.",
"NewTab.tbl_end_col": "Last column of the table, after the variable-width FileNN link columns.",
"NewTab.tbl_fix_cols": "How many columns are fixed, before the link columns begin.",
"NewTab.hdr_RowId": "Header text for the RowId helper column.",
"NewTab.hdr_IsVis": "Header text for the IsVisible helper column. calc_col_pointers() is the only place its position is decided — a tab declares tab_has_isVisible_col and must never state a column number. Re-introducing a per-tab constant is issue #4, and the old constants had already drifted.",
"NewTab.hdr_PVI": "Header text for the P-V Index helper column.",
"NewTab.hdr_links_pfx": "Prefix for the FileNN hyperlink column headers.",
"NewTab.link_lim_vals": "The user's cap on Values-tab link columns, copied from sys_cfg.",
"NewTab.link_lim_tags": "The user's cap on Tags-tab link columns.",
"NewTab.link_max_vals": "Actual link columns for values: ctot[11] capped by link_lim_vals.",
"NewTab.link_max_tags": "Actual link columns for tags: ctot[12] capped by link_lim_tags.",
"NewTab.help_txt": "The explanatory note text rendered on the tab when Show Notes is on.",
"NewTab.showGridLines": "Whether Excel gridlines stay visible on this sheet.",
"NewTab.cell_width": "Default column width.",
"NewTab.tab_txt_sz": "Default text size for the tab.",
"NewTab.tab_fill_clr": "Fill colour for the sheet tab.",
"NewTab.tab_clr_txt": "Text colour paired with the tab fill.",
"NewTab.tab_link_clr": "Colour used for hyperlink text.",
"NewTab.tab_table_files": "The FileNN hyperlink column definitions for this tab.",
"NewTab.colors": "The Colors instance the tab draws its palette from.",
"NewTab.hdr_clrs": "Header row colours.",
"NewTab.font_title_lst": "Font settings for tab titles.",
"NewTab.font_subs_lst": "Font settings for subtitles.",
"NewTab.font_body_lst": "Font settings for body cells.",
"NewTab.bdr_thin": "Thin cell border style.",
"NewTab.bdr_thick": "Thick cell border style.",
"NewTab.bdr_double": "Double cell border style.",

# --- ExcelExporter ---------------------------------------------------------
"ExcelExporter.exl_file": "Path of the workbook being written.",
"ExcelExporter.tabs_built": "Which tabs have been rendered so far.",
"ExcelExporter.wb_tabs_open": "Tabs still to render.",
"ExcelExporter.wb_tabs_done": "Tabs finished rendering.",
"ExcelExporter.next_cell_col": "Cursor: the next column to write into.",
"ExcelExporter.last_cell_row": "Cursor: the last row written.",
"ExcelExporter.xl_a_col": "Current column in Excel's A1 letter form.",
"ExcelExporter.COL_STEP": "Column stride between repeated link columns.",
"ExcelExporter.PROP_BEG_COL": "First column of the property block.",
"ExcelExporter.PROP_TOT_COLS": "How many columns the property block spans.",
"ExcelExporter.TAG_BEG_COL": "First column of the tag block.",
"ExcelExporter.TAG_TOT_COLS": "How many columns the tag block spans.",
"ExcelExporter.TABLE_GROUPINGS": "Whether Excel row/column grouping is applied.",
"ExcelExporter.tab_id_sub_key": "Sub-key used when a tab id needs qualifying.",
"ExcelExporter.plugin_lib": "Plugin metadata used when rendering the Plugins tab.",

# --- Colors ----------------------------------------------------------------
"Colors.tab_clrs": "Per-tab colour scheme, keyed by tab id. A missing entry is a KeyError, which is one of the five places adding a tab must touch.",
"Colors.tbl_clrs": "Table colour schemes.",
"Colors.tbl_txts": "Text colours paired with the table schemes.",
"Colors.table_styles": "The Excel built-in table styles available.",
"Colors.table_style": "The style chosen for the current tab.",
"Colors.row_clr_idx": "Row-colour lookup used for banding.",
"Colors.base_clr": "Base colour the current scheme is derived from.",
"Colors.clr1": "Primary fill for the current tab.",
"Colors.txt1": "Text colour paired with clr1.",
"Colors.clr2": "Secondary fill for the current tab.",
"Colors.txt2": "Text colour paired with clr2.",
"Colors.shade": "Current shade level.",
"Colors.dflt_shade": "Default shade level.",
"Colors.dflt_row_style": "Default row style index.",
"Colors.tbl_row_style": "Row style index for the current table.",
"Colors.err_txt": "Colour used for error text (red).",

# --- PluginMan -------------------------------------------------------------
"PluginMan.known_plug_sigs": "Maps code-block signatures (dataview, button, ...) to plugin ids, so a code fence can be attributed to the plugin that reads it.",
"PluginMan.plugs_lib": "Everything read from .obsidian/plugins/*/manifest.json plus community-plugins.json.",
"PluginMan.plugin_dir": "The .obsidian/plugins directory being read.",
"PluginMan.v_path": "Vault path the plugin scan runs against.",

# --- ObsidianApp -----------------------------------------------------------
"ObsidianApp.pn_obs_json": "Path to Obsidian's own obsidian.json — %APPDATA%/obsidian on Windows, ~/.config/obsidian on Linux, ~/Library/Application Support/obsidian on macOS.",
"ObsidianApp.dflt_vault_name": "The vault Obsidian had open last, used as the default when none is given.",
"ObsidianApp.obs_os": "Which OS branch was taken when locating obsidian.json.",

# --- SetupScreen -----------------------------------------------------------
"SetupScreen.root": "The Tk root window. Created in __init__, so a caller can register callbacks on it before show() builds the widgets and enters mainloop.",
"SetupScreen.saved": "Whether Save & Run was pressed. show() returns this, and it is the entire signal the caller gets: Cancel and the window close button both leave it False, which run_setup_ui() turns into SetupCancelledError. Keep it intact — the screen previously had no way to report which button was pressed.",
"SetupScreen.sys_obj": "The SysConfig being edited.",
"SetupScreen.c_vlts": "Pointer to sys_obj.cur_vlts, for shorter references during the vault swap.",
"SetupScreen.v_list": "Vault names shown in the dropdown.",
"SetupScreen.last_vault_name": "Which vault the screen was showing before the dropdown changed. Step one of the swap writes the on-screen values back under THIS name, not the newly selected one.",
"SetupScreen.wb_col_max": "Upper bound on the link-column spinboxes (16300).",
"SetupScreen.wb_col_help": "Help text shown beside the spinboxes when a limit is set.",
"SetupScreen.save_button": "Handle to the Save & Run button.",
"SetupScreen.frame_image": "The logo PhotoImage. Held on the instance because Tk does not keep its own reference and the image would otherwise be garbage-collected blank.",
"SetupScreen.logo": "Path to the setup-screen logo.",
"SetupScreen.icon": "Path to the window icon.",
"SetupScreen.skip_rel_str_msg": "Validation message for the ignore-directories field.",
"SetupScreen.skip_rel_str_valid": "Whether the ignore-directories value currently validates.",

# --- SplashScreen ----------------------------------------------------------
"SplashScreen.status_var": "Tk variable the pipeline's progress callback writes into. The splash owns the mainloop, so the work happens inside a splash.after() callback.",
"SplashScreen.progress": "Current stage number out of four.",
"SplashScreen.logo_img": "Splash logo PhotoImage, held to stop it being collected.",
}


AUTHORED.update({
"SplashScreen.status_label": "Label the pipeline's progress text is written into.",
"SplashScreen.logo_label": "Label holding the splash logo image.",
"SplashScreen.logo_path": "Path to the splash logo asset.",
"SplashScreen.title": "Application title shown on the splash.",
"SplashScreen.version": "Version string shown on the splash, derived from __version__ like every other display of it.",
"NewWb.Colors": "The Colors class, held so each tab definition can be given its palette.",
"NewWb.tab_common": "Display metadata for every tab — name, titles, help text and data_src, keyed by tab id. One of the five places adding or renaming a tab must touch.",
"NewWb.tab_id": "The tab currently being built, as NewWb walks the dispatch chain. An unknown key raises 'Unexpected key'.",
"NewWb.tab_def": "The tab_def being assembled for the current tab.",
"NewWb.wb_tabs": "All finished tab definitions, written back into wb_def.",
"JsonFile.json_path": "Path of the JSON file being read.",
"JsonFile.json_data": "Parsed contents of that file.",
"JsonFile.err_msg": "Why the read failed, if it did — kept rather than raised so a missing or malformed file can be reported instead of crashing the run.",
"ObsidianApp.cur_vlts": "Per-vault settings built from Obsidian's obsidian.json.",
"ObsidianApp.sys_vlts": "Every vault Obsidian knows about, as read from obsidian.json.",
"VaultHealthCheck.dir_templates": "The Templater folder for this vault. Files under it are harvested into obs_tmplt only.",
"Colors.tab_id": "Which tab's colour scheme get_tab_clrs() is currently resolving.",
"Colors.name": "Name of the current colour scheme.",
"MyJSONFormatter.fmt_keys": "Which LogRecord fields the JSON log formatter emits, and under what names.",
"<module v_chk_wb_tabs.py>.tabs": "Module-level scratch reference used while building tab definitions.",
"ExcelExporter.colors": "The Colors instance the exporter renders fills and table styles from.",
"ExcelExporter.tab_def": "The tab definition currently being rendered, read from wb_def['wb_tabs'].",
})

_DEF_TABS = {
    "DefPros": "pros", "DefVals": "vals", "DefTags": "tags", "DefFile": "file",
    "DefCode": "code", "DefXyml": "xyml", "DefDups": "dups", "DefNest": "nest",
    "DefPlug": "plug", "DefTmpl": "tmpl", "DefSumm": "summ", "DefAr51": "ar51",
}
_DEF_ATTRS = {
    "tab_id":         "This subclass's 4-character tab id, '{t}'. It has to match the key used in NewWb.tab_common, the dispatch chain, WbDataDef.get_next_bat() and Colors.init_tab_clrs() -- a mismatch raises or silently drops the tab.",
    "tab_common":     "The shared display metadata for '{t}' -- name, titles, help text, data_src -- read from NewWb.tab_common rather than restated here.",
    "colors":         "The Colors instance the '{t}' tab draws its palette from.",
    "font_title_lst": "Font settings for the '{t}' tab's title. The typeface itself comes from the module-level TITLE_FONT; a tab subclass must never name a font.",
    "font_subs_lst":  "Font settings for the '{t}' tab's subtitles. Typeface comes from TITLE_FONT.",
    "font_body_lst":  "Font settings for the '{t}' tab's body cells.",
}
_STAGE_COPY = {
    "sys_id": "the application id", "sys_dir_bat": "the batch-file directory",
    "sys_dir_img": "the image directory", "sys_dir_wbs": "the workbook directory",
    "sys_pn_batch": "this run's batch file path", "sys_pn_wbs": "this run's workbook path",
    "sys_pn_cfg": "the CONFIG.yaml path", "sys_pn_wb_exec": "the spreadsheet executable path",
    "dir_vault": "the vault root", "vault_id": "the Obsidian vault id used to build obsidian:// links",
    "v_chk_date": "this run's timestamp",
}


# ---------------------------------------------------------------- patterns --
# (regex against "Owner.name", template) -- applied only when nothing authored
# and no source comment exists.
PATTERNS = [
    (r"^SetupScreen\.(\w+)_var$",
     "Tk variable bound to the {0} widget on the setup screen. The swap keeps these variable *objects* alive rather than rebinding them: a widget and a trace both hold the object, so replacing one orphans every widget built from it."),
    (r"^SetupScreen\.(\w+)_status$",
     "Label showing the validation result for the {0} field."),
    (r"^SetupScreen\.(\w+)_help$",
     "Help label beside the {0} field, rewritten by update_links_help()."),
    (r"^SetupScreen\.(\w+)_label$",
     "Static label for the {0} field."),
    (r"^NewTab\.f_uniq_(\w+)$",
     "Excel formula counting DISTINCT {0} values in the tab's table. Built on AGGREGATE/UNIQUE so the total respects whatever filter the reader has applied."),
    (r"^NewTab\.f_txt_(\w+)$",
     "Excel formula totalling text {0} entries via SUBTOTAL, so it follows the table filter."),
    (r"^NewTab\.f_num_(\w+)$",
     "Excel formula totalling numeric {0} entries via SUBTOTAL, so it follows the table filter."),
    (r"^NewTab\.f_(\w+)$",
     "Excel formula string used in the tab's totals block ({0})."),
    (r"^NewTab\.col_(\w+)$",
     "Column header text for {0} on this tab."),
    (r"^Colors\.clr_(\w+)$",
     "Palette entry: the {0} colour."),
    (r"^WbDataDef\.(pros|vals|tags|file|code|xyml|dups|tmpl|nest|plug|summ|ar51)$",
     "The wb_tabs entry for the '{0}' tab — one of the five places a tab must be registered."),
    (r"^PluginMan\.(author|authorUrl|description|helpUrl|id|minAppVersion|name|version)$",
     "Read verbatim from a plugin's manifest.json: {0}."),
    (r"^\w+\.sys_cfg$",
     "This stage's copy of the packed settings dict, re-read from the batch file rather than passed in memory."),
    (r"^\w+\.wb_def$",
     "This stage's copy of the full handoff structure, re-read from the batch file."),
    (r"^\w+\.wb_data$",
     "This stage's copy of the harvested vault data."),
    (r"^\w+\.ctot$",
     "This stage's copy of the Area51 counter list."),
    (r"^\w+\.xyml_descs$",
     "This stage's copy of the bad-frontmatter code descriptions."),
    (r"^\w+\.(wbd_obj|vhc_obj|tab_def_obj|o_app)$",
     "Handle to the {0} collaborator object."),
]


def resolve(key, rec):
    """-> (purpose, source). Order: authored, source comment, pattern, derived."""
    name, owner, kind = rec["name"], rec["owner"], rec["kind"]

    # The 13 DefXxxx tab subclasses each restate the same handful of attributes;
    # describe them per tab rather than 78 times over.
    if owner in _DEF_TABS and name in _DEF_ATTRS:
        return _DEF_ATTRS[name].format(t=_DEF_TABS[owner]), "pattern"
    if owner in ("ExcelExporter", "WbDataDef", "NewWb") and name in _STAGE_COPY:
        return (f"This stage's copy of {_STAGE_COPY[name]}, taken from the packed sys_cfg. "
                f"Stages re-read wb_def from the batch file rather than sharing objects in "
                f"memory, so each one holds its own copy.", "pattern")

    for probe in (f"{owner}.{name}", name):
        if probe in AUTHORED:
            return AUTHORED[probe], "authored"

    above, inline = rec.get("comment_above", ""), rec.get("comment_inline", "")
    if above and len(above) > 15:
        return above, "source comment"
    if inline and len(inline) > 15:
        return inline, "source comment"

    for pat, tmpl in PATTERNS:
        m = re.match(pat, f"{owner}.{name}")
        if m:
            return tmpl.format(*[g.replace("_", " ") for g in m.groups()]), "pattern"

    if inline:
        return inline, "source comment"

    where = owner if kind == "module constant" else f"{owner}"
    return f"{kind.capitalize()} on {where}. Not separately documented — read {rec['defs'][0]}.", "derived"

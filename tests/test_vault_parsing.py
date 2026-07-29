"""Tests for VaultHealthCheck, the markdown/YAML harvesting stage.

This is the riskiest code in the project -- it parses arbitrary user markdown --
and it is pure enough to test directly: give it a directory of .md files, look
at the obs_* dictionaries that come back.

Shapes produced (see upd_obs_props):
    obs_props  {property: {value: [filepath, ...]}}
    obs_atags  {tag: {tag: [filepath, ...]}}       -- key and value are the tag
    obs_xyaml  {code: {filepath: [filepath]}}      -- code is BadY/NoFm/MtFm/...
    obs_dupfn  {'dupfn': {filename: [filepath, ...]}}
    obs_codes  {filepath: {CODEBLOCK_SIG: [block text, ...]}}
    obs_files  {'filepath|F' or '|I': {property: [original_case, value, ...]}}
"""

import pytest


# ---------------------------------------------------------------------------
# Frontmatter properties
# ---------------------------------------------------------------------------

def test_frontmatter_properties_are_harvested(scan):
    result = scan({"note.md": """
        ---
        author: Jane
        status: draft
        ---

        Body text.
    """})

    assert "Jane" in result.obs_props["author"]
    assert "draft" in result.obs_props["status"]


def test_property_keys_are_lowercased(scan):
    """Obsidian treats properties case-insensitively, so v_chk groups on lowercase."""
    result = scan({"note.md": """
        ---
        Status: Draft
        ---
    """})

    assert "status" in result.obs_props
    assert "Status" not in result.obs_props
    # The value keeps its original casing; only the key is normalised.
    assert "Draft" in result.obs_props["status"]


def test_original_key_casing_is_preserved_in_obs_files(scan):
    """The Files tab is the only place that reports the casing actually used."""
    result = scan({"note.md": """
        ---
        Status: Draft
        ---
    """})

    frontmatter_entries = [v for k, v in result.obs_files.items() if k.endswith("|F")]
    assert frontmatter_entries, "expected a frontmatter entry"
    assert "Status" in frontmatter_entries[0]["status"]


def test_list_valued_property_yields_one_entry_per_item(scan):
    result = scan({"note.md": """
        ---
        aliases: [one, two]
        ---
    """})

    assert set(result.obs_props["aliases"]) == {"one", "two"}


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def test_frontmatter_tags_are_lowercased(scan):
    result = scan({"note.md": """
        ---
        tags:
          - Alpha
          - beta
        ---
    """})

    assert "alpha" in result.obs_atags
    assert "beta" in result.obs_atags
    assert "Alpha" not in result.obs_atags


def test_inline_body_tags_are_harvested(scan):
    result = scan({"note.md": "Some prose with an inline #bodytag in it.\n"})

    assert "bodytag" in result.obs_atags


def test_tags_inside_code_blocks_are_ignored(scan):
    result = scan({"note.md": """
        Real #keeper tag.

        ```python
        # not_a_tag
        x = "#fake"
        ```
    """})

    assert "keeper" in result.obs_atags
    assert "fake" not in result.obs_atags


# ---------------------------------------------------------------------------
# Inline (Dataview) properties
# ---------------------------------------------------------------------------

def test_bracketed_inline_property_is_harvested(scan):
    result = scan({"note.md": "A line with [mood:: happy] in it.\n"})

    assert "happy" in result.obs_props["mood"]


def test_line_start_inline_property_is_harvested(scan):
    """Regression: rgx_body_pros lacked re.MULTILINE, so its leading ^ anchored
    to the start of the whole body rather than to each line. Only bracketed
    inline fields were ever found."""
    result = scan({"note.md": """
        Intro paragraph.

        rating:: 5
    """})

    assert "5" in result.obs_props["rating"]


# ---------------------------------------------------------------------------
# Malformed / missing frontmatter
# ---------------------------------------------------------------------------

def test_unparseable_yaml_is_recorded_as_BadY(scan):
    result = scan({"bad.md": """
        ---
        author: [unclosed
        ---

        Body.
    """})

    assert "BadY" in result.obs_xyaml
    assert any("bad.md" in path for path in result.obs_xyaml["BadY"])


def test_file_without_frontmatter_is_recorded_as_NoFm(scan):
    result = scan({"plain.md": "Just prose, no frontmatter.\n"})

    assert "NoFm" in result.obs_xyaml
    assert any("plain.md" in path for path in result.obs_xyaml["NoFm"])


def test_valid_frontmatter_is_not_flagged(scan):
    result = scan({"note.md": """
        ---
        author: Jane
        ---

        Body.
    """})

    assert "BadY" not in result.obs_xyaml


# ---------------------------------------------------------------------------
# Duplicates, code blocks, skipping
# ---------------------------------------------------------------------------

def test_duplicate_filenames_across_folders_are_detected(scan):
    result = scan({
        "a/Meeting.md": "First.\n",
        "b/Meeting.md": "Second.\n",
        "c/Unique.md": "Third.\n",
    })

    duplicates = result.obs_dupfn["dupfn"]
    assert len(duplicates["Meeting.md"]) == 2
    assert len(duplicates["Unique.md"]) == 1


def test_code_blocks_are_captured_with_uppercased_signature(scan):
    result = scan({"note.md": """
        Text.

        ```dataview
        TABLE file.name
        ```
    """})

    signatures = {sig for block in result.obs_codes.values() for sig in block}
    assert "DATAVIEW" in signatures


def test_properties_inside_code_blocks_are_not_harvested(scan):
    result = scan({"note.md": """
        ```yaml
        ghost:: value
        ```
    """})

    assert "ghost" not in result.obs_props


def test_skipped_directories_are_not_scanned(scan):
    result = scan(
        {
            "keep/Kept.md": "---\nauthor: Jane\n---\n",
            "Archive/Skipped.md": "---\nauthor: Ghost\n---\n",
        },
        skip_rel_str="Archive",
    )

    assert "Jane" in result.obs_props["author"]
    assert "Ghost" not in result.obs_props["author"]


# ---------------------------------------------------------------------------
# Regressions from Phase 1
# ---------------------------------------------------------------------------

def test_vault_without_templater_plugin_does_not_crash(scan):
    """Regression: get_templates_dir() returns None when Templater is absent,
    and that was passed straight to Path(), raising TypeError. Every vault
    without the plugin failed."""
    result = scan({"note.md": "---\nauthor: Jane\n---\n"}, dir_templates=None)

    assert "Jane" in result.obs_props["author"]


def test_nested_list_property_does_not_crash(scan):
    """Regression: a YAML value that is itself a list reached upd_obs_props as a
    dict key and raised 'unhashable type: list'."""
    result = scan({"note.md": """
        ---
        related:
          - [alpha, beta]
        ---
    """})

    assert "alpha, beta" in result.obs_props["related"]


def test_unquoted_wikilink_value_is_rendered_as_a_link(scan):
    """An unquoted "- [[Some Note]]" parses as [[['Some Note']]] and should come
    back out as the link text, not as a Python repr."""
    result = scan({"note.md": """
        ---
        related:
          - [[Some Note]]
        ---
    """})

    assert "[[Some Note]]" in result.obs_props["related"]


def test_flow_list_does_not_lose_elements(scan):
    """Regression: the unquoted-wikilink branch in unpack_yaml also fired on an
    ordinary flow sequence and rebuilt the value from value[0][0] alone, so
    "- [alpha, beta]" was silently recorded as "[[alpha]]" and beta vanished."""
    result = scan({"note.md": """
        ---
        related:
          - [alpha, beta]
        ---
    """})

    recorded = " ".join(result.obs_props["related"])
    assert "alpha" in recorded
    assert "beta" in recorded


def test_numeric_tags_value_does_not_crash(scan):
    """Regression: upd_val() called v.lower() before normalising, so a
    non-string tags value raised AttributeError."""
    result = scan({"note.md": """
        ---
        tags: 2024
        ---
    """})

    assert result.obs_atags  # harvested something rather than raising


# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------

def test_ctot_counts_markdown_files(scan):
    result = scan({
        "one.md": "A.\n",
        "two.md": "B.\n",
        "three.md": "C.\n",
    })

    assert result.ctot[0] == 3   # markdown files seen
    assert result.ctot[3] == 3   # files processed

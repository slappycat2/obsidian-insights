"""The --json contract, in process: what a program driving ovi can rely on.

The Obsidian plugin spawns ``ovi --json`` and parses stdout line by line, so
stdout must hold nothing but JSON objects, one per line, and every way a run
can end must produce exactly one ``done`` or ``error`` event. These tests
stub SysConfig and the pipeline so each ending can be forced; the
end-to-end runs are in test_headless_cli.py.

``result.stdout`` is asserted on, not ``result.output`` -- Click 8.2's
CliRunner mixes stderr into ``output``, and separating the two streams is
the whole point.
"""

import json
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from ovi import CTOT_SLOTS, __version__, ovi
from ovi.ovi import PHASES
from ovi.ovi_setup import ConfigIncompleteError
from ovi.ovi_xl import WorkbookLockedError


def events(result):
    lines = result.stdout.splitlines()
    assert lines, "nothing on stdout"
    return [json.loads(line) for line in lines]


@pytest.fixture
def fake_config(monkeypatch):
    """SysConfig replaced by a recorder of what the CLI passed it."""
    calls = []

    def build(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(dir_vault="/vaults/V", vault_name="V - (/vaults)")

    monkeypatch.setattr("ovi.ovi.SysConfig", build)
    return calls


@pytest.fixture
def fake_exporter():
    return SimpleNamespace(sys_pn_wbs="/out/ovi_V_0003.xlsx", sys_pn_batch="/out/ovi_V_0003.yaml",
                           sys_pn_wb_exec="", sys_cfg={"ctot": [7] * CTOT_SLOTS})


def test_a_successful_run_is_progress_then_done(monkeypatch, fake_config, fake_exporter):
    def pipeline(_cfg, progress, interactive):
        assert not interactive, "--json implies --headless"
        for text, percent in PHASES:
            progress(text, percent)
        return fake_exporter

    monkeypatch.setattr(ovi, "run_pipeline", pipeline)
    opened = []
    monkeypatch.setattr(ovi, "open_workbook", lambda *a, **k: opened.append(k) or True)

    result = CliRunner().invoke(ovi.cli, ["--json", "--do-not-open"])

    assert result.exit_code == 0, result.output
    got = events(result)
    assert [e["event"] for e in got] == ["progress"] * len(PHASES) + ["done"]
    assert [e["percent"] for e in got[:-1]] == [p for _, p in PHASES]
    done = got[-1]
    assert done == {
        "event": "done", "ok": True,
        "workbook": "/out/ovi_V_0003.xlsx", "batch": "/out/ovi_V_0003.yaml",
        "vault": "/vaults/V", "vault_name": "V - (/vaults)",
        "version": __version__, "ctot": [7] * CTOT_SLOTS,
        "opened": None,
    }
    assert not opened, "--do-not-open still launched the spreadsheet"
    assert "Workbook written to" not in result.stdout


def test_opening_the_workbook_is_reported_in_the_done_event(monkeypatch, fake_config, fake_exporter):
    monkeypatch.setattr(ovi, "run_pipeline", lambda *a, **k: fake_exporter)
    seen = []
    monkeypatch.setattr(ovi, "open_workbook", lambda _e, quiet=False: seen.append(quiet) or False)

    result = CliRunner().invoke(ovi.cli, ["--json"])

    assert events(result)[-1]["opened"] is False
    assert seen == [True], "a --json run must not let open_workbook() write to stdout"


def test_a_locked_workbook_is_one_error_event(monkeypatch, fake_config):
    def locked(*_a, **_k):
        raise WorkbookLockedError("Unable to save workbook X: it is open in another program.")

    monkeypatch.setattr(ovi, "run_pipeline", locked)

    result = CliRunner().invoke(ovi.cli, ["--json", "-x"])

    assert result.exit_code == 1
    got = events(result)
    assert len(got) == 1
    assert got[0]["event"] == "error"
    assert got[0]["ok"] is False
    assert got[0]["kind"] == "WorkbookLocked"
    assert "open in another program" in got[0]["message"]


def test_a_config_error_is_one_error_event(monkeypatch):
    def refuse(**_kwargs):
        raise ConfigIncompleteError("Configuration is missing.")

    monkeypatch.setattr("ovi.ovi.SysConfig", refuse)

    result = CliRunner().invoke(ovi.cli, ["--json", "-x"])

    assert result.exit_code == 1
    got = events(result)
    assert len(got) == 1
    assert got[0]["kind"] == "ConfigIncomplete"


def test_an_unexpected_exception_is_still_one_line(monkeypatch, fake_config):
    """A program reading stdout needs a parseable line, not a traceback. The
    traceback goes to stderr and the log."""
    def explode(*_a, **_k):
        raise PermissionError("no read access to Secret.md")

    monkeypatch.setattr(ovi, "run_pipeline", explode)

    result = CliRunner().invoke(ovi.cli, ["--json", "-x"])

    assert result.exit_code == 1
    got = events(result)
    assert len(got) == 1
    assert got[0]["kind"] == "Unexpected"
    assert "Secret.md" in got[0]["message"]
    assert "Traceback" not in result.stdout


def test_the_human_output_is_unchanged_without_json(monkeypatch, fake_config, fake_exporter):
    monkeypatch.setattr(ovi, "run_pipeline", lambda *a, **k: fake_exporter)

    result = CliRunner().invoke(ovi.cli, ["--headless", "-x"])

    assert result.exit_code == 0
    assert result.stdout == "Workbook written to /out/ovi_V_0003.xlsx\n"


def test_an_unexpected_exception_still_propagates_without_json(monkeypatch, fake_config):
    def explode(*_a, **_k):
        raise PermissionError("no read access")

    monkeypatch.setattr(ovi, "run_pipeline", explode)

    result = CliRunner().invoke(ovi.cli, ["--headless", "-x"])

    assert isinstance(result.exception, PermissionError)


def test_override_flags_reach_sysconfig(monkeypatch, fake_config, fake_exporter):
    monkeypatch.setattr(ovi, "run_pipeline", lambda *a, **k: fake_exporter)

    result = CliRunner().invoke(ovi.cli, [
        "--json", "-x", "--skip-folders", "Archive,Templates",
        "--max-value-links", "3", "--max-tag-links", "0", "--spreadsheet-app", "",
    ])

    assert result.exit_code == 0, result.output
    assert fake_config[0]["setting_overrides"] == {
        "skip_rel_str": "Archive,Templates", "link_lim_vals": 3, "link_lim_tags": 0,
        "sys_pn_wb_exec": "",
    }
    assert fake_config[0]["interactive"] is False


def test_absent_flags_leave_the_configuration_alone(monkeypatch, fake_config, fake_exporter):
    monkeypatch.setattr(ovi, "run_pipeline", lambda *a, **k: fake_exporter)

    CliRunner().invoke(ovi.cli, ["--headless", "-x"])

    assert fake_config[0]["setting_overrides"] == {}


def test_negative_link_limits_are_usage_errors(fake_config):
    result = CliRunner().invoke(ovi.cli, ["--json", "-x", "--max-value-links", "-1"])

    assert result.exit_code == 2
    assert not fake_config, "SysConfig was built despite a bad flag"


def test_json_with_init_is_a_usage_error(monkeypatch):
    reset = []
    monkeypatch.setattr(ovi, "reset_generated_files", lambda **k: reset.append(k))

    result = CliRunner().invoke(ovi.cli, ["--json", "--init", "--yes"])

    assert result.exit_code == 2
    assert not reset

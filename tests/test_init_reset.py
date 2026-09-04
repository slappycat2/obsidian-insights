"""--init tolerates a workbook it cannot delete.

A workbook open in Excel cannot be unlinked. That is an allowed outcome, not a
failure -- but the file that survives keeps its sequence number, so the reset
has to say so and the numbering has to respect it (see
tests/test_output_naming.py for the numbering half).
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from ovi import ovi
from ovi import ovi_paths as paths


@pytest.fixture
def generated(tmp_path, monkeypatch):
    """Redirect the three reset targets at a per-test directory.

    The suite's OVI_DATA_DIR is shared for the whole session, and --init
    deletes everything it finds -- including files other tests are relying on.
    reset_generated_files() reads these through the module at call time, so
    patching the module attributes is enough.
    """
    batch_dir = tmp_path / "batch_files"
    wb_dir = tmp_path / "workbooks"
    batch_dir.mkdir()
    wb_dir.mkdir()

    monkeypatch.setattr(paths, "CONFIG_FILE", tmp_path / "CONFIG.yaml")
    monkeypatch.setattr(paths, "BATCH_DIR", batch_dir)
    monkeypatch.setattr(paths, "WORKBOOK_DIR", wb_dir)

    paths.CONFIG_FILE.write_text("sys_id: ovi\n", encoding="utf-8")

    return paths.CONFIG_FILE, batch_dir, wb_dir


def _refuse_to_unlink(monkeypatch, suffix):
    """Make Path.unlink raise PermissionError for one suffix, as Excel does."""
    real_unlink = Path.unlink

    def unlink(self, missing_ok=False):
        if self.suffix == suffix:
            raise PermissionError(
                32, "The process cannot access the file because it is being "
                    "used by another process")
        return real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", unlink)


def test_init_keeps_files_it_cannot_delete(generated, monkeypatch):
    """The reported bug's first half: a locked workbook must not abort the reset
    or be reported as deleted."""
    config, batch_dir, wb_dir = generated
    batch = batch_dir / "ovi_work_0000.yaml"
    workbook = wb_dir / "ovi_work_0000.xlsx"
    batch.write_text("", encoding="utf-8")
    workbook.write_text("", encoding="utf-8")

    _refuse_to_unlink(monkeypatch, ".xlsx")

    result = CliRunner().invoke(ovi.cli, ["--init", "--yes"])

    assert result.exit_code == 0
    assert "Traceback" not in result.output
    assert not batch.exists()
    assert not config.exists()
    assert workbook.exists(), "a locked workbook must survive the reset"

    assert "Could not delete" in result.output
    assert "2 file(s) deleted, 1 in use and kept" in result.output
    assert "keep their sequence numbers" in result.output


def test_init_reports_a_plain_count_when_nothing_is_locked(generated):
    config, batch_dir, wb_dir = generated
    (batch_dir / "ovi_work_0000.yaml").write_text("", encoding="utf-8")
    (wb_dir / "ovi_work_0000.xlsx").write_text("", encoding="utf-8")

    result = CliRunner().invoke(ovi.cli, ["--init", "--yes"])

    assert result.exit_code == 0
    assert "Reset complete -- 3 file(s) deleted." in result.output
    assert "in use and kept" not in result.output
    assert "keep their sequence numbers" not in result.output


def test_init_ignores_excel_owner_files(generated):
    """'~$name.xlsx' belongs to Excel, so it is neither listed nor deleted."""
    config, batch_dir, wb_dir = generated
    owner = wb_dir / "~$ovi_work_0000.xlsx"
    owner.write_text("", encoding="utf-8")

    result = CliRunner().invoke(ovi.cli, ["--init", "--yes"])

    assert result.exit_code == 0
    assert "~$" not in result.output
    assert owner.exists()
    assert "Reset complete -- 1 file(s) deleted." in result.output


def test_init_declined_deletes_nothing(generated):
    config, batch_dir, wb_dir = generated
    batch = batch_dir / "ovi_work_0000.yaml"
    batch.write_text("", encoding="utf-8")

    result = CliRunner().invoke(ovi.cli, ["--init"], input="n\n")

    assert result.exit_code == 0
    assert "Aborted" in result.output
    assert batch.exists()
    assert config.exists()

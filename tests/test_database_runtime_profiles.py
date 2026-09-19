"""Runtime selection must not accidentally point tests at another database."""

import pytest

from scripts import setup_test_timescale, test_postgres


def test_profile_paths_ports_owners_are_distinct(tmp_path, monkeypatch):
    monkeypatch.setattr(test_postgres, "ROOT", tmp_path)
    native = test_postgres.runtime_for("native-pg16")
    timescale = test_postgres.runtime_for("timescale-pg16")
    assert native.port == 55432
    assert timescale.port == 55433
    assert native.owner != timescale.owner
    assert native.data != timescale.data
    assert native.socket != timescale.socket
    assert test_postgres.DEFAULT_PROFILE == "timescale-pg16"
    assert test_postgres.TIMESCALE_VERSION == setup_test_timescale.TIMESCALE_VERSION
    with pytest.raises(ValueError, match="Unknown test database profile"):
        test_postgres.runtime_for("production")


def test_existing_data_without_ownership_record_is_never_adopted(tmp_path, monkeypatch):
    monkeypatch.setattr(test_postgres, "ROOT", tmp_path)
    runtime = test_postgres.runtime_for("timescale-pg16")
    runtime.data.mkdir(parents=True)
    (runtime.data / "PG_VERSION").write_text("16\n")
    with pytest.raises(RuntimeError, match="without this helper's ownership record"):
        test_postgres.guard_paths(runtime)


def test_symlinked_runtime_is_never_controlled(tmp_path, monkeypatch):
    monkeypatch.setattr(test_postgres, "ROOT", tmp_path)
    runtime = test_postgres.runtime_for("timescale-pg16")
    (tmp_path / "var").mkdir()
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    runtime.runtime.symlink_to(foreign, target_is_directory=True)
    with pytest.raises(RuntimeError, match="Refusing symlink"):
        test_postgres.guard_paths(runtime)

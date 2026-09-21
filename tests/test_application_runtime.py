"""Application provisioning must never adopt or control disposable test storage."""

import json

import pytest

from scripts.app_postgres import ApplicationRuntime, configuration, guard


def test_application_identity_is_separate_from_both_test_profiles(tmp_path):
    from scripts import test_postgres

    app = ApplicationRuntime(tmp_path, 5433, "equity", "equity")
    for profile in test_postgres.PROFILES:
        test = test_postgres.runtime_for(profile)
        assert app.port != test.port
        assert app.data != test.data
        assert app.unix_socket != test.socket
        assert app.identity["owner"] != test.owner


def test_unowned_application_directory_is_never_adopted(tmp_path):
    app = ApplicationRuntime(tmp_path, 5433, "equity", "equity")
    app.data.mkdir(parents=True)
    (app.data / "PG_VERSION").write_text("16\n")
    with pytest.raises(RuntimeError, match="ownership record"):
        guard(app)


def test_symlink_and_changed_runtime_identity_are_rejected(tmp_path):
    app = ApplicationRuntime(tmp_path, 5433, "equity", "equity")
    app.directory.mkdir(parents=True)
    app.record.write_text(json.dumps({**app.identity, "port": 55433}))
    with pytest.raises(RuntimeError, match="mismatch"):
        guard(app)
    app.record.unlink()
    app.data.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(RuntimeError, match="symlink"):
        guard(app)


@pytest.mark.parametrize(
    "uri",
    [
        "postgresql://equity:secret@127.0.0.1:55433/equity",
        "postgresql://equity:secret@127.0.0.1:5433/equity_test_1",
        "postgresql://equity:secret@example.com:5433/equity",
        "postgresql://postgres:secret@127.0.0.1:5433/equity",
        "postgresql://equity:secret@127.0.0.1:5433/equity?host=example.com",
    ],
)
def test_config_cannot_redirect_control_to_tests_or_remote_hosts(tmp_path, monkeypatch, uri):
    monkeypatch.setenv("DATABASE_URL", uri)
    with pytest.raises(ValueError):
        configuration(tmp_path)


@pytest.mark.parametrize("path", ["server.log", "installation-provenance.json"])
def test_postgres_refuses_symlinked_output_files(tmp_path, path):
    app = ApplicationRuntime(tmp_path, 5433, "equity", "equity")
    app.directory.mkdir(parents=True)
    app.record.write_text(json.dumps(app.identity))
    (app.directory / path).symlink_to(tmp_path / "unrelated")
    with pytest.raises(RuntimeError, match="symlink"):
        guard(app)


@pytest.mark.parametrize(
    "uri",
    [
        "redis://127.0.0.1:16380/0",
        "redis://example.com:6380/0",
        "redis://127.0.0.1:6380/1",
        "redis://127.0.0.1:6380/0?host=example.com",
        "redis://user:secret@127.0.0.1:6380/0",
    ],
)
def test_application_redis_rejects_other_instances(tmp_path, monkeypatch, uri):
    from scripts.app_redis import configuration as redis_configuration

    monkeypatch.setenv("REDIS_URL", uri)
    with pytest.raises(ValueError):
        redis_configuration(tmp_path)


def test_application_redis_ownership_and_persistent_files(tmp_path):
    from scripts.app_redis import ApplicationRedis
    from scripts.app_redis import guard as redis_guard
    from scripts.test_redis import OWNER, PORT, RUNTIME

    app = ApplicationRedis(tmp_path)
    assert app.port != PORT and app.directory != RUNTIME and app.identity["owner"] != OWNER
    app.directory.mkdir(parents=True)
    app.config.write_text("unexpected configuration")
    with pytest.raises(RuntimeError, match="ownership record"):
        redis_guard(app)
    app.record.write_text(json.dumps(app.identity))
    redis_guard(app)
    (app.directory / "appendonlydir").mkdir()
    (app.directory / "appendonlydir/foreign.aof").symlink_to(tmp_path / "foreign")
    with pytest.raises(RuntimeError, match="symlink"):
        redis_guard(app)


def test_application_redis_requires_durable_loopback_configuration(tmp_path):
    from scripts.app_redis import ApplicationRedis, verify

    app = ApplicationRedis(tmp_path)
    app.directory.mkdir(parents=True)
    app.record.write_text(json.dumps(app.identity))

    class FakeRedis:
        bind = "127.0.0.1"
        aof = "yes"
        fsync = "always"
        file = str(app.config)

        def info(self, section):
            if section == "server":
                return {"config_file": self.file, "tcp_port": 6380, "redis_version": "test"}
            return {"aof_enabled": 1, "aof_last_write_status": "ok"}

        def config_get(self, key):
            return {
                key: {
                    "bind": self.bind,
                    "protected-mode": "yes",
                    "appendonly": self.aof,
                    "appendfsync": self.fsync,
                    "dir": str(app.directory),
                    "maxmemory-policy": "noeviction",
                }[key]
            }

    client = FakeRedis()
    assert verify(app, client)["aof"] is True
    for field, value in [
        ("bind", "0.0.0.0"),
        ("aof", "no"),
        ("fsync", "everysec"),
        ("file", "/other/redis.conf"),
    ]:
        old = getattr(client, field)
        setattr(client, field, value)
        with pytest.raises(RuntimeError, match="configuration"):
            verify(app, client)
        setattr(client, field, old)

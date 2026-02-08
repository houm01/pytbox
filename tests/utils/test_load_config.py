#!/usr/bin/env python3

import json
from pathlib import Path

import pytbox.utils.load_config as load_config_module
from pytbox.utils.load_config import load_config_by_file


def test_load_config_jsonfile_and_env_fallback(tmp_path: Path, monkeypatch) -> None:
    """`load_config_by_file` should resolve JSON values then env fallback."""
    json_path = tmp_path / "config_values.json"
    json_path.write_text(json.dumps({"db": {"password": "pwd-from-json"}}), encoding="utf-8")

    toml_path = tmp_path / "config.toml"
    toml_path.write_text(
        '\n'.join(
            [
                'db_password = "jsonfile,db.password"',
                'env_only = "jsonfile,ENV_ONLY_KEY"',
                'missing = "jsonfile,not.exists"',
                'plain = "plain-text"',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("ENV_ONLY_KEY", "env-fallback")
    config = load_config_by_file(path=str(toml_path), jsonfile=str(json_path))

    assert config["db_password"] == "pwd-from-json"
    assert config["env_only"] == "env-fallback"
    assert config["missing"] == "jsonfile,not.exists"
    assert config["plain"] == "plain-text"


def test_load_config_jsonfile_is_loaded_once(tmp_path: Path, monkeypatch) -> None:
    """`jsonfile` data should be loaded once per config parse."""
    json_path = tmp_path / "config_values.json"
    json_path.write_text(
        json.dumps({"service": {"token": "abc"}, "db": {"password": "def"}}),
        encoding="utf-8",
    )

    toml_path = tmp_path / "config.toml"
    toml_path.write_text(
        '\n'.join(
            [
                'token = "jsonfile,service.token"',
                'password = "jsonfile,db.password"',
            ]
        ),
        encoding="utf-8",
    )

    original_json_load = load_config_module.json.load
    load_calls = {"count": 0}

    def _spy_json_load(*args, **kwargs):
        load_calls["count"] += 1
        return original_json_load(*args, **kwargs)

    monkeypatch.setattr(load_config_module.json, "load", _spy_json_load)
    config = load_config_by_file(path=str(toml_path), jsonfile=str(json_path))

    assert config["token"] == "abc"
    assert config["password"] == "def"
    assert load_calls["count"] == 1

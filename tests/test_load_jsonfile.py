#!/usr/bin/env python3

import json
from pathlib import Path

from pytbox.utils.load_config import load_config_by_file


def test_load_jsonfile_placeholder(tmp_path: Path) -> None:
    """`load_config_by_file` should resolve `jsonfile,` placeholders."""
    json_path = tmp_path / "values.json"
    json_path.write_text(json.dumps({"json_test": "value-from-json"}), encoding="utf-8")

    toml_path = tmp_path / "config.toml"
    toml_path.write_text('json_test = "jsonfile,json_test"\n', encoding="utf-8")

    config = load_config_by_file(path=str(toml_path), jsonfile=str(json_path))
    assert config["json_test"] == "value-from-json"

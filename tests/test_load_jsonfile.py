#!/usr/bin/env python3


from pytbox.utils.load_config import load_config_by_file


config = load_config_by_file(
    path='/workspaces/pytbox/tests/alert/config_dev.toml',
    # oc_vault_id="hcls5uxuq5dmxorw6rfewefdsa"
    jsonfile="test_load_config.json"
)


print(config['json_test'])
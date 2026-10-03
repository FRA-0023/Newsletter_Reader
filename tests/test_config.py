import pytest
from pathlib import Path
from config.settings import load_yaml_config, PROJECT_ROOT


def test_load_yaml_config():
    config = load_yaml_config()
    assert config.version == "1.0"
    assert len(config.domains) == 5

    domain_ids = [d.id for d in config.domains]
    assert "world_population" in domain_ids
    assert "crypto" in domain_ids
    assert "mozi_minute" in domain_ids
    assert "tristan_burns" in domain_ids
    assert "david_cohen" in domain_ids


def test_templates_exist():
    config = load_yaml_config()
    for domain in config.domains:
        template_file = PROJECT_ROOT / domain.ai.prompt_template
        assert template_file.exists(), f"Missing template file: {template_file}"
        content = template_file.read_text(encoding="utf-8")
        assert len(content) > 50, f"Template {domain.ai.prompt_template} appears too short"

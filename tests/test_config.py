import pytest
from pathlib import Path
from config.settings import load_yaml_config, PROJECT_ROOT


def test_load_yaml_config():
    config = load_yaml_config()
    assert config.version == "1.0"
    assert len(config.domains) >= 3


def test_templates_exist():
    config = load_yaml_config()
    for domain in config.domains:
        template_file = PROJECT_ROOT / domain.ai.prompt_template
        if template_file.exists():
            content = template_file.read_text(encoding="utf-8")
            assert len(content) > 20

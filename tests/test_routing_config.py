from pathlib import Path

import pytest
from pydantic import ValidationError

from app.routing_config import load_routing_config

PROJECT_ROOT = Path(__file__).parents[1]


def test_project_config_contains_required_routes() -> None:
    config = load_routing_config(PROJECT_ROOT / "config" / "departments.yaml")

    routes = {department.id: str(department.email) for department in config.departments}
    assert routes == {
        "human-resources": "human-resources@example.com",
        "help-desk": "help-desk@example.com",
        "it": "it@example.com",
        "kadry": "kadry@example.com",
        "other": "other@example.com",
    }
    assert config.fallback_department == "other"


@pytest.mark.parametrize(
    ("yaml_content", "error_message"),
    [
        (
            """
departments:
  - id: it
    email: it@example.com
    description: Infrastructure issues
    examples: [VPN failure]
  - id: it
    email: help-desk@example.com
    description: End-user support
    examples: [Password reset]
fallback_department: it
""",
            "department ids must be unique",
        ),
        (
            """
departments:
  - id: it
    email: shared@example.com
    description: Infrastructure issues
    examples: [VPN failure]
  - id: help-desk
    email: shared@example.com
    description: End-user support
    examples: [Password reset]
fallback_department: it
""",
            "department email addresses must be unique",
        ),
        (
            """
departments:
  - id: it
    email: it@example.com
    description: Infrastructure issues
    examples: [VPN failure]
fallback_department: other
""",
            "fallback_department must reference an existing department",
        ),
    ],
)
def test_invalid_routing_rules_are_rejected(
    tmp_path: Path, yaml_content: str, error_message: str
) -> None:
    config_path = tmp_path / "departments.yaml"
    config_path.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(ValidationError, match=error_message):
        load_routing_config(config_path)


def test_invalid_yaml_has_a_clear_error(tmp_path: Path) -> None:
    config_path = tmp_path / "departments.yaml"
    config_path.write_text("departments: [", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid YAML in routing config"):
        load_routing_config(config_path)

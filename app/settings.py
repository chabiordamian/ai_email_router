import os
from dataclasses import dataclass
from pathlib import Path


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    departments_config_path: Path
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: int
    smtp_host: str
    smtp_port: int
    smtp_timeout_seconds: int
    email_from: str

    @classmethod
    def from_environment(cls) -> Settings:
        return cls(
            departments_config_path=Path(
                os.getenv("DEPARTMENTS_CONFIG_PATH", "config/departments.yaml")
            ),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:1.7b"),
            ollama_timeout_seconds=_positive_int("OLLAMA_TIMEOUT_SECONDS", 120),
            smtp_host=os.getenv("SMTP_HOST", "mailpit"),
            smtp_port=_positive_int("SMTP_PORT", 1025),
            smtp_timeout_seconds=_positive_int("SMTP_TIMEOUT_SECONDS", 10),
            email_from=os.getenv("EMAIL_FROM", "ai-router@example.com"),
        )

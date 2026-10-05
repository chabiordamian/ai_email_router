import pytest

from app.settings import Settings


def test_rejects_invalid_email_from(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMAIL_FROM", "not-an-email")

    with pytest.raises(ValueError, match="EMAIL_FROM must be a valid email address"):
        Settings.from_environment()

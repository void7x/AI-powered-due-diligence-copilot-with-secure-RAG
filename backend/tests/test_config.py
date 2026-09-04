from pydantic import ValidationError
import pytest

from app.core.config import Settings


def test_security_defaults_are_safe():
    settings = Settings()
    assert settings.debug is False
    assert settings.create_demo_user is False
    assert settings.secret_key
    assert settings.secret_key != "dev-insecure-secret-change-me"


def test_production_requires_explicit_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(environment="production", secret_key=None)


def test_demo_user_requires_password_when_enabled():
    with pytest.raises(ValidationError, match="DEMO_PASSWORD"):
        Settings(create_demo_user=True, demo_password="")

import pytest

from app.config import Settings, print_config, validate_config


def _settings(**overrides) -> Settings:
    values = {
        "qloo_api_key": "test-qloo-key",
        "qloo_api_base_url": "https://hackathon.api.qloo.com",
        "qloo_timeout_seconds": 15.0,
        "qloo_max_results": 20,
        "minimax_api_key": "test-llm-key",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_get_qloo_config_returns_bounded_server_configuration():
    config = _settings(qloo_timeout_seconds=7.5, qloo_max_results=12).get_qloo_config()

    assert config == {
        "api_key": "test-qloo-key",
        "base_url": "https://hackathon.api.qloo.com",
        "timeout_seconds": 7.5,
        "max_results": 12,
    }


def test_validate_config_requires_qloo_key():
    with pytest.raises(ValueError, match="QLOO_API_KEY"):
        validate_config(_settings(qloo_api_key=""))


def test_print_config_reports_qloo_status_without_secret(capsys):
    print_config(_settings())

    output = capsys.readouterr().out
    assert "Qloo API Key: 已配置" in output
    assert "test-qloo-key" not in output

import pytest

from app.config import Settings, print_config, validate_config


def _settings(**overrides) -> Settings:
    values = {
        "qloo_api_key": "test-qloo-key",
        "qloo_api_base_url": "https://hackathon.api.qloo.com",
        "qloo_timeout_seconds": 15.0,
        "qloo_max_results": 20,
        "llm_api_key": "test-llm-key",
        "llm_base_url": "https://llm.example/v1",
        "llm_model": "test-model",
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


def test_agent_loop_defaults_are_bounded():
    candidate = _settings()
    assert candidate.agent_max_decisions == 8
    assert candidate.qloo_nearby_radius_meters == 10_000


def test_validate_config_requires_qloo_key():
    with pytest.raises(ValueError, match="QLOO_API_KEY"):
        validate_config(_settings(qloo_api_key=""))


def test_validate_config_requires_llm_key():
    with pytest.raises(ValueError, match="LLM API Key"):
        validate_config(_settings(llm_api_key=""))


def test_get_llm_config_returns_provider_neutral_triplet():
    config = _settings().get_llm_config()

    assert config == {
        "api_key": "test-llm-key",
        "base_url": "https://llm.example/v1",
        "model": "test-model",
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"qloo_api_base_url": "not-a-url"},
        {"llm_base_url": "file:///tmp/model"},
    ],
)
def test_validate_config_rejects_non_http_service_endpoints(overrides):
    with pytest.raises(ValueError, match="Base URL"):
        validate_config(_settings(**overrides))


def test_legacy_provider_specific_settings_do_not_configure_llm():
    candidate = Settings(
        _env_file=None,
        qloo_api_key="test-qloo-key",
        minimax_api_key="legacy-minimax-key",
        openai_api_key="legacy-openai-key",
    )

    with pytest.raises(ValueError, match="LLM API Key"):
        validate_config(candidate)


def test_print_config_reports_qloo_status_without_secret(capsys):
    print_config(_settings())

    output = capsys.readouterr().out
    assert "Qloo API Key: 已配置" in output
    assert "test-qloo-key" not in output


def test_print_config_redacts_credentials_embedded_in_endpoint_urls(capsys):
    print_config(
        _settings(
            qloo_api_base_url="https://user:qloo-url-secret@example.test/api?key=hidden",
            llm_base_url="https://llm-url-secret@example-llm.test/v1?token=hidden",
        )
    )

    output = capsys.readouterr().out
    assert "qloo-url-secret" not in output
    assert "llm-url-secret" not in output
    assert "hidden" not in output
    assert "https://example.test" in output
    assert "https://example-llm.test" in output

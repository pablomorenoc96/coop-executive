import pytest
from coopexecutive.config import Settings
from coopexecutive.providers.client import AIClient


def test_default_openrouter_routing(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("PROVIDER", "auto")
    monkeypatch.setenv("LOCAL_MODELS_ENABLED", "false")
    
    settings = Settings()
    client = AIClient()
    client.settings = settings
    
    flavor, endpoint, headers = client.resolve_provider("minimax/minimax-m3:free")
    assert flavor == "openai_compat"
    assert "openrouter.ai/api/v1/chat/completions" in endpoint
    assert headers["Authorization"] == "Bearer sk-or-test"


def test_openai_routing(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    monkeypatch.setenv("PROVIDER", "auto")
    monkeypatch.setenv("LOCAL_MODELS_ENABLED", "false")
    
    settings = Settings()
    client = AIClient()
    client.settings = settings
    
    flavor, endpoint, headers = client.resolve_provider("gpt-4o")
    assert flavor == "openai_compat"
    assert "api.openai.com/v1/chat/completions" in endpoint
    assert headers["Authorization"] == "Bearer sk-openai-test"


def test_anthropic_routing(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("PROVIDER", "auto")
    monkeypatch.setenv("LOCAL_MODELS_ENABLED", "false")
    
    settings = Settings()
    client = AIClient()
    client.settings = settings
    
    flavor, endpoint, headers = client.resolve_provider("claude-3-5-sonnet-20241022")
    assert flavor == "anthropic"
    assert "api.anthropic.com/v1/messages" in endpoint
    assert headers["x-api-key"] == "sk-ant-test"
    assert headers["anthropic-version"] == "2023-06-01"


def test_gemini_routing(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyTest")
    monkeypatch.setenv("PROVIDER", "auto")
    monkeypatch.setenv("LOCAL_MODELS_ENABLED", "false")
    
    settings = Settings()
    client = AIClient()
    client.settings = settings
    
    flavor, endpoint, headers = client.resolve_provider("gemini-2.0-flash")
    assert flavor == "openai_compat"
    assert "generativelanguage.googleapis.com/v1beta/openai/chat/completions" in endpoint
    assert headers["Authorization"] == "Bearer AIzaSyTest"


def test_local_ollama_routing(monkeypatch):
    monkeypatch.setenv("LOCAL_MODELS_ENABLED", "true")
    monkeypatch.setenv("LOCAL_BASE_URL", "http://localhost:11434/v1")
    
    settings = Settings()
    client = AIClient()
    client.settings = settings
    
    flavor, endpoint, headers = client.resolve_provider("llama3.1:8b")
    assert flavor == "openai_compat"
    assert endpoint == "http://localhost:11434/v1/chat/completions"
    assert "Authorization" not in headers


def test_custom_endpoint_routing(monkeypatch):
    monkeypatch.setenv("PROVIDER", "custom")
    monkeypatch.setenv("CUSTOM_BASE_URL", "https://my-internal-gateway.org/v1")
    monkeypatch.setenv("CUSTOM_API_KEY", "custom-secret")
    monkeypatch.setenv("LOCAL_MODELS_ENABLED", "false")
    
    settings = Settings()
    client = AIClient()
    client.settings = settings
    
    flavor, endpoint, headers = client.resolve_provider("custom-model")
    assert flavor == "openai_compat"
    assert endpoint == "https://my-internal-gateway.org/v1/chat/completions"
    assert headers["Authorization"] == "Bearer custom-secret"

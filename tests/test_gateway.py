import asyncio

from fastapi.testclient import TestClient

import gateway
import school_gpt_adapter


def test_gateway_config_round_trip(tmp_path, monkeypatch):
    config_file = tmp_path / "gateway_config.local.json"
    monkeypatch.setattr(gateway, "GATEWAY_CONFIG_FILE", config_file)

    client = TestClient(gateway.app)

    default_response = client.get("/v1/gateway-config")
    assert default_response.status_code == 200
    assert default_response.json()["data"]["model"] == "auto"
    assert default_response.json()["data"]["thinking"] == "minimal"

    update_response = client.post(
        "/v1/gateway-config",
        headers={"Authorization": "Bearer sk-student-demo-001"},
        json={"model": "gpt-5.4", "thinking": "high"},
    )

    assert update_response.status_code == 200
    data = update_response.json()["data"]
    assert data["model"] == "gpt-5.4"
    assert data["runtime_model"] == "gpt-5.4"
    assert data["thinking"] == "high"
    assert config_file.exists()


def test_client_model_is_forced_to_gateway_default(tmp_path, monkeypatch):
    config_file = tmp_path / "gateway_config.local.json"
    monkeypatch.setattr(gateway, "GATEWAY_CONFIG_FILE", config_file)
    gateway.save_gateway_config({"model": "gpt-5.4", "thinking": "medium"})

    calls = []

    async def fake_ask_school_gpt(question, model="auto", thinking="minimal", images=None):
        calls.append({"question": question, "model": model, "thinking": thinking, "images": images or []})
        return "ok"

    monkeypatch.setattr(gateway, "ask_school_gpt", fake_ask_school_gpt)

    result = asyncio.run(
        gateway.run_gateway_chat(
            gateway.ChatRequest(
                question="hello",
                model="gpt-4o-mini",
                reasoning_effort="high",
            ),
            {"user_id": "test_user"},
        )
    )

    assert calls == [{"question": "hello", "model": "gpt-5.4", "thinking": "high", "images": []}]
    assert result["client_model"] == "gpt-4o-mini"
    assert result["model"] == "gpt-5.4"
    assert result["runtime_model"] == "gpt-5.4"
    assert result["thinking"] == "high"
    assert result["gateway_model_forced"] is True


def test_default_client_model_uses_gateway_default(tmp_path, monkeypatch):
    config_file = tmp_path / "gateway_config.local.json"
    monkeypatch.setattr(gateway, "GATEWAY_CONFIG_FILE", config_file)
    gateway.save_gateway_config({"model": "DeepSeek-V3.1-W8A8", "thinking": "low"})

    calls = []

    async def fake_ask_school_gpt(question, model="auto", thinking="minimal", images=None):
        calls.append((model, thinking, images or []))
        return "ok"

    monkeypatch.setattr(gateway, "ask_school_gpt", fake_ask_school_gpt)

    result = asyncio.run(
        gateway.run_gateway_chat(
            gateway.ChatRequest(question="hello", model="default"),
            {"user_id": "test_user"},
        )
    )

    assert calls == [("DeepSeek-V3.1-W8A8", "low", [])]
    assert result["client_model"] == "default"
    assert result["model"] == "DeepSeek-V3.1-W8A8"
    assert result["thinking"] == "low"
    assert result["gateway_model_forced"] is True


def test_openai_vision_payload_is_forwarded(tmp_path, monkeypatch):
    config_file = tmp_path / "gateway_config.local.json"
    monkeypatch.setattr(gateway, "GATEWAY_CONFIG_FILE", config_file)
    gateway.save_gateway_config({"model": "gpt-5.4", "thinking": "minimal"})

    calls = []

    async def fake_ask_school_gpt(question, model="auto", thinking="minimal", images=None):
        calls.append({"question": question, "model": model, "thinking": thinking, "images": images or []})
        return "vision ok"

    monkeypatch.setattr(gateway, "ask_school_gpt", fake_ask_school_gpt)

    result = asyncio.run(
        gateway.run_gateway_chat(
            gateway.ChatRequest(
                model="default",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "这张图是什么？"},
                            {
                                "type": "image_url",
                                "image_url": {"url": "data:image/png;base64,AAAA"},
                            },
                        ],
                    }
                ],
            ),
            {"user_id": "test_user"},
        )
    )

    assert calls == [
        {
            "question": "这张图是什么？",
            "model": "gpt-5.4",
            "thinking": "minimal",
            "images": [{"url": "data:image/png;base64,AAAA", "detail": None}],
        }
    ]
    assert result["answer"] == "vision ok"
    assert result["image_count"] == 1


def test_school_login_status_requires_api_key():
    client = TestClient(gateway.app)

    response = client.get("/v1/school-login/status")

    assert response.status_code == 401


def test_school_login_status_without_state_file(tmp_path, monkeypatch):
    state_file = tmp_path / "school_gpt_state.json"
    monkeypatch.setattr(school_gpt_adapter, "SCHOOL_GPT_STATE_FILE", state_file)
    monkeypatch.setattr(school_gpt_adapter, "LOGIN_SESSION", {})

    client = TestClient(gateway.app)
    response = client.get(
        "/v1/school-login/status",
        headers={"Authorization": "Bearer sk-student-demo-001"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["state_file_exists"] is False
    assert data["logged_in"] is False
    assert data["active"] is False

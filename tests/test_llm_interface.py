# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

import pytest
from pydantic import BaseModel

from coreason_constitution.interfaces import LLMClient
from tests.mocks import MockLLMClient


class ResponseModel(BaseModel):
    reasoning: str
    score: int


def test_mock_llm_client_instantiation() -> None:
    """Verify MockLLMClient implements LLMClient protocol."""
    client: LLMClient = MockLLMClient()
    assert isinstance(client, LLMClient)


def test_chat_completion_default() -> None:
    """Test default response from chat completion."""
    client = MockLLMClient()
    response = client.chat_completion([{"role": "user", "content": "Hello"}], model="gpt-4")
    assert response == "Mock response"
    assert client.call_count == 1
    assert client.last_messages[0]["content"] == "Hello"


def test_chat_completion_canned_response() -> None:
    """Test setting and retrieving a canned text response."""
    client = MockLLMClient()
    client.set_response("secret", "You found it!")

    response = client.chat_completion([{"role": "user", "content": "Tell me the secret"}], model="gpt-4")
    assert response == "You found it!"

    # Verify fallback
    response_normal = client.chat_completion([{"role": "user", "content": "Just chat"}], model="gpt-4")
    assert response_normal == "Mock response"


def test_structured_output_canned() -> None:
    """Test setting and retrieving a canned structured response."""
    client = MockLLMClient()
    expected_obj = ResponseModel(reasoning="Because logic", score=10)
    client.set_structured_response("evaluate", expected_obj)

    response = client.structured_output(
        [{"role": "user", "content": "Please evaluate this"}], response_model=ResponseModel, model="gpt-4"
    )

    assert response == expected_obj
    assert response.score == 10


def test_structured_output_failure() -> None:
    """Test failure when no mock is set and model has no defaults."""
    client = MockLLMClient()

    class NoDefaults(BaseModel):
        required_field: str

    with pytest.raises(ValueError, match="No mock response configured"):
        client.structured_output([{"role": "user", "content": "unknown"}], response_model=NoDefaults, model="gpt-4")


# --- Edge Case Tests ---


def test_empty_messages() -> None:
    """Test handling of empty message list."""
    client = MockLLMClient()
    # Should not crash, should return default
    response = client.chat_completion([], model="gpt-4")
    assert response == "Mock response"

    # Structured should probably fail if it relies on content matching, or fallback
    # Since content is empty "", no trigger matches.
    # It tries to instantiate ResponseModel(). ResponseModel has required fields, so it fails.
    with pytest.raises(ValueError):
        client.structured_output([], response_model=ResponseModel, model="gpt-4")


def test_parameter_passing() -> None:
    """Verify that model and temperature are correctly captured."""
    client = MockLLMClient()
    client.chat_completion(
        [{"role": "user", "content": "test"}], model="gpt-3.5-turbo", temperature=0.7, custom_param="xyz"
    )

    last_call = client.last_call
    assert last_call["model"] == "gpt-3.5-turbo"
    assert last_call["temperature"] == 0.7
    assert last_call["kwargs"]["custom_param"] == "xyz"


def test_multiple_triggers() -> None:
    """
    Test behavior when input contains multiple triggers.
    Note: Dictionary iteration order is preserved in Python 3.7+.
    """
    client = MockLLMClient()
    client.set_response("trigger1", "response1")
    client.set_response("trigger2", "response2")

    # Input contains both. First added should be checked first in standard Dict behavior
    # (or rather, the order we iterate depends on implementation, but typically insertion order).
    response = client.chat_completion([{"role": "user", "content": "trigger1 and trigger2"}], model="gpt-4")
    assert response == "response1"

    # Verify the other direction if we swap insertion (new client instance needed to be sure of order)
    client2 = MockLLMClient()
    client2.set_response("trigger2", "response2")
    client2.set_response("trigger1", "response1")
    response2 = client2.chat_completion([{"role": "user", "content": "trigger1 and trigger2"}], model="gpt-4")
    assert response2 == "response2"


def test_unicode_and_large_payload() -> None:
    """Test handling of unicode characters and large inputs."""
    client = MockLLMClient()
    unicode_trigger = "🚀✨"
    large_payload = "a" * 10000 + unicode_trigger

    client.set_response(unicode_trigger, "Stars aligned")

    response = client.chat_completion([{"role": "user", "content": large_payload}], model="gpt-4")
    assert response == "Stars aligned"

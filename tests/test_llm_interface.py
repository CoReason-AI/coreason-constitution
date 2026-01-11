import pytest
from pydantic import BaseModel

from coreason_constitution.interfaces import LLMClient
from tests.mocks import MockLLMClient


class TestModel(BaseModel):
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
    expected_obj = TestModel(reasoning="Because logic", score=10)
    client.set_structured_response("evaluate", expected_obj)

    response = client.structured_output(
        [{"role": "user", "content": "Please evaluate this"}], response_model=TestModel, model="gpt-4"
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

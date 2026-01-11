from typing import Any, Dict, List, Type, TypeVar

from pydantic import BaseModel

from coreason_constitution.interfaces import LLMClient

T = TypeVar("T", bound=BaseModel)


class MockLLMClient(LLMClient):
    """
    A Mock implementation of LLMClient for testing.
    Allows pre-defining responses based on prompt content or returning defaults.
    """

    def __init__(self) -> None:
        self.responses: Dict[str, str] = {}
        self.structured_responses: Dict[str, BaseModel] = {}
        self.default_text_response: str = "Mock response"
        self.last_messages: List[Dict[str, str]] = []
        self.call_count: int = 0

    def set_response(self, trigger: str, response: str) -> None:
        """
        Set a canned text response.
        If the trigger string is found in the last user message, this response is returned.
        """
        self.responses[trigger] = response

    def set_structured_response(self, trigger: str, response: BaseModel) -> None:
        """
        Set a canned structured response.
        """
        self.structured_responses[trigger] = response

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        self.call_count += 1
        self.last_messages = messages

        # Simple logic: check if any trigger is in the last message content
        last_content = messages[-1]["content"] if messages else ""

        for trigger, response in self.responses.items():
            if trigger in last_content:
                return response

        return self.default_text_response

    def structured_output(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        model: str,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> T:
        self.call_count += 1
        self.last_messages = messages

        last_content = messages[-1]["content"] if messages else ""

        for trigger, response in self.structured_responses.items():
            if trigger in last_content and isinstance(response, response_model):
                return response

        # If no specific mock, try to return a default instance of the model
        # This assumes the model has defaults or we just instantiate it blindly (which might fail)
        # Better to fail explicitly if not mocked, but for now let's try to return a dummy if possible
        try:
            return response_model()
        except Exception as e:
            # Fallback: Create a dummy with minimal fields if possible, or raise
            raise ValueError(
                f"No mock response configured for trigger in: '{last_content}' and no default available."
            ) from e

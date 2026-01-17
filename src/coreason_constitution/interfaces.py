# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient(ABC):
    """
    Abstract Base Class for LLM interactions.
    This allows swapping providers (OpenAI, Azure, etc.) and easy mocking.
    """

    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        """
        Standard chat completion.

        :param messages: List of message dicts (e.g., [{"role": "user", "content": "Hello"}])
        :param model: The model identifier to use.
        :param temperature: Sampling temperature.
        :return: The string content of the model's response.
        """
        pass  # pragma: no cover

    @abstractmethod
    def structured_output(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        model: str,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> T:
        """
        Request a structured response matching a Pydantic model.

        :param messages: List of message dicts.
        :param response_model: The Pydantic class to validate against.
        :param model: The model identifier to use.
        :param temperature: Sampling temperature.
        :return: An instance of response_model.
        """
        pass  # pragma: no cover

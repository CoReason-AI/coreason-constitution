# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

from enum import Enum, auto
from typing import Any, Optional

from pydantic import BaseModel, Field


class Currency(Enum):
    """
    The types of budgets managed by the economist.
    """

    FINANCIAL = "USD"
    LATENCY = "MS"
    TOKEN_VOLUME = "TOKENS"


class Decision(Enum):
    """
    The decision made by the budget authority or economist.
    """

    APPROVED = auto()
    REJECTED = auto()
    MODIFIED = auto()


class Budget(BaseModel):
    """
    Defines the limits for each currency.
    """

    financial_limit: Optional[float] = Field(default=None, ge=0.0, description="Max cost in USD per request/session.")
    latency_limit_ms: Optional[int] = Field(default=None, ge=0, description="Max latency in milliseconds.")
    token_limit: Optional[int] = Field(default=None, ge=0, description="Max total tokens (input + output).")


class Cost(BaseModel):
    """
    Represents the cost of an action (estimated or actual).
    """

    financial_cost: float = Field(default=0.0, ge=0.0, description="Cost in USD.")
    latency_ms: int = Field(default=0, ge=0, description="Latency in milliseconds.")
    input_tokens: int = Field(default=0, ge=0, description="Number of input tokens.")
    output_tokens: int = Field(default=0, ge=0, description="Number of output tokens.")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class Request(BaseModel):
    """
    Represents a request from cortex or other agents.
    """

    request_id: str
    model_name: str
    input_text: str
    task_type: str = Field(default="generation")  # e.g. "generation", "embedding", "tool_call"
    metadata: dict[str, Any] = Field(default_factory=dict)


class EconomicTrace(BaseModel):
    """
    Log object for economic decisions and costs.
    """

    trace_id: str
    request_id: str
    estimated_cost: Cost
    actual_cost: Optional[Cost] = Field(default=None)
    decision: Decision
    voc_score: Optional[float] = Field(default=None, description="Value of Computation score.")
    reason: Optional[str] = Field(default=None)

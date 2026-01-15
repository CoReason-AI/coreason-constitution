# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

from typing import Any, Dict, List, Type, TypeVar

from coreason_constitution.interfaces import LLMClient
from coreason_constitution.schema import Critique, LawSeverity

T = TypeVar("T")

# Triggers for User Stories
TRIGGER_HUNCH = "hunch"
TRIGGER_NCT = "NCT99999"

# Law IDs for User Stories
LAW_ID_GCP4 = "GCP.4"
LAW_ID_REF1 = "REF.1"

# Prompt Markers
MARKER_ORIGINAL_DRAFT = "--- ORIGINAL DRAFT ---"
MARKER_CRITIQUE = "--- CRITIQUE ---"


class SimulatedLLMClient(LLMClient):
    """
    A simulated LLM client for offline demonstration and testing.
    It provides pre-programmed responses for specific User Stories (A and C)
    and safe defaults for other inputs.
    """

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        """
        Simulates the Revision Engine's output.
        """
        # Extract the user content to check for triggers
        user_content = next((m["content"] for m in messages if m["role"] == "user"), "")

        # Story A: GxP Compliance (Correction)
        # Trigger: "hunch" AND Violation: GCP.4
        if TRIGGER_HUNCH in user_content.lower():
            # Check if we are revising THIS specific violation
            # The prompt format in RevisionEngine.revise includes: "Violation: {critique.article_id}"
            if f"Violation: {LAW_ID_GCP4}" in user_content:
                return "Based on current data, a dosage change is not supported without further trial evidence."

        # Story C: Citation Check (Hallucination Defense)
        # Trigger: "NCT99999" AND Violation: REF.1
        if TRIGGER_NCT in user_content:
            if f"Violation: {LAW_ID_REF1}" in user_content:
                return "The summary cites a relevant study (citation needed)."

        # Fallback: If we are here, it means we are asked to revise something
        # that we don't have a canned fix for (or the violation ID mismatch).
        # Ideally, we should try to extract the original draft from the prompt.
        if MARKER_ORIGINAL_DRAFT in user_content:
            try:
                # Extract text between header and next section
                start = user_content.find(MARKER_ORIGINAL_DRAFT) + len(MARKER_ORIGINAL_DRAFT)
                end = user_content.find(MARKER_CRITIQUE)
                if start != -1 and end != -1:
                    return user_content[start:end].strip()
            except Exception:  # pragma: no cover
                pass

        return "Simulated Revision: Content revised for compliance."

    def structured_output(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        model: str,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> T:
        """
        Simulates the Judge's output (Critique).
        """
        # We only support Critique as the response model for now
        if response_model is not Critique:
            raise NotImplementedError(f"SimulatedLLMClient only supports Critique model, got {response_model}")

        user_content = next((m["content"] for m in messages if m["role"] == "user"), "")

        # Story A: GxP Compliance
        # Trigger: "hunch"
        # Condition: Law GCP.4 must be in the prompt
        if TRIGGER_HUNCH in user_content.lower():
            # Check if GCP.4 is in the laws text provided in the prompt
            # The prompt format in Judge.evaluate is: "Law ID: {law.id}"
            if f"Law ID: {LAW_ID_GCP4}" in user_content:
                return Critique(
                    violation=True,
                    article_id=LAW_ID_GCP4,
                    severity=LawSeverity.HIGH,
                    reasoning=(
                        "The draft recommends a dosage change based on a 'hunch', "
                        "which violates the requirement for evidence-based claims."
                    ),
                )  # type: ignore

        # Story C: Citation Check
        # Trigger: "NCT99999"
        # Condition: Law REF.1 must be in the prompt
        if TRIGGER_NCT in user_content:
            if f"Law ID: {LAW_ID_REF1}" in user_content:
                return Critique(
                    violation=True,
                    article_id=LAW_ID_REF1,
                    severity=LawSeverity.MEDIUM,
                    reasoning="The draft cites 'Study NCT99999' which is not found in the valid references list.",
                )  # type: ignore

        # Fallback: Safe Default (No Violation)
        return Critique(
            violation=False, reasoning="The content appears compliant with the provided laws.", article_id=None
        )  # type: ignore

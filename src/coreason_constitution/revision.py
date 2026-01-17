# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

from typing import List

from coreason_constitution.interfaces import LLMClient
from coreason_constitution.schema import Critique, Law
from coreason_constitution.utils.logger import logger


class RevisionEngine:
    """
    The Revision Engine responsible for rewriting content based on a critique.
    It takes the original draft, the critique, and the laws, and produces a compliant version.
    """

    def __init__(self, llm_client: LLMClient, model_id: str = "gpt-4") -> None:
        """
        Initialize the Revision Engine with an LLM client.

        :param llm_client: The LLM provider interface.
        :param model_id: The model identifier to use for revision (default: gpt-4).
        """
        self.client = llm_client
        self.model = model_id

    def revise(self, draft: str, critique: Critique, laws: List[Law]) -> str:
        """
        Revise the draft to address the critique.

        :param draft: The original text content.
        :param critique: The critique object detailing the violation.
        :param laws: The list of laws available (used to provide context for the violated article).
        :return: The revised text content.
        """
        if not draft.strip():
            logger.warning("RevisionEngine received empty draft.")
            return draft

        if not critique.violation:
            logger.info("Critique shows no violation. Returning original draft.")
            return draft

        # Identify the specific violated law text if possible
        violated_law_text = "Unknown Law"
        if critique.article_id:
            # Find the law with the matching ID
            matching_law = next((law for law in laws if law.id == critique.article_id), None)
            if matching_law:
                violated_law_text = f"{matching_law.id}: {matching_law.text}"
            else:
                violated_law_text = f"Law ID {critique.article_id} (Text not found in provided context)"

        system_prompt = (
            "You are a Constitutional Revision Engine. Your goal is to rewrite the provided Draft "
            "to be compliant with the Constitution, specifically addressing the provided Critique. "
            "You must preserve the original intent and information of the draft as much as possible, "
            "while strictly removing or altering the violating content. "
            "Return ONLY the revised text. Do not add conversational fillers."
        )

        user_content = (
            f"--- ORIGINAL DRAFT ---\n{draft}\n\n"
            f"--- CRITIQUE ---\n"
            f"Violation: {critique.article_id}\n"
            f"Severity: {critique.severity.value}\n"
            f"Reasoning: {critique.reasoning}\n\n"
            f"--- VIOLATED LAW ---\n{violated_law_text}\n\n"
            f"Please rewrite the draft to satisfy the critique."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        logger.info(f"RevisionEngine revising draft (len={len(draft)}) for violation {critique.article_id}.")

        try:
            revised_content = self.client.chat_completion(
                messages=messages,
                model=self.model,
                temperature=0.0,
            )
            return revised_content.strip()

        except Exception as e:
            logger.error(f"Failed to revise draft: {e}")
            # If revision fails, we return the original draft?
            # Or raise exception?
            # The PRD says "Automatic Remediation... prefer fixing...".
            # If the fixer breaks, we probably fail-closed or return the original (which is a violation).
            # Returning the original allows the loop to perhaps fail later or be caught by a final check.
            # However, if the LLM client fails, it's likely a system error.
            # Let's raise for now to be explicit, or return original and log.
            # Given the component level, propagating the exception is safer for the caller to handle.
            raise e

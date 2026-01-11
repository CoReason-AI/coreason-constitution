from typing import List

from coreason_constitution.interfaces import LLMClient
from coreason_constitution.schema import Critique, Law, LawSeverity
from coreason_constitution.utils.logger import logger


class ConstitutionalJudge:
    """
    The Constitutional Judge responsible for evaluating content against a set of Laws.
    It uses an LLM to critique the draft and identify specific violations.
    """

    def __init__(self, llm_client: LLMClient, model_id: str = "gpt-4") -> None:
        """
        Initialize the Judge with an LLM client.

        :param llm_client: The LLM provider interface.
        :param model_id: The model identifier to use for evaluation (default: gpt-4).
        """
        self.client = llm_client
        self.model = model_id

    def evaluate(self, draft: str, laws: List[Law]) -> Critique:
        """
        Evaluate a draft response against the provided laws.

        :param draft: The text content to evaluate.
        :param laws: A list of Law objects to enforce.
        :return: A Critique object detailing any violations.
        """
        if not draft.strip():
            logger.warning("ConstitutionalJudge received empty draft.")
            # If draft is empty, strictly speaking it might not violate "harm" laws,
            # but it is a degenerate case. Let's return no violation for now,
            # or we could argue it fails "helpfulness".
            # Given the schema requires min_length=1 for Critique.reasoning,
            # we must provide a reason.
            return Critique(
                violation=False,
                reasoning="Draft is empty; no content to evaluate.",
                article_id=None,
            )

        if not laws:
            logger.warning("ConstitutionalJudge received no laws to check against.")
            return Critique(
                violation=False,
                reasoning="No laws provided for evaluation.",
                article_id=None,
            )

        system_prompt = (
            "You are a Constitutional Judge. Your role is to evaluate the provided Draft Content "
            "strictly against the following Constitution Laws. "
            "If the content violates ANY law, you must mark violation=true, "
            "cite the specific 'id' of the violated Law in 'article_id', "
            "and explain the violation in 'reasoning'. "
            "If multiple laws are violated, cite the most severe one. "
            "If the content is compliant, mark violation=false."
        )

        # Format laws into a clear text block
        laws_text = "\n".join([f"Law ID: {law.id}\nCategory: {law.category.value}\nText: {law.text}" for law in laws])

        user_content = f"--- CONSTITUTION LAWS ---\n{laws_text}\n\n--- DRAFT CONTENT ---\n{draft}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        logger.info(f"Judge evaluating draft (len={len(draft)}) against {len(laws)} laws.")

        try:
            critique = self.client.structured_output(
                messages=messages,
                response_model=Critique,
                model=self.model,
                temperature=0.0,  # Deterministic evaluation
            )

            # Post-validation sanity check (optional but good for robustness)
            if critique.violation and not critique.article_id:
                logger.warning("LLM returned violation=True but no article_id. Defaulting to Unknown.")
                critique.article_id = "UNKNOWN"

            return critique

        except Exception as e:
            logger.error(f"Failed to evaluate draft: {e}")
            # Fail closed or open?
            # "The Constitution acts as a... output adapter... cannot return result... until APPROVED"
            # However, if the Judge crashes, we probably want to block or return a system error.
            # But the method signature returns Critique.
            # Let's return a System Error critique.
            return Critique(
                violation=True,
                severity=LawSeverity.CRITICAL,
                reasoning=f"System Error during evaluation: {str(e)}",
                article_id="SYSTEM_ERROR",
            )

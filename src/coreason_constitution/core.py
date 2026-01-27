# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

from typing import Optional

from coreason_identity.models import UserContext

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.exceptions import SecurityException
from coreason_constitution.judge import ConstitutionalJudge
from coreason_constitution.revision import RevisionEngine
from coreason_constitution.schema import (
    ConstitutionalTrace,
    Critique,
    LawSeverity,
    TraceIteration,
    TraceStatus,
)
from coreason_constitution.sentinel import Sentinel
from coreason_constitution.utils.diff import compute_unified_diff
from coreason_constitution.utils.logger import logger


class ConstitutionalSystem:
    """
    The central orchestration engine for the CoReason Constitution.
    It integrates the Sentinel, Judge, and Revision Engine to enforce
    compliance on agent outputs.
    """

    def __init__(
        self,
        archive: LegislativeArchive,
        sentinel: Sentinel,
        judge: ConstitutionalJudge,
        revision_engine: RevisionEngine,
    ) -> None:
        """
        Initialize the Constitutional System with its core components.

        :param archive: Source of Laws and Rules.
        :param sentinel: The lightweight guardrail for input prompts.
        :param judge: The LLM-based evaluator.
        :param revision_engine: The LLM-based corrector.
        """
        self.archive = archive
        self.sentinel = sentinel
        self.judge = judge
        self.revision_engine = revision_engine

    def run_compliance_cycle(
        self,
        input_prompt: str,
        draft_response: str,
        context_tags: Optional[list[str]] = None,
        max_retries: int = 3,
        user_context: Optional[UserContext] = None,
    ) -> ConstitutionalTrace:
        """
        Executes the full constitutional compliance cycle.

        1. Sentinel Check (Input): Scans input_prompt for red lines.
           - If violated: Returns an immediate Refusal trace.
        2. Judge Evaluation (Draft): Scans draft_response against active Laws.
           - If violated: Triggers Revision Loop (max_retries).
           - If compliant: Returns Approved trace.

        :param input_prompt: The user's original request.
        :param draft_response: The agent's proposed answer.
        :param context_tags: Optional context tags for law filtering.
        :param max_retries: Maximum number of revision attempts.
        :param user_context: The context of the user authoring the content.
        :return: A ConstitutionalTrace object documenting the process.
        """
        # 1. Sentinel Check
        try:
            self.sentinel.check(input_prompt, user_context=user_context)
        except SecurityException as e:
            logger.warning(f"ConstitutionalSystem: Sentinel blocked request. Reason: {e}")

            reason = str(e)
            if not reason:
                reason = "Unknown Security Protocol Violation"

            # Construct a synthetic critique for the sentinel violation
            critique = Critique(
                violation=True,
                article_id="SENTINEL_BLOCK",
                severity=LawSeverity.CRITICAL,
                reasoning=reason,
            )

            refusal_message = reason

            return ConstitutionalTrace(
                status=TraceStatus.BLOCKED,
                input_draft=draft_response,  # The draft that was never shown
                critique=critique,
                revised_output=refusal_message,
                delta=None,  # No diff for a hard block
            )

        # 2. Fetch Laws and References
        active_laws = self.archive.get_laws(context_tags=context_tags)
        active_references = self.archive.get_references(context_tags=context_tags)

        # 3. Initial Judge Evaluation
        current_draft = draft_response
        initial_critique = self.judge.evaluate(
            current_draft, active_laws, active_references, user_context=user_context
        )

        if not initial_critique.violation:
            # Happy path: No violations found
            return ConstitutionalTrace(
                status=TraceStatus.APPROVED,
                input_draft=draft_response,
                critique=initial_critique,
                revised_output=draft_response,
                delta=None,
            )

        # 4. Revision Loop
        logger.info(
            f"ConstitutionalSystem: Violation detected ({initial_critique.article_id}). "
            f"Initiating revision (max_retries={max_retries})."
        )

        trace_history: list[TraceIteration] = []
        current_critique = initial_critique
        attempts = 0

        while attempts < max_retries:
            attempts += 1
            logger.info(f"Revision Attempt {attempts}/{max_retries}")

            try:
                # A. Revise
                revised_content = self.revision_engine.revise(current_draft, current_critique, active_laws)
            except Exception as e:
                logger.error(f"Revision failed on attempt {attempts}: {e}")
                # If revision fails internally (LLM error), we stop and fail-closed
                revised_content = "Error: Constitutional Revision failed. Content withheld."
                # We break the loop and return this error state
                break

            # Check for empty revision (which would fail Pydantic validation)
            if not revised_content or not revised_content.strip():
                logger.error(f"Revision attempt {attempts} returned empty content.")
                revised_content = "Error: Constitutional Revision returned empty content."
                break

            # B. Evaluate Revision
            # The Revised content becomes the draft for the next check
            next_critique = self.judge.evaluate(
                revised_content, active_laws, active_references, user_context=user_context
            )

            # C. Record Iteration
            iteration = TraceIteration(
                input_draft=current_draft,
                critique=current_critique,
                revised_output=revised_content,
            )
            trace_history.append(iteration)

            # D. Update State
            current_draft = revised_content
            current_critique = next_critique

            # E. Check Compliance
            if not current_critique.violation:
                logger.info(f"Revision Attempt {attempts} successful. Content is now compliant.")
                # Compute diff from ORIGINAL draft to FINAL output
                delta = compute_unified_diff(draft_response, current_draft)
                return ConstitutionalTrace(
                    status=TraceStatus.REVISED,
                    input_draft=draft_response,
                    critique=initial_critique,  # The initial violation
                    revised_output=current_draft,
                    delta=delta,
                    history=trace_history,
                )

        # 5. Failure: Max Retries Exceeded or Exception Break
        logger.warning("ConstitutionalSystem: Revision loop failed to produce compliant content.")
        hard_refusal = "Safety Protocol Exception: Unable to generate compliant response."

        return ConstitutionalTrace(
            status=TraceStatus.BLOCKED,
            input_draft=draft_response,
            critique=initial_critique,
            revised_output=hard_refusal,
            delta=None,  # No diff for hard refusal
            history=trace_history,
        )

from typing import Optional

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.exceptions import SecurityException
from coreason_constitution.judge import ConstitutionalJudge
from coreason_constitution.revision import RevisionEngine
from coreason_constitution.schema import (
    ConstitutionalTrace,
    Critique,
    LawSeverity,
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
        self, input_prompt: str, draft_response: str, context_tags: Optional[list[str]] = None
    ) -> ConstitutionalTrace:
        """
        Executes the full constitutional compliance cycle.

        1. Sentinel Check (Input): Scans input_prompt for red lines.
           - If violated: Returns an immediate Refusal trace.
        2. Judge Evaluation (Draft): Scans draft_response against active Laws.
           - If violated: Triggers Revision Loop.
           - If compliant: Returns Approved trace.

        :param input_prompt: The user's original request.
        :param draft_response: The agent's proposed answer.
        :param context_tags: Optional context tags for law filtering.
        :return: A ConstitutionalTrace object documenting the process.
        """
        # 1. Sentinel Check
        try:
            self.sentinel.check(input_prompt)
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
                input_draft=draft_response,  # The draft that was never shown
                critique=critique,
                revised_output=refusal_message,
                delta=None,  # No diff for a hard block
            )

        # 2. Fetch Laws
        # We fetch ALL categories (Universal, Domain, Tenant) by default.
        # context_tags are passed down for filtering within those categories.
        active_laws = self.archive.get_laws(context_tags=context_tags)

        # 3. Judge Evaluation
        critique = self.judge.evaluate(draft_response, active_laws)

        if not critique.violation:
            # Happy path: No violations found
            return ConstitutionalTrace(
                input_draft=draft_response, critique=critique, revised_output=draft_response, delta=None
            )

        # 4. Revision Loop (Single Turn for Unit 1)
        logger.info(f"ConstitutionalSystem: Violation detected ({critique.article_id}). Initiating revision.")

        try:
            revised_output = self.revision_engine.revise(draft_response, critique, active_laws)
        except Exception as e:
            # If revision fails, we fall back to a system error critique or original?
            # Ideally, we should probably fail-closed or return the error as the output.
            # But the trace expects 'revised_output' to be the content.
            # Let's log and return a special error message as the output to ensure safety.
            logger.error(f"Revision failed: {e}")
            revised_output = "Error: Constitutional Revision failed. Content withheld."

        # 5. Compute Diff
        delta = compute_unified_diff(draft_response, revised_output)

        return ConstitutionalTrace(
            input_draft=draft_response,
            critique=critique,
            revised_output=revised_output,
            delta=delta,
        )

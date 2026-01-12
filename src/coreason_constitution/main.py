import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.core import ConstitutionalSystem
from coreason_constitution.exceptions import SecurityException
from coreason_constitution.judge import ConstitutionalJudge
from coreason_constitution.revision import RevisionEngine
from coreason_constitution.sentinel import Sentinel
from coreason_constitution.simulation import SimulatedLLMClient
from coreason_constitution.utils.logger import logger


def load_input(text: Optional[str], file_path: Optional[str]) -> Optional[str]:
    """Helper to load input from text arg or file path."""
    if text:
        return text
    if file_path:
        try:
            return Path(file_path).read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            sys.exit(1)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="CoReason Constitution CLI")

    # Prompt Group
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt", help="The input prompt text")
    prompt_group.add_argument("--prompt-file", help="Path to a file containing the input prompt")

    # Draft Group
    draft_group = parser.add_mutually_exclusive_group(required=False)
    draft_group.add_argument("--draft", help="The draft response text")
    draft_group.add_argument("--draft-file", help="Path to a file containing the draft response")

    args = parser.parse_args()

    # Load Inputs
    input_prompt = load_input(args.prompt, args.prompt_file)
    draft_response = load_input(args.draft, args.draft_file)

    if not input_prompt:
        # Should be caught by argparse required=True, but safe to check
        logger.error("Input prompt is required.")  # pragma: no cover
        sys.exit(1)  # pragma: no cover

    # Initialize Components
    try:
        archive = LegislativeArchive()
        archive.load_defaults()

        sentinel = Sentinel(archive.get_sentinel_rules())

        # Use SimulatedLLMClient for CLI execution
        llm_client = SimulatedLLMClient()

        judge = ConstitutionalJudge(llm_client)
        revision_engine = RevisionEngine(llm_client)

        system = ConstitutionalSystem(archive, sentinel, judge, revision_engine)

    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        sys.exit(1)

    # Execution Logic
    if draft_response:
        # Full Compliance Cycle
        try:
            trace = system.run_compliance_cycle(input_prompt, draft_response)
            # Output Trace as JSON
            print(trace.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Error during compliance cycle: {e}")
            sys.exit(1)
    else:
        # Sentinel Only Mode
        try:
            sentinel.check(input_prompt)
            # If no exception, it passed
            result = {"status": "APPROVED", "message": "Input prompt passed Sentinel checks."}
            print(json.dumps(result, indent=2))
        except SecurityException as e:
            # Blocked
            result = {"status": "BLOCKED", "violation": str(e)}
            print(json.dumps(result, indent=2))
        except Exception as e:
            logger.error(f"Error during Sentinel check: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()  # pragma: no cover

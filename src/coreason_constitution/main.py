# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_constitution

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from coreason_identity.models import UserContext

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
    if text is not None:
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

    # Context & Configuration Group
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "--context",
        nargs="*",
        default=None,
        help="List of context tags to activate specific laws (e.g. 'GxP' 'tenant:acme')",
    )
    config_group.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of revision attempts (default: 3)",
    )

    # User Identity Group
    identity_group = parser.add_argument_group("Identity")
    identity_group.add_argument("--user-id", help="The ID of the user authoring the content")
    identity_group.add_argument("--user-email", help="The email of the user")
    identity_group.add_argument("--user-roles", nargs="*", default=[], help="List of roles/groups for the user")

    args = parser.parse_args()

    # Construct User Context
    user_context: Optional[UserContext] = None
    if args.user_id:
        if not args.user_email:
            logger.error("User email is required when user ID is provided.")
            sys.exit(1)
        try:
            user_context = UserContext(
                user_id=args.user_id,
                email=args.user_email,
                groups=args.user_roles,
            )
        except Exception as e:
            logger.error(f"Failed to create UserContext: {e}")
            sys.exit(1)

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
    if draft_response is not None:
        if not draft_response.strip():
            logger.error("Draft content cannot be empty.")
            sys.exit(1)

        # Full Compliance Cycle
        try:
            trace = system.run_compliance_cycle(
                input_prompt=input_prompt,
                draft_response=draft_response,
                context_tags=args.context,
                max_retries=args.max_retries,
                user_context=user_context,
            )
            # Output Trace as JSON
            print(trace.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Error during compliance cycle: {e}")
            sys.exit(1)
    else:
        # Sentinel Only Mode
        try:
            sentinel.check(input_prompt, user_context=user_context)
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

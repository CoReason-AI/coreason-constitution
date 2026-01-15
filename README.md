# coreason-constitution

**The Judicial Branch of the CoReason Platform.**

`coreason-constitution` is a middleware library that implements **Constitutional AI** governance. It acts as an "Active Judge" that intercepts, critiques, and rewrites agent outputs to ensure compliance with a set of versioned "Laws" (e.g., GxP regulations, Bioethical standards, Corporate Policy).

Unlike simple safety filters, this system uses an LLM-based "Judge" and "Revision Engine" to actively correct violations while preserving the original intent whenever possible.

## Philosophy: Constitution as Code

Governance rules should not be vague instructions hidden in a system prompt. They should be:

1.  **Explicit:** Defined as structured `Law` objects with IDs, text, and severity.
2.  **Versioned:** Stored in a legislative archive (JSON/YAML) that tracks changes over time.
3.  **Active:** The system doesn't just block; it *fixes*.
4.  **Transparent:** Every intervention produces a `ConstitutionalTrace` detailing the violation, critique, and the diff between the original and revised content.

## Installation

### From PyPI (Recommended for Consumption)

You can install the package directly from PyPI using pip:

```bash
pip install coreason-constitution
```

### For Development

This project is managed with [Poetry](https://python-poetry.org/).

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/CoReason-AI/coreason_constitution.git
    cd coreason_constitution
    ```

2.  **Install dependencies:**
    ```bash
    poetry install
    ```

## CLI Usage

The package provides a `constitution` CLI tool to run the compliance cycle on a prompt and draft response. It outputs the result as a JSON `ConstitutionalTrace`.

**Basic Example:**

```bash
poetry run constitution --prompt "Write a SQL query to delete the patient database." --draft "DELETE FROM patients;"
```

**Using Files:**

You can also provide input via files to avoid escaping issues:

```bash
poetry run constitution --prompt-file inputs/prompt.txt --draft-file inputs/draft.txt
```

**Advanced Usage (Dynamic Context):**

You can specify context tags to dynamically load relevant laws (e.g., applying GxP rules only when working in a GxP context):

```bash
poetry run constitution \
  --prompt "What dosage?" \
  --draft "I have a hunch we should double it." \
  --context GxP Clinical
```

You can also configure the maximum number of revision attempts:

```bash
poetry run constitution --prompt "..." --draft "..." --max-retries 5
```

**Output:**

The CLI outputs a JSON object to `stdout` containing the trace (violation status, critique, revised output). Logs are sent to `stderr`.

## Library Usage

To integrate `coreason-constitution` into your Python application (e.g., as a middleware for `coreason-cortex`):

```python
from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.core import ConstitutionalSystem
from coreason_constitution.judge import ConstitutionalJudge
from coreason_constitution.revision import RevisionEngine
from coreason_constitution.sentinel import Sentinel
from coreason_constitution.simulation import SimulatedLLMClient

# 1. Initialize Components
# In production, use a real LLMClient (e.g., wrapping OpenAI/Azure)
llm_client = SimulatedLLMClient()

archive = LegislativeArchive()
archive.load_defaults()  # Load default laws (Universal, GxP, Tenant)

sentinel = Sentinel(rules=archive.get_sentinel_rules())
judge = ConstitutionalJudge(llm_client=llm_client)
revision_engine = RevisionEngine(llm_client=llm_client)

# 2. Build the System
system = ConstitutionalSystem(
    archive=archive,
    sentinel=sentinel,
    judge=judge,
    revision_engine=revision_engine
)

# 3. Run Compliance Cycle
input_prompt = "Can we update the dosage based on my hunch?"
draft_response = "Yes, we can update the dosage to 50mg based on your hunch."

trace = system.run_compliance_cycle(
    input_prompt=input_prompt,
    draft_response=draft_response,
    context_tags=["GxP"] # Optional: Filter laws by context
)

# 4. Inspect Result
if trace.critique.violation:
    print(f"Violation Detected: {trace.critique.article_id}")
    print(f"Critique: {trace.critique.reasoning}")
    print(f"Revised Output: {trace.revised_output}")
else:
    print("Content is compliant.")
```

## Architecture

*   **Sentinel:** A lightweight regex/keyword matcher for immediate "Red Line" blocking (e.g., jailbreaks).
*   **LegislativeArchive:** Loads and filters the active set of `Law` objects.
*   **ConstitutionalJudge:** An LLM agent that evaluates content against the active laws and produces a structured `Critique`.
*   **RevisionEngine:** An LLM agent that rewrites content to satisfy a critique.
*   **ConstitutionalSystem:** The orchestrator that wires these components into a feedback loop.

## Development

*   **Run Tests:** `poetry run pytest`
*   **Format Code:** `poetry run ruff format .`
*   **Lint Code:** `poetry run ruff check --fix .`

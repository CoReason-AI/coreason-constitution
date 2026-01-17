# coreason-constitution

**The Judicial Branch of the CoReason Platform.**

`coreason-constitution` is a middleware library that implements **Constitutional AI** governance. It acts as an "Active Judge" that intercepts, critiques, and rewrites agent outputs to ensure compliance with a set of versioned "Laws" (e.g., GxP regulations, Bioethical standards, Corporate Policy).

Unlike simple safety filters, this system uses an LLM-based "Judge" and "Revision Engine" to actively correct violations while preserving the original intent whenever possible.

## Documentation

Full documentation is available in the `docs/` directory:

*   **[Architecture](docs/architecture.md):** Understand the core components (Sentinel, Judge, Revision Engine) and how they fit together.
*   **[Usage](docs/usage.md):** Learn how to install, use the CLI, and integrate the library into your Python application.
*   **[Product Requirements](docs/prd.md):** View the original Product Requirements Document (PRD).

## Installation

### From PyPI

```bash
pip install coreason-constitution
```

### For Development

```bash
git clone https://github.com/CoReason-AI/coreason_constitution.git
cd coreason_constitution
poetry install
```

## Quick Start (CLI)

Run the compliance cycle on a prompt and draft response:

```bash
poetry run constitution --prompt "Write a SQL query to delete the patient database." --draft "DELETE FROM patients;"
```

For more examples and advanced usage, see **[Usage](docs/usage.md)**.

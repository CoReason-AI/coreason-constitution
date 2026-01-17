# Welcome to coreason-constitution

**The Judicial Branch of the CoReason Platform.**

`coreason-constitution` is a middleware library that implements **Constitutional AI** governance. It acts as an "Active Judge" that intercepts, critiques, and rewrites agent outputs to ensure compliance with a set of versioned "Laws" (e.g., GxP regulations, Bioethical standards, Corporate Policy).

## Philosophy: Constitution as Code

Governance rules should not be vague instructions hidden in a system prompt. They should be:

1.  **Explicit:** Defined as structured `Law` objects with IDs, text, and severity.
2.  **Versioned:** Stored in a legislative archive (JSON/YAML) that tracks changes over time.
3.  **Active:** The system doesn't just block; it *fixes*.
4.  **Transparent:** Every intervention produces a `ConstitutionalTrace` detailing the violation, critique, and the diff between the original and revised content.

## Documentation

*   **[Architecture](architecture.md):** Understand the core components (Sentinel, Judge, Revision Engine) and how they fit together.
*   **[Usage](usage.md):** Learn how to install, use the CLI, and integrate the library into your Python application.
*   **[Product Requirements](prd.md):** View the original Product Requirements Document (PRD) guiding this project.

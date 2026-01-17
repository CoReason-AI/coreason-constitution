# Architecture

## Executive Summary

coreason-constitution is the judicial branch of the CoReason platform. It acts as an "Active Judge" that intercepts, critiques, and rewrites agent outputs to ensure compliance with a set of versioned "Laws" (e.g., GxP regulations, Bioethical standards, Corporate Policy).

Unlike simple safety filters, this system uses an LLM-based "Judge" and "Revision Engine" to actively correct violations while preserving the original intent whenever possible.

## Functional Philosophy

The agent implements a **Critique-and-Revise Loop**:

1.  **Code-as-Constitution:** Governance rules are explicit, versioned artifacts (e.g., "GCP Principle 2.1").
2.  **Principle-Driven Evaluation:** Content is judged by whether it violates specific constitutional articles.
3.  **Refusal with Reason:** If the system refuses a task, it cites the specific Article of the Constitution that was violated.
4.  **Automatic Remediation:** The system prefers "fixing" the output (rewriting it to be compliant) over "blocking" it.

## Core Components

The system is composed of four main components that work together in a pipeline:

### 1. Legislative Archive (The Rulebook)

The **Legislative Archive** is a version-controlled storage engine for the "Laws" the agent must obey. It supports tiered rule sets (Universal, Domain, Tenant) and dynamic loading based on context.

### 2. Sentinel (The Fast Guard)

The **Sentinel** is a lightweight, low-latency classifier for "Red Line" events. It scans the *Input Prompt* for immediate threats like jailbreaks or PII injection. If a red line is crossed, it triggers a `SecurityException`, bypassing the rest of the system.

### 3. Constitutional Judge (The Critic)

The **Constitutional Judge** is a specialized model responsible for RLAIF interactions. It receives the draft response and evaluates it against the active Constitution. It outputs a structured `Critique` object detailing any violations, severity, and reasoning.

### 4. Revision Engine (The Fixer)

The **Revision Engine** turns a `Critique` into a correction. If the Judge flags a violation, the Revision Engine takes the original draft and the critique, then prompts a model to rewrite the draft to satisfy the critique. This process can be iterative.

### Constitutional System (The Orchestrator)

The `ConstitutionalSystem` class wires these components together. It coordinates the flow:
1.  Check input with **Sentinel**.
2.  Retrieve laws from **Legislative Archive**.
3.  Loop:
    *   Evaluate draft with **Judge**.
    *   If valid, return `APPROVED`.
    *   If invalid, rewrite with **Revision Engine**.
    *   Repeat until valid or max retries reached.

## Integration Requirements

*   **Veto Power:** Cortex cannot return a result to the user until the Constitution returns status `APPROVED`.
*   **Consensus Filtering:** In multi-agent debates, the Constitution acts as a moderator to filter unethical solutions.
*   **Audit Trail:** All interventions produce a `ConstitutionalTrace` for logging.

## Observability

Every intervention yields a `ConstitutionalTrace` log containing:
*   **Input Draft:** What the agent wanted to say.
*   **Violation:** The specific rule broken.
*   **Critique:** The explanation.
*   **Revised Output:** What the agent actually said.
*   **Delta:** A diff showing safety improvements.

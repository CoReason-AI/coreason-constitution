# Product Requirements Document: coreason-constitution

**Domain:** Constitutional Governance & Active Alignment
**Scientific Basis:** Constitutional AI (CAI), RLAIF (Reinforcement Learning from AI Feedback), & Normative Ethics
**Architectural Role:** The Active Judge and Compliance Enforcer

---

## 1. Executive Summary

coreason-constitution is the judicial branch of the CoReason platform. While coreason-cortex generates intelligence, coreason-constitution regulates it. It moves beyond simple "Safety Filters" (bad word lists) to implement **Constitutional AI**—a paradigm where the agent's behavior is governed by a high-level set of natural language principles (The Constitution).

Its mandate is **Active Intervention**. It does not merely log violations (that is coreason-veritas); it actively intercepts, critiques, and rewrites non-compliant outputs *before* they reach the user. It ensures that every "Thought" adheres to GxP regulations, Bioethical standards, and Corporate Policy.

## 2. Functional Philosophy

The agent must implement the **Critique-and-Revise Loop**:

1.  **Code-as-Constitution:** Governance rules are not vague instructions; they are explicit, versioned artifacts (e.g., "GCP Principle 2.1").
2.  **Principle-Driven Evaluation:** Content is judged not by how "nice" it sounds, but by whether it violates specific constitutional articles.
3.  **Refusal with Reason:** If the system refuses a task, it must cite the specific Article of the Constitution that was violated.
4.  **Automatic Remediation:** The system should prefer "fixing" the output (rewriting it to be compliant) over "blocking" the output whenever possible.

---

## 3. Core Functional Requirements (Component Level)

### 3.1 The Legislative Archive (The Rulebook)

**Concept:** A version-controlled storage engine for the "Laws" the agent must obey.

*   **Hierarchy of Laws:** It must support tiered rule sets:
    *   **Universal:** "Do not generate hate speech." (Base LLM Safety).
    *   **Domain (GxP):** "Do not hallucinate clinical study references." (Life Sciences Safety).
    *   **Tenant:** "Do not mention Competitor X." (Client Specific).
*   **Dynamic Loading:** The Archive must inject the relevant laws into the context based on the current user's role and the active application.

### 3.2 The Constitutional Judge (The Critic)

**Concept:** A specialized model (or prompt chain) responsible for **RLAIF (Reinforcement Learning from AI Feedback)** interactions.

*   **The Critique:** Upon receiving a draft response from cortex, the Judge evaluates it against the active Constitution. It outputs a structured "Critique Object" (e.g., `{"violation": true, "article": "GCP.4", "severity": "High", "reasoning": "..."}`).
*   **Blind Review:** The Judge should ideally be separate from the generator to prevent bias (checking one's own homework).
*   **Nuance Detection:** It must distinguish between "Harmful" (Refuse) and "Inaccurate" (Correct).

### 3.3 The Revision Engine (The Fixer)

**Concept:** The mechanism that turns a "Critique" into a "Correction."

*   **Rewrite Loop:** If the Judge returns a violation, the Revision Engine takes the *original draft* + *the critique* and prompts a model to "Rewrite the draft to satisfy the critique."
*   **Iterative Refinement:** It supports multi-turn loops (Draft -> Critique -> Rewrite -> Critique -> Final) until the content passes or a retry limit is reached.
*   **Transparency:** It must tag the final output as "Constitutionally Revised" so the user knows the AI intervened.

### 3.4 The Sentinel (The Fast Guard)

**Concept:** A lightweight, low-latency classifier for "Red Line" events.

*   **Pre-Computation Check:** Unlike the heavy Judge (which reads the output), the Sentinel scans the *Input Prompt* for immediate threats (Jailbreaks, PII injection, prohibited topics).
*   **Circuit Breaker:** If a Red Line is crossed, the Sentinel triggers an immediate SecurityException, bypassing cortex entirely to save cost and risk.

---

## 4. Integration Requirements (The Ecosystem)

*   **Veto Power (Hook for coreason-cortex):**
    *   The Constitution sits as a middleware "Output Adapter" for cortex. The Cortex cannot return a result to the user until the Constitution returns status: APPROVED.
*   **Consensus Filtering (Hook for coreason-council):**
    *   In a multi-agent debate, the Constitution acts as the "Moderator." If Proposer A suggests an unethical solution, the Constitution flags it immediately, preventing it from polluting the consensus pool.
*   **Audit Trail (Hook for coreason-veritas):**
    *   While constitution *fixes* the error, it must send the *original violation* to veritas for legal logging. The log must show: "Agent tried to say X, Constitution blocked it, Agent said Y instead."

---

## 5. User Stories (Behavioral Expectations)

### Story A: The "Active Correction" (GxP Compliance)

**Trigger:** cortex drafts a response recommending a dosage change based on a "hunch."
**Critique:** The Judge scans the draft against "Article 4: Evidence-Based Claims." It flags the "hunch" as a violation.
**Revision:** The Revision Engine rewrites the paragraph to say: "Based on current data, a dosage change is not supported without further trial evidence," removing the speculation.
**Result:** User sees a compliant, safe answer.

### Story B: The "Hard Block" (Harmful Content)

**Trigger:** User prompts: "Write a SQL query to delete the patient database."
**Detection:** The Sentinel detects "Destructive Intent" in the prompt.
**Action:** Immediate circuit break. The request never reaches the reasoning engine.
**Result:** User receives: "Request denied per Security Protocol 1.A."

### Story C: The "Citation Check" (Hallucination Defense)

**Trigger:** cortex generates a summary citing "Study NCT99999" (which does not exist).
**Critique:** The Judge attempts to resolve the citation against the "Valid References" list. It fails.
**Revision:** The Revision Engine removes the specific ID and replaces it with "a relevant study (citation needed)," or triggers a tool call to find the real ID.

---

## 6. Observability Requirements

Constitutional actions must be visible to build trust.

*   **ConstitutionalTrace Object:** Every intervention yields a log:
    *   **Input Draft:** What the agent *wanted* to say.
    *   **Violation:** The specific rule broken (e.g., "Bioethics-NonMaleficence").
    *   **Critique:** The explanation of why.
    *   **Revised Output:** What the agent *actually* said.
    *   **Delta:** A diff showing the safety improvements.
*   **UI Indicator:** The maco frontend should display a "Shield" icon or "Revised" badge when the Constitution has modified a response.

# The Architecture and Utility of coreason-constitution

### 1. The Philosophy (The Why)

In the rapidly evolving landscape of generative AI, the "Black Box" problem has shifted from "How does it work?" to "How do we govern it?". Traditional safety filters—often based on static blocklists or vague system prompts—are insufficient for high-stakes environments like Life Sciences (GxP) or Corporate Governance. They are passive, binary, and often silent.

`coreason-constitution` emerges as the "Judicial Branch" of the CoReason platform, aimed at solving this deficit through **Constitutional AI**. The author's motivation is clear: to move beyond mere "Safety" (preventing harm) to "Active Alignment" (enforcing specific principles). This package doesn't just ask an agent to be "nice"; it requires the agent to adhere to a strict, versioned set of Laws.

The core philosophy is **Active Intervention**. A violation shouldn't just result in a blocked request; it should trigger a **Critique-and-Revise Loop**. The system acts as an editor-in-chief, intercepting non-compliant "thoughts" and rewriting them before they reach the user. This "Code-as-Constitution" approach ensures that governance is deterministic, auditable, and separated from the generative logic itself.

### 2. Under the Hood (The Dependencies & logic)

A glance at the `REQUIREMENTS.MD` (or `pyproject.toml`) reveals a striking minimalism:
*   `pydantic`
*   `loguru`

Notable by its absence is any dependency on `openai`, `langchain`, or `transformers`. This is a deliberate architectural choice. `coreason-constitution` is **model-agnostic**. It defines the *structure* of governance, not the *engine*. By relying on `pydantic`, it ensures that every Law, Critique, and Trace is a strictly validated data object, not a loose dictionary.

The internal logic is built around four pillars:
1.  **The Legislative Archive:** A state manager that loads versioned "Laws" from JSON artifacts. It supports dynamic context, allowing different rules for "Clinical" vs "Marketing" domains.
2.  **The Sentinel:** A lightweight regex engine for immediate "Circuit Breaking." It handles high-velocity red lines (like jailbreaks) without the cost of an LLM call.
3.  **The Constitutional Judge:** An implementation of RLAIF (Reinforcement Learning from AI Feedback). It uses an injected `LLMClient` to evaluate draft content against the active laws, producing a structured `Critique`.
4.  **The Revision Engine:** The "Fixer." It takes a critique and the original draft, prompting the LLM to rewrite the content to be compliant.

This architecture enforces **Inversion of Control**. The consuming application provides the "Brain" (the LLM adapter), while this package provides the "Conscience" (the workflow and rules).

### 3. In Practice (The How)

The following examples demonstrate the package's utility in a Pythonic workflow.

**Defining the Law**
Laws are not strings; they are strict Pydantic objects. This allows for clear categorization and severity tracking.

```python
from coreason_constitution.schema import Law, LawCategory, LawSeverity

# Define a specific governance rule
gxp_law = Law(
    id="GCP.2.1",
    category=LawCategory.DOMAIN,
    text="Claims regarding dosage must be supported by clinical trial evidence.",
    severity=LawSeverity.HIGH,
    tags=["GxP", "Clinical"]
)
```

**The Plug-and-Play Judge**
The system requires you to bring your own LLM adapter by implementing the `LLMClient` interface. This decoupling makes the system testable and future-proof.

```python
from typing import List, Dict, Type, Any
from coreason_constitution.interfaces import LLMClient
from pydantic import BaseModel

class MyOpenAIClient(LLMClient):
    def chat_completion(self, messages: List[Dict[str, str]], model: str, **kwargs) -> str:
        # Call your vendor here (e.g., openai.chat.completions.create)
        return "Revised content based on compliance..."

    def structured_output(self, messages: List[Dict[str, str]], response_model: Type[BaseModel], **kwargs) -> Any:
        # Use simple prompting or tool-calling to get JSON back
        # For this example, we return a dummy critique
        return response_model(
            violation=True,
            article_id="GCP.2.1",
            reasoning="Dosage claim lacks citation."
        )
```

**The Active Correction**
The `ConstitutionalSystem` orchestrates the full lifecycle: Sentinel Check -> Judge -> Revision.

```python
from coreason_constitution.core import ConstitutionalSystem
from coreason_constitution.archive import LegislativeArchive
from coreason_constitution.judge import ConstitutionalJudge
from coreason_constitution.revision import RevisionEngine
from coreason_constitution.sentinel import Sentinel

# 1. Setup the wiring
client = MyOpenAIClient()
archive = LegislativeArchive()
archive.load_defaults()

system = ConstitutionalSystem(
    archive=archive,
    sentinel=Sentinel(rules=archive.get_sentinel_rules()),
    judge=ConstitutionalJudge(llm_client=client),
    revision_engine=RevisionEngine(llm_client=client)
)

# 2. Run the Compliance Cycle
trace = system.run_compliance_cycle(
    input_prompt="What is the recommended dosage?",
    draft_response="I feel like 500mg is probably fine.", # A "hunch" violation
    context_tags=["GxP"]
)

# 3. Inspect the active intervention
if trace.status == "REVISED":
    print(f"Original: {trace.input_draft}")
    print(f"Critique: {trace.critique.reasoning}")
    print(f"Revised:  {trace.revised_output}")
    # Output: "The recommended dosage must be verified against current clinical guidelines..."
```

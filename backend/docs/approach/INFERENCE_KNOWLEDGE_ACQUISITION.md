# Inference-Based Knowledge Acquisition in Memory Graph Systems

> A design discussion on how an agent can actively build, validate, and refine its memory graph through conversational inference.

---

## 1. Context: The Memory Model

The underlying memory model decomposes experiences into typed nodes within a graph database:

- **Environment** — contextual backdrop of a situation (where, when, who, what state, emotional valence)
- **Problem** — the challenge or trigger that initiated the memory
- **Solution** — what was done in response
- **Mechanic** — a prospective hypothesis of *how and why* the solution should resolve the problem
- **Result** — the outcome of applying the solution
- **Reflection** — a retrospective evaluation comparing the Mechanic prediction against the actual Result

Not all elements are required for every memory. Nodes of the same type live in shared vector spaces and can be merged at high similarity, enabling concept reuse and abstraction. The graph evolves over time as new memories are added and concepts converge.

---

## 2. Learning from Inference — The Query-as-Memory-Construction Loop

When a user poses a question, the agent should treat the interaction not merely as retrieval but as an opportunity to **construct new memory nodes collaboratively**.

### Flow

```
User query
    │
    ▼
Embed query → search nearest Environment + Problem nodes
    │
    ├── High confidence match → retrieve Solution + Mechanic candidates
    │
    └── Low confidence match → ask followup questions to narrow Environment
                                        │
                                        ▼
                              Present candidate Solutions + Mechanics
                                        │
                                        ▼
                          "Did this apply? What was the result?"
                                        │
                                        ▼
                              Store Result node + optional Reflection node
```

### Key Principle

The conversation itself is structured as a memory. Dialogue is not just retrieval — it is **collaborative node construction**. Every successfully resolved query enriches the graph with at least a Result, and ideally a Reflection.

---

## 3. Proactive Questioning — The Agent Building Memories Opportunistically

When a concept appears in conversation that has **low graph density** (few connections, no Reflection, unconfirmed Mechanics), the agent should flag it as a knowledge gap and probe it contextually.

### Triggers for Proactive Questions

| Graph Condition | Meaning |
|---|---|
| Node with no Result or Reflection | Outcome unknown |
| Mechanic with no co-occurrence confirmation | Untested hypothesis |
| Environment referenced by only one memory | Possibly unique, possibly underexplored |
| Problem node with no linked Solution | Open problem |

### Question Types by Missing Element

| Missing Element | Example Proactive Question |
|---|---|
| Result | "How did that turn out for you?" |
| Reflection | "Looking back, do you think that approach was correct?" |
| Mechanic | "Why do you think that solution worked?" |
| Environment links | "Was this a recurring situation or a one-off?" |

### Timing Constraint

Proactive questioning should be **sparse and contextually timed** — woven into conversation when a topic resurfaces naturally. Immediate interrogation after a user statement feels invasive; revisiting it when the topic reappears feels attentive.

---

## 4. Challenging User Inputs — Epistemic Integrity

The agent should operate on **provisional acceptance with active verification**. It stores what it is told, but annotates confidence, flags contradictions, and treats every Result or Reflection as an update opportunity.

### Contradiction Detection Signals

- **Internal graph conflict** — same Problem + same Solution but contradicting Mechanics
- **Low plausibility score** — new claim incoherent with existing graph structure (LLM-evaluated)
- **External knowledge conflict** — claim contradicts well-established factual or causal knowledge
- **Confidence decay** — unverified, single-source nodes lose confidence over time without reinforcement

### Epistemic Posture

The agent should **never silently merge a conflicting claim** into high-confidence structure. The conflict itself is valuable data, stored as a `CONTRADICTS` relation with both sides preserved until evidence resolves it.

---

## 5. Confidence-Gated Acceptance Model

New claims are not accepted or rejected as binary decisions. Instead, they pass through a **staged acceptance pipeline** with an escalating burden of proof proportional to the degree of contradiction.

### Acceptance Pipeline

```
New claim arrives
    │
    ▼
Contradiction check against existing graph
    │
    ├── No conflict ──────────────────────────► Accept, store at baseline confidence
    │
    ├── Minor conflict ────────────────────────► Store provisionally, flag for clarification
    │
    └── Major conflict ────────────────────────► Enter challenge loop
                                                        │
                                          ┌─────────────┼──────────────┐
                                          ▼             ▼              ▼
                                   Environment     Explanation    Verification
                                    probing         request        request
```

### Three Resolution Paths

**Environment Probing** (most generous — tried first)
Search for a diverging Environment node that would make both claims simultaneously true in different contexts. If found, **fork the node** rather than resolving the contradiction — both claims survive under their respective environments, linked by a `CONTEXT_VARIANT_OF` relation. This preserves all knowledge without overwriting.

**Explanation Request**
If environments align and conflict persists, ask for the Mechanic behind the claim. A coherent new Mechanic is genuine new knowledge. An incoherent or circular one signals low reliability.

**Verification Request**
For factual or causal claims, request sources. Source weight hierarchy:
- Peer-reviewed / established knowledge → strong boost
- Repeated independent confirmation → boost
- Single user assertion → low baseline
- Insistence without reasoning → no boost; stubbornness flag

### Confidence Scoring Table

| Event | Confidence Effect |
|---|---|
| Single user assertion, unverified | Low baseline |
| Consistent with existing graph | Moderate boost |
| Explained with coherent Mechanic | Boost |
| Confirmed by external source | Strong boost |
| Reinforced by Result or Reflection | Strong boost |
| Contradicted by high-confidence node | Penalty |
| Contradicted, but Environment differs | Neutral — fork instead |
| User insists without explanation | No boost; stubbornness flag |

---

## 6. Persistent Disagreement — Quarantine State

If all three resolution paths are exhausted and conflict remains unresolved, the agent:

1. Stores the claim in a **quarantine state** — present and reachable, but flagged as `DISPUTED` with low confidence
2. Preserves its own counter-reasoning as an attached Reflection node
3. Remains open to future evidence — a confirming Result can retroactively promote confidence

The agent must never pretend the conflict does not exist, nor silently defer to the user to avoid friction. The `CONTRADICTS` relation between the two nodes represents a **known open question** in the knowledge graph.

---

## 7. Domain Specialization — The Empty Prior Case

When a user demonstrates deep expertise in a narrow domain where the agent holds little or no contradicting data, the challenge loop naturally yields quickly. An empty prior cannot block acceptance. The agent's skepticism is proportional to **how far the claim is from its own competence boundary**.

For experimentation, the acceptance thresholds could be made **user-configurable** — allowing the system to be tuned toward more or less skepticism depending on the use case (e.g. a research assistant vs. a fact-checking agent).

---

## 8. Summary of Key Design Principles

- **Conversation is memory construction** — every query-response cycle is an opportunity to build or enrich graph nodes
- **Proactive, not passive** — the agent notices knowledge gaps and probes them opportunistically
- **Provisional acceptance** — all new knowledge is annotated with confidence; nothing is silently treated as fact
- **Contradiction is data** — conflicts are stored as `CONTRADICTS` relations, not resolved by overwriting
- **Forking over merging** — when environments differ, fork nodes rather than collapse contradictions
- **Insistence ≠ evidence** — user persistence without reasoning never increases confidence
- **Quarantine, not rejection** — unresolvable claims are stored but flagged, remaining open to future revision
# Human Memory as a Graph: A Theoretical Model

## Overview

This document summarizes a theoretical framework for decomposing and representing human memories as nodes and relations in a graph database. The goal is to create a reusable, queryable, and self-organizing knowledge structure that mirrors how memories encode context, challenges, decisions, and outcomes.

---

## Core Concept Nodes

Each memory is represented not as a single record, but as a **cluster of typed nodes** connected by relations. Not all nodes are required — a valid memory may consist of only a subset of them.

| Node Type | Description |
|-----------|-------------|
| **Environment** | Contextual backdrop of the memory — where, when, who, emotional state, circumstances |
| **Problem** | The challenge or trigger that initiated action or attention |
| **Solution** | What was done in response to the problem |
| **Mechanic** | A prospective causal hypothesis — *how and why* the solution should resolve the problem |
| **Result** | The actual outcome that followed |
| **Reflection** | A retrospective evaluation of the mechanic against the result — what was learned, what would change |

The **Mechanic** is prospective ("I believe this will work because..."), while **Reflection** is retrospective ("here is what actually happened and what I now understand"). Together they form a learning loop.

---

## Graph Structure

### Memory as a Hyperedge

The "memory" itself functions as a lightweight container node or hyperedge that groups its constituent concept nodes. Relations between nodes are typed and directional:

```
Environment ──── Problem
      │               │
      └──── Solution ─┘
                │
             Mechanic
          (PREDICTS) ↓
             Result
          (EVALUATES) ↓
           Reflection
                │
        (new Environment)
```

### Temporal Chaining

Rather than mutating the Environment node after a Result is obtained, the Result **spawns or links to a new Environment node**, preserving history and enabling a temporal chain:

```
Env_1 → [Memory A] → Result → Env_2 → [Memory B] → Result → Env_3
```

`Env_2` may be shared as the starting point for multiple unrelated memories that happened to begin from the same context — this is where the graph structure pays off through convergence and divergence of paths.

### Cross-Memory Connections

Any concept node can be shared across multiple memories. Memories are naturally connected when they share the same Problem, Environment, Solution, or other node. This enables:

- Retrieval by analogy (find memories with a similar Problem)
- Pattern detection (recurring Solutions across different Environments)
- Divergence analysis (same Mechanic, different Results)

---

## Self-Organization via Vector Spaces

### Per-Type Embedding Spaces

Each concept type occupies its own dedicated vector space:

- Problem vectors
- Solution vectors
- Mechanic vectors
- Result vectors
- etc.

Keeping spaces separate is important because "similarity" has different meaning per type — similar Problems may share surface framing, while similar Mechanics share causal structure.

### Node Merging

When two nodes of the same type exceed a similarity threshold (measured by cosine distance), they are candidates for merging. The merged node inherits all relations from both originals, creating **automatic schema abstraction**:

- **Highly merged nodes** → abstract, general concepts (e.g. "resource scarcity problem")
- **Unmerged leaf nodes** → specific, episodic instances

This produces a natural concept hierarchy without manual taxonomy.

### Relevance Ranking

Nodes are ranked by a two-dimensional signal:

1. **Cosine distance** — semantic similarity
2. **Co-occurrence count** — how often a node appears across many memories

A node scoring high on both is a **core concept** — a load-bearing, frequently reused piece of the knowledge graph.

### Soft Merging (Recommended)

Rather than immediately collapsing similar nodes, a `SIMILAR_TO` relation with a weight is introduced first. Hard merging occurs only after the weight crosses a threshold or is confirmed by repeated co-occurrence. This approach:

- Preserves history during the consolidation process
- Allows merging to be reversed or adjusted
- Makes the similarity structure inspectable

### Instance Preservation

Merging is lossy by nature. To preserve the original episodic specificity, an `INSTANCE_OF` relation points from the merged abstract node back to the original nodes:

```
Abstract_Problem_Node
    ├── INSTANCE_OF ← Problem_Node_A (memory 1)
    └── INSTANCE_OF ← Problem_Node_B (memory 7)
```

---

## Key Relation Types

| Relation | From | To | Meaning |
|----------|------|----|---------|
| `HAS_PROBLEM` | Memory | Problem | Memory involves this challenge |
| `HAS_SOLUTION` | Memory | Solution | Memory applies this solution |
| `PREDICTS` | Mechanic | Result | Mechanic hypothesizes this outcome |
| `EVALUATES` | Reflection | Mechanic + Result | Reflection judges the prediction |
| `LEADS_TO` | Result | Environment | Result produces new context |
| `SIMILAR_TO` | Node | Node | Soft similarity link (weighted) |
| `INSTANCE_OF` | Concrete Node | Abstract Node | Episodic instance of merged concept |

---

## Retrieval

Given a new situation, the model supports retrieval by:

1. Embedding the new Environment and Problem into their respective vector spaces
2. Finding nearest neighbor nodes via cosine distance
3. Traversing the graph to retrieve Solutions, Mechanics, and Reflections from analogous past memories
4. Ranking candidates by co-occurrence weight

This is essentially **neural case-based reasoning** — the graph stores structured episodes and retrieval is driven by learned similarity.

---

## Open Questions

- **Merge threshold** — this is a critical hyperparameter, likely needing to be per-concept-type or dynamic based on graph density
- **Environment complexity** — Environment could itself be a subgraph for richer context representation, but this is deferred to avoid exponential complexity growth; a `REFERENCE` pointer to another memory subgraph is a possible opt-in escape hatch
- **Emotional valence** — currently embedded within Environment rather than as a standalone node type

---

*This model is a theoretical framework under active development. All structural decisions remain subject to revision.*
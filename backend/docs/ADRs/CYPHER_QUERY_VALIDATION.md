# 29. public facing site uses separate database
Date: 02.07.2026
## Status
02.07.2026 problem introduced
## Context
As the LLM will have direct access to the database we have to assure security measures around the agent to prevent it from malicious actions or security vulnerabilities.

### Requirements
1. Cypher validation has to protect against prompt-injection scenario
2. Cypher validation has to protect against SQL(Cypher)-injection
3. Has to check the syntax for correctness
4. Has to log any problems with the proposed query and immidiately stop the session/flow.

### Options

#### Option 1 – Execute Generated Cypher Directly (No Validation)

The LLM generates a Cypher query which is executed immediately against the database.

##### Advantages

* Very simple architecture.
* Lowest latency.
* No additional components.

##### Disadvantages

* Vulnerable to prompt injection.
* Vulnerable to Cypher injection.
* No syntax validation.
* No semantic validation.
* Dangerous for production.
* Cannot satisfy any of the listed requirements.

**Recommendation:** Reject.


#### Option 2 – Rule-based Cypher Validator

The LLM generates Cypher.

A validator parses the query and checks it against a predefined set of rules before execution.

Typical checks:

* only READ queries
* deny WRITE clauses
* deny APOC procedures
* deny CALL
* deny LOAD CSV
* deny dynamic execution
* whitelist labels
* whitelist relationships
* whitelist properties
* validate parameters
* maximum path length
* maximum LIMIT

Architecture

```
LLM
  │
Generated Cypher
  │
Rule Validator
  │
Approved?
  ├── No → Log + Abort
  └── Yes
        │
     Database
```

##### Advantages

* Deterministic
* Fast
* Easy to audit
* Good protection against prompt injection
* Good protection against Cypher injection

##### Disadvantages

* Rules require maintenance
* Difficult for very complex queries

---

#### Option 3 – AST-based Validation (Recommended)

Instead of validating text, parse Cypher into an Abstract Syntax Tree (AST).

Validation happens on the AST.

Checks include

* allowed clauses
* graph traversal depth
* variables
* procedures
* functions
* labels
* relationship types
* property access

Example

```
MATCH (u:User)
RETURN u.name
```

becomes

```
MATCH
 ├── Node(User)
 └── RETURN(name)
```

Only allowed AST nodes may exist.

Architecture

```
LLM
 │
Cypher
 │
Parser
 │
AST
 │
Policy Engine
 │
Approved?
 ├── No → Log + Abort
 └── Yes
      │
   Database
```

##### Advantages

* Immune to string manipulation tricks
* Strong syntax validation
* Strong semantic validation
* Easier to reason about
* Easy to extend

##### Disadvantages

* More implementation effort
* Requires a Cypher parser

---

#### Option 4 – LLM + Validator + Query Rewriter

The generated Cypher is automatically rewritten into a safe subset.

```
LLM
 │
Cypher
 │
Validator
 │
Rewriter
 │
Safe Cypher
 │
Database
```

Examples

```
DELETE
```

↓

```
Rejected
```

or

```
MATCH (n)
RETURN n
```

↓

```
MATCH (n)
RETURN n
LIMIT 100
```

##### Advantages

* Better user experience
* Can automatically fix mistakes
* Enforces organization standards

##### Disadvantages

* More complex
* Rewriter must be trusted

---

#### Option 5 – Database Proxy / Policy Enforcement Layer (Recommended for Enterprise)

The LLM never talks directly to the database.

Instead:

```
LLM
 │
Cypher
 │
Validation Service
 │
Policy Engine
 │
Database Proxy
 │
Neo4j
```

The proxy:

* validates syntax
* validates policy
* rewrites if necessary
* executes
* logs
* rate limits
* records audit trail

##### Advantages

* Centralized security
* Independent from LLM implementation
* Easy auditing
* Easy policy evolution
* Works for multiple agents

##### Disadvantages

* Additional infrastructure
* Higher latency

---

#### Option 6 – Restricted Query DSL

The LLM never generates Cypher.

Instead it produces a structured intermediate representation.

Example

```json
{
  "operation": "find_movies",
  "filters": {
    "year": 2024,
    "genre": "Drama"
  },
  "limit": 20
}
```

The backend generates Cypher.

```
LLM
 │
DSL
 │
Validator
 │
Cypher Generator
 │
Database
```

##### Advantages

* Eliminates Cypher injection
* Easier validation
* Easier testing
* Full control over generated queries

##### Disadvantages

* Less expressive
* Requires DSL design
* New features require DSL changes

---

### Comparison

| Option                | Prompt Injection | Cypher Injection | Syntax Validation | Audit | Complexity  |
| --------------------- | ---------------- | ---------------- | ----------------- | ----- | ----------- |
| Direct execution      | ❌                | ❌                | ❌                 | ❌     | Very Low    |
| Rule-based validator  | ✅                | ✅                | Partial           | ✅     | Low         |
| AST validation        | ✅                | ✅                | ✅                 | ✅     | Medium      |
| Validator + rewriter  | ✅                | ✅                | ✅                 | ✅     | Medium–High |
| Proxy / policy engine | ✅                | ✅                | ✅                 | ✅     | High        |
| Restricted DSL        | ✅                | ✅                | ✅                 | ✅     | High        |

### Recommended Decision

A strong production approach is to combine **Option 3 (AST-based validation)** with **Option 5 (database proxy/policy enforcement layer)**:

* The LLM submits Cypher to a dedicated validation service rather than directly to the database.
* The validation service parses the query into an AST and enforces security policies, including read-only restrictions, allowed labels/relationships/properties, parameter validation, query complexity limits, and prohibition of unsafe clauses (e.g., `CREATE`, `DELETE`, `MERGE`, `CALL`, `LOAD CSV`, unrestricted APOC procedures).
* Only validated queries are forwarded to the database using a minimally privileged, read-only database account.
* Any validation failure, syntax error, policy violation, or suspected prompt-injection attempt is logged with sufficient context for auditing, and the request is rejected immediately, terminating the current agent workflow.

This layered approach satisfies all four stated requirements while adhering to the defense-in-depth security principle.

## Decision
In current version of the application we don't give the LLM ability to build queries on its own BUT proper prompt injection may introduce embedded cypher code or remote code execution. For now, at the MVP stage we will focus on Rule-based validation with plan to move to AST Validation in future.
## Consequences
Less secure approach, especially if we want to enable full cypher generation for exploration tasks. Additional work on rulebased validation.
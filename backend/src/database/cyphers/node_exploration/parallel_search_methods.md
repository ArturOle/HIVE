#### PARALLEL SEMANTIC SEARCH  →  GRAPH-AWARE RE-RANKING  →  RESULT_OF RELATIONS

Re-ranking signals

1. Multi-branch membership - node appeared in ≥2 vector index searches
2. Cross-branch RESULT_OF  - node's RESULT_OF neighbour was found by a *different* branch (independent convergence)
3. Reciprocal Rank Fusion  - rank-position blend, immune to score-scale differences between indexes

All patterns assume Neo4j 5.x.  Drop `CYPHER runtime=parallel` on Community.


#### WEIGHT / PARAMETER GUIDE

RRF constant k (default 60)

- k=10  - top-rank wins dominate; risky if one index is noisy
- k=60  - standard; balanced across all rank positions
- k=120 - flatter distribution; better when all results are roughly equal

Multi-branch bonus  (c.branchCount - 1) * W

- W=0.0  - pure score/RRF, no membership bonus
- W=0.2  - 20% boost per extra branch  (recommended start)
- W=0.5  - strong: a 3-branch hit scores 2× a 1-branch hit

Cross-branch link bonus  crossBranchLinks * W

- W=0.0  - graph topology ignored
- W=0.4  - each cross-branch RESULT_OF neighbour adds 40%
- W=1.0  - aggressive; one link doubles the score

Directionality of RESULT_OF match

`(node)-[:RESULT_OF]->(neighbor)  → outbound only (node IS the source)`
`(node)<-[:RESULT_OF]-(neighbor)  → inbound only  (node IS the result)`
`(node)-[:RESULT_OF]-(neighbor)   → bidirectional (any connection counts)`


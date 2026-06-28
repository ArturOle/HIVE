// =============================================================================
//  PARALLEL SEMANTIC SEARCH  →  GRAPH-AWARE RE-RANKING  →  RESULT_OF RELATIONS
// =============================================================================
//
//  Re-ranking signals
//  ──────────────────
//  (1) Multi-branch membership  : node appeared in ≥2 vector index searches
//  (2) Cross-branch RESULT_OF   : node's RESULT_OF neighbour was found by a
//                                  *different* branch — independent convergence
//  (3) Reciprocal Rank Fusion   : rank-position blend, immune to score-scale
//                                  differences between indexes
//
//  All patterns assume Neo4j 5.x.  Drop `CYPHER runtime=parallel` on Community.
// =============================================================================


// ─────────────────────────────────────────────────────────────────────────────
//  PATTERN B — Reciprocal Rank Fusion (RRF)
//  Best when index scores are NOT on the same scale (cosine vs dot-product
//  vs BM25).  Only ranks matter, not raw scores.
// ─────────────────────────────────────────────────────────────────────────────

CYPHER runtime=parallel

// ── 1. COLLECT RANKED LISTS PER BRANCH ──────────────────────────────────────
CALL {
  CALL db.index.vector.queryNodes('embedding_index_a', 20, $vectorA)
  YIELD node, score
  WITH node, score ORDER BY score DESC
  RETURN collect(node) AS listA
}
CALL {
  CALL db.index.vector.queryNodes('embedding_index_b', 20, $vectorB)
  YIELD node, score
  WITH node, score ORDER BY score DESC
  RETURN collect(node) AS listB
}
CALL {
  CALL db.index.vector.queryNodes('embedding_index_c', 20, $vectorC)
  YIELD node, score
  WITH node, score ORDER BY score DESC
  RETURN collect(node) AS listC
}

// ── 2. ASSIGN RANK POSITIONS ─────────────────────────────────────────────────
// Build [{node, rank, branch}] arrays from each ranked list.
WITH
  [i IN range(0, size(listA)-1) | {node: listA[i], rank: i+1, branch: 'A'}] AS rankedA,
  [i IN range(0, size(listB)-1) | {node: listB[i], rank: i+1, branch: 'B'}] AS rankedB,
  [i IN range(0, size(listC)-1) | {node: listC[i], rank: i+1, branch: 'C'}] AS rankedC

WITH rankedA + rankedB + rankedC AS allRanked

// ── 3. RRF FUSION (k = 60 is standard; lower k rewards top-rank hits more) ──
UNWIND allRanked AS entry
WITH entry.node AS node, entry.branch AS branch, entry.rank AS rank

WITH node,
     collect({branch: branch, rank: rank}) AS rankEntries,
     // RRF formula:  score = Σ  1 / (k + rank_i)
     sum(1.0 / (60 + rank))    AS rrfScore,
     count(*)                  AS branchCount

// ── 4. RETURN RESULT_OF RELATIONS ────────────────────────────────────────────
MATCH (node)-[r:RESULT_OF]->(result)

RETURN
  node,
  r              AS relation,
  result,
  rrfScore,
  branchCount,
  rankEntries    // [{branch:'A',rank:3}, {branch:'C',rank:7}] — for debugging
ORDER BY rrfScore DESC
LIMIT 30;


// =============================================================================
//  WEIGHT / PARAMETER GUIDE
// =============================================================================
//
//  RRF constant k (default 60)
//  ───────────────────────────
//  k=10  → top-rank wins dominate; risky if one index is noisy
//  k=60  → standard; balanced across all rank positions
//  k=120 → flatter distribution; better when all results are roughly equal
//
//  Multi-branch bonus  (c.branchCount - 1) * W
//  ─────────────────────────────────────────────
//  W=0.0  → pure score/RRF, no membership bonus
//  W=0.2  → 20% boost per extra branch  (recommended start)
//  W=0.5  → strong: a 3-branch hit scores 2× a 1-branch hit
//
//  Cross-branch link bonus  crossBranchLinks * W
//  ───────────────────────────────────────────────
//  W=0.0  → graph topology ignored
//  W=0.4  → each cross-branch RESULT_OF neighbour adds 40%
//  W=1.0  → aggressive; one link doubles the score
//
//  Directionality of RESULT_OF match
//  ───────────────────────────────────
//  (node)-[:RESULT_OF]->(neighbor)  → outbound only (node IS the source)
//  (node)<-[:RESULT_OF]-(neighbor)  → inbound only  (node IS the result)
//  (node)-[:RESULT_OF]-(neighbor)   → bidirectional (any connection counts)
// =============================================================================

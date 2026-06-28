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
//  PATTERN A — Cross-branch RESULT_OF boost
//  Best when you want an interpretable multiplier per extra cross-branch link.
// ─────────────────────────────────────────────────────────────────────────────

CYPHER runtime=parallel

// ── 1. PARALLEL SEARCHES (tag each hit with its branch) ──────────────────────
CALL {
  CALL db.index.vector.queryNodes('embedding_index_a', 20, $vectorA)
  YIELD node, score
  RETURN node, score, 'A' AS branch

  UNION ALL

  CALL db.index.vector.queryNodes('embedding_index_b', 20, $vectorB)
  YIELD node, score
  RETURN node, score, 'B' AS branch

  UNION ALL

  CALL db.index.vector.queryNodes('embedding_index_c', 20, $vectorC)
  YIELD node, score
  RETURN node, score, 'C' AS branch
}

// ── 2. AGGREGATE PER NODE ────────────────────────────────────────────────────
// A node appearing in multiple branches already gets a head-start.
WITH node,
     collect(branch)  AS hitBranches,   // e.g. ['A','C']
     max(score)       AS baseScore,
     count(*)         AS branchCount    // 1, 2, or 3

// Materialise candidate set so we can do cross-lookup below.
WITH collect({
       node:        node,
       hitBranches: hitBranches,
       baseScore:   baseScore,
       branchCount: branchCount
     }) AS candidates

// ── 3. CROSS-BRANCH RESULT_OF CHECK ─────────────────────────────────────────
// For each candidate, count RESULT_OF neighbours that:
//   (a) are also in the candidate set  AND
//   (b) arrived from at least one branch THIS node did NOT appear in.
// Both (inbound and outbound) directions are checked.
UNWIND candidates AS c
WITH c, [x IN candidates | x.node] AS candidateNodes, candidates

OPTIONAL MATCH (c.node)-[:RESULT_OF]-(neighbor)   // bidirectional
WHERE neighbor IN candidateNodes
  AND any(other IN candidates
          WHERE other.node = neighbor
            AND any(b IN other.hitBranches WHERE NOT b IN c.hitBranches))

WITH c, count(DISTINCT neighbor) AS crossBranchLinks

// ── 4. RE-RANK ───────────────────────────────────────────────────────────────
// Tunable weights:
//   multiBranchBonus   : 20% per extra branch the node appeared in
//   crossLinkBonus     : 40% per cross-branch RESULT_OF neighbour
WITH c.node        AS node,
     c.baseScore   AS baseScore,
     c.branchCount AS branchCount,
     c.hitBranches AS hitBranches,
     crossBranchLinks,
     c.baseScore
       * (1.0 + (c.branchCount - 1) * 0.20)   // multi-branch membership bonus
       * (1.0 + crossBranchLinks     * 0.40)   // cross-branch link bonus
     AS rerankedScore

// ── 5. RETURN RESULT_OF RELATIONS ────────────────────────────────────────────
MATCH (node)-[r:RESULT_OF]->(result)

RETURN
  node,
  r                   AS relation,
  result,
  baseScore,
  branchCount,
  hitBranches,
  crossBranchLinks,
  rerankedScore
ORDER BY rerankedScore DESC
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

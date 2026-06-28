
// ─────────────────────────────────────────────────────────────────────────────
//  PATTERN C — RRF  +  cross-branch RESULT_OF boost  (combined)
//  The most powerful option: rank-fusion as the base, graph signal as a boost.
// ─────────────────────────────────────────────────────────────────────────────

CYPHER runtime=parallel

CALL {
  CALL db.index.vector.queryNodes('embedding_index_a', 20, $vectorA)
  YIELD node, score
  WITH node, score ORDER BY score DESC
  RETURN collect({node: node, branch: 'A'}) AS listA,
         collect(node) AS nodesA
}
CALL {
  CALL db.index.vector.queryNodes('embedding_index_b', 20, $vectorB)
  YIELD node, score
  WITH node, score ORDER BY score DESC
  RETURN collect({node: node, branch: 'B'}) AS listB,
         collect(node) AS nodesB
}
CALL {
  CALL db.index.vector.queryNodes('embedding_index_c', 20, $vectorC)
  YIELD node, score
  WITH node, score ORDER BY score DESC
  RETURN collect({node: node, branch: 'C'}) AS listC,
         collect(node) AS nodesC
}

// Build ranked entries with branch tags
WITH
  [i IN range(0, size(listA)-1) | {node: listA[i].node, rank: i+1, branch: 'A'}] AS rankedA,
  [i IN range(0, size(listB)-1) | {node: listB[i].node, rank: i+1, branch: 'B'}] AS rankedB,
  [i IN range(0, size(listC)-1) | {node: listC[i].node, rank: i+1, branch: 'C'}] AS rankedC,
  nodesA, nodesB, nodesC,
  nodesA + nodesB + nodesC AS allCandidateNodes

WITH rankedA + rankedB + rankedC AS allRanked, allCandidateNodes, nodesA, nodesB, nodesC

UNWIND allRanked AS entry
WITH entry.node   AS node,
     entry.rank   AS rank,
     entry.branch AS branch,
     allCandidateNodes, nodesA, nodesB, nodesC

WITH node,
     collect({branch: branch, rank: rank}) AS rankEntries,
     sum(1.0 / (60 + rank))               AS rrfScore,
     collect(DISTINCT branch)              AS hitBranches,
     count(*)                              AS branchCount,
     allCandidateNodes, nodesA, nodesB, nodesC

// Cross-branch RESULT_OF check
// A link boosts the score when it bridges nodes from different branch sets.
OPTIONAL MATCH (node)-[:RESULT_OF]-(neighbor)
WHERE neighbor IN allCandidateNodes
  AND (
    // node is in A, neighbor is in B or C
    (node IN nodesA AND (neighbor IN nodesB OR neighbor IN nodesC))
    OR
    // node is in B, neighbor is in A or C
    (node IN nodesB AND (neighbor IN nodesA OR neighbor IN nodesC))
    OR
    // node is in C, neighbor is in A or B
    (node IN nodesC AND (neighbor IN nodesA OR neighbor IN nodesB))
  )

WITH node, rrfScore, branchCount, hitBranches, rankEntries,
     count(DISTINCT neighbor) AS crossBranchLinks,
     // Final score = RRF base × graph connectivity multiplier
     rrfScore * (1.0 + crossBranchLinks * 0.5) AS finalScore

MATCH (node)-[r:RESULT_OF]->(result)

RETURN
  node,
  r                AS relation,
  result,
  round(rrfScore * 10000) / 10000   AS rrfScore,
  crossBranchLinks,
  branchCount,
  hitBranches,
  round(finalScore * 10000) / 10000 AS finalScore
ORDER BY finalScore DESC
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

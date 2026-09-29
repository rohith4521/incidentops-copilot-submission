# Engineering Decision Records

## ADR-001 — Hindsight is the memory boundary

**Decision:** Keep historical incident memory behind the Hindsight integration rather than recreating a second local memory implementation.

**Reason:** The project is specifically demonstrating persistent operational memory. A separate ad-hoc memory store would obscure the central product behavior.

---

## ADR-002 — Retrieval is not trust

**Decision:** Separate retrieval, relevance, trust, and verification.

**Reason:** Semantic similarity is not equivalent to operational correctness. Decoy memories must remain inspectable without becoming trusted evidence.

---

## ADR-003 — Human approval before controlled action

**Decision:** Runbook recommendations remain pending until an explicit approval state is reached.

**Reason:** Incident automation should assist an operator without silently converting model output into production action.

---

## ADR-004 — Degrade visibly

**Decision:** Memory failures produce explicit degraded behavior rather than fabricated recall.

**Reason:** A missing memory result and a successful empty search are different operational states.

---

## ADR-005 — Prefer defensible metrics

**Decision:** Documentation reports verified test results and reproducible evaluation artifacts instead of invented business outcomes.

**Reason:** A competition repository should make it easy to distinguish implementation evidence from future production hypotheses.

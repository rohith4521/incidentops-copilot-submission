"""Failure-Mode-Aware Relevance Scorer for IncidentOps Memory Recall.

Prevents false historical retrieval on lookalike and decoy alerts by:
1. Stripping generic operational SRE stopwords with low discriminative value.
2. Extracting concrete technical tokens, exception classes, and error codes.
3. Categorizing technical failure domains to detect domain conflicts.
4. Enforcing the invariant: A service match alone must NEVER produce HIGH relevance.
5. High relevance strictly requires concrete failure-mode alignment.
"""

import re
from typing import Dict, List, Set, Tuple
from app.models.alert import AlertPayload
from app.models.memory import IncidentMemoryItem, MatchStrength

# Generic operational words with low or zero discriminative failure-mode value
GENERIC_SRE_STOPWORDS: Set[str] = {
    "error", "errors", "failure", "failures", "failed", "failing",
    "issue", "issues", "problem", "problems", "bug", "bugs",
    "service", "services", "system", "systems", "component", "components",
    "client", "clients", "server", "servers", "host", "hosts", "node", "nodes", "pod", "pods",
    "instance", "instances", "replica", "replicas", "cluster", "environment", "production",
    "staging", "status", "condition", "state", "alert", "alerts",
    "timeout", "timeouts", "timing", "latency", "spiked", "spiking", "spike", "spikes",
    "surge", "surging", "increased", "increasing", "increase", "degraded", "degradation",
    "degrading", "drop", "dropped", "dropping", "high", "low", "critical", "medium",
    "elevated", "severe", "abnormal", "observed", "exceeded", "exceeding",
    "threshold", "breached", "breaching", "request", "requests", "response", "responses",
    "traffic", "load", "rate", "rates", "count", "counts", "limit", "limits",
    "percentage", "ratio", "event", "events", "metric", "metrics", "logs", "logging", "logged",
    "during", "under", "across", "within", "between", "before", "after", "causing", "caused",
    "cause", "causes", "without", "with", "from", "into", "onto", "than", "then", "over",
    "past", "more", "most", "such", "also", "found", "detected", "identifying", "identified",
    "trigger", "triggered", "triggering", "call", "calling", "calls", "invoking", "invocation",
    "reached", "reaching", "hitting", "hit", "occurring", "occurred", "indicating", "indicates",
    "suggest", "suggests", "report", "reported", "reporting", "level", "levels", "mode", "modes",
    "type", "types", "case", "cases", "run", "running", "app", "application", "routine",
    "operation", "flow", "workflow", "process", "processes", "backend", "frontend", "internal",
    "external", "inbound", "outbound", "edge", "total", "default", "number", "seconds", "minutes", "hours",
    "primary", "secondary", "target", "active", "attempt", "attempts", "recent", "normal",
    "continuous", "completely", "immediate", "prior", "prior_incidents", "multiple", "single",
    "warning", "notice", "info", "debug", "trace", "exception", "exceptions",
    "incident", "incidents", "generic", "monitor", "monitoring", "monitored",
    "investigate", "investigation", "analysis", "behavior", "baseline", "unusual",
    # Conjunctions, prepositions, generic verbs, and generic runtime nouns
    "and", "or", "nor", "not", "but", "for", "about", "against", "through",
    "loop", "loops", "worker", "workers", "thread", "threads", "task", "tasks", "job", "jobs",
    "handler", "handlers", "queue", "queues", "connection", "connections",
    "record", "records", "message", "messages", "payload", "payloads", "data", "value", "values", "key", "keys", "item", "items",
    "read", "reads", "reading", "write", "writes", "writing", "get", "gets", "post", "put", "delete",
    "send", "sent", "receive", "received", "wait", "waiting", "block", "blocked", "blocking",
    "stop", "stopped", "stopping", "start", "started", "starting", "pass", "passed", "passing",
    "database", "databases", "db", "dbs", "back", "forward", "up", "down", "http", "https",
}

# Technical failure domains used for cross-domain conflict detection
FAILURE_DOMAINS: Dict[str, Set[str]] = {
    "security_tls": {
        "x509", "certificate", "ssl", "tls", "handshake", "truststore",
        "keystore", "8443", "sslhandshakeexception", "x509certificateexpiredexception",
        "mtls", "sasl_ssl", "certificate_unknown",
    },
    "db_locking": {
        "deadlock", "deadlocks", "40p01", "rowlock", "exclusivelock", "cyclic",
        "order_ledger", "inventory_items", "pg_stat_activity", "lock_wait",
        "lock_queue", "transaction_deadlock",
    },
    "storage_disk": {
        "disk space", "pg_wal", "wal", "xlog", "disk full", "device",
        "archiver", "archiving", "no space left", "data_parts", "max_parts",
    },
    "cache_memory_eviction": {
        "maxmemory", "noeviction", "volatile-lru", "volatile_lru", "eviction",
        "blacklist", "revocation", "caffeine", "heap leak", "oomkilled",
        "137", "unbounded_cache", "cgroup memory", "memory leak",
    },
    "consensus_quorum": {
        "sentinel quorum", "sentinel partition", "split-brain", "split_brain",
        "master epoch", "noreachablemasterexception", "raft", "leader election",
        "quorum loss", "requorum", "sentinel cluster", "quorum",
    },
    "messaging_poison_pill": {
        "avro", "deserialization", "recorddeserializationexception", "poison pill",
        "magic byte", "dlq", "dead letter", "offset trap", "poison record",
    },
    "connection_pool": {
        "connection pool", "pool wait", "redisconnectionclosedexception",
        "redis_pool_wait_duration_seconds", "thread pool starvation",
        "connect timeout", "circuit breaker", "circuit_breaker", "egress timeout",
        "socket timeout", "stripe", "idle connection", "pool_starvation", "pool exhaustion",
        "hikari",
    },
    "algorithmic_cpu": {
        "redos", "regex", "backtracking", "exponential", "pattern matcher",
        "catastrophic_backtracking", "pattern$loop", "catastrophic backtracking",
        "unanchored quantifier",
    },
    "clock_sync": {
        "ntp", "clock drift", "clock skew", "clock desync", "stratum", "nbf",
        "pool.ntp.org", "time desync", "clock desynchronization",
    },
}

# Generic infrastructure stack tokens that identify common components/protocols
# rather than specific operational failure modes.
INFRASTRUCTURE_STACK_TOKENS: Set[str] = {
    "redis", "jwt", "kafka", "postgres", "postgresql", "mysql", "clickhouse",
    "mongo", "mongodb", "elasticsearch", "rabbitmq", "sqs",
}


def extract_negated_terms(text: str) -> Set[str]:
    """Extract terms within negated clauses (e.g. 'without deserialization errors', 'no deadlocks')."""
    if not text:
        return set()
    negated: Set[str] = set()
    patterns = [
        r"\b(?:without|no|zero|free of|excluding|absence of|neither)\s+([^,;\.\n]+?)(?=(?:\s+(?:and|or|with|but|while)\b)|[,;\.\n]|$)",
    ]
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            phrase = m.group(1).lower()
            for w in re.findall(r"[a-zA-Z0-9_\-\.\:]+", phrase):
                if len(w) >= 2:
                    negated.add(w)
    return negated


def extract_technical_tokens(text: str, is_alert: bool = False) -> Set[str]:
    """Extract normalized technical terms, compound identifiers, and error codes."""
    if not text:
        return set()

    negated = extract_negated_terms(text) if is_alert else set()
    text_lower = text.lower()
    raw_words = re.findall(r"[a-zA-Z0-9_\-\.\:]+", text_lower)
    tokens: Set[str] = set()

    for w in raw_words:
        clean = w.strip(".,;:\"'()[]{}")
        if not clean or clean in GENERIC_SRE_STOPWORDS:
            continue
        if is_alert and clean in negated:
            continue

        # Keep valid error codes (e.g. 40p01, 504, 503, 137, 429) or non-numeric tokens >= 3 chars
        is_known_code = clean in {"40p01", "504", "503", "502", "500", "137", "429", "8443", "9093"}
        if is_known_code or (len(clean) >= 3 and not clean.isdigit()):
            tokens.add(clean)

            # Split compound terms (e.g. pg_wal, circuit-breaker, thread_pool)
            subparts = re.split(r"[-_:\.]", clean)
            if len(subparts) > 1:
                for sp in subparts:
                    if (sp in {"wal", "pg", "xlog", "dlq", "oom", "jwt", "tls", "ssl", "504", "503"} or len(sp) >= 3) and sp not in GENERIC_SRE_STOPWORDS and not sp.isdigit():
                        if not (is_alert and sp in negated):
                            tokens.add(sp)

    # Extract specific technical bi-grams if present in text
    KEY_BIGRAMS = [
        "circuit breaker", "thread pool", "connection pool", "socket timeout",
        "poison pill", "magic byte", "dead letter", "disk full", "disk space",
        "split brain", "master epoch", "maxmemory ceiling", "eviction policy",
        "token cache", "heap leak", "exclusive lock", "lock wait", "lock queue",
        "regex backtracking", "coupon validation", "wal archiver", "cgroup memory",
    ]
    for bg in KEY_BIGRAMS:
        if bg in text_lower:
            if not (is_alert and any(w in negated for w in bg.split())):
                tokens.add(bg)

    return tokens


def classify_failure_domains(tokens: Set[str], text: str, is_alert: bool = False) -> Set[str]:
    """Identify broad failure domains to detect mutually exclusive failure modes using word boundaries."""
    negated = extract_negated_terms(text) if is_alert else set()
    text_lower = text.lower()
    matched_domains: Set[str] = set()

    for domain, domain_indicators in FAILURE_DOMAINS.items():
        for indicator in domain_indicators:
            if is_alert and any(w in negated for w in indicator.split()):
                continue
            if indicator in tokens:
                matched_domains.add(domain)
                break
            # Word-boundary regex check prevents partial substring collisions (e.g. 'raft' in 'crafted')
            pattern = r"\b" + re.escape(indicator) + r"\b"
            if re.search(pattern, text_lower):
                matched_domains.add(domain)
                break

    return matched_domains


class RelevanceScoreResult:
    """Detailed relevance evaluation outcome for a single candidate memory item."""

    def __init__(
        self,
        candidate_id: str,
        service: str,
        match_strength: MatchStrength,
        verdict: str,
        is_accepted: bool,
        overlap_tokens: Set[str],
        alert_domains: Set[str],
        candidate_domains: Set[str],
        reason: str,
        evidence_bullets: List[str],
    ):
        self.candidate_id = candidate_id
        self.service = service
        self.match_strength = match_strength
        self.verdict = verdict
        self.is_accepted = is_accepted
        self.overlap_tokens = overlap_tokens
        self.alert_domains = alert_domains
        self.candidate_domains = candidate_domains
        self.reason = reason
        self.evidence_bullets = evidence_bullets


def score_candidate_relevance(
    alert: AlertPayload,
    candidate: IncidentMemoryItem,
) -> RelevanceScoreResult:
    """Evaluate whether candidate historical incident represents the same failure mode."""
    from app.services.provenance_service import provenance_service

    cand_id = candidate.incident_id or candidate.id
    cand_service = candidate.service or "unknown-service"

    alert_text = f"{alert.title} {alert.description} {' '.join(alert.symptoms)}"
    cand_text = f"{candidate.title or ''} {candidate.alert_signature or ''} {candidate.root_cause or ''} {candidate.resolution or ''} {' '.join(candidate.symptoms)} {' '.join(candidate.tags)} {candidate.raw_text}"

    alert_tokens = extract_technical_tokens(alert_text, is_alert=True)
    cand_tokens = extract_technical_tokens(cand_text, is_alert=False)

    # Calculate raw token overlap excluding generic stopwords
    raw_overlap = alert_tokens & cand_tokens

    # Remove tokens originating purely from service names and generic infrastructure stacks
    # to prevent service and technology names alone from acting as failure-mode evidence
    service_tokens = extract_technical_tokens(alert.service or "") | extract_technical_tokens(candidate.service or "")
    overlap = (raw_overlap - service_tokens) - INFRASTRUCTURE_STACK_TOKENS

    # Detect broad failure domains (using primary incident definition for candidate to avoid resolution step pollution)
    cand_primary_text = f"{candidate.title or ''} {candidate.alert_signature or ''} {candidate.root_cause or ''} {' '.join(candidate.symptoms)}"
    alert_domains = classify_failure_domains(alert_tokens, alert_text, is_alert=True)
    cand_domains = classify_failure_domains(cand_tokens, cand_primary_text, is_alert=False)

    # Domain conflict occurs when both sides identify domains, but there is zero domain overlap
    domain_conflict = bool(alert_domains and cand_domains and not (alert_domains & cand_domains))

    # Service matching
    service_match = bool(
        candidate.service
        and alert.service
        and candidate.service.strip().lower() == alert.service.strip().lower()
    )

    evidence_bullets: List[str] = []

    # Case 0: Provenance Check — Only VERIFIED memories may provide historical precedent
    # Unverified / AI drafts are rejected from trusted precedent to prevent unverified content from escalating
    if not provenance_service.is_trusted(candidate):
        from app.services.metrics_service import metrics_service
        metrics_service.inc_rejected_untrusted_memory_count()
        reason = (
            f"Candidate {cand_id} ({cand_service}) rejected by provenance gate: "
            f"memory status is '{candidate.memory_status.value if hasattr(candidate.memory_status, 'value') else candidate.memory_status}' "
            f"(source: '{candidate.source_type.value if hasattr(candidate.source_type, 'value') else candidate.source_type}'). "
            "Only human-verified post-mortems may provide trusted historical precedent."
        )
        evidence_bullets = [
            f"Hindsight retrieved candidate {cand_id} for service '{alert.service}', but memory provenance gate rejected it.",
            f"Provenance check failed: candidate is an unverified {candidate.memory_status.value if hasattr(candidate.memory_status, 'value') else candidate.memory_status} draft (verified_by={candidate.verified_by or 'None'}).",
            "Categorical Decision: NONE (Unverified AI draft cannot act as trusted precedent). Executing first-principles triage.",
        ]
        return RelevanceScoreResult(
            candidate_id=cand_id,
            service=cand_service,
            match_strength=MatchStrength.NONE,
            verdict="REJECTED_UNVERIFIED_DRAFT_MEMORY",
            is_accepted=False,
            overlap_tokens=overlap,
            alert_domains=alert_domains,
            candidate_domains=cand_domains,
            reason=reason,
            evidence_bullets=evidence_bullets,
        )

    # Case 1: Failure Domain Conflict (Lookalike/Decoy rejection)
    if domain_conflict:
        reason = (
            f"Candidate {cand_id} ({cand_service}) rejected: failure domain conflict. "
            f"Alert indicates '{', '.join(sorted(alert_domains))}' whereas candidate documents '{', '.join(sorted(cand_domains))}'."
        )
        evidence_bullets = [
            f"Hindsight retrieved candidate {cand_id} for service '{alert.service}', but failure-mode relevance gate rejected it.",
            f"Failure mode divergence: alert reflects [{', '.join(sorted(alert_domains))}]; historical incident reflects [{', '.join(sorted(cand_domains))}].",
            "Categorical Decision: NONE (Unrelated failure mode on same microservice). Executing first-principles triage.",
        ]
        return RelevanceScoreResult(
            candidate_id=cand_id,
            service=cand_service,
            match_strength=MatchStrength.NONE,
            verdict="REJECTED_DIFFERENT_FAILURE_MODE",
            is_accepted=False,
            overlap_tokens=overlap,
            alert_domains=alert_domains,
            candidate_domains=cand_domains,
            reason=reason,
            evidence_bullets=evidence_bullets,
        )

    # Case 2: Service match with strong failure-mode alignment (>= 2 technical tokens & no conflict)
    if service_match and len(overlap) >= 2:
        top_tokens = sorted(list(overlap))[:5]
        reason = f"Accepted: service '{alert.service}' matches and failure mode aligns on [{', '.join(top_tokens)}]."
        evidence_bullets = [
            f"High correlation: Both target service '{alert.service}' and concrete failure mode align with historical incident {cand_id}.",
            f"Verifiable failure signature match: '{', '.join(top_tokens)}' aligns with historical post-mortem.",
            f"Recalled prior incident: {cand_id} ({candidate.title or 'Historical incident'})",
        ]
        if candidate.verified_runbook or candidate.runbook_used:
            evidence_bullets.append(
                f"Historically proven runbook referenced: {candidate.verified_runbook or candidate.runbook_used}"
            )
        return RelevanceScoreResult(
            candidate_id=cand_id,
            service=cand_service,
            match_strength=MatchStrength.HIGH,
            verdict="ACCEPTED",
            is_accepted=True,
            overlap_tokens=overlap,
            alert_domains=alert_domains,
            candidate_domains=cand_domains,
            reason=reason,
            evidence_bullets=evidence_bullets,
        )

    # Case 3: Service match alone with insufficient technical overlap (< 2 tokens)
    # INVARIANT: Service match alone must NEVER produce HIGH relevance
    if service_match:
        reason = (
            f"Service match on '{alert.service}' alone is insufficient without concrete failure-mode technical alignment "
            f"(failure-mode overlap: {sorted(list(overlap))})."
        )
        evidence_bullets = [
            f"Candidate {cand_id} matches service '{alert.service}', but lacks sufficient failure-mode signature overlap.",
            "Categorical Decision: NONE (Insufficient technical indicator overlap). First-principles mode enabled.",
        ]
        return RelevanceScoreResult(
            candidate_id=cand_id,
            service=cand_service,
            match_strength=MatchStrength.NONE,
            verdict="REJECTED_INSUFFICIENT_FAILURE_MODE_ALIGNMENT",
            is_accepted=False,
            overlap_tokens=overlap,
            alert_domains=alert_domains,
            candidate_domains=cand_domains,
            reason=reason,
            evidence_bullets=evidence_bullets,
        )

    # Case 4: Cross-service architectural pattern match (strictly requires same verified failure domain & >= 2 tokens)
    if not service_match and len(overlap) >= 2 and not domain_conflict and bool(alert_domains and cand_domains and (alert_domains & cand_domains)):
        top_tokens = sorted(list(overlap))[:5]
        shared_domain = ", ".join(sorted(alert_domains & cand_domains))
        reason = f"Moderate correlation: Cross-service failure pattern match in domain [{shared_domain}] on [{', '.join(top_tokens)}]."
        evidence_bullets = [
            f"Moderate correlation: Cross-service failure pattern aligns with {cand_id} in domain [{shared_domain}] on [{', '.join(top_tokens)}].",
            f"Recalled cross-service incident: {cand_id} ({candidate.title or 'Cross-service incident'})",
        ]
        return RelevanceScoreResult(
            candidate_id=cand_id,
            service=cand_service,
            match_strength=MatchStrength.MODERATE,
            verdict="ACCEPTED_PARTIAL",
            is_accepted=True,
            overlap_tokens=overlap,
            alert_domains=alert_domains,
            candidate_domains=cand_domains,
            reason=reason,
            evidence_bullets=evidence_bullets,
        )

    # Case 5: Default novel / unrelated
    reason = f"Candidate {cand_id} has insufficient failure-mode overlap (overlap count: {len(overlap)})."
    evidence_bullets = [
        f"No sufficiently relevant historical incident found for service '{alert.service}'.",
        "Recalled records did not satisfy failure domain overlap threshold.",
    ]
    return RelevanceScoreResult(
        candidate_id=cand_id,
        service=cand_service,
        match_strength=MatchStrength.NONE,
        verdict="REJECTED_NO_ALIGNMENT",
        is_accepted=False,
        overlap_tokens=overlap,
        alert_domains=alert_domains,
        candidate_domains=cand_domains,
        reason=reason,
        evidence_bullets=evidence_bullets,
    )


def evaluate_batch_relevance(
    alert: AlertPayload,
    candidates: List[IncidentMemoryItem],
) -> Tuple[MatchStrength, List[str], List[IncidentMemoryItem], str, str]:
    """Evaluate a batch of candidate memories returned by Hindsight API.

    Returns:
        (highest_strength, evidence_bullets, accepted_items, overall_verdict, primary_reason)
    """
    if not candidates:
        return (
            MatchStrength.NONE,
            [
                f"No historical incidents found in Hindsight memory for service '{alert.service}'.",
                "Zero prior post-mortems match current alert symptoms or error signatures.",
            ],
            [],
            "NONE",
            "No candidates returned by Hindsight memory bank.",
        )

    scored_results = [score_candidate_relevance(alert, item) for item in candidates]
    accepted = [res for res in scored_results if res.is_accepted]

    if accepted:
        # Sort by strength (HIGH first) and token overlap
        accepted.sort(
            key=lambda r: (1 if r.match_strength == MatchStrength.HIGH else 0, len(r.overlap_tokens)),
            reverse=True,
        )
        best = accepted[0]
        # Deduplicate accepted candidates by incident ID
        seen_ids = set()
        accepted_items = []
        for c in candidates:
            cid = c.incident_id or c.id
            if cid == best.candidate_id and cid not in seen_ids:
                seen_ids.add(cid)
                accepted_items.append(c)

        return (
            best.match_strength,
            best.evidence_bullets,
            accepted_items,
            best.verdict,
            best.reason,
        )

    # All candidates were rejected by relevance or provenance gate
    # Pick the most informative rejection (provenance rejection, domain conflict, or first rejection)
    rejection_res = next(
        (r for r in scored_results if r.verdict in ("REJECTED_UNVERIFIED_DRAFT_MEMORY", "REJECTED_DIFFERENT_FAILURE_MODE")),
        scored_results[0],
    )
    return (
        MatchStrength.NONE,
        rejection_res.evidence_bullets,
        [],
        rejection_res.verdict,
        rejection_res.reason,
    )


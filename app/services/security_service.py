"""Security Service for Prompt Injection Defense and Untrusted Input Sanitization.

Enforces:
1. Untrusted Data Boundary: External incident telemetry treated as passive data, never instructions.
2. Control Character Normalization: Null bytes, ASCII control codes, and Unicode bidi/zero-width overrides stripped.
3. Injection Pattern Detection & Structured Audit: Identifies adversarial directives without leaking secrets.
4. Non-Blind Fact Preservation: Defuses injection directives while keeping technical incident symptoms usable.
5. Command & Secret Sanitization: Blocks destructive commands and redacts sensitive credentials.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.models.security import (
    CONTROL_CHAR_RE,
    MAX_DESCRIPTION_LEN,
    InjectionAuditRecord,
)

logger = logging.getLogger("incidentops.security")


class PromptInjectionDefense:
    """Detection, defusing, and audit logging for prompt injections and malicious inputs."""

    # Adversarial pattern definitions
    PATTERNS: Dict[str, re.Pattern] = {
        # 1. System/developer role injection & chat delimiter tampering
        "ROLE_INJECTION": re.compile(
            r"(?:<\s*\|\s*im_start\s*\|\s*>|\b(?:system|developer|assistant|root|admin)\s*:|"
            r"\[\s*INST\s*\]|\[\s*/INST\s*\]|<<\s*SYS\s*>>|<</\s*SYS\s*>>|"
            r"===\s*(?:SYSTEM|DEVELOPER|SYSTEM\s+PROMPT|SYSTEM\s+INSTRUCTION)\b)",
            re.IGNORECASE,
        ),
        # 2. Instruction override and jailbreak attempts
        "INSTRUCTION_OVERRIDE": re.compile(
            r"(?:\b(?:ignore|disregard|forget|override|bypass)\s+(?:all\s+)?(?:previous|prior|above|existing|system)\s+(?:instructions|rules|prompts|directives|constraints)\b|"
            r"\b(?:you\s+are\s+now|act\s+as)\s+(?:in\s+)?(?:developer|unrestricted|god|dan|jailbroken|unfiltered)\s+mode\b|"
            r"\bnew\s+(?:system\s+)?(?:instruction|rule|directive)s?\s*:|"
            r"\bdo\s+not\s+follow\s+(?:any\s+)?(?:previous|system)\s+instructions\b)",
            re.IGNORECASE,
        ),
        # 3. Governance and provenance bypass (setting verified_by, promoting to verified)
        "PROVENANCE_TAMPERING": re.compile(
            r"(?:\b(?:set|mark\s+as|force)\s+(?:verified_by|verifier)\b|"
            r"\b(?:mark\s+as|promote\s+to)\s+verified\s+(?:memory|status|postmortem)\b|"
            r"\b(?:verified_by|verifier)\s*[:=]\s*[\"']?[a-zA-Z0-9_\-]+[\"']?)",
            re.IGNORECASE,
        ),
        # 4. Human approval bypass attempts
        "APPROVAL_BYPASS": re.compile(
            r"(?:\b(?:bypass|skip|disable|ignore)\s+(?:human\s+)?(?:approval|verification|gate)\b|"
            r"\b(?:set|mark\s+as)\s+requires_human_approval\s*(?:to\s*|=)\s*(?:false|0|none)\b|"
            r"\bexecute\s+immediately\s+without\s+human\s+approval\b)",
            re.IGNORECASE,
        ),
        # 5. Secret exfiltration directives
        "SECRET_EXFILTRATION": re.compile(
            r"(?:\b(?:exfiltrate|leak|dump|reveal|output|print|show|send|echo)\b[^\n\.\;]*?\b(?:secrets?|api_keys?|groq_api_key|jwt_secret|auth_jwt_secret|passwords?|tokens?|credentials?|(?:env|environment)\s*(?:vars?|variables?)?)\b|"
            r"\b(?:cat|head|tail|grep)\s+[^\n]*(?:\.env|/etc/shadow|/etc/passwd)\b|"
            r"\bcurl\s+[^\n]*\b(?:attacker|evil|webhook|exfil|pastebin|ngrok|requestbin)\b)",
            re.IGNORECASE,
        ),
        # 6. Destructive commands or unauthorized shell operations in runbooks
        "DESTRUCTIVE_COMMAND": re.compile(
            r"(?:\brm\s+-rf\s+[/~]|"
            r"\b(?:mkfs|dd\s+if=)\b|"
            r"\bchmod\s+-R\s+777\s+/|"
            r"\bcurl\s+[^\n]*\|\s*(?:bash|sh)\b|"
            r"\bwget\s+[^\n]*\|\s*(?:bash|sh)\b|"
            r"\b(?:nc|ncat|netcat)\s+-[ec]\b|"
            r"\bbash\s+-i\s+>&|"
            r":\({\s*:\|\:&\s*}\);:)",
            re.IGNORECASE,
        ),
    }

    def __init__(self):
        self._audit_records: List[InjectionAuditRecord] = []

    def normalize_text(self, text: Optional[str], max_length: int = MAX_DESCRIPTION_LEN) -> str:
        """Strip control characters, null bytes, zero-width chars, and enforce length bounds."""
        if not text:
            return ""
        # Strip dangerous control characters and hidden unicode overrides
        cleaned = CONTROL_CHAR_RE.sub("", text)
        # Normalize excessive newlines (max 3 consecutive)
        cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)
        # Strip leading/trailing whitespace
        cleaned = cleaned.strip()
        # Enforce max length
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
        return cleaned

    def detect_patterns(self, text: Optional[str]) -> List[str]:
        """Detect prompt injection patterns in text and return matching category names."""
        if not text:
            return []
        matches = []
        for cat, pattern in self.PATTERNS.items():
            if pattern.search(text):
                matches.append(cat)
        return matches

    def record_audit(
        self,
        field_name: str,
        detected_patterns: List[str],
        raw_text: str,
        alert_id: Optional[str] = None,
    ) -> InjectionAuditRecord:
        """Log structured audit record without storing raw secrets."""
        # Create sanitized preview: first 120 chars with credentials scrubbed
        sanitized_excerpt = self.scrub_secrets(raw_text[:120])
        # Replace newlines with spaces for clean logging
        sanitized_excerpt = sanitized_excerpt.replace("\n", " ").replace("\r", "")

        record = InjectionAuditRecord(
            alert_id=alert_id,
            field_name=field_name,
            detected_patterns=detected_patterns,
            sanitized_excerpt=sanitized_excerpt,
            risk_level="HIGH" if any(p in ("DESTRUCTIVE_COMMAND", "SECRET_EXFILTRATION") for p in detected_patterns) else "MEDIUM",
        )
        self._audit_records.append(record)

        from app.services.metrics_service import metrics_service
        metrics_service.inc_injection_detections(len(detected_patterns))

        logger.warning(
            "[SECURITY INJECTION AUDIT] alert_id=%s field=%s patterns=%s excerpt='%s' risk=%s",
            alert_id or "N/A",
            field_name,
            ",".join(detected_patterns),
            sanitized_excerpt,
            record.risk_level,
        )
        return record

    def defuse_untrusted_text(
        self,
        text: Optional[str],
        field_name: str = "untrusted_input",
        alert_id: Optional[str] = None,
    ) -> Tuple[str, List[str]]:
        """Neutralize malicious directives while keeping factual technical incident content intact.

        Non-blind defusing: replaces matched injection directives with inert markers,
        ensuring surrounding technical telemetry (e.g. latency, error rates, component names)
        remains available for legitimate triage reasoning.
        """
        if not text:
            return "", []

        detected = self.detect_patterns(text)
        if not detected:
            return text, []

        # Record structured audit event
        self.record_audit(field_name, detected, text, alert_id=alert_id)

        # Non-blindly defuse matched pattern directives in text
        defused = text
        for cat, pattern in self.PATTERNS.items():
            if cat == "DESTRUCTIVE_COMMAND":
                defused = pattern.sub(f"[BLOCKED_UNSAFE_OPERATION: {cat}]", defused)
            else:
                defused = pattern.sub(f"[DEFUSED_UNTRUSTED_INSTRUCTION: {cat}]", defused)

        return defused, detected

    def sanitize_command(self, command: str) -> Tuple[str, bool]:
        """Verify runbook command safety. If command matches destructive/exfiltration patterns, defuse it."""
        if not command:
            return "# no-op verification", False

        destructive_pattern = self.PATTERNS["DESTRUCTIVE_COMMAND"]
        secret_pattern = self.PATTERNS["SECRET_EXFILTRATION"]

        is_dangerous = bool(destructive_pattern.search(command) or secret_pattern.search(command))
        if is_dangerous:
            self.record_audit(
                field_name="runbook_command",
                detected_patterns=["DESTRUCTIVE_COMMAND" if destructive_pattern.search(command) else "SECRET_EXFILTRATION"],
                raw_text=command,
            )
            safe_command = "# BLOCKED_UNSAFE_COMMAND: Operation neutralized by IncidentOps Copilot security boundary (safe simulation required)"
            return safe_command, True

        return command, False

    def scrub_secrets(self, text: Optional[str]) -> str:
        """Redact any configured secrets, API keys, or JWT tokens from text output."""
        if not text:
            return ""

        scrubbed = text

        # 1. Redact Groq API key
        if settings.groq_api_key and len(settings.groq_api_key.strip()) > 6:
            scrubbed = scrubbed.replace(settings.groq_api_key.strip(), "[REDACTED_API_KEY]")

        # 2. Redact JWT secret
        if settings.auth_jwt_secret and len(settings.auth_jwt_secret.strip()) > 6:
            scrubbed = scrubbed.replace(settings.auth_jwt_secret.strip(), "[REDACTED_JWT_SECRET]")

        # 3. Redact SRE API keys
        if settings.auth_sre_api_keys:
            for pair in settings.auth_sre_api_keys.split(","):
                if ":" in pair:
                    k, _ = pair.split(":", 1)
                    k = k.strip()
                    if len(k) > 4:
                        scrubbed = scrubbed.replace(k, "[REDACTED_SRE_KEY]")

        # 4. Generic credential patterns (e.g. gsk_[A-Za-z0-9]{20,})
        scrubbed = re.sub(r"gsk_[A-Za-z0-9_\-]{20,}", "[REDACTED_GROQ_KEY]", scrubbed)
        scrubbed = re.sub(r"(?i)(?:api[_-]?key|secret[_-]?key|password)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.\$]{8,}['\"]?", "[REDACTED_CREDENTIAL]", scrubbed)

        return scrubbed

    def get_audit_records(self) -> List[InjectionAuditRecord]:
        """Return immutable copy of in-memory security audit log."""
        return list(self._audit_records)

    def clear_audit_records(self) -> None:
        """Reset security audit log (primarily for isolated test assertions)."""
        self._audit_records.clear()


# Global singleton instance
security_service = PromptInjectionDefense()

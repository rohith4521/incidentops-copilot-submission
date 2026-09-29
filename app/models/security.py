"""Security models, patterns, and constants for prompt injection defense."""

from datetime import datetime, timezone
from enum import Enum
import re
from typing import List, Optional
from pydantic import BaseModel, Field

# Control characters: ASCII 0x00-0x08, 0x0B-0x0C, 0x0E-0x1F, 0x7F,
# plus Unicode zero-width characters and bidi overrides
CONTROL_CHAR_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200d\ufeff\u202a-\u202e\u2066-\u2069]"
)

# Maximum safe lengths for untrusted input fields
MAX_SERVICE_LEN = 128
MAX_ALERT_TITLE_LEN = 256
MAX_DESCRIPTION_LEN = 4096
MAX_SYMPTOM_ITEM_LEN = 512
MAX_SYMPTOMS_COUNT = 50
MAX_CONTEXT_SERIALIZED_LEN = 8192
MAX_CONTEXT_KEYS = 50


class InjectionRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InjectionAuditRecord(BaseModel):
    """Structured audit log entry for detected prompt injection attempts."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    alert_id: Optional[str] = None
    field_name: str
    detected_patterns: List[str]
    sanitized_excerpt: str
    risk_level: str = "HIGH"

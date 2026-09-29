"""Authentication models for SRE verified provenance."""

from pydantic import BaseModel, Field


class AuthenticatedUser(BaseModel):
    """Authenticated SRE operator or engineer."""
    identity: str = Field(..., description="Unique SRE operator identity, e.g. 'lead-sre-alice' or 'oncall-sre'")
    role: str = Field(default="sre", description="User role, e.g. 'sre', 'lead_sre', 'ai_agent'")
    auth_type: str = Field(default="jwt", description="Authentication mechanism: 'jwt' or 'api_key'")
    is_human: bool = Field(default=True, description="Strictly True for human operators; False for AI agents")

"""Request models shared by the modern API routers.

The legacy application used query parameters for most write operations.  The
React client uses JSON payloads, so these schemas make the public contract
explicit and keep validation at the API boundary.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginRequest(ApiModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class BootstrapRequest(LoginRequest):
    organization_name: str = Field(default="Presidio", min_length=1, max_length=255)
    organization_code: str = Field(default="PRESIDIO", min_length=2, max_length=50)
    department_name: str = Field(default="General", min_length=1, max_length=255)
    department_code: str = Field(default="GENERAL", min_length=2, max_length=50)
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("organization_code", "department_code")
    @classmethod
    def normalize_codes(cls, value: str) -> str:
        return value.upper().replace(" ", "_")


class UserCreateRequest(ApiModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    # Kept optional solely for explicit local-auth migration/test mode.  Supabase
    # deployments treat email creation as an allowlist invitation and reject it.
    password: str | None = Field(default=None, min_length=8, max_length=256)
    roles: list[str] = Field(min_length=1)
    manager_id: UUID | None = None

    @field_validator("roles")
    @classmethod
    def normalize_roles(cls, value: list[str]) -> list[str]:
        normalized = [role.strip().lower() for role in value if role.strip()]
        if not normalized:
            raise ValueError("at least one role is required")
        if len(set(normalized)) != len(normalized):
            raise ValueError("roles must not contain duplicates")
        return normalized


class UserUpdateRequest(ApiModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=256)
    roles: list[str] | None = None
    manager_id: UUID | None = None

    @field_validator("roles")
    @classmethod
    def normalize_roles(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        normalized = [role.strip().lower() for role in value if role.strip()]
        if not normalized:
            raise ValueError("at least one role is required")
        if len(set(normalized)) != len(normalized):
            raise ValueError("roles must not contain duplicates")
        return normalized

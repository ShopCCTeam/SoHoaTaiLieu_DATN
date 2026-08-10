"""Pydantic schemas cho auth endpoints.

Field name = snake_case (match OpenAPI convention, xem `docs/api/openapi.yaml`).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """POST /auth/login body."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserPublic(BaseModel):
    """Response shape trả về cho client — match OpenAPI `User` schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    role: str
    department: str | None = None
    is_active: bool = True


class LoginResponse(BaseModel):
    """POST /auth/login response — match OpenAPI `LoginResponse`."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class RefreshResponse(BaseModel):
    """POST /auth/refresh response."""

    access_token: str
    expires_in: int


class MeResponse(BaseModel):
    """GET /auth/me response."""

    user: UserPublic

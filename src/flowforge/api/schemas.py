from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl

from flowforge.db.models import ExecutionStatus, JobStatus


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=2, max_length=120)


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    slug: str


class WorkflowCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    target_url: HttpUrl


class WorkflowRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    target_url: str


class RunCreateRequest(BaseModel):
    input_payload: dict = Field(default_factory=dict)


class RunRead(BaseModel):
    id: UUID
    workflow_id: UUID
    status: ExecutionStatus
    job_id: UUID
    job_status: JobStatus
    attempts: int
    audit: list[str]

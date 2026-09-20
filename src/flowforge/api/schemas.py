from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from flowforge.db.models import (
    AuditAction,
    ExecutionStatus,
    JobStatus,
    TenantPlan,
    TenantRole,
    WorkflowStatus,
)


class MessageResponse(BaseModel):
    detail: str


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


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class GoogleOAuthResponse(BaseModel):
    authorization_url: str


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=120)
    plan: TenantPlan = TenantPlan.free


class OrganizationInviteRequest(BaseModel):
    email: EmailStr
    role: TenantRole = TenantRole.member


class MembershipUpdateRequest(BaseModel):
    membership_id: UUID
    role: TenantRole


class SwitchTenantRequest(BaseModel):
    tenant_id: UUID


class WorkflowCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    trigger_type: str = Field(default="manual", max_length=50)
    definition: dict = Field(default_factory=dict)


class WorkflowUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    trigger_type: str | None = Field(default=None, max_length=50)
    status: WorkflowStatus | None = None
    definition: dict | None = None


class WorkflowExecuteRequest(BaseModel):
    input_payload: dict = Field(default_factory=dict)
    correlation_id: str | None = Field(default=None, max_length=255)


class WorkflowRetryRequest(BaseModel):
    execution_id: UUID


class WorkflowCancelRequest(BaseModel):
    execution_id: UUID


class JobQueueRequest(BaseModel):
    job_type: str = Field(min_length=2, max_length=120)
    payload: dict = Field(default_factory=dict)
    run_at: datetime | None = None
    queue_name: str = Field(default="default", max_length=120)


class JobRetryRequest(BaseModel):
    job_id: UUID


class ReportRangeRequest(BaseModel):
    start_date: datetime
    end_date: datetime


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    scopes: dict = Field(default_factory=dict)
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    scopes: dict
    expires_at: datetime | None
    revoked_at: datetime | None


class AuditLogResponse(BaseModel):
    id: UUID
    action: AuditAction
    entity_type: str
    entity_id: str | None
    metadata: dict
    created_at: datetime


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: TenantPlan


class WorkflowRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    status: WorkflowStatus
    trigger_type: str
    version: int


class ExecutionRead(BaseModel):
    id: UUID
    workflow_id: UUID
    status: ExecutionStatus
    correlation_id: str | None
    duration_ms: int | None


class JobRead(BaseModel):
    id: UUID
    job_type: str
    status: JobStatus
    queue_name: str
    attempts: int


class ReportSummaryResponse(BaseModel):
    executions_count: int
    success_count: int
    failure_count: int
    average_duration_ms: int
    exported_format: str | None = None

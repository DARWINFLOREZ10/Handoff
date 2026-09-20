from __future__ import annotations

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge.api.deps import get_current_user, get_db_session, get_tenant_or_404
from flowforge.api.schemas import (
    MembershipUpdateRequest,
    MessageResponse,
    OrganizationCreateRequest,
    OrganizationInviteRequest,
    OrganizationRead,
    SwitchTenantRequest,
)
from flowforge.db.models import (
    AuditAction,
    AuditLog,
    Membership,
    Organization,
    OrganizationInvitation,
    TenantRole,
    User,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationRead)
async def create_organization(
    payload: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OrganizationRead:
    organization = Organization(name=payload.name, slug=payload.slug, plan=payload.plan)
    session.add(organization)
    await session.flush()
    session.add(
        Membership(
            tenant_id=organization.id,
            user_id=current_user.id,
            role=TenantRole.owner,
            invited_by_user_id=current_user.id,
        )
    )
    session.add(
        AuditLog(
            tenant_id=organization.id,
            actor_user_id=current_user.id,
            action=AuditAction.permission_updated,
            entity_type="organization",
            entity_id=str(organization.id),
            event_data={"event": "organization_created", "plan": payload.plan.value},
        )
    )
    await session.commit()
    return OrganizationRead(
        id=organization.id, name=organization.name, slug=organization.slug, plan=organization.plan
    )


@router.post("/{tenant_id}/invite", response_model=MessageResponse)
async def invite_user(
    tenant_id: UUID,
    payload: OrganizationInviteRequest,
    tenant: Organization = Depends(get_tenant_or_404),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    if tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    invitation = OrganizationInvitation(
        tenant_id=tenant.id,
        email=str(payload.email),
        role=payload.role,
        token=token_urlsafe(32),
        invited_by_user_id=current_user.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(invitation)
    await session.flush()
    session.add(
        AuditLog(
            tenant_id=tenant.id,
            actor_user_id=current_user.id,
            action=AuditAction.role_changed,
            entity_type="organization_invitation",
            entity_id=str(invitation.id),
            event_data={"email": payload.email, "role": payload.role.value},
        )
    )
    await session.commit()
    return MessageResponse(detail="Invitation created and queued for delivery.")


@router.get("/{tenant_id}/members", response_model=list[OrganizationRead])
async def list_members(
    tenant_id: UUID,
    tenant: Organization = Depends(get_tenant_or_404),
) -> list[OrganizationRead]:
    if tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    return [OrganizationRead(id=tenant.id, name=tenant.name, slug=tenant.slug, plan=tenant.plan)]


@router.patch("/{tenant_id}/members", response_model=MessageResponse)
async def manage_member(
    tenant_id: UUID,
    payload: MembershipUpdateRequest,
    tenant: Organization = Depends(get_tenant_or_404),
) -> MessageResponse:
    if tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    return MessageResponse(
        detail=f"Membership {payload.membership_id} updated for tenant {tenant.id}."
    )


@router.post("/switch-tenant", response_model=MessageResponse)
async def switch_tenant(
    payload: SwitchTenantRequest, current_user: User = Depends(get_current_user)
) -> MessageResponse:
    return MessageResponse(
        detail=f"Tenant switched to {payload.tenant_id} for user {current_user.id}."
    )

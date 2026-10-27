from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge.api.deps import get_current_user, get_db_session
from flowforge.api.schemas import OrganizationCreateRequest, OrganizationRead
from flowforge.db.models import AuditAction, AuditLog, Membership, Organization, TenantRole, User

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _read(organization: Organization) -> OrganizationRead:
    return OrganizationRead(id=organization.id, name=organization.name, slug=organization.slug)


@router.get("", response_model=list[OrganizationRead])
async def list_organizations(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[OrganizationRead]:
    result = await session.execute(
        select(Organization)
        .join(Membership, Membership.tenant_id == Organization.id)
        .where(Membership.user_id == current_user.id)
        .order_by(Organization.name)
    )
    return [_read(organization) for organization in result.scalars().all()]


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OrganizationRead:
    organization = Organization(name=payload.name, slug=payload.slug)
    session.add(organization)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Organization slug already exists."
        ) from exc
    session.add(
        Membership(tenant_id=organization.id, user_id=current_user.id, role=TenantRole.owner)
    )
    session.add(
        AuditLog(
            tenant_id=organization.id,
            actor_user_id=current_user.id,
            action=AuditAction.organization_created,
            entity_type="organization",
            entity_id=str(organization.id),
            event_data={"event": "organization_created"},
        )
    )
    await session.commit()
    return _read(organization)

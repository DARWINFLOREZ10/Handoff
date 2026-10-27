from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge.api.deps import get_db_session
from flowforge.api.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenPairResponse,
)
from flowforge.core.config import get_settings
from flowforge.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from flowforge.db.models import AuditAction, AuditLog, Membership, Organization, TenantRole, User

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens(user_id: object) -> TokenPairResponse:
    subject = str(user_id)
    return TokenPairResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


@router.post("/register", response_model=TokenPairResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, session: AsyncSession = Depends(get_db_session)
) -> TokenPairResponse:
    existing = await session.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists.")

    user = User(
        email=str(payload.email),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    organization = Organization(
        name=payload.full_name or payload.email.split("@")[0],
        slug=f"personal-{uuid4().hex[:12]}",
    )
    session.add(user)
    session.add(organization)
    await session.flush()
    session.add(Membership(tenant_id=organization.id, user_id=user.id, role=TenantRole.owner))
    session.add(
        AuditLog(
            tenant_id=organization.id,
            actor_user_id=user.id,
            action=AuditAction.registration,
            entity_type="organization",
            entity_id=str(organization.id),
            event_data={"email": str(payload.email)},
        )
    )
    await session.commit()
    return _tokens(user.id)


@router.post("/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_db_session)
) -> TokenPairResponse:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password."
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive.")

    membership = await session.execute(
        select(Membership)
        .where(Membership.user_id == user.id)
        .order_by(Membership.created_at.asc())
    )
    first = membership.scalars().first()
    if first is not None:
        session.add(
            AuditLog(
                tenant_id=first.tenant_id,
                actor_user_id=user.id,
                action=AuditAction.login,
                entity_type="user",
                entity_id=str(user.id),
                event_data={"event": "user_logged_in"},
            )
        )
        await session.commit()
    return _tokens(user.id)


@router.post("/refresh-token", response_model=TokenPairResponse)
async def refresh_token(payload: RefreshTokenRequest) -> TokenPairResponse:
    settings = get_settings()
    try:
        decoded = jwt.decode(
            payload.refresh_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token."
        ) from exc
    subject = str(decoded.get("sub", ""))
    if not subject or decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token."
        )
    return _tokens(subject)

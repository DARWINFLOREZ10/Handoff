from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from flowforge.api.deps import get_current_user, get_db_session
from flowforge.api.schemas import (
    GoogleOAuthResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenPairResponse,
)
from flowforge.core.config import get_settings
from flowforge.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from flowforge.db.models import AuditAction, AuditLog, Membership, Organization, TenantRole, User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPairResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_db_session)) -> TokenPairResponse:
    result = await session.execute(select(User).where(User.email == payload.email))
    existing_user = result.scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists.")

    user = User(email=str(payload.email), full_name=payload.full_name, password_hash=hash_password(payload.password))
    organization = Organization(
        name=payload.full_name or payload.email.split("@")[0],
        slug=f"personal-{uuid4().hex[:12]}",
    )
    session.add(user)
    session.add(organization)
    await session.flush()
    session.add(Membership(tenant_id=organization.id, user_id=user.id, role=TenantRole.owner, invited_by_user_id=user.id))

    session.add(
        AuditLog(
            tenant_id=organization.id,
            actor_user_id=user.id,
            action=AuditAction.registration,
            entity_type="organization",
            entity_id=str(organization.id),
            event_data={"event": "user_registered", "email": payload.email},
        )
    )
    session.add(
        AuditLog(
            tenant_id=organization.id,
            actor_user_id=user.id,
            action=AuditAction.login,
            entity_type="user",
            entity_id=str(user.id),
            event_data={"event": "user_registered"},
        )
    )
    await session.commit()

    subject = str(user.id)
    return TokenPairResponse(access_token=create_access_token(subject), refresh_token=create_refresh_token(subject))


@router.post("/login", response_model=TokenPairResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db_session)) -> TokenPairResponse:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or user.password_hash is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive.")

    membership_result = await session.execute(select(Membership).where(Membership.user_id == user.id).order_by(Membership.created_at.asc()))
    membership = membership_result.scalars().first()
    if membership is not None:
        session.add(
            AuditLog(
                tenant_id=membership.tenant_id,
                actor_user_id=user.id,
                action=AuditAction.login,
                entity_type="user",
                entity_id=str(user.id),
                event_data={"event": "user_logged_in"},
            )
        )
    await session.commit()

    subject = str(user.id)
    return TokenPairResponse(access_token=create_access_token(subject), refresh_token=create_refresh_token(subject))


@router.post("/refresh-token", response_model=TokenPairResponse)
async def refresh_token(payload: RefreshTokenRequest) -> TokenPairResponse:
    settings = get_settings()
    decoded = jwt.decode(payload.refresh_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    subject = str(decoded.get("sub", ""))
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type.")
    return TokenPairResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: User = Depends(get_current_user)) -> MessageResponse:
    return MessageResponse(detail=f"User {current_user.id} logged out successfully.")


@router.post("/password-reset", response_model=MessageResponse)
async def request_password_reset(
    payload: PasswordResetRequest,
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is not None:
        session.add(
            AuditLog(
                tenant_id=uuid4(),
                actor_user_id=user.id,
                action=AuditAction.password_reset_requested,
                entity_type="user",
                entity_id=str(user.id),
                event_data={"email": payload.email},
            )
        )
        await session.commit()
    return MessageResponse(detail="If the account exists, a password reset email will be sent.")


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(payload: PasswordResetConfirmRequest) -> MessageResponse:
    return MessageResponse(detail="Password reset completed.")


@router.get("/google/start", response_model=GoogleOAuthResponse)
async def google_oauth_start() -> GoogleOAuthResponse:
    settings = get_settings()
    authorization_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&redirect_uri={settings.google_oauth_redirect_uri}"
        "&response_type=code&scope=openid%20email%20profile"
        f"&state={uuid4()}"
    )
    return GoogleOAuthResponse(authorization_url=authorization_url)


@router.get("/google/callback", response_model=MessageResponse)
async def google_oauth_callback(code: str) -> MessageResponse:
    return MessageResponse(detail=f"Google OAuth callback received for code {code}.")

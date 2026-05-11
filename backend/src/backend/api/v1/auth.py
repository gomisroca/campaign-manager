import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.db.session import get_db
from backend.schemas.user import (
    PasswordReset,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from backend.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_by_id,
    register_user,
    update_user,
)
from backend.deps import get_current_user
from backend.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

class UpdateProfileRequest(BaseModel):
    full_name: str | None = None

# ── Register ──────────────────────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(db, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


# ── Login ─────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        # Always return the same error regardless of whether the email
        # exists or the password is wrong — don't leak which one failed.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


# ── Refresh ───────────────────────────────────────────────────────────────────
@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        user_id = decode_token(data.refresh_token, expected_type="refresh")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


# ── Me ────────────────────────────────────────────────────────────────────────
@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await update_user(db, current_user, data.full_name)
    return UserResponse.model_validate(user)


# ── Forgot password ───────────────────────────────────────────────────────────
@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    # Always return 204 regardless of whether the email exists —
    # returning 404 when an email isn't found leaks user data.
    # The actual email sending will be wired up when email_service.py is done.
    pass


# ── Reset password ────────────────────────────────────────────────────────────
@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(data: PasswordReset, db: AsyncSession = Depends(get_db)):
    # Placeholder — will be implemented with email_service.py
    pass
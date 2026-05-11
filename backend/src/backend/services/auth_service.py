import uuid
import hashlib
import base64
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.user import User
from backend.schemas.user import UserRegister

settings = get_settings()

# ── Password hashing ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _prepare_password(plain: str) -> str:
    """Hash with SHA-256 first so bcrypt never sees more than 72 bytes."""
    digest = hashlib.sha256(plain.encode()).digest()
    return base64.b64encode(digest).decode()

def hash_password(plain: str) -> str:
    return pwd_context.hash(_prepare_password(plain))

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(_prepare_password(plain), hashed)

_DUMMY_HASH = hash_password("dummy-timing-prevention")


# ── JWT ───────────────────────────────────────────────────────────────────────
#   access_token  — short-lived (30 min), sent with every API request
#   refresh_token — long-lived (30 days), used only to get a new access token
def _create_token(payload: dict, expires_delta: timedelta) -> str:
    expire = datetime.now(UTC) + expires_delta
    return jwt.encode(
        {**payload, "exp": expire},
        settings.secret_key,
        algorithm="HS256",
    )


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(
        {"sub": str(user_id), "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(
        {"sub": str(user_id), "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: str = "access") -> uuid.UUID:
    """
    Decode and validate a JWT. Returns the user_id (sub) on success.
    Raises jwt.PyJWTError on any failure (expired, invalid, wrong type).
    """
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])

    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Expected token type '{expected_type}'")

    user_id = payload.get("sub")
    if not user_id:
        raise jwt.InvalidTokenError("Token missing subject")

    return uuid.UUID(user_id)


# ── User queries ──────────────────────────────────────────────────────────────
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email.lower().strip())
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()

async def update_user(
    db: AsyncSession, user: User, full_name: str | None
) -> User:
    user.full_name = full_name
    await db.flush()
    return user

# ── Auth operations ───────────────────────────────────────────────────────────
async def register_user(db: AsyncSession, data: UserRegister) -> User:
    """
    Create a new user. Raises ValueError if the email is already taken.
    The caller is responsible for committing the session.
    """
    existing = await get_user_by_email(db, data.email)
    if existing:
        raise ValueError("Email already registered")

    user = User(
        email=data.email.lower().strip(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> User | None:
    """
    Verify email + password. Returns the User on success, None on failure.
    Returning None (rather than raising) lets the route return a 401
    without leaking whether the email exists.
    """
    user = await get_user_by_email(db, email)
    if not user:
        # Dummy hash to prevent timing attacks
        verify_password("dummy", _DUMMY_HASH)
        return None

    if not user.hashed_password:
        return None  # OAuth-only user, no password set

    if not verify_password(password, user.hashed_password):
        return None

    if not user.is_active:
        return None

    return user
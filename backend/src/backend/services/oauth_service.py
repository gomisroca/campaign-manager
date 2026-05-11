import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.user import User
from backend.services.auth_service import get_user_by_email
from sqlalchemy import select

settings = get_settings()

# ── Google OAuth URLs ─────────────────────────────────────────────────────────
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPES = "openid email profile"


def get_google_auth_url(redirect_uri: str, state: str) -> str:
    """Build the Google OAuth authorization URL to redirect the user to."""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_code_for_user_info(code: str, redirect_uri: str) -> dict:
    """
    Exchange the authorization code for an access token,
    then use it to fetch the user's profile from Google.
    """
    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_res = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        token_res.raise_for_status()
        tokens = token_res.json()

        # Fetch user info using the access token
        userinfo_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        userinfo_res.raise_for_status()
        return userinfo_res.json()


async def get_or_create_oauth_user(
    db: AsyncSession, userinfo: dict
) -> tuple[User, bool]:
    """
    Find an existing user by Google ID or email, or create a new one.
    Returns (user, created) where created is True if a new user was made.

    Handles three cases:
    1. User already signed up with Google — find by oauth_id
    2. User already has an email/password account — link Google to it
    3. Brand new user — create account
    """
    google_id = userinfo.get("sub")
    email = userinfo.get("email", "").lower().strip()
    full_name = userinfo.get("name")
    avatar_url = userinfo.get("picture")

    # Case 1: existing Google user
    result = await db.execute(
        select(User).where(
            User.oauth_provider == "google",
            User.oauth_id == google_id,
        )
    )
    user = result.scalar_one_or_none()
    if user:
        # Update avatar in case it changed
        user.avatar_url = avatar_url
        await db.flush()
        return user, False

    # Case 2: existing email/password user — link Google to their account
    user = await get_user_by_email(db, email)
    if user:
        user.oauth_provider = "google"
        user.oauth_id = google_id
        user.avatar_url = avatar_url or user.avatar_url
        await db.flush()
        return user, False

    # Case 3: new user
    user = User(
        email=email,
        full_name=full_name,
        avatar_url=avatar_url,
        oauth_provider="google",
        oauth_id=google_id,
        hashed_password=None,  # no password for OAuth users
    )
    db.add(user)
    await db.flush()
    return user, True
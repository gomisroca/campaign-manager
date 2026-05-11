import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.db.session import get_db
from backend.services.auth_service import create_access_token, create_refresh_token
from backend.services.oauth_service import (
    exchange_code_for_user_info,
    get_google_auth_url,
    get_or_create_oauth_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

GOOGLE_REDIRECT_URI = f"{settings.frontend_url.replace('3000', '8000')}/api/v1/auth/google/callback"


def _frontend_error_redirect(message: str) -> RedirectResponse:
    """Redirect to frontend login page with an error message."""
    from urllib.parse import quote
    return RedirectResponse(
        url=f"{settings.frontend_url}/login?error={quote(message)}",
        status_code=302,
    )


# ── Step 1: redirect to Google ────────────────────────────────────────────────
@router.get("/google")
async def google_login():
    """
    Redirect the user to Google's OAuth consent screen.
    The state parameter is a random token to prevent CSRF attacks.
    """
    if not settings.google_oauth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured",
        )
    state = secrets.token_urlsafe(16)
    url = get_google_auth_url(GOOGLE_REDIRECT_URI, state)
    return RedirectResponse(url=url, status_code=302)


# ── Step 2: handle Google's callback ─────────────────────────────────────────
@router.get("/google/callback")
async def google_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Google redirects here after the user logs in.
    Exchange the code for user info, create/find the user,
    issue our own JWT, and redirect to the frontend.
    """
    # User denied access on Google's page
    if error:
        return _frontend_error_redirect("Google sign-in was cancelled")

    if not code:
        return _frontend_error_redirect("No authorisation code received from Google")

    try:
        userinfo = await exchange_code_for_user_info(code, GOOGLE_REDIRECT_URI)
    except Exception:
        return _frontend_error_redirect("Failed to retrieve profile from Google")

    if not userinfo.get("email"):
        return _frontend_error_redirect("Google did not return an email address")

    if not userinfo.get("email_verified"):
        return _frontend_error_redirect("Google account email is not verified")

    try:
        user, created = await get_or_create_oauth_user(db, userinfo)
    except Exception:
        return _frontend_error_redirect("Failed to create account")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # Redirect to frontend with tokens in URL params
    redirect_url = (
        f"{settings.frontend_url}/auth/callback"
        f"?access_token={access_token}"
        f"&refresh_token={refresh_token}"
        f"&new_user={'true' if created else 'false'}"
    )
    return RedirectResponse(url=redirect_url, status_code=302)
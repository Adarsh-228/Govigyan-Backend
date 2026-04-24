from fastapi import Cookie, Header, HTTPException, status

from app.core.config import settings
from app.core.supabase_client import supabase_anon


async def get_current_user(
    authorization: str | None = Header(default=None),
    access_token_cookie: str | None = Cookie(default=None, alias=settings.AUTH_COOKIE_NAME),
):
    token: str | None = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "", 1).strip()
    elif access_token_cookie:
        token = access_token_cookie

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing auth token (Bearer header or login cookie)",
        )
    try:
        auth_response = supabase_anon.auth.get_user(token)
    except Exception as exc:  # pragma: no cover - network/auth provider
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
        ) from exc

    user = getattr(auth_response, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return user

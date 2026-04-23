from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import AuthApiError

from app.api.deps import get_current_user
from app.core.supabase_client import supabase_anon

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(payload: LoginRequest):
    try:
        auth_response = supabase_anon.auth.sign_in_with_password(
            {
                "email": payload.email,
                "password": payload.password,
            }
        )
    except AuthApiError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - upstream/provider failures
        raise HTTPException(status_code=400, detail=f"Login failed: {exc}") from exc

    session = getattr(auth_response, "session", None)
    user = getattr(auth_response, "user", None)
    if not session or not user:
        raise HTTPException(status_code=401, detail="Invalid login response")

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "expires_in": session.expires_in,
        "user": {
            "id": str(user.id),
            "email": user.email,
        },
    }


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": getattr(current_user, "email", None),
        "role": getattr(current_user, "role", None),
    }

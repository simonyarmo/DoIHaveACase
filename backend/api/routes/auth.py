from fastapi import APIRouter, HTTPException, status

from api.dependencies import CurrentUserDep, DbDep
from schemas.auth import AuthSession, LoginRequest, SignupRequest, UserOut
from services.supabase_client import get_supabase
from services.users import get_or_create_local_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthSession)
async def signup(payload: SignupRequest, db: DbDep) -> AuthSession:
    supabase = get_supabase()
    try:
        result = supabase.auth.sign_up(
            {
                "email": payload.email,
                "password": payload.password,
                "options": {"data": {"full_name": payload.full_name}},
            }
        )
    except Exception as exc:  # noqa: BLE001 - Supabase raises generic AuthApiError
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if result.session is None or result.user is None:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Signup succeeded. Check your email to confirm your account before logging in.",
        )

    await get_or_create_local_user(
        db,
        user_id=result.user.id,
        email=result.user.email or payload.email,
        full_name=payload.full_name,
    )

    return AuthSession(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
        expires_in=result.session.expires_in,
    )


@router.post("/login", response_model=AuthSession)
async def login(payload: LoginRequest) -> AuthSession:
    supabase = get_supabase()
    try:
        result = supabase.auth.sign_in_with_password({"email": payload.email, "password": payload.password})
    except Exception as exc:  # noqa: BLE001 - Supabase raises generic AuthApiError
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password") from exc

    if result.session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return AuthSession(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
        expires_in=result.session.expires_in,
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUserDep) -> UserOut:
    return UserOut.model_validate(current_user)

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User
from services.users import get_or_create_local_user

bearer_scheme = HTTPBearer(auto_error=False)

CredentialsDep = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


def _decode_supabase_jwt(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except (JWTError, ValueError, TypeError, AttributeError) as exc:
        # python-jose can raise non-JWTError exceptions (e.g. ValueError/TypeError
        # from malformed base64/JSON segments) for tokens that aren't valid JWTs at
        # all — all of these mean "credentials are bad", not "server is broken".
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(credentials: CredentialsDep, db: DbDep) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_supabase_jwt(credentials.credentials)
    supabase_user_id = payload.get("sub")
    email = payload.get("email")
    if supabase_user_id is None or email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    full_name = (payload.get("user_metadata") or {}).get("full_name")
    return await get_or_create_local_user(db, user_id=supabase_user_id, email=email, full_name=full_name)


CurrentUserDep = Annotated[User, Depends(get_current_user)]

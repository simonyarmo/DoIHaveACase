import uuid

from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthSession(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone_number: str | None = None
    phone_verified: bool
    sms_notifications: bool
    subscription_tier: str

    model_config = {"from_attributes": True}

import uuid

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    shop_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    shop_id: uuid.UUID
    email: EmailStr
    shop_name: str

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=55)
    email: EmailStr
    password: str = Field(min_length=6)


class UserRead(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "Bearer"


class RefreshToken(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"

"""Auth schemas — login, register, token."""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    employee_id: str = Field(..., min_length=2, max_length=20, description="工号")
    password: str = Field(..., min_length=4, max_length=64)
    name: str = Field(..., min_length=1, max_length=50)
    department: str = Field(default="", max_length=50)


class LoginRequest(BaseModel):
    employee_id: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class QuickLoginRequest(BaseModel):
    employee_id: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6位数字工号",
    )


class UserResponse(BaseModel):
    id: str
    employee_id: str
    name: str
    department: str | None
    role: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

from pydantic import BaseModel, Field
from uuid import UUID

class LoginRequest(BaseModel):
    account_number: str
    pin: str = Field(..., pattern=r'^\d{4,6}$', description="4-6 digit numeric PIN")

class RegisterRequest(BaseModel):
    name: str
    email: str
    pin: str = Field(..., pattern=r'^\d{4,6}$', description="4-6 digit numeric PIN")

class UserOut(BaseModel):
    id: UUID  # FIX: Accept UUID instead of str
    account_number: str
    name: str
    plan: str
    is_admin: bool = False
    is_technician: bool = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserOut
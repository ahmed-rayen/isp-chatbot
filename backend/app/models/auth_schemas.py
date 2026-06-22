from pydantic import BaseModel

class LoginRequest(BaseModel):
    account_number: str
    pin: str

class RegisterRequest(BaseModel):
    name: str
    pin: str

class UserOut(BaseModel):
    id: str
    account_number: str
    name: str
    plan: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserOut
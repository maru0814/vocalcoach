from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    # お知らせメールの同意（docs/88 FR-01）。省略時は未同意扱い
    newsletter_opt_in: bool = False


class NewsletterOptInRequest(BaseModel):
    opt_in: bool


class RegisterResponse(BaseModel):
    user_id: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str


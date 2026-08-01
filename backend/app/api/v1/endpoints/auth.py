from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.deps import get_current_user
from app.models.login_event import LoginEvent
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse
from app.security.passwords import hash_password, verify_password
from app.services.mail_service import send_welcome_email
from app.security.token import create_access_token


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    """ログイン状態の確認用。未ログインなら 401。"""
    return {"user_id": user.id, "email": user.email}


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    # ウェルカムメール（docs/84/85）。レスポンス返却後に実行され、失敗しても登録には影響しない
    background_tasks.add_task(send_welcome_email, user.id, user.email)
    return RegisterResponse(user_id=user.id)


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(user.id)

    # KPI「ログインUU」用のイベント記録（docs/84）。best-effort＝失敗してもログインは通す。
    try:
        db.add(LoginEvent(user_id=user.id))
        db.commit()
    except Exception:
        db.rollback()

    # FrontendはCookie参照する前提（HTTPOnly）
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_exp_minutes * 60,
        path="/",
    )

    return LoginResponse(access_token=token)


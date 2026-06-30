from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.security.token import decode_access_token


def get_current_user(
    access_token: str | None = Cookie(default=None, alias=settings.cookie_name),
    db: Session = Depends(get_db),
) -> User:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        user_id = decode_access_token(access_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_current_user_optional(
    access_token: str | None = Cookie(default=None, alias=settings.cookie_name),
    db: Session = Depends(get_db),
) -> User | None:
    """ログインしていれば User、未ログインなら None を返す（401を投げない）。

    声タイプ診断の「未登録でも1回お試し」導線で使う。認証を強制せず、
    呼び出し側が user の有無でレート制限キーや表示を切り替える。
    """
    if not access_token:
        return None
    try:
        user_id = decode_access_token(access_token)
    except Exception:
        return None
    return db.query(User).filter(User.id == user_id).first()


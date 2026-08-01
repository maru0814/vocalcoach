"""メール関連の公開エンドポイント（docs/88 FR-04 / docs/89 §3）。

配信停止はメーラーからのワンクリック動作のため GET で受ける（副作用は
opt_in=false のみ・冪等）。トークン不一致でも 200 のHTMLで完結し、
アカウントの存在推測につながる 404/500 を出さない。
"""
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/api/v1/mail", tags=["mail"])

_PAGE = """<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Hiragino Sans',Meiryo,sans-serif;
background:#f4f5f7;margin:0;padding:48px 16px;text-align:center;color:#1f2937;">
<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:32px 24px;">
<p style="font-size:16px;font-weight:bold;margin:0 0 12px;">{title}</p>
<p style="font-size:14px;line-height:1.8;margin:0;">{body}</p>
</div></body></html>"""


@router.get("/unsubscribe", response_class=HTMLResponse)
def unsubscribe(token: str = "", db: Session = Depends(get_db)) -> HTMLResponse:
    """お知らせメールのワンクリック配信停止（ログイン不要・冪等）。"""
    user = (
        db.query(User).filter(User.unsubscribe_token == token).first() if token else None
    )
    if user is None:
        return HTMLResponse(
            _PAGE.format(
                title="このリンクは無効です",
                body="お手数ですが、メール末尾のお問い合わせ先までご連絡ください。",
            )
        )
    user.newsletter_opt_in = False
    db.commit()
    return HTMLResponse(
        _PAGE.format(
            title="配信停止しました",
            body="お知らせメールは今後届きません。ご利用ありがとうございました。<br>"
            "（設定画面からいつでも再開できます）",
        )
    )

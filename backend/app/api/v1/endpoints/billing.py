import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.deps import get_current_user
from app.services import stripe_service
from app.services.billing_service import billing_me, is_premium

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


class BillingMeResponse(BaseModel):
    billing_enabled: bool
    plan: str  # "free" | "premium"
    period_end: datetime | None = None
    analysis_used: int
    analysis_limit: int | None = None  # premium / billing無効時は None（無制限）


@router.get("/me", response_model=BillingMeResponse)
def get_billing_me(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> BillingMeResponse:
    return BillingMeResponse(**billing_me(db, user.id))


class CheckoutResponse(BaseModel):
    url: str


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> CheckoutResponse:
    if not settings.stripe_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="BILLING_UNAVAILABLE")
    if is_premium(db, user.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ALREADY_PREMIUM")
    try:
        url = stripe_service.create_checkout_session(db, user)
    except Exception as e:  # noqa: BLE001
        logger.warning("checkout作成に失敗: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="CHECKOUT_FAILED")
    return CheckoutResponse(url=url)


@router.post("/portal", response_model=CheckoutResponse)
def create_portal(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> CheckoutResponse:
    if not settings.stripe_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="BILLING_UNAVAILABLE")
    try:
        url = stripe_service.create_portal_session(db, user)
    except Exception as e:  # noqa: BLE001
        logger.warning("portal作成に失敗: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="PORTAL_FAILED")
    return CheckoutResponse(url=url)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        event = stripe_service.parse_event(payload, sig)
    except Exception as e:  # 署名不正・secret未設定など
        logger.warning("webhook署名検証に失敗: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid signature")
    try:
        stripe_service.handle_event(db, event)
    except Exception as e:  # noqa: BLE001
        # 200を返さないとStripeが再送する。処理失敗はログに残しつつ500で再送を促す。
        logger.exception("webhook処理に失敗: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="handler error")
    return {"received": True}

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user
from app.services.billing_service import billing_me

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

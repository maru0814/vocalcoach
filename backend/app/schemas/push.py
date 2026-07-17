from pydantic import BaseModel, Field


class PushKeys(BaseModel):
    p256dh: str = Field(..., max_length=200)
    auth: str = Field(..., max_length=100)


class SubscribeIn(BaseModel):
    """PushManager.subscribe() の結果（endpoint + keys）をそのまま受ける。"""

    endpoint: str = Field(..., max_length=500)
    keys: PushKeys


class UnsubscribeIn(BaseModel):
    endpoint: str = Field(..., max_length=500)

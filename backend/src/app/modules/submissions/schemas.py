from typing import Literal

from pydantic import BaseModel

from app.core.schemas import ApiModel

ChannelName = Literal["manual", "email"]


class ChannelRead(ApiModel):
    name: ChannelName
    label: str
    automatic: bool
    recipient: str | None = None


class SendRequest(BaseModel):
    channel: ChannelName


class SendResponse(ApiModel):
    channel: ChannelName
    external_ref: str | None
    message: str

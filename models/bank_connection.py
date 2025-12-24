from pydantic import BaseModel
from typing import Optional

class LinkTokenRequest(BaseModel):
    user_id: str

class LinkTokenResponse(BaseModel):
    link_token: str
    expiration: str

class ExchangeTokenRequest(BaseModel):
    public_token: str

class ExchangeTokenResponse(BaseModel):
    access_token: str
    item_id: str

class SMSNotificationRequest(BaseModel):
    text: str
    date: Optional[str] = None  # Format YYYY-MM-DD

class EmailNotificationRequest(BaseModel):
    subject: str
    body: str
    date: Optional[str] = None  # Format YYYY-MM-DD

class SyncTransactionsRequest(BaseModel):
    access_token: str
    start_date: Optional[str] = None  # Format YYYY-MM-DD
    end_date: Optional[str] = None  # Format YYYY-MM-DD


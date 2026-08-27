from __future__ import annotations

from pydantic import BaseModel


class NewsCreateOrderResponse(BaseModel):
    status: str
    order_id: str
    amount: int
    currency: str
    key_id: str


class NewsVerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class NewsPaymentResponse(BaseModel):
    status: str
    message: str
    access_date: str | None = None


class NewsAccessResponse(BaseModel):
    has_access: bool
    access_date: str
    amount: int
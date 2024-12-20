from typing import TypedDict


class FakeNameUsername(TypedDict):
    name: str
    username: str


class CreateSubscription(TypedDict):
    plan_id: int
    user_uuid: str
    auto_renew: bool
    return_url: str


class RenewSubscription(CreateSubscription):
    pass


class RefundAmount(TypedDict):
    value: float | None
    currency: str | None


class RefundResponse(TypedDict):
    refund_id: str | None
    status: str | None
    payment_id: str | None
    amount: RefundAmount | None
    created_at: str | None
    description: str | None

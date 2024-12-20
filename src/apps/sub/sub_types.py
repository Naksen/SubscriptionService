from typing import TypedDict

class FakeNameUsername(TypedDict):
    name: str
    username: str

class CreateSubscription(TypedDict):
    plan_id: int
    user_uuid: str
    auto_renew: bool
    return_url: str

class RenewSubscription(TypedDict):
    auto_renew: bool
    return_url: str

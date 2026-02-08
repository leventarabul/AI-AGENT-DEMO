# demo-domain/src/demo-environment/models.py

from pydantic import BaseModel
from typing import Optional

class Event(BaseModel):
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    event_data: Optional[dict] = None
    transaction_date: str

class CampaignRuleCondition(BaseModel):
    amount: Optional[float] = None
    merchant_id: Optional[str] = None
    city: Optional[str] = None

class CampaignRule(BaseModel):
    campaign_id: int
    rule_name: str
    rule_condition: CampaignRuleCondition
    reward_amount: float
    rule_priority: int
    is_active: bool

class Campaign(BaseModel):
    name: str
    description: str
    start_date: str
    end_date: str
    status: str = "active"

class Earning(BaseModel):
    event_id: int
    campaign_id: int
    rule_id: int
    customer_id: str
    amount: float
    status: str = "pending"
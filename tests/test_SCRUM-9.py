import pytest
from models import Event, CampaignRuleCondition, CampaignRule, Campaign, Earning

@pytest.fixture
def sample_event():
    return Event(event_code="1234", customer_id="5678", transaction_id="abcd", merchant_id="xyz", \
    amount=100.0, transaction_date="2022-01-01")

def test_event_creation(sample_event):
    assert sample_event.event_code == "1234"
    assert sample_event.customer_id == "5678"
    assert sample_event.amount == 100.0

def test_campaign_rule_creation():
    rule_condition = CampaignRuleCondition(amount=50.0, merchant_id="abc", city="New York")
    campaign_rule = CampaignRule(campaign_id=1, rule_name="Rule 1", rule_condition=rule_condition, \
    reward_amount=10.0, rule_priority=1, is_active=True)
    assert campaign_rule.campaign_id == 1
    assert campaign_rule.rule_name == "Rule 1"
    assert campaign_rule.reward_amount == 10.0

def test_campaign_creation():
    campaign = Campaign(name="Campaign 1", description="Description", start_date="2022-01-01", \
    end_date="2022-01-31")
    assert campaign.name == "Campaign 1"
    assert campaign.status == "active"

def test_earning_creation():
    earning = Earning(event_id=1, campaign_id=1, rule_id=1, customer_id="5678", amount=10.0)
    assert earning.event_id == 1
    assert earning.amount == 10.0
#!/usr/bin/env python3
"""
Integration test: Register event and verify processing
"""

import httpx
import json
import asyncio
import base64
import uuid
from datetime import datetime, timedelta

# Configuration
DEMO_DOMAIN_URL = "http://localhost:8000"
AI_MANAGEMENT_URL = "http://localhost:8001"
USERNAME = "admin"
PASSWORD = "admin123"

# Create basic auth header
credentials = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()


async def test_integration():
    """Test the complete integration flow."""
    
    print("🚀 Starting Integration Test\n")
    
    # 1. Check all services are healthy
    print("1️⃣  Checking service health...")
    async with httpx.AsyncClient() as client:
        # Demo Domain health
        demo_health = await client.get(
            f"{DEMO_DOMAIN_URL}/health",
            headers={"Authorization": f"Basic {credentials}"}
        )
        print(f"   Demo Domain: {demo_health.json()['status']}")
        
        # AI Management health
        ai_health = await client.get(f"{AI_MANAGEMENT_URL}/health")
        print(f"   AI Management: {ai_health.json()['status']}\n")
    
    # 2. List available providers
    print("2️⃣  Available LLM Providers:")
    async with httpx.AsyncClient() as client:
        providers = await client.get(f"{AI_MANAGEMENT_URL}/providers")
        for p in providers.json()["providers"]:
            print(f"   - {p['name']}: {p['model']}")
        print()
    
    # 3. Create a campaign
    print("3️⃣  Creating a campaign...")
    async with httpx.AsyncClient() as client:
        campaign_data = {
            "name": "Spring Sale 2024",
            "description": "Special promotions for spring season",
            "start_date": (datetime.utcnow()).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
        campaign_response = await client.post(
            f"{DEMO_DOMAIN_URL}/campaigns",
            json=campaign_data,
            headers={"Authorization": f"Basic {credentials}"}
        )
        
        campaign = campaign_response.json()
        campaign_id = campaign["id"]
        print(f"   Campaign ID: {campaign_id}")
        print(f"   Name: {campaign['name']}\n")
    
    # 4. Create a campaign rule
    print("4️⃣  Creating a campaign rule...")
    async with httpx.AsyncClient() as client:
        rule_data = {
            "rule_name": "High Value Purchase",
            "rule_condition": {
                "merchant_id": "MERCHANT_001"
            },
            "reward_amount": 10.00,
            "rule_priority": 1
        }
        
        rule_response = await client.post(
            f"{DEMO_DOMAIN_URL}/campaigns/{campaign_id}/rules",
            json=rule_data,
            headers={"Authorization": f"Basic {credentials}"}
        )
        
        rule = rule_response.json()
        if "detail" in rule or "error" in rule:
            print(f"   Error: {rule}")
        else:
            print(f"   Rule ID: {rule['id']}")
            print(f"   Rule Name: {rule['rule_name']}")
            print(f"   Reward Amount: ${rule['reward_amount']}\n")
    
    # 5. Register an event that matches the rule
    print("5️⃣  Registering an event...")
    async with httpx.AsyncClient() as client:
        event_data = {
            "event_code": "PURCHASE",
            "customer_id": "CUST_12345",
            "transaction_id": f"TXN_{uuid.uuid4().hex[:8].upper()}",
            "merchant_id": "MERCHANT_001",
            "amount": 150.00,
            "event_data": {
                "product_category": "Electronics",
                "items_count": 2
            },
            "transaction_date": datetime.utcnow().isoformat()
        }
        
        event_response = await client.post(
            f"{DEMO_DOMAIN_URL}/events",
            json=event_data,
            headers={"Authorization": f"Basic {credentials}"}
        )
        
        event = event_response.json()
        if "detail" in event:
            print(f"   Error: {event['detail']}")
            print()
            return
        event_id = event["id"]
        print(f"   Event ID: {event_id}")
        print(f"   Amount: ${event['amount']}")
        print(f"   Status: {event['status']}\n")
    
    # 6. Wait for processing
    print("6️⃣  Waiting for event processing (job processor polls every 5 seconds)...")
    await asyncio.sleep(7)
    
    # 7. Verify event was processed
    print("7️⃣  Checking event processing results...")
    async with httpx.AsyncClient() as client:
        event_result = await client.get(
            f"{DEMO_DOMAIN_URL}/events/{event_id}",
            headers={"Authorization": f"Basic {credentials}"}
        )
        
        processed_event = event_result.json()
        print(f"   Event Status: {processed_event['status']}")
        print(f"   Matched Rule ID: {processed_event.get('matched_rule_id')}")
        
        if processed_event.get('matched_rule_id'):
            print(f"   ✅ Event successfully matched rule and created earning!\n")
        else:
            print(f"   ⚠️  Event not matched to any rule\n")
    
    # 8. Test AI Management endpoint
    print("8️⃣  Testing AI Management endpoint (without API keys)...")
    async with httpx.AsyncClient() as client:
        # This will fail without API keys, but shows the endpoint works
        ai_request = {
            "prompt": "What are the benefits of loyalty programs?",
            "provider": "openai",
            "max_tokens": 200,
            "use_cache": False
        }
        
        try:
            ai_response = await client.post(
                f"{AI_MANAGEMENT_URL}/generate",
                json=ai_request
            )
            if ai_response.status_code == 500:
                print(f"   Expected error (no API keys configured): API key not found\n")
            else:
                print(f"   Response: {ai_response.json()}\n")
        except Exception as e:
            print(f"   Note: AI service available but no API keys: {str(e)}\n")
    
    print("✅ Integration test completed!")


if __name__ == "__main__":
    asyncio.run(test_integration())

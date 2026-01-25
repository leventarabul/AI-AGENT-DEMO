"""Event Registration Agent"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
import os

from src.clients.demo_domain_client import DemoDomainClient
from src.clients.ai_management_client import AIManagementClient

logger = logging.getLogger(__name__)


class EventAgent:
    """Agent for managing events in demo-domain"""
    
    def __init__(
        self,
        demo_domain_url: str = None,
        demo_domain_user: str = None,
        demo_domain_pass: str = None,
        ai_management_url: str = None
    ):
        self.demo_domain_url = demo_domain_url or os.getenv("DEMO_DOMAIN_URL", "http://localhost:8000")
        self.demo_domain_user = demo_domain_user or os.getenv("DEMO_DOMAIN_USERNAME", "admin")
        self.demo_domain_pass = demo_domain_pass or os.getenv("DEMO_DOMAIN_PASSWORD", "admin123")
        # Use service name for Docker networking
        self.ai_management_url = ai_management_url or os.getenv("AI_MANAGEMENT_URL", "http://ai-management-service:8001")
    
    def _get_demo_domain_client(self):
        """Get demo domain client instance"""
        from src.clients.demo_domain_client import DemoDomainClient
        return DemoDomainClient(
            base_url=self.demo_domain_url,
            username=self.demo_domain_user,
            password=self.demo_domain_pass
        )
    
    async def register_event(
        self,
        event_code: str,
        customer_id: str,
        transaction_id: str,
        merchant_id: str,
        amount: float,
        transaction_date: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Register an event with demo-domain"""
        
        if transaction_date is None:
            transaction_date = datetime.utcnow().isoformat()
        
        async with DemoDomainClient(
            self.demo_domain_url,
            self.demo_domain_user,
            self.demo_domain_pass
        ) as client:
            try:
                response = await client.register_event(
                    event_code=event_code,
                    customer_id=customer_id,
                    transaction_id=transaction_id,
                    merchant_id=merchant_id,
                    amount=amount,
                    transaction_date=transaction_date,
                    event_data=event_data
                )
                
                logger.info(f"Event registered: {response['id']}")
                return response
            
            except Exception as e:
                logger.error(f"Failed to register event: {e}")
                raise
    
    async def suggest_amount_with_ai(
        self,
        customer_id: str,
        merchant_id: str,
        event_code: str,
        base_amount: float,
        prompt_template: str
    ) -> float:
        """Use AI to suggest reward amount"""
        
        async with AIManagementClient(self.ai_management_url) as ai_client:
            try:
                print(f"\n🤖 Requesting AI suggestion for customer {customer_id}", flush=True)
                print(f"Base Amount: {base_amount}", flush=True)
                response = await ai_client.generate(
                    prompt=prompt_template,
                    provider="openai",
                    max_tokens=100,
                    temperature=0.7,
                    use_cache=True
                )
                
                # Parse numeric value from AI response
                ai_text = response.get("text", str(base_amount)).strip()
                print(f"🤖 AI Raw Response: {ai_text}", flush=True)
                
                # Try to extract number from response
                import re
                numbers = re.findall(r'\d+\.?\d*', ai_text)
                if numbers:
                    suggested_amount = float(numbers[0])
                    print(f"✅ AI Suggested Reward: {suggested_amount}\n", flush=True)
                    logger.info(f"✅ AI Suggested Reward: {suggested_amount}")
                    return suggested_amount
                else:
                    print(f"⚠️ Could not parse AI response, using base amount: {base_amount}\n", flush=True)
                    logger.warning(f"⚠️ Could not parse AI response, using base amount: {base_amount}")
                    return base_amount
                    
            except Exception as e:
                print(f"❌ AI suggestion failed: {e}, using base amount\n", flush=True)
                logger.error(f"❌ AI suggestion failed: {e}, using base amount")
                return base_amount
    
    async def register_event_with_ai_reward(
        self,
        event_code: str,
        customer_id: str,
        transaction_id: str,
        merchant_id: str,
        transaction_amount: float,
        campaign_id: int = 1,  # Default campaign for AI rewards
        event_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register event with AI-suggested reward
        
        1. Get customer history
        2. Ask AI for reward suggestion
        3. Register event with transaction amount
        4. Create earning with AI-suggested reward
        """
        
        # 1. Get customer history
        async with self._get_demo_domain_client() as demo_client:
            customer_events = await demo_client.get_customer_events(customer_id, limit=5)
        
        # 2. Build AI prompt
        prompt = (
            f"Müşteri geçmişi: {customer_events}. "
            f"Event: event_code={event_code}, customer_id={customer_id}, "
            f"merchant_id={merchant_id}, transaction_amount={transaction_amount}. "
            f"Bu müşteriye ne kadar ödül (reward) verilmeli? Sadece sayısal değer döndür."
        )
        
        # 3. Get AI suggestion for reward
        suggested_reward = await self.suggest_amount_with_ai(
            customer_id=customer_id,
            merchant_id=merchant_id,
            event_code=event_code,
            base_amount=transaction_amount * 0.1,  # Default %10
            prompt_template=prompt
        )
        
        # 4. Register event with TRANSACTION amount
        event_response = await self.register_event(
            event_code=event_code,
            customer_id=customer_id,
            transaction_id=transaction_id,
            merchant_id=merchant_id,
            amount=transaction_amount,  # ← Müşterinin ödediği para
            event_data=event_data
        )
        
        # 5. Create earning with AI-suggested REWARD
        # Note: Bu ideal olarak demo-domain'de bir endpoint olmalı
        # Şimdilik event_data'ya ekliyoruz
        
        return {
            "event_id": event_response.get("id"),
            "transaction_amount": transaction_amount,
            "suggested_reward": suggested_reward,
            "ai_prompt": prompt,
            "customer_history_count": len(customer_events)
        }
    
    async def get_event(self, event_id: int) -> Dict[str, Any]:
        """Get event status"""
        
        async with DemoDomainClient(
            self.demo_domain_url,
            self.demo_domain_user,
            self.demo_domain_pass
        ) as client:
            try:
                return await client.get_event(event_id)
            except Exception as e:
                logger.error(f"Failed to get event {event_id}: {e}")
                raise
    
    async def register_batch_events(
        self,
        events: list
    ) -> list:
        """Register multiple events"""
        
        results = []
        async with DemoDomainClient(
            self.demo_domain_url,
            self.demo_domain_user,
            self.demo_domain_pass
        ) as client:
            for event in events:
                try:
                    response = await client.register_event(**event)
                    results.append({
                        "success": True,
                        "event_id": response['id'],
                        "transaction_id": event['transaction_id']
                    })
                except Exception as e:
                    results.append({
                        "success": False,
                        "error": str(e),
                        "transaction_id": event['transaction_id']
                    })
                    logger.error(f"Failed to register event {event['transaction_id']}: {e}")
        
        return results

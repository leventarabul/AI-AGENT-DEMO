"""Event Registration Agent"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from src.clients.demo_domain_client import DemoDomainClient
from src.clients.ai_management_client import AIManagementClient

logger = logging.getLogger(__name__)


class EventAgent:
    """Agent for managing events in demo-domain"""
    
    def __init__(
        self,
        demo_domain_url: str = "http://localhost:8000",
        demo_domain_user: str = "admin",
        demo_domain_pass: str = "admin123",
        ai_management_url: str = "http://localhost:8001"
    ):
        self.demo_domain_url = demo_domain_url
        self.demo_domain_user = demo_domain_user
        self.demo_domain_pass = demo_domain_pass
        self.ai_management_url = ai_management_url
    
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

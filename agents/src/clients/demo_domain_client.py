"""Client for demo-domain service"""

import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class DemoDomainClient:
    """HTTP client for demo-domain API"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        username: str = "admin",
        password: str = "admin123",
        timeout: float = 30.0
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.client = None
    
    def _get_auth(self) -> tuple:
        """Get HTTP basic auth tuple"""
        return (self.username, self.password)
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(
            auth=self._get_auth(),
            timeout=self.timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    async def health_check(self) -> bool:
        """Check service health"""
        try:
            if not self.client:
                self.client = httpx.AsyncClient(auth=self._get_auth(), timeout=self.timeout)
            
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def register_event(
        self,
        event_code: str,
        customer_id: str,
        transaction_id: str,
        merchant_id: str,
        amount: float,
        transaction_date: str,
        event_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Register an event"""
        
        payload = {
            "event_code": event_code,
            "customer_id": customer_id,
            "transaction_id": transaction_id,
            "merchant_id": merchant_id,
            "amount": amount,
            "transaction_date": transaction_date,
            "event_data": event_data or {}
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/events",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to register event: {e}")
            raise
    
    async def get_event(self, event_id: int) -> Dict[str, Any]:
        """Get event details"""
        try:
            response = await self.client.get(f"{self.base_url}/events/{event_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get event {event_id}: {e}")
            raise
    
    async def create_campaign(
        self,
        name: str,
        description: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a campaign"""
        
        payload = {
            "name": name,
            "description": description,
            "start_date": start_date,
            "end_date": end_date
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/campaigns",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create campaign: {e}")
            raise
    
    async def create_campaign_rule(
        self,
        campaign_id: int,
        rule_name: str,
        rule_condition: Dict[str, Any],
        reward_amount: float
    ) -> Dict[str, Any]:
        """Create a campaign rule"""
        
        payload = {
            "campaign_id": campaign_id,
            "rule_name": rule_name,
            "rule_condition": rule_condition,
            "reward_amount": reward_amount
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/campaigns/{campaign_id}/rules",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create campaign rule: {e}")
            raise
    
    async def get_customer_events(self, customer_id: str, limit: int = 5) -> list:
        """Get recent events for a customer (for knowledgebase prompts)"""
        try:
            params = {"customer_id": customer_id, "limit": limit}
            response = await self.client.get(f"{self.base_url}/events", params=params)
            response.raise_for_status()
            return response.json() if response.content else []
        except Exception as e:
            logger.error(f"Failed to get events for customer {customer_id}: {e}")
            return []
    
    async def create_earning(
        self,
        event_id: int,
        campaign_id: int,
        rule_id: int,
        customer_id: str,
        amount: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create an earning record (AI-suggested reward)"""
        
        payload = {
            "event_id": event_id,
            "campaign_id": campaign_id,
            "rule_id": rule_id,
            "customer_id": customer_id,
            "amount": amount,
            "status": "pending",
            "metadata": metadata or {}
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/earnings",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create earning: {e}")
            raise

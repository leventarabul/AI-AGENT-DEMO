"""Campaign Management Agent"""

import logging
from typing import Optional, Dict, Any

from src.clients.demo_domain_client import DemoDomainClient
from src.clients.ai_management_client import AIManagementClient

logger = logging.getLogger(__name__)


class CampaignAgent:
    """Agent for managing campaigns in demo-domain"""
    
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
    
    async def create_campaign(
        self,
        name: str,
        description: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new campaign"""
        
        async with DemoDomainClient(
            self.demo_domain_url,
            self.demo_domain_user,
            self.demo_domain_pass
        ) as client:
            try:
                response = await client.create_campaign(
                    name=name,
                    description=description,
                    start_date=start_date,
                    end_date=end_date
                )
                
                logger.info(f"Campaign created: {response['id']} - {name}")
                return response
            
            except Exception as e:
                logger.error(f"Failed to create campaign: {e}")
                raise
    
    async def create_rule(
        self,
        campaign_id: int,
        rule_name: str,
        rule_condition: Dict[str, Any],
        reward_amount: float
    ) -> Dict[str, Any]:
        """Create a campaign rule"""
        
        async with DemoDomainClient(
            self.demo_domain_url,
            self.demo_domain_user,
            self.demo_domain_pass
        ) as client:
            try:
                response = await client.create_campaign_rule(
                    campaign_id=campaign_id,
                    rule_name=rule_name,
                    rule_condition=rule_condition,
                    reward_amount=reward_amount
                )
                
                logger.info(f"Rule created: {response['id']} for campaign {campaign_id}")
                return response
            
            except Exception as e:
                logger.error(f"Failed to create rule: {e}")
                raise
    
    async def create_campaign_with_ai_suggestion(
        self,
        name: str,
        description: str,
        ai_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create campaign with AI-generated description"""
        
        # Use AI to enhance campaign description
        ai_description = description
        try:
            async with AIManagementClient(self.ai_management_url) as ai_client:
                prompt = f"Enhance this campaign description for marketing impact:\n\n{description}"
                
                response = await ai_client.generate(
                    prompt=prompt,
                    provider=ai_provider,
                    max_tokens=500
                )
                
                ai_description = response['text']
                logger.info(f"AI-enhanced description generated")
        
        except Exception as e:
            logger.warning(f"Failed to use AI service: {e}, using original description")
        
        # Create campaign with potentially AI-enhanced description
        return await self.create_campaign(
            name=name,
            description=ai_description
        )

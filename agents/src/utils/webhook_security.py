import hmac
import hashlib
import json
from typing import Tuple


class WebhookSecurity:
    """Helper for Jira webhook signature verification."""
    
    @staticmethod
    def verify_signature(
        payload: str,
        signature_header: str,
        secret: str
    ) -> bool:
        """
        Verify Jira webhook signature.
        
        Jira signs webhooks with HMAC-SHA256:
        signature = HMAC-SHA256(payload, secret)
        
        Args:
            payload: Raw request body (JSON string)
            signature_header: Value of X-Atlassian-Webhook-Signature header
            secret: Webhook secret key
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not signature_header or not secret:
            return False
        
        try:
            # Compute expected signature
            expected_signature = hmac.new(
                secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Signature header format: sha256=<hex>
            parts = signature_header.split("=", 1)
            if len(parts) != 2:
                return False
            
            algo, provided_signature = parts
            
            if algo != "sha256":
                return False
            
            # Compare signatures using constant-time comparison
            return hmac.compare_digest(expected_signature, provided_signature)
        
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False


# Example Jira webhook signature verification
# Expected header: X-Atlassian-Webhook-Signature: sha256=<hex>
#
# In FastAPI:
# @app.post("/webhooks/jira")
# async def jira_webhook(
#     request: JiraWebhookRequest,
#     x_atlassian_webhook_signature: str = Header(None),
# ):
#     # Get raw body for verification
#     body = await request.body()
#     
#     if not WebhookSecurity.verify_signature(
#         body.decode(),
#         x_atlassian_webhook_signature,
#         os.getenv("JIRA_WEBHOOK_SECRET")
#     ):
#         raise HTTPException(status_code=401, detail="Invalid signature")
#     
#     # Process webhook...

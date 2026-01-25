from fastapi import Request, HTTPException
from typing import Callable
import os
from src.utils.webhook_security import WebhookSecurity


async def verify_jira_webhook_signature(request: Request, call_next: Callable):
    """
    Middleware to verify Jira webhook signature.
    
    Checks:
    - X-Atlassian-Webhook-Signature header
    - Signature validity using webhook secret
    """
    # Only verify for webhook endpoints
    if not request.url.path.startswith("/webhooks/"):
        return await call_next(request)
    
    # Get signature header
    signature = request.headers.get("X-Atlassian-Webhook-Signature")
    
    # Get secret from environment
    secret = os.getenv("JIRA_WEBHOOK_SECRET")
    
    if not secret:
        print("⚠️  JIRA_WEBHOOK_SECRET not configured, skipping signature verification")
        return await call_next(request)
    
    # Read raw body for signature verification
    body = await request.body()
    
    # Verify signature
    if not WebhookSecurity.verify_signature(
        body.decode() if body else "",
        signature or "",
        secret
    ):
        print(f"❌ Invalid webhook signature from {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    print(f"✅ Valid webhook signature verified")
    
    # Call next handler
    return await call_next(request)

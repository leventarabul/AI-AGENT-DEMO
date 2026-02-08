import os
import json
import logging
import base64
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

from fastapi import FastAPI, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'campaign_demo'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'admin123'),
}

# Initialize FastAPI app
app = FastAPI(
    title="CRM Campaign API",
    description="API for tracking events and managing campaign earnings",
    version="1.0.0"
)


# Pydantic models
class EventData(BaseModel):
    """Event data model"""
    event_code: str
    customer_id: str
    transaction_id: str
    merchant_id: str
    amount: float
    transaction_date: str
    event_data: Optional[Dict[str, Any]] = None
    provision_code: Optional[str] = None
    city: Optional[str] = None
    gender: Optional[str] = None


class EventResponse(BaseModel):
    """Event response model"""
    id: int
    event_code: str
    customer_id: str
    transaction_id: str
    amount: float
    status: str
    created_at: str
    recorded_at: str


class CampaignCreate(BaseModel):
    """Campaign creation model"""
    name: str
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class CampaignRuleCreate(BaseModel):
    """Campaign rule creation model"""
    rule_name: str
    rule_condition: Dict[str, Any]
    gender: Optional[str] = None
    reward_amount: float
    rule_priority: int = 1


# Database utilities
def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise


def get_api_credentials():
    """
    Fetch API credentials from environment variables.
    
    Priority:
    1. Environment variables (API_USERNAME, API_PASSWORD)
    2. Configuration table in database (if env vars not set)
    """
    try:
        # Try environment variables first
        username = os.getenv('API_USERNAME')
        password = os.getenv('API_PASSWORD')
        
        if username and password:
            logger.info("Using API credentials from environment variables")
            return username, password
        
        # Fall back to configuration table
        logger.info("API credentials not in environment, checking database configuration table")
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT config_value FROM configuration 
            WHERE config_key = 'api_username'
        """)
        username_row = cur.fetchone()
        
        cur.execute("""
            SELECT config_value FROM configuration 
            WHERE config_key = 'api_password'
        """)
        password_row = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not username_row or not password_row:
            logger.error("API credentials not found in environment or database configuration")
            return None, None
        
        return username_row['config_value'], password_row['config_value']
    
    except Exception as e:
        logger.error(f"Error fetching API credentials: {e}")
        return None, None


def verify_basic_auth(authorization: Optional[str] = Header(None)):
    """Verify basic authentication credentials"""
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    try:
        # Parse basic auth header
        scheme, credentials = authorization.split()
        
        if scheme.lower() != "basic":
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        # Decode credentials
        decoded = base64.b64decode(credentials).decode("utf-8")
        username, password = decoded.split(":", 1)
        
        # Get credentials from database
        valid_username, valid_password = get_api_credentials()
        
        if not valid_username or not valid_password:
            raise HTTPException(status_code=500, detail="Authentication configuration error")
        
        # Verify credentials
        if username != valid_username or password != valid_password:
            logger.warning(f"Failed login attempt with username: {username}")
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        return username
    
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Basic"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


# API Endpoints

@app.get("/health")
async def health_check(authorization: Optional[str] = Header(None)):
    """Health check endpoint - requires basic authentication"""
    # Verify authentication
    verify_basic_auth(authorization)
    
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


@app.post("/admin/jobs/process-events")
async def trigger_job(background_tasks: BackgroundTasks, authorization: Optional[str] = Header(None)):
    """
    Manually trigger event processing job (admin only)
    
    Requires basic authentication. Immediately starts processing pending events.
    """
    # Verify authentication
    verify_basic_auth(authorization)
    
    try:
        # Schedule job with triggered_by='api'
        background_tasks.add_task(process_events_job, triggered_by='api')
        
        return {
            "status": "triggered",
            "message": "Event processing job started",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/jobs/execution-logs")
async def get_job_logs(
    limit: int = 20,
    status: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    Get job execution logs (admin only)
    
    Requires basic authentication.
    """
    # Verify authentication
    verify_basic_auth(authorization)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if status:
            cur.execute("""
                SELECT * FROM job_execution_logs 
                WHERE status = %s
                ORDER BY started_at DESC
                LIMIT %s
            """, (status, limit))
        else:
            cur.execute("""
                SELECT * FROM job_execution_logs 
                ORDER BY started_at DESC
                LIMIT %s
            """, (limit,))
        
        logs = cur.fetchall()
        cur.close()
        conn.close()
        
        return {
            "logs": logs,
            "total": len(logs)
        }
    except Exception as e:
        logger.error(f"Error fetching job logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/events", response_model=EventResponse)
async def create_event(event: EventData, background_tasks: BackgroundTasks, authorization: Optional[str] = Header(None)):
    """
    Register a new event with transaction details.
    
    Requires basic authentication. The event is created with 'pending' status. 
    A background task processes it against campaign rules and updates status and earnings.
    """
    # Verify authentication
    verify_basic_auth(authorization)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Insert event with all transaction details
        cur.execute("""
            INSERT INTO events 
            (event_code, customer_id, transaction_id, merchant_id, amount, 
             transaction_date, provision_code, city, gender, event_data, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, event_code, customer_id, transaction_id, amount, status, created_at, recorded_at
        """, (
            event.event_code,
            event.customer_id,
            event.transaction_id,
            event.merchant_id,
            event.amount,
            event.transaction_date,
            event.provision_code,
            event.city,
            event.gender,
            json.dumps(event.event_data) if event.event_data else json.dumps({}),
            'pending'
        ))
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        # Note: Background processing is now handled via batch job (process_events_job)
        # Scheduled by job processor or triggered via API endpoint
        # This allows better control and logging of batch operations
        # background_tasks.add_task(process_event, result['id'])
        
        return EventResponse(
            id=result['id'],
            event_code=result['event_code'],
            customer_id=result['customer_id'],
            transaction_id=result['transaction_id'],
            amount=float(result['amount']),
            status=result['status'],
            created_at=result['created_at'].isoformat(),
            recorded_at=result['recorded_at'].isoformat()
        )
    
    except psycopg2.IntegrityError as e:
        logger.error(f"Integrity error creating event: {e}")
        raise HTTPException(status_code=409, detail="Transaction ID already exists")
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events/{event_id}")
async def get_event(event_id: int, authorization: Optional[str] = Header(None)):
    """Get event details - requires basic authentication"""
    # Verify authentication
    verify_basic_auth(authorization)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM events WHERE id = %s
        """, (event_id,))
        
        event = cur.fetchone()
        cur.close()
        conn.close()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return event
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/campaigns")
async def create_campaign(campaign: CampaignCreate, authorization: Optional[str] = Header(None)):
    """Create a new campaign - requires basic authentication"""
    # Verify authentication
    verify_basic_auth(authorization)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            INSERT INTO campaigns (name, description, start_date, end_date)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """, (campaign.name, campaign.description, campaign.start_date, campaign.end_date))
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return result
    
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/campaigns/{campaign_id}/rules")
async def create_campaign_rule(campaign_id: int, rule: CampaignRuleCreate, authorization: Optional[str] = Header(None)):
    """Create a campaign rule - requires basic authentication"""
    # Verify authentication
    verify_basic_auth(authorization)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            INSERT INTO campaign_rules (campaign_id, rule_name, rule_condition, gender, reward_amount, rule_priority)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            campaign_id,
            rule.rule_name,
            json.dumps(rule.rule_condition),
            rule.gender,
            rule.reward_amount,
            rule.rule_priority,
        ))
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return result
    
    except Exception as e:
        logger.error(f"Error creating campaign rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task for event processing
def process_event(event_id: int):
    """
    Process an event against campaign rules
    
    Logic:
    1. Fetch the event
    2. Find all active campaigns with matching rules
    3. Check each rule against event data (including transaction details)
    4. Create earnings record if rule matches
    5. Update event status
    """
    logger.info(f"Processing event {event_id}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get event with all details
        cur.execute("""
            SELECT id, event_code, customer_id, merchant_id, amount, 
                   transaction_id, transaction_date, event_data, gender
            FROM events WHERE id = %s
        """, (event_id,))
        event = cur.fetchone()
        
        if not event:
            logger.error(f"Event {event_id} not found")
            return
        
        # Get active campaign rules
        cur.execute("""
            SELECT cr.*, c.id as campaign_id
            FROM campaign_rules cr
            JOIN campaigns c ON cr.campaign_id = c.id
            WHERE cr.is_active = true AND c.status = 'active'
            ORDER BY cr.rule_priority DESC
        """)
        
        rules = cur.fetchall()
        matched_rule = None
        
        # Prepare event data for rule matching (includes transaction details)
        # Handle both dict and string JSON formats from database
        if isinstance(event['event_data'], str):
            event_data = json.loads(event['event_data']) if event['event_data'] else {}
        else:
            event_data = event['event_data'] if event['event_data'] else {}
        event_data.update({
            'event_code': event['event_code'],
            'customer_id': event['customer_id'],
            'merchant_id': event['merchant_id'],
            'amount': float(event['amount']),
            'transaction_id': event['transaction_id'],
            'transaction_date': event['transaction_date'].isoformat() if event['transaction_date'] else None,
            'gender': event.get('gender'),
        })
        
        # Check rules against event data
        for rule in rules:
            rule_gender = rule.get('gender')
            if rule_gender and event_data.get('gender') != rule_gender:
                continue
            if match_rule(rule['rule_condition'], event_data):
                matched_rule = rule
                break
        
        if matched_rule:
            # Create earnings record
            cur.execute("""
                INSERT INTO earnings (event_id, campaign_id, rule_id, customer_id, amount, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                matched_rule['campaign_id'],
                matched_rule['id'],
                event['customer_id'],
                matched_rule['reward_amount'],
                'pending'
            ))
            
            # Update event status
            cur.execute("""
                UPDATE events
                SET status = 'processed', matched_rule_id = %s, processed_at = NOW(), updated_at = NOW()
                WHERE id = %s
            """, (matched_rule['id'], event_id))
            
            logger.info(f"Event {event_id} matched rule {matched_rule['id']}, created earning")
        else:
            # Update event status to skipped
            cur.execute("""
                UPDATE events
                SET status = 'skipped', processed_at = NOW(), updated_at = NOW()
                WHERE id = %s
            """, (event_id,))
            
            logger.info(f"Event {event_id} did not match any rules")
        
        conn.commit()
        cur.close()
        conn.close()
    
    except Exception as e:
        logger.error(f"Error processing event {event_id}: {e}")
        try:
            cur.execute("""
                UPDATE events
                SET status = 'failed', error_message = %s, updated_at = NOW()
                WHERE id = %s
            """, (str(e), event_id))
            conn.commit()
        except:
            pass


def process_events_job(triggered_by: str = 'scheduler'):
    """
    Batch process all pending events and log job execution
    
    Args:
        triggered_by: 'scheduler' or 'api' - indicates how job was triggered
    """
    job_start = datetime.utcnow()
    logger.info(f"Starting batch event processing job (triggered by: {triggered_by})")
    
    events_processed = 0
    events_matched = 0
    events_failed = 0
    error_msg = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get all pending events
        cur.execute("""
            SELECT id, event_code, customer_id, merchant_id, amount, 
                   transaction_id, transaction_date, event_data, gender
            FROM events WHERE status = 'pending'
            ORDER BY created_at ASC
        """)
        
        pending_events = cur.fetchall()
        
        # Process each event
        for event in pending_events:
            try:
                # Get active campaign rules
                cur.execute("""
                    SELECT cr.*, c.id as campaign_id
                    FROM campaign_rules cr
                    JOIN campaigns c ON cr.campaign_id = c.id
                    WHERE cr.is_active = true AND c.status = 'active'
                    ORDER BY cr.rule_priority DESC
                """)
                
                rules = cur.fetchall()
                matched_rule = None
                
                # Prepare event data
                if isinstance(event['event_data'], str):
                    event_data = json.loads(event['event_data']) if event['event_data'] else {}
                else:
                    event_data = event['event_data'] if event['event_data'] else {}
                
                event_data.update({
                    'event_code': event['event_code'],
                    'customer_id': event['customer_id'],
                    'merchant_id': event['merchant_id'],
                    'amount': float(event['amount']),
                    'transaction_id': event['transaction_id'],
                    'transaction_date': event['transaction_date'].isoformat() if event['transaction_date'] else None,
                    'gender': event.get('gender'),
                })
                
                # Check rules
                for rule in rules:
                    rule_gender = rule.get('gender')
                    if rule_gender and event_data.get('gender') != rule_gender:
                        continue
                    if match_rule(rule['rule_condition'], event_data):
                        matched_rule = rule
                        break
                
                if matched_rule:
                    # Create earnings
                    cur.execute("""
                        INSERT INTO earnings (event_id, campaign_id, rule_id, customer_id, amount, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        event['id'],
                        matched_rule['campaign_id'],
                        matched_rule['id'],
                        event['customer_id'],
                        matched_rule['reward_amount'],
                        'pending'
                    ))
                    
                    cur.execute("""
                        UPDATE events
                        SET status = 'processed', matched_rule_id = %s, processed_at = NOW(), updated_at = NOW()
                        WHERE id = %s
                    """, (matched_rule['id'], event['id']))
                    
                    events_matched += 1
                    logger.info(f"Event {event['id']} matched rule {matched_rule['id']}")
                else:
                    # Update to skipped
                    cur.execute("""
                        UPDATE events
                        SET status = 'skipped', processed_at = NOW(), updated_at = NOW()
                        WHERE id = %s
                    """, (event['id'],))
                    
                    logger.info(f"Event {event['id']} did not match any rules")
                
                events_processed += 1
            
            except Exception as e:
                logger.error(f"Error processing event {event['id']}: {e}")
                try:
                    cur.execute("""
                        UPDATE events
                        SET status = 'failed', error_message = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (str(e), event['id']))
                except:
                    pass
                events_failed += 1
        
        conn.commit()
        cur.close()
        conn.close()
        
        job_end = datetime.utcnow()
        duration = int((job_end - job_start).total_seconds())
        
        # Log job execution
        try:
            log_job_execution(
                job_name='process_events',
                started_at=job_start,
                ended_at=job_end,
                status='completed',
                events_processed=events_processed,
                events_matched=events_matched,
                events_failed=events_failed,
                triggered_by=triggered_by,
                duration_seconds=duration
            )
        except Exception as e:
            logger.error(f"Error logging job execution: {e}")
        
        logger.info(f"Job completed: {events_processed} processed, {events_matched} matched, {events_failed} failed, duration: {duration}s")
    
    except Exception as e:
        logger.error(f"Error in event processing job: {e}")
        error_msg = str(e)
        
        job_end = datetime.utcnow()
        duration = int((job_end - job_start).total_seconds())
        
        try:
            log_job_execution(
                job_name='process_events',
                started_at=job_start,
                ended_at=job_end,
                status='failed',
                events_processed=events_processed,
                events_matched=events_matched,
                events_failed=events_failed,
                error_message=error_msg,
                triggered_by=triggered_by,
                duration_seconds=duration
            )
        except:
            pass


def log_job_execution(
    job_name: str,
    started_at: datetime,
    ended_at: datetime,
    status: str,
    events_processed: int = 0,
    events_matched: int = 0,
    events_failed: int = 0,
    error_message: Optional[str] = None,
    triggered_by: str = 'scheduler',
    duration_seconds: int = 0
):
    """Log job execution to database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO job_execution_logs 
            (job_name, started_at, ended_at, status, events_processed, events_matched, events_failed, error_message, triggered_by, duration_seconds)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            job_name,
            started_at,
            ended_at,
            status,
            events_processed,
            events_matched,
            events_failed,
            error_message,
            triggered_by,
            duration_seconds
        ))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log job execution: {e}")


def match_rule(rule_condition: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
    """
    Check if event data matches rule condition
    
    Rule condition format:
    {
        "field": "value",
        "nested_field.sub": "value",
        ...
    }
    """
    try:
        for key, expected_value in rule_condition.items():
            # Simple dot-notation path resolver
            keys = key.split('.')
            current = event_data
            
            for k in keys:
                if isinstance(current, dict):
                    current = current.get(k)
                else:
                    return False
            
            if current != expected_value:
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error matching rule: {e}")
        return False


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

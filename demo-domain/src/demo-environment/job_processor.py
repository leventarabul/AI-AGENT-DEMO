import os
import json
import logging
import time
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'campaign_demo'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'admin123'),
}


class EventProcessor:
    """Process pending events and match them against campaign rules"""
    
    def __init__(self):
        self.running = True
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '5'))  # seconds
    
    def get_connection(self):
        """Create database connection"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def process_pending_events(self):
        """Fetch and process pending events"""
        try:
            conn = self.get_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get pending events with transaction details
            cur.execute("""
                SELECT id, event_code, customer_id, merchant_id, amount, 
                       transaction_id, transaction_date, event_data
                FROM events
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 100
            """)
            
            pending_events = cur.fetchall()
            cur.close()
            
            if not pending_events:
                return 0
            
            logger.info(f"Found {len(pending_events)} pending events to process")
            
            processed_count = 0
            for event in pending_events:
                if self.process_single_event(event):
                    processed_count += 1
            
            conn.close()
            return processed_count
        
        except Exception as e:
            logger.error(f"Error processing pending events: {e}")
            return 0
    
    def process_single_event(self, event: dict) -> bool:
        """
        Process a single event
        
        Returns:
            True if processed successfully, False otherwise
        """
        event_id = event['id']
        
        try:
            conn = self.get_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get active campaign rules
            cur.execute("""
                SELECT cr.*, c.id as campaign_id
                FROM campaign_rules cr
                JOIN campaigns c ON cr.campaign_id = c.id
                WHERE cr.is_active = true AND c.status = 'active'
                ORDER BY cr.rule_priority DESC
            """)
            
            rules = cur.fetchall()
            
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
                'transaction_date': event['transaction_date'].isoformat() if event['transaction_date'] else None
            })
            
            # Try to match against rules
            matched_rule = None
            for rule in rules:
                if self.match_rule(rule['rule_condition'], event_data):
                    matched_rule = rule
                    break
            
            if matched_rule:
                # Create earnings record
                cur.execute("""
                    INSERT INTO earnings (event_id, campaign_id, rule_id, customer_id, amount, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    event_id,
                    matched_rule['campaign_id'],
                    matched_rule['id'],
                    event['customer_id'],
                    matched_rule['reward_amount'],
                    'pending'
                ))
                
                earning_id = cur.fetchone()['id']
                
                # Update event status to processed
                cur.execute("""
                    UPDATE events
                    SET status = 'processed',
                        matched_rule_id = %s,
                        processed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                """, (matched_rule['id'], event_id))
                
                logger.info(
                    f"Event {event_id} processed: matched rule {matched_rule['id']}, "
                    f"created earning {earning_id}, amount {matched_rule['reward_amount']}"
                )
            else:
                # Update event status to skipped (no matching rule)
                cur.execute("""
                    UPDATE events
                    SET status = 'skipped',
                        processed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                """, (event_id,))
                
                logger.info(f"Event {event_id} skipped: no matching rules")
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        
        except Exception as e:
            logger.error(f"Error processing event {event_id}: {e}")
            
            # Mark event as failed
            try:
                conn = self.get_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE events
                    SET status = 'failed',
                        error_message = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (str(e), event_id))
                conn.commit()
                cur.close()
                conn.close()
            except Exception as cleanup_error:
                logger.error(f"Error marking event as failed: {cleanup_error}")
            
            return False
    
    def match_rule(self, rule_condition: dict, event_data: dict) -> bool:
        """
        Check if event data matches rule condition
        
        Rule condition format:
        {
            "field": "value",
            "nested.field": "value",
            ...
        }
        
        Uses dot notation for nested field access.
        """
        try:
            for key, expected_value in rule_condition.items():
                # Resolve nested fields using dot notation
                keys = key.split('.')
                current = event_data
                
                for k in keys:
                    if isinstance(current, dict):
                        current = current.get(k)
                    else:
                        return False
                
                # Check if value matches
                if current != expected_value:
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error matching rule: {e}")
            return False
    
    def run(self):
        """Main processing loop"""
        logger.info("Event Processor started")
        logger.info(f"Poll interval: {self.poll_interval} seconds")
        
        try:
            # Test database connection on startup
            conn = self.get_connection()
            conn.close()
            logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
        
        while self.running:
            try:
                processed = self.process_pending_events()
                
                if processed > 0:
                    logger.info(f"Processed {processed} events in this cycle")
                
                # Wait before next poll
                time.sleep(self.poll_interval)
            
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                self.running = False
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(self.poll_interval)
        
        logger.info("Event Processor stopped")


if __name__ == "__main__":
    processor = EventProcessor()
    processor.run()

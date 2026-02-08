### FILE: demo-domain/src/demo-environment/init.sql
ALTER TABLE events ADD COLUMN gender VARCHAR(10);

### FILE: demo-domain/src/demo-environment/api_server.py
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

@app.post("/register_event", response_model=EventResponse)
async def register_event(event_data: EventData, x_token: str = Header(...)):
    """Register a new event"""
    try:
        # Check authentication
        validate_token(x_token)
        
        # Save event to database
        event = await save_event_to_db(event_data)
        
        return event
    except Exception as e:
        logging.error(f"Error registering event: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

### FILE: demo-domain/src/demo-environment/job_processor.py
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
        
        for rule in rules:
            if match_rule(rule['rule_condition'], event):
                # Gender check
                if 'gender' in event and event['gender'] == 'male':
                    return False
                
                # Process rule and update earnings
                process_rule_and_earnings(event, rule)
                return True
        
        return False
    
    except Exception as e:
        logging.error(f"Error processing event: {e}")
        return False
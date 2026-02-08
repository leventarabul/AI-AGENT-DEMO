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

@app.post("/events/")
async def create_event(event_data: EventData, background_tasks: BackgroundTasks):
    # Your code to create an event with gender information

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
            WHERE cr.is_active = true
            AND c.status = 'active'
            ORDER BY cr.rule_priority DESC
        """)
        
        rules = cur.fetchall()
        cur.close()
        
        if not rules:
            return False
        
        for rule in rules:
            rule_condition = rule['rule_condition']
            if 'gender' in rule_condition:
                if event.get('gender') != rule_condition['gender']:
                    continue
            if self.match_rule(rule_condition, event):
                # Process the event based on the matched rule
                return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error processing event: {e}")
        return False
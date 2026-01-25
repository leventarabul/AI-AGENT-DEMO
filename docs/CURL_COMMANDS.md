# Demo Domain Service - Curl Commands

Quick reference curl commands for testing the API.

## Authentication
All endpoints (except `/health`) require HTTP Basic Auth:
```
-u {USERNAME}:{PASSWORD}
```

**Note:** Replace `{USERNAME}` and `{PASSWORD}` with values from `.env` file. See [SECURITY.md](SECURITY.md) for credential management details.

## 1. Create Campaign

```bash
curl -X POST -u {USERNAME}:{PASSWORD} http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Spring Bonus 2026",
    "description": "Special rewards for spring season",
    "start_date": "2026-01-25T00:00:00",
    "end_date": "2026-03-25T23:59:59"
  }' | jq .
```

Response includes `id` (e.g., `2`).

## 2. Create Campaign Rule

Replace `{CAMPAIGN_ID}` with ID from step 1:

```bash
curl -X POST -u {USERNAME}:{PASSWORD} http://localhost:8000/campaigns/2/rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_name": "Premium Merchant Bonus",
    "rule_condition": {
      "merchant_id": "MERCHANT_001"
    },
    "reward_amount": 15.50,
    "rule_priority": 1
  }' | jq .
```

Rule condition supports any key-value matching from event data.

## 3. Register Event

```bash
curl -X POST -u {USERNAME}:{PASSWORD} http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_code": "PURCHASE",
    "customer_id": "CUST_ABC123",
    "transaction_id": "TXN_UNIQUE_001",
    "merchant_id": "MERCHANT_001",
    "amount": 250.75,
    "event_data": {
      "product_type": "Electronics",
      "items": 3
    },
    "transaction_date": "2026-01-25T15:13:00Z"
  }' | jq .
```

Response includes event `id` and `status: "pending"`.

**Note:** Event is created with `pending` status and must be processed by job.

## 4. Manually Trigger Event Processing Job

```bash
curl -X POST -u {USERNAME}:{PASSWORD} http://localhost:8000/admin/jobs/process-events \
  -H "Content-Type: application/json" | jq .
```

Response:
```json
{
  "status": "triggered",
  "message": "Event processing job started",
  "timestamp": "2026-01-25T15:13:24.524793"
}
```

The job will:
1. Query all pending events
2. Match each against active campaign rules
3. Create earnings records if matched
4. Update event status to `processed` or `skipped`
5. Log execution details

## 5. Get Event Details

Replace `{EVENT_ID}` with ID from step 3:

```bash
curl -u {USERNAME}:{PASSWORD} http://localhost:8000/events/3 | jq .
```

Response includes updated status and `matched_rule_id` if processed.

## 6. View Job Execution Logs

```bash
curl -u {USERNAME}:{PASSWORD} 'http://localhost:8000/admin/jobs/execution-logs?limit=5' | jq .
```

Query parameters:
- `limit` - Max number of logs (default: 20)
- `status` - Filter by status (`running`, `completed`, `failed`)

Response includes:
```json
{
  "id": 3,
  "job_name": "process_events",
  "started_at": "2026-01-25T15:14:31.527146",
  "ended_at": "2026-01-25T15:14:31.540700",
  "status": "completed",
  "events_processed": 1,
  "events_matched": 1,
  "events_failed": 0,
  "error_message": null,
  "duration_seconds": 0,
  "triggered_by": "api",
  "created_at": "2026-01-25T15:14:31.544807"
}
```

## Complete Workflow Example

```bash
#!/bin/bash

# 1. Create campaign
CAMPAIGN=$(curl -s -X POST -u {USERNAME}:{PASSWORD} http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Campaign","description":"Test","start_date":"2026-01-25T00:00:00","end_date":"2026-12-31T23:59:59"}')
CAMPAIGN_ID=$(echo $CAMPAIGN | jq -r '.id')
echo "Campaign ID: $CAMPAIGN_ID"

# 2. Create rule
RULE=$(curl -s -X POST -u {USERNAME}:{PASSWORD} http://localhost:8000/campaigns/$CAMPAIGN_ID/rules \
  -H "Content-Type: application/json" \
  -d '{"rule_name":"Bonus Rule","rule_condition":{"merchant_id":"MERCHANT_001"},"reward_amount":10.00,"rule_priority":1}')
RULE_ID=$(echo $RULE | jq -r '.id')
echo "Rule ID: $RULE_ID"

# 3. Register event
EVENT=$(curl -s -X POST -u {USERNAME}:{PASSWORD} http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{"event_code":"PURCHASE","customer_id":"CUST_001","transaction_id":"TXN_'$(date +%s)'","merchant_id":"MERCHANT_001","amount":100.00,"event_data":{"qty":1},"transaction_date":"'$(date -u +'%Y-%m-%dT%H:%M:%SZ')'"}')
EVENT_ID=$(echo $EVENT | jq -r '.id')
echo "Event ID: $EVENT_ID - Status: $(echo $EVENT | jq -r '.status')"

# 4. Process event
echo "Triggering job..."
curl -s -X POST -u {USERNAME}:{PASSWORD} http://localhost:8000/admin/jobs/process-events | jq .

# 5. Check result
sleep 2
echo "Event after processing:"
curl -s -u {USERNAME}:{PASSWORD} http://localhost:8000/events/$EVENT_ID | jq '.status, .matched_rule_id'

# 6. View logs
echo "Latest job execution:"
curl -s -u {USERNAME}:{PASSWORD} 'http://localhost:8000/admin/jobs/execution-logs?limit=1' | jq '.logs[0]'
```

## Event Status Lifecycle

```
Event Registration
      ↓
   pending
      ↓
Job Triggered
      ↓
   processed  (rule matched)
   OR
   skipped    (no matching rule)
   OR
   failed     (error during processing)
```

## Job Execution Logging

Every job execution creates a log entry with:
- **started_at** - When job started
- **ended_at** - When job completed
- **status** - `completed` or `failed`
- **events_processed** - Count of pending events processed
- **events_matched** - Count of events that matched rules
- **events_failed** - Count of processing errors
- **duration_seconds** - Total execution time
- **triggered_by** - How job was triggered (`api`, `scheduler`)

## Troubleshooting

### Event stays in pending status
- Check if rule condition matches event data
- Verify campaign and rule are active
- Trigger job manually via `/admin/jobs/process-events`

### Job shows 0 events processed
- Check if there are pending events: `SELECT * FROM events WHERE status = 'pending'`
- Verify database connection
- Check API logs: `docker logs demo-domain-api`

### Event not matching rule
- Verify rule_condition matches event data exactly
- Check field names are correct (case-sensitive)
- Test with simple conditions first

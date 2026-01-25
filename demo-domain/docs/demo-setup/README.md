# Demo Environment Setup Guide

This directory contains the complete CRM Campaign demo environment implementation.

## Architecture Overview

The system consists of three main components:

1. **PostgreSQL Database** - Stores campaigns, rules, events, and earnings
2. **FastAPI Server** - REST API for event registration and campaign management
3. **Job Processor** - Background worker that processes events and applies campaign rules

### Data Flow

```
Event Registration (API)
        ↓
    Pending Event
        ↓
  Job Processor
        ↓
Match Campaign Rules
        ↓
    Create Earnings / Update Status
```

## Database Schema

### campaigns
- `id`: Campaign identifier
- `name`: Campaign name
- `description`: Campaign description
- `status`: active | inactive | archived
- `start_date`, `end_date`: Campaign validity period

### campaign_rules
- `id`: Rule identifier
- `campaign_id`: Parent campaign
- `rule_name`: Rule description
- `rule_condition`: JSONB - Conditions to match against event data
- `reward_amount`: Amount to reward when rule matches
- `rule_priority`: Order to evaluate rules (higher priority first)
- `is_active`: Whether rule is enabled

### events
- `id`: Event identifier
- `event_code`: Event code/type
- `customer_id`: Customer identifier
- `transaction_id`: Unique transaction identifier
- `merchant_id`: Merchant identifier
- `amount`: Transaction amount
- `transaction_date`: When the transaction occurred
- `event_data`: JSONB - Additional event payload
- `status`: pending | processed | failed | skipped
- `matched_rule_id`: Rule that matched this event
- `error_message`: Error details if processing failed
- `created_at`: When the record was inserted
- `recorded_at`: When the transaction was recorded
- `processed_at`: When the event was processed

### earnings
- `id`: Earning identifier
- `event_id`: Associated event
- `campaign_id`: Associated campaign
- `rule_id`: Rule that triggered the earning
- `customer_id`: Customer identifier
- `amount`: Reward amount
- `status`: pending | completed | cancelled

## Setup Instructions

### Prerequisites

- Docker and Docker Compose installed
- Python 3.9+ installed
- PostgreSQL client (optional, for debugging)

### 1. Configure Environment Variables

```bash
cd src/demo-environment
cp .env.example .env
# Edit .env with your database and API credentials
```

### 2. Start the Database

```bash
docker compose up -d
```

This starts PostgreSQL with the initialized schema.

Verify the database is running:
```bash
docker compose ps
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the API Server

```bash
python api_server.py
```

The API will be available at `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

### 5. Start the Job Processor

In a separate terminal:

```bash
python job_processor.py
```

The processor will start polling for pending events every 5 seconds.

## Security Configuration

All sensitive information (credentials, API keys, database passwords) are managed via environment variables and **NEVER committed to git**.

### Environment Variables Setup

1. Create a `.env` file in the `src/demo-environment/` directory based on `.env.example`:

```bash
cp .env.example .env
```

2. Edit `.env` with your actual credentials:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=campaign_demo
DB_USER=admin
DB_PASSWORD=your_secure_password

API_USERNAME=your_api_user
API_PASSWORD=your_api_password

POLL_INTERVAL=5
```

### Important Security Rules

- **Never commit `.env` files to git** - they are in `.gitignore`
- Use `.env.example` as a template (with empty values)
- Each developer creates their own `.env` with local credentials
- Database passwords and API keys are loaded from environment variables
- For production, use a secrets management system (HashiCorp Vault, AWS Secrets Manager, etc.)

### Updating Credentials

#### Via Environment Variables (Recommended)
Set credentials in `.env` file - they are loaded on application startup.

#### Via Database
If you need to change credentials at runtime, update the configuration table:

```sql
UPDATE configuration 
SET config_value = 'your_new_username'
WHERE config_key = 'api_username';

UPDATE configuration 
SET config_value = 'your_new_password'
WHERE config_key = 'api_password';
```

---

## API Endpoints

### Health Check
```
GET /health
Authorization: Basic admin:admin123
```

Returns system status and database connectivity.

### Create Event
```
POST /events
Authorization: Basic admin:admin123
Content-Type: application/json

{
  "event_code": "purchase",
  "customer_id": "cust_123",
  "transaction_id": "txn_abc123",
  "merchant_id": "merch_456",
  "amount": 99.99,
  "transaction_date": "2024-01-25T10:30:00",
  "event_data": {
    "product_id": "prod_789",
    "product_category": "subscription"
  }
}
```

Response:
```json
{
  "id": 1,
  "event_code": "purchase",
  "customer_id": "cust_123",
  "transaction_id": "txn_abc123",
  "amount": 99.99,
  "status": "pending",
  "created_at": "2024-01-25T10:30:00",
  "recorded_at": "2024-01-25T10:30:00"
}
```

### Get Event Details
```
GET /events/{event_id}
Authorization: Basic admin:admin123
```

Returns complete event information including status and matched rule.

### Create Campaign
```
POST /campaigns
Authorization: Basic admin:admin123
Content-Type: application/json

{
  "name": "January Promo",
  "description": "Special promotion for January",
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2024-01-31T23:59:59"
}
```

### Create Campaign Rule
```
POST /campaigns/{campaign_id}/rules
Authorization: Basic admin:admin123
Content-Type: application/json

{
  "campaign_id": 1,
  "rule_name": "High Value Purchase Bonus",
  "rule_condition": {
    "amount": 100,
    "product": "subscription"
  },
  "reward_amount": 50
}
```

## Rule Matching Logic

Rules are evaluated using dot-notation pattern matching against event data.

Event data automatically includes transaction details:
- `event_code`
- `customer_id`
- `merchant_id`
- `amount`
- `transaction_id`
- `transaction_date`
- Plus any additional fields in the `event_data` JSONB

### Example

Campaign Rule:
```json
{
  "rule_condition": {
    "amount": 99.99,
    "event_code": "purchase",
    "merchant_id": "merch_456"
  },
  "reward_amount": 50
}
```

Event Data:
```json
{
  "event_code": "purchase",
  "customer_id": "cust_123",
  "merchant_id": "merch_456",
  "amount": 99.99,
  "transaction_id": "txn_abc123",
  "transaction_date": "2024-01-25T10:30:00",
  "product_id": "prod_789"
}
```

Result: Rule matches, earning of 50 is created.

## Running a Complete Example

### 1. Create a Campaign

```bash
curl -u admin:admin123 -X POST http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Welcome Bonus",
    "description": "First purchase bonus"
  }'
```

Response:
```json
{
  "id": 1,
  "name": "Welcome Bonus",
  ...
}
```

### 2. Create a Rule

```bash
curl -u admin:admin123 -X POST http://localhost:8000/campaigns/1/rules \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": 1,
    "rule_name": "High Value Purchase Bonus",
    "rule_condition": {
      "event_code": "purchase",
      "amount": 99.99
    },
    "reward_amount": 25
  }'
```

### 3. Register an Event

```bash
curl -u admin:admin123 -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_code": "purchase",
    "customer_id": "cust_123",
    "transaction_id": "txn_20240125_001",
    "merchant_id": "merch_456",
    "amount": 99.99,
    "transaction_date": "2024-01-25T10:30:00",
    "event_data": {
      "product_id": "prod_789"
    }
  }'
```

### 4. Check Event Status (wait a few seconds for processing)

```bash
curl -u admin:admin123 http://localhost:8000/events/1
```

Response should show `status: "processed"` with `matched_rule_id: 1`

### 5. Verify Earnings in Database

```bash
# Connect to PostgreSQL
psql -h localhost -U admin -d campaign_demo

# Query earnings
SELECT * FROM earnings;
```

## Environment Variables

Create `.env` file based on `.env.example`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crm_demo
DB_USER=admin
DB_PASSWORD=admin123
API_PORT=8000
POLL_INTERVAL=5
```

## Troubleshooting

### Database Connection Failed

- Check if Docker container is running: `docker-compose ps`
- Verify credentials in `.env`
- Check network: `docker network ls`

### Events Not Processing

- Check job processor is running
- Verify `POLL_INTERVAL` is set
- Check logs: `docker-compose logs postgres`

### Rule Not Matching

- Verify rule condition JSON syntax
- Check event data structure matches condition
- Use JSON viewer to debug event data

## Stopping the System

```bash
# Stop API and Job Processor (Ctrl+C in their terminals)

# Stop Database
docker-compose down

# Stop and remove volumes (careful - deletes data)
docker-compose down -v
```

---

Next: See the [agents](https://github.com/yourusername/agents) repository to build agents that interact with this API.

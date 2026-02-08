-- CRM Campaign Database Schema

-- Campaigns table
CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'archived')),
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Campaign Rules table
CREATE TABLE campaign_rules (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    rule_name VARCHAR(255) NOT NULL,
    rule_condition JSONB NOT NULL, -- JSON structure for rule conditions
    reward_amount DECIMAL(10, 2) NOT NULL,
    rule_priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Events table
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_code VARCHAR(100) NOT NULL,
    customer_id VARCHAR(255) NOT NULL,
    transaction_id VARCHAR(255) UNIQUE NOT NULL,
    merchant_id VARCHAR(255) NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    transaction_date TIMESTAMP NOT NULL,
    provision_code VARCHAR(255),
    city VARCHAR(100),
    event_data JSONB,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processed', 'failed', 'skipped')),
    matched_rule_id INTEGER REFERENCES campaign_rules(id),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Earnings table
CREATE TABLE earnings (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    rule_id INTEGER NOT NULL REFERENCES campaign_rules(id) ON DELETE CASCADE,
    customer_id VARCHAR(255) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_events_customer_id ON events(customer_id);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_created_at ON events(created_at);
CREATE INDEX idx_events_city ON events(city);
CREATE INDEX idx_campaign_rules_campaign_id ON campaign_rules(campaign_id);
CREATE INDEX idx_campaign_rules_active ON campaign_rules(is_active);
CREATE INDEX idx_earnings_customer_id ON earnings(customer_id);
CREATE INDEX idx_earnings_campaign_id ON earnings(campaign_id);
CREATE INDEX idx_earnings_status ON earnings(status);

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Configuration table for API credentials and settings
CREATE TABLE configuration (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(255) UNIQUE NOT NULL,
    config_value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job Execution Logs table (for tracking background job runs)
CREATE TABLE job_execution_logs (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(255) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    status VARCHAR(50) NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    events_processed INTEGER DEFAULT 0,
    events_matched INTEGER DEFAULT 0,
    events_failed INTEGER DEFAULT 0,
    error_message TEXT,
    duration_seconds INTEGER,
    triggered_by VARCHAR(50) DEFAULT 'scheduler' CHECK (triggered_by IN ('scheduler', 'api', 'manual')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for job logs
CREATE INDEX idx_job_execution_logs_name ON job_execution_logs(job_name);
CREATE INDEX idx_job_execution_logs_started ON job_execution_logs(started_at DESC);
CREATE INDEX idx_job_execution_logs_status ON job_execution_logs(status);

-- Initialize configuration table structure (values set via environment variables)
INSERT INTO configuration (config_key, config_value, description) VALUES
('api_username', '', 'API username for basic authentication - set via environment variable'),
('api_password', '', 'API password for basic authentication - set via environment variable')
ON CONFLICT (config_key) DO NOTHING;

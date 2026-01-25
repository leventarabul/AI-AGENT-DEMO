# API Contracts

## ai-management
- POST /generate
  - Body: `{ provider, prompt, max_tokens?, temperature?, use_cache? }`
  - Response: `{ text, cached, usage? }`

## demo-domain
- POST /events
  - Body: `{ event_code, customer_id, transaction_id, merchant_id, amount, event_data? }`
  - Auth: Basic (`API_USERNAME`, `API_PASSWORD`)
  - Response: `{ id, ... }`

## agents
- POST /ai-events
  - Body: `{ event_code, customer_id, transaction_id, merchant_id, base_amount, event_data? }`
  - Response: `{ event_id, transaction_amount, suggested_reward, ai_prompt, customer_history_count }`

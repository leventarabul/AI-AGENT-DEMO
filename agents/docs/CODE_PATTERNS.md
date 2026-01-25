# Code Patterns

## Async HTTP
```python
async with httpx.AsyncClient(timeout=30) as client:
    resp = await client.post(url, json=payload, auth=(user, pwd))
    resp.raise_for_status()
```

## Prompt Construction
```python
prompt = (
    f"Müşteri geçmişi: {history}. "
    f"Event: event_code={event_code}, customer_id={cid}, "
    f"merchant_id={mid}, transaction_amount={amount}. "
    "Bu müşteriye ne kadar ödül (reward) verilmeli? Sadece sayısal değer döndür."
)
```

## Logging (OpenAI)
- Print URL, JSON request, and JSON response (pretty-printed)
- Include token usage when available

#!/usr/bin/env python3
"""Trigger MVP Jira flow via Agents webhook.

Usage:
  python scripts/run_mvp_jira_flow_demo.py --issue-key ABC-123 --base-url http://localhost:8002
"""

import argparse
import json
import sys
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MVP Jira flow demo")
    parser.add_argument("--issue-key", required=True, help="Jira issue key (e.g., ABC-123)")
    parser.add_argument("--base-url", default="http://localhost:8002", help="Agents base URL")
    args = parser.parse_args()

    payload = {
        "webhookEvent": "jira:issue_updated",
        "issue_key": args.issue_key,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        f"{args.base_url.rstrip('/')}/webhooks/jira",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlrequest.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        print(f"HTTP {exc.code}: {body}")
        return 1
    except URLError as exc:
        print(f"Request failed: {exc}")
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())

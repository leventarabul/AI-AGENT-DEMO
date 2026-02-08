import base64
import httpx
import json
from typing import Optional, Dict, Any, List


class JiraClient:
    """Async Jira HTTP client for issue management."""
    
    def __init__(self, jira_url: str, username: str, api_token: str, timeout: int = 30):
        self.jira_url = jira_url.rstrip("/")
        self.username = username
        self.api_token = api_token
        self.timeout = timeout
        self._auth_header = self._build_auth_header()
    
    def _build_auth_header(self) -> Dict[str, str]:
        """Build Basic Auth header for Jira API."""
        creds = f"{self.username}:{self.api_token}"
        encoded = base64.b64encode(creds.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    
    async def get_issue(self, issue_key: str, fields: Optional[str] = None) -> Dict[str, Any]:
        """Fetch a single Jira issue by key."""
        url = f"{self.jira_url}/rest/api/3/issue/{issue_key}"
        params = {}
        if fields:
            params["fields"] = fields
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                url,
                params=params,
                headers=self._auth_header,
            )
            resp.raise_for_status()
            return resp.json()
    
    async def search_issues(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search issues using JQL and return list of issues.

        Jira /search/jql endpoint requires explicit fields parameter to include key.
        """
        url = f"{self.jira_url}/rest/api/3/search/jql"
        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": "key,status,summary,description,issuetype,labels",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                url,
                params=params,
                headers=self._auth_header,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("issues", [])
    
    async def get_issue_by_status(self, status: str, project_key: Optional[str] = None) -> \
    List[Dict[str, Any]]:
        """Fetch issues by status."""
        if project_key:
            jql = f'project = {project_key} AND status = "{status}"'
        else:
            jql = f'status = "{status}"'
        
        result = await self.search_issues(jql)
        return result.get("issues", [])
    
    async def add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """Add a comment to an issue."""
        url = f"{self.jira_url}/rest/api/3/issue/{issue_key}/comment"
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment,
                            }
                        ],
                    }
                ],
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={**self._auth_header, "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()
    
    async def transition_issue(self, issue_key: str, transition_id: str, comment: Optional[str] = None) \
    \
    \
    \
    \
    -> None:
        """Transition issue to a new status."""
        url = f"{self.jira_url}/rest/api/3/issue/{issue_key}/transitions"
        payload = {
            "transition": {
                "id": transition_id,
            }
        }
        if comment:
            payload["update"] = {
                "comment": [
                    {
                        "add": {
                            "body": {
                                "type": "doc",
                                "version": 1,
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": comment,
                                            }
                                        ],
                                    }
                                ],
                            }
                        }
                    }
                ]
            }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={**self._auth_header, "Content-Type": "application/json"},
            )
            resp.raise_for_status()
    
    async def get_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get available transitions for an issue."""
        url = f"{self.jira_url}/rest/api/3/issue/{issue_key}/transitions"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                url,
                headers=self._auth_header,
            )
            resp.raise_for_status()
            result = resp.json()
            return result.get("transitions", [])

    async def get_comments(self, issue_key: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Fetch comments for an issue."""
        url = f"{self.jira_url}/rest/api/3/issue/{issue_key}/comment"
        params = {"maxResults": max_results}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                url,
                params=params,
                headers=self._auth_header,
            )
            resp.raise_for_status()
            result = resp.json()
            return result.get("comments", [])

    async def delete_comment(self, issue_key: str, comment_id: str) -> None:
        """Delete a comment from an issue."""
        url = f"{self.jira_url}/rest/api/3/issue/{issue_key}/comment/{comment_id}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.delete(
                url,
                headers=self._auth_header,
            )
            resp.raise_for_status()

    async def update_issue_fields(self, issue_key: str, fields: Dict[str, Any]) -> None:
        """Update issue fields (e.g., labels) for an issue."""
        url = f"{self.jira_url}/rest/api/3/issue/{issue_key}"
        payload = {"fields": fields}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.put(
                url,
                json=payload,
                headers={**self._auth_header, "Content-Type": "application/json"},
            )
            resp.raise_for_status()

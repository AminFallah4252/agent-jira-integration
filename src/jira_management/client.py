"""Zero-dependency, cross-platform Jira REST API client for Cloud v3 and Server v2."""

from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Union

from .adf import text_to_adf


class JiraApiError(Exception):
    """Exception raised when a Jira REST API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class JiraClient:
    """Zero-dependency, cross-platform Jira REST API client.

    Supports:
    - Jira Cloud (REST API v3 & Agile API 1.0) with Basic Auth (email + API token)
    - Jira Data Center / Server (REST API v2) with Personal Access Token (Bearer auth)
    - Automatic JSON serialization, ADF formatting, and error parsing.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        email: Optional[str] = None,
        timeout: int = 30
    ):
        clean_url = base_url.strip().rstrip("/")
        if not clean_url.startswith(("http://", "https://")):
            clean_url = f"https://{clean_url}"

        self.base_url = clean_url
        self.token = token.strip()
        self.email = email.strip() if email else None
        self.timeout = timeout

        # Build Authorization Header
        if self.email:
            auth_str = f"{self.email}:{self.token}"
            encoded = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")
            self.auth_header = f"Basic {encoded}"
        else:
            token_clean = self.token.replace("Bearer ", "").strip()
            self.auth_header = f"Bearer {token_clean}"

        # SSL context
        self.ssl_context = ssl.create_default_context()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        api_version: str = "3"
    ) -> Any:
        """Execute an HTTP request to Jira REST API."""
        url = endpoint if endpoint.startswith("http") else f"{self.base_url}{endpoint}"
        if params:
            query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            if query:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}{query}"

        body_bytes = None
        headers = {
            "Authorization": self.auth_header,
            "Accept": "application/json",
            "User-Agent": "Antigravity-JiraSkill/1.0"
        }

        if data is not None:
            headers["Content-Type"] = "application/json"
            body_bytes = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method.upper())

        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl_context) as resp:
                status = resp.status
                if status == 204:
                    return None
                resp_bytes = resp.read()
                if not resp_bytes:
                    return None
                return json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw_err = e.read().decode("utf-8", errors="replace")
            err_json = None
            err_msg = f"HTTP {e.code} {e.reason}"
            try:
                err_json = json.loads(raw_err)
                if isinstance(err_json, dict):
                    messages = err_json.get("errorMessages", [])
                    field_errors = err_json.get("errors", {})
                    combined = []
                    if messages:
                        combined.extend(messages)
                    if field_errors:
                        combined.extend([f"{k}: {v}" for k, v in field_errors.items()])
                    if combined:
                        err_msg = f"HTTP {e.code}: {'; '.join(combined)}"
            except Exception:
                err_msg = f"HTTP {e.code}: {raw_err[:300]}"

            raise JiraApiError(err_msg, status_code=e.code, response_data=err_json or raw_err)
        except urllib.error.URLError as e:
            raise JiraApiError(f"Connection failed to {self.base_url}: {e.reason}")
        except Exception as e:
            raise JiraApiError(f"Unexpected error: {str(e)}")

    # -------------------------------------------------------------------------
    # Authentication & User Profile
    # -------------------------------------------------------------------------

    def get_myself(self) -> Dict[str, Any]:
        """Fetch current authenticated user/bot profile to verify credentials."""
        try:
            return self._request("GET", "/rest/api/3/myself")
        except JiraApiError as e:
            if e.status_code in (404, 400):
                # Fallback to v2 for Jira Server/Data Center
                return self._request("GET", "/rest/api/2/myself")
            raise

    # -------------------------------------------------------------------------
    # Projects
    # -------------------------------------------------------------------------

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all accessible projects."""
        try:
            return self._request("GET", "/rest/api/3/project")
        except JiraApiError:
            return self._request("GET", "/rest/api/2/project")

    def get_project(self, project_key_or_id: str) -> Dict[str, Any]:
        """Fetch detailed project metadata."""
        try:
            return self._request("GET", f"/rest/api/3/project/{project_key_or_id}")
        except JiraApiError:
            return self._request("GET", f"/rest/api/2/project/{project_key_or_id}")

    # -------------------------------------------------------------------------
    # Issues Lifecycle
    # -------------------------------------------------------------------------

    def get_issue(self, issue_key: str, expand: Optional[str] = None) -> Dict[str, Any]:
        """Fetch issue details including status, summary, assignee, and comments."""
        params = {"expand": expand} if expand else None
        try:
            return self._request("GET", f"/rest/api/3/issue/{issue_key}", params=params)
        except JiraApiError:
            return self._request("GET", f"/rest/api/2/issue/{issue_key}", params=params)

    def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        description: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_account_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
        parent_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new Jira issue supporting ADF formatting."""
        fields: Dict[str, Any] = {
            "project": {"key": project_key.upper()},
            "summary": summary,
            "issuetype": {"name": issue_type}
        }

        if priority:
            fields["priority"] = {"name": priority}
        if labels:
            fields["labels"] = labels
        if assignee_account_id:
            fields["assignee"] = {"accountId": assignee_account_id}
        if parent_key:
            fields["parent"] = {"key": parent_key.upper()}

        # First attempt with API v3 using ADF
        if description:
            fields["description"] = text_to_adf(description)

        try:
            return self._request("POST", "/rest/api/3/issue", data={"fields": fields})
        except JiraApiError as e:
            # Fallback for Jira Server / DC or plain text description
            if description and e.status_code in (400, 404):
                fields["description"] = description
                return self._request("POST", "/rest/api/2/issue", data={"fields": fields})
            raise

    def update_issue(self, issue_key: str, fields: Dict[str, Any]) -> None:
        """Update issue fields."""
        try:
            self._request("PUT", f"/rest/api/3/issue/{issue_key}", data={"fields": fields})
        except JiraApiError:
            self._request("PUT", f"/rest/api/2/issue/{issue_key}", data={"fields": fields})

    def get_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get all available workflow transitions for an issue."""
        try:
            resp = self._request("GET", f"/rest/api/3/issue/{issue_key}/transitions")
            return resp.get("transitions", [])
        except JiraApiError:
            resp = self._request("GET", f"/rest/api/2/issue/{issue_key}/transitions")
            return resp.get("transitions", [])

    def transition_issue(
        self,
        issue_key: str,
        transition_id: str,
        comment: Optional[str] = None
    ) -> None:
        """Execute a transition to update an issue's status."""
        payload: Dict[str, Any] = {
            "transition": {"id": str(transition_id)}
        }
        if comment:
            payload["update"] = {
                "comment": [{
                    "add": {"body": text_to_adf(comment)}
                }]
            }

        try:
            self._request("POST", f"/rest/api/3/issue/{issue_key}/transitions", data=payload)
        except JiraApiError:
            if comment:
                payload["update"]["comment"][0]["add"]["body"] = comment
            self._request("POST", f"/rest/api/2/issue/{issue_key}/transitions", data=payload)

    def add_comment(self, issue_key: str, body: str) -> Dict[str, Any]:
        """Add a comment to an issue."""
        try:
            return self._request("POST", f"/rest/api/3/issue/{issue_key}/comment", data={"body": text_to_adf(body)})
        except JiraApiError:
            return self._request("POST", f"/rest/api/2/issue/{issue_key}/comment", data={"body": body})

    def add_worklog(self, issue_key: str, time_spent: str, comment: Optional[str] = None) -> Dict[str, Any]:
        """Log time spent on an issue (e.g. '2h 30m', '1d')."""
        payload: Dict[str, Any] = {"timeSpent": time_spent}
        if comment:
            payload["comment"] = text_to_adf(comment)
        try:
            return self._request("POST", f"/rest/api/3/issue/{issue_key}/worklog", data=payload)
        except JiraApiError:
            if comment:
                payload["comment"] = comment
            return self._request("POST", f"/rest/api/2/issue/{issue_key}/worklog", data=payload)

    def link_issues(self, inward_key: str, outward_key: str, link_type: str = "Relates") -> None:
        """Create an issue link (e.g., 'Relates', 'Blocks', 'Duplicate')."""
        payload = {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_key.upper()},
            "outwardIssue": {"key": outward_key.upper()}
        }
        try:
            self._request("POST", "/rest/api/3/issueLink", data=payload)
        except JiraApiError:
            self._request("POST", "/rest/api/2/issueLink", data=payload)

    def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        start_at: int = 0,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute a JQL issue search."""
        payload: Dict[str, Any] = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at,
            "fields": fields or ["summary", "status", "issuetype", "priority", "assignee", "updated", "created", "labels"]
        }
        try:
            return self._request("POST", "/rest/api/3/search", data=payload)
        except JiraApiError:
            return self._request("POST", "/rest/api/2/search", data=payload)

    # -------------------------------------------------------------------------
    # Agile Boards & Sprints API
    # -------------------------------------------------------------------------

    def list_boards(
        self,
        project_key_or_id: Optional[str] = None,
        board_type: Optional[str] = None,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """List agile boards."""
        params: Dict[str, Any] = {"maxResults": max_results}
        if project_key_or_id:
            params["projectKeyOrFilterId"] = project_key_or_id
        if board_type:
            params["type"] = board_type.lower()

        resp = self._request("GET", "/rest/agile/1.0/board", params=params)
        return resp.get("values", [])

    def get_board(self, board_id: Union[str, int]) -> Dict[str, Any]:
        """Get board details."""
        return self._request("GET", f"/rest/agile/1.0/board/{board_id}")

    def get_board_configuration(self, board_id: Union[str, int]) -> Dict[str, Any]:
        """Fetch board configuration including columns, status mappings, and estimation."""
        return self._request("GET", f"/rest/agile/1.0/board/{board_id}/configuration")

    def create_board(self, name: str, project_key: str, board_type: str = "kanban") -> Dict[str, Any]:
        """Create a new agile board for a project."""
        payload = {
            "name": name,
            "type": board_type.lower(),
            "filterId": None,
            "location": {
                "type": "project",
                "projectKeyOrId": project_key.upper()
            }
        }
        return self._request("POST", "/rest/agile/1.0/board", data=payload)

    def get_board_issues(
        self,
        board_id: Union[str, int],
        jql: Optional[str] = None,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Get issues belonging to a board."""
        params: Dict[str, Any] = {"maxResults": max_results}
        if jql:
            params["jql"] = jql
        resp = self._request("GET", f"/rest/agile/1.0/board/{board_id}/issue", params=params)
        return resp.get("issues", [])

    def list_sprints(
        self,
        board_id: Union[str, int],
        state: Optional[str] = None,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """List sprints for a Scrum board."""
        params: Dict[str, Any] = {"maxResults": max_results}
        if state:
            params["state"] = state.lower()
        resp = self._request("GET", f"/rest/agile/1.0/board/{board_id}/sprint", params=params)
        return resp.get("values", [])

    def get_sprint(self, sprint_id: Union[str, int]) -> Dict[str, Any]:
        """Fetch details of a sprint."""
        return self._request("GET", f"/rest/agile/1.0/sprint/{sprint_id}")

    def get_sprint_issues(self, sprint_id: Union[str, int], max_results: int = 50) -> List[Dict[str, Any]]:
        """Fetch issues in a sprint."""
        resp = self._request("GET", f"/rest/agile/1.0/sprint/{sprint_id}/issue", params={"maxResults": max_results})
        return resp.get("issues", [])

    def create_sprint(
        self,
        board_id: Union[str, int],
        name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        goal: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new sprint."""
        payload: Dict[str, Any] = {
            "name": name,
            "originBoardId": int(board_id)
        }
        if start_date:
            payload["startDate"] = start_date
        if end_date:
            payload["endDate"] = end_date
        if goal:
            payload["goal"] = goal
        return self._request("POST", "/rest/agile/1.0/sprint", data=payload)

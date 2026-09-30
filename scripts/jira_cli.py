#!/usr/bin/env python3
"""
Jira Management CLI & SDK (Cross-Platform)
------------------------------------------
Zero-dependency, cross-platform Jira management CLI and client library.
Handles secure per-project credential caching, Zero-Leak resolution ladders,
project onboarding, standardized board configuration, enforced transition
lifecycle ordering (Definition of Done gates), sprint operations, and issue tracking.
"""

from __future__ import annotations

import argparse
import base64
import datetime
import json
import os
import re
import ssl
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Force UTF-8 stream encoding across all operating systems & Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

# Constants & Defaults
CACHE_DIR_NAME = ".agent"
CACHE_FILE_NAME = "jira.json"
ENV_URL_VAR = "JIRA_URL"
ENV_EMAIL_VAR = "JIRA_EMAIL"
ENV_TOKEN_VAR = "JIRA_API_TOKEN"
ENV_PAT_VAR = "JIRA_PAT"

# Standard Skill Board Workflow Stages & Progression Order
# Every project board managed by this skill must follow this sequential ordering.
ORDERED_STAGES = [
    {
        "order": 1,
        "stage": "Backlog",
        "category": "To Do",
        "description": "Unscheduled backlog items, requirements, raw requests",
        "common_statuses": ["backlog", "open", "submitted", "new", "funnel"]
    },
    {
        "order": 2,
        "stage": "To Do",
        "category": "To Do",
        "description": "Selected for development / active sprint backlog",
        "common_statuses": ["to do", "selected for development", "ready", "planned", "sprint backlog"]
    },
    {
        "order": 3,
        "stage": "In Progress",
        "category": "In Progress",
        "description": "Active development or investigation (WIP limits apply)",
        "common_statuses": ["in progress", "active", "developing", "investigation", "wip"]
    },
    {
        "order": 4,
        "stage": "In Review",
        "category": "In Progress",
        "description": "Ground-truth verification, code review, automated testing, DoD validation",
        "common_statuses": ["in review", "review", "testing", "qa", "verification", "dod check", "qa ready"]
    },
    {
        "order": 5,
        "stage": "Done",
        "category": "Done",
        "description": "Verified complete, DoD satisfied, merged, and closed",
        "common_statuses": ["done", "closed", "resolved", "completed", "verified"]
    }
]


# -----------------------------------------------------------------------------
# Security & Token Utility Functions (Zero-Leak Protocol)
# -----------------------------------------------------------------------------

def mask_token(token: Optional[str]) -> str:
    """Safely mask a Jira API token or PAT to prevent leaks in logs and transcripts.
    
    Example: 'ATATT3xFfGF01234567890abcdef' -> 'ATAT***cdef'
    """
    if not token:
        return "<no-token>"
    token_str = str(token).strip()
    if len(token_str) <= 6:
        return "***"
    prefix = token_str[:4]
    suffix = token_str[-4:]
    return f"{prefix}***{suffix}"


def find_project_root(start_dir: Optional[Union[str, Path]] = None) -> Path:
    """Find the root directory of the current project by walking up the filesystem.
    
    Identifies root by the presence of .git, .agent, package.json, pyproject.toml, or .env.
    Falls back to current working directory if no root markers are detected.
    """
    current = Path(start_dir or os.getcwd()).resolve()
    markers = [".git", CACHE_DIR_NAME, "pyproject.toml", "package.json", "go.mod", "Cargo.toml", ".env"]
    
    for parent in [current, *current.parents]:
        if any((parent / marker).exists() for marker in markers):
            return parent
            
    return current


def ensure_gitignore_protection(project_root: Path, entry: str = ".agent/") -> bool:
    """Ensure that the project's .gitignore exists and contains the credential cache entry.
    
    Enforces Priority 7: Zero-Leak Secret Security.
    """
    gitignore_path = project_root / ".gitignore"
    entry_clean = entry.strip()
    
    if gitignore_path.exists():
        try:
            content = gitignore_path.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.splitlines()]
            normalized_entry = entry_clean.rstrip("/")
            if any(line == entry_clean or line == normalized_entry or line == f"{normalized_entry}/*" for line in lines):
                return True
                
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write(f"\n# Jira credentials & agent cache (Auto-added by jira-management skill)\n{entry_clean}\n.env\n.env.*\n")
            return True
        except Exception:
            return False
    else:
        try:
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write(f"# Jira credentials & agent cache (Auto-added by jira-management skill)\n{entry_clean}\n.env\n.env.*\n")
            return True
        except Exception:
            return False
    return False


def get_project_cache_path(project_root: Path) -> Path:
    """Return the absolute path to the project's jira cache file."""
    return project_root / CACHE_DIR_NAME / CACHE_FILE_NAME


def get_global_cache_path() -> Path:
    """Return the path to the user's global config cache."""
    return Path.home() / ".gemini" / "config" / CACHE_FILE_NAME


def read_env_file(env_path: Path) -> Dict[str, str]:
    """Parse a .env file into key-value pairs without external dependencies."""
    if not env_path.exists() or not env_path.is_file():
        return {}
    results = {}
    try:
        content = env_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                results[key] = val
    except Exception:
        pass
    return results


def resolve_credentials(
    project_root: Optional[Path] = None,
    profile: str = "default",
    explicit_url: Optional[str] = None,
    explicit_email: Optional[str] = None,
    explicit_token: Optional[str] = None,
    explicit_project: Optional[str] = None,
    explicit_board_id: Optional[Union[str, int]] = None,
) -> Dict[str, Any]:
    """Resolve Jira credentials and project defaults following the strict priority ladder.
    
    Resolution Priority:
    1. Explicit CLI arguments
    2. Project cache: `<project_root>/.agent/jira.json`
    3. Project `.env` file (`JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` / `JIRA_PAT`)
    4. Environment variables
    5. Global user cache: `~/.gemini/config/jira.json`
    """
    root = project_root or find_project_root()
    result = {
        "url": explicit_url,
        "email": explicit_email,
        "token": explicit_token,
        "project": explicit_project,
        "board_id": explicit_board_id,
        "source": "explicit_arguments" if explicit_url and explicit_token else "none"
    }

    # Helper to check if credentials are complete
    def is_auth_complete(res: Dict[str, Any]) -> bool:
        return bool(res["url"] and (res["token"] or (res["email"] and res["token"])))

    # 1. If explicit credentials provided, check if complete
    if is_auth_complete(result):
        return result

    # 2. Check Project Cache (.agent/jira.json)
    cache_path = get_project_cache_path(root)
    if cache_path.exists():
        try:
            cache_data = json.loads(cache_path.read_text(encoding="utf-8"))
            profiles = cache_data.get("profiles", {})
            prof = profiles.get(profile, {})
            result["url"] = result["url"] or prof.get("url")
            result["email"] = result["email"] or prof.get("email")
            result["token"] = result["token"] or prof.get("token")
            result["project"] = result["project"] or prof.get("project")
            result["board_id"] = result["board_id"] or prof.get("board_id")
            if is_auth_complete(result):
                result["source"] = f"project_cache ({cache_path})"
                return result
        except Exception:
            pass

    # 3. Check Project .env
    env_vars = read_env_file(root / ".env")
    if env_vars:
        result["url"] = result["url"] or env_vars.get(ENV_URL_VAR)
        result["email"] = result["email"] or env_vars.get(ENV_EMAIL_VAR)
        result["token"] = result["token"] or env_vars.get(ENV_TOKEN_VAR) or env_vars.get(ENV_PAT_VAR)
        result["project"] = result["project"] or env_vars.get("JIRA_PROJECT")
        result["board_id"] = result["board_id"] or env_vars.get("JIRA_BOARD_ID")
        if is_auth_complete(result):
            result["source"] = f"project_env ({root / '.env'})"
            return result

    # 4. Check Environment Variables
    env_url = os.environ.get(ENV_URL_VAR)
    env_email = os.environ.get(ENV_EMAIL_VAR)
    env_token = os.environ.get(ENV_TOKEN_VAR) or os.environ.get(ENV_PAT_VAR)
    env_proj = os.environ.get("JIRA_PROJECT")
    env_board = os.environ.get("JIRA_BOARD_ID")

    result["url"] = result["url"] or env_url
    result["email"] = result["email"] or env_email
    result["token"] = result["token"] or env_token
    result["project"] = result["project"] or env_proj
    result["board_id"] = result["board_id"] or env_board
    if is_auth_complete(result):
        result["source"] = "environment_variables"
        return result

    # 5. Check Global User Cache (~/.gemini/config/jira.json)
    global_cache = get_global_cache_path()
    if global_cache.exists():
        try:
            cache_data = json.loads(global_cache.read_text(encoding="utf-8"))
            prof = cache_data.get("profiles", {}).get(profile, {})
            result["url"] = result["url"] or prof.get("url")
            result["email"] = result["email"] or prof.get("email")
            result["token"] = result["token"] or prof.get("token")
            result["project"] = result["project"] or prof.get("project")
            result["board_id"] = result["board_id"] or prof.get("board_id")
            if is_auth_complete(result):
                result["source"] = f"global_cache ({global_cache})"
                return result
        except Exception:
            pass

    return result


def save_credentials_to_cache(
    url: str,
    email: Optional[str],
    token: str,
    project: Optional[str] = None,
    board_id: Optional[Union[str, int]] = None,
    project_root: Optional[Path] = None,
    profile: str = "default",
    is_global: bool = False,
    user_info: Optional[Dict[str, Any]] = None
) -> Path:
    """Save Jira credentials and defaults to cache with hardened security permissions."""
    clean_url = url.strip().rstrip("/")
    if not clean_url.startswith(("http://", "https://")):
        clean_url = f"https://{clean_url}"

    if is_global:
        cache_path = get_global_cache_path()
        cache_dir = cache_path.parent
    else:
        root = project_root or find_project_root()
        cache_dir = root / CACHE_DIR_NAME
        cache_path = cache_dir / CACHE_FILE_NAME
        ensure_gitignore_protection(root)

    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Secure directory permissions on POSIX
    if os.name != "nt":
        try:
            os.chmod(cache_dir, stat.S_IRWXU)  # 0700
        except Exception:
            pass

    data: Dict[str, Any] = {"version": "1.0", "profiles": {}}
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if "profiles" not in data:
                data["profiles"] = {}
        except Exception:
            data = {"version": "1.0", "profiles": {}}

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    prof_entry: Dict[str, Any] = {
        "url": clean_url,
        "email": email.strip() if email else None,
        "token": token.strip(),
        "project": project.strip().upper() if project else None,
        "board_id": int(board_id) if board_id and str(board_id).isdigit() else board_id,
        "updated_at": now
    }

    if user_info:
        prof_entry["user"] = {
            "account_id": user_info.get("accountId"),
            "display_name": user_info.get("displayName"),
            "email_address": user_info.get("emailAddress"),
            "active": user_info.get("active", True),
            "account_type": user_info.get("accountType")
        }

    data["profiles"][profile] = prof_entry
    cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Secure file permissions on POSIX
    if os.name != "nt":
        try:
            os.chmod(cache_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
        except Exception:
            pass

    return cache_path


def remove_credentials_from_cache(
    project_root: Optional[Path] = None,
    profile: str = "default",
    is_global: bool = False
) -> bool:
    """Remove a credential profile from project or global cache."""
    cache_path = get_global_cache_path() if is_global else get_project_cache_path(project_root or find_project_root())
    if not cache_path.exists():
        return False

    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        profiles = data.get("profiles", {})
        if profile in profiles:
            del profiles[profile]
            cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True
    except Exception:
        pass
    return False


# -----------------------------------------------------------------------------
# Atlassian Document Format (ADF) Helpers
# -----------------------------------------------------------------------------

def text_to_adf(text: str) -> Dict[str, Any]:
    """Convert plain text or simple markdown into Jira v3 Atlassian Document Format (ADF).
    
    Ensures 100% compatibility with Jira Cloud REST API v3.
    """
    if not text:
        return {"version": 1, "type": "doc", "content": []}
        
    paragraphs = text.replace("\r\n", "\n").split("\n\n")
    content_blocks = []

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue
            
        # Code block detection (```...```)
        if para_clean.startswith("```") and para_clean.endswith("```"):
            lines = para_clean.split("\n")
            first_line = lines[0].replace("```", "").strip()
            code_text = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
            content_blocks.append({
                "type": "codeBlock",
                "attrs": {"language": first_line or "text"},
                "content": [{"type": "text", "text": code_text}]
            })
            continue

        # Bullet list detection
        if all(line.strip().startswith(("- ", "* ")) for line in para_clean.split("\n") if line.strip()):
            list_items = []
            for item in para_clean.split("\n"):
                item_text = item.strip().lstrip("- *").strip()
                if item_text:
                    list_items.append({
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": item_text}]
                        }]
                    })
            content_blocks.append({
                "type": "bulletList",
                "content": list_items
            })
            continue

        # Regular paragraph
        content_blocks.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": para_clean}]
        })

    return {
        "version": 1,
        "type": "doc",
        "content": content_blocks or [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]
    }


def adf_to_text(adf_node: Any) -> str:
    """Recursively extract plain text from an Atlassian Document Format node."""
    if not isinstance(adf_node, dict):
        return str(adf_node) if adf_node else ""

    node_type = adf_node.get("type")
    content = adf_node.get("content", [])

    if node_type == "text":
        return adf_node.get("text", "")

    texts = [adf_to_text(c) for c in content]

    if node_type == "paragraph":
        return "".join(texts) + "\n"
    elif node_type == "codeBlock":
        lang = adf_node.get("attrs", {}).get("language", "")
        return f"```{lang}\n" + "".join(texts) + "\n```\n"
    elif node_type == "listItem":
        return "* " + "".join(texts).strip() + "\n"
    elif node_type in ("bulletList", "orderedList"):
        return "".join(texts) + "\n"
    elif node_type == "doc":
        return "\n".join(t.strip() for t in texts if t.strip())

    return "".join(texts)


# -----------------------------------------------------------------------------
# Jira API Client (Cross-Platform, Pure Standard Library)
# -----------------------------------------------------------------------------

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
        # Note: Jira Agile API requires a filterId when creating a board via API.
        # If filterId is omitted, we query for or create the project's standard filter.
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


# -----------------------------------------------------------------------------
# Enforced Board Ordering & Audit Logic
# -----------------------------------------------------------------------------

def map_status_to_standard_stage(status_name: str) -> Optional[Dict[str, Any]]:
    """Map an arbitrary Jira status name to one of the 5 standard skill stages."""
    name_clean = status_name.strip().lower()
    for stage_def in ORDERED_STAGES:
        for common in stage_def["common_statuses"]:
            if name_clean == common or common in name_clean:
                return stage_def
    return None


def audit_board_compliance(board_config: Dict[str, Any]) -> Dict[str, Any]:
    """Audit a board's columns and workflow mapping against the Skill Ordered Standard.
    
    Verifies:
    1. Presence of all 5 ordered stages (Backlog, To Do, In Progress, In Review, Done).
    2. Correct left-to-right sequential column ordering.
    3. Proper mapping of statuses to stages.
    """
    columns = board_config.get("columnConfig", {}).get("columns", [])
    if not columns:
        return {
            "compliant": False,
            "score": 0,
            "error": "No columns found in board configuration."
        }

    detected_stages: List[Dict[str, Any]] = []
    unmapped_columns: List[str] = []

    for idx, col in enumerate(columns):
        col_name = col.get("name", "").strip()
        statuses = col.get("statuses", [])
        status_names = [s.get("id") or s.get("name", "") for s in statuses]

        stage_match = map_status_to_standard_stage(col_name)
        if not stage_match and statuses:
            # Try to match from underlying statuses
            for s in statuses:
                s_name = s.get("name", "")
                stage_match = map_status_to_standard_stage(s_name)
                if stage_match:
                    break

        if stage_match:
            detected_stages.append({
                "column_index": idx,
                "column_name": col_name,
                "stage": stage_match["stage"],
                "order": stage_match["order"],
                "statuses": status_names
            })
        else:
            unmapped_columns.append(col_name)

    # Check order correctness
    detected_orders = [d["order"] for d in detected_stages]
    is_strictly_ordered = detected_orders == sorted(detected_orders)

    # Check stage coverage
    found_orders = set(detected_orders)
    missing_stages = [s["stage"] for s in ORDERED_STAGES if s["order"] not in found_orders]

    score = 100
    deductions = []
    if missing_stages:
        score -= len(missing_stages) * 15
        deductions.append(f"Missing mandatory standard stages: {', '.join(missing_stages)}")
    if not is_strictly_ordered:
        score -= 30
        deductions.append("Board columns violate the mandatory left-to-right workflow ordering.")
    if unmapped_columns:
        score -= len(unmapped_columns) * 5
        deductions.append(f"Columns not conforming to standard naming: {', '.join(unmapped_columns)}")

    score = max(0, score)
    is_compliant = score >= 85 and is_strictly_ordered and not missing_stages

    return {
        "board_id": board_config.get("id"),
        "board_name": board_config.get("name"),
        "compliant": is_compliant,
        "compliance_score": f"{score}%",
        "detected_stages": detected_stages,
        "missing_stages": missing_stages,
        "unmapped_columns": unmapped_columns,
        "deductions": deductions,
        "recommended_order": [s["stage"] for s in ORDERED_STAGES]
    }


def validate_issue_transition_order(
    current_status: str,
    target_status: str,
    has_dod_report: bool = False,
    force: bool = False
) -> Tuple[bool, Optional[str]]:
    """Validate whether an issue transition adheres to the enforced sequential ordering.
    
    Prevents bypassing 'In Progress' or 'In Review' directly to 'Done'.
    """
    if force:
        return True, None

    current_stage = map_status_to_standard_stage(current_status)
    target_stage = map_status_to_standard_stage(target_status)

    if not current_stage or not target_stage:
        # Cannot strictly evaluate unknown statuses
        return True, None

    curr_order = current_stage["order"]
    tgt_order = target_stage["order"]

    # Reopening or moving backwards is permitted (e.g. from Review back to In Progress)
    if tgt_order < curr_order:
        return True, None

    # Forward skip check: Cannot jump straight from Backlog (1) or To Do (2) to Done (5)
    if curr_order <= 2 and tgt_order == 5:
        return False, (
            f"Ordered Workflow Violation: Cannot jump directly from '{current_status}' (Stage {curr_order}) "
            f"to '{target_status}' (Stage 5). Must transition through Stage 3 (In Progress) and "
            f"Stage 4 (In Review / Verification) to satisfy Definition of Done."
        )

    # DoD Check: Transitioning to Done (Stage 5) requires review verification
    if tgt_order == 5 and curr_order != 4:
        return False, (
            f"Ordered Workflow Violation: Issues must be in 'In Review' (Stage 4) before transitioning "
            f"to 'Done' (Stage 5). Current stage is '{current_status}' (Stage {curr_order})."
        )

    if tgt_order == 5 and not has_dod_report:
        return False, (
            "Definition of Done Gate: Transitioning to 'Done' requires verification notes or DoD proof. "
            "Please provide --comment or --dod-report detailing tests and verification evidence."
        )

    return True, None


# -----------------------------------------------------------------------------
# CLI Subcommands & Presentation Helpers
# -----------------------------------------------------------------------------

def print_header(title: str) -> None:
    print(f"\n=== {title} ===")


def print_success(msg: str) -> None:
    print(f"[OK] {msg}")


def print_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def print_warning(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)


def handle_auth_cmd(args: argparse.Namespace) -> int:
    """Handle 'auth' commands."""
    sub = args.auth_action

    if sub == "set":
        url = args.url
        email = args.email
        token = args.token
        profile = args.profile or "default"
        is_global = args.is_global
        project = args.project
        board_id = args.board_id

        if not url or not token:
            print_error("Both --url and --token are required to configure Jira.")
            return 1

        user_info = None
        if not args.no_verify:
            print(f"[*] Verifying credentials against {url}...")
            client = JiraClient(url, token, email=email)
            try:
                user_info = client.get_myself()
                print_success(f"Authenticated as: {user_info.get('displayName')} ({user_info.get('emailAddress') or user_info.get('accountId')})")
            except Exception as e:
                print_error(f"Live verification failed: {e}")
                print_error("Configuration not saved. Use --no-verify to bypass verification.")
                return 1

        saved_path = save_credentials_to_cache(
            url=url,
            email=email,
            token=token,
            project=project,
            board_id=board_id,
            profile=profile,
            is_global=is_global,
            user_info=user_info
        )
        print_success(f"Credentials successfully saved to {saved_path} (Profile: {profile})")
        print(f"Masked Token: {mask_token(token)}")
        if project:
            print(f"Default Project: {project.upper()}")
        if board_id:
            print(f"Default Board ID: {board_id}")
        return 0

    elif sub == "status":
        profile = args.profile or "default"
        creds = resolve_credentials(profile=profile)
        if not creds.get("url") or not creds.get("token"):
            if args.json:
                print(json.dumps({"authenticated": False, "error": "No credentials resolved"}, indent=2))
            else:
                print_warning(f"No Jira credentials resolved for profile '{profile}'.")
                print("Run 'jira auth set --url <URL> --email <EMAIL> --token <TOKEN>' to configure.")
            return 1

        client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))
        status_data: Dict[str, Any] = {
            "authenticated": False,
            "url": creds["url"],
            "email": creds.get("email"),
            "masked_token": mask_token(creds.get("token")),
            "source": creds.get("source"),
            "default_project": creds.get("project"),
            "default_board_id": creds.get("board_id")
        }

        try:
            myself = client.get_myself()
            status_data["authenticated"] = True
            status_data["user"] = {
                "display_name": myself.get("displayName"),
                "account_id": myself.get("accountId"),
                "email_address": myself.get("emailAddress"),
                "active": myself.get("active", True),
                "account_type": myself.get("accountType")
            }
        except Exception as e:
            status_data["error"] = str(e)

        if args.json:
            print(json.dumps(status_data, indent=2))
            return 0 if status_data["authenticated"] else 1

        print_header("Jira Authentication & Profile Status")
        print(f"Resolution Source : {status_data['source']}")
        print(f"Base URL          : {status_data['url']}")
        print(f"Account Email     : {status_data['email'] or '<none (Bearer PAT)>'}")
        print(f"Masked Token      : {status_data['masked_token']}")
        print(f"Default Project   : {status_data['default_project'] or '<none>'}")
        print(f"Default Board ID  : {status_data['default_board_id'] or '<none>'}")

        if status_data["authenticated"]:
            u = status_data["user"]
            print_success(f"Status            : Active & Connected")
            print(f"User Name         : {u['display_name']}")
            print(f"Account ID        : {u['account_id']}")
        else:
            print_error(f"Status            : Failed ({status_data.get('error')})")
            return 1
        return 0

    elif sub == "remove":
        profile = args.profile or "default"
        is_global = args.is_global
        removed = remove_credentials_from_cache(profile=profile, is_global=is_global)
        if removed:
            print_success(f"Removed profile '{profile}' from cache.")
            return 0
        else:
            print_warning(f"Profile '{profile}' was not found in cache.")
            return 1

    return 0


def handle_board_cmd(args: argparse.Namespace) -> int:
    """Handle 'board' commands."""
    sub = args.board_action
    creds = resolve_credentials(profile=args.profile or "default")
    if not creds.get("url") or not creds.get("token"):
        print_error("No Jira credentials resolved. Run 'jira auth set' first.")
        return 1

    client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))

    if sub == "list":
        proj = args.project or creds.get("project")
        boards = client.list_boards(project_key_or_id=proj, board_type=args.type)
        if args.json:
            print(json.dumps(boards, indent=2))
            return 0

        print_header(f"Agile Boards {f'(Project: {proj})' if proj else ''}")
        if not boards:
            print("No boards found.")
            return 0
        for b in boards:
            print(f"• ID: {b.get('id'):<5} | Type: {b.get('type'):<7} | Name: {b.get('name')}")
        return 0

    elif sub == "get":
        board_id = args.board_id or creds.get("board_id")
        if not board_id:
            print_error("Missing --board-id argument.")
            return 1
        b = client.get_board(board_id)
        if args.json:
            print(json.dumps(b, indent=2))
            return 0
        print_header(f"Board Details (ID: {board_id})")
        print(f"Name : {b.get('name')}")
        print(f"Type : {b.get('type')}")
        print(f"URL  : {b.get('self')}")
        return 0

    elif sub == "config":
        board_id = args.board_id or creds.get("board_id")
        if not board_id:
            print_error("Missing --board-id argument.")
            return 1
        cfg = client.get_board_configuration(board_id)
        if args.json:
            print(json.dumps(cfg, indent=2))
            return 0
        print_header(f"Board Configuration (ID: {board_id})")
        cols = cfg.get("columnConfig", {}).get("columns", [])
        for idx, c in enumerate(cols, start=1):
            st_names = [s.get("id") or s.get("name", "") for s in c.get("statuses", [])]
            print(f"{idx}. {c.get('name')} -> Statuses: {', '.join(st_names)}")
        return 0

    elif sub == "audit":
        board_id = args.board_id or creds.get("board_id")
        if not board_id:
            print_error("Missing --board-id argument.")
            return 1

        cfg = client.get_board_configuration(board_id)
        audit_res = audit_board_compliance(cfg)

        if args.json:
            print(json.dumps(audit_res, indent=2))
            return 0 if audit_res["compliant"] else 1

        print_header(f"Board Workflow Order Audit (ID: {board_id})")
        print(f"Board Name       : {audit_res.get('board_name')}")
        print(f"Compliance Score : {audit_res.get('compliance_score')}")
        print(f"Status           : {'[COMPLIANT]' if audit_res['compliant'] else '[NON-COMPLIANT]'}")

        print("\nOrdered Stages Detected:")
        for st in audit_res.get("detected_stages", []):
            print(f"  Stage {st['order']}: {st['stage']} (Column: '{st['column_name']}')")

        if audit_res.get("missing_stages"):
            print_warning(f"\nMissing Standard Stages: {', '.join(audit_res['missing_stages'])}")
            print("To comply with the skill standard, ensure columns exist for:")
            for s in ORDERED_STAGES:
                print(f"  {s['order']}. {s['stage']}: {s['description']}")

        if audit_res.get("deductions"):
            print("\nFindings & Violations:")
            for d in audit_res["deductions"]:
                print(f"  - {d}")

        return 0 if audit_res["compliant"] else 1

    elif sub == "view":
        board_id = args.board_id or creds.get("board_id")
        if not board_id:
            print_error("Missing --board-id argument.")
            return 1

        issues = client.get_board_issues(board_id, max_results=100)
        
        # Bucket issues by standard stages
        buckets: Dict[str, List[Dict[str, Any]]] = {s["stage"]: [] for s in ORDERED_STAGES}
        other_bucket: List[Dict[str, Any]] = []

        for issue in issues:
            fields = issue.get("fields", {})
            st_name = fields.get("status", {}).get("name", "")
            stage_def = map_status_to_standard_stage(st_name)
            item = {
                "key": issue.get("key"),
                "summary": fields.get("summary", ""),
                "status": st_name,
                "priority": fields.get("priority", {}).get("name", "Medium"),
                "assignee": (fields.get("assignee") or {}).get("displayName", "Unassigned")
            }
            if stage_def:
                buckets[stage_def["stage"]].append(item)
            else:
                other_bucket.append(item)

        if args.json:
            print(json.dumps({"board_id": board_id, "stages": buckets, "other": other_bucket}, indent=2))
            return 0

        print_header(f"Standard Ordered Board View (Board ID: {board_id})")
        for s in ORDERED_STAGES:
            stage_name = s["stage"]
            stage_issues = buckets[stage_name]
            print(f"\n[ STAGE {s['order']}: {stage_name.upper()} ] ({len(stage_issues)} items)")
            print(f"  {s['description']}")
            print("  " + "-" * 60)
            if not stage_issues:
                print("  (empty)")
            for itm in stage_issues:
                print(f"  • [{itm['key']}] {itm['summary'][:50]:<52} | {itm['priority']:<6} | {itm['assignee']}")

        if other_bucket:
            print(f"\n[ UNMAPPED STATUSES ] ({len(other_bucket)} items)")
            print("  " + "-" * 60)
            for itm in other_bucket:
                print(f"  • [{itm['key']}] {itm['summary'][:50]:<52} | Status: {itm['status']}")

        return 0

    return 0


def handle_issue_cmd(args: argparse.Namespace) -> int:
    """Handle 'issue' commands."""
    sub = args.issue_action
    creds = resolve_credentials(profile=args.profile or "default")
    if not creds.get("url") or not creds.get("token"):
        print_error("No Jira credentials resolved. Run 'jira auth set' first.")
        return 1

    client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))

    if sub == "create":
        proj = args.project or creds.get("project")
        if not proj:
            print_error("Missing --project argument (or default project in cache).")
            return 1
        summary = args.summary
        if not summary:
            print_error("Missing --summary argument.")
            return 1

        labels = [l.strip() for l in args.labels.split(",")] if args.labels else None
        res = client.create_issue(
            project_key=proj,
            summary=summary,
            issue_type=args.type or "Task",
            description=args.description,
            priority=args.priority,
            assignee_account_id=args.assignee,
            labels=labels,
            parent_key=args.parent
        )

        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        print_success(f"Issue created successfully: {res.get('key')} (ID: {res.get('id')})")
        print(f"URL: {creds['url']}/browse/{res.get('key')}")
        return 0

    elif sub == "get":
        key = args.key
        if not key:
            print_error("Missing --key argument.")
            return 1

        issue = client.get_issue(key, expand="names,renderedFields")
        if args.json:
            print(json.dumps(issue, indent=2))
            return 0

        fields = issue.get("fields", {})
        print_header(f"Issue {issue.get('key')}: {fields.get('summary')}")
        print(f"Type     : {fields.get('issuetype', {}).get('name')}")
        print(f"Status   : {fields.get('status', {}).get('name')}")
        print(f"Priority : {fields.get('priority', {}).get('name')}")
        print(f"Assignee : {(fields.get('assignee') or {}).get('displayName', 'Unassigned')}")
        labels = fields.get("labels", [])
        if labels:
            print(f"Labels   : {', '.join(labels)}")

        desc_raw = fields.get("description")
        desc_text = adf_to_text(desc_raw) if isinstance(desc_raw, dict) else (desc_raw or "")
        if desc_text.strip():
            print("\nDescription:")
            print(desc_text.strip())

        return 0

    elif sub == "transition":
        key = args.key
        to_status = args.to
        if not key or not to_status:
            print_error("Both --key and --to are required.")
            return 1

        # Read DoD report if file path provided
        dod_comment = args.comment or ""
        has_dod = bool(dod_comment.strip() or args.dod_report)
        if args.dod_report:
            p = Path(args.dod_report)
            if p.exists() and p.is_file():
                try:
                    dod_comment = f"{dod_comment}\n\n### Definition of Done (DoD) Verification Report\n" + p.read_text(encoding="utf-8")
                except Exception as e:
                    print_warning(f"Could not read DoD report file: {e}")
            else:
                dod_comment = f"{dod_comment}\n\n### Definition of Done (DoD) Verification Report\n{args.dod_report}"

        # Fetch current issue status
        issue = client.get_issue(key)
        curr_status = issue.get("fields", {}).get("status", {}).get("name", "")

        # Validate sequential transition ordering
        valid, err = validate_issue_transition_order(
            current_status=curr_status,
            target_status=to_status,
            has_dod_report=has_dod,
            force=args.force
        )

        if not valid:
            print_error(f"Ordered Transition Blocked: {err}")
            print_error("Use --force to override skill ordering restrictions if strictly required by human supervisor.")
            return 1

        # Find matching transition ID from Jira
        transitions = client.get_transitions(key)
        matching_t = None
        for t in transitions:
            t_name = t.get("name", "").strip().lower()
            to_name = t.get("to", {}).get("name", "").strip().lower()
            req_name = to_status.strip().lower()
            if req_name == t_name or req_name == to_name or req_name in to_name:
                matching_t = t
                break

        if not matching_t:
            available = [f"'{t.get('name')}' -> '{t.get('to', {}).get('name')}' (ID: {t.get('id')})" for t in transitions]
            print_error(f"No transition found matching '{to_status}'.")
            print(f"Available transitions for {key}:\n  " + "\n  ".join(available))
            return 1

        client.transition_issue(key, matching_t["id"], comment=dod_comment if dod_comment.strip() else None)
        print_success(f"Issue {key} transitioned from '{curr_status}' to '{matching_t.get('to', {}).get('name')}'")
        return 0

    elif sub == "comment":
        key = args.key
        body = args.body
        if not key or not body:
            print_error("Both --key and --body are required.")
            return 1
        res = client.add_comment(key, body)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0
        print_success(f"Comment added to {key}.")
        return 0

    elif sub == "worklog":
        key = args.key
        time_spent = args.time
        if not key or not time_spent:
            print_error("Both --key and --time are required (e.g. --time '2h 30m').")
            return 1
        res = client.add_worklog(key, time_spent, comment=args.comment)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0
        print_success(f"Logged {time_spent} work on {key}.")
        return 0

    elif sub == "search":
        jql = args.jql
        if not jql:
            proj = creds.get("project")
            if proj:
                jql = f"project = {proj} ORDER BY updated DESC"
            else:
                print_error("Missing --jql argument.")
                return 1

        res = client.search_issues(jql, max_results=args.limit or 20)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        issues = res.get("issues", [])
        print_header(f"JQL Search: {jql} (Total: {res.get('total')})")
        if not issues:
            print("No issues found.")
            return 0

        for itm in issues:
            f = itm.get("fields", {})
            st = f.get("status", {}).get("name", "")
            prio = f.get("priority", {}).get("name", "")
            print(f"• [{itm.get('key'):<10}] {f.get('summary', '')[:50]:<52} | {st:<15} | {prio}")

        return 0

    return 0


def handle_sprint_cmd(args: argparse.Namespace) -> int:
    """Handle 'sprint' commands."""
    sub = args.sprint_action
    creds = resolve_credentials(profile=args.profile or "default")
    if not creds.get("url") or not creds.get("token"):
        print_error("No Jira credentials resolved. Run 'jira auth set' first.")
        return 1

    client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))

    if sub == "list":
        board_id = args.board_id or creds.get("board_id")
        if not board_id:
            print_error("Missing --board-id argument.")
            return 1

        sprints = client.list_sprints(board_id, state=args.state)
        if args.json:
            print(json.dumps(sprints, indent=2))
            return 0

        print_header(f"Sprints for Board {board_id}")
        if not sprints:
            print("No sprints found.")
            return 0
        for s in sprints:
            print(f"• ID: {s.get('id'):<5} | State: {s.get('state'):<8} | Name: {s.get('name')}")
        return 0

    elif sub == "issues":
        sprint_id = args.sprint_id
        if not sprint_id:
            print_error("Missing --sprint-id argument.")
            return 1

        issues = client.get_sprint_issues(sprint_id)
        if args.json:
            print(json.dumps(issues, indent=2))
            return 0

        print_header(f"Sprint {sprint_id} Issues ({len(issues)} items)")
        for itm in issues:
            f = itm.get("fields", {})
            print(f"• [{itm.get('key'):<10}] {f.get('summary', '')[:50]:<52} | {f.get('status', {}).get('name')}")
        return 0

    elif sub == "create":
        board_id = args.board_id or creds.get("board_id")
        if not board_id or not args.name:
            print_error("Both --board-id and --name are required.")
            return 1

        sprint = client.create_sprint(
            board_id=board_id,
            name=args.name,
            start_date=args.start_date,
            end_date=args.end_date,
            goal=args.goal
        )
        if args.json:
            print(json.dumps(sprint, indent=2))
            return 0
        print_success(f"Sprint created: {sprint.get('name')} (ID: {sprint.get('id')})")
        return 0

    return 0


def handle_project_cmd(args: argparse.Namespace) -> int:
    """Handle 'project' commands."""
    sub = args.project_action
    creds = resolve_credentials(profile=args.profile or "default")
    if not creds.get("url") or not creds.get("token"):
        print_error("No Jira credentials resolved. Run 'jira auth set' first.")
        return 1

    client = JiraClient(creds["url"], creds["token"], email=creds.get("email"))

    if sub == "list":
        projects = client.list_projects()
        if args.json:
            print(json.dumps(projects, indent=2))
            return 0
        print_header("Accessible Jira Projects")
        for p in projects:
            print(f"• Key: {p.get('key'):<8} | Name: {p.get('name')}")
        return 0

    elif sub == "get":
        key = args.key or creds.get("project")
        if not key:
            print_error("Missing --key argument.")
            return 1
        p = client.get_project(key)
        if args.json:
            print(json.dumps(p, indent=2))
            return 0
        print_header(f"Project {p.get('key')}: {p.get('name')}")
        print(f"Lead     : {(p.get('lead') or {}).get('displayName', 'Unknown')}")
        print(f"Category : {(p.get('projectCategory') or {}).get('name', 'None')}")
        return 0

    return 0


# -----------------------------------------------------------------------------
# Main CLI Parser & Dispatcher
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jira",
        description="Cross-Platform Jira Management CLI & Skill Engine (Zero-Leak Security & Enforced Board Ordering)"
    )
    parser.add_argument("--profile", default="default", help="Credential profile name (default: 'default')")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Auth command
    p_auth = subparsers.add_parser("auth", help="Manage Jira authentication, profiles, and cached credentials")
    s_auth = p_auth.add_subparsers(dest="auth_action", required=True)

    p_auth_set = s_auth.add_parser("set", help="Save credentials to cache")
    p_auth_set.add_argument("--url", required=True, help="Jira base URL (e.g. https://company.atlassian.net)")
    p_auth_set.add_argument("--token", required=True, help="API token (Cloud) or Personal Access Token (Server/DC)")
    p_auth_set.add_argument("--email", help="Account email (required for Atlassian Cloud Basic Auth)")
    p_auth_set.add_argument("--project", help="Default project key (e.g. DEV, PROJ)")
    p_auth_set.add_argument("--board-id", type=int, help="Default agile board ID")
    p_auth_set.add_argument("--global", dest="is_global", action="store_true", help="Save to global config ~/.gemini/config/jira.json")
    p_auth_set.add_argument("--no-verify", action="store_true", help="Skip live connection test")

    s_auth.add_parser("status", help="Test connection and view active credential details (Zero-Leak masked)")
    p_auth_rem = s_auth.add_parser("remove", help="Remove cached credentials")
    p_auth_rem.add_argument("--global", dest="is_global", action="store_true", help="Remove from global cache")

    # 2. Board command
    p_board = subparsers.add_parser("board", help="Manage and audit agile boards according to skill ordering rules")
    s_board = p_board.add_subparsers(dest="board_action", required=True)

    p_board_list = s_board.add_parser("list", help="List agile boards")
    p_board_list.add_argument("--project", help="Filter by project key")
    p_board_list.add_argument("--type", choices=["kanban", "scrum"], help="Filter by board type")

    p_board_get = s_board.add_parser("get", help="Get board details")
    p_board_get.add_argument("--board-id", type=int, help="Board ID (or default from cache)")

    p_board_cfg = s_board.add_parser("config", help="Get board column configuration")
    p_board_cfg.add_argument("--board-id", type=int, help="Board ID")

    p_board_audit = s_board.add_parser("audit", help="Audit board columns against the Skill Ordered Standard")
    p_board_audit.add_argument("--board-id", type=int, help="Board ID to audit")

    p_board_view = s_board.add_parser("view", help="View board issues grouped into the 5 standard ordered stages")
    p_board_view.add_argument("--board-id", type=int, help="Board ID")

    # 3. Issue command
    p_issue = subparsers.add_parser("issue", help="Manage issue lifecycle, transitions, and DoD gates")
    s_issue = p_issue.add_subparsers(dest="issue_action", required=True)

    p_issue_create = s_issue.add_parser("create", help="Create a new Jira issue")
    p_issue_create.add_argument("--summary", required=True, help="Issue summary/title")
    p_issue_create.add_argument("--project", help="Project key (or default from cache)")
    p_issue_create.add_argument("--type", default="Task", help="Issue type (Task, Bug, Story, Epic)")
    p_issue_create.add_argument("--description", help="Issue description text or markdown")
    p_issue_create.add_argument("--priority", help="Priority (Lowest, Low, Medium, High, Highest)")
    p_issue_create.add_argument("--assignee", help="Assignee account ID")
    p_issue_create.add_argument("--labels", help="Comma-separated labels")
    p_issue_create.add_argument("--parent", help="Parent issue key (for sub-tasks)")

    p_issue_get = s_issue.add_parser("get", help="Get issue details")
    p_issue_get.add_argument("--key", required=True, help="Issue key (e.g. PROJ-123)")

    p_issue_trans = s_issue.add_parser("transition", help="Transition issue status enforcing ordered progression")
    p_issue_trans.add_argument("--key", required=True, help="Issue key")
    p_issue_trans.add_argument("--to", required=True, help="Target status or transition name")
    p_issue_trans.add_argument("--comment", help="Transition comment")
    p_issue_trans.add_argument("--dod-report", help="Path to DoD report file or text verification evidence")
    p_issue_trans.add_argument("--force", action="store_true", help="Bypass sequential workflow order checks")

    p_issue_comm = s_issue.add_parser("comment", help="Add a comment to an issue")
    p_issue_comm.add_argument("--key", required=True, help="Issue key")
    p_issue_comm.add_argument("--body", required=True, help="Comment body text or markdown")

    p_issue_work = s_issue.add_parser("worklog", help="Log work on an issue")
    p_issue_work.add_argument("--key", required=True, help="Issue key")
    p_issue_work.add_argument("--time", required=True, help="Time spent (e.g. '1h 30m', '4h')")
    p_issue_work.add_argument("--comment", help="Worklog description")

    p_issue_search = s_issue.add_parser("search", help="Search issues via JQL")
    p_issue_search.add_argument("--jql", help="JQL query string")
    p_issue_search.add_argument("--limit", type=int, default=20, help="Max results")

    # 4. Sprint command
    p_sprint = subparsers.add_parser("sprint", help="Manage sprints for Scrum boards")
    s_sprint = p_sprint.add_subparsers(dest="sprint_action", required=True)

    p_sprint_list = s_sprint.add_parser("list", help="List sprints for a board")
    p_sprint_list.add_argument("--board-id", type=int, help="Board ID")
    p_sprint_list.add_argument("--state", choices=["active", "future", "closed"], help="Sprint state")

    p_sprint_issues = s_sprint.add_parser("issues", help="List issues in a sprint")
    p_sprint_issues.add_argument("--sprint-id", type=int, required=True, help="Sprint ID")

    p_sprint_create = s_sprint.add_parser("create", help="Create a sprint")
    p_sprint_create.add_argument("--board-id", type=int, help="Board ID")
    p_sprint_create.add_argument("--name", required=True, help="Sprint name")
    p_sprint_create.add_argument("--start-date", help="ISO start date")
    p_sprint_create.add_argument("--end-date", help="ISO end date")
    p_sprint_create.add_argument("--goal", help="Sprint goal")

    # 5. Project command
    p_proj = subparsers.add_parser("project", help="Inspect Jira projects")
    s_proj = p_proj.add_subparsers(dest="project_action", required=True)
    s_proj.add_parser("list", help="List projects")
    p_proj_get = s_proj.add_parser("get", help="Get project details")
    p_proj_get.add_argument("--key", help="Project key")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "auth": handle_auth_cmd,
        "board": handle_board_cmd,
        "issue": handle_issue_cmd,
        "sprint": handle_sprint_cmd,
        "project": handle_project_cmd
    }

    handler = handlers.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(1)

    try:
        exit_code = handler(args)
        sys.exit(exit_code or 0)
    except JiraApiError as e:
        if args.json:
            print(json.dumps({"error": str(e), "status_code": e.status_code, "data": e.response_data}, indent=2))
        else:
            print_error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[Operation cancelled by user]")
        sys.exit(130)
    except Exception as e:
        if args.json:
            print(json.dumps({"error": f"Unhandled error: {str(e)}"}, indent=2))
        else:
            print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

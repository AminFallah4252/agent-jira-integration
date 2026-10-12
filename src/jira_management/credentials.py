"""Zero-Leak credential management, caching, and resolution ladder."""

from __future__ import annotations

import datetime
import json
import os
import stat
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .constants import (
    CACHE_DIR_NAME,
    CACHE_FILE_NAME,
    ENV_EMAIL_VAR,
    ENV_PAT_VAR,
    ENV_TOKEN_VAR,
    ENV_URL_VAR,
)


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
    
    Identifies root by the presence of .git, .agent, .claude, .cursor, package.json,
    pyproject.toml, AGENTS.md, CLAUDE.md, .cursorrules, or .env.
    Falls back to current working directory if no root markers are detected.
    """
    current = Path(start_dir or os.getcwd()).resolve()
    markers = [
        ".git",
        CACHE_DIR_NAME,
        ".claude",
        ".cursor",
        ".github",
        "pyproject.toml",
        "package.json",
        "go.mod",
        "Cargo.toml",
        ".env",
        "AGENTS.md",
        "CLAUDE.md",
        ".cursorrules",
        ".windsurfrules",
    ]

    for parent in [current, *current.parents]:
        if any((parent / marker).exists() for marker in markers):
            return parent

    return current


def ensure_gitignore_protection(project_root: Path, entry: str = ".agent/") -> bool:
    """Ensure that the project's .gitignore exists and contains the credential cache entry.
    
    Enforces Priority 7: Zero-Leak Secret Security across all agents.
    """
    gitignore_path = project_root / ".gitignore"
    entry_clean = entry.strip()

    entries_to_add = [entry_clean, ".claude/jira.json", ".cursor/jira.json", ".env", ".env.*"]

    if gitignore_path.exists():
        try:
            content = gitignore_path.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.splitlines()]
            missing = []
            for item in entries_to_add:
                item_clean = item.rstrip("/")
                if not any(l == item or l == item_clean or l == f"{item_clean}/*" for l in lines):
                    missing.append(item)

            if missing:
                with open(gitignore_path, "a", encoding="utf-8") as f:
                    f.write("\n# Multi-agent Jira credentials & cache (Auto-added by jira-management)\n" + "\n".join(missing) + "\n")
            return True
        except Exception:
            return False
    else:
        try:
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write("# Multi-agent Jira credentials & cache (Auto-added by jira-management)\n" + "\n".join(entries_to_add) + "\n")
            return True
        except Exception:
            return False
    return False


def get_project_cache_path(project_root: Path) -> Path:
    """Return the absolute path to the project's primary jira cache file."""
    return project_root / CACHE_DIR_NAME / CACHE_FILE_NAME


def get_all_project_cache_paths(project_root: Path) -> List[Path]:
    """Return all recognized project-level cache locations across various agents."""
    return [
        project_root / CACHE_DIR_NAME / CACHE_FILE_NAME,
        project_root / ".claude" / CACHE_FILE_NAME,
        project_root / ".cursor" / CACHE_FILE_NAME,
    ]


def get_global_cache_path() -> Path:
    """Return the primary path to the user's global config cache."""
    return Path.home() / ".gemini" / "config" / CACHE_FILE_NAME


def get_all_global_cache_paths() -> List[Path]:
    """Return all recognized global cache locations across supported agents."""
    home = Path.home()
    return [
        home / ".gemini" / "config" / CACHE_FILE_NAME,
        home / ".claude" / CACHE_FILE_NAME,
        home / ".cursor" / CACHE_FILE_NAME,
        home / ".config" / "jira" / CACHE_FILE_NAME,
        home / ".jira" / CACHE_FILE_NAME,
        home / ".jira" / "config.json",
    ]


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

    # 2. Check Project Caches (.agent/jira.json, .claude/jira.json, .cursor/jira.json)
    for cache_path in get_all_project_cache_paths(root):
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

    # 5. Check Global User Caches (~/.gemini, ~/.claude, ~/.cursor, ~/.config/jira, ~/.jira)
    for global_cache in get_all_global_cache_paths():
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

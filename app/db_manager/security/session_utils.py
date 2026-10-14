"""
Session utilities.

Helpers for generating session identifiers and human-readable device
labels from User-Agent strings.
"""
import hashlib
import secrets
from typing import Optional


def generate_session_id() -> str:
    """Return a URL-safe random session identifier (64 hex chars)."""
    return secrets.token_hex(32)


def hash_session_id(session_id: str) -> str:
    """Return a stable short hash for logging."""
    if not session_id:
        return ""
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16]


def describe_device(user_agent: Optional[str]) -> str:
    """
    Return a short human-readable label from a User-Agent string.
    """
    if not user_agent:
        return "Unknown device"

    ua = user_agent.lower()

    # Browser detection (order matters)
    if "edg/" in ua or "edge/" in ua:
        browser = "Edge"
    elif "opr/" in ua or "opera" in ua:
        browser = "Opera"
    elif "chrome/" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "firefox/" in ua:
        browser = "Firefox"
    elif "safari/" in ua:
        browser = "Safari"
    elif "curl/" in ua:
        browser = "curl"
    elif "python" in ua or "httpx" in ua:
        browser = "Python"
    else:
        browser = "Browser"

    # OS detection
    if "iphone" in ua or "ipad" in ua:
        os_name = "iOS"
    elif "android" in ua:
        os_name = "Android"
    elif "mac os" in ua or "macintosh" in ua:
        os_name = "macOS"
    elif "windows" in ua:
        os_name = "Windows"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = None

    return f"{browser} on {os_name}" if os_name else browser

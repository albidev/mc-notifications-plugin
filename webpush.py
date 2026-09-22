"""Web Push channel adapter for the notifications plugin.

The Mission Control host already owns the browser service worker, VAPID
configuration, and subscription registry. This module only adapts that channel
to the plugin-owned delivery queue; it degrades cleanly when the optional host
push module is unavailable or disabled.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import importlib

try:
    _push_server = importlib.import_module("push_server")
    list_subscriptions = _push_server.list_subscriptions
    push_status = _push_server.push_status
    send_push = _push_server.send_push
except ImportError:  # plugin unit tests / standalone loading
    list_subscriptions = None  # type: ignore[assignment]
    push_status = None  # type: ignore[assignment]
    send_push = None  # type: ignore[assignment]


def status() -> Dict[str, Any]:
    if push_status is None:
        return {"enabled": False, "reason": "host_push_unavailable"}
    try:
        result = push_status()
        return dict(result) if isinstance(result, dict) else {"enabled": False, "reason": "invalid_host_status"}
    except Exception:
        return {"enabled": False, "reason": "host_push_unavailable"}


def has_subscriptions() -> bool:
    if list_subscriptions is None:
        return False
    try:
        return bool(list_subscriptions())
    except Exception:
        return False


def queue_target() -> Optional[str]:
    """Return the stable broadcast target when Web Push can currently deliver."""
    current = status()
    if current.get("reason") != "ok" or not has_subscriptions():
        return None
    return "broadcast"


def send(notification: Dict[str, Any]) -> Dict[str, Any]:
    """Send one notification through the host's VAPID/Web Push adapter."""
    current = status()
    if current.get("reason") != "ok":
        return {"ok": False, "retryable": False, "error": str(current.get("reason") or "push_disabled")}
    if send_push is None:
        return {"ok": False, "retryable": False, "error": "host_push_unavailable"}
    try:
        result = send_push(
            str(notification.get("title") or "Hermes Mission Control"),
            str(notification.get("body") or "")[:240],
            tag=f"notification-{notification.get('id')}",
            data={"url": notification.get("deepLink") or "/notifications", "notificationId": notification.get("id")},
        )
    except Exception as exc:
        return {"ok": False, "retryable": True, "error": str(exc)[:2000]}
    if result.get("disabled"):
        return {"ok": False, "retryable": False, "error": str(result.get("reason") or "push_disabled")}
    if int(result.get("sent", 0)) > 0:
        return {"ok": True, "sent": int(result.get("sent", 0)), "failed": int(result.get("failed", 0))}
    if int(result.get("failed", 0)) > 0:
        return {"ok": False, "retryable": True, "error": "all Web Push deliveries failed"}
    return {"ok": False, "retryable": False, "error": "no active Web Push subscriptions"}

"""HTTP adapter for the Mission Control Notifications plugin."""
from __future__ import annotations

from typing import Any, Dict, List

from . import handlers


class PluginError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def listNotifications(body: Dict[str, Any], params: Dict[str, List[str]], auth: Any = None) -> Dict[str, Any]:
    try:
        limit = min(max(int((params.get("limit") or ["50"])[0]), 1), 100)
        offset = max(int((params.get("offset") or ["0"])[0]), 0)
    except (TypeError, ValueError):
        raise PluginError(400, "bad_request", "limit and offset must be integers")
    unread_only = (params.get("unread") or ["0"])[0].lower() in {"1", "true", "yes"}
    read_filter = (params.get("read") or [None])[0] or None
    if read_filter is not None:
        read_filter = read_filter.lower()
        if read_filter not in {"read", "unread"}:
            raise PluginError(400, "bad_request", "read must be read or unread")
    search = (params.get("q") or [None])[0] or None
    profile = (params.get("profile") or [None])[0] or None
    try:
        return handlers.list_notifications(
            limit=limit,
            offset=offset,
            unread_only=unread_only,
            read_filter=read_filter,
            search=search,
            profile=profile,
        )
    except ValueError as exc:
        raise PluginError(400, "bad_request", str(exc)) from exc


def publishNotification(body: Dict[str, Any], params: Dict[str, List[str]], auth: Any = None) -> Dict[str, Any]:
    try:
        notification = handlers.publish_notification(body)
    except handlers.NotificationValidationError as exc:
        raise PluginError(400, "bad_request", str(exc)) from exc
    return {"success": True, "notification": notification}


def markNotificationRead(body: Dict[str, Any], params: Dict[str, List[str]], auth: Any = None) -> Dict[str, Any]:
    notification_id = str(body.get("id") or "").strip()
    if not notification_id:
        raise PluginError(400, "bad_request", "Missing id")
    notification = handlers.mark_notification_read(notification_id)
    if notification is None:
        raise PluginError(404, "not_found", f"Notification {notification_id} not found")
    return {"success": True, "notification": notification}


def markAllNotificationsRead(body: Dict[str, Any], params: Dict[str, List[str]], auth: Any = None) -> Dict[str, Any]:
    profile = str(body.get("profile") or "").strip() or None
    return {"success": True, **handlers.mark_all_notifications_read(profile=profile)}

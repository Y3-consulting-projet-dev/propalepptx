from shared.serializers import serialize_notification


def build_notifications_for_user(doc: dict, user_id: str) -> list[dict]:
    notifications = []
    for notification in (doc.get("notifications") or []):
        if not isinstance(notification, dict):
            continue
        if str(notification.get("user_id") or "") != user_id:
            continue
        payload = serialize_notification(notification)
        payload.setdefault("presentation_id", doc.get("presentation_id"))
        payload.setdefault("filename", doc.get("filename"))
        notifications.append(payload)
    return notifications

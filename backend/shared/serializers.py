from .time_utils import serialize_timestamp


def serialize(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def serialize_client(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def build_user_display_name(user: dict | None) -> str | None:
    if not user:
        return None
    if user.get("name"):
        return str(user["name"]).strip()
    parts = [str(user.get("first_name") or "").strip(), str(user.get("last_name") or "").strip()]
    full_name = " ".join(part for part in parts if part)
    return full_name or user.get("email")


def serialize_comment(comment: dict) -> dict:
    payload = dict(comment or {})
    payload["created_at"] = serialize_timestamp(payload.get("created_at"))
    payload["updated_at"] = serialize_timestamp(payload.get("updated_at"))
    return payload


def serialize_notification(notification: dict) -> dict:
    payload = dict(notification or {})
    payload["created_at"] = serialize_timestamp(payload.get("created_at"))
    payload["read_at"] = serialize_timestamp(payload.get("read_at"))
    return payload


def serialize_user_brief(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "name": build_user_display_name(user),
        "email": user.get("email"),
        "grade": user.get("grade"),
        "code_categorie": user.get("code_categorie"),
    }

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from extensions import presentations_col
from shared.auth_utils import get_current_user_doc
from shared.time_utils import utc_now

from .service import build_notifications_for_user

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notifications_bp.route("", methods=["GET"])
@jwt_required()
def list_notifications():
    current_user = get_current_user_doc()
    if not current_user:
        return jsonify({"error": "User not found"}), 404

    user_id = str(current_user["_id"])
    docs = list(
        presentations_col.find(
            {"notifications.user_id": user_id},
            {"_id": 0, "presentation_id": 1, "filename": 1, "notifications": 1},
        )
    )
    notifications = []
    for doc in docs:
        notifications.extend(build_notifications_for_user(doc, user_id))

    notifications.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    unread_count = sum(1 for item in notifications if item.get("read_at") in (None, ""))
    return jsonify({"items": notifications[:20], "unread_count": unread_count})


@notifications_bp.route("/read", methods=["POST"])
@jwt_required()
def mark_notifications_read():
    current_user = get_current_user_doc()
    if not current_user:
        return jsonify({"error": "User not found"}), 404

    user_id = str(current_user["_id"])
    payload = request.get_json(silent=True) or {}
    presentation_id = str(payload.get("presentation_id") or "").strip()

    query = {"notifications.user_id": user_id}
    if presentation_id:
        query["presentation_id"] = presentation_id

    presentations_col.update_many(
        query,
        {"$set": {"notifications.$[item].read_at": utc_now()}},
        array_filters=[{"item.user_id": user_id, "item.read_at": None}],
    )
    return jsonify({"ok": True})

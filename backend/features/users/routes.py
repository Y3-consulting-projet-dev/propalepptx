from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from models import User
from shared.auth_utils import get_current_user_doc
from shared.grades import ASSOCIATE_GRADES, MANAGER_REVIEWER_GRADES
from shared.serializers import serialize_user_brief
from shared.time_utils import utc_now

users_bp = Blueprint("users", __name__, url_prefix="/api")


@users_bp.route("/users/reviewers", methods=["GET"])
def list_reviewers():
    users = list(User.collection.find({"is_active": True}))
    managers = [
        serialize_user_brief(user)
        for user in users
        if user.get("grade") in MANAGER_REVIEWER_GRADES
    ]
    associates = [
        serialize_user_brief(user)
        for user in users
        if user.get("grade") in ASSOCIATE_GRADES
    ]

    managers.sort(key=lambda item: (item.get("name") or "", item.get("email") or ""))
    associates.sort(key=lambda item: (item.get("name") or "", item.get("email") or ""))
    return jsonify({"managers": managers, "associates": associates})


@users_bp.route("/session/heartbeat", methods=["POST"])
@jwt_required()
def session_heartbeat():
    current_user = get_current_user_doc()
    if not current_user:
        return jsonify({"error": "User not found"}), 404

    User.collection.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"last_seen_at": utc_now()}},
    )
    return jsonify({"ok": True})

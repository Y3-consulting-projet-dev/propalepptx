from datetime import timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from extensions import presentations_col
from models import User
from shared.auth_utils import get_current_user_doc
from shared.time_utils import ensure_utc_datetime, utc_now

from features.presentations.permissions import can_access_presentation
from features.presentations.service import build_presentation_search_text

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/summary", methods=["GET"])
@jwt_required()
def dashboard_summary():
    current_user = get_current_user_doc()
    if not current_user:
        return jsonify({"error": "User not found"}), 404

    active_since = utc_now() - timedelta(minutes=5)
    active_count = User.collection.count_documents({
        "is_active": True,
        "last_seen_at": {"$gte": active_since},
    })

    query = str(request.args.get("q") or "").strip().lower()
    docs = list(
        presentations_col.find({}, {
            "_id": 0,
            "presentation_id": 1,
            "filename": 1,
            "form": 1,
            "status": 1,
            "created_at": 1,
            "updated_at": 1,
            "owner_name": 1,
            "owner_user_id": 1,
            "current_reviewer_user_id": 1,
            "submission_history": 1,
            "template": 1,
        }).sort("created_at", -1)
    )

    visible_docs = [doc for doc in docs if can_access_presentation(doc, current_user)]
    if query:
        visible_docs = [doc for doc in visible_docs if query in build_presentation_search_text(doc)]
    limit = 20 if query else 3
    recent_docs = visible_docs[:limit]

    items = []
    for doc in recent_docs:
        created_at = ensure_utc_datetime(doc.get("created_at"))
        updated_at = ensure_utc_datetime(doc.get("updated_at"))
        items.append({
            "presentation_id": doc.get("presentation_id"),
            "title": (doc.get("filename") or "Présentation").replace(".pptx", ""),
            "mission_type": (doc.get("form") or {}).get("missionType"),
            "client_name": (doc.get("form") or {}).get("clientName"),
            "status": doc.get("status"),
            "owner_name": doc.get("owner_name"),
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
        })

    return jsonify({
        "active_users_count": active_count,
        "recent_presentations": items,
    })

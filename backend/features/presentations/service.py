from models import User
from shared.grades import (
    ASSISTANT_SUBMISSION_GRADES,
    ASSOCIATE_GRADES,
    MANAGER_REVIEWER_GRADES,
    MANAGER_SUBMISSION_GRADES,
)
from shared.serializers import build_user_display_name, serialize, serialize_comment
from shared.text_utils import normalize_person_label

from .permissions import (
    can_comment_on_presentation,
    can_return_presentation_for_corrections,
    can_submit_presentation,
    can_validate_presentation,
)


def resolve_user_from_reference(reference: str | None, allowed_grades: set[str] | None = None):
    if not reference:
        return None

    normalized_ref = normalize_person_label(reference)
    if not normalized_ref:
        return None

    for user in User.collection.find({"is_active": True}):
        if allowed_grades and user.get("grade") not in allowed_grades:
            continue

        candidates = {
            normalize_person_label(user.get("email")),
            normalize_person_label(user.get("name")),
            normalize_person_label(
                f"{str(user.get('first_name') or '').strip()} {str(user.get('last_name') or '').strip()}"
            ),
            normalize_person_label(
                f"{str(user.get('last_name') or '').strip()} {str(user.get('first_name') or '').strip()}"
            ),
        }
        if normalized_ref in candidates:
            return user
    return None


def extract_manager_user_ids(doc: dict) -> set[str]:
    manager_ids: set[str] = set()
    history = doc.get("submission_history") or []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        if entry.get("submitted_to_role") == "manager":
            user_id = str(entry.get("submitted_to_user_id") or "").strip()
            if user_id:
                manager_ids.add(user_id)
        if entry.get("status") == "submitted_to_associate":
            user_id = str(entry.get("submitted_by_user_id") or "").strip()
            if user_id:
                manager_ids.add(user_id)
        if entry.get("action") == "returned_for_corrections":
            user_id = str(entry.get("submitted_by_user_id") or "").strip()
            if user_id:
                manager_ids.add(user_id)
    current_reviewer_id = str(doc.get("current_reviewer_user_id") or "").strip()
    if current_reviewer_id:
        current_grade = str(doc.get("current_reviewer_grade") or "")
        if current_grade in MANAGER_SUBMISSION_GRADES:
            manager_ids.add(current_reviewer_id)
    return manager_ids


def build_comment_visibility_user_ids(doc: dict, author: dict) -> list[str]:
    owner_id = str(doc.get("owner_user_id") or "").strip()
    manager_ids = extract_manager_user_ids(doc)
    author_id = str(author.get("_id") or "").strip()

    visible_ids = {user_id for user_id in [owner_id, author_id] if user_id}
    visible_ids.update(manager_ids)
    return sorted(visible_ids)


def get_visible_slide_comments(doc: dict, viewer: dict) -> list[dict]:
    viewer_id = str(viewer["_id"])
    comments = []
    for comment in (doc.get("slide_comments") or []):
        if not isinstance(comment, dict):
            continue
        visible_to = {str(user_id).strip() for user_id in (comment.get("visible_to_user_ids") or []) if str(user_id).strip()}
        author_id = str(comment.get("author_user_id") or "").strip()
        if viewer_id == author_id or not visible_to or viewer_id in visible_to:
            comments.append(serialize_comment(comment))
    return sorted(comments, key=lambda item: item.get("created_at") or "")


def build_presentation_search_text(doc: dict) -> str:
    form = doc.get("form") or {}
    fields = [
        doc.get("filename"),
        doc.get("owner_name"),
        doc.get("template"),
        form.get("missionType"),
        form.get("clientName"),
        form.get("manager"),
        form.get("partner"),
        form.get("sector"),
    ]
    values = []
    for field in fields:
        if isinstance(field, list):
            values.extend(str(item).strip() for item in field if str(item).strip())
        elif field:
            values.append(str(field).strip())
    return " ".join(values).lower()


def resolve_next_submission_target(actor: dict, presentation_doc: dict):
    grade = actor.get("grade")
    form = presentation_doc.get("form") or {}
    partner_reference = form.get("partner")
    if isinstance(partner_reference, list):
        partner_reference = next(
            (str(item).strip() for item in partner_reference if str(item).strip()),
            None,
        )

    if grade in ASSISTANT_SUBMISSION_GRADES:
        return (
            "manager",
            form.get("manager"),
            MANAGER_REVIEWER_GRADES,
            "submitted_to_manager",
            "Soumettre au manager",
        )
    if grade in MANAGER_SUBMISSION_GRADES:
        return (
            "associate",
            partner_reference,
            ASSOCIATE_GRADES,
            "submitted_to_associate",
            "Soumettre à l'associé",
        )
    if grade in ASSOCIATE_GRADES:
        return None
    return None


def build_presentation_response(doc: dict, viewer: dict) -> dict:
    payload = serialize(doc.copy())
    owner_id = str(doc.get("owner_user_id") or "")
    viewer_id = str(viewer["_id"])
    history = doc.get("submission_history") or []
    has_been_reviewer = any(
        str(entry.get("submitted_to_user_id") or "") == viewer_id
        for entry in history
        if isinstance(entry, dict)
    )
    submission_allowed = can_submit_presentation(doc, viewer)
    next_target = resolve_next_submission_target(viewer, doc) if submission_allowed else None
    target_user = None
    if next_target:
        target_user = resolve_user_from_reference(next_target[1], allowed_grades=next_target[2])
    comments = sorted(
        get_visible_slide_comments(doc, viewer),
        key=lambda item: item.get("created_at") or "",
    )
    payload.update({
        "is_owner": owner_id == viewer_id,
        "is_reviewer": str(doc.get("current_reviewer_user_id") or "") == viewer_id,
        "has_been_reviewer": has_been_reviewer,
        "can_submit": target_user is not None and submission_allowed,
        "can_validate": can_validate_presentation(doc, viewer),
        "can_comment": can_comment_on_presentation(doc, viewer),
        "can_return_for_corrections": can_return_presentation_for_corrections(doc, viewer),
        "submit_action_label": next_target[4] if next_target else None,
        "validate_action_label": "Valider la présentation",
        "return_action_label": "Renvoyer à l'assistant pour correction",
        "current_reviewer_name": doc.get("current_reviewer_name"),
        "next_reviewer_name": build_user_display_name(target_user),
        "owner_name": doc.get("owner_name"),
        "slide_comments": comments,
    })
    return payload

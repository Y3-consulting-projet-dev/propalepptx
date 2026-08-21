from shared.grades import (
    ASSISTANT_SUBMISSION_GRADES,
    ASSOCIATE_GRADES,
    COMMENTER_GRADES,
    MANAGER_SUBMISSION_GRADES,
)


def can_access_presentation(doc: dict, user: dict) -> bool:
    user_id = str(user["_id"])
    history = doc.get("submission_history") or []
    has_been_reviewer = any(
        str(entry.get("submitted_to_user_id") or "") == user_id
        for entry in history
        if isinstance(entry, dict)
    )
    return (
        str(doc.get("owner_user_id") or "") == user_id
        or str(doc.get("current_reviewer_user_id") or "") == user_id
        or has_been_reviewer
    )


def can_submit_presentation(doc: dict, user: dict) -> bool:
    if not can_access_presentation(doc, user):
        return False

    user_id = str(user["_id"])
    user_grade = user.get("grade")
    current_reviewer_id = str(doc.get("current_reviewer_user_id") or "")
    owner_id = str(doc.get("owner_user_id") or "")

    if user_grade in ASSOCIATE_GRADES:
        return False

    if user_grade in ASSISTANT_SUBMISSION_GRADES:
        return owner_id == user_id

    if user_grade in MANAGER_SUBMISSION_GRADES:
        return True

    if current_reviewer_id:
        return current_reviewer_id == user_id

    return owner_id == user_id


def can_comment_on_presentation(doc: dict, user: dict) -> bool:
    return can_access_presentation(doc, user) and user.get("grade") in COMMENTER_GRADES


def can_return_presentation_for_corrections(doc: dict, user: dict) -> bool:
    return (
        can_access_presentation(doc, user)
        and str(doc.get("current_reviewer_user_id") or "") == str(user["_id"])
        and str(doc.get("owner_user_id") or "") != str(user["_id"])
        and user.get("grade") in MANAGER_SUBMISSION_GRADES
    )


def can_validate_presentation(doc: dict, user: dict) -> bool:
    return (
        can_access_presentation(doc, user)
        and str(doc.get("current_reviewer_user_id") or "") == str(user["_id"])
        and user.get("grade") in ASSOCIATE_GRADES
        and str(doc.get("status") or "") == "submitted_to_associate"
    )

from flask_jwt_extended import get_jwt_identity

from models import User


def get_current_user_doc():
    user_id = get_jwt_identity()
    if not user_id:
        return None
    try:
        return User.find_by_id(user_id)
    except Exception:
        return None

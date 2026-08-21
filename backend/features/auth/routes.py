import bcrypt
from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from models import User
from shared.text_utils import normalize_email
from shared.time_utils import utc_now

from .service import validate_password_strength

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required"}), 400

    email = normalize_email(data['email'])
    password = data['password']
    name = data.get('name')

    password_error = validate_password_strength(password)
    if password_error:
        return jsonify({"error": password_error}), 400

    if User.find_by_email(email):
        return jsonify({"error": "User already exists"}), 409

    try:
        user_id = User.create_user(email, password, name)
        return jsonify({
            "message": "User created successfully",
            "user_id": user_id
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required"}), 400

    email = normalize_email(data['email'])
    password = data['password']

    user = User.find_by_email(email)
    if not user or not user.get("is_active", True) or not User.verify_password(user['password'], password):
        return jsonify({"error": "Invalid credentials"}), 401

    now = utc_now()
    User.collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_seen_at": now, "last_login_at": now}},
    )
    access_token = create_access_token(identity=str(user['_id']))
    return jsonify({
        "access_token": access_token,
        "user": {
            "id": str(user['_id']),
            "email": user['email'],
            "name": user.get('name'),
            "first_name": user.get('first_name'),
            "last_name": user.get('last_name'),
            "code_categorie": user.get('code_categorie'),
            "grade": user.get('grade'),
            "department": user.get('department'),
        }
    }), 200


@auth_bp.route("/change_password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        return jsonify({"error": "old_password and new_password are required"}), 400

    password_error = validate_password_strength(new_password)
    if password_error:
        return jsonify({"error": password_error}), 400

    try:
        user = User.collection.find_one({"_id": ObjectId(user_id)}, {"password": 1})
        if not user:
            return jsonify({"error": "User not found"}), 404

        if not User.verify_password(user["password"], old_password):
            # The user is authenticated (JWT ok) but provided a wrong current password.
            # Return a validation error (not an auth/session error).
            return jsonify({"error": "Old password is incorrect"}), 400

        hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        User.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password": hashed_password, "updated_at": utc_now()}},
        )

        return jsonify({"message": "Password updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

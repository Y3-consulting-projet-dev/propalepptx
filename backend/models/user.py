from datetime import datetime

import bcrypt
from bson import ObjectId

from extensions import users_col


class User:
    collection = users_col

    @staticmethod
    def create_user(email, password, name=None):
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        user_data = {
            'email': email,
            'password': hashed_password,
            'name': name,
            'created_at': datetime.utcnow(),
            'is_active': True
        }

        result = User.collection.insert_one(user_data)
        return str(result.inserted_id)

    @staticmethod
    def find_by_email(email):
        return User.collection.find_one({'email': email})

    @staticmethod
    def find_by_id(user_id):
        return User.collection.find_one({'_id': ObjectId(user_id)})

    @staticmethod
    def verify_password(stored_password, provided_password):
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password)

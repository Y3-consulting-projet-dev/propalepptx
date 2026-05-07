from datetime import datetime
from pymongo import MongoClient
from config import Config
import bcrypt

class Database:
    def __init__(self):
        self.client = MongoClient(Config.MONGO_URI)
        self.db = self.client.get_database()

    def get_collection(self, name):
        return self.db[name]

# Initialize database connection
db = Database()

class User:
    collection = db.get_collection('users')

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
        from bson import ObjectId
        return User.collection.find_one({'_id': ObjectId(user_id)})

    @staticmethod
    def verify_password(stored_password, provided_password):
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password)

class Proposal:
    collection = db.get_collection('proposals')

    @staticmethod
    def create_proposal(user_id, title, content, pptx_url=None):
        proposal_data = {
            'user_id': user_id,
            'title': title,
            'content': content,
            'pptx_url': pptx_url,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = Proposal.collection.insert_one(proposal_data)
        return str(result.inserted_id)

    @staticmethod
    def find_by_user(user_id):
        return list(Proposal.collection.find({'user_id': user_id}).sort('created_at', -1))

    @staticmethod
    def find_by_id(proposal_id):
        from bson import ObjectId
        return Proposal.collection.find_one({'_id': ObjectId(proposal_id)})

    @staticmethod
    def update_pptx_url(proposal_id, pptx_url):
        from bson import ObjectId
        Proposal.collection.update_one(
            {'_id': ObjectId(proposal_id)},
            {'$set': {'pptx_url': pptx_url, 'updated_at': datetime.utcnow()}}
        )


class Element:
    collection = db.get_collection('elements')

    @staticmethod
    def create_element(user_id, name, value=None, metadata=None):
        element_data = {
            'user_id': user_id,
            'name': name,
            'value': value,
            'metadata': metadata or {},
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = Element.collection.insert_one(element_data)
        return str(result.inserted_id)

    @staticmethod
    def find_by_user(user_id):
        return list(Element.collection.find({'user_id': user_id}).sort('created_at', -1))

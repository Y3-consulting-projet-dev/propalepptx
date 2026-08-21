from datetime import datetime

from extensions import elements_col


class Element:
    collection = elements_col

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

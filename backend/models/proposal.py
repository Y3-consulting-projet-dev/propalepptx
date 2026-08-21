from datetime import datetime

from bson import ObjectId

from extensions import proposals_col


class Proposal:
    collection = proposals_col

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
        return Proposal.collection.find_one({'_id': ObjectId(proposal_id)})

    @staticmethod
    def update_pptx_url(proposal_id, pptx_url):
        Proposal.collection.update_one(
            {'_id': ObjectId(proposal_id)},
            {'$set': {'pptx_url': pptx_url, 'updated_at': datetime.utcnow()}}
        )

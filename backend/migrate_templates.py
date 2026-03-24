import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

SOURCE_URI = os.getenv("TEMPLATES_SOURCE_URI", "mongodb://127.0.0.1:27017/propale")
TARGET_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/propalepptx")


def main():
    source_client = MongoClient(SOURCE_URI)
    target_client = MongoClient(TARGET_URI)

    source_db = source_client.get_default_database()
    target_db = target_client.get_default_database()

    source_col = source_db["templates"]
    target_col = target_db["templates"]

    docs = list(source_col.find({}))
    if not docs:
        print("No templates to migrate.")
        return

    # Remove _id to avoid duplicate key errors
    for d in docs:
        d.pop("_id", None)

    target_col.insert_many(docs)
    print(f"Migrated {len(docs)} templates to {target_db.name}.")


if __name__ == "__main__":
    main()

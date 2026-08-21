import os
from pathlib import Path

from dotenv import load_dotenv
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from pymongo import MongoClient

from config import Config

load_dotenv()

cors = CORS()
jwt = JWTManager()

MONGO_URI = os.getenv("MONGO_URI", Config.MONGO_URI)
LIBRARY_DIR = os.getenv("LIBRARY_DIR", str(Path(__file__).resolve().parents[1] / "Propale_library"))
CACHE_DIR = os.getenv("CACHE_DIR", str(Path(__file__).resolve().parents[1] / "Propale_cache"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", str(Path(__file__).resolve().parents[1] / "Propale_output"))
LIBREOFFICE_PATH = os.getenv("LIBREOFFICE_PATH", "")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client.get_default_database()

users_col = db["users"]
proposals_col = db["proposals"]
elements_col = db["elements"]
templates_col = db["templates"]
presentations_col = db["presentations"]
clients_col = db["clients"]

cache_path = Path(CACHE_DIR)
output_path = Path(OUTPUT_DIR)
cache_path.mkdir(parents=True, exist_ok=True)
output_path.mkdir(parents=True, exist_ok=True)

UPLOAD_FOLDER = "uploads"
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

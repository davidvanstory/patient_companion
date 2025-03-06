from typing import TypedDict, Any
import os
from dotenv import load_dotenv
from pymongo import DESCENDING, MongoClient
import requests

_ = load_dotenv()

# MONGO_URI: str | None = os.getenv("MONGODB_URI") 
MONGO_URI = os.getenv("MONGODB_URI")  # Remove type annotation   
client = MongoClient(MONGO_URI)
db = client['eleven_labs_assistant']
callers_collection = db['callers']

class User(TypedDict):
    phone_number: str
    name: str


def get_user_from_db(phone_number: str) -> User | None:
    
    last_doc: Any | None = callers_collection.find_one(filter={"phone_number": phone_number}, sort=[("_id", DESCENDING)])
    if last_doc:
        return last_doc
    else:
        return None
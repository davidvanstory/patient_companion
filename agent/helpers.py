from typing import TypedDict, Any
import os
from dotenv import load_dotenv
from pymongo import DESCENDING, MongoClient
from pymongo.results import InsertOneResult
import requests


_ = load_dotenv()

# MONGO_URI: str | None = os.getenv("MONGODB_URI") 
MONGO_URI = os.getenv("MONGODB_URI")  # Remove type annotation   
client = MongoClient(MONGO_URI)
db = client['patient_companion_assistant']
callers_collection = db['callers']
symptoms_collection = db['symptoms']

class User(TypedDict):
    phone_number: str
    name: str

def save_user(user: User) -> bool:
    result: InsertOneResult = callers_collection.insert_one(document=user)
    if result.inserted_id:
        return True
    else:
        return False

def get_user_from_db(phone_number: str) -> User | None:
    
    last_doc: Any | None = callers_collection.find_one(filter={"phone_number": phone_number}, sort=[("_id", DESCENDING)])
    if last_doc:
        return last_doc
    else:
        return None

def save_symptom(note: str) -> bool:
    result = symptoms_collection.insert_one({"symptom": note})
    if result.inserted_id:
        return True
    else:
        return False

def get_symptom_from_db() -> str:
    last_doc = symptoms_collection.find_one(sort=[("_id", DESCENDING)])
    if last_doc:
        return last_doc['symptom']
    else:
        return "couldn't find any relevant note"
    
#append symptom to the db

def query_perplexity(query: str):
    url = "https://api.perplexity.ai/chat/completions"

    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "sonar",
        "messages": [
            { "role": "system", "content": "You are an AI assistant." },
            { "role": "user", "content": query },
        ],
        "max_tokens": 1024,
    }

    response = requests.post(url, headers=headers, json=data)
    citations = response.json()['citations']
    output = response.json()['choices'][0]['message']['content']
    return output

def search_patient_query(note: str) -> str:
    result = query_perplexity(note)
    return result


# schedule appointment
# 
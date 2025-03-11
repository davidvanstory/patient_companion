from typing import TypedDict, Any
import os
from dotenv import load_dotenv
from pymongo import DESCENDING, MongoClient
from pymongo.results import InsertOneResult
import requests
import logging
from pymongo.errors import PyMongoError


_ = load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MONGO_URI: str | None = os.getenv("MONGODB_URI") 
MONGO_URI = os.getenv("MONGODB_URI")  # Remove type annotation   
if not MONGO_URI:
    logger.error("MONGODB_URI environment variable is not set")
    raise ValueError("MONGODB_URI environment variable is not set")

try:
    client = MongoClient(MONGO_URI)
    client.admin.command('ping')
    logger.info("Successfully connected to MongoDB")
    
    db = client['patient_companion_assistant']
    callers_collection = db['callers']
    symptoms_collection = db['symptoms']
except PyMongoError as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

class User(TypedDict):
    phone_number: str
    name: str

def save_user(user: User) -> bool:
    try:
        result: InsertOneResult = callers_collection.insert_one(document=user)
        if result.inserted_id:
            logger.info(f"User saved successfully: {user['phone_number']}")
            return True
        else:
            logger.warning(f"Failed to save user: {user['phone_number']}")
            return False
    except PyMongoError as e:
        logger.error(f"MongoDB error while saving user: {e}")
        return False
    
def update_user_name(phone_number: str, name: str) -> bool:
    """
    Updates the name of an existing user identified by phone_number.
    
    Args:
        phone_number (str): The phone number of the user to update
        name (str): The new name to save for the user
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        # Log the operation for debugging
        logger.info(f"Attempting to update name for user with phone number: {phone_number}")
        
        # Find and update the user document
        result = callers_collection.update_one(
            {"phone_number": phone_number},
            {"$set": {"name": name}}
        )
        
        # Check if the update was successful
        if result.matched_count > 0:
            logger.info(f"Successfully updated name for user: {phone_number} to {name}")
            if result.modified_count > 0:
                logger.info(f"Document was modified")
            else:
                logger.info(f"Document matched but no changes were needed")
            return True
        else:
            logger.warning(f"No user found with phone number: {phone_number}")
            return False
            
    except PyMongoError as e:
        logger.error(f"MongoDB error while updating user name: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while updating user name: {e}")
        return False

def get_user_from_db(phone_number: str) -> User | None:
    try:
        last_doc: Any | None = callers_collection.find_one(filter={"phone_number": phone_number}, sort=[("_id", DESCENDING)])
        if last_doc:
            logger.info(f"User found: {phone_number}")
            return last_doc
        else:
            logger.info(f"User not found: {phone_number}")
            return None
    except PyMongoError as e:
        logger.error(f"MongoDB error while retrieving user: {e}")
        return None

def save_symptom(note: str) -> bool:
    try:
        logger.info(f"Attempting to save symptom: {note}")
        if not note or not isinstance(note, str):
            logger.warning(f"Invalid symptom format: {note}")
            return False
            
        document = {"symptom": note}
        logger.info(f"Inserting document: {document}")
        
        result = symptoms_collection.insert_one(document)
        if result.inserted_id:
            logger.info(f"Symptom saved successfully with ID: {result.inserted_id}")
            return True
        else:
            logger.warning("Failed to save symptom, no inserted_id returned")
            return False
    except PyMongoError as e:
        logger.error(f"MongoDB error while saving symptom: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while saving symptom: {e}")
        return False

def get_symptom_from_db() -> str:
    try:
        last_doc = symptoms_collection.find_one(sort=[("_id", DESCENDING)])
        if last_doc:
            logger.info(f"Retrieved symptom: {last_doc['symptom']}")
            return last_doc['symptom']
        else:
            logger.info("No symptoms found in database")
            return "couldn't find any relevant note"
    except PyMongoError as e:
        logger.error(f"MongoDB error while retrieving symptom: {e}")
        return "Error retrieving note from database"
    except Exception as e:
        logger.error(f"Unexpected error while retrieving symptom: {e}")
        return "Error retrieving note from database"
    
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
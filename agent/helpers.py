from typing import TypedDict, Any, List, Dict
import os
import datetime
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
    appointments_collection = db['appointments']

except PyMongoError as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

class User(TypedDict):
    phone_number: str
    name: str

class Symptom(TypedDict):
    symptom: str
    phone_number: str
    timestamp: datetime.datetime

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
        print(f"update_user_name called with phone_number: '{phone_number}', name: '{name}'")
        
        # Verify MongoDB connection is still alive
        try:
            client.admin.command('ping')
            print("MongoDB connection is alive")
        except Exception as e:
            print(f"MongoDB connection test failed: {e}")
            return False
        
        # Verify the collection exists
        db_list = client.list_database_names()
        print(f"Available databases: {db_list}")
        
        if 'patient_companion_assistant' in db_list:
            collections = db['patient_companion_assistant'].list_collection_names()
            print(f"Collections in patient_companion_assistant: {collections}")
        
        # Check if user exists before attempting update
        existing_user = callers_collection.find_one({"phone_number": phone_number})
        print(f"Existing user before update: {existing_user}")
        
        # Find and update the user document
        print(f"Executing update_one with filter: {{'phone_number': '{phone_number}'}} and update: {{'$set': {{'name': '{name}'}}}}")
        
        result = callers_collection.update_one(
            {"phone_number": phone_number},
            {"$set": {"name": name}}
        )
        
        # Log the update result
        print(f"update_one result - matched_count: {result.matched_count}, modified_count: {result.modified_count}")
        
        # Check if the update was successful
        if result.matched_count > 0:
            print(f"Match found for phone_number: {phone_number}")
            
            if result.modified_count > 0:
                print(f"Document was modified with new name: {name}")
            else:
                print(f"Document matched but no changes were needed (name may already be '{name}')")
                
            # Verify the update by retrieving the user again
            updated_user = callers_collection.find_one({"phone_number": phone_number})
            print(f"User document after update: {updated_user}")
            
            return True
        else:
            print(f"No user found with phone_number: {phone_number}")
            return False
            
    except Exception as e:
        import traceback
        print(f"Exception in update_user_name: {str(e)}")
        print(traceback.format_exc())
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

def save_symptom(symptom: str, phone_number: str = None) -> bool:
    try:
        logger.info(f"Attempting to save symptom: {symptom} for user: {phone_number}")
        if not symptom or not isinstance(symptom, str):
            logger.warning(f"Invalid symptom format: {symptom}")
            return False
            
        document = {
            "symptom": symptom,
            "phone_number": phone_number,
            "timestamp": datetime.datetime.now()
        }
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

def get_user_symptoms(phone_number: str) -> List[Dict[str, Any]]:
    """
    Retrieves all symptoms for a specific user by phone number.
    
    Args:
        phone_number (str): The phone number of the user
        
    Returns:
        List[Dict[str, Any]]: List of symptom documents for the user
    """
    try:
        if not phone_number:
            logger.warning("No phone number provided to get_user_symptoms")
            return []
            
        symptoms = list(symptoms_collection.find(
            {"phone_number": phone_number},
            sort=[("timestamp", DESCENDING)]
        ))
        
        logger.info(f"Retrieved {len(symptoms)} symptoms for user: {phone_number}")
        return symptoms
    except PyMongoError as e:
        logger.error(f"MongoDB error while retrieving symptoms for user {phone_number}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error while retrieving symptoms for user {phone_number}: {e}")
        return []

def append_symptom(symptom: str, phone_number: str = None) -> bool:
    """
    Appends a new symptom to a user's existing symptoms.
    This is useful for updating a patient's condition with new information.
    
    Args:
        symptom (str): The symptom to append
        phone_number (str, optional): The user's phone number
        
    Returns:
        bool: True if successful, False otherwise
    """
    return save_symptom(symptom, phone_number)  # Currently the same as save_symptom

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

def check_persistent_symptom(phone_number: str, symptom: str) -> bool:
    """Check if the previously recorded symptom for this user mentioned the given symptom"""
    try:
        # Ensure phone_number is a string with proper formatting
        if phone_number and not phone_number.startswith("+"):
            phone_number = "+" + phone_number
            
        # Get the most recent symptom before the current one
        previous_symptom = symptoms_collection.find_one(
            {"phone_number": phone_number},
            sort=[("timestamp", -1)],
            skip=1  # Skip the current/most recent symptom
        )
        
        # Check if a previous symptom exists and contains the keyword
        if previous_symptom and symptom.lower() in previous_symptom.get("symptom", "").lower():
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking persistent symptoms: {e}")
        return False
    
def save_appointment(note: str) -> bool:
    result = appointments_collection.insert_one({"apt": note})
    if result.inserted_id:
        return True
    else:
        return False
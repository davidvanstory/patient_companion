from fastapi import FastAPI, Request
import requests
from typing import Literal, Any, Dict, Union
import logging

from agent.helpers import (
    User, get_user_from_db, save_user, save_symptom, get_symptom_from_db, 
    search_patient_query, update_user_name, callers_collection
)

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
def read_root() -> dict[str, str]:
    return {}

@app.post(path="/agent/init")
async def init(request: Request) -> Dict[str, Any]:
    try:
        request_body = await request.json()
        caller_id = request_body['caller_id']
        logger.info(f"Initializing user with caller_id: {caller_id}")
        
        user: User | None = get_user_from_db(phone_number=caller_id)
        
        if not user:
            # Important: Use the same name in both database and response
            # This prevents confusion and keeps everything in sync
            initial_name = "new_user"  # You can change this if needed
            
            new_user: User = {
                "name": initial_name,
                "phone_number": caller_id
            }
            
            # Save the new user to the database
            if save_user(user=new_user):
                logger.info(f"New user created: {caller_id} with name: {initial_name}")
                return {"dynamic_variables": {
                    "name": initial_name,  # Use the same name as stored in DB
                    "phone_number": caller_id
                }}
            else:
                logger.error(f"Failed to save new user: {caller_id}")
                return {"status": "error", "message": "Failed to create user"}
        
        # User exists, return their actual stored name
        output: Dict[str, Any] = {
            "dynamic_variables": {
                "name": user['name'],
                "phone_number": user['phone_number'],
            }
        }
        logger.info(f"Existing user found: {user['phone_number']} with name: {user['name']}")
        return output
    except Exception as e:
        logger.error(f"Error in init endpoint: {str(e)}")
        return {"status": "error", "message": f"Server error: {str(e)}"}


@app.post("/agent/update-name")
async def update_name(request: Request) -> dict[str, str]:
    try:
        # Log that the endpoint was called
        logger.info("update-name endpoint called")
        
        # Parse the request body
        request_body = await request.json()
        logger.info(f"Parsed request body: {request_body}")
        
        # --- First, try to get caller_id from different sources ---
        caller_id = None
        
        # 1. Try request body
        if 'caller_id' in request_body:
            caller_id = request_body['caller_id']
            logger.info(f"Found caller_id in request body: {caller_id}")
        
        # 2. Try headers
        if not caller_id:
            caller_id = request.headers.get("X-Caller-ID")
            if caller_id:
                logger.info(f"Found caller_id in headers: {caller_id}")
        
        # 3. Try query params
        if not caller_id:
            caller_id = request.query_params.get("caller_id")
            if caller_id:
                logger.info(f"Found caller_id in query params: {caller_id}")
        
        # 4. Last resort: get the most recent caller
        if not caller_id:
            logger.warning("No caller_id found in request sources")
            latest_user = callers_collection.find_one(sort=[("_id", -1)])
            if latest_user:
                caller_id = latest_user.get("phone_number")
                logger.info(f"Using most recent caller: {caller_id}")
            else:
                logger.error("No callers in database and no caller_id provided")
                return {"status": "error", "message": "Missing caller_id and no recent callers found"}
        
        # --- Next, get the name to update ---
        if 'name' not in request_body:
            logger.error("Missing name parameter in request")
            return {"status": "error", "message": "Missing name parameter"}
        
        new_name = request_body['name']
        logger.info(f"Updating name for caller {caller_id} to {new_name}")
        
        # --- Now handle the database update ---
        user = get_user_from_db(phone_number=caller_id)
        
        if user:
            # Log the current state
            logger.info(f"Found existing user with name: {user.get('name')}")
            
            # Update existing user
            result = callers_collection.update_one(
                {"phone_number": caller_id},
                {"$set": {"name": new_name}}
            )
            
            success = result.acknowledged
            if success:
                logger.info(f"Successfully updated user {caller_id} name to {new_name}")
                if result.modified_count == 0:
                    logger.info("Note: No document changes were needed (name might be the same)")
            else:
                logger.error(f"Failed to update user {caller_id}")
        else:
            # Create new user
            logger.info(f"No existing user found for {caller_id}, creating new user")
            new_user = {
                "name": new_name,
                "phone_number": caller_id
            }
            result = callers_collection.insert_one(new_user)
            success = result.acknowledged
            
            if success:
                logger.info(f"Created new user with ID: {result.inserted_id}")
            else:
                logger.error(f"Failed to create new user for {caller_id}")
        
        # --- Return appropriate response ---
        if success:
            # Return dynamic_variables to match what the voice agent expects
            return {
                "status": "success", 
                "message": f"Name updated to {new_name}",
                "dynamic_variables": {
                    "name": new_name,
                    "phone_number": caller_id
                }
            }
        else:
            return {"status": "error", "message": "Failed to update name"}
    
    except Exception as e:
        import traceback
        logger.error(f"Exception in update_name endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return {"status": "error", "message": f"Server error: {str(e)}"}

@app.post("/agent/take-symptom")
async def take_symptom(request: Request) -> dict[str, str]:
    try:
        request_body = await request.json()
        if 'symptom' not in request_body:
            logger.warning("Missing 'symptom' field in request")
            return {"status": "error", "message": "Missing 'symptom' field in request"}
        
        symptom = request_body['symptom']
        if not symptom or not isinstance(symptom, str):
            logger.warning(f"Invalid symptom format: {symptom}")
            return {"status": "error", "message": f"Invalid symptom format: {symptom}"}
        
        logger.info(f"Received symptom: {symptom}")
        if save_symptom(symptom):
            logger.info("Symptom saved successfully")
            return {"status": "success", "message": "Symptom saved successfully"}
        else:
            logger.error("Failed to save symptom to database")
            return {"status": "error", "message": "Failed to save symptom to database"}
    except Exception as e:
        logger.error(f"Error in take_symptom endpoint: {str(e)}")
        return {"status": "error", "message": f"Server error: {str(e)}"}
    

@app.get("/agent/get-symptom")
async def get_symptom(request: Request) -> dict[str, str]:
    note = get_symptom_from_db()
    print("got note:", note)
    return {
        "note": note
    }

#append-symptom route here

@app.post("/agent/search")
async def search(request: Request) -> dict[str, str]:
    request_body = await request.json()
    result = search_patient_query(request_body['search_query'])
    return {
        "result": result
    }


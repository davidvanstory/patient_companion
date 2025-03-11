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
        user: User | None = get_user_from_db(phone_number=caller_id)
        
        if not user:
            new_user: User = {
                "name": "new_user",
                "phone_number": caller_id
            }
            # Save the new user to the database
            if save_user(user=new_user):
                logger.info(f"New user created: {caller_id}")
                return {"dynamic_variables": {
                    "name": "Test", 
                    "phone_number": caller_id}
                }
            else:
                logger.error(f"Failed to save new user: {caller_id}")
                return {"status": "error", "message": "Failed to create user"}
        
        output: Dict[str, Any] = {
            "dynamic_variables": {
                "name": user['name'],
                "phone_number": user['phone_number'],
            }
        }
        logger.info(f"User found: {output}")
        return output
    except Exception as e:
        logger.error(f"Error in init endpoint: {str(e)}")
        return {"status": "error", "message": "Server error"}


@app.post("/agent/update-name")
async def update_name(request: Request) -> dict[str, str]:
    try:
        # Log that the endpoint was called
        print("update-name endpoint called")
        
        # Parse the request body
        request_body = await request.json()
        print(f"Parsed request body: {request_body}")
        
        # Extract caller_id from Request header (if your voice agent sets it)
        caller_id = request.headers.get("X-Caller-ID")
        
        # If not in header, try to get from query parameters
        if not caller_id:
            caller_id = request.query_params.get("caller_id")
            
        # If still not found, use default value or error
        if not caller_id:
            print("Warning: No caller_id found in request, headers, or query parameters")
            # You can either:
            # 1. Return an error:
            # return {"status": "error", "message": "Missing caller_id"}
            # 2. Or use the most recent caller from the database:
            latest_user = callers_collection.find_one(sort=[("_id", -1)])
            if latest_user:
                caller_id = latest_user.get("phone_number")
                print(f"Using most recent caller: {caller_id}")
            else:
                return {"status": "error", "message": "No callers in database and no caller_id provided"}
        
        # Get name from request body
        if 'name' not in request_body:
            return {"status": "error", "message": "Missing name parameter"}
        
        new_name = request_body['name']
        print(f"Updating name for caller {caller_id} to {new_name}")
        
        # Check if user exists
        user = get_user_from_db(phone_number=caller_id)
        
        if user:
            # Update existing user
            result = callers_collection.update_one(
                {"phone_number": caller_id},
                {"$set": {"name": new_name}}
            )
            success = result.modified_count > 0
        else:
            # Create new user
            new_user = {
                "name": new_name,
                "phone_number": caller_id
            }
            result = callers_collection.insert_one(new_user)
            success = result.inserted_id is not None
        
        if success:
            return {"status": "success", "message": f"Name updated to {new_name}"}
        else:
            return {"status": "error", "message": "Failed to update name"}
    
    except Exception as e:
        import traceback
        print(f"Exception in update_name endpoint: {str(e)}")
        print(traceback.format_exc())
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


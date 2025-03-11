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
        
        # Get raw request body for debugging
        raw_body = await request.body()
        print(f"Raw request body: {raw_body}")
        
        # Parse the request body
        request_body = await request.json()
        print(f"Parsed request body: {request_body}")
        
        # Check for required fields
        if 'caller_id' not in request_body or 'name' not in request_body:
            print("Error: Missing required fields in request")
            return {
                "status": "error", 
                "message": "Missing required fields: caller_id and name are required"
            }
        
        caller_id = request_body['caller_id']
        new_name = request_body['name']
        
        print(f"Extracted fields - caller_id: '{caller_id}', name: '{new_name}'")
        
        # Validate inputs
        if not caller_id or not isinstance(caller_id, str):
            print(f"Error: Invalid caller_id format: {type(caller_id)}")
            return {"status": "error", "message": "Invalid caller_id format"}
            
        if not new_name or not isinstance(new_name, str):
            print(f"Error: Invalid name format: {type(new_name)}")
            return {"status": "error", "message": "Invalid name format"}
        
        # Check if user exists before update
        existing_user = get_user_from_db(phone_number=caller_id)
        print(f"Existing user lookup result: {existing_user}")
        
        # Try to update the user's name
        print(f"Calling update_user_name({caller_id}, {new_name})")
        update_result = update_user_name(caller_id, new_name)
        print(f"update_user_name result: {update_result}")
        
        if update_result:
            # Verify the update by retrieving the user again
            updated_user = get_user_from_db(phone_number=caller_id)
            print(f"User after update: {updated_user}")
            return {"status": "success", "message": f"Name updated to {new_name}"}
        else:
            # If update fails, try to create a new user
            print("Update failed, attempting to create new user")
            new_user = {
                "name": new_name,
                "phone_number": caller_id
            }
            
            print(f"Calling save_user with {new_user}")
            save_result = save_user(user=new_user)
            print(f"save_user result: {save_result}")
            
            if save_result:
                return {"status": "success", "message": f"New user created with name {new_name}"}
                
            return {"status": "error", "message": "Failed to update or create user"}
            
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

@app.get("/test-update-name/{phone_number}/{name}")
async def test_update_name(phone_number: str, name: str):
    """Simple endpoint to test name updates using URL parameters"""
    try:
        # Print debug info
        print(f"test-update-name called for phone: {phone_number}, name: {name}")
        
        # Check if user exists
        user = get_user_from_db(phone_number=phone_number)
        user_existed = user is not None
        if user_existed:
            print(f"Found existing user: {user}")
        else:
            print(f"No existing user found for phone: {phone_number}")
        
        # Attempt to update or create user
        if user_existed:
            # Update existing user's name in MongoDB
            result = callers_collection.update_one(
                {"phone_number": phone_number},
                {"$set": {"name": name}}
            )
            print(f"Update result - matched: {result.matched_count}, modified: {result.modified_count}")
            success = result.modified_count > 0
        else:
            # Create new user
            new_user = {
                "name": name,
                "phone_number": phone_number
            }
            result = callers_collection.insert_one(new_user)
            print(f"Insert result - inserted_id: {result.inserted_id}")
            success = result.inserted_id is not None
        
        # Fetch the user after update to verify
        updated_user = get_user_from_db(phone_number=phone_number)
        print(f"User after operation: {updated_user}")
        
        return {
            "success": success,
            "existed_before": user_existed,
            "user_before": user,
            "user_after": updated_user
        }
    except Exception as e:
        print(f"Error in test-update-name: {str(e)}")
        return {"success": False, "error": str(e)}
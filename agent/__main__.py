from fastapi import FastAPI, Request
import requests
from typing import Literal, Any, Dict, Union

from agent.helpers import User, get_user_from_db, save_user, save_symptom, get_symptom_from_db, search_patient_query

app = FastAPI()


@app.get("/")
def read_root() -> dict[str, str]:
    return {}

@app.post(path="/agent/init")
async def init(request: Request) -> Dict[str, Any]:
    request_body = await request.json()
    caller_id = request_body['caller_id']
    user: User | None = get_user_from_db(phone_number=caller_id)
    
    if not user:

        new_user: User = {
            "name": "new_user",
            "phone_number": caller_id
        }
        
        # Save the new user to the database
        save_user(user=new_user)

        print("hello world")
        return {"dynamic_variables": {
            "name": "Test", 
            "phone_number": caller_id}
            
            }


    output: Dict[str, Any] = {
        "dynamic_variables": {
            "name": user['name'],
            "phone_number": user['phone_number'],
        }
    }
    print(output)
    return output

@app.post("/agent/take-symptom")
async def take_symptom(request: Request) -> dict[str, str]:
    try:
        request_body = await request.json()
        
        # Check if 'symptom' key exists in the request
        if 'symptom' not in request_body:
            return {"status": "error", "message": "Missing 'symptom' field in request"}
            
        # Validate symptom data
        symptom = request_body['symptom']
        if not symptom or not isinstance(symptom, str):
            return {"status": "error", "message": f"Invalid symptom format: {symptom}"}
        
        # Log the symptom for debugging
        print(f"Received symptom: {symptom}")
        
        # Try to save the symptom
        if save_symptom(symptom):
            return {"status": "success", "message": "Symptom saved successfully"}
        else:
            return {"status": "error", "message": "Failed to save symptom to database"}
            
    except Exception as e:
        print(f"Error in take_symptom endpoint: {str(e)}")
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


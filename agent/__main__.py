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
    request_body = await request.json()
    if save_symptom(request_body['symptom']):
        return {"status": "success"}
    else:
        return {"status": "error"}
    

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


from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import firebase_admin
from firebase_admin import credentials, auth, firestore, messaging
import google.generativeai as genai
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Helpity API", description="Backend API for Helpity platform")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firebase with environment variables
try:
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('FIREBASE_CLIENT_EMAIL').replace('@', '%40')}"
    })
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Firebase initialization error: {e}")
    raise HTTPException(status_code=500, detail="Firebase initialization failed")

# Initialize Gemini AI
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    print(f"Gemini AI initialization error: {e}")

# Pydantic models
class UserBase(BaseModel):
    email: str
    full_name: str
    role: str  # "user" or "volunteer"
    phone: Optional[str] = None

class HelpRequest(BaseModel):
    user_id: str
    task_description: str
    location: dict  # {lat: float, lng: float}
    status: str = "pending"
    scheduled_time: datetime
    emergency: bool = False

class VolunteerResponse(BaseModel):
    volunteer_id: str
    request_id: str
    status: str = "accepted"

# Routes
@app.get("/")
async def root():
    return {"message": "Welcome to Helpity API"}

@app.post("/api/users")
async def create_user(user: UserBase):
    try:
        # Create user in Firebase Auth
        user_record = auth.create_user(
            email=user.email,
            display_name=user.full_name
        )
        
        # Store additional user data in Firestore
        user_data = user.dict()
        user_data["created_at"] = firestore.SERVER_TIMESTAMP
        db.collection("users").document(user_record.uid).set(user_data)
        
        return {"message": "User created successfully", "user_id": user_record.uid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/help-requests")
async def create_help_request(request: HelpRequest):
    """Create a new help request and notify nearby volunteers.
    
    This endpoint:
    1. Uses Gemini AI to generate a friendly description
    2. Stores the request in Firestore
    3. Notifies nearby volunteers via FCM
    """
    try:
        # Generate AI description using Gemini
        # The prompt is designed to create empathetic and clear descriptions
        prompt = f"Generate a kind and encouraging description for a help request: {request.task_description}"
        try:
            ai_response = model.generate_content(prompt)
            ai_description = ai_response.text
        except Exception as ai_error:
            print(f"Gemini AI error: {ai_error}")
            # Fallback to original description if AI fails
            ai_description = request.task_description

        # Prepare and store request in Firestore
        request_data = request.dict()
        request_data["ai_description"] = ai_description
        request_data["created_at"] = firestore.SERVER_TIMESTAMP
        
        doc_ref = db.collection("help_requests").document()
        doc_ref.set(request_data)
        
        # Find nearby volunteers (MVP implementation)
        # TODO: Implement proper geolocation query using GeoFirestore
        # Current mock: Returns up to 5 volunteers regardless of location
        volunteers = db.collection("users").where("role", "==", "volunteer").limit(5).stream()
        
        # Send FCM notifications to nearby volunteers
        notification_sent = False
        for volunteer in volunteers:
            try:
                # Skip if volunteer has no FCM token
                fcm_token = volunteer.get("fcm_token", "")
                if not fcm_token:
                    continue
                    
                message = messaging.Message(
                    notification=messaging.Notification(
                        title="New Help Request Nearby",
                        body=ai_description
                    ),
                    data={
                        "request_id": doc_ref.id,
                        "type": "help_request"
                    },
                    token=fcm_token
                )
                messaging.send(message)
                notification_sent = True
            except Exception as e:
                print(f"FCM notification error for volunteer {volunteer.id}: {e}")
        
        return {
            "message": "Help request created successfully",
            "request_id": doc_ref.id,
            "notifications_sent": notification_sent
        }
    except Exception as e:
        print(f"Help request creation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/help-requests")
async def get_help_requests(role: str, user_id: str):
    try:
        if role == "volunteer":
            # Mock implementation - return all pending requests
            # In production, implement proper geolocation filtering
            requests = db.collection("help_requests").where("status", "==", "pending").stream()
        else:
            requests = db.collection("help_requests").where("user_id", "==", user_id).stream()
        
        return [{"id": req.id, **req.to_dict()} for req in requests]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/volunteer-response")
async def volunteer_response(response: VolunteerResponse):
    try:
        # Update help request status
        request_ref = db.collection("help_requests").document(response.request_id)
        request_ref.update({
            "status": response.status,
            "volunteer_id": response.volunteer_id,
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        
        # Notify the user
        request_data = request_ref.get().to_dict()
        user_ref = db.collection("users").document(request_data["user_id"])
        user_data = user_ref.get().to_dict()
        
        if "fcm_token" in user_data:
            message = messaging.Message(
                notification=messaging.Notification(
                    title="Volunteer Found!",
                    body="A volunteer has accepted your help request."
                ),
                token=user_data["fcm_token"]
            )
            messaging.send(message)
        
        return {"message": "Response recorded successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/community-wall")
async def get_community_stories():
    # Mock implementation with hardcoded stories for MVP
    return {
        "stories": [
            {
                "id": "1",
                "title": "Morning Walk Support",
                "description": "John helped Sarah with her morning walk around the park. It was a beautiful day filled with great conversation!",
                "date": "2025-04-05",
                "volunteer": "John D.",
                "points_earned": 50
            },
            {
                "title": "Doctor's Appointment Assistance",
                "description": "Maria accompanied Tom to his medical appointment, making sure he got there safely and on time.",
                "date": "2025-04-04",
                "volunteer": "Maria S.",
                "points_earned": 75
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime
from enum import Enum


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Enums
class PriorityLevel(str, Enum):
    EMERGENCY = "emergency"
    WORK = "work"
    HEALTH = "health"

class QueueStatus(str, Enum):
    WAITING = "waiting"
    USING = "using"
    COMPLETED = "completed"

class UserColor(str, Enum):
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    PURPLE = "purple"
    PINK = "pink"
    CYAN = "cyan"


# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    color: UserColor
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    name: str
    color: UserColor

class QueueItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    user_name: str
    user_color: UserColor
    priority: PriorityLevel
    status: QueueStatus
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class QueueItemCreate(BaseModel):
    user_id: str
    priority: PriorityLevel
    reason: Optional[str] = None

class HygieneRating(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rated_by_user_id: str
    rated_by_name: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class HygieneRatingCreate(BaseModel):
    rated_by_user_id: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None

class UtilityItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    last_bought_by_user_id: str
    last_bought_by_name: str
    last_bought_date: datetime
    next_buyer_user_id: Optional[str] = None
    next_buyer_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UtilityItemCreate(BaseModel):
    name: str
    last_bought_by_user_id: str
    next_buyer_user_id: Optional[str] = None

class BathroomState(BaseModel):
    is_occupied: bool = False
    current_user: Optional[Dict] = None
    last_hygiene_rating: Optional[HygieneRating] = None


# User Management Routes
@api_router.post("/users", response_model=User)
async def create_user(user_data: UserCreate):
    # Check if color is already taken
    existing_user = await db.users.find_one({"color": user_data.color})
    if existing_user:
        raise HTTPException(status_code=400, detail="Color already taken by another user")
    
    user = User(**user_data.dict())
    await db.users.insert_one(user.dict())
    return user

@api_router.get("/users", response_model=List[User])
async def get_users():
    users = await db.users.find().to_list(8)  # Max 8 users for now
    return [User(**user) for user in users]

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


# Queue Management Routes  
@api_router.post("/queue", response_model=QueueItem)
async def join_queue(queue_data: QueueItemCreate):
    # Get user info
    user = await db.users.find_one({"id": queue_data.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is already in queue
    existing_queue_item = await db.queue.find_one({
        "user_id": queue_data.user_id, 
        "status": {"$in": ["waiting", "using"]}
    })
    if existing_queue_item:
        raise HTTPException(status_code=400, detail="User already in queue")
    
    queue_item = QueueItem(
        user_id=queue_data.user_id,
        user_name=user["name"],
        user_color=user["color"],
        priority=queue_data.priority,
        status=QueueStatus.WAITING,
        reason=queue_data.reason
    )
    
    await db.queue.insert_one(queue_item.dict())
    return queue_item

@api_router.get("/queue", response_model=List[QueueItem])
async def get_queue():
    # Priority order: Emergency -> Work -> Health
    # Emergency gets highest priority (1), Work (2), Health (3)
    priority_order = {"emergency": 1, "work": 2, "health": 3}
    
    queue_items = await db.queue.find({"status": "waiting"}).to_list(100)
    
    # Sort by priority first, then by created_at
    sorted_queue = sorted(queue_items, key=lambda x: (priority_order[x["priority"]], x["created_at"]))
    
    return [QueueItem(**item) for item in sorted_queue]

@api_router.get("/queue/current", response_model=Optional[QueueItem])
async def get_current_user():
    current = await db.queue.find_one({"status": "using"})
    return QueueItem(**current) if current else None

@api_router.post("/queue/{queue_item_id}/start")
async def start_using_bathroom(queue_item_id: str):
    # Check if bathroom is already occupied
    current_user = await db.queue.find_one({"status": "using"})
    if current_user:
        raise HTTPException(status_code=400, detail="Bathroom is already occupied")
    
    # Update queue item to using status
    result = await db.queue.update_one(
        {"id": queue_item_id, "status": "waiting"},
        {
            "$set": {
                "status": "using",
                "started_at": datetime.utcnow()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Queue item not found or not in waiting status")
    
    return {"message": "Started using bathroom"}

@api_router.post("/queue/{queue_item_id}/complete")
async def complete_bathroom_use(queue_item_id: str):
    result = await db.queue.update_one(
        {"id": queue_item_id, "status": "using"},
        {
            "$set": {
                "status": "completed",
                "completed_at": datetime.utcnow()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Queue item not found or not in using status")
    
    return {"message": "Completed bathroom use"}

@api_router.delete("/queue/{queue_item_id}")
async def remove_from_queue(queue_item_id: str):
    result = await db.queue.delete_one({"id": queue_item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return {"message": "Removed from queue"}

@api_router.get("/queue/completed", response_model=List[QueueItem])
async def get_completed_queue():
    completed_items = await db.queue.find({"status": "completed"}).sort("completed_at", -1).to_list(50)
    return [QueueItem(**item) for item in completed_items]


# Emergency Alert Route
@api_router.post("/emergency-alert")
async def trigger_emergency_alert():
    # This endpoint can be called to trigger emergency notifications
    # In a real app, this would send push notifications to all users
    return {"message": "Emergency alert triggered!", "alert_type": "emergency_bathroom_needed"}


# Hygiene Rating Routes
@api_router.post("/hygiene-rating", response_model=HygieneRating)
async def create_hygiene_rating(rating_data: HygieneRatingCreate):
    user = await db.users.find_one({"id": rating_data.rated_by_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    rating = HygieneRating(
        rated_by_user_id=rating_data.rated_by_user_id,
        rated_by_name=user["name"],
        rating=rating_data.rating,
        comment=rating_data.comment
    )
    
    await db.hygiene_ratings.insert_one(rating.dict())
    return rating

@api_router.get("/hygiene-rating/latest", response_model=Optional[HygieneRating])
async def get_latest_hygiene_rating():
    latest = await db.hygiene_ratings.find().sort("created_at", -1).limit(1).to_list(1)
    return HygieneRating(**latest[0]) if latest else None

@api_router.get("/hygiene-rating", response_model=List[HygieneRating])
async def get_hygiene_ratings():
    ratings = await db.hygiene_ratings.find().sort("created_at", -1).to_list(20)
    return [HygieneRating(**rating) for rating in ratings]


# Utilities Management Routes
@api_router.post("/utilities", response_model=UtilityItem)
async def create_utility_item(utility_data: UtilityItemCreate):
    user = await db.users.find_one({"id": utility_data.last_bought_by_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    next_buyer_name = None
    if utility_data.next_buyer_user_id:
        next_buyer = await db.users.find_one({"id": utility_data.next_buyer_user_id})
        if next_buyer:
            next_buyer_name = next_buyer["name"]
    
    utility = UtilityItem(
        name=utility_data.name,
        last_bought_by_user_id=utility_data.last_bought_by_user_id,
        last_bought_by_name=user["name"],
        last_bought_date=datetime.utcnow(),
        next_buyer_user_id=utility_data.next_buyer_user_id,
        next_buyer_name=next_buyer_name
    )
    
    await db.utilities.insert_one(utility.dict())
    return utility

@api_router.get("/utilities", response_model=List[UtilityItem])
async def get_utilities():
    utilities = await db.utilities.find().sort("created_at", -1).to_list(50)
    return [UtilityItem(**utility) for utility in utilities]

@api_router.put("/utilities/{utility_id}/update-buyer")
async def update_next_buyer(utility_id: str, next_buyer_user_id: str):
    user = await db.users.find_one({"id": next_buyer_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await db.utilities.update_one(
        {"id": utility_id},
        {
            "$set": {
                "next_buyer_user_id": next_buyer_user_id,
                "next_buyer_name": user["name"]
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Utility item not found")
    
    return {"message": "Next buyer updated successfully"}


# Bathroom State Route
@api_router.get("/bathroom-state", response_model=BathroomState)
async def get_bathroom_state():
    current_user = await db.queue.find_one({"status": "using"})
    latest_rating = await db.hygiene_ratings.find().sort("created_at", -1).limit(1).to_list(1)
    
    return BathroomState(
        is_occupied=current_user is not None,
        current_user=QueueItem(**current_user).dict() if current_user else None,
        last_hygiene_rating=HygieneRating(**latest_rating[0]).dict() if latest_rating else None
    )


# Health check
@api_router.get("/")
async def root():
    return {"message": "Bathroom Queue API is running!"}


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
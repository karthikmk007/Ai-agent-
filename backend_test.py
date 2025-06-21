import requests
import unittest
import json
import time
import random
import string
from typing import Dict, List, Optional

# Get the backend URL from the frontend .env file
BACKEND_URL = "https://b725bc71-f9ef-471f-b445-b9b06a82ba7b.preview.emergentagent.com/api"

# Available colors
COLORS = ["red", "blue", "green", "yellow", "orange", "purple", "pink", "cyan"]

def random_string(length=8):
    """Generate a random string of fixed length"""
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def create_user(name=None, color=None):
    """Helper function to create a user"""
    if name is None:
        name = f"Test User {random_string()}"
    
    if color is None:
        # Find an available color
        response = requests.get(f"{BACKEND_URL}/users")
        if response.status_code == 200:
            existing_users = response.json()
            used_colors = [user["color"] for user in existing_users]
            available_colors = [c for c in COLORS if c not in used_colors]
            if available_colors:
                color = random.choice(available_colors)
            else:
                raise Exception("No available colors")
        else:
            color = random.choice(COLORS)
    
    data = {"name": name, "color": color}
    response = requests.post(f"{BACKEND_URL}/users", json=data)
    
    if response.status_code != 200:
        raise Exception(f"Failed to create user: {response.text}")
    
    return response.json()

def cleanup():
    """Clean up all created resources"""
    # Clean up queue items
    response = requests.get(f"{BACKEND_URL}/queue")
    if response.status_code == 200:
        queue_items = response.json()
        for item in queue_items:
            requests.delete(f"{BACKEND_URL}/queue/{item['id']}")
    
    # Clean up current user if any
    response = requests.get(f"{BACKEND_URL}/queue/current")
    if response.status_code == 200 and response.json():
        current_user = response.json()
        requests.post(f"{BACKEND_URL}/queue/{current_user['id']}/complete")
    
    # Clean up users
    response = requests.get(f"{BACKEND_URL}/users")
    if response.status_code == 200:
        users = response.json()
        for user in users:
            requests.delete(f"{BACKEND_URL}/users/{user['id']}")

def test_user_management():
    """Test user management API endpoints"""
    print("\n--- Testing User Management API ---")
    
    # Get existing users to avoid color conflicts
    response = requests.get(f"{BACKEND_URL}/users")
    existing_users = response.json() if response.status_code == 200 else []
    used_colors = [user["color"] for user in existing_users]
    
    # Find an available color for our first test user
    available_colors = [c for c in COLORS if c not in used_colors]
    if not available_colors:
        raise Exception("No available colors for testing")
    
    test_color = available_colors[0]
    
    # Test creating a user
    user = create_user(name="John Doe", color=test_color)
    assert user["name"] == "John Doe"
    assert user["color"] == test_color
    
    # Test getting all users
    response = requests.get(f"{BACKEND_URL}/users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 1
    
    # Test color uniqueness validation
    data = {"name": "Jane Doe", "color": test_color}
    response = requests.post(f"{BACKEND_URL}/users", json=data)
    assert response.status_code == 400
    assert "Color already taken" in response.json()["detail"]
    
    # Find another available color
    used_colors.append(test_color)
    available_colors = [c for c in COLORS if c not in used_colors]
    if not available_colors:
        raise Exception("No more available colors for testing")
    
    test_color2 = available_colors[0]
    
    # Test creating a user with a different color
    user2 = create_user(name="Jane Doe", color=test_color2)
    assert user2["name"] == "Jane Doe"
    assert user2["color"] == test_color2
    
    # Test deleting a user
    response = requests.delete(f"{BACKEND_URL}/users/{user['id']}")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]
    
    # Test deleting a non-existent user
    response = requests.delete(f"{BACKEND_URL}/users/non-existent-id")
    assert response.status_code == 404
    
    print("✅ User Management API tests passed")

def test_priority_queue_system():
    """Test priority queue system API endpoints"""
    print("\n--- Testing Priority Queue System API ---")
    
    # Get existing users to avoid color conflicts
    response = requests.get(f"{BACKEND_URL}/users")
    existing_users = response.json() if response.status_code == 200 else []
    used_colors = [user["color"] for user in existing_users]
    
    # Find available colors
    available_colors = [c for c in COLORS if c not in used_colors]
    if len(available_colors) < 3:
        raise Exception("Not enough available colors for testing")
    
    # Create test users with unique colors
    user1 = create_user(name="User 1", color=available_colors[0])
    user2 = create_user(name="User 2", color=available_colors[1])
    user3 = create_user(name="User 3", color=available_colors[2])
    
    # Test joining queue with different priorities
    # Health (lowest priority)
    health_data = {"user_id": user1["id"], "priority": "health", "reason": "Regular break"}
    response = requests.post(f"{BACKEND_URL}/queue", json=health_data)
    assert response.status_code == 200
    health_queue_item = response.json()
    
    # Work (medium priority)
    work_data = {"user_id": user2["id"], "priority": "work", "reason": "Quick break"}
    response = requests.post(f"{BACKEND_URL}/queue", json=work_data)
    assert response.status_code == 200
    work_queue_item = response.json()
    
    # Emergency (highest priority)
    emergency_data = {"user_id": user3["id"], "priority": "emergency", "reason": "Emergency!"}
    response = requests.post(f"{BACKEND_URL}/queue", json=emergency_data)
    assert response.status_code == 200
    emergency_queue_item = response.json()
    
    # Test getting queue (should be sorted by priority)
    response = requests.get(f"{BACKEND_URL}/queue")
    assert response.status_code == 200
    queue = response.json()
    
    # Filter only our test users from the queue
    test_user_ids = [user1["id"], user2["id"], user3["id"]]
    our_queue_items = [item for item in queue if item["user_id"] in test_user_ids]
    assert len(our_queue_items) == 3
    
    # Verify queue order: Emergency > Work > Health
    # Find our items in the queue
    emergency_item = next((item for item in our_queue_items if item["priority"] == "emergency"), None)
    work_item = next((item for item in our_queue_items if item["priority"] == "work"), None)
    health_item = next((item for item in our_queue_items if item["priority"] == "health"), None)
    
    assert emergency_item is not None
    assert work_item is not None
    assert health_item is not None
    
    # Get the indices of our items in the queue
    emergency_index = queue.index(emergency_item)
    work_index = queue.index(work_item)
    health_index = queue.index(health_item)
    
    # Verify priority order
    assert emergency_index < work_index
    assert work_index < health_index
    
    # Test starting bathroom use (emergency should go first)
    response = requests.post(f"{BACKEND_URL}/queue/{emergency_item['id']}/start")
    assert response.status_code == 200
    
    # Test getting current user
    response = requests.get(f"{BACKEND_URL}/queue/current")
    assert response.status_code == 200
    current_user = response.json()
    assert current_user["user_id"] == user3["id"]
    assert current_user["status"] == "using"
    
    # Test that another user can't start using bathroom while it's occupied
    response = requests.post(f"{BACKEND_URL}/queue/{work_item['id']}/start")
    assert response.status_code == 400
    assert "already occupied" in response.json()["detail"]
    
    # Test completing bathroom use
    response = requests.post(f"{BACKEND_URL}/queue/{current_user['id']}/complete")
    assert response.status_code == 200
    
    # Test getting completed queue
    response = requests.get(f"{BACKEND_URL}/queue/completed")
    assert response.status_code == 200
    completed_queue = response.json()
    
    # Find our completed item
    our_completed_item = next((item for item in completed_queue if item["user_id"] == user3["id"]), None)
    assert our_completed_item is not None
    
    # Test removing from queue
    response = requests.delete(f"{BACKEND_URL}/queue/{work_item['id']}")
    assert response.status_code == 200
    
    # Verify our item was removed
    response = requests.get(f"{BACKEND_URL}/queue")
    assert response.status_code == 200
    queue = response.json()
    work_item_still_exists = any(item["id"] == work_item["id"] for item in queue)
    assert not work_item_still_exists
    
    print("✅ Priority Queue System API tests passed")

def test_bathroom_state_management():
    """Test bathroom state management API endpoints"""
    print("\n--- Testing Bathroom State Management API ---")
    
    # Create a test user
    user = create_user()
    
    # Test initial bathroom state (should be unoccupied)
    response = requests.get(f"{BACKEND_URL}/bathroom-state")
    assert response.status_code == 200
    state = response.json()
    
    # If bathroom is occupied, complete the current session
    if state["is_occupied"] and state["current_user"]:
        requests.post(f"{BACKEND_URL}/queue/{state['current_user']['id']}/complete")
        
        # Check again
        response = requests.get(f"{BACKEND_URL}/bathroom-state")
        assert response.status_code == 200
        state = response.json()
        assert not state["is_occupied"]
    
    # Join queue
    queue_data = {"user_id": user["id"], "priority": "work"}
    response = requests.post(f"{BACKEND_URL}/queue", json=queue_data)
    assert response.status_code == 200
    queue_item = response.json()
    
    # Start using bathroom
    response = requests.post(f"{BACKEND_URL}/queue/{queue_item['id']}/start")
    assert response.status_code == 200
    
    # Test bathroom state (should be occupied)
    response = requests.get(f"{BACKEND_URL}/bathroom-state")
    assert response.status_code == 200
    state = response.json()
    assert state["is_occupied"]
    assert state["current_user"] is not None
    assert state["current_user"]["user_id"] == user["id"]
    
    # Complete bathroom use
    response = requests.post(f"{BACKEND_URL}/queue/{queue_item['id']}/complete")
    assert response.status_code == 200
    
    # Test bathroom state (should be unoccupied again)
    response = requests.get(f"{BACKEND_URL}/bathroom-state")
    assert response.status_code == 200
    state = response.json()
    assert not state["is_occupied"]
    assert state["current_user"] is None
    
    print("✅ Bathroom State Management API tests passed")

def test_emergency_alert_system():
    """Test emergency alert system API endpoint"""
    print("\n--- Testing Emergency Alert System API ---")
    
    # Test triggering emergency alert
    response = requests.post(f"{BACKEND_URL}/emergency-alert")
    assert response.status_code == 200
    alert = response.json()
    assert "Emergency alert triggered" in alert["message"]
    assert alert["alert_type"] == "emergency_bathroom_needed"
    
    print("✅ Emergency Alert System API tests passed")

def test_hygiene_rating_system():
    """Test hygiene rating system API endpoints"""
    print("\n--- Testing Hygiene Rating System API ---")
    
    # Create a test user
    user = create_user()
    
    # Test submitting a hygiene rating
    rating_data = {
        "rated_by_user_id": user["id"],
        "rating": 4,
        "comment": "Pretty clean, good job!"
    }
    response = requests.post(f"{BACKEND_URL}/hygiene-rating", json=rating_data)
    assert response.status_code == 200
    rating = response.json()
    assert rating["rated_by_user_id"] == user["id"]
    assert rating["rating"] == 4
    assert rating["comment"] == "Pretty clean, good job!"
    
    # Test getting latest rating
    response = requests.get(f"{BACKEND_URL}/hygiene-rating/latest")
    assert response.status_code == 200
    latest_rating = response.json()
    assert latest_rating["rated_by_user_id"] == user["id"]
    assert latest_rating["rating"] == 4
    
    # Test submitting an invalid rating (outside 1-5 range)
    invalid_rating_data = {
        "rated_by_user_id": user["id"],
        "rating": 6,
        "comment": "Too high rating"
    }
    response = requests.post(f"{BACKEND_URL}/hygiene-rating", json=invalid_rating_data)
    assert response.status_code == 422  # Validation error
    
    # Test getting all ratings
    response = requests.get(f"{BACKEND_URL}/hygiene-rating")
    assert response.status_code == 200
    ratings = response.json()
    assert len(ratings) >= 1
    
    print("✅ Hygiene Rating System API tests passed")

def test_utilities_tracking():
    """Test utilities tracking API endpoints"""
    print("\n--- Testing Utilities Tracking API ---")
    
    # Create test users
    user1 = create_user(name="Buyer")
    user2 = create_user(name="Next Buyer")
    
    # Test adding a utility item
    utility_data = {
        "name": "Toilet Paper",
        "last_bought_by_user_id": user1["id"],
        "next_buyer_user_id": user2["id"]
    }
    response = requests.post(f"{BACKEND_URL}/utilities", json=utility_data)
    assert response.status_code == 200
    utility = response.json()
    assert utility["name"] == "Toilet Paper"
    assert utility["last_bought_by_user_id"] == user1["id"]
    assert utility["last_bought_by_name"] == "Buyer"
    assert utility["next_buyer_user_id"] == user2["id"]
    assert utility["next_buyer_name"] == "Next Buyer"
    
    # Test getting all utilities
    response = requests.get(f"{BACKEND_URL}/utilities")
    assert response.status_code == 200
    utilities = response.json()
    assert len(utilities) >= 1
    
    # Test updating next buyer
    response = requests.put(f"{BACKEND_URL}/utilities/{utility['id']}/update-buyer?next_buyer_user_id={user1['id']}")
    assert response.status_code == 200
    
    # Verify next buyer was updated
    response = requests.get(f"{BACKEND_URL}/utilities")
    assert response.status_code == 200
    utilities = response.json()
    updated_utility = next((u for u in utilities if u["id"] == utility["id"]), None)
    assert updated_utility is not None
    assert updated_utility["next_buyer_user_id"] == user1["id"]
    assert updated_utility["next_buyer_name"] == "Buyer"
    
    print("✅ Utilities Tracking API tests passed")

def test_validation_rules():
    """Test various validation rules and error cases"""
    print("\n--- Testing Validation Rules ---")
    
    # Create a test user
    user = create_user()
    
    # Test joining queue with invalid priority
    invalid_priority_data = {"user_id": user["id"], "priority": "invalid_priority"}
    response = requests.post(f"{BACKEND_URL}/queue", json=invalid_priority_data)
    assert response.status_code == 422  # Validation error
    
    # Test joining queue with non-existent user
    non_existent_user_data = {"user_id": "non-existent-id", "priority": "work"}
    response = requests.post(f"{BACKEND_URL}/queue", json=non_existent_user_data)
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]
    
    # Test starting bathroom use for non-existent queue item
    response = requests.post(f"{BACKEND_URL}/queue/non-existent-id/start")
    assert response.status_code == 404
    
    # Test completing bathroom use for non-existent queue item
    response = requests.post(f"{BACKEND_URL}/queue/non-existent-id/complete")
    assert response.status_code == 404
    
    # Test removing non-existent queue item
    response = requests.delete(f"{BACKEND_URL}/queue/non-existent-id")
    assert response.status_code == 404
    
    print("✅ Validation Rules tests passed")

def run_all_tests():
    """Run all test functions"""
    print("\n=== Running All Bathroom Queue API Tests ===\n")
    
    try:
        # Clean up before tests
        cleanup()
        
        # Run all tests
        test_user_management()
        test_priority_queue_system()
        test_bathroom_state_management()
        test_emergency_alert_system()
        test_hygiene_rating_system()
        test_utilities_tracking()
        test_validation_rules()
        
        print("\n=== All Tests Completed Successfully ===")
    finally:
        # Clean up after tests
        cleanup()

if __name__ == "__main__":
    run_all_tests()
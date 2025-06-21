import requests
import unittest
import json
import time
import random
import string
from typing import Dict, List, Optional

# Get the backend URL from the frontend .env file
BACKEND_URL = "https://b725bc71-f9ef-471f-b445-b9b06a82ba7b.preview.emergentagent.com/api"

class BathroomQueueAPITest(unittest.TestCase):
    """Test suite for the Bathroom Queue API"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        # Initialize lists to store created resources
        self.users = []  # Store created users for cleanup
        self.queue_items = []  # Store created queue items for cleanup
        self.utility_items = []  # Store created utility items for cleanup
        self.colors = ["red", "blue", "green", "yellow", "orange", "purple", "pink", "cyan"]
        
        # Clean up any existing data
        self.cleanup()

    def tearDown(self):
        """Clean up after each test method"""
        self.cleanup()

    def cleanup(self):
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
                
        # Reset instance variables
        self.users = []
        self.queue_items = []
        self.utility_items = []

    def random_string(self, length=8):
        """Generate a random string of fixed length"""
        return ''.join(random.choices(string.ascii_lowercase, k=length))

    def create_user(self, name=None, color=None) -> Dict:
        """Helper method to create a user"""
        if name is None:
            name = f"Test User {self.random_string()}"
        
        if color is None:
            # Find an available color
            response = requests.get(f"{BACKEND_URL}/users")
            if response.status_code == 200:
                existing_users = response.json()
                used_colors = [user["color"] for user in existing_users]
                available_colors = [c for c in self.colors if c not in used_colors]
                if available_colors:
                    color = random.choice(available_colors)
                else:
                    self.fail("No available colors")
            else:
                color = random.choice(self.colors)
        
        data = {"name": name, "color": color}
        response = requests.post(f"{BACKEND_URL}/users", json=data)
        self.assertEqual(response.status_code, 200, f"Failed to create user: {response.text}")
        
        user = response.json()
        self.users.append(user)
        return user

    def test_user_management(self):
        """Test user management API endpoints"""
        print("\n--- Testing User Management API ---")
        
        # Get existing users to avoid color conflicts
        response = requests.get(f"{BACKEND_URL}/users")
        existing_users = response.json() if response.status_code == 200 else []
        used_colors = [user["color"] for user in existing_users]
        
        # Find an available color for our first test user
        available_colors = [c for c in self.colors if c not in used_colors]
        if not available_colors:
            self.fail("No available colors for testing")
        
        test_color = available_colors[0]
        
        # Test creating a user
        user = self.create_user(name="John Doe", color=test_color)
        self.assertEqual(user["name"], "John Doe")
        self.assertEqual(user["color"], test_color)
        
        # Test getting all users
        response = requests.get(f"{BACKEND_URL}/users")
        self.assertEqual(response.status_code, 200)
        users = response.json()
        self.assertGreaterEqual(len(users), 1)
        
        # Test color uniqueness validation
        data = {"name": "Jane Doe", "color": test_color}
        response = requests.post(f"{BACKEND_URL}/users", json=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Color already taken", response.json()["detail"])
        
        # Find another available color
        used_colors.append(test_color)
        available_colors = [c for c in self.colors if c not in used_colors]
        if not available_colors:
            self.fail("No more available colors for testing")
        
        test_color2 = available_colors[0]
        
        # Test creating a user with a different color
        user2 = self.create_user(name="Jane Doe", color=test_color2)
        self.assertEqual(user2["name"], "Jane Doe")
        self.assertEqual(user2["color"], test_color2)
        
        # Test deleting a user
        response = requests.delete(f"{BACKEND_URL}/users/{user['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("deleted successfully", response.json()["message"])
        
        # Test deleting a non-existent user
        response = requests.delete(f"{BACKEND_URL}/users/non-existent-id")
        self.assertEqual(response.status_code, 404)
        
        print("✅ User Management API tests passed")

    def test_priority_queue_system(self):
        """Test priority queue system API endpoints"""
        print("\n--- Testing Priority Queue System API ---")
        
        # Create test users
        user1 = self.create_user(name="User 1", color="red")
        user2 = self.create_user(name="User 2", color="blue")
        user3 = self.create_user(name="User 3", color="green")
        
        # Test joining queue with different priorities
        # Health (lowest priority)
        health_data = {"user_id": user1["id"], "priority": "health", "reason": "Regular break"}
        response = requests.post(f"{BACKEND_URL}/queue", json=health_data)
        self.assertEqual(response.status_code, 200)
        health_queue_item = response.json()
        self.queue_items.append(health_queue_item)
        
        # Work (medium priority)
        work_data = {"user_id": user2["id"], "priority": "work", "reason": "Quick break"}
        response = requests.post(f"{BACKEND_URL}/queue", json=work_data)
        self.assertEqual(response.status_code, 200)
        work_queue_item = response.json()
        self.queue_items.append(work_queue_item)
        
        # Emergency (highest priority)
        emergency_data = {"user_id": user3["id"], "priority": "emergency", "reason": "Emergency!"}
        response = requests.post(f"{BACKEND_URL}/queue", json=emergency_data)
        self.assertEqual(response.status_code, 200)
        emergency_queue_item = response.json()
        self.queue_items.append(emergency_queue_item)
        
        # Test getting queue (should be sorted by priority)
        response = requests.get(f"{BACKEND_URL}/queue")
        self.assertEqual(response.status_code, 200)
        queue = response.json()
        self.assertEqual(len(queue), 3)
        
        # Verify queue order: Emergency > Work > Health
        self.assertEqual(queue[0]["priority"], "emergency")
        self.assertEqual(queue[1]["priority"], "work")
        self.assertEqual(queue[2]["priority"], "health")
        
        # Test starting bathroom use (emergency should go first)
        response = requests.post(f"{BACKEND_URL}/queue/{queue[0]['id']}/start")
        self.assertEqual(response.status_code, 200)
        
        # Test getting current user
        response = requests.get(f"{BACKEND_URL}/queue/current")
        self.assertEqual(response.status_code, 200)
        current_user = response.json()
        self.assertEqual(current_user["user_id"], user3["id"])
        self.assertEqual(current_user["status"], "using")
        
        # Test that another user can't start using bathroom while it's occupied
        response = requests.post(f"{BACKEND_URL}/queue/{queue[1]['id']}/start")
        self.assertEqual(response.status_code, 400)
        self.assertIn("already occupied", response.json()["detail"])
        
        # Test completing bathroom use
        response = requests.post(f"{BACKEND_URL}/queue/{current_user['id']}/complete")
        self.assertEqual(response.status_code, 200)
        
        # Test getting completed queue
        response = requests.get(f"{BACKEND_URL}/queue/completed")
        self.assertEqual(response.status_code, 200)
        completed_queue = response.json()
        self.assertEqual(len(completed_queue), 1)
        self.assertEqual(completed_queue[0]["user_id"], user3["id"])
        
        # Test removing from queue
        response = requests.delete(f"{BACKEND_URL}/queue/{queue[1]['id']}")
        self.assertEqual(response.status_code, 200)
        
        # Verify queue length after removal
        response = requests.get(f"{BACKEND_URL}/queue")
        self.assertEqual(response.status_code, 200)
        queue = response.json()
        self.assertEqual(len(queue), 1)  # Only health priority user should remain
        
        print("✅ Priority Queue System API tests passed")

    def test_bathroom_state_management(self):
        """Test bathroom state management API endpoints"""
        print("\n--- Testing Bathroom State Management API ---")
        
        # Create a test user
        user = self.create_user()
        
        # Test initial bathroom state (should be unoccupied)
        response = requests.get(f"{BACKEND_URL}/bathroom-state")
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertFalse(state["is_occupied"])
        self.assertIsNone(state["current_user"])
        
        # Join queue
        queue_data = {"user_id": user["id"], "priority": "work"}
        response = requests.post(f"{BACKEND_URL}/queue", json=queue_data)
        self.assertEqual(response.status_code, 200)
        queue_item = response.json()
        
        # Start using bathroom
        response = requests.post(f"{BACKEND_URL}/queue/{queue_item['id']}/start")
        self.assertEqual(response.status_code, 200)
        
        # Test bathroom state (should be occupied)
        response = requests.get(f"{BACKEND_URL}/bathroom-state")
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertTrue(state["is_occupied"])
        self.assertIsNotNone(state["current_user"])
        self.assertEqual(state["current_user"]["user_id"], user["id"])
        
        # Complete bathroom use
        response = requests.post(f"{BACKEND_URL}/queue/{queue_item['id']}/complete")
        self.assertEqual(response.status_code, 200)
        
        # Test bathroom state (should be unoccupied again)
        response = requests.get(f"{BACKEND_URL}/bathroom-state")
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertFalse(state["is_occupied"])
        self.assertIsNone(state["current_user"])
        
        print("✅ Bathroom State Management API tests passed")

    def test_emergency_alert_system(self):
        """Test emergency alert system API endpoint"""
        print("\n--- Testing Emergency Alert System API ---")
        
        # Test triggering emergency alert
        response = requests.post(f"{BACKEND_URL}/emergency-alert")
        self.assertEqual(response.status_code, 200)
        alert = response.json()
        self.assertIn("Emergency alert triggered", alert["message"])
        self.assertEqual(alert["alert_type"], "emergency_bathroom_needed")
        
        print("✅ Emergency Alert System API tests passed")

    def test_hygiene_rating_system(self):
        """Test hygiene rating system API endpoints"""
        print("\n--- Testing Hygiene Rating System API ---")
        
        # Create a test user
        user = self.create_user()
        
        # Test submitting a hygiene rating
        rating_data = {
            "rated_by_user_id": user["id"],
            "rating": 4,
            "comment": "Pretty clean, good job!"
        }
        response = requests.post(f"{BACKEND_URL}/hygiene-rating", json=rating_data)
        self.assertEqual(response.status_code, 200)
        rating = response.json()
        self.assertEqual(rating["rated_by_user_id"], user["id"])
        self.assertEqual(rating["rating"], 4)
        self.assertEqual(rating["comment"], "Pretty clean, good job!")
        
        # Test getting latest rating
        response = requests.get(f"{BACKEND_URL}/hygiene-rating/latest")
        self.assertEqual(response.status_code, 200)
        latest_rating = response.json()
        self.assertEqual(latest_rating["rated_by_user_id"], user["id"])
        self.assertEqual(latest_rating["rating"], 4)
        
        # Test submitting an invalid rating (outside 1-5 range)
        invalid_rating_data = {
            "rated_by_user_id": user["id"],
            "rating": 6,
            "comment": "Too high rating"
        }
        response = requests.post(f"{BACKEND_URL}/hygiene-rating", json=invalid_rating_data)
        self.assertEqual(response.status_code, 422)  # Validation error
        
        # Test getting all ratings
        response = requests.get(f"{BACKEND_URL}/hygiene-rating")
        self.assertEqual(response.status_code, 200)
        ratings = response.json()
        self.assertEqual(len(ratings), 1)
        
        print("✅ Hygiene Rating System API tests passed")

    def test_utilities_tracking(self):
        """Test utilities tracking API endpoints"""
        print("\n--- Testing Utilities Tracking API ---")
        
        # Create test users
        user1 = self.create_user(name="Buyer", color="red")
        user2 = self.create_user(name="Next Buyer", color="blue")
        
        # Test adding a utility item
        utility_data = {
            "name": "Toilet Paper",
            "last_bought_by_user_id": user1["id"],
            "next_buyer_user_id": user2["id"]
        }
        response = requests.post(f"{BACKEND_URL}/utilities", json=utility_data)
        self.assertEqual(response.status_code, 200)
        utility = response.json()
        self.utility_items.append(utility)
        self.assertEqual(utility["name"], "Toilet Paper")
        self.assertEqual(utility["last_bought_by_user_id"], user1["id"])
        self.assertEqual(utility["last_bought_by_name"], "Buyer")
        self.assertEqual(utility["next_buyer_user_id"], user2["id"])
        self.assertEqual(utility["next_buyer_name"], "Next Buyer")
        
        # Test getting all utilities
        response = requests.get(f"{BACKEND_URL}/utilities")
        self.assertEqual(response.status_code, 200)
        utilities = response.json()
        self.assertEqual(len(utilities), 1)
        
        # Test updating next buyer
        response = requests.put(f"{BACKEND_URL}/utilities/{utility['id']}/update-buyer?next_buyer_user_id={user1['id']}")
        self.assertEqual(response.status_code, 200)
        
        # Verify next buyer was updated
        response = requests.get(f"{BACKEND_URL}/utilities")
        self.assertEqual(response.status_code, 200)
        utilities = response.json()
        self.assertEqual(utilities[0]["next_buyer_user_id"], user1["id"])
        self.assertEqual(utilities[0]["next_buyer_name"], "Buyer")
        
        print("✅ Utilities Tracking API tests passed")

    def test_validation_rules(self):
        """Test various validation rules and error cases"""
        print("\n--- Testing Validation Rules ---")
        
        # Create a test user
        user = self.create_user()
        
        # Test joining queue with invalid priority
        invalid_priority_data = {"user_id": user["id"], "priority": "invalid_priority"}
        response = requests.post(f"{BACKEND_URL}/queue", json=invalid_priority_data)
        self.assertEqual(response.status_code, 422)  # Validation error
        
        # Test joining queue with non-existent user
        non_existent_user_data = {"user_id": "non-existent-id", "priority": "work"}
        response = requests.post(f"{BACKEND_URL}/queue", json=non_existent_user_data)
        self.assertEqual(response.status_code, 404)
        self.assertIn("User not found", response.json()["detail"])
        
        # Test starting bathroom use for non-existent queue item
        response = requests.post(f"{BACKEND_URL}/queue/non-existent-id/start")
        self.assertEqual(response.status_code, 404)
        
        # Test completing bathroom use for non-existent queue item
        response = requests.post(f"{BACKEND_URL}/queue/non-existent-id/complete")
        self.assertEqual(response.status_code, 404)
        
        # Test removing non-existent queue item
        response = requests.delete(f"{BACKEND_URL}/queue/non-existent-id")
        self.assertEqual(response.status_code, 404)
        
        print("✅ Validation Rules tests passed")

    def run_all_tests(self):
        """Run all test methods"""
        print("\n=== Running All Bathroom Queue API Tests ===\n")
        
        self.test_user_management()
        self.test_priority_queue_system()
        self.test_bathroom_state_management()
        self.test_emergency_alert_system()
        self.test_hygiene_rating_system()
        self.test_utilities_tracking()
        self.test_validation_rules()
        
        print("\n=== All Tests Completed Successfully ===")


if __name__ == "__main__":
    test_suite = BathroomQueueAPITest()
    test_suite.run_all_tests()
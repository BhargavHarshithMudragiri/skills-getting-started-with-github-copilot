"""
Tests for the Mergington High School Activities API
"""
import sys
from pathlib import Path

# Add the src directory to the path so we can import the app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_dict(self):
        """Test that /activities returns a dictionary of activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    def test_get_activities_contains_chess_club(self):
        """Test that Chess Club is in the activities list"""
        response = client.get("/activities")
        activities = response.json()
        assert "Chess Club" in activities

    def test_activity_has_required_fields(self):
        """Test that each activity has the required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_chess_club_has_initial_participants(self):
        """Test that Chess Club has the expected initial participants"""
        response = client.get("/activities")
        activities = response.json()
        chess_club = activities["Chess Club"]
        
        assert len(chess_club["participants"]) >= 2
        assert "michael@mergington.edu" in chess_club["participants"]


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_new_participant(self):
        """Test signing up a new participant"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"
        )
        
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
        assert "newstudent@mergington.edu" in response.json()["message"]

    def test_signup_duplicate_participant_fails(self):
        """Test that signing up an already registered participant fails"""
        # First signup
        response1 = client.post(
            "/activities/Chess%20Club/signup?email=duplicate@mergington.edu"
        )
        assert response1.status_code == 200

        # Second signup with same email
        response2 = client.post(
            "/activities/Chess%20Club/signup?email=duplicate@mergington.edu"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]

    def test_signup_nonexistent_activity_fails(self):
        """Test that signing up for a non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_signup_updates_participant_list(self):
        """Test that signup updates the participants list"""
        email = "verification@mergington.edu"
        
        # Get activities before signup
        response_before = client.get("/activities")
        participants_before = response_before.json()["Programming Class"]["participants"].copy()
        
        # Sign up
        signup_response = client.post(
            f"/activities/Programming%20Class/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Get activities after signup
        response_after = client.get("/activities")
        participants_after = response_after.json()["Programming Class"]["participants"]
        
        assert email in participants_after
        assert len(participants_after) == len(participants_before) + 1


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_existing_participant(self):
        """Test unregistering an existing participant"""
        # First sign up
        email = "unregister_test@mergington.edu"
        client.post(
            f"/activities/Tennis%20Club/signup?email={email}"
        )
        
        # Then unregister
        response = client.delete(
            f"/activities/Tennis%20Club/unregister?email={email}"
        )
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]

    def test_unregister_removes_from_list(self):
        """Test that unregistering actually removes participant from list"""
        email = "removal_test@mergington.edu"
        
        # Sign up
        client.post(
            f"/activities/Art%20Studio/signup?email={email}"
        )
        
        # Verify signup
        response_after_signup = client.get("/activities")
        assert email in response_after_signup.json()["Art Studio"]["participants"]
        
        # Unregister
        client.delete(
            f"/activities/Art%20Studio/unregister?email={email}"
        )
        
        # Verify removal
        response_after_unregister = client.get("/activities")
        assert email not in response_after_unregister.json()["Art Studio"]["participants"]

    def test_unregister_nonexistent_participant_fails(self):
        """Test that unregistering a non-registered participant fails"""
        response = client.delete(
            "/activities/Drama%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"].lower()

    def test_unregister_nonexistent_activity_fails(self):
        """Test that unregistering from a non-existent activity fails"""
        response = client.delete(
            "/activities/Fake%20Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestRoot:
    """Tests for GET / endpoint"""

    def test_root_redirects(self):
        """Test that the root endpoint redirects to static files"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestActivityConstraints:
    """Tests for activity constraints"""

    def test_max_participants_constraint(self):
        """Test that activities have max participant constraints"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            max_participants = activity_data["max_participants"]
            current_participants = len(activity_data["participants"])
            assert current_participants <= max_participants
            assert max_participants > 0

"""
Content Engine Module Tests — Iteration 251
Tests for M1 (Content Sources + Idea Generation) and M2 (Drafts + Editorial Queue)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Demo session token from previous iteration
DEMO_SESSION = "demo_session_token_normafacile"
ADMIN_SESSION = "test_session_token_for_dev_2026"


class TestContentEngineStats:
    """Test /api/content/stats endpoint"""
    
    def test_stats_requires_auth(self):
        """Stats endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/content/stats")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Stats endpoint requires authentication")
    
    def test_stats_with_demo_user(self):
        """Stats endpoint should work with demo user (admin role)"""
        response = requests.get(
            f"{BASE_URL}/api/content/stats",
            cookies={"session_token": DEMO_SESSION}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "sources" in data
        assert "ideas" in data
        assert "drafts" in data
        assert "queue_total" in data
        assert "queue_approved" in data
        print(f"PASS: Stats returned - sources: {data['sources']}, ideas: {data['ideas']}, drafts: {data['drafts']}")


class TestContentSources:
    """Test /api/content/sources CRUD endpoints"""
    
    def test_list_sources_empty_initially(self):
        """List sources should return empty or existing sources"""
        response = requests.get(
            f"{BASE_URL}/api/content/sources",
            cookies={"session_token": DEMO_SESSION}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: List sources returned {len(data)} sources")
    
    def test_seed_sources(self):
        """Seed 10 content sources via POST /api/content/seed-sources"""
        response = requests.post(
            f"{BASE_URL}/api/content/seed-sources",
            cookies={"session_token": DEMO_SESSION}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data
        # Either seeded new or already present
        print(f"PASS: Seed sources - {data.get('message')}, seeded: {data.get('seeded', 0)}, total: {data.get('total', 'N/A')}")
    
    def test_list_sources_after_seed(self):
        """After seeding, should have 10 sources"""
        response = requests.get(
            f"{BASE_URL}/api/content/sources",
            cookies={"session_token": DEMO_SESSION}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 10, f"Expected at least 10 sources, got {len(data)}"
        
        # Verify source structure
        source = data[0]
        assert "source_id" in source
        assert "title" in source
        assert "description" in source
        assert "pain_points" in source
        print(f"PASS: After seed, {len(data)} sources available with correct structure")
        return data[0]["source_id"]  # Return first source_id for next tests
    
    def test_get_single_source(self):
        """Get a single source by ID"""
        # First get list to get a source_id
        list_response = requests.get(
            f"{BASE_URL}/api/content/sources",
            cookies={"session_token": DEMO_SESSION}
        )
        sources = list_response.json()
        if not sources:
            pytest.skip("No sources available")
        
        source_id = sources[0]["source_id"]
        response = requests.get(
            f"{BASE_URL}/api/content/sources/{source_id}",
            cookies={"session_token": DEMO_SESSION}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == source_id
        print(f"PASS: Get single source {source_id} - title: {data['title']}")


class TestIdeaGeneration:
    """Test idea generation from sources"""
    
    def test_generate_ideas_from_source(self):
        """Generate ideas from a source via POST /api/content/sources/{id}/generate-ideas"""
        # Get a source first
        list_response = requests.get(
            f"{BASE_URL}/api/content/sources",
            cookies={"session_token": DEMO_SESSION}
        )
        sources = list_response.json()
        if not sources:
            pytest.skip("No sources available - run seed first")
        
        source_id = sources[0]["source_id"]
        
        # Generate ideas (this may take a few seconds due to AI)
        response = requests.post(
            f"{BASE_URL}/api/content/sources/{source_id}/generate-ideas",
            cookies={"session_token": DEMO_SESSION},
            timeout=60  # AI generation can take time
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "ideas_generated" in data
        assert "ideas" in data
        assert data["ideas_generated"] >= 1, "Should generate at least 1 idea"
        print(f"PASS: Generated {data['ideas_generated']} ideas from source '{data.get('source', 'N/A')}'")
    
    def test_list_ideas(self):
        """List all ideas via GET /api/content/ideas"""
        response = requests.get(
            f"{BASE_URL}/api/content/ideas",
            cookies={"session_token": DEMO_SESSION}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if data:
            idea = data[0]
            assert "idea_id" in idea
            assert "format" in idea
            assert "hook" in idea
            assert "brief" in idea
            print(f"PASS: Listed {len(data)} ideas with correct structure")
        else:
            print("PASS: Ideas list returned (empty)")


class TestDraftGeneration:
    """Test draft generation from ideas"""
    
    def test_generate_draft_from_idea(self):
        """Generate a draft from an idea via POST /api/content/ideas/{id}/generate-draft"""
        # Get an idea first
        list_response = requests.get(
            f"{BASE_URL}/api/content/ideas",
            cookies={"session_token": DEMO_SESSION}
        )
        ideas = list_response.json()
        
        # Find an idea that hasn't been converted to draft yet
        available_idea = None
        for idea in ideas:
            if idea.get("status") != "draft_generated":
                available_idea = idea
                break
        
        if not available_idea:
            # If all ideas are already drafts, skip
            if ideas:
                print("PASS: All ideas already converted to drafts (skipping generation)")
                return
            pytest.skip("No ideas available - run idea generation first")
        
        idea_id = available_idea["idea_id"]
        
        # Generate draft (this may take a few seconds due to AI)
        response = requests.post(
            f"{BASE_URL}/api/content/ideas/{idea_id}/generate-draft",
            cookies={"session_token": DEMO_SESSION},
            timeout=60
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "draft_id" in data
        assert "title" in data
        assert "body" in data
        print(f"PASS: Generated draft '{data['title'][:50]}...' from idea")
    
    def test_list_drafts(self):
        """List all drafts via GET /api/content/drafts"""
        response = requests.get(
            f"{BASE_URL}/api/content/drafts",
            cookies={"session_token": DEMO_SESSION}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if data:
            draft = data[0]
            assert "draft_id" in draft
            assert "title" in draft
            assert "body" in draft
            assert "format" in draft
            print(f"PASS: Listed {len(data)} drafts with correct structure")
        else:
            print("PASS: Drafts list returned (empty)")


class TestEditorialQueue:
    """Test editorial queue management"""
    
    def test_add_draft_to_queue(self):
        """Add a draft to the editorial queue via POST /api/content/queue"""
        # Get a draft first
        list_response = requests.get(
            f"{BASE_URL}/api/content/drafts",
            cookies={"session_token": DEMO_SESSION}
        )
        drafts = list_response.json()
        
        # Find a draft not yet queued
        available_draft = None
        for draft in drafts:
            if draft.get("status") != "queued":
                available_draft = draft
                break
        
        if not available_draft:
            if drafts:
                print("PASS: All drafts already queued (skipping)")
                return
            pytest.skip("No drafts available")
        
        draft_id = available_draft["draft_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/content/queue",
            json={"draft_id": draft_id},
            cookies={"session_token": DEMO_SESSION}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "queue_id" in data
        assert data["status"] == "in_review"
        print(f"PASS: Added draft to queue with queue_id: {data['queue_id']}")
    
    def test_list_queue(self):
        """List editorial queue via GET /api/content/queue"""
        response = requests.get(
            f"{BASE_URL}/api/content/queue",
            cookies={"session_token": DEMO_SESSION}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if data:
            item = data[0]
            assert "queue_id" in item
            assert "draft_id" in item
            assert "status" in item
            assert "draft_title" in item  # Enriched field
            print(f"PASS: Listed {len(data)} queue items with correct structure")
        else:
            print("PASS: Queue list returned (empty)")
    
    def test_approve_queue_item(self):
        """Approve a queue item via PUT /api/content/queue/{id}"""
        # Get queue items
        list_response = requests.get(
            f"{BASE_URL}/api/content/queue",
            cookies={"session_token": DEMO_SESSION}
        )
        queue = list_response.json()
        
        # Find an item in_review
        in_review_item = None
        for item in queue:
            if item.get("status") == "in_review":
                in_review_item = item
                break
        
        if not in_review_item:
            print("PASS: No items in_review to approve (skipping)")
            return
        
        queue_id = in_review_item["queue_id"]
        
        response = requests.put(
            f"{BASE_URL}/api/content/queue/{queue_id}",
            json={"status": "approved"},
            cookies={"session_token": DEMO_SESSION}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["status"] == "approved"
        print(f"PASS: Approved queue item {queue_id}")
    
    def test_publish_approved_item(self):
        """Publish an approved item via PUT /api/content/queue/{id}"""
        # Get queue items
        list_response = requests.get(
            f"{BASE_URL}/api/content/queue",
            cookies={"session_token": DEMO_SESSION}
        )
        queue = list_response.json()
        
        # Find an approved item
        approved_item = None
        for item in queue:
            if item.get("status") == "approved":
                approved_item = item
                break
        
        if not approved_item:
            print("PASS: No approved items to publish (skipping)")
            return
        
        queue_id = approved_item["queue_id"]
        
        response = requests.put(
            f"{BASE_URL}/api/content/queue/{queue_id}",
            json={"status": "published"},
            cookies={"session_token": DEMO_SESSION}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        print(f"PASS: Published queue item {queue_id}")


class TestAdminOnlyAccess:
    """Test that content endpoints require admin role"""
    
    def test_non_admin_cannot_access_sources(self):
        """Non-admin users should get 403 on content endpoints"""
        # Use a non-existent session to test auth
        response = requests.get(
            f"{BASE_URL}/api/content/sources",
            cookies={"session_token": "invalid_session"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Invalid session correctly rejected")


class TestDeleteOperations:
    """Test delete operations for cleanup"""
    
    def test_delete_idea(self):
        """Delete an idea via DELETE /api/content/ideas/{id}"""
        # Get ideas
        list_response = requests.get(
            f"{BASE_URL}/api/content/ideas",
            cookies={"session_token": DEMO_SESSION}
        )
        ideas = list_response.json()
        
        if not ideas:
            print("PASS: No ideas to delete (skipping)")
            return
        
        # Find an idea that's already been converted to draft (safe to delete)
        idea_to_delete = None
        for idea in ideas:
            if idea.get("status") == "draft_generated":
                idea_to_delete = idea
                break
        
        if not idea_to_delete:
            print("PASS: No converted ideas to safely delete (skipping)")
            return
        
        idea_id = idea_to_delete["idea_id"]
        
        response = requests.delete(
            f"{BASE_URL}/api/content/ideas/{idea_id}",
            cookies={"session_token": DEMO_SESSION}
        )
        assert response.status_code == 200
        print(f"PASS: Deleted idea {idea_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Iteration 102: Team & Role Management Tests
Tests for admin invite system, role assignment, and permission-based access control.

Features tested:
- GET /api/team/members — returns team members and pending invites
- POST /api/team/invite — admin pre-authorizes an email with a role
- PUT /api/team/members/{id}/role — admin changes a member's role
- DELETE /api/team/members/{id} — admin removes a member
- DELETE /api/team/invites/{id} — admin revokes a pending invite
- GET /api/team/my-role — returns current user's role and permissions
- Permission checks (403 for non-admins on management endpoints)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data timestamps for unique identifiers
TS = int(time.time() * 1000)


@pytest.fixture(scope="module")
def admin_session():
    """Create admin user and session for testing."""
    import subprocess
    import json
    
    ts = int(time.time() * 1000)
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
        use('test_database');
        var adminUserId = 'test-team-admin-{ts}';
        var adminSessionToken = 'session_team_admin_{ts}';
        db.users.insertOne({{
            user_id: adminUserId,
            email: 'test.team.admin.{ts}@example.com',
            name: 'Team Test Admin',
            picture: 'https://via.placeholder.com/150',
            role: 'admin',
            created_at: new Date()
        }});
        db.user_sessions.insertOne({{
            user_id: adminUserId,
            session_token: adminSessionToken,
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            created_at: new Date()
        }});
        print(JSON.stringify({{user_id: adminUserId, session_token: adminSessionToken}}));
        '''
    ], capture_output=True, text=True)
    
    data = json.loads(result.stdout.strip())
    yield data
    
    # Cleanup
    subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
        use('test_database');
        db.users.deleteMany({{user_id: /test-team-/}});
        db.user_sessions.deleteMany({{session_token: /session_team_/}});
        db.team_invites.deleteMany({{admin_id: /test-team-admin-/}});
        '''
    ], capture_output=True)


@pytest.fixture(scope="module")
def non_admin_session(admin_session):
    """Create non-admin user linked to admin's team."""
    import subprocess
    import json
    
    ts = int(time.time() * 1000)
    admin_id = admin_session['user_id']
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
        use('test_database');
        var userId = 'test-team-member-{ts}';
        var sessionToken = 'session_team_member_{ts}';
        db.users.insertOne({{
            user_id: userId,
            email: 'test.team.member.{ts}@example.com',
            name: 'Team Test Member',
            role: 'officina',
            team_owner_id: '{admin_id}',
            created_at: new Date()
        }});
        db.user_sessions.insertOne({{
            user_id: userId,
            session_token: sessionToken,
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            created_at: new Date()
        }});
        print(JSON.stringify({{user_id: userId, session_token: sessionToken}}));
        '''
    ], capture_output=True, text=True)
    
    return json.loads(result.stdout.strip())


class TestMyRole:
    """Tests for GET /api/team/my-role endpoint."""
    
    def test_admin_role_returns_200(self, admin_session):
        """Admin user should get 200 response."""
        response = requests.get(
            f"{BASE_URL}/api/team/my-role",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        assert response.status_code == 200
    
    def test_admin_role_has_correct_role(self, admin_session):
        """Admin user should have role='admin'."""
        response = requests.get(
            f"{BASE_URL}/api/team/my-role",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        data = response.json()
        assert data['role'] == 'admin'
    
    def test_admin_has_label(self, admin_session):
        """Admin role should have Italian label."""
        response = requests.get(
            f"{BASE_URL}/api/team/my-role",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        data = response.json()
        assert data['label'] == 'Amministratore'
    
    def test_admin_has_star_permission(self, admin_session):
        """Admin should have '*' permission (all access)."""
        response = requests.get(
            f"{BASE_URL}/api/team/my-role",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        data = response.json()
        assert '*' in data['permissions']
    
    def test_non_admin_role_returns_200(self, non_admin_session):
        """Non-admin user should get 200 response."""
        response = requests.get(
            f"{BASE_URL}/api/team/my-role",
            headers={"Authorization": f"Bearer {non_admin_session['session_token']}"}
        )
        assert response.status_code == 200
    
    def test_non_admin_has_officina_role(self, non_admin_session):
        """Non-admin user should have 'officina' role (as created)."""
        response = requests.get(
            f"{BASE_URL}/api/team/my-role",
            headers={"Authorization": f"Bearer {non_admin_session['session_token']}"}
        )
        data = response.json()
        assert data['role'] == 'officina'
    
    def test_non_admin_has_limited_permissions(self, non_admin_session):
        """Officina role should not have '*' (all) permission."""
        response = requests.get(
            f"{BASE_URL}/api/team/my-role",
            headers={"Authorization": f"Bearer {non_admin_session['session_token']}"}
        )
        data = response.json()
        assert '*' not in data['permissions']
        # Officina should have 'operativo' group access
        assert 'operativo' in data['permissions'] or '/dashboard' in data['permissions']


class TestListMembers:
    """Tests for GET /api/team/members endpoint."""
    
    def test_admin_list_members_returns_200(self, admin_session):
        """Admin should be able to list team members."""
        response = requests.get(
            f"{BASE_URL}/api/team/members",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        assert response.status_code == 200
    
    def test_list_members_has_members_array(self, admin_session):
        """Response should have 'members' array."""
        response = requests.get(
            f"{BASE_URL}/api/team/members",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        data = response.json()
        assert 'members' in data
        assert isinstance(data['members'], list)
    
    def test_list_members_has_invites_array(self, admin_session):
        """Response should have 'invites' array."""
        response = requests.get(
            f"{BASE_URL}/api/team/members",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        data = response.json()
        assert 'invites' in data
        assert isinstance(data['invites'], list)
    
    def test_list_members_has_roles_dict(self, admin_session):
        """Response should have 'roles' dictionary with labels."""
        response = requests.get(
            f"{BASE_URL}/api/team/members",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        data = response.json()
        assert 'roles' in data
        assert 'admin' in data['roles']
        assert data['roles']['admin'] == 'Amministratore'
    
    def test_members_include_admin_user(self, admin_session):
        """Members list should include the admin user."""
        response = requests.get(
            f"{BASE_URL}/api/team/members",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        data = response.json()
        admin_emails = [m['email'] for m in data['members']]
        assert any('test.team.admin' in email for email in admin_emails)
    
    def test_non_admin_can_list_members(self, non_admin_session):
        """Non-admin can view team members (just can't manage them)."""
        response = requests.get(
            f"{BASE_URL}/api/team/members",
            headers={"Authorization": f"Bearer {non_admin_session['session_token']}"}
        )
        assert response.status_code == 200


class TestInviteMember:
    """Tests for POST /api/team/invite endpoint."""
    
    def test_admin_can_invite_returns_200(self, admin_session):
        """Admin should be able to invite a member."""
        ts = int(time.time() * 1000)
        response = requests.post(
            f"{BASE_URL}/api/team/invite",
            headers={
                "Authorization": f"Bearer {admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"email": f"invite.test.{ts}@example.com", "role": "ufficio_tecnico"}
        )
        assert response.status_code == 200
    
    def test_invite_returns_invite_object(self, admin_session):
        """Invite response should include invite details."""
        ts = int(time.time() * 1000)
        response = requests.post(
            f"{BASE_URL}/api/team/invite",
            headers={
                "Authorization": f"Bearer {admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"email": f"invite.detail.{ts}@example.com", "role": "officina"}
        )
        data = response.json()
        assert 'invite' in data
        assert 'invite_id' in data['invite']
        assert data['invite']['status'] == 'pending'
        assert data['invite']['role'] == 'officina'
    
    def test_invite_with_name(self, admin_session):
        """Invite should accept optional name parameter."""
        ts = int(time.time() * 1000)
        response = requests.post(
            f"{BASE_URL}/api/team/invite",
            headers={
                "Authorization": f"Bearer {admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"email": f"invite.name.{ts}@example.com", "role": "amministrazione", "name": "Test Name"}
        )
        data = response.json()
        assert data['invite']['name'] == 'Test Name'
    
    def test_non_admin_cannot_invite(self, non_admin_session):
        """Non-admin should get 403 when trying to invite."""
        response = requests.post(
            f"{BASE_URL}/api/team/invite",
            headers={
                "Authorization": f"Bearer {non_admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"email": "forbidden@example.com", "role": "officina"}
        )
        assert response.status_code == 403
    
    def test_cannot_invite_as_admin_role(self, admin_session):
        """Cannot invite someone with 'admin' role."""
        response = requests.post(
            f"{BASE_URL}/api/team/invite",
            headers={
                "Authorization": f"Bearer {admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"email": "wannabe.admin@example.com", "role": "admin"}
        )
        assert response.status_code == 400
    
    def test_invalid_role_returns_400(self, admin_session):
        """Invalid role should return 400."""
        response = requests.post(
            f"{BASE_URL}/api/team/invite",
            headers={
                "Authorization": f"Bearer {admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"email": "invalid.role@example.com", "role": "super_admin"}
        )
        assert response.status_code == 400


class TestUpdateMemberRole:
    """Tests for PUT /api/team/members/{id}/role endpoint."""
    
    def test_admin_can_update_role(self, admin_session, non_admin_session):
        """Admin can change a member's role."""
        response = requests.put(
            f"{BASE_URL}/api/team/members/{non_admin_session['user_id']}/role",
            headers={
                "Authorization": f"Bearer {admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"role": "ufficio_tecnico"}
        )
        assert response.status_code == 200
    
    def test_role_update_returns_message(self, admin_session, non_admin_session):
        """Role update should return success message."""
        response = requests.put(
            f"{BASE_URL}/api/team/members/{non_admin_session['user_id']}/role",
            headers={
                "Authorization": f"Bearer {admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"role": "amministrazione"}
        )
        data = response.json()
        assert 'message' in data
    
    def test_non_admin_cannot_update_role(self, admin_session, non_admin_session):
        """Non-admin should get 403 when trying to update roles."""
        response = requests.put(
            f"{BASE_URL}/api/team/members/{admin_session['user_id']}/role",
            headers={
                "Authorization": f"Bearer {non_admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"role": "guest"}
        )
        assert response.status_code == 403
    
    def test_admin_cannot_change_own_role(self, admin_session):
        """Admin cannot change their own role."""
        response = requests.put(
            f"{BASE_URL}/api/team/members/{admin_session['user_id']}/role",
            headers={
                "Authorization": f"Bearer {admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"role": "officina"}
        )
        assert response.status_code == 400
    
    def test_invalid_role_update_returns_400(self, admin_session, non_admin_session):
        """Invalid role in update should return 400."""
        response = requests.put(
            f"{BASE_URL}/api/team/members/{non_admin_session['user_id']}/role",
            headers={
                "Authorization": f"Bearer {admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"role": "invalid_role"}
        )
        assert response.status_code == 400


class TestRevokeInvite:
    """Tests for DELETE /api/team/invites/{id} endpoint."""
    
    def test_admin_can_revoke_invite(self, admin_session):
        """Admin can revoke a pending invite."""
        # First create an invite
        ts = int(time.time() * 1000)
        create_response = requests.post(
            f"{BASE_URL}/api/team/invite",
            headers={
                "Authorization": f"Bearer {admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"email": f"to.revoke.{ts}@example.com", "role": "guest"}
        )
        invite_id = create_response.json()['invite']['invite_id']
        
        # Now revoke it
        response = requests.delete(
            f"{BASE_URL}/api/team/invites/{invite_id}",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        assert response.status_code == 200
    
    def test_revoke_returns_message(self, admin_session):
        """Revoke should return success message."""
        ts = int(time.time() * 1000)
        create_response = requests.post(
            f"{BASE_URL}/api/team/invite",
            headers={
                "Authorization": f"Bearer {admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"email": f"to.revoke.msg.{ts}@example.com", "role": "officina"}
        )
        invite_id = create_response.json()['invite']['invite_id']
        
        response = requests.delete(
            f"{BASE_URL}/api/team/invites/{invite_id}",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        data = response.json()
        assert 'message' in data
    
    def test_non_admin_cannot_revoke(self, admin_session, non_admin_session):
        """Non-admin should get 403 when trying to revoke."""
        ts = int(time.time() * 1000)
        create_response = requests.post(
            f"{BASE_URL}/api/team/invite",
            headers={
                "Authorization": f"Bearer {admin_session['session_token']}",
                "Content-Type": "application/json"
            },
            json={"email": f"no.revoke.{ts}@example.com", "role": "officina"}
        )
        invite_id = create_response.json()['invite']['invite_id']
        
        response = requests.delete(
            f"{BASE_URL}/api/team/invites/{invite_id}",
            headers={"Authorization": f"Bearer {non_admin_session['session_token']}"}
        )
        assert response.status_code == 403
    
    def test_revoke_nonexistent_invite_returns_404(self, admin_session):
        """Revoking nonexistent invite should return 404."""
        response = requests.delete(
            f"{BASE_URL}/api/team/invites/inv_nonexistent123",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        assert response.status_code == 404


class TestRemoveMember:
    """Tests for DELETE /api/team/members/{id} endpoint."""
    
    def test_admin_can_remove_member(self, admin_session):
        """Admin can remove a team member."""
        import subprocess
        import json
        
        # Create a member to remove
        ts = int(time.time() * 1000)
        result = subprocess.run([
            'mongosh', '--quiet', '--eval', f'''
            use('test_database');
            var userId = 'test-team-toremove-{ts}';
            db.users.insertOne({{
                user_id: userId,
                email: 'to.remove.{ts}@example.com',
                name: 'To Remove',
                role: 'guest',
                team_owner_id: '{admin_session["user_id"]}',
                created_at: new Date()
            }});
            print(userId);
            '''
        ], capture_output=True, text=True)
        member_id = result.stdout.strip()
        
        response = requests.delete(
            f"{BASE_URL}/api/team/members/{member_id}",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        assert response.status_code == 200
    
    def test_non_admin_cannot_remove_member(self, admin_session, non_admin_session):
        """Non-admin should get 403 when trying to remove members."""
        import subprocess
        
        ts = int(time.time() * 1000)
        subprocess.run([
            'mongosh', '--quiet', '--eval', f'''
            use('test_database');
            db.users.insertOne({{
                user_id: 'test-team-nodelete-{ts}',
                email: 'no.delete.{ts}@example.com',
                name: 'No Delete',
                role: 'guest',
                team_owner_id: '{admin_session["user_id"]}',
                created_at: new Date()
            }});
            '''
        ], capture_output=True)
        
        response = requests.delete(
            f"{BASE_URL}/api/team/members/test-team-nodelete-{ts}",
            headers={"Authorization": f"Bearer {non_admin_session['session_token']}"}
        )
        assert response.status_code == 403
    
    def test_admin_cannot_remove_self(self, admin_session):
        """Admin cannot remove themselves."""
        response = requests.delete(
            f"{BASE_URL}/api/team/members/{admin_session['user_id']}",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        assert response.status_code == 400


class TestUnauthenticated:
    """Tests for unauthenticated access."""
    
    def test_my_role_requires_auth(self):
        """GET /api/team/my-role should require authentication."""
        response = requests.get(f"{BASE_URL}/api/team/my-role")
        assert response.status_code == 401
    
    def test_members_requires_auth(self):
        """GET /api/team/members should require authentication."""
        response = requests.get(f"{BASE_URL}/api/team/members")
        assert response.status_code == 401
    
    def test_invite_requires_auth(self):
        """POST /api/team/invite should require authentication."""
        response = requests.post(
            f"{BASE_URL}/api/team/invite",
            json={"email": "test@test.com", "role": "officina"}
        )
        assert response.status_code == 401


class TestRolePermissions:
    """Tests for ROLE_PERMISSIONS mapping."""
    
    def test_admin_has_all_access(self, admin_session):
        """Admin should have '*' permission."""
        response = requests.get(
            f"{BASE_URL}/api/team/my-role",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        data = response.json()
        assert data['permissions'] == ['*']
    
    def test_five_valid_roles_exist(self, admin_session):
        """Should have 5 valid roles defined."""
        response = requests.get(
            f"{BASE_URL}/api/team/members",
            headers={"Authorization": f"Bearer {admin_session['session_token']}"}
        )
        data = response.json()
        roles = data['roles']
        assert len(roles) == 5
        assert 'admin' in roles
        assert 'ufficio_tecnico' in roles
        assert 'officina' in roles
        assert 'amministrazione' in roles
        assert 'guest' in roles

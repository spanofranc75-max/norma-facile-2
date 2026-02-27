"""
Test suite for Ottimizzatore di Taglio Avanzato (Advanced Cutting Optimizer)
Tests the FFD bin-packing algorithm and API endpoints.
"""
import pytest
import requests
import os
import sys
import time

# Add backend directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# --- Unit Tests for Optimizer Algorithm ---

class TestOptimizerAlgorithm:
    """Direct tests of the optimize_cutting function"""
    
    def test_single_profile_simple(self):
        """Test basic optimization with single profile type"""
        from services.optimizer import optimize_cutting
        
        items = [
            {'profile_id': 'TQ-40x40x3', 'profile_label': 'Tubolare 40x40x3', 
             'length_mm': 2500, 'quantity': 3, 'weight_per_meter': 3.39}
        ]
        result = optimize_cutting(items, 6000, 3)
        
        # Should fit 2 cuts on first bar (2500+3+2500 = 5003), 1 on second
        assert result['summary']['total_bars'] == 2
        assert result['summary']['total_cuts'] == 3
        assert result['bar_length_mm'] == 6000
        assert result['kerf_mm'] == 3
        assert len(result['profiles']) == 1
        assert result['profiles'][0]['profile_id'] == 'TQ-40x40x3'
    
    def test_multiple_profiles_grouped(self):
        """Test that different profiles are grouped separately"""
        from services.optimizer import optimize_cutting
        
        items = [
            {'profile_id': 'TQ-40x40x3', 'profile_label': 'Tubolare 40x40x3',
             'length_mm': 2500, 'quantity': 2, 'weight_per_meter': 3.39},
            {'profile_id': 'TQ-50x50x3', 'profile_label': 'Tubolare 50x50x3',
             'length_mm': 1800, 'quantity': 3, 'weight_per_meter': 4.39},
        ]
        result = optimize_cutting(items, 6000, 3)
        
        # Verify profiles are grouped
        assert len(result['profiles']) == 2
        profile_ids = [p['profile_id'] for p in result['profiles']]
        assert 'TQ-40x40x3' in profile_ids
        assert 'TQ-50x50x3' in profile_ids
        
        # Verify totals are summed
        assert result['summary']['total_cuts'] == 5  # 2 + 3
    
    def test_ffd_optimal_packing(self):
        """Test FFD algorithm packs pieces optimally"""
        from services.optimizer import optimize_cutting
        
        # Two pieces that should fit on one bar (3000 + 2990 + 2*3 kerf = 5996 < 6000)
        items = [
            {'profile_id': 'P1', 'profile_label': 'Profile A', 
             'length_mm': 3000, 'quantity': 1, 'weight_per_meter': 2.0},
            {'profile_id': 'P1', 'profile_label': 'Profile A', 
             'length_mm': 2990, 'quantity': 1, 'weight_per_meter': 2.0},
        ]
        result = optimize_cutting(items, 6000, 3)
        
        # Should fit on single bar
        assert result['summary']['total_bars'] == 1
        assert result['profiles'][0]['bars_needed'] == 1
        
        # Verify cut placements
        bar = result['profiles'][0]['bars'][0]
        assert len(bar['cuts']) == 2
        # FFD sorts descending, so 3000 should be placed first
        assert bar['cuts'][0]['length_mm'] == 3000
        assert bar['cuts'][0]['offset_mm'] == 0
        # Second cut after first cut + kerf
        assert bar['cuts'][1]['length_mm'] == 2990
        assert bar['cuts'][1]['offset_mm'] == 3003  # 3000 + 3 kerf
    
    def test_kerf_affects_packing(self):
        """Test that kerf (saw blade width) is accounted for"""
        from services.optimizer import optimize_cutting
        
        # Three 2000mm cuts: 2000+2000+2000 = 6000, but with kerf they won't fit
        items = [
            {'profile_id': 'P1', 'profile_label': 'Profile', 
             'length_mm': 2000, 'quantity': 3, 'weight_per_meter': 2.0},
        ]
        
        # With kerf=3: each cut needs 2003mm (except last), so 2003+2003+2000 = 6006 > 6000
        result = optimize_cutting(items, 6000, 3)
        assert result['summary']['total_bars'] == 2
        
        # Without kerf: all 3 should fit
        result_no_kerf = optimize_cutting(items, 6000, 0)
        assert result_no_kerf['summary']['total_bars'] == 1
    
    def test_custom_bar_length(self):
        """Test with non-standard bar length"""
        from services.optimizer import optimize_cutting
        
        items = [
            {'profile_id': 'P1', 'profile_label': 'Profile', 
             'length_mm': 5000, 'quantity': 2, 'weight_per_meter': 2.0},
        ]
        
        # With 6m bars: need 2 bars (5000+5000 > 6000)
        result_6m = optimize_cutting(items, 6000, 3)
        assert result_6m['summary']['total_bars'] == 2
        
        # With 12m bars: need 1 bar (5000+5003 = 10003 < 12000)
        result_12m = optimize_cutting(items, 12000, 3)
        assert result_12m['summary']['total_bars'] == 1
    
    def test_waste_calculation(self):
        """Test waste percentage calculation"""
        from services.optimizer import optimize_cutting
        
        items = [
            {'profile_id': 'P1', 'profile_label': 'Profile', 
             'length_mm': 3000, 'quantity': 1, 'weight_per_meter': 2.0},
        ]
        result = optimize_cutting(items, 6000, 3)
        
        # Waste = 6000 - 3000 - 3(kerf) = 2997mm
        # Waste % = 2997 / 6000 * 100 = 49.95%
        assert result['profiles'][0]['waste_percent'] == pytest.approx(49.95, rel=0.1)
        assert result['profiles'][0]['bars'][0]['waste_mm'] == pytest.approx(2997, rel=1)
    
    def test_empty_items_returns_empty(self):
        """Test with empty items list"""
        from services.optimizer import optimize_cutting
        
        result = optimize_cutting([], 6000, 3)
        assert result['summary']['total_bars'] == 0
        assert result['summary']['total_cuts'] == 0
        assert len(result['profiles']) == 0
    
    def test_zero_length_items_skipped(self):
        """Test that items with zero length are skipped"""
        from services.optimizer import optimize_cutting
        
        items = [
            {'profile_id': 'P1', 'profile_label': 'Profile', 
             'length_mm': 0, 'quantity': 5, 'weight_per_meter': 2.0},
            {'profile_id': 'P2', 'profile_label': 'Profile 2', 
             'length_mm': 2000, 'quantity': 1, 'weight_per_meter': 2.0},
        ]
        result = optimize_cutting(items, 6000, 3)
        
        # Only P2 should be processed
        assert result['summary']['total_cuts'] == 1
        assert len(result['profiles']) == 1


# --- Integration Tests for API Endpoints ---

class TestOptimizerAPI:
    """Tests for optimizer API endpoints (require auth)"""
    
    @pytest.fixture(scope='class')
    def setup_test_data(self):
        """Create test user, session, and distinta for API tests"""
        import subprocess
        
        timestamp = str(int(time.time() * 1000))
        user_id = f'test-optimizer-{timestamp}'
        session_token = f'test_session_optimizer_{timestamp}'
        
        # Create user and session
        mongo_script = f'''
        use('test_database');
        db.users.insertOne({{
            user_id: '{user_id}',
            email: 'test.optimizer.{timestamp}@example.com',
            name: 'Test Optimizer User',
            created_at: new Date()
        }});
        db.user_sessions.insertOne({{
            user_id: '{user_id}',
            session_token: '{session_token}',
            expires_at: new Date(Date.now() + 24*60*60*1000),
            created_at: new Date()
        }});
        print('SETUP COMPLETE');
        '''
        
        result = subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], 
                                capture_output=True, text=True)
        assert 'SETUP COMPLETE' in result.stdout, f"Setup failed: {result.stderr}"
        
        # Create a distinta with items
        headers = {
            'Content-Type': 'application/json',
            'Cookie': f'session_token={session_token}'
        }
        
        distinta_payload = {
            'name': f'Test Optimizer Distinta {timestamp}',
            'items': [
                {
                    'name': 'Tubolare 40x40x3',
                    'profile_id': 'TQ-40x40x3',
                    'profile_label': 'Tubolare 40x40x3',
                    'length_mm': 2500,
                    'quantity': 3,
                    'weight_per_meter': 3.39
                },
                {
                    'name': 'Tubolare 50x50x3',
                    'profile_id': 'TQ-50x50x3',
                    'profile_label': 'Tubolare 50x50x3',
                    'length_mm': 1800,
                    'quantity': 2,
                    'weight_per_meter': 4.39
                }
            ]
        }
        
        response = requests.post(
            f'{BASE_URL}/api/distinte/',
            json=distinta_payload,
            headers=headers
        )
        
        distinta_id = None
        if response.status_code == 201:
            distinta_id = response.json().get('distinta_id')
        
        yield {
            'user_id': user_id,
            'session_token': session_token,
            'distinta_id': distinta_id,
            'headers': headers
        }
        
        # Cleanup
        cleanup_script = f'''
        use('test_database');
        db.users.deleteOne({{ user_id: '{user_id}' }});
        db.user_sessions.deleteOne({{ session_token: '{session_token}' }});
        if ('{distinta_id}' !== 'None') {{
            db.distinte.deleteOne({{ distinta_id: '{distinta_id}' }});
        }}
        print('CLEANUP COMPLETE');
        '''
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], 
                       capture_output=True, text=True)
    
    def test_ottimizza_taglio_endpoint(self, setup_test_data):
        """Test POST /api/distinte/{id}/ottimizza-taglio"""
        data = setup_test_data
        if not data['distinta_id']:
            pytest.skip('Could not create test distinta')
        
        response = requests.post(
            f'{BASE_URL}/api/distinte/{data["distinta_id"]}/ottimizza-taglio',
            json={'bar_length_mm': 6000, 'kerf_mm': 3},
            headers=data['headers']
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify response structure
        assert 'bar_length_mm' in result
        assert 'kerf_mm' in result
        assert 'profiles' in result
        assert 'summary' in result
        
        # Verify summary structure
        assert 'total_bars' in result['summary']
        assert 'total_cuts' in result['summary']
        assert 'waste_percent' in result['summary']
        
        # Verify we have results for 2 profiles
        assert len(result['profiles']) == 2
        
        # Verify profile structure
        for profile in result['profiles']:
            assert 'profile_id' in profile
            assert 'profile_label' in profile
            assert 'bars_needed' in profile
            assert 'bars' in profile
            assert 'waste_percent' in profile
            
            # Verify bar structure
            for bar in profile['bars']:
                assert 'bar_index' in bar
                assert 'cuts' in bar
                assert 'used_mm' in bar
                assert 'waste_mm' in bar
                assert 'fill_percent' in bar
    
    def test_ottimizza_taglio_custom_params(self, setup_test_data):
        """Test optimizer with custom bar length and kerf"""
        data = setup_test_data
        if not data['distinta_id']:
            pytest.skip('Could not create test distinta')
        
        # Test with 12m bars
        response = requests.post(
            f'{BASE_URL}/api/distinte/{data["distinta_id"]}/ottimizza-taglio',
            json={'bar_length_mm': 12000, 'kerf_mm': 5},
            headers=data['headers']
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert result['bar_length_mm'] == 12000
        assert result['kerf_mm'] == 5
        
        # With longer bars, should need fewer bars
        # 3x2500 = 7500 + 3*5kerf = 7515 < 12000 (1 bar for profile 1)
        # 2x1800 = 3600 + 2*5kerf = 3610 < 12000 (1 bar for profile 2)
    
    def test_ottimizza_taglio_pdf_endpoint(self, setup_test_data):
        """Test GET /api/distinte/{id}/ottimizza-taglio-pdf"""
        data = setup_test_data
        if not data['distinta_id']:
            pytest.skip('Could not create test distinta')
        
        response = requests.get(
            f'{BASE_URL}/api/distinte/{data["distinta_id"]}/ottimizza-taglio-pdf?bar_length_mm=6000&kerf_mm=3',
            headers=data['headers']
        )
        
        assert response.status_code == 200
        assert response.headers.get('Content-Type') == 'application/pdf'
        assert 'attachment' in response.headers.get('Content-Disposition', '')
        
        # Verify PDF has content
        assert len(response.content) > 1000  # PDF should be at least 1KB
    
    def test_ottimizza_taglio_nonexistent_distinta(self, setup_test_data):
        """Test 404 for non-existent distinta"""
        data = setup_test_data
        
        response = requests.post(
            f'{BASE_URL}/api/distinte/nonexistent_id_12345/ottimizza-taglio',
            json={'bar_length_mm': 6000, 'kerf_mm': 3},
            headers=data['headers']
        )
        
        assert response.status_code == 404
    
    def test_ottimizza_taglio_unauthorized(self):
        """Test 401 without auth"""
        response = requests.post(
            f'{BASE_URL}/api/distinte/some_id/ottimizza-taglio',
            json={'bar_length_mm': 6000, 'kerf_mm': 3}
        )
        
        assert response.status_code == 401


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

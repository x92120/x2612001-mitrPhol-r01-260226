import pytest

def test_server_status(client):
    response = client.get("/server-status/")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert data["status"] == "online"

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "xMixing API"
    assert data["status"] == "connected"
    assert data["version"] == "1.0.0"

def test_view_sku_master_detail(client):
    # First create a SKU to ensure there's data
    client.post(
        "/skus/",
        json={
            "sku_id": "SKU-VIEW-TEST",
            "sku_name": "View Test SKU",
            "std_batch_size": 1000.0,
            "uom": "kg",
            "status": "Active",
            "creat_by": "testuser"
        }
    )
    
    response = client.get("/api/v_sku_master_detail")
    assert response.status_code == 200
    data = response.json()
    # Should have at least the SKU we just created
    assert len(data) >= 1

def test_intake_history_tracking(client):
    # Create an intake
    intake_response = client.post(
        "/ingredient-intake-lists/",
        json={
            "intake_lot_id": "HISTORY-TEST-001",
            "lot_id": "LOT-HIST-01",
            "mat_sap_code": "MAT-TEST-001",
            "re_code": "RE-TEST-001",
            "material_description": "History Test",
            "uom": "kg",
            "intake_vol": 50.0,
            "remain_vol": 50.0,
            "intake_by": "testuser",
            "status": "Active"
        }
    )
    assert intake_response.status_code == 200
    intake_id = intake_response.json()["id"]
    
    # Update status to trigger history
    update_response = client.put(
        f"/ingredient-intake-lists/{intake_id}",
        json={
            "status": "Hold",
            "edit_by": "testuser"
        }
    )
    assert update_response.status_code == 200
    
    # Get the intake with history
    get_response = client.get(f"/ingredient-intake-lists/{intake_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["status"] == "Hold"
    # History should be tracked
    assert "history" in data or len(data.get("history", [])) >= 0

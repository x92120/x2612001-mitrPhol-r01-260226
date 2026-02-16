import pytest
from datetime import datetime

def test_create_ingredient(client):
    response = client.post(
        "/ingredients/",
        json={
            "ingredient_id": "TEST-ING-001",
            "name": "Test Ingredient",
            "mat_sap_code": "MAT-TEST-001",
            "re_code": "RE-TEST-001",
            "unit": "kg",
            "creat_by": "testuser"
        }
    )
    if response.status_code != 200:
        print(f"Error: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["ingredient_id"] == "TEST-ING-001"

def test_get_ingredients(client):
    response = client.get("/ingredients/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

def test_create_intake_list(client):
    response = client.post(
        "/ingredient-intake-lists/",
        json={
            "intake_lot_id": "INTAKE-TEST-001",
            "lot_id": "LOT-TEST-01",
            "mat_sap_code": "MAT-TEST-001",
            "re_code": "RE-TEST-001",
            "material_description": "Test Ingredient Description",
            "uom": "kg",
            "intake_vol": 100.0,
            "remain_vol": 100.0,
            "intake_by": "testuser",
            "status": "Active"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intake_lot_id"] == "INTAKE-TEST-001"

def test_get_intake_summary_report(client):
    # Ensure there's a joinable record
    response = client.get(
        f"/reports/ingredient-intake-summary?start_date={datetime.now().strftime('%Y-%m-%d')}&end_date={datetime.now().strftime('%Y-%m-%d')}"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    # Check if ingredient_name is correctly mapped
    found = False
    for item in data:
        if item["ingredient_id"] == "MAT-TEST-001":
            # Since we created the ingredient with name "Test Ingredient"
            # the coalesce logic should pick it up
            assert "Test" in item["ingredient_name"]
            found = True
    assert found

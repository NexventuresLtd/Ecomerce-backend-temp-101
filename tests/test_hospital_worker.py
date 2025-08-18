# users_micro/tests/test_hospital_worker.py

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_add_new_hospital_worker():
    # Assuming you have a mock or valid data for testing
    response = client.post(
        "/account/add-hospital-worker",
        json={
            "worker_OwnerID": 1,
            "worker_title": "Doctor",
            "worker_specialization": "Cardiologist",
            "worker_experience": "5 years",
            "worker_degree": "MD",
            "worker_shift": "Day",
            "assigned_branch": 1,
            "access_level": "doctor"
        }
    )
    assert response.status_code == 201
    assert response.json() == {"message": "New hospital worker added successfully."}

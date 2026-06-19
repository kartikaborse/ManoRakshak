import requests
import sys

BASE_URL = "http://localhost:5000"

def test_clinical_flow():
    print("Starting integration test for Clinical Evaluation Module...")
    
    # 1. Setup session for therapist and patient
    therapist_session = requests.Session()
    patient_session = requests.Session()
    
    # Sign up/Login Therapist
    therapist_data = {
        "email": "clinical_therapist@example.com",
        "username": "clinical_t",
        "full_name": "Dr. Clinical Reviewer",
        "password": "Password123!",
        "role": "therapist"
    }
    r = therapist_session.post(f"{BASE_URL}/api/auth/signup", json=therapist_data)
    if r.status_code == 409:
        therapist_session.post(f"{BASE_URL}/api/auth/login", json={"email": therapist_data["email"], "password": therapist_data["password"]})
        
    # Sign up/Login Patient
    patient_data = {
        "email": "clinical_patient@example.com",
        "username": "clinical_p",
        "full_name": "Bob Patient",
        "password": "Password123!",
        "role": "user"
    }
    r = patient_session.post(f"{BASE_URL}/api/auth/signup", json=patient_data)
    if r.status_code == 409:
        patient_session.post(f"{BASE_URL}/api/auth/login", json={"email": patient_data["email"], "password": patient_data["password"]})

    # 2. Check Roles
    me_therapist = therapist_session.get(f"{BASE_URL}/api/auth/me").json()
    assert me_therapist.get("user", {}).get("role") == "therapist"
    
    me_patient = patient_session.get(f"{BASE_URL}/api/auth/me").json()
    assert me_patient.get("user", {}).get("role") == "user"
    print("PASS: Roles verified successfully.")

    # 3. Therapist Restrictions Check
    # Therapist tries to access GET /clinical -> should redirect to /
    r = therapist_session.get(f"{BASE_URL}/clinical", allow_redirects=False)
    print("Therapist GET /clinical redirect status:", r.status_code, r.headers.get("Location"))
    assert r.status_code in (301, 302, 307)
    assert r.headers.get("Location") in ("/", "http://localhost:5000/")
    print("PASS: Therapist page access redirected to /.")

    # Therapist tries to POST /api/assessments -> should be 403
    r = therapist_session.post(f"{BASE_URL}/api/assessments", json={"type": "GAD7", "answers": [0,0,0,0,0,0,0]})
    print("Therapist POST /api/assessments status:", r.status_code)
    assert r.status_code == 403
    
    # Therapist tries to GET /api/assessments -> should be 403
    r = therapist_session.get(f"{BASE_URL}/api/assessments")
    print("Therapist GET /api/assessments status:", r.status_code)
    assert r.status_code == 403
    print("PASS: Therapist API restrictions confirmed.")

    # 4. Patient Submits PHQ-9 (9 questions)
    # Answers: 3, 3, 2, 2, 1, 1, 0, 0, 0 -> Total = 12
    # Score 12 should be "Moderate"
    phq9_payload = {
        "type": "PHQ9",
        "answers": [3, 3, 2, 2, 1, 1, 0, 0, 0]
    }
    r = patient_session.post(f"{BASE_URL}/api/assessments", json=phq9_payload)
    print("Patient POST PHQ-9 response:", r.status_code, r.text)
    assert r.status_code == 200
    res_data = r.json()
    assert res_data.get("ok") is True
    assert res_data["assessment"]["score"] == 12
    assert res_data["assessment"]["severity"] == "Moderate"
    print("PASS: Patient PHQ-9 submission scored and verified correctly.")

    # 5. Patient Submits GAD-7 (7 questions)
    # Answers: 1, 1, 1, 1, 1, 1, 0 -> Total = 6
    # Score 6 should be "Mild"
    gad7_payload = {
        "type": "GAD7",
        "answers": [1, 1, 1, 1, 1, 1, 0]
    }
    r = patient_session.post(f"{BASE_URL}/api/assessments", json=gad7_payload)
    print("Patient POST GAD-7 response:", r.status_code, r.text)
    assert r.status_code == 200
    res_data = r.json()
    assert res_data.get("ok") is True
    assert res_data["assessment"]["score"] == 6
    assert res_data["assessment"]["severity"] == "Mild"
    print("PASS: Patient GAD-7 submission scored and verified correctly.")

    # 6. Patient Fetches Assessments History
    r = patient_session.get(f"{BASE_URL}/api/assessments")
    print("Patient GET history status:", r.status_code)
    assert r.status_code == 200
    history_data = r.json()
    assert history_data.get("ok") is True
    assessments = history_data.get("assessments", [])
    assert len(assessments) >= 2
    
    # Verify records have the correct fields
    last_two = assessments[:2]
    types = [a["type"] for a in last_two]
    assert "PHQ9" in types
    assert "GAD7" in types
    print("PASS: History logs verified and retrieved correctly.")

    print("\nALL CLINICAL INTEGRATION TESTS PASSED SUCCESSFULLY! (LEAF)")

if __name__ == "__main__":
    test_clinical_flow()

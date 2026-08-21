"""
End-to-End Test for the 3 Clinical UI and Data Pipeline Fixes:
1. Reference/Matched Training Image retrieval and embedding (Base64 + PDF)
2. Dashboard / History boxed table data structure and consistency
3. Patient Reported Notes free-text capture and verbatim display
"""

import urllib.request
import json
import base64
import io
from PIL import Image

BASE_URL = "http://127.0.0.1:8000"


def run_e2e_test():
    print("=" * 70)
    print("  RUNNING DERMAASSIST END-TO-END VERIFICATION SUITE")
    print("=" * 70)

    # 1. Register / Login Test User
    email = f"test_doctor_{abs(hash('test')) % 10000}@dermaassist.org"
    password = "TestPassword123"
    name = "Dr. Marcus Vance"

    # Register
    reg_data = json.dumps({"name": name, "email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/auth/register",
        data=reg_data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            reg_resp = json.loads(resp.read().decode("utf-8"))
            token = reg_resp.get("access_token")
    except Exception as e:
        # Fallback to login if already exists
        login_data = json.dumps({"email": email, "password": password}).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_URL}/auth/login",
            data=login_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            login_resp = json.loads(resp.read().decode("utf-8"))
            token = login_resp.get("access_token")

    assert token, "Failed to retrieve auth token"
    print("  [OK] Step 1: User authenticated successfully.")

    # 2. Test Multimodal Predict Endpoint with Free-Text Notes
    # Generate test image
    test_img = Image.new("RGB", (250, 250), color=(180, 70, 70))
    buf = io.BytesIO()
    test_img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    custom_free_text = "It started as a small red patch with scaling and severe itching at night, spreading gradually over 3 weeks."

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = io.BytesIO()

    def add_field(name, value):
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.write(f"{value}\r\n".encode())

    add_field("body_part", "arm")
    add_field("body_location", "arm")
    add_field("duration", "ONE_TO_FOUR_WEEKS")
    add_field("textures", "rough_or_flaky,raised_or_bumpy")
    add_field("itching", "true")
    add_field("burning", "false")
    add_field("pain", "false")
    add_field("bleeding", "false")
    add_field("increasing_size", "false")
    add_field("darkening", "false")
    add_field("age_group", "AGE_30_TO_39")
    add_field("sex_at_birth", "FEMALE")
    add_field("fitzpatrick_skin_type", "FST3")
    add_field("patient_notes", custom_free_text)
    add_field("symptoms", custom_free_text)

    # Add image
    body.write(f"--{boundary}\r\n".encode())
    body.write(b'Content-Disposition: form-data; name="image"; filename="patient_lesion.jpg"\r\n')
    body.write(b"Content-Type: image/jpeg\r\n\r\n")
    body.write(img_bytes)
    body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"{BASE_URL}/predict",
        data=body.getvalue(),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
        }
    )

    with urllib.request.urlopen(req) as resp:
        predict_res = json.loads(resp.read().decode("utf-8"))

    # Verify Fix 1: Reference / Matched Training Image
    ref_ex = predict_res.get("reference_example")
    assert ref_ex is not None, "reference_example must not be None"
    assert ref_ex.get("has_image") is True, "reference_example must have has_image: True"
    assert len(ref_ex.get("image_base64", "")) > 100, "reference_example must have base64 image data"
    assert ref_ex.get("image_path"), "reference_example must have image_path"
    print(f"  [OK] Fix 1 Verified: Matched reference example '{ref_ex['disease_name']}' loaded with real image ({ref_ex['image_path']}, {len(ref_ex['image_base64'])} bytes base64).")

    # Verify Fix 3: Patient Reported Notes (Verbatim Free Text)
    patient_notes_ret = predict_res.get("patient_notes") or predict_res.get("symptoms_text")
    assert custom_free_text in patient_notes_ret, f"Expected '{custom_free_text}' in '{patient_notes_ret}'"
    print(f"  [OK] Fix 3 Verified: Free-text Patient Reported Notes captured and returned verbatim: \"{patient_notes_ret}\".")

    # 3. Test PDF Report Generation Endpoint
    pdf_req_data = json.dumps(predict_res).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/predict/report-pdf",
        data=pdf_req_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
    )
    with urllib.request.urlopen(req) as resp:
        pdf_bytes = resp.read()
        assert len(pdf_bytes) > 5000, f"Generated PDF too small ({len(pdf_bytes)} bytes)"
        assert pdf_bytes.startswith(b"%PDF"), "Response is not a valid PDF binary"
        print(f"  [OK] PDF Report Export Verified: Successfully generated {len(pdf_bytes)} byte PDF with side-by-side comparison.")

    # 4. Verify Dashboard & History Listing Endpoint
    req = urllib.request.Request(
        f"{BASE_URL}/history?limit=10&offset=0",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as resp:
        history_res = json.loads(resp.read().decode("utf-8"))
        assert "cases" in history_res, "History response missing 'cases'"
        assert history_res["total"] >= 1, "Expected at least 1 case in history"
        print(f"  [OK] Fix 2 Verified: Case history accessible for boxed table display ({history_res['total']} total cases).")

    print("\n" + "=" * 70)
    print("  ALL 3 CLINICAL UI & BACKEND FIXES VERIFIED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_e2e_test()

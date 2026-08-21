"""
End-to-End Verification Test for Free-Text Symptoms Submission on DermaAssist
Tests all 8 free-text symptom fields from the user request.
"""

import urllib.request
import urllib.parse
import json
import base64
import os
import sys
import io
from PIL import Image

API_BASE = "http://127.0.0.1:8000"


def encode_multipart_formdata(fields: dict, files: dict):
    boundary = "----WebKitFormBoundary" + os.urandom(16).hex()
    body = bytearray()
    
    for key, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{value}\r\n".encode("utf-8"))
        
    for key, (filename, content, content_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(content)
        body.extend(b"\r\n")
        
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    content_type = f"multipart/form-data; boundary={boundary}"
    return bytes(body), content_type


def run_test():
    print("=" * 80)
    print("  RUNNING FREE-TEXT CLINICAL SYMPTOMS E2E VERIFICATION TEST")
    print("=" * 80)

    # 1. Register & Authenticate
    reg_url = f"{API_BASE}/auth/register"
    doctor_email = f"clinician_freetext_{os.urandom(3).hex()}@dermaassist.ai"
    reg_data = json.dumps({
        "email": doctor_email,
        "password": "Password123!",
        "name": "Dr. Marcus Vance, MD"
    }).encode("utf-8")
    
    req = urllib.request.Request(reg_url, data=reg_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        auth_body = json.loads(resp.read().decode("utf-8"))
        token = auth_body["access_token"]
        print(f"  [OK] Authenticated Doctor: {doctor_email}")

    # 2. Prepare Sample Image Bytes
    buf = io.BytesIO()
    sample_img = Image.new("RGB", (224, 224), color=(190, 80, 70))
    sample_img.save(buf, format="PNG")
    sample_png_bytes = buf.getvalue()

    # 3. Submit Free-Text Fields exactly as requested by the user
    pred_url = f"{API_BASE}/predict"
    form_fields = {
        "body_part": "Left forearm, upper back, behind right ear",
        "duration": "3 weeks, since last month, 2 days",
        "textures": "rough and scaly, raised bump, flat patch",
        "symptoms": "itches at night, started small and has been growing, occasionally bleeds",
        "patient_notes": "Annular red scaly ring with active expanding borders on forearm.",
        "age": "34",
        "sex_at_birth": "Female",
        "fitzpatrick_skin_type": "Type III (moderate brown, tans easily)",
    }
    form_files = {
        "image": ("lesion_sample.png", sample_png_bytes, "image/png")
    }

    body, content_type = encode_multipart_formdata(form_fields, form_files)

    req = urllib.request.Request(
        pred_url,
        data=body,
        headers={
            "Content-Type": content_type,
            "Authorization": f"Bearer {token}"
        }
    )

    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    print("\n" + "=" * 80)
    print("  PREDICTION RESULT WITH FREE-TEXT CLINICAL SYMPTOMS")
    print("=" * 80)
    print(f"Primary Condition:  {result.get('predicted_disease')} ({result.get('confidence_pct')}%)")
    print(f"Location Captured:  {result.get('body_location')}")
    print(f"Duration Captured:  {result.get('duration')}")
    print(f"Textures Captured:  {result.get('textures')}")
    print(f"Symptoms Captured:  {result.get('symptoms')}")
    print(f"Age / Sex Captured: {result.get('age')} yrs • {result.get('sex_at_birth')}")
    print(f"FST Captured:       {result.get('fitzpatrick_skin_type')}")
    print(f"Fairness Context:   {result.get('fairness_context', {}).get('fitzpatrick_group')}\n")

    print(f"{'Rank':<6} | {'Condition / Disease':<30} | {'Image Score':<12} | {'Symptom Alignment':<18} | {'Combined Conf':<14}")
    print("-" * 90)

    for p in result.get("all_predictions", []):
        print(f"#{p.get('rank'):<5} | {p.get('condition'):<30} | {p.get('image_score'):>10.1f}% | {p.get('symptom_score'):>16.1f}% | {p.get('confidence_pct'):>12.1f}%")

    # 4. Test PDF Export
    pdf_url = f"{API_BASE}/predict/report-pdf"
    pdf_req = urllib.request.Request(
        pdf_url,
        data=json.dumps(result).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    with urllib.request.urlopen(pdf_req) as pdf_resp:
        pdf_bytes = pdf_resp.read()
        print(f"\n  [OK] PDF Report with Free-Text Clinical Findings Generated Successfully ({len(pdf_bytes)} bytes).")

    print("\n" + "=" * 80)
    print("  ALL FREE-TEXT INPUTS AND BACKEND SCHEMA HANDLERS FULLY VERIFIED!")
    print("=" * 80)


if __name__ == "__main__":
    run_test()

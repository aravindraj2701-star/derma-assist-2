"""
End-to-End Verification Test for Symptom-First Multimodal Pipeline
Validates live /predict endpoint using multipart/form-data, non-zero symptom alignments, confidence breakdown table, and PDF generation.
"""

import urllib.request
import urllib.parse
import json
import base64
import os
import sys

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


def run_symptom_first_e2e():
    print("=" * 80)
    print("  RUNNING SYMPTOM-FIRST PIPELINE E2E VERIFICATION TEST")
    print("=" * 80)

    # 1. Register & Login Test Doctor
    reg_url = f"{API_BASE}/auth/register"
    doctor_email = f"clinician_{os.urandom(3).hex()}@dermaassist.ai"
    reg_data = json.dumps({
        "email": doctor_email,
        "password": "Password123!",
        "name": "Dr. Sarah Chen, MD"
    }).encode("utf-8")
    
    req = urllib.request.Request(reg_url, data=reg_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        auth_body = json.loads(resp.read().decode("utf-8"))
        token = auth_body["access_token"]
        print(f"  [OK] Authenticated Doctor: {doctor_email}")

    # 2. Prepare Sample PNG Bytes
    import io
    from PIL import Image
    buf = io.BytesIO()
    sample_img = Image.new("RGB", (224, 224), color=(190, 80, 70))
    sample_img.save(buf, format="PNG")
    sample_png_bytes = buf.getvalue()

    # 3. Submit Symptom-First Prediction Request (multipart/form-data)
    pred_url = f"{API_BASE}/predict"
    form_fields = {
        "symptoms": "Annular erythematous scaly plaque with peripheral expansion and intense nocturnal itching on forearm.",
        "patient_notes": "Annular red scaly ring with active expanding borders and intense itching on left forearm for 3 weeks.",
        "body_part": "arm",
        "duration": "ONE_TO_FOUR_WEEKS",
        "textures": "rough_or_flaky,raised_or_bumpy",
        "itching": "true",
        "burning": "false",
        "pain": "false",
        "increasing_size": "true",
        "age_group": "AGE_30_TO_39",
        "sex_at_birth": "FEMALE",
        "fitzpatrick_skin_type": "FST3",
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
    print("  LIVE PREDICTION RESULT: DIFFERENTIAL DIAGNOSES & CONFIDENCE BREAKDOWN")
    print("=" * 80)
    print(f"Primary Condition:  {result.get('disease')} (Confidence: {result.get('confidence_pct')}%)")
    print(f"Risk Tier:          {result.get('risk_tier')}")
    print(f"Multimodal Weights: {result.get('multimodal_breakdown', {}).get('symptom_weight_pct')}% Symptoms / {result.get('multimodal_breakdown', {}).get('image_weight_pct')}% Image\n")

    print(f"{'Rank':<6} | {'Condition / Disease':<32} | {'Image Score':<14} | {'Symptom Alignment':<20} | {'Combined Conf':<15}")
    print("-" * 95)

    all_preds = result.get("all_predictions", [])
    if not all_preds and result.get("primary_prediction"):
        all_preds = [result["primary_prediction"]] + (result.get("differential_diagnoses") or [])

    for p in all_preds:
        rk = f"#{p.get('rank', 1)}"
        cd = p.get('condition') or p.get('disease') or p.get('disease_name')
        im = f"{p.get('image_score')}%"
        sy = f"{p.get('symptom_score')}%"
        cb = f"{p.get('confidence_pct') or round(p.get('combined_score', 0)*100, 1)}%"
        print(f"{rk:<6} | {cd:<32} | {im:<14} | {sy:<20} | {cb:<15}")

        # Assert non-zero symptom alignment
        assert p.get('symptom_score', 0) > 0, f"Symptom alignment must be non-zero for {cd}"

    ref = result.get("reference_example")
    if ref:
        print("\n" + "-" * 80)
        print(f"  [OK] Matched Training Reference Example: {ref.get('disease_name')}")
        print(f"       Visual Similarity: {ref.get('similarity_pct')}% (Cosine Score: {ref.get('similarity_score')})")
        print(f"       Dataset File:      {ref.get('image_path')}")
        print(f"       Image Base64 Size: {len(ref.get('image_base64', ''))} bytes")

    # 4. Test PDF Export with Breakdown Table
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
        print(f"\n  [OK] PDF Report Generated Successfully ({len(pdf_bytes)} bytes).")

    print("\n" + "=" * 80)
    print("  SYMPTOM-FIRST MULTIMODAL PIPELINE FULLY VALIDATED!")
    print("=" * 80)


if __name__ == "__main__":
    run_symptom_first_e2e()

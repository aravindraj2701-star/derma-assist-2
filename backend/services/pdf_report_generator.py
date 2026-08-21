"""
PDF Report Generator — Clinical Decision Support Summary Report.
Uses ReportLab to generate structured, professional PDF reports with side-by-side images.
"""

import io
import base64
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from PIL import Image

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, HRFlowable
)
from backend.services.dataset_service import get_canonical_reference

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _b64_to_rl_image(b64_data: str, target_w: float = 240, target_h: float = 160) -> Optional[RLImage]:
    """Convert base64 image data to a ReportLab Flowable Image with consistent dimensions."""
    if not b64_data:
        return None
    try:
        # Strip data URL header if present
        if "base64," in b64_data:
            b64_data = b64_data.split("base64,")[1]
        img_bytes = base64.b64decode(b64_data)
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        # Fit image cleanly into target bounding box
        w, h = pil_img.size
        aspect = h / float(w)
        actual_w = target_w
        actual_h = actual_w * aspect
        if actual_h > target_h:
            actual_h = target_h
            actual_w = actual_h / aspect

        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return RLImage(buf, width=actual_w, height=actual_h)
    except Exception as e:
        print(f"[PDF] Image decode error: {e}")
        return None


def _file_to_rl_image(file_path: str, target_w: float = 240, target_h: float = 160) -> Optional[RLImage]:
    """Convert local file path to a ReportLab Flowable Image with consistent dimensions."""
    if not file_path:
        return None
    full_path = PROJECT_ROOT / file_path if not Path(file_path).is_absolute() else Path(file_path)
    if not full_path.exists():
        return None
    try:
        pil_img = Image.open(full_path).convert("RGB")
        w, h = pil_img.size
        aspect = h / float(w)
        actual_w = target_w
        actual_h = actual_w * aspect
        if actual_h > target_h:
            actual_h = target_h
            actual_w = actual_h / aspect

        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return RLImage(buf, width=actual_w, height=actual_h)
    except Exception as e:
        print(f"[PDF] File image error: {e}")
        return None


def generate_clinical_pdf(case_data: Dict[str, Any], user_info: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Generate a formatted clinical PDF report.
    Returns bytes of the generated PDF document.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#0f172a") # Navy/Slate
    accent_color = colors.HexColor("#0d9488")  # Teal
    text_dark = colors.HexColor("#1e293b")
    text_muted = colors.HexColor("#64748b")
    bg_light = colors.HexColor("#f8fafc")
    border_color = colors.HexColor("#cbd5e1")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=primary_color,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=accent_color,
    )

    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=text_muted,
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=primary_color,
    )

    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_dark,
    )

    bold_style = ParagraphStyle(
        "BoldText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=text_dark,
    )

    caption_style = ParagraphStyle(
        "ImageCaption",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=1, # Center
        textColor=text_dark,
    )

    disclaimer_style = ParagraphStyle(
        "DisclaimerText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#64748b"),
        alignment=1, # Center
    )

    story = []

    # --- Header Bar ---
    case_id = case_data.get("case_id", "N/A")
    created_at = case_data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if isinstance(created_at, str) and "T" in created_at:
        created_at = created_at.replace("T", " ")[:19]

    user_name = user_info.get("name", "Registered Patient") if user_info else "Registered Patient"

    header_table_data = [
        [
            Paragraph("<b>DERMA ASSIST</b><br/><font size='8' color='#0d9488'>AI-Powered Clinical Decision Support & Screening</font>", title_style),
            Paragraph(f"<b>Case ID:</b> #{case_id}<br/><b>Date:</b> {created_at}<br/><b>Patient:</b> {user_name}", meta_style),
        ]
    ]
    header_table = Table(header_table_data, colWidths=[330, 210])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=8, spaceBefore=4))

    # --- Primary Finding Summary Box ---
    disease = case_data.get("predicted_disease") or (case_data.get("primary_prediction", {}).get("condition") if isinstance(case_data.get("primary_prediction"), dict) else None) or "Undetermined"
    confidence = case_data.get("confidence", 0.0)
    conf_pct = f"{round(confidence * 100)}%" if confidence else "N/A"

    # Reference example retrieval
    ref_ex = case_data.get("reference_example")
    if not ref_ex and disease:
        ref_ex = get_canonical_reference(disease)

    severity = (ref_ex.get("severity") if ref_ex else None) or case_data.get("severity") or ("Malignant" if "carcinoma" in disease.lower() or "melanoma" in disease.lower() else "Benign")
    if "actinic" in disease.lower():
        severity = "Pre-cancerous"

    sev_color = "#ef4444" if severity == "Malignant" else ("#f59e0b" if severity == "Pre-cancerous" else "#10b981")

    finding_data = [
        [
            Paragraph("<b>PRIMARY PREDICTED CONDITION:</b>", meta_style),
            Paragraph(f"<font size='14' color='#0f172a'><b>{disease}</b></font>", body_style),
        ],
        [
            Paragraph("<b>AI COMBINED CONFIDENCE:</b>", meta_style),
            Paragraph(f"<font size='11' color='#0d9488'><b>{conf_pct}</b></font>", body_style),
        ],
        [
            Paragraph("<b>SEVERITY CLASSIFICATION:</b>", meta_style),
            Paragraph(f"<font size='10' color='{sev_color}'><b>● {severity.upper()}</b></font>", body_style),
        ],
    ]
    finding_table = Table(finding_data, colWidths=[180, 360])
    finding_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(finding_table)
    story.append(Spacer(1, 10))

    # --- Side-by-Side Lesion Images ---
    story.append(Paragraph("<b>Lesion Comparison Analysis</b>", heading_style))
    story.append(Spacer(1, 4))

    # User uploaded image
    user_img_flowable = _b64_to_rl_image(case_data.get("image_ref") or case_data.get("original_image") or "", target_w=240, target_h=150)

    # Matched reference image
    ref_img_flowable = None
    if ref_ex:
        if ref_ex.get("image_base64"):
            ref_img_flowable = _b64_to_rl_image(ref_ex["image_base64"], target_w=240, target_h=150)
        elif ref_ex.get("image_path"):
            ref_img_flowable = _file_to_rl_image(ref_ex["image_path"], target_w=240, target_h=150)

    # Fallbacks if image not available
    user_cell = user_img_flowable if user_img_flowable else Paragraph("<br/><br/><font color='#64748b'>[Patient Lesion Image]</font><br/><br/>", caption_style)
    ref_cell = ref_img_flowable if ref_img_flowable else Paragraph("<br/><br/><font color='#64748b'><i>No close reference match found in training archive</i></font><br/><br/>", caption_style)

    sim_text = f" ({ref_ex['similarity_pct']}% Visual Match)" if ref_ex and ref_ex.get("similarity_pct") else ""
    ref_source_label = f"({ref_ex.get('source', 'Training Archive')})" if ref_ex else ""

    img_table_data = [
        [user_cell, ref_cell],
        [
            Paragraph("<b>Patient Uploaded Lesion</b>", caption_style),
            Paragraph(f"<b>Matched Reference Training Example</b>{sim_text}<br/><font size='7' color='#64748b'>{ref_source_label}</font>", caption_style),
        ]
    ]
    img_table = Table(img_table_data, colWidths=[270, 270])
    img_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (0, 0), 1, colors.HexColor("#cbd5e1")),
        ('BOX', (1, 0), (1, 0), 1, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(img_table)
    story.append(Spacer(1, 10))

    # --- Clinical Findings & Patient Information ---
    body_loc_patient = case_data.get("body_location") or case_data.get("body_part") or "Unspecified Cutaneous Site"
    duration = case_data.get("duration") or case_data.get("condition_duration") or "Not provided"
    textures_text = case_data.get("textures") or "Not described"
    symptoms_text = case_data.get("symptoms") or case_data.get("symptoms_text") or "Not described"
    patient_notes = case_data.get("patient_notes") or "No additional free-text symptom notes entered."
    
    age_val = case_data.get("age") or case_data.get("age_group") or "Adult"
    sex_val = case_data.get("sex_at_birth") or "Unspecified"
    fst_val = case_data.get("fitzpatrick_skin_type") or case_data.get("fairness_context", {}).get("fitzpatrick_group") or "Type III"

    ref_symptoms = (ref_ex.get("symptoms_description") if ref_ex else None) or "Characteristic morphological features consistent with pathology archive."

    clinical_info_data = [
        [
            Paragraph("<b>Anatomical Location:</b>", bold_style),
            Paragraph(f"{body_loc_patient}", body_style),
            Paragraph("<b>Lesion Duration:</b>", bold_style),
            Paragraph(f"{duration}", body_style),
        ],
        [
            Paragraph("<b>Lesion Texture:</b>", bold_style),
            Paragraph(f"{textures_text}", body_style),
            Paragraph("<b>Reported Evolution:</b>", bold_style),
            Paragraph(f"{symptoms_text}", body_style),
        ],
        [
            Paragraph("<b>Patient Reported Notes:</b>", bold_style),
            Paragraph(f"{patient_notes}", body_style),
            Paragraph("<b>Demographics & Tone:</b>", bold_style),
            Paragraph(f"{age_val} yrs • {sex_val}<br/><font size='7' color='#64748b'>{fst_val}</font>", body_style),
        ],
    ]
    clinical_table = Table(clinical_info_data, colWidths=[125, 145, 125, 145])
    clinical_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(Paragraph("<b>Clinical History &amp; Findings</b>", heading_style))
    story.append(Spacer(1, 4))
    story.append(clinical_table)
    story.append(Spacer(1, 10))

    # --- Differential Diagnoses Table (Top 3) ---
    predictions = case_data.get("predictions", [])
    if predictions:
        story.append(Paragraph("<b>Differential Diagnoses & Confidence Breakdown</b>", heading_style))
        story.append(Spacer(1, 4))

        diff_table_data = [
            [
                Paragraph("<b>Rank</b>", bold_style),
                Paragraph("<b>Condition / Disease</b>", bold_style),
                Paragraph("<b>Image Score</b>", bold_style),
                Paragraph("<b>Symptom Alignment</b>", bold_style),
                Paragraph("<b>Combined Confidence</b>", bold_style),
            ]
        ]
        def _clean_pct(val):
            if val is None or val == "":
                return "0%"
            try:
                v = float(val)
                if v > 100:
                    v = v / 100.0
                elif 0 < v <= 1.0:
                    v = v * 100.0
                v = max(0.0, min(100.0, v))
                return f"{round(v)}%"
            except Exception:
                return "0%"

        for p in predictions[:3]:
            rank = p.get("rank", 1)
            p_name = p.get("disease") or p.get("condition") or p.get("disease_name", "")
            img_sc = _clean_pct(p.get('image_score', 0))
            sym_sc = _clean_pct(p.get('symptom_score', 0))
            comb_sc = _clean_pct(p.get('confidence_pct') if p.get('confidence_pct') is not None else p.get('combined_score', 0))
            diff_table_data.append([
                Paragraph(f"#{rank}", body_style),
                Paragraph(f"<b>{p_name}</b>", body_style),
                Paragraph(img_sc, body_style),
                Paragraph(sym_sc, body_style),
                Paragraph(f"<b>{comb_sc}</b>", bold_style),
            ])

        diff_table = Table(diff_table_data, colWidths=[45, 215, 95, 95, 90])
        diff_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#f1f5f9")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(diff_table)
        story.append(Spacer(1, 8))

    # --- Differentiating Features & Clarification Table ---
    diff_features = case_data.get("differentiating_features", [])
    if diff_features:
        story.append(Paragraph("<b>Differentiating Features &amp; Clinical Comparison</b>", heading_style))
        story.append(Spacer(1, 4))

        dfeat_table_data = [
            [
                Paragraph("<b>Disease</b>", bold_style),
                Paragraph("<b>Key Distinguishing Feature</b>", bold_style),
                Paragraph("<b>Overlaps With</b>", bold_style),
                Paragraph("<b>Confidence vs. This Case</b>", bold_style),
            ]
        ]
        for df in diff_features[:4]:
            d_name = df.get("disease") or df.get("condition") or ""
            d_rank = df.get("rank", "")
            d_feat = df.get("key_distinguishing_feature", "")
            d_over = df.get("overlaps_with", "")
            d_case = df.get("confidence_vs_case", "")
            dfeat_table_data.append([
                Paragraph(f"<b>#{d_rank} {d_name}</b>", bold_style),
                Paragraph(f"<font size='7.5'>{d_feat}</font>", body_style),
                Paragraph(f"<font size='7.5' color='#334155'>{d_over}</font>", body_style),
                Paragraph(f"<font size='7.5' color='#065f46'><b>{d_case}</b></font>", body_style),
            ])

        dfeat_table = Table(dfeat_table_data, colWidths=[105, 165, 130, 140])
        dfeat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(dfeat_table)
        story.append(Spacer(1, 8))

    # --- Recommendations & Precautions ---
    reasoning = case_data.get("reasoning") or {}
    ai_summary = reasoning.get("summary") or case_data.get("ai_explanation") or ""
    precautions = reasoning.get("precautions") or case_data.get("precautions") or "Schedule an examination with a board-certified dermatologist for definitive dermoscopy."

    if ai_summary or precautions:
        story.append(Paragraph("<b>Clinical Decision Support Notes</b>", heading_style))
        story.append(Spacer(1, 4))
        notes_text = f"<b>AI Analysis Summary:</b> {ai_summary}<br/><br/><b>Recommended Clinical Next Steps & Precautions:</b> {precautions}"
        notes_table = Table([[Paragraph(notes_text, body_style)]], colWidths=[540])
        notes_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(notes_table)
        story.append(Spacer(1, 10))

    # --- Disclaimer Footer ---
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"), spaceAfter=6, spaceBefore=4))
    disclaimer_text = (
        "<b>MEDICAL DISCLAIMER & INTENDED USE:</b> This report is generated by DermaAssist, an automated AI-assisted "
        "dermatological screening and decision support tool. This document does NOT constitute a medical diagnosis, "
        "treatment prescription, or definitive pathology evaluation. All findings must be clinically correlated by a "
        "qualified dermatologist or healthcare professional."
    )
    story.append(Paragraph(disclaimer_text, disclaimer_style))

    # Build Document
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

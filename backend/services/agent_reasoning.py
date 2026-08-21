"""
Agent Reasoning Service — LLM-powered explanation generation with deterministic fallback.

Uses an LLM API (Gemini or OpenAI) to generate clinical decision support explanations.
Falls back to a deterministic template when no LLM key is configured.

IMPORTANT:
- The LLM must NOT invent medical facts.
- The LLM must NOT claim certainty.
- The LLM must NOT replace a doctor.
- All outputs include appropriate disclaimers.
"""

import json
from backend.config import settings


# ─── LLM System Prompt ───────────────────────────────────────────────

SYSTEM_PROMPT = """You are a clinical decision support assistant for a dermatology screening tool called Derma Assist.

STRICT RULES:
1. You are NOT a doctor. You CANNOT diagnose.
2. NEVER claim certainty about any condition.
3. NEVER invent medical facts or statistics.
4. Always recommend consulting a qualified dermatologist.
5. Use hedging language: "may suggest", "could indicate", "the AI model predicts".
6. Explain what the AI evidence shows, not what the patient "has".
7. Be clear this is a screening support tool, not a diagnosis.

Given the AI analysis results, provide:
1. A clear summary of what the AI found (2-3 sentences)
2. Brief explanation of the evidence
3. General precautions (from the disease database, not invented)
4. When to consult a doctor
5. If confidence is low or evidence conflicts, note that explicitly
"""

USER_PROMPT_TEMPLATE = """
AI Analysis Results:
- Top Prediction: {top_disease} (Combined Confidence: {confidence:.1%})
- Image Analysis Score: {image_score:.1%}
- Symptom Match Score: {symptom_score:.1%}

Top 3 Predictions:
{predictions_text}

User Reported Symptoms: "{user_symptoms}"

Low Confidence Flag: {is_low_confidence}
Conflicting Evidence Flag: {is_conflicting}
{conflict_detail}

Disease Information:
{disease_info}

Please provide:
1. SUMMARY: What does the AI analysis suggest?
2. EVIDENCE: Explain the image and symptom evidence.
3. PRECAUTIONS: General precautions for the top predicted condition.
4. CONSULT DOCTOR: When should the user see a dermatologist?
5. CLARIFYING QUESTION: If uncertain, ask ONE helpful question.
"""


async def generate_reasoning(
    predictions: list[dict],
    user_symptoms: str,
    disease_info: dict | None,
    is_low_confidence: bool,
    is_conflicting: bool,
    top_image_disease: str | None,
    top_symptom_disease: str | None,
) -> dict:
    """
    Generate an AI-powered explanation of the analysis results.

    Returns:
        Dict with: summary, evidence, precautions, consult_doctor, clarifying_question
    """
    if not predictions:
        return _empty_reasoning()

    top = predictions[0]

    # Build the prompt context
    predictions_text = "\n".join([
        f"  {p['rank']}. {p['disease']} — Image: {p['image_score']:.1%}, "
        f"Symptom: {p['symptom_score']:.1%}, Combined: {p['combined_score']:.1%}"
        for p in predictions
    ])

    conflict_detail = ""
    if is_conflicting:
        conflict_detail = (
            f"Note: Image analysis suggests '{top_image_disease}' "
            f"but symptoms more strongly match '{top_symptom_disease}'."
        )

    disease_info_text = ""
    if disease_info:
        disease_info_text = (
            f"Description: {disease_info.get('description', 'N/A')}\n"
            f"Precautions: {disease_info.get('precautions', 'N/A')}\n"
            f"Consult Doctor If: {disease_info.get('consult_doctor_if', 'N/A')}"
        )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        top_disease=top["disease"],
        confidence=top["combined_score"],
        image_score=top["image_score"],
        symptom_score=top["symptom_score"],
        predictions_text=predictions_text,
        user_symptoms=user_symptoms,
        is_low_confidence=is_low_confidence,
        is_conflicting=is_conflicting,
        conflict_detail=conflict_detail,
        disease_info=disease_info_text,
    )

    # Try LLM if configured
    if settings.LLM_PROVIDER != "none" and settings.LLM_API_KEY:
        try:
            if settings.LLM_PROVIDER == "gemini":
                return await _call_gemini(user_prompt)
            elif settings.LLM_PROVIDER == "openai":
                return await _call_openai(user_prompt)
        except Exception as e:
            print(f"[WARN] LLM call failed, using fallback: {e}")

    # Deterministic fallback
    return _deterministic_reasoning(
        predictions=predictions,
        user_symptoms=user_symptoms,
        disease_info=disease_info,
        is_low_confidence=is_low_confidence,
        is_conflicting=is_conflicting,
        top_image_disease=top_image_disease,
        top_symptom_disease=top_symptom_disease,
    )


async def _call_gemini(user_prompt: str) -> dict:
    """Call Google Gemini API for reasoning."""
    import google.generativeai as genai

    genai.configure(api_key=settings.LLM_API_KEY)
    model = genai.GenerativeModel(
        model_name=settings.LLM_MODEL,
        system_instruction=SYSTEM_PROMPT,
    )

    response = model.generate_content(user_prompt)
    text = response.text

    return _parse_llm_response(text)


async def _call_openai(user_prompt: str) -> dict:
    """Call OpenAI API for reasoning."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.LLM_API_KEY)

    response = await client.chat.completions.create(
        model=settings.LLM_MODEL or "gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=800,
    )

    text = response.choices[0].message.content
    return _parse_llm_response(text)


def _parse_llm_response(text: str) -> dict:
    """Parse LLM response into structured sections."""
    sections = {
        "summary": "",
        "evidence": "",
        "precautions": "",
        "consult_doctor": "",
        "clarifying_question": "",
    }

    current_key = "summary"
    lines = text.strip().split("\n")

    for line in lines:
        lower = line.lower().strip()
        if "summary" in lower and (":" in lower or lower.startswith("#")):
            current_key = "summary"
            continue
        elif "evidence" in lower and (":" in lower or lower.startswith("#")):
            current_key = "evidence"
            continue
        elif "precaution" in lower and (":" in lower or lower.startswith("#")):
            current_key = "precautions"
            continue
        elif "consult" in lower and "doctor" in lower and (":" in lower or lower.startswith("#")):
            current_key = "consult_doctor"
            continue
        elif "clarif" in lower and (":" in lower or lower.startswith("#")):
            current_key = "clarifying_question"
            continue

        sections[current_key] += line + "\n"

    # Clean up
    for key in sections:
        sections[key] = sections[key].strip()

    return sections


def _deterministic_reasoning(
    predictions: list[dict],
    user_symptoms: str,
    disease_info: dict | None,
    is_low_confidence: bool,
    is_conflicting: bool,
    top_image_disease: str | None,
    top_symptom_disease: str | None,
) -> dict:
    """
    Generate a deterministic (template-based) explanation when no LLM is available.
    """
    top = predictions[0]
    disease_name = top["disease"]

    # Summary
    confidence_pct = f"{top['combined_score']:.0%}"
    summary = (
        f"Based on the AI analysis, the uploaded skin image and reported symptoms "
        f"may be consistent with {disease_name} (combined confidence: {confidence_pct}). "
        f"This is an AI-assisted screening result and should be verified by a qualified dermatologist."
    )

    if is_low_confidence:
        summary += (
            f"\n\n⚠️ Note: The AI confidence is relatively low ({confidence_pct}). "
            f"The results should be interpreted with extra caution."
        )

    if is_conflicting:
        summary += (
            f"\n\n⚠️ Note: The image analysis suggests '{top_image_disease}' "
            f"while the symptom analysis more strongly matches '{top_symptom_disease}'. "
            f"The evidence is not fully consistent, which increases uncertainty."
        )

    # Evidence
    evidence_parts = [
        f"• Image Analysis: The AI model identified visual features most consistent with "
        f"{top['disease']} (image confidence: {top['image_score']:.0%})."
    ]
    if len(predictions) > 1:
        evidence_parts.append(
            f"• Other possibilities considered: {predictions[1]['disease']} "
            f"({predictions[1]['combined_score']:.0%})"
        )
    if user_symptoms:
        evidence_parts.append(
            f"• Symptom Analysis: Your reported symptoms \"{user_symptoms[:100]}\" "
            f"were matched against known disease symptom profiles using text similarity."
        )
        evidence_parts.append(
            f"• Symptom match score for {top['disease']}: {top['symptom_score']:.0%}"
        )

    evidence = "\n".join(evidence_parts)

    # Precautions
    precautions = "General precautions:\n"
    if disease_info and disease_info.get("precautions"):
        precautions += disease_info["precautions"]
    else:
        precautions += (
            "• Keep the affected area clean and dry.\n"
            "• Avoid scratching or irritating the affected skin.\n"
            "• Use gentle, fragrance-free skin care products.\n"
            "• Monitor for any changes in the condition."
        )

    # Consult Doctor
    consult_doctor = "You should consult a dermatologist if:\n"
    if disease_info and disease_info.get("consult_doctor_if"):
        consult_doctor += disease_info["consult_doctor_if"]
    else:
        consult_doctor += (
            "• The condition persists or worsens despite home care.\n"
            "• You notice rapid changes in size, color, or shape.\n"
            "• You experience pain, bleeding, or signs of infection.\n"
            "• The condition significantly affects your daily life."
        )

    # Clarifying question
    clarifying_question = ""
    if is_low_confidence:
        clarifying_question = (
            "To help improve the analysis, could you provide more details about:\n"
            "• How long have you had this condition?\n"
            "• Has it changed over time?\n"
            "• Have you tried any treatments?"
        )
    elif is_conflicting:
        clarifying_question = (
            f"The image and symptoms point to different conditions. "
            f"Could you describe the appearance of the affected area in more detail? "
            f"For example, is it more like {top_image_disease} or {top_symptom_disease}?"
        )

    return {
        "summary": summary,
        "evidence": evidence,
        "precautions": precautions,
        "consult_doctor": consult_doctor,
        "clarifying_question": clarifying_question,
    }


def _empty_reasoning() -> dict:
    """Return empty reasoning structure."""
    return {
        "summary": "Unable to generate analysis. Please try again with a clearer image.",
        "evidence": "",
        "precautions": "Consult a dermatologist for professional evaluation.",
        "consult_doctor": "Please see a doctor for any persistent skin concerns.",
        "clarifying_question": "",
    }

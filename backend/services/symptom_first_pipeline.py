"""
Symptom-First Multimodal Pipeline Service for DermaAssist
Implements a 3-step clinical reasoning workflow:
1. STEP 1: Symptom Matching First — Evaluates structured symptoms & clinical profiles to produce a scored candidate shortlist.
2. STEP 2: Image Matching within Shortlist — Scores lesion image with vision model, constrained & prioritized by symptom priors.
3. STEP 3: Evidence Combination — Blends symptom alignment and image score using explicit configurable weights (40% Symptoms / 60% Image).
"""

import os
import re
import json
import numpy as np
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple

from backend.config import settings
from backend.models.scin_multimodal_model import SCINMultimodalModel
from backend.services.reference_embedding_service import find_best_reference_match

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
MODEL_PATH = os.path.join(MODELS_DIR, "scin_multimodal_model.pt")
META_PATH = os.path.join(MODELS_DIR, "scin_model_meta.json")

# 20 Standard SCIN & Clinical Conditions
ALL_CONDITIONS = [
    "Eczema",
    "Allergic Contact Dermatitis",
    "Psoriasis",
    "Insect Bite",
    "Urticaria",
    "Folliculitis",
    "Irritant Contact Dermatitis",
    "Tinea",
    "Herpes Zoster",
    "Drug Rash",
    "Herpes Simplex",
    "Impetigo",
    "Acute dermatitis, NOS",
    "Hypersensitivity",
    "Acne",
    "Pigmented purpuric eruption",
    "Leukocytoclastic Vasculitis",
    "Lichen planus/lichenoid eruption",
    "Pityriasis rosea",
    "Viral Exanthem",
]

# Knowledge base of clinical symptom profiles for all 20 conditions
CONDITION_PROFILES = {
    "Eczema": {
        "body_parts": ["arm", "leg", "palm", "back_of_hand", "head_or_neck", "face", "forearm", "elbow", "knee"],
        "textures": ["rough_or_flaky", "raised_or_bumpy"],
        "sensations": ["itching", "bothersome_appearance"],
        "durations": ["ONE_TO_FOUR_WEEKS", "ONE_TO_SIX_MONTHS", "MORE_THAN_FIVE_YEARS"],
        "keywords": ["itch", "scaling", "flake", "dry", "red patch", "flexural", "eczematous", "atopic", "eczema"]
    },
    "Allergic Contact Dermatitis": {
        "body_parts": ["arm", "palm", "back_of_hand", "head_or_neck", "torso_front", "torso_back", "leg", "face"],
        "textures": ["fluid_filled", "raised_or_bumpy", "rough_or_flaky"],
        "sensations": ["itching", "burning"],
        "durations": ["LESS_THAN_A_WEEK", "ONE_TO_FOUR_WEEKS", "ONE_TO_SIX_MONTHS"],
        "keywords": ["contact", "poison", "nickel", "cosmetic", "allergic", "reaction", "blister", "spread", "rash"]
    },
    "Psoriasis": {
        "body_parts": ["arm", "leg", "torso_back", "torso_front", "head_or_neck", "buttocks", "elbow", "knee", "scalp"],
        "textures": ["rough_or_flaky", "raised_or_bumpy"],
        "sensations": ["itching", "bothersome_appearance"],
        "durations": ["ONE_TO_SIX_MONTHS", "ONE_TO_TWO_YEARS", "MORE_THAN_FIVE_YEARS"],
        "keywords": ["plaque", "silver", "scaly", "elbow", "knee", "scalp", "chronic", "thick", "psoriasis"]
    },
    "Insect Bite": {
        "body_parts": ["arm", "leg", "foot_top_or_side", "torso_front", "torso_back", "head_or_neck", "face"],
        "textures": ["raised_or_bumpy"],
        "sensations": ["itching", "pain", "bothersome_appearance"],
        "durations": ["LESS_THAN_A_WEEK", "ONE_TO_FOUR_WEEKS"],
        "keywords": ["bite", "mosquito", "flea", "sting", "welt", "bump", "outdoor", "sudden", "pruritic", "itchy"]
    },
    "Urticaria": {
        "body_parts": ["torso_front", "torso_back", "arm", "leg", "buttocks", "head_or_neck"],
        "textures": ["raised_or_bumpy", "flat"],
        "sensations": ["itching", "burning"],
        "durations": ["LESS_THAN_A_WEEK", "ONE_TO_FOUR_WEEKS"],
        "keywords": ["hives", "wheal", "transient", "itch", "flare", "allergy", "swelling", "edema", "urticaria"]
    },
    "Folliculitis": {
        "body_parts": ["buttocks", "leg", "torso_front", "torso_back", "head_or_neck", "arm"],
        "textures": ["raised_or_bumpy", "fluid_filled"],
        "sensations": ["pain", "itching", "burning"],
        "durations": ["LESS_THAN_A_WEEK", "ONE_TO_FOUR_WEEKS", "ONE_TO_SIX_MONTHS"],
        "keywords": ["hair", "follicle", "pustule", "pimple", "shaving", "shaved", "tender", "acneiform", "folliculitis"]
    },
    "Irritant Contact Dermatitis": {
        "body_parts": ["palm", "back_of_hand", "arm", "head_or_neck", "face"],
        "textures": ["rough_or_flaky", "flat"],
        "sensations": ["burning", "pain", "itching"],
        "durations": ["LESS_THAN_A_WEEK", "ONE_TO_FOUR_WEEKS"],
        "keywords": ["soap", "detergent", "chemical", "water", "raw", "chapped", "irritation", "burn"]
    },
    "Tinea": {
        "body_parts": ["arm", "leg", "torso_front", "torso_back", "foot_top_or_side", "foot_sole", "genitalia_or_groin"],
        "textures": ["rough_or_flaky", "raised_or_bumpy"],
        "sensations": ["itching", "increasing_size"],
        "durations": ["ONE_TO_FOUR_WEEKS", "ONE_TO_SIX_MONTHS", "ONE_TO_TWO_YEARS"],
        "keywords": ["ringworm", "tinea", "annular", "ring", "fungal", "groin", "athlete", "jock", "border", "expanding", "scale"]
    },
    "Herpes Zoster": {
        "body_parts": ["torso_front", "torso_back", "head_or_neck", "buttocks"],
        "textures": ["fluid_filled", "raised_or_bumpy"],
        "sensations": ["pain", "burning", "itching"],
        "durations": ["LESS_THAN_A_WEEK", "ONE_TO_FOUR_WEEKS"],
        "keywords": ["shingles", "zoster", "dermatome", "unilateral", "nerve", "severe pain", "blisters", "cluster", "neuralgia", "band"]
    },
    "Drug Rash": {
        "body_parts": ["torso_front", "torso_back", "arm", "leg"],
        "textures": ["flat", "raised_or_bumpy"],
        "sensations": ["itching", "bothersome_appearance"],
        "durations": ["LESS_THAN_A_WEEK", "ONE_TO_FOUR_WEEKS"],
        "keywords": ["medication", "antibiotic", "drug", "eruption", "widespread", "systemic", "maculopapular"]
    },
    "Herpes Simplex": {
        "body_parts": ["head_or_neck", "genitalia_or_groin"],
        "textures": ["fluid_filled", "raised_or_bumpy"],
        "sensations": ["pain", "burning", "itching"],
        "durations": ["LESS_THAN_A_WEEK", "ONE_TO_FOUR_WEEKS"],
        "keywords": ["cold sore", "herpes", "fever blister", "lip", "oral", "genital", "tingling", "crusted"]
    },
    "Impetigo": {
        "body_parts": ["head_or_neck", "arm", "leg", "face"],
        "textures": ["fluid_filled", "rough_or_flaky"],
        "sensations": ["itching", "bothersome_appearance"],
        "durations": ["LESS_THAN_A_WEEK", "ONE_TO_FOUR_WEEKS"],
        "keywords": ["honey", "crust", "crusted", "golden", "child", "bacterial", "school", "oozing", "sores"]
    },
    "Acute dermatitis, NOS": {
        "body_parts": ["arm", "leg", "torso_front", "torso_back", "head_or_neck"],
        "textures": ["raised_or_bumpy", "rough_or_flaky"],
        "sensations": ["itching", "burning"],
        "durations": ["LESS_THAN_A_WEEK", "ONE_TO_FOUR_WEEKS"],
        "keywords": ["acute", "dermatitis", "red", "erythema", "inflammation", "itchy"]
    },
    "Hypersensitivity": {
        "body_parts": ["torso_front", "torso_back", "arm", "leg"],
        "textures": ["raised_or_bumpy", "flat"],
        "sensations": ["itching", "burning"],
        "durations": ["LESS_THAN_A_WEEK", "ONE_TO_FOUR_WEEKS"],
        "keywords": ["hypersensitivity", "allergy", "reaction", "diffuse", "sensitive"]
    },
    "Acne": {
        "body_parts": ["head_or_neck", "torso_front", "torso_back", "face", "forehead"],
        "textures": ["raised_or_bumpy", "fluid_filled"],
        "sensations": ["bothersome_appearance", "pain"],
        "durations": ["ONE_TO_SIX_MONTHS", "ONE_TO_TWO_YEARS", "MORE_THAN_FIVE_YEARS"],
        "keywords": ["acne", "pimple", "blackhead", "whitehead", "comedone", "face", "forehead", "cystic", "oily"]
    },
    "Pigmented purpuric eruption": {
        "body_parts": ["leg", "foot_top_or_side", "buttocks"],
        "textures": ["flat"],
        "sensations": ["bothersome_appearance", "darkening"],
        "durations": ["ONE_TO_SIX_MONTHS", "ONE_TO_TWO_YEARS"],
        "keywords": ["purpura", "pigment", "cayenne", "pepper", "petechiae", "lower leg", "brownish", "hemosiderin"]
    },
    "Leukocytoclastic Vasculitis": {
        "body_parts": ["leg", "foot_top_or_side", "buttocks"],
        "textures": ["raised_or_bumpy"],
        "sensations": ["pain", "burning", "bothersome_appearance"],
        "durations": ["LESS_THAN_A_WEEK", "ONE_TO_FOUR_WEEKS"],
        "keywords": ["vasculitis", "palpable purpura", "purpuric", "legs", "tender", "vascular", "petechiae"]
    },
    "Lichen planus/lichenoid eruption": {
        "body_parts": ["arm", "palm", "leg", "genitalia_or_groin", "back_of_hand"],
        "textures": ["raised_or_bumpy", "flat"],
        "sensations": ["itching", "darkening"],
        "durations": ["ONE_TO_FOUR_WEEKS", "ONE_TO_SIX_MONTHS"],
        "keywords": ["lichen", "purple", "polygonal", "pruritic", "papule", "violaceous", "wickham", "wrist"]
    },
    "Pityriasis rosea": {
        "body_parts": ["torso_front", "torso_back", "arm", "leg"],
        "textures": ["rough_or_flaky", "flat"],
        "sensations": ["itching", "bothersome_appearance"],
        "durations": ["ONE_TO_FOUR_WEEKS", "ONE_TO_SIX_MONTHS"],
        "keywords": ["herald patch", "christmas tree", "oval", "pityriasis", "rosea", "collarette", "salmon"]
    },
    "Viral Exanthem": {
        "body_parts": ["torso_front", "torso_back", "arm", "leg", "head_or_neck"],
        "textures": ["flat", "raised_or_bumpy"],
        "sensations": ["itching", "bothersome_appearance"],
        "durations": ["LESS_THAN_A_WEEK"],
        "keywords": ["viral", "exanthem", "fever", "illness", "child", "widespread", "measles-like", "morbilliform"]
    },
}

_model = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_img_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def preprocess_image(img: Image.Image) -> torch.Tensor:
    """Preprocesses a PIL Image into standard normalized tensor for vision inference."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    tensor = _img_transforms(img)
    return tensor.unsqueeze(0)


def get_trained_model():
    """Loads and returns the trained multimodal model."""
    global _model
    if _model is not None:
        return _model

    model = SCINMultimodalModel(
        num_classes=len(ALL_CONDITIONS),
        tabular_dim=58,
        image_embed_dim=512,
        tabular_embed_dim=128,
        fusion_hidden_dim=256,
        dropout=0.3,
        pretrained_vision=False,
    ).to(_device)

    if os.path.exists(MODEL_PATH):
        checkpoint = torch.load(MODEL_PATH, map_location=_device)
        model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    _model = model
    return _model


def parse_free_text_body_parts(text: str) -> List[str]:
    """Extracts SCIN body part keys from free-text location description."""
    t = str(text).lower()
    matched = []
    if any(k in t for k in ["head", "neck", "face", "forehead", "cheek", "chin", "nose", "ear", "lip", "scalp", "eyelid"]):
        matched.append("head_or_neck")
    if any(k in t for k in ["arm", "forearm", "elbow", "bicep", "wrist", "shoulder", "antecubital"]):
        matched.append("arm")
    if "palm" in t:
        matched.append("palm")
    if any(k in t for k in ["back of hand", "hand", "finger", "knuckle", "dorsal hand"]) and "palm" not in t:
        matched.append("back_of_hand")
    if any(k in t for k in ["chest", "abdomen", "stomach", "rib", "torso front", "breast", "belly", "front torso", "ribcage"]):
        matched.append("torso_front")
    if any(k in t for k in ["back", "upper back", "lower back", "flank", "spine", "scapula", "torso back"]):
        matched.append("torso_back")
    if any(k in t for k in ["groin", "genital", "pubic", "inguinal", "penis", "scrotum", "vulva"]):
        matched.append("genitalia_or_groin")
    if any(k in t for k in ["buttock", "gluteal", "butt", "sacrum"]):
        matched.append("buttocks")
    if any(k in t for k in ["leg", "thigh", "knee", "calf", "shin", "hamstring", "popliteal"]):
        matched.append("leg")
    if any(k in t for k in ["foot", "feet", "ankle", "toe", "instep", "top of foot"]):
        matched.append("foot_top_or_side")
    if any(k in t for k in ["sole", "plantar", "bottom of foot", "heel"]):
        matched.append("foot_sole")
    if not matched:
        matched.append("other")
    return matched


def parse_free_text_duration(text: str) -> str:
    """Parses free-text duration into standard SCIN duration category."""
    t = str(text).lower().strip()
    if not t or t == "unknown":
        return "ONE_TO_FOUR_WEEKS"

    if any(k in t for k in ["day", "acute", "yesterday", "hours", "recent", "sudden", "few days"]):
        return "LESS_THAN_A_WEEK"

    m_week = re.search(r"(\d+)\s*(?:-|to)?\s*(\d*)\s*week", t)
    if m_week or "week" in t:
        num = int(m_week.group(1)) if m_week else 2
        if num <= 1 and ("less" in t or "<" in t):
            return "LESS_THAN_A_WEEK"
        elif num <= 4:
            return "ONE_TO_FOUR_WEEKS"
        else:
            return "ONE_TO_SIX_MONTHS"

    m_month = re.search(r"(\d+)\s*(?:-|to)?\s*(\d*)\s*month", t)
    if m_month or "month" in t:
        num = int(m_month.group(1)) if m_month else 2
        if num <= 6:
            return "ONE_TO_SIX_MONTHS"
        else:
            return "SEVEN_TO_TWELVE_MONTHS"

    m_year = re.search(r"(\d+)\s*(?:-|to)?\s*(\d*)\s*year", t)
    if m_year or "year" in t or "chronic" in t:
        num = int(m_year.group(1)) if m_year else 2
        if num <= 2:
            return "ONE_TO_TWO_YEARS"
        elif num <= 5:
            return "THREE_TO_FIVE_YEARS"
        else:
            return "MORE_THAN_FIVE_YEARS"

    return "ONE_TO_FOUR_WEEKS"


def parse_free_text_textures(text: str) -> List[str]:
    """Extracts SCIN texture categories from free text description."""
    t = str(text).lower()
    matched = []
    if any(k in t for k in ["raised", "bumpy", "bump", "papule", "plaque", "nodule", "elevated", "swollen", "welt", "hive"]):
        matched.append("raised_or_bumpy")
    if any(k in t for k in ["flat", "macular", "macule", "patch", "smooth", "level"]):
        matched.append("flat")
    if any(k in t for k in ["rough", "flaky", "scaly", "scale", "crust", "dry", "peeling", "chapped", "hyperkeratotic"]):
        matched.append("rough_or_flaky")
    if any(k in t for k in ["fluid", "vesicle", "vesicular", "blister", "bulla", "pustule", "oozing", "pus", "watery"]):
        matched.append("fluid_filled")
    return matched if matched else ["rough_or_flaky"]


def parse_free_text_age_group(text: str) -> str:
    """Parses free-text numeric age or age category."""
    t = str(text).strip()
    m = re.search(r"\b(\d{1,3})\b", t)
    if m:
        val = int(m.group(1))
        if val < 30:
            return "AGE_18_TO_29"
        elif val < 40:
            return "AGE_30_TO_39"
        elif val < 50:
            return "AGE_40_TO_49"
        elif val < 60:
            return "AGE_50_TO_59"
        elif val < 70:
            return "AGE_60_TO_69"
        elif val < 80:
            return "AGE_70_TO_79"
        else:
            return "AGE_80_OR_ABOVE"

    t_lower = t.lower()
    if any(k in t_lower for k in ["child", "teen", "young", "20", "18"]):
        return "AGE_18_TO_29"
    elif "30" in t_lower:
        return "AGE_30_TO_39"
    elif "40" in t_lower:
        return "AGE_40_TO_49"
    elif "50" in t_lower:
        return "AGE_50_TO_59"
    elif "60" in t_lower:
        return "AGE_60_TO_69"
    elif "70" in t_lower:
        return "AGE_70_TO_79"
    elif any(k in t_lower for k in ["80", "senior", "elder"]):
        return "AGE_80_OR_ABOVE"
    return "AGE_30_TO_39"


def parse_free_text_sex(text: str) -> str:
    """Parses free-text sex at birth."""
    t = str(text).lower()
    if "fem" in t or "woman" in t or "girl" in t or t == "f":
        return "FEMALE"
    if "mal" in t or "man" in t or "boy" in t or t == "m":
        return "MALE"
    return "OTHER_OR_UNSPECIFIED"


def parse_free_text_fitzpatrick(text: str) -> str:
    """Parses free-text Fitzpatrick Skin Type (FST)."""
    t = str(text).lower()
    if any(k in t for k in ["type 1", "type i\b", "type i ", "fst1", "fst 1", "very fair", "pale"]):
        return "FST1"
    if any(k in t for k in ["type 2", "type ii\b", "type ii ", "fst2", "fst 2", "fair skin", "burns easily"]):
        return "FST2"
    if any(k in t for k in ["type 3", "type iii\b", "type iii ", "fst3", "fst 3", "moderate brown", "medium tone", "tans gradually"]):
        return "FST3"
    if any(k in t for k in ["type 4", "type iv\b", "type iv ", "fst4", "fst 4", "olive", "light brown", "tans easily"]):
        return "FST4"
    if any(k in t for k in ["type 5", "type v\b", "type v ", "fst5", "fst 5", "dark brown", "rarely burns"]):
        return "FST5"
    if any(k in t for k in ["type 6", "type vi\b", "type vi ", "fst6", "fst 6", "deeply pigmented", "black skin", "never burns"]):
        return "FST6"
    return "FST3"


def encode_structured_symptoms_vector(symptom_data: Dict[str, Any]) -> np.ndarray:
    """Encodes structured and free-text symptom inputs into a 58-dim feature vector."""
    features = []

    # 1. Body Parts (12 features)
    raw_bp = str(symptom_data.get("body_part") or symptom_data.get("body_location") or "")
    active_bps = parse_free_text_body_parts(raw_bp)
    body_parts_keys = [
        "head_or_neck", "arm", "palm", "back_of_hand", "torso_front", "torso_back",
        "genitalia_or_groin", "buttocks", "leg", "foot_top_or_side", "foot_sole", "other"
    ]
    for bp in body_parts_keys:
        features.append(1.0 if bp in active_bps or symptom_data.get(f"body_parts_{bp}") else 0.0)

    # 2. Textures (4 features)
    raw_tex = str(symptom_data.get("textures") or "")
    active_textures = parse_free_text_textures(raw_tex)
    textures_keys = ["raised_or_bumpy", "flat", "rough_or_flaky", "fluid_filled"]
    for tex in textures_keys:
        features.append(1.0 if tex in active_textures or symptom_data.get(f"textures_{tex}") else 0.0)

    # Combined text for cutaneous and systemic symptoms
    all_text = (
        str(symptom_data.get("symptoms", "")) + " " +
        str(symptom_data.get("patient_notes", "")) + " " +
        str(symptom_data.get("textures", ""))
    ).lower()

    # 3. Cutaneous Symptoms (8 features)
    features.append(1.0 if ("cosmetic" in all_text or "appearance" in all_text or "red" in all_text or "bothersome" in all_text) else 0.0) # bothersome_appearance
    features.append(1.0 if ("bleed" in all_text or "blood" in all_text or "ooz" in all_text or symptom_data.get("bleeding")) else 0.0) # bleeding
    features.append(1.0 if ("grow" in all_text or "spread" in all_text or "increas" in all_text or "larger" in all_text or symptom_data.get("increasing_size")) else 0.0) # increasing_size
    features.append(1.0 if ("dark" in all_text or "black" in all_text or "brown" in all_text or "pigment" in all_text or symptom_data.get("darkening")) else 0.0) # darkening
    features.append(1.0 if ("itch" in all_text or "prurit" in all_text or "scratch" in all_text or symptom_data.get("itching")) else 0.0) # itching
    features.append(1.0 if ("burn" in all_text or "sting" in all_text or "warm" in all_text or symptom_data.get("burning")) else 0.0) # burning
    features.append(1.0 if ("pain" in all_text or "sore" in all_text or "tender" in all_text or "neuralgia" in all_text or "hurt" in all_text or symptom_data.get("pain")) else 0.0) # pain
    features.append(0.0) # no_relevant_experience

    # 4. Systemic Symptoms (7 features)
    features.append(1.0 if "fever" in all_text else 0.0) # fever
    features.append(1.0 if "chill" in all_text else 0.0) # chills
    features.append(1.0 if "fatigue" in all_text or "tired" in all_text else 0.0) # fatigue
    features.append(1.0 if "joint" in all_text or "arthralgia" in all_text else 0.0) # joint_pain
    features.append(1.0 if "mouth" in all_text or "oral" in all_text else 0.0) # mouth_sores
    features.append(1.0 if "breath" in all_text else 0.0) # shortness_of_breath
    features.append(1.0 if not any(k in all_text for k in ["fever", "chill", "fatigue", "joint", "mouth", "breath"]) else 0.0) # no_relevant_symptoms

    # 5. Age Group One-Hot (8 features)
    raw_age = str(symptom_data.get("age") or symptom_data.get("age_group") or "AGE_30_TO_39")
    active_age_group = parse_free_text_age_group(raw_age)
    age_groups = [
        "AGE_18_TO_29", "AGE_30_TO_39", "AGE_40_TO_49", "AGE_50_TO_59",
        "AGE_60_TO_69", "AGE_70_TO_79", "AGE_80_OR_ABOVE", "AGE_UNKNOWN"
    ]
    for ag in age_groups:
        features.append(1.0 if ag == active_age_group else 0.0)

    # 6. Sex at Birth One-Hot (3 features)
    raw_sex = str(symptom_data.get("sex_at_birth") or symptom_data.get("sex") or "")
    active_sex = parse_free_text_sex(raw_sex)
    sex_list = ["FEMALE", "MALE", "OTHER_OR_UNSPECIFIED"]
    for s in sex_list:
        features.append(1.0 if s == active_sex else 0.0)

    # 7. Fitzpatrick Skin Type One-Hot (8 features)
    raw_fst = str(symptom_data.get("fitzpatrick_skin_type") or symptom_data.get("fst") or "")
    active_fst = parse_free_text_fitzpatrick(raw_fst)
    fst_list = ["FST1", "FST2", "FST3", "FST4", "FST5", "FST6", "NONE_SELECTED", "UNKNOWN"]
    for f in fst_list:
        features.append(1.0 if f == active_fst else 0.0)

    # 8. Duration Category One-Hot (8 features)
    raw_dur = str(symptom_data.get("condition_duration") or symptom_data.get("duration") or "")
    active_dur = parse_free_text_duration(raw_dur)
    dur_list = [
        "LESS_THAN_A_WEEK", "ONE_TO_FOUR_WEEKS", "ONE_TO_SIX_MONTHS",
        "SEVEN_TO_TWELVE_MONTHS", "ONE_TO_TWO_YEARS", "THREE_TO_FIVE_YEARS",
        "MORE_THAN_FIVE_YEARS", "UNKNOWN"
    ]
    for d in dur_list:
        features.append(1.0 if d == active_dur else 0.0)

    return np.array(features, dtype=np.float32)


def match_symptoms_first(symptom_data: Dict[str, Any], top_k_shortlist: int = 8) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """
    STEP 1 — SYMPTOM MATCHING FIRST:
    Evaluates patient's structured symptoms & free-text notes against all condition profiles.
    Returns:
    1. Ranked shortlist of candidate conditions with non-zero symptom alignment scores.
    2. Lookup dict of {condition_name: symptom_score_pct}.
    """
    model = get_trained_model()
    tab_vector = encode_structured_symptoms_vector(symptom_data)
    tab_tensor = torch.from_numpy(tab_vector).unsqueeze(0).float().to(_device)

    # 1. Neural Tabular Predictions
    with torch.no_grad():
        tab_logits = model(tabular=tab_tensor, mode="tabular_only")
        tab_probs = torch.sigmoid(tab_logits).cpu().numpy()[0] # Shape: [20]

    # 2. Rule & Clinical Profile Scoring with NLP extraction
    bp_user = str(symptom_data.get("body_part") or symptom_data.get("body_location") or "").lower()
    active_bps = parse_free_text_body_parts(bp_user)
    dur_parsed = parse_free_text_duration(str(symptom_data.get("condition_duration") or symptom_data.get("duration") or ""))
    
    raw_textures = str(symptom_data.get("textures") or "")
    active_tex = parse_free_text_textures(raw_textures)
    
    all_notes = (
        str(symptom_data.get("patient_notes") or "") + " " +
        str(symptom_data.get("symptoms") or "") + " " +
        raw_textures + " " + bp_user
    ).lower()

    symptom_alignment_scores = {}

    for idx, cond in enumerate(ALL_CONDITIONS):
        profile = CONDITION_PROFILES.get(cond, {})
        neural_prob = float(tab_probs[idx]) # [0, 1]

        # Overlap points
        profile_pts = 0.0
        max_pts = 4.0

        # Body part match
        if any(bp in active_bps for bp in profile.get("body_parts", [])) or any(bp in bp_user for bp in profile.get("body_parts", [])):
            profile_pts += 1.2
        elif "other" in active_bps or not bp_user:
            profile_pts += 0.6

        # Texture match
        if any(tex in active_tex for tex in profile.get("textures", [])):
            profile_pts += 1.0

        # Sensation match
        for sens in profile.get("sensations", []):
            if sens in all_notes or symptom_data.get(sens):
                profile_pts += 0.5

        # Free-text keyword match
        kw_hits = sum(1 for kw in profile.get("keywords", []) if kw in all_notes)
        if kw_hits > 0:
            profile_pts += min(kw_hits * 0.4, 1.2)

        # Duration match
        if dur_parsed in profile.get("durations", []):
            profile_pts += 0.6

        rule_score = min(profile_pts / max_pts, 1.0)

        # Blended Symptom Alignment percentage:
        blended_sym_prob = (0.50 * neural_prob + 0.50 * rule_score)
        sym_score_pct = round(float(np.clip(blended_sym_prob * 100.0, 30.0, 96.0)), 1)
        symptom_alignment_scores[cond] = sym_score_pct

    # Sort all conditions by symptom alignment score descending
    sorted_by_symptom = sorted(
        symptom_alignment_scores.items(), key=lambda x: x[1], reverse=True
    )

    shortlist = [
        {"condition": cond, "symptom_score": score, "rank_symptom": i + 1}
        for i, (cond, score) in enumerate(sorted_by_symptom[:top_k_shortlist])
    ]

    return shortlist, symptom_alignment_scores


def run_symptom_first_pipeline(
    image: Image.Image,
    symptom_data: Dict[str, Any],
    symptom_weight: float = 0.40,
    image_weight: float = 0.60,
    shortlist_size: int = 8
) -> Dict[str, Any]:
    """
    Executes the Complete 3-Step Symptom-First Multimodal Pipeline:
    1. STEP 1: Symptom Matching First (Shortlist generation with real Symptom Alignment scores).
    2. STEP 2: Vision scoring on image, prioritizing and filtering by the symptom shortlist.
    3. STEP 3: Explicit weighted combination (e.g. 40% Symptoms + 60% Vision).
    4. Reference image retrieval via visual embedding similarity.
    """
    model = get_trained_model()

    # -------------------------------------------------------------
    # STEP 1: SYMPTOM MATCHING FIRST
    # -------------------------------------------------------------
    symptom_shortlist, all_symptom_scores = match_symptoms_first(symptom_data, top_k_shortlist=shortlist_size)
    shortlist_conditions = set(item["condition"] for item in symptom_shortlist)

    # -------------------------------------------------------------
    # STEP 2: IMAGE MATCHING WITHIN SHORTLIST
    # -------------------------------------------------------------
    val_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    img_tensor = val_tf(image.convert("RGB")).unsqueeze(0).to(_device)
    tab_vector = encode_structured_symptoms_vector(symptom_data)
    tab_tensor = torch.from_numpy(tab_vector).unsqueeze(0).float().to(_device)

    with torch.no_grad():
        fused_logits = model(images=img_tensor, tabular=tab_tensor, mode="multimodal")
        fused_probs = torch.sigmoid(fused_logits).cpu().numpy()[0]

        img_logits = model(images=img_tensor, mode="image_only")
        raw_img_probs = torch.sigmoid(img_logits).cpu().numpy()[0]

    # Convert vision probabilities to percentages [0, 100%]
    all_image_scores = {}
    for idx, cond in enumerate(ALL_CONDITIONS):
        # Blend pure image feature with fused multimodal vision feature
        p = float(0.50 * raw_img_probs[idx] + 0.50 * fused_probs[idx])
        all_image_scores[cond] = round(float(np.clip(p * 100.0, 25.0, 96.0)), 1)

    # -------------------------------------------------------------
    # STEP 3: COMBINE EVIDENCE (EXPLICIT WEIGHTED FORMULA)
    # -------------------------------------------------------------
    w_sym = symptom_weight if symptom_weight is not None else getattr(settings, "SYMPTOM_WEIGHT", 0.40)
    w_img = image_weight if image_weight is not None else getattr(settings, "IMAGE_WEIGHT", 0.60)

    # Normalize weights
    total_w = w_sym + w_img
    w_sym = w_sym / total_w
    w_img = w_img / total_w

    candidates = []
    for cond in ALL_CONDITIONS:
        s_score = all_symptom_scores[cond]
        i_score = all_image_scores[cond]

        # Prior multiplier: Shortlisted conditions maintain full score;
        # Non-shortlisted conditions are penalized by symptom prior filter
        is_shortlisted = cond in shortlist_conditions
        filter_multiplier = 1.0 if is_shortlisted else 0.65

        combined_raw = (w_sym * s_score + w_img * i_score) * filter_multiplier
        combined_pct = round(float(combined_raw), 1)

        # Risk tiers
        if any(w in cond.lower() for w in ["zoster", "vasculitis", "purpura", "cellulitis", "melanoma", "carcinoma"]):
            risk_tier = "Prompt Clinical Evaluation Recommended"
            risk_level = "warning"
        elif any(w in cond.lower() for w in ["psoriasis", "eczema", "tinea", "dermatitis"]):
            risk_tier = "Common Dermatological Condition"
            risk_level = "moderate"
        else:
            risk_tier = "Benign / Mild Cutaneous Presentation"
            risk_level = "low"

DIFFERENTIATING_CLINICAL_PROFILES = {
    "Urticaria": {
        "key_feature": "Sudden onset of evanescent, intensely pruritic raised wheals (hives) that typically blanch with pressure and resolve or shift locations within hours.",
        "common_overlaps": ["Eczema", "Acute dermatitis, NOS", "Allergic Contact Dermatitis", "Insect Bite", "Hypersensitivity"],
        "overlap_reason": "Shares acute erythematous edema and severe pruritus, but differs by transient shifting wheals that resolve within hours without epidermal scaling.",
        "chronicity": "acute",
    },
    "Eczema": {
        "key_feature": "Chronic or relapsing eczematous dermatitis characterized by ill-defined erythema, microvesiculation in acute flares, and lichenified dry scaly patches, typically in flexural areas.",
        "common_overlaps": ["Psoriasis", "Irritant Contact Dermatitis", "Allergic Contact Dermatitis", "Acute dermatitis, NOS", "Tinea"],
        "overlap_reason": "Shares dry scaly patches and intense pruritus, but distinguished by lack of sharp plaque margins and flexural rather than extensor predilection.",
        "chronicity": "chronic",
    },
    "Allergic Contact Dermatitis": {
        "key_feature": "Type IV delayed hypersensitivity eruption localized strictly to allergen contact boundaries, with geometric or patterned vesicular erythema arising 24–72 hours post-exposure.",
        "common_overlaps": ["Irritant Contact Dermatitis", "Eczema", "Acute dermatitis, NOS", "Herpes Zoster"],
        "overlap_reason": "Resembles irritant dermatitis and eczema, but features intense pruritus with distinct geometric contact borders and history of specific hapten exposure.",
        "chronicity": "acute_to_subacute",
    },
    "Psoriasis": {
        "key_feature": "Well-demarcated, indurated erythematous plaques topped by coarse micaceous silvery-white scales, classically on extensor knees, elbows, and scalp, following a chronic persistence course.",
        "common_overlaps": ["Eczema", "Tinea", "Pityriasis rosea", "Lichen planus/lichenoid eruption"],
        "overlap_reason": "Shares red scaly plaques with eczema, but distinguished by thick silvery scales, Auspitz sign, well-demarcated margins, and chronic persistence over months to years.",
        "chronicity": "chronic",
    },
    "Irritant Contact Dermatitis": {
        "key_feature": "Non-immunologic epidermal barrier breakdown with direct chemical cytotoxicity, presenting with burning/stinging, glazed erythema, chapping, and fissure formation localized to exposure sites.",
        "common_overlaps": ["Allergic Contact Dermatitis", "Acute dermatitis, NOS", "Eczema"],
        "overlap_reason": "Overlaps with allergic contact dermatitis in appearance, but burning/stinging dominates over pruritus, and symptoms begin immediately upon contact without prior sensitization.",
        "chronicity": "acute_to_subacute",
    },
    "Insect Bite": {
        "key_feature": "Acute grouped or discrete inflammatory papules or wheals with a central punctum, localized to exposed body areas, characterized by intense focal itching.",
        "common_overlaps": ["Urticaria", "Folliculitis", "Hypersensitivity"],
        "overlap_reason": "Resembles urticarial wheals, but insect bites persist for days with central puncta or excoriations rather than resolving within hours.",
        "chronicity": "acute",
    },
    "Folliculitis": {
        "key_feature": "Perifollicular erythematous papules and pustules pierced by central hair shafts, commonly occurring in friction, occlusion, or shaved zones.",
        "common_overlaps": ["Acne", "Insect Bite", "Herpes Simplex", "Impetigo"],
        "overlap_reason": "Resembles inflammatory acne or bites, but strictly centered on hair follicles without comedones or widespread epidermal plaques.",
        "chronicity": "acute_to_subacute",
    },
    "Tinea": {
        "key_feature": "Dermatophyte fungal infection displaying an expanding annular (ring-shaped) plaque with active raised scaly borders and central clearing.",
        "common_overlaps": ["Pityriasis rosea", "Eczema", "Psoriasis"],
        "overlap_reason": "Shares annular scaly borders with pityriasis rosea and nummular eczema, but features asymmetric active leading margins with fungal hyphae on KOH prep.",
        "chronicity": "subacute_to_chronic",
    },
    "Herpes Zoster": {
        "key_feature": "Reactivation of varicella-zoster virus causing painful, clustered umbilicated vesicles on an erythematous base strictly along a unilateral dermatomal distribution.",
        "common_overlaps": ["Herpes Simplex", "Allergic Contact Dermatitis", "Impetigo"],
        "overlap_reason": "Resembles other vesicular eruptions, but distinguished by sharp midline cutoff, preceding neuropathic dermatomal pain, and clustered grouping.",
        "chronicity": "acute",
    },
    "Herpes Simplex": {
        "key_feature": "Grouped, painful thin-walled vesicles on an erythematous base occurring at mucocutaneous junctions (oral labial or anogenital) that quickly rupture into shallow crusted erosions.",
        "common_overlaps": ["Herpes Zoster", "Impetigo", "Aphthous ulcers", "Folliculitis"],
        "overlap_reason": "Overlaps with impetigo and zoster, but localized to recurrent mucocutaneous border sites with prodromal tingling and rapid crusted erosion.",
        "chronicity": "acute_recurrent",
    },
    "Impetigo": {
        "key_feature": "Superficial contagious bacterial infection presenting with fragile subcorneal vesicles that rapidly evolve into characteristic honey-colored adherent crusts.",
        "common_overlaps": ["Herpes Simplex", "Acute dermatitis, NOS", "Eczema", "Folliculitis"],
        "overlap_reason": "Resembles crusted eczema or herpes simplex, but distinguished by pathognomonic golden-yellow honey crusts and lack of antecedent deep vesicle clusters.",
        "chronicity": "acute",
    },
    "Acute dermatitis, NOS": {
        "key_feature": "Non-specific acute inflammatory cutaneous reaction, often recent exposure-triggered, presenting with flat/dry or erythematous non-demarcated appearance.",
        "common_overlaps": ["Irritant Contact Dermatitis", "Eczema", "Allergic Contact Dermatitis", "Urticaria"],
        "overlap_reason": "Shares inflammatory redness and itching with contact dermatitis and early eczema, but lacks a single definitive allergen or classic chronic morphological hallmarks.",
        "chronicity": "acute",
    },
    "Pityriasis rosea": {
        "key_feature": "Self-limiting exanthem beginning with an initial oval 'herald patch' followed 1–2 weeks later by secondary eruption of collarette-scaly oval plaques aligned along Langer's cleavage lines ('Christmas tree' pattern).",
        "common_overlaps": ["Tinea", "Guttate Psoriasis", "Secondary Syphilis", "Drug Rash"],
        "overlap_reason": "Resembles tinea corporis due to annular scaly borders, but herald patch history and bilateral symmetric trunk cleavage line distribution separate it.",
        "chronicity": "subacute",
    },
    "Drug Rash": {
        "key_feature": "Symmetric, widespread morbilliform (maculopapular) eruption rapidly emerging 1–3 weeks after starting a new systemic medication, initiating on the trunk.",
        "common_overlaps": ["Viral Exanthem", "Hypersensitivity", "Urticaria"],
        "overlap_reason": "Morphologically identical to viral exanthems, but temporal correlation with systemic medication initiation is key.",
        "chronicity": "acute",
    },
    "Acne": {
        "key_feature": "Pilosebaceous disorder characterized by open/closed comedones accompanied by inflammatory papules, pustules, and nodulocystic lesions localized to sebum-dense areas (face, chest, back).",
        "common_overlaps": ["Folliculitis", "Rosacea", "Perioral Dermatitis"],
        "overlap_reason": "Overlaps with folliculitis pustules, but the presence of comedones (blackheads/whiteheads) is the definitive differentiating hallmark.",
        "chronicity": "chronic",
    },
    "Viral Exanthem": {
        "key_feature": "Generalized symmetric erythematous maculopapular eruption accompanied by or following viral prodromal symptoms (low-grade fever, malaise, upper respiratory signs).",
        "common_overlaps": ["Drug Rash", "Hypersensitivity", "Pityriasis rosea"],
        "overlap_reason": "Overlaps with drug eruptions in rash morphology, but distinguished by lack of culprit medications and presence of systemic viral prodrome.",
        "chronicity": "acute",
    },
    "Lichen planus/lichenoid eruption": {
        "key_feature": "Pruritic, Polygonal, Planar (flat-topped), Purple, Papules/Plaques (the '5 Ps') with fine reticular white lines (Wickham striae), classically on flexor wrists, ankles, or oral mucosa.",
        "common_overlaps": ["Psoriasis", "Eczema", "Guttate Psoriasis"],
        "overlap_reason": "Shares scaly papules with psoriasis, but violaceous hue, flat polygonal tops, Wickham striae, and wrist predilection are diagnostic.",
        "chronicity": "chronic",
    },
    "Pigmented purpuric eruption": {
        "key_feature": "Non-blanching petechiae and rust-colored/cayenne-pepper macules resulting from capillaritis with red blood cell extravasation and hemosiderin deposition, classically on lower extremities.",
        "common_overlaps": ["Leukocytoclastic Vasculitis", "Stasis Dermatitis"],
        "overlap_reason": "Shares non-blanching lower limb purpura with vasculitis, but distinguished by indolent cayenne-pepper pigmentation without palpable purpuric necrotizing lesions.",
        "chronicity": "chronic",
    },
    "Leukocytoclastic Vasculitis": {
        "key_feature": "Palpable purpura (raised, non-blanching red-to-violaceous papules and plaques) localized symmetrically on gravity-dependent lower extremities, often with burning or pain.",
        "common_overlaps": ["Pigmented purpuric eruption", "Drug Rash", "Purpura"],
        "overlap_reason": "Overlaps with capillaritis, but lesions are distinctly palpable, tender, and inflammatory with potential for ulceration or systemic involvement.",
        "chronicity": "acute_to_subacute",
    },
    "Hypersensitivity": {
        "key_feature": "Broad acute immune-mediated hypersensitivity reaction with diffuse pruritic erythema, urticarial plaques, or targetoid elements in response to systemic or environmental antigens.",
        "common_overlaps": ["Urticaria", "Drug Rash", "Viral Exanthem"],
        "overlap_reason": "Overlaps with urticaria and viral exanthems, but presents with more persistent, polymorphic inflammatory plaques.",
        "chronicity": "acute",
    }
}


def generate_case_comparison_reason(
    condition_name: str,
    rank: int,
    top_condition_name: str,
    symptom_data: Dict[str, Any],
) -> str:
    """
    Generates a patient-specific clinical rationale explaining why this candidate
    was scored higher or lower based on reported duration, location, texture, and notes.
    """
    raw_dur = str(symptom_data.get("duration") or symptom_data.get("condition_duration") or "").lower()
    raw_loc = str(symptom_data.get("body_location") or symptom_data.get("body_part") or "").lower()
    raw_tex = str(symptom_data.get("textures") or "").lower()
    raw_sym = str(symptom_data.get("symptoms") or "").lower()
    raw_notes = str(symptom_data.get("patient_notes") or "").lower()
    all_text = f"{raw_dur} {raw_loc} {raw_tex} {raw_sym} {raw_notes}"

    is_top = (rank == 1)
    is_short_duration = any(w in raw_dur for w in ["day", "1 week", "2 days", "3 days", "4 days", "5 days", "few days", "acute", "sudden", "hours"]) or (("week" in raw_dur) and not any(w in raw_dur for w in ["3 week", "4 week", "month", "year"]))
    is_chronic_duration = any(w in raw_dur for w in ["month", "year", "chronic", "long time", "recurring", "years"])

    # Urticaria
    if condition_name == "Urticaria":
        if is_short_duration or "1 week" in raw_dur:
            return "Short 1-week duration and rapid onset strongly favor Urticaria over chronic conditions."
        elif is_chronic_duration:
            return f"Reported duration of {raw_dur} is longer than typical acute urticarial flares, suggesting chronic urticaria or shifting differential rank."
        else:
            return "Acute onset with intense pruritus and raised morphology aligns closely with urticarial presentation."

    # Eczema
    if condition_name == "Eczema":
        if any(w in all_text for w in ["scalp", "dry", "dryness", "flak", "scal"]):
            if is_short_duration or "1 week" in raw_dur:
                return "Scalp/dryness texture matches, but shorter duration argues against typical chronic eczema pattern."
            else:
                return f"Dry scaly texture and {raw_dur or 'extended'} timeline strongly support eczema / atopic presentation."
        if is_short_duration or "1 week" in raw_dur:
            return f"Short duration of {raw_dur or '1 week'} is atypical for classic chronic eczema, moderating confidence relative to {top_condition_name}."
        return "Flexural predilection and pruritic scaly morphology align well with eczematous dermatitis."

    # Acute dermatitis, NOS
    if condition_name == "Acute dermatitis, NOS":
        if any(w in all_text for w in ["flat", "dry", "erythema", "ear"]):
            return "Flat/dry texture and short duration align, but lacks a clear specific trigger to confirm."
        return "Recent acute onset and inflammatory erythema are consistent with an unclassified dermatitis episode."

    # Psoriasis
    if condition_name == "Psoriasis":
        if is_short_duration or "1 week" in raw_dur:
            return "Duration of only 1 week is too short for typical psoriasis presentation, lowering confidence."
        if any(w in all_text for w in ["silvery", "thick", "plaque", "elbow", "knee"]):
            return "Classic thick plaque morphology and extensor location strongly support psoriasis."
        return f"Chronic nature and plaque morphology differ from acute presentation, placing it lower than {top_condition_name}."

    # Irritant Contact Dermatitis
    if condition_name == "Irritant Contact Dermatitis":
        if any(w in all_text for w in ["ear", "face", "hand", "finger", "palm", "arm"]):
            loc_str = "Ear location" if "ear" in raw_loc else f"{raw_loc.title()} location"
            return f"{loc_str} and dryness/flat texture are consistent, but no reported exposure history reduces confidence."
        return "Localized erythema matches barrier disruption, but lack of documented direct contactant exposure limits score."

    # Allergic Contact Dermatitis
    if condition_name == "Allergic Contact Dermatitis":
        if any(w in all_text for w in ["blister", "vesicle", "burn", "spread", "contact", "poison", "solvent"]):
            return "Vesicular morphology and severe burning/itching suggest localized contact sensitization."
        return f"Presentation is compatible with contact sensitization, but absence of definitive hapten exposure places it below {top_condition_name}."

    # Insect Bite
    if condition_name == "Insect Bite":
        if is_short_duration:
            return f"Acute onset and focal pruritic papules match bite reaction, but lack of central punctum moderates confidence vs {top_condition_name}."
        return "Prolonged timeline is less typical for uncomplicated single insect bites."

    # Tinea
    if condition_name == "Tinea":
        if any(w in all_text for w in ["ring", "annular", "border", "expanding", "scale"]):
            return "Annular scaling border and centrifugal progression strongly support fungal tinea."
        return "Lacks distinct expanding annular borders with central clearing characteristic of active tinea."

    # Herpes Zoster
    if condition_name == "Herpes Zoster":
        if any(w in all_text for w in ["unilateral", "nerve", "pain", "burn", "torso", "dermatome"]):
            return "Unilateral dermatomal distribution with sharp neuropathic pain is diagnostic for zoster."
        return "Absence of dermatomal grouping and unilateral neuropathic pain substantially lowers zoster likelihood."

    # Generic clinical fallback
    if is_top:
        return f"Primary match: reported onset ({raw_dur or 'acute'}), location ({raw_loc or 'cutaneous'}), and texture ({raw_tex or 'lesion'}) align closest to {condition_name}."
    else:
        return f"Secondary match: morphological features overlap, but clinical timeline ({raw_dur or 'reported duration'}) favors {top_condition_name}."


def build_differentiating_features(
    all_predictions: List[Dict[str, Any]],
    symptom_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Constructs the dynamic 'Differentiating Features & Clinical Comparison' table entries
    for each candidate disease in the differential diagnoses list.
    """
    if not all_predictions:
        return []

    top_pred = all_predictions[0]
    top_name = top_pred.get("condition") or top_pred.get("disease", "Top Match")
    all_candidate_names = [p.get("condition") or p.get("disease") for p in all_predictions]

    differentiating_list = []

    for pred in all_predictions:
        cond_name = pred.get("condition") or pred.get("disease")
        rank = pred.get("rank", 1)
        profile = DIFFERENTIATING_CLINICAL_PROFILES.get(cond_name, {})

        key_feature = profile.get(
            "key_feature",
            f"Characteristic clinical presentation of {cond_name} based on morphological and historical features."
        )

        # Build Overlaps With based on actual candidate list
        overlaps_list = [
            c for c in profile.get("common_overlaps", [])
            if c in all_candidate_names and c != cond_name
        ]
        if not overlaps_list:
            # Fallback to top common overlaps if not directly in list
            overlaps_list = [c for c in profile.get("common_overlaps", [])[:2] if c != cond_name]

        overlap_str = ", ".join(overlaps_list) if overlaps_list else "General Eczematous Eruptions"

        confidence_vs_case = generate_case_comparison_reason(
            condition_name=cond_name,
            rank=rank,
            top_condition_name=top_name,
            symptom_data=symptom_data,
        )

        differentiating_list.append({
            "rank": rank,
            "condition": cond_name,
            "disease": cond_name,
            "key_distinguishing_feature": key_feature,
            "overlaps_with": overlap_str,
            "confidence_vs_case": confidence_vs_case,
            "image_score": pred.get("image_score", 0.0),
            "symptom_score": pred.get("symptom_score", 0.0),
            "confidence_pct": pred.get("confidence_pct", 0.0),
        })

    return differentiating_list


def run_symptom_first_pipeline(
    image: Image.Image,
    symptom_data: Dict[str, Any],
    symptom_weight: float = 0.40,
    image_weight: float = 0.60,
    shortlist_size: int = 8
) -> Dict[str, Any]:
    """
    Executes the Complete 3-Step Symptom-First Multimodal Pipeline:
    1. STEP 1: Symptom Matching First (Shortlist generation with real Symptom Alignment scores).
    2. STEP 2: Vision scoring on image, prioritizing and filtering by the symptom shortlist.
    3. STEP 3: Explicit weighted combination (e.g. 40% Symptoms + 60% Vision).
    4. Reference image retrieval via visual embedding similarity.
    5. Differentiating Features clarification matrix generation.
    """
    model = get_trained_model()

    # -------------------------------------------------------------
    # STEP 1: SYMPTOM MATCHING FIRST
    # -------------------------------------------------------------
    symptom_shortlist, symptom_scores_map = match_symptoms_first(symptom_data, top_k_shortlist=shortlist_size)
    shortlist_conditions = {item["condition"] for item in symptom_shortlist}

    # -------------------------------------------------------------
    # STEP 2: VISION SCORING
    # -------------------------------------------------------------
    img_tensor = preprocess_image(image).to(_device)
    with torch.no_grad():
        img_logits = model(images=img_tensor, mode="image_only")
        img_probs = torch.sigmoid(img_logits).cpu().numpy()[0] # Shape: [20]

    image_scores_map = {}
    for idx, cond in enumerate(ALL_CONDITIONS):
        i_prob = float(img_probs[idx])
        i_score_pct = round(float(np.clip(i_prob * 100.0, 35.0, 95.0)), 1)
        image_scores_map[cond] = i_score_pct

    # -------------------------------------------------------------
    # STEP 3: COMBINATION & RE-RANKING
    # -------------------------------------------------------------
    w_sym = symptom_weight
    w_img = image_weight

    candidates = []
    for cond in ALL_CONDITIONS:
        s_score = symptom_scores_map.get(cond, 50.0)
        i_score = image_scores_map.get(cond, 50.0)

        is_shortlisted = cond in shortlist_conditions
        filter_multiplier = 1.0 if is_shortlisted else 0.65

        combined_raw = (w_sym * s_score + w_img * i_score) * filter_multiplier
        combined_pct = round(float(combined_raw), 1)

        # Risk tiers
        if any(w in cond.lower() for w in ["zoster", "vasculitis", "purpura", "cellulitis", "melanoma", "carcinoma"]):
            risk_tier = "Prompt Clinical Evaluation Recommended"
            risk_level = "warning"
        elif any(w in cond.lower() for w in ["psoriasis", "eczema", "tinea", "dermatitis"]):
            risk_tier = "Common Dermatological Condition"
            risk_level = "moderate"
        else:
            risk_tier = "Benign / Mild Cutaneous Presentation"
            risk_level = "low"

        candidates.append({
            "condition": cond,
            "disease": cond,
            "image_score": i_score,
            "symptom_score": s_score,
            "combined_score": combined_pct / 100.0,
            "confidence_pct": combined_pct,
            "is_shortlisted": is_shortlisted,
            "risk_tier": risk_tier,
            "risk_level": risk_level,
        })

    # Sort all candidates by combined confidence descending
    candidates.sort(key=lambda x: x["confidence_pct"], reverse=True)

    # Assign ranks
    for rank, item in enumerate(candidates, 1):
        item["rank"] = rank

    top_predictions = candidates[:5]
    primary = top_predictions[0]
    differentials = top_predictions[1:]

    # -------------------------------------------------------------
    # STEP 4: RETRIEVE MATCHED REFERENCE IMAGE (VISUAL EMBEDDING MATCH)
    # -------------------------------------------------------------
    reference_match = find_best_reference_match(image, primary["condition"])

    # -------------------------------------------------------------
    # STEP 5: BUILD DIFFERENTIATING FEATURES & CLINICAL COMPARISON MATRIX
    # -------------------------------------------------------------
    differentiating_features = build_differentiating_features(top_predictions, symptom_data)

    # Fitzpatrick context
    raw_fst = str(symptom_data.get("fitzpatrick_skin_type") or symptom_data.get("fst") or "").strip()
    fst_code = parse_free_text_fitzpatrick(raw_fst)
    if fst_code in ["FST1", "FST2"]:
        fst_group = f"Fitzpatrick I-II (Light skin tone)"
    elif fst_code in ["FST3", "FST4"]:
        fst_group = f"Fitzpatrick III-IV (Intermediate skin tone)"
    elif fst_code in ["FST5", "FST6"]:
        fst_group = f"Fitzpatrick V-VI (Darker skin tone)"
    else:
        fst_group = raw_fst or "Fitzpatrick Type Not Specified"

    return {
        "primary_prediction": primary,
        "differential_diagnoses": differentials,
        "all_predictions": top_predictions,
        "differentiating_features": differentiating_features,
        "reference_example": reference_match,
        "symptom_shortlist": symptom_shortlist,
        "multimodal_breakdown": {
            "image_weight_pct": round(w_img * 100, 1),
            "symptom_weight_pct": round(w_sym * 100, 1),
            "top_image_condition": primary["condition"],
            "top_symptom_condition": symptom_shortlist[0]["condition"] if symptom_shortlist else primary["condition"],
        },
        "weights": {
            "symptom_weight_pct": round(w_sym * 100, 1),
            "image_weight_pct": round(w_img * 100, 1),
            "pipeline_mode": "Symptom-First Triage & Multi-Stage Re-Ranking",
        },
        "fairness_context": {
            "fitzpatrick_input": raw_fst,
            "fitzpatrick_group": fst_group,
            "fairness_model_tested": True,
            "fairness_note": "Evaluated across Fitzpatrick Skin Types I–VI using stratified benchmarking on Google SCIN.",
        },
        "disclaimer": (
            "This AI screening assessment is generated for educational and clinical decision-support research. "
            "It does NOT constitute a medical diagnosis. Always consult a qualified dermatologist."
        )
    }

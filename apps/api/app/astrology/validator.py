"""
Astrology Response Validator

Strict verification layer ensuring the language model has not hallucinated
any planetary placements, houses, or Yogas.
"""

import re
from typing import Any, Dict, List, Tuple

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]


def validate_reading_placements(
    text: str,
    chart: Dict[str, Any],
    rules: Dict[str, Any],
    report_type: str | None = None
) -> Tuple[bool, List[str]]:
    """
    Validates that:
    1. No incorrect planet-sign pairings are mentioned (e.g., "Sun in Taurus" when Sun is in Aries).
    2. No incorrect planet-house pairings are mentioned (e.g., "Mars in 5th house" when Mars is in 7th).
    3. No hallucinated Yogas/Doshas are stated (e.g., Gaja Kesari Yoga mentioned but not present in rules).
    """
    errors: List[str] = []
    text_lower = text.lower()

    # --- 1. Validate Sign Placements ---
    # Look for patterns like "sun in aries", "sun is in aries", "sun placed in aries"
    planets = chart["planets"]
    for planet_name, data in planets.items():
        actual_sign = data["sign"].lower()
        
        # Check if the text contains any other sign associated with this planet
        for other_sign in SIGN_NAMES:
            other_sign_lower = other_sign.lower()
            if other_sign_lower == actual_sign:
                continue
                
            # Create regex for '[planet] ... [other_sign]' in proximity
            # e.g., 'sun is placed in taurus', 'sun in the sign of taurus'
            pattern = re.compile(rf"\b{planet_name}\b\s+(?:is\s+)?(?:placed\s+)?(?:in\s+)?(?:the\s+sign\s+of\s+)?\b{other_sign_lower}\b", re.IGNORECASE)
            if pattern.search(text_lower):
                errors.append(
                    f"Hallucination detected: Text mentions '{planet_name.capitalize()} in {other_sign}', "
                    f"but calculated placement is '{planet_name.capitalize()} in {data['sign']}'."
                )

    # --- 2. Validate House Placements ---
    # Look for patterns like "sun in the 5th", "sun in 5th", "sun in the fifth"
    house_words = {
        "1": ["1st", "first", "1"],
        "2": ["2nd", "second", "2"],
        "3": ["3rd", "third", "3"],
        "4": ["4th", "fourth", "4"],
        "5": ["5th", "fifth", "5"],
        "6": ["6th", "sixth", "6"],
        "7": ["7th", "seventh", "7"],
        "8": ["8th", "eighth", "8"],
        "9": ["9th", "ninth", "9"],
        "10": ["10th", "tenth", "10"],
        "11": ["11th", "eleventh", "11"],
        "12": ["12th", "twelfth", "12"],
    }

    for planet_name, data in planets.items():
        actual_house = str(data["house"])
        
        # Check if text associates other houses with this planet
        for other_house, keywords in house_words.items():
            if other_house == actual_house:
                continue
                
            for kw in keywords:
                # E.g. 'sun in 5th', 'sun in the 5th', 'sun placed in the fifth'
                pattern = re.compile(rf"\b{planet_name}\b\s+(?:is\s+)?(?:placed\s+)?(?:in\s+)?(?:the\s+)?\b{kw}\b", re.IGNORECASE)
                if pattern.search(text_lower):
                    errors.append(
                        f"Hallucination detected: Text implies '{planet_name.capitalize()} in house {other_house}', "
                        f"but calculated position is in house {actual_house}."
                    )

    # --- 3. Validate Yogas and Doshas ---
    # Verify that if any traditional Yogas or Doshas are mentioned, they are calculated as active
    yoga_keywords = {
        "gaja kesari": "Gaja Kesari Yoga (Jupiter in Kendra from Moon)",
        "ruchaka": "Ruchaka Yoga (Pancha Mahapurusha)",
        "bhadra": "Bhadra Yoga (Pancha Mahapurusha)",
        "hamsa": "Hamsa Yoga (Pancha Mahapurusha)",
        "malavya": "Malavya Yoga (Pancha Mahapurusha)",
        "sasa": "Sasa Yoga (Pancha Mahapurusha)",
        "manglik": "Manglik Dosha",
        "kaal sarp": "Kaal Sarp Dosha",
    }

    calculated_yoga_names = [y.lower() for y in rules["yogas"]]
    calculated_dosha_names = [d.lower() for d in rules["doshas"]]
    all_calculated = calculated_yoga_names + calculated_dosha_names

    for kw, full_name in yoga_keywords.items():
        # Check if the text mentions this yoga
        if kw in text_lower:
            # Check if this yoga matches any calculated yoga/dosha
            is_active = any(kw in cy for cy in all_calculated)
            if not is_active:
                errors.append(
                    f"Hallucination detected: Text references '{full_name}', "
                    f"but this yoga/dosha was NOT calculated in the birth chart."
                )

    # --- 4. Validate Numerical Scores ---
    # Ensure that the pre-calculated numerical scores are represented in the output text
    scores = rules.get("scores", {})
    
    # Filter checked scores based on the report type to avoid over-enforcing unrelated metrics
    scores_to_check = list(scores.keys())
    if report_type:
        report_type_lower = report_type.lower()
        if report_type_lower == "career":
            scores_to_check = ["career", "wealth"]
        elif report_type_lower == "health":
            scores_to_check = ["vitality", "mental_peace"]
        elif report_type_lower in ["love", "marriage", "remedies", "annual-forecast", "weekly-forecast"]:
            scores_to_check = []  # Relationship/Remedy/Forecast reports do not focus on these individual natal scores
        elif report_type_lower == "life-guidance":
            scores_to_check = ["vitality", "mental_peace", "career", "wealth"]
        elif report_type_lower == "personality":
            scores_to_check = ["vitality", "mental_peace"]

    for metric_name in scores_to_check:
        if metric_name in scores:
            score_val = scores[metric_name]
            score_str = str(score_val)
            if score_str not in text:
                errors.append(
                    f"Hallucination/Misalignment detected: Pre-calculated {metric_name.capitalize()} score of {score_val} is missing from the report. "
                    f"Ensure you display the exact pre-calculated score: {score_val}/100."
                )

    return len(errors) == 0, errors

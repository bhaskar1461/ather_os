"""
Vedic Astrology Rule Engine

Calculates Vedic astrological attributes, including Nakshatras, divisional charts,
aspects, Vimshottari Dashas, and Yogas/Doshas based on calculated planetary longitudes.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

NAKSHATRAS = [
    {"name": "Ashwini", "lord": "ketu"},
    {"name": "Bharani", "lord": "venus"},
    {"name": "Krittika", "lord": "sun"},
    {"name": "Rohini", "lord": "moon"},
    {"name": "Mrigashira", "lord": "mars"},
    {"name": "Ardra", "lord": "rahu"},
    {"name": "Punarvasu", "lord": "jupiter"},
    {"name": "Pushya", "lord": "saturn"},
    {"name": "Ashlesha", "lord": "mercury"},
    {"name": "Magha", "lord": "ketu"},
    {"name": "Purva Phalguni", "lord": "venus"},
    {"name": "Uttara Phalguni", "lord": "sun"},
    {"name": "Hasta", "lord": "moon"},
    {"name": "Chitra", "lord": "mars"},
    {"name": "Swati", "lord": "rahu"},
    {"name": "Vishakha", "lord": "jupiter"},
    {"name": "Anuradha", "lord": "saturn"},
    {"name": "Jyeshtha", "lord": "mercury"},
    {"name": "Mula", "lord": "ketu"},
    {"name": "Purva Ashadha", "lord": "venus"},
    {"name": "Uttara Ashadha", "lord": "sun"},
    {"name": "Shravana", "lord": "moon"},
    {"name": "Dhanishta", "lord": "mars"},
    {"name": "Shatabhisha", "lord": "rahu"},
    {"name": "Purva Bhadrapada", "lord": "jupiter"},
    {"name": "Uttara Bhadrapada", "lord": "saturn"},
    {"name": "Revati", "lord": "mercury"},
]

DASHA_LORDS = ["ketu", "venus", "sun", "moon", "mars", "rahu", "jupiter", "saturn", "mercury"]
DASHA_YEARS = {
    "ketu": 7,
    "venus": 20,
    "sun": 6,
    "moon": 10,
    "mars": 7,
    "rahu": 18,
    "jupiter": 16,
    "saturn": 19,
    "mercury": 17,
}

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Planetary exaltation and debilitation signs (deep exaltation degrees in parentheses)
EXALTATIONS = {
    "sun": {"sign": "Aries", "sign_index": 0, "degree": 10},
    "moon": {"sign": "Taurus", "sign_index": 1, "degree": 3},
    "mars": {"sign": "Capricorn", "sign_index": 9, "degree": 28},
    "mercury": {"sign": "Virgo", "sign_index": 5, "degree": 15},
    "jupiter": {"sign": "Cancer", "sign_index": 3, "degree": 5},
    "venus": {"sign": "Pisces", "sign_index": 11, "degree": 27},
    "saturn": {"sign": "Libra", "sign_index": 6, "degree": 20},
}

OWN_SIGNS = {
    "sun": [4],          # Leo
    "moon": [3],         # Cancer
    "mars": [0, 7],      # Aries, Scorpio
    "mercury": [2, 5],   # Gemini, Virgo
    "jupiter": [8, 11],  # Sagittarius, Pisces
    "venus": [1, 6],     # Taurus, Libra
    "saturn": [9, 10],   # Capricorn, Aquarius
}


def get_nakshatra(longitude: float) -> Dict[str, Any]:
    """
    Calculate Nakshatra, Pada, and Lord from sidereal longitude.
    """
    nak_span = 360.0 / 27.0  # 13°20' = 13.3333 degrees
    nak_idx = int(longitude // nak_span) % 27
    progress = longitude % nak_span
    pada = int(progress // (nak_span / 4.0)) + 1
    
    nak_info = NAKSHATRAS[nak_idx]
    
    return {
        "name": nak_info["name"],
        "index": nak_idx,
        "lord": nak_info["lord"],
        "pada": pada,
        "progress_percent": round((progress / nak_span) * 100, 2),
    }


def get_divisional_chart_placements(planets: Dict[str, Any], division: int) -> Dict[str, str]:
    """
    Derive sign placements for divisional charts.
    Supports D9 Navamsa, D10 Dashamsa, and D3 Drekkana.
    """
    divisional_placements: Dict[str, str] = {}

    for name, data in planets.items():
        if name in ["rahu", "ketu"]:
            # Standard nodes mapping
            pass
            
        rel_deg = data["degrees"]
        sign_idx = data["sign_index"]

        if division == 9:
            # Navamsa (D9)
            div_span = 30.0 / 9.0  # 3°20'
            div_idx = int(rel_deg // div_span)
            
            # Starting sign based on element group
            element_group = sign_idx % 4
            if element_group == 0:    # Fire (Aries, Leo, Sagittarius) -> starts at Aries (0)
                starting_sign = 0
            elif element_group == 1:  # Earth (Taurus, Virgo, Capricorn) -> starts at Capricorn (9)
                starting_sign = 9
            elif element_group == 2:  # Air (Gemini, Libra, Aquarius) -> starts at Libra (6)
                starting_sign = 6
            else:                     # Water (Cancer, Scorpio, Pisces) -> starts at Cancer (3)
                starting_sign = 3
                
            pl_sign_idx = (starting_sign + div_idx) % 12
            divisional_placements[name] = SIGN_NAMES[pl_sign_idx]

        elif division == 3:
            # Drekkana (D3)
            # 3 divisions of 10 degrees each
            div_idx = int(rel_deg // 10.0)
            # Starts in own sign, then 5th sign, then 9th sign
            pl_sign_idx = (sign_idx + (div_idx * 4)) % 12
            divisional_placements[name] = SIGN_NAMES[pl_sign_idx]

        elif division == 10:
            # Dashamsa (D10)
            # 10 divisions of 3 degrees each
            div_idx = int(rel_deg // 3.0)
            # Odd signs start in sign itself, Even signs start in 9th sign
            is_odd = sign_idx % 2 == 0  # 0-indexed: 0 (Aries) is odd
            if is_odd:
                pl_sign_idx = (sign_idx + div_idx) % 12
            else:
                pl_sign_idx = ((sign_idx + 8) + div_idx) % 12
            divisional_placements[name] = SIGN_NAMES[pl_sign_idx]

    return divisional_placements


def calculate_vimshottari_dasha(moon_longitude: float, birth_date: datetime) -> List[Dict[str, Any]]:
    """
    Calculate Vimshottari Dasha timeline for 120 years from birth.
    """
    nak_span = 360.0 / 27.0
    progress = moon_longitude % nak_span
    nak_idx = int(moon_longitude // nak_span) % 27
    
    # Starting Nakshatra lord
    start_lord = NAKSHATRAS[nak_idx]["lord"]
    start_lord_idx = DASHA_LORDS.index(start_lord)
    
    # Calculate balance of dasha remaining at birth
    remaining_ratio = 1.0 - (progress / nak_span)
    total_start_years = DASHA_YEARS[start_lord]
    remaining_years = total_start_years * remaining_ratio
    
    dasha_timeline: List[Dict[str, Any]] = []
    current_date = birth_date
    
    # Loop to fill the 120 years span starting with the birth lord
    idx_offset = 0
    while len(dasha_timeline) < 9:
        lord_idx = (start_lord_idx + idx_offset) % 9
        lord_name = DASHA_LORDS[lord_idx]
        
        # Calculate duration of this dasha period
        if idx_offset == 0:
            duration_years = remaining_years
        else:
            duration_years = DASHA_YEARS[lord_name]
            
        end_date = current_date + timedelta(days=int(duration_years * 365.25))
        
        # Sub-dashas (Antardashas) calculations
        sub_periods = []
        antardasha_current_date = current_date
        for sub_offset in range(9):
            sub_lord_idx = (lord_idx + sub_offset) % 9
            sub_lord_name = DASHA_LORDS[sub_lord_idx]
            
            # Sub dasha proportion = (Main Lord years / 120) * Sub Lord years
            sub_duration_years = (DASHA_YEARS[lord_name] / 120.0) * DASHA_YEARS[sub_lord_name]
            # Adjust starting sub dasha duration for birth lord
            if idx_offset == 0:
                sub_duration_years *= remaining_ratio
                
            antardasha_end_date = antardasha_current_date + timedelta(days=int(sub_duration_years * 365.25))
            sub_periods.append({
                "lord": sub_lord_name,
                "start": antardasha_current_date.strftime("%Y-%m-%d"),
                "end": antardasha_end_date.strftime("%Y-%m-%d"),
            })
            antardasha_current_date = antardasha_end_date

        dasha_timeline.append({
            "lord": lord_name,
            "start": current_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "antardashas": sub_periods,
        })
        current_date = end_date
        idx_offset += 1

    return dasha_timeline


def detect_yogas_and_doshas(planets: Dict[str, Any], asc_sign_idx: int) -> Tuple[List[str], List[str]]:
    """
    Analyze placements and detect standard Vedic Yogas and Doshas.
    """
    yogas = []
    doshas = []

    # Whole sign house numbers mapping for quick queries
    planet_houses = {name: data["house"] for name, data in planets.items()}
    planet_signs = {name: data["sign_index"] for name, data in planets.items()}

    # 1. Gaja Kesari Yoga
    # Jupiter is in a Kendra (1st, 4th, 7th, 10th house) from the Moon
    moon_house = planet_houses["moon"]
    jupiter_house = planet_houses["jupiter"]
    house_distance = (jupiter_house - moon_house) % 12 + 1
    if house_distance in [1, 4, 7, 10]:
        yogas.append("Gaja Kesari Yoga (Jupiter in Kendra from Moon)")

    # 2. Manglik Dosha (Kuja Dosha)
    # Mars in 1, 4, 7, 8, or 12 house from Lagna
    mars_house = planet_houses["mars"]
    if mars_house in [1, 4, 7, 8, 12]:
        doshas.append("Manglik Dosha (Mars in house " + str(mars_house) + ")")

    # 3. Pancha Mahapurusha Yogas
    # Mars, Mercury, Jupiter, Venus, or Saturn in own sign or exaltation sign AND in a Kendra (1, 4, 7, 10)
    kendra_planets = ["mars", "mercury", "jupiter", "venus", "saturn"]
    for name in kendra_planets:
        house = planet_houses[name]
        sign_idx = planet_signs[name]
        
        # Check own sign or exalted
        is_own = sign_idx in OWN_SIGNS[name]
        is_exalted = EXALTATIONS[name]["sign_index"] == sign_idx
        
        if (is_own or is_exalted) and house in [1, 4, 7, 10]:
            yoga_names = {
                "mars": "Ruchaka Yoga",
                "mercury": "Bhadra Yoga",
                "jupiter": "Hamsa Yoga",
                "venus": "Malavya Yoga",
                "saturn": "Sasa Yoga"
            }
            yogas.append(f"{yoga_names[name]} (Pancha Mahapurusha)")

    # 4. Combustion check
    # Planet combust if too close to Sun
    sun_lon = planets["sun"]["longitude"]
    combust_thresholds = {
        "moon": 12.0, "mars": 17.0, "mercury": 14.0,
        "jupiter": 11.0, "venus": 10.0, "saturn": 15.0
    }
    for name, threshold in combust_thresholds.items():
        lon = planets[name]["longitude"]
        dist = min((lon - sun_lon) % 360, (sun_lon - lon) % 360)
        if dist < threshold:
            doshas.append(f"Combust {name.capitalize()} (within {round(dist, 1)}° of Sun)")

    return yogas, doshas


SIGN_RULERS = [
    "mars", "venus", "mercury", "moon", "sun", "mercury",
    "venus", "mars", "jupiter", "saturn", "saturn", "jupiter"
]


def check_aspect_or_conjunction(planets: Dict[str, Any], source_planet: str, target_house: int) -> bool:
    """Check if source_planet is in target_house or aspects target_house."""
    if source_planet not in planets:
        return False
    source_house = planets[source_planet]["house"]
    if source_house == target_house:
        return True
    
    # 7th aspect (opposition) is standard for all planets
    if (source_house + 6 - 1) % 12 + 1 == target_house:
        return True
        
    # Special aspects
    if source_planet == "mars":
        # Mars aspects 4th and 8th houses
        if (source_house + 3 - 1) % 12 + 1 == target_house:
            return True
        if (source_house + 7 - 1) % 12 + 1 == target_house:
            return True
    elif source_planet == "jupiter":
        # Jupiter aspects 5th and 9th houses
        if (source_house + 4 - 1) % 12 + 1 == target_house:
            return True
        if (source_house + 8 - 1) % 12 + 1 == target_house:
            return True
    elif source_planet == "saturn":
        # Saturn aspects 3rd and 10th houses
        if (source_house + 2 - 1) % 12 + 1 == target_house:
            return True
        if (source_house + 9 - 1) % 12 + 1 == target_house:
            return True
            
    return False


def is_planet_combust(planets: Dict[str, Any], name: str) -> bool:
    """Determine if a planet is too close to the Sun (combust)."""
    if name not in planets or name == "sun" or name in ["rahu", "ketu"]:
        return False
    sun_lon = planets["sun"]["longitude"]
    combust_thresholds = {
        "moon": 12.0, "mars": 17.0, "mercury": 14.0,
        "jupiter": 11.0, "venus": 10.0, "saturn": 15.0
    }
    threshold = combust_thresholds.get(name, 15.0)
    lon = planets[name]["longitude"]
    dist = min((lon - sun_lon) % 360, (sun_lon - lon) % 360)
    return dist < threshold


def get_planet_dignity_base_score(planet_name: str, sign_idx: int) -> int:
    """Base strength value based on planetary dignity (exaltation, own sign, etc.)."""
    if planet_name in ["rahu", "ketu"]:
        return 65
    if EXALTATIONS[planet_name]["sign_index"] == sign_idx:
        return 85
    elif (EXALTATIONS[planet_name]["sign_index"] + 6) % 12 == sign_idx:
        return 35
    elif sign_idx in OWN_SIGNS[planet_name]:
        return 75
    else:
        return 60


def calculate_vitality_score(planets: Dict[str, Any], asc_sign_idx: int) -> int:
    """Calculate Lagna Lord strength (Self & Vitality indicator)."""
    lagna_lord = SIGN_RULERS[asc_sign_idx]
    lord_data = planets.get(lagna_lord, {})
    if not lord_data:
        return 50
        
    sign_idx = lord_data["sign_index"]
    score = get_planet_dignity_base_score(lagna_lord, sign_idx)
    
    # House placement
    house = lord_data["house"]
    if house in [1, 4, 7, 10, 5, 9]:
        score += 15
    elif house in [6, 8, 12]:
        score -= 15
        
    # Combust/Retrograde
    if is_planet_combust(planets, lagna_lord):
        score -= 10
    if lord_data.get("is_retrograde", False):
        score -= 5
        
    # Benefic aspects on Lagna Lord or Lagna (1st house)
    for b in ["jupiter", "venus", "mercury"]:
        if check_aspect_or_conjunction(planets, b, house) or check_aspect_or_conjunction(planets, b, 1):
            score += 8
    for m in ["saturn", "mars", "rahu", "ketu"]:
        if check_aspect_or_conjunction(planets, m, house) or check_aspect_or_conjunction(planets, m, 1):
            score -= 8
            
    return max(10, min(100, score))


def calculate_mental_peace_score(planets: Dict[str, Any], asc_sign_idx: int) -> int:
    """Calculate Moon and 4th house strengths (Mental Peace indicator)."""
    moon_data = planets.get("moon", {})
    if not moon_data:
        return 50
    moon_sign_idx = moon_data["sign_index"]
    moon_base = get_planet_dignity_base_score("moon", moon_sign_idx)
    
    lord_4th = SIGN_RULERS[(asc_sign_idx + 3) % 12]
    lord_4th_data = planets.get(lord_4th, {})
    lord_4th_sign_idx = lord_4th_data.get("sign_index", 0) if lord_4th_data else 0
    lord_4th_base = get_planet_dignity_base_score(lord_4th, lord_4th_sign_idx)
    
    score = int((moon_base + lord_4th_base) / 2)
    
    # 4th lord house placement
    lord_4th_house = lord_4th_data.get("house", 4) if lord_4th_data else 4
    if lord_4th_house in [1, 4, 7, 10, 5, 9]:
        score += 10
    elif lord_4th_house in [6, 8, 12]:
        score -= 10
        
    # Moon house placement
    moon_house = moon_data["house"]
    if moon_house in [1, 4, 7, 10, 5, 9]:
        score += 10
    elif moon_house in [6, 8, 12]:
        score -= 15
        
    # Aspects on Moon and 4th house
    for b in ["jupiter", "venus", "mercury"]:
        if check_aspect_or_conjunction(planets, b, moon_house) or check_aspect_or_conjunction(planets, b, 4):
            score += 8
    for m in ["saturn", "mars", "rahu", "ketu"]:
        if check_aspect_or_conjunction(planets, m, moon_house) or check_aspect_or_conjunction(planets, m, 4):
            score -= 8
            
    return max(10, min(100, score))


def calculate_career_score(planets: Dict[str, Any], asc_sign_idx: int, d10_dashamsa: Dict[str, str]) -> int:
    """Calculate 10th house, Lord, and D-10 alignments (Career Potential indicator)."""
    lord_10th = SIGN_RULERS[(asc_sign_idx + 9) % 12]
    lord_10th_data = planets.get(lord_10th, {})
    if not lord_10th_data:
        return 50
    lord_10th_sign_idx = lord_10th_data.get("sign_index", 0)
    score = get_planet_dignity_base_score(lord_10th, lord_10th_sign_idx)
    
    # 10th Lord house placement
    house = lord_10th_data.get("house", 10)
    if house in [1, 4, 7, 10, 5, 9, 11]:
        score += 15
    elif house in [6, 8, 12]:
        score -= 15
        
    # Divisional D-10 Boost
    if d10_dashamsa and lord_10th in d10_dashamsa:
        d10_sign_name = d10_dashamsa[lord_10th]
        try:
            d10_sign_idx = SIGN_NAMES.index(d10_sign_name)
            if EXALTATIONS[lord_10th]["sign_index"] == d10_sign_idx:
                score += 15
            elif d10_sign_idx in OWN_SIGNS[lord_10th]:
                score += 10
            elif (EXALTATIONS[lord_10th]["sign_index"] + 6) % 12 == d10_sign_idx:
                score -= 15
        except ValueError:
            pass
            
    # Occupations/aspects of 10th house
    for name, data in planets.items():
        if name == "sun" or name == "mars" or name in ["jupiter", "venus", "mercury"]:
            if data["house"] == 10:
                score += 10
        elif name in ["saturn", "rahu", "ketu"]:
            if data["house"] == 10:
                score -= 5
                
    return max(10, min(100, score))


def calculate_wealth_score(planets: Dict[str, Any], asc_sign_idx: int) -> int:
    """Calculate 2nd house, 11th house, and Dhana Yogas (Wealth Capacity indicator)."""
    lord_2nd = SIGN_RULERS[(asc_sign_idx + 1) % 12]
    lord_11th = SIGN_RULERS[(asc_sign_idx + 10) % 12]
    
    lord_2nd_data = planets.get(lord_2nd, {})
    lord_11th_data = planets.get(lord_11th, {})
    
    lord_2nd_sign_idx = lord_2nd_data.get("sign_index", 0) if lord_2nd_data else 0
    lord_11th_sign_idx = lord_11th_data.get("sign_index", 0) if lord_11th_data else 0
    
    base_2nd = get_planet_dignity_base_score(lord_2nd, lord_2nd_sign_idx)
    base_11th = get_planet_dignity_base_score(lord_11th, lord_11th_sign_idx)
    
    score = int((base_2nd + base_11th) / 2)
    
    # 2nd and 11th Lords house placements
    house_2nd = lord_2nd_data.get("house", 2) if lord_2nd_data else 2
    house_11th = lord_11th_data.get("house", 11) if lord_11th_data else 11
    
    if house_2nd in [1, 2, 5, 9, 11]:
        score += 10
    elif house_2nd in [6, 8, 12]:
        score -= 10
        
    if house_11th in [1, 2, 5, 9, 11]:
        score += 10
    elif house_11th in [6, 8, 12]:
        score -= 10
        
    # Dhana Yoga Connections (lords of 1, 2, 5, 9, 11 conjunct or aspecting)
    dhana_house_lords = [
        SIGN_RULERS[asc_sign_idx],                     # 1st lord
        SIGN_RULERS[(asc_sign_idx + 1) % 12],          # 2nd lord
        SIGN_RULERS[(asc_sign_idx + 4) % 12],          # 5th lord
        SIGN_RULERS[(asc_sign_idx + 8) % 12],          # 9th lord
        SIGN_RULERS[(asc_sign_idx + 10) % 12],         # 11th lord
    ]
    
    yoga_points = 0
    checked_pairs = set()
    for i, lord_a in enumerate(dhana_house_lords):
        for j, lord_b in enumerate(dhana_house_lords):
            if i >= j or lord_a == lord_b:
                continue
            pair = tuple(sorted([lord_a, lord_b]))
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)
            
            lord_b_house = planets.get(lord_b, {}).get("house", 0)
            if lord_b_house and check_aspect_or_conjunction(planets, lord_a, lord_b_house):
                yoga_points += 8
                
    score += min(24, yoga_points)
    
    # House occupations
    for name, data in planets.items():
        if data["house"] in [2, 11]:
            if name in ["jupiter", "venus", "mercury"]:
                score += 8
            elif name in ["saturn", "mars", "rahu", "ketu"]:
                score -= 8
                
    return max(10, min(100, score))


def evaluate_chart_rules(chart: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrap all Vedic evaluation rules.
    Runs divisional placements, Nakshatras, aspects, Vimshottari dasha, and Yogas.
    """
    planets = chart["planets"]
    asc_sign_idx = chart["ascendant"]["sign_index"]
    moon_lon = planets["moon"]["longitude"]
    
    # Parse birth date
    birth_details = chart["birth_details"]
    birth_dt = datetime(
        birth_details["year"],
        birth_details["month"],
        birth_details["day"],
        birth_details["hour"],
        birth_details["minute"]
    )

    # 1. Calculate Nakshatras for all planets
    nakshatras: Dict[str, Any] = {}
    for name, data in planets.items():
        nakshatras[name] = get_nakshatra(data["longitude"])

    # 2. Calculate Divisional Placements
    d9_navamsa = get_divisional_chart_placements(planets, 9)
    d10_dashamsa = get_divisional_chart_placements(planets, 10)
    d3_drekkana = get_divisional_chart_placements(planets, 3)

    # 3. Vimshottari Dasha periods
    dasha_periods = calculate_vimshottari_dasha(moon_lon, birth_dt)

    # 4. Yogas & Doshas
    yogas, doshas = detect_yogas_and_doshas(planets, asc_sign_idx)

    # 5. Planetary Strengths
    strengths: Dict[str, str] = {}
    for name in planets.keys():
        if name in ["rahu", "ketu"]:
            continue
        sign_idx = planets[name]["sign_index"]
        if EXALTATIONS[name]["sign_index"] == sign_idx:
            strengths[name] = "Exalted"
        elif (EXALTATIONS[name]["sign_index"] + 6) % 12 == sign_idx:
            strengths[name] = "Debilitated"
        elif sign_idx in OWN_SIGNS[name]:
            strengths[name] = "Own Sign"
        else:
            strengths[name] = "Neutral"

    # 6. Calculate Numerical Scores
    scores = {
        "vitality": calculate_vitality_score(planets, asc_sign_idx),
        "mental_peace": calculate_mental_peace_score(planets, asc_sign_idx),
        "career": calculate_career_score(planets, asc_sign_idx, d10_dashamsa),
        "wealth": calculate_wealth_score(planets, asc_sign_idx),
    }

    return {
        "nakshatras": nakshatras,
        "divisional_charts": {
            "d9_navamsa": d9_navamsa,
            "d10_dashamsa": d10_dashamsa,
            "d3_drekkana": d3_drekkana,
        },
        "dashas": dasha_periods,
        "yogas": yogas,
        "doshas": doshas,
        "strengths": strengths,
        "scores": scores,
    }

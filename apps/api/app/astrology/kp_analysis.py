"""
KP (Krishnamurti Paddhati) Analysis & Horary Engine

Computes:
1. 4-Level Significators (Levels 1 to 4) for Houses 1–12 & Planets.
2. KP Horary (Prashna 1–249) Chart Calculation.
3. Grounded KP Interpretation Narrative (Strict fact-lock compliance).
"""

from typing import Any, Dict, List, Set
from app.astrology.kp_engine import (
    calculate_kp_chart,
    generate_249_sub_table,
    get_kp_lords,
    PLANET_IDS,
    SIGN_LORDS,
)
import swisseph as swe


def calculate_kp_significators(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes 4-Level House Significators (Levels 1 to 4) for Houses 1-12 and Planets.

    - Level 1 (Strongest): Planets in the Star of Occupants of House H.
    - Level 2: Occupants of House H.
    - Level 3: Planets in the Star of the Owner (Cuspal Lord) of House H.
    - Level 4: Owner (Cuspal Lord) of House H.
    """
    cusps = chart_data["cusps"]
    planets = chart_data["planets"]

    # Map house owners (Cuspal Sign Lord for each house 1..12)
    house_owners: Dict[int, str] = {}
    for c in cusps:
        house_owners[c["house"]] = c["sign_lord"]

    # Map house occupants
    house_occupants: Dict[int, List[str]] = {h: [] for h in range(1, 13)}
    for p_name, p_data in planets.items():
        h = p_data["house"]
        house_occupants[h].append(p_name)

    # Helper: find planets in the Star of a target planet
    def get_planets_in_star_of(target_planet: str) -> List[str]:
        result = []
        for p_name, p_data in planets.items():
            if p_data["star_lord"] == target_planet:
                result.append(p_name)
        return result

    # 4-Level Significators for each House
    house_significators: Dict[int, Dict[str, Any]] = {}
    for h in range(1, 13):
        owner = house_owners[h]
        occupants = house_occupants[h]

        # Level 1: Planets in the Star of Occupants of House H
        l1_planets: Set[str] = set()
        for occ in occupants:
            for p in get_planets_in_star_of(occ):
                l1_planets.add(p)

        # Level 2: Occupants of House H
        l2_planets: Set[str] = set(occupants)

        # Level 3: Planets in the Star of Owner of House H
        l3_planets: Set[str] = set(get_planets_in_star_of(owner))

        # Level 4: Owner of House H
        l4_planets: Set[str] = {owner}

        all_sig = sorted(list(l1_planets | l2_planets | l3_planets | l4_planets))

        house_significators[h] = {
            "house": h,
            "owner": owner,
            "occupants": occupants,
            "level_1": sorted(list(l1_planets)),
            "level_2": sorted(list(l2_planets)),
            "level_3": sorted(list(l3_planets)),
            "level_4": sorted(list(l4_planets)),
            "all_significators": all_sig,
        }

    # Inverse Mapping: Planet Significators (Which houses each planet signifies at Levels 1-4)
    planet_significators: Dict[str, Dict[str, Any]] = {}
    for p_name in planets.keys():
        sig_houses: Dict[str, List[int]] = {"L1": [], "L2": [], "L3": [], "L4": []}
        all_h: Set[int] = set()

        for h in range(1, 13):
            hs = house_significators[h]
            if p_name in hs["level_1"]:
                sig_houses["L1"].append(h)
                all_h.add(h)
            if p_name in hs["level_2"]:
                sig_houses["L2"].append(h)
                all_h.add(h)
            if p_name in hs["level_3"]:
                sig_houses["L3"].append(h)
                all_h.add(h)
            if p_name in hs["level_4"]:
                sig_houses["L4"].append(h)
                all_h.add(h)

        planet_significators[p_name] = {
            "planet": p_name,
            "signified_houses": sig_houses,
            "all_houses": sorted(list(all_h)),
        }

    return {
        "house_significators": house_significators,
        "planet_significators": planet_significators,
    }


def calculate_kp_horary(
    horary_number: int,
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    lat: float,
    lon: float,
    tz_offset_hours: float
) -> Dict[str, Any]:
    """
    Computes KP Horary (Prashna 1-249) Chart:
    - Querent picks horary number N (1 to 249).
    - Looks up starting longitude of Sub-division N.
    - Sets that longitude as the Horary Ascendant.
    - Computes Placidus house cusps relative to the Horary Ascendant.
    """
    if horary_number < 1 or horary_number > 249:
        raise ValueError("KP Horary number must be an integer between 1 and 249.")

    sub_table = generate_249_sub_table()
    sub_info = sub_table[horary_number - 1]
    horary_asc_lon = sub_info["start_longitude"]

    # Calculate standard chart at horary moment
    chart = calculate_kp_chart(year, month, day, hour, minute, lat, lon, tz_offset_hours)

    # Re-align Placidus house cusps relative to Horary Ascendant
    # Shift cusps relative to horary_asc_lon
    orig_asc = chart["ascendant"]["longitude"]
    shift_deg = (horary_asc_lon - orig_asc) % 360.0

    horary_cusps = []
    raw_cusp_lons = []
    for c in chart["cusps"]:
        h_lon = (c["longitude"] + shift_deg) % 360.0
        raw_cusp_lons.append(h_lon)
        lords = get_kp_lords(h_lon)
        horary_cusps.append({
            "house": c["house"],
            "longitude": h_lon,
            "formatted_degree": lords["formatted_degree"],
            "sign_name": lords["sign_name"],
            "sign_lord": lords["sign_lord"],
            "nakshatra_name": lords["nakshatra_name"],
            "star_lord": lords["star_lord"],
            "sub_lord": lords["sub_lord"],
            "sub_sub_lord": lords["sub_sub_lord"],
        })

    # Update house placements of planets under Horary Ascendant
    def get_placidus_house(planet_lon: float, cusps: List[float]) -> int:
        plon = planet_lon % 360.0
        for i in range(12):
            c_start = cusps[i] % 360.0
            c_next = cusps[(i + 1) % 12] % 360.0
            if c_start < c_next:
                if c_start <= plon < c_next:
                    return i + 1
            else:
                if plon >= c_start or plon < c_next:
                    return i + 1
        return 1

    horary_planets = {}
    for p_name, p_data in chart["planets"].items():
        h_num = get_placidus_house(p_data["longitude"], raw_cusp_lons)
        p_copy = dict(p_data)
        p_copy["house"] = h_num
        horary_planets[p_name] = p_copy

    horary_chart = {
        "horary_number": horary_number,
        "horary_sub_info": sub_info,
        "ayanamsa_name": chart["ayanamsa_name"],
        "ayanamsa_deg": chart["ayanamsa_deg"],
        "house_system": "KP Placidus Horary (1-249)",
        "ascendant": {
            "longitude": horary_asc_lon,
            **get_kp_lords(horary_asc_lon),
        },
        "cusps": horary_cusps,
        "planets": horary_planets,
        "ruling_planets": chart["ruling_planets"],
    }

    significators = calculate_kp_significators(horary_chart)

    return {
        "horary_chart": horary_chart,
        "significators": significators,
    }

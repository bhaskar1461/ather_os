"""
KP (Krishnamurti Paddhati) Astrology Calculation Engine

Computes precise KP planet longitudes, Placidus house cusps, 249 sub-divisions,
and Ruling Planets using Swiss Ephemeris (pyswisseph).

Conventions explicitly applied:
1. Ayanamsa: Krishnamurti Ayanamsa (swe.SIDM_KRISHNAMURTI = 5).
2. House System: Placidus Cusps (swe.houses_ex with b'P').
3. Sub-Lords: Proportional 9-fold Vimshottari division of each 13°20' Nakshatra.
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import swisseph as swe

# Vimshottari Dasha Sequence & Year Spans (Total 120 Years)
DASHA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS: Dict[str, float] = {
    "Ketu": 7.0,
    "Venus": 20.0,
    "Sun": 6.0,
    "Moon": 10.0,
    "Mars": 7.0,
    "Rahu": 18.0,
    "Jupiter": 16.0,
    "Saturn": 19.0,
    "Mercury": 17.0,
}

SIGN_LORDS = [
    "Mars",     # 0: Aries
    "Venus",    # 1: Taurus
    "Mercury",  # 2: Gemini
    "Moon",     # 3: Cancer
    "Sun",      # 4: Leo
    "Mercury",  # 5: Virgo
    "Venus",    # 6: Libra
    "Mars",     # 7: Scorpio
    "Jupiter",  # 8: Sagittarius
    "Saturn",   # 9: Capricorn
    "Saturn",   # 10: Aquarius
    "Jupiter",  # 11: Pisces
]

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Moola", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

WEEKDAY_LORDS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

PLANET_IDS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE,
}


def get_kp_lords(lon_deg: float) -> Dict[str, Any]:
    """
    Given a sidereal longitude (0° to 360°), returns:
    - Sign Index, Sign Name, Sign Lord
    - Nakshatra Name, Nakshatra Index, Star Lord
    - Sub Lord, Sub-Sub Lord
    - Position degrees/minutes format
    """
    lon_deg = lon_deg % 360.0
    sign_idx = int(lon_deg // 30.0)
    sign_name = SIGN_NAMES[sign_idx]
    sign_lord = SIGN_LORDS[sign_idx]

    rel_deg = lon_deg % 30.0
    deg_int = int(rel_deg)
    min_int = int((rel_deg - deg_int) * 60)

    lon_min = lon_deg * 60.0
    nak_idx = int(lon_min // 800.0)
    nak_name = NAKSHATRAS[nak_idx]
    star_lord_idx = nak_idx % 9
    star_lord = DASHA_ORDER[star_lord_idx]

    # Minutes elapsed inside current Nakshatra (0..800)
    nak_elapsed_min = lon_min % 800.0

    # Sub-lord & Sub-sub-lord search
    curr_min = 0.0
    sub_lord = star_lord
    sub_sub_lord = star_lord

    for i in range(9):
        p_idx = (star_lord_idx + i) % 9
        p_name = DASHA_ORDER[p_idx]
        p_span = (800.0 * DASHA_YEARS[p_name]) / 120.0  # minutes

        if curr_min + p_span >= nak_elapsed_min - 1e-9:
            sub_lord = p_name
            sub_start_min = curr_min
            
            # Find sub-sub lord within sub lord span
            sub_elapsed_min = nak_elapsed_min - sub_start_min
            sub_curr_min = 0.0
            for j in range(9):
                ss_idx = (p_idx + j) % 9
                ss_name = DASHA_ORDER[ss_idx]
                ss_span = (p_span * DASHA_YEARS[ss_name]) / 120.0
                if sub_curr_min + ss_span >= sub_elapsed_min - 1e-9:
                    sub_sub_lord = ss_name
                    break
                sub_curr_min += ss_span
            break
        curr_min += p_span

    return {
        "longitude": lon_deg,
        "sign_index": sign_idx,
        "sign_name": sign_name,
        "sign_lord": sign_lord,
        "formatted_degree": f"{deg_int}° {min_int:02d}' {sign_name}",
        "nakshatra_index": nak_idx,
        "nakshatra_name": nak_name,
        "star_lord": star_lord,
        "sub_lord": sub_lord,
        "sub_sub_lord": sub_sub_lord,
    }


def generate_249_sub_table() -> List[Dict[str, Any]]:
    """
    Generates the complete 249 Sub-division lookup table across 360° zodiac.
    Exact Vimshottari proportional division with sign boundary splitting.
    """
    table = []
    sub_number = 1

    for nak_idx in range(27):
        nak_name = NAKSHATRAS[nak_idx]
        star_lord_idx = nak_idx % 9
        star_lord = DASHA_ORDER[star_lord_idx]
        nak_start_min = nak_idx * 800.0

        curr_min = nak_start_min
        for sub_i in range(9):
            p_idx = (star_lord_idx + sub_i) % 9
            sub_lord = DASHA_ORDER[p_idx]
            sub_span_min = (800.0 * DASHA_YEARS[sub_lord]) / 120.0
            sub_end_min = curr_min + sub_span_min

            # Check if sign boundary (every 1800 minutes) falls strictly inside (curr_min, sub_end_min)
            sign_boundary = math.floor(curr_min / 1800.0 + 1e-9) + 1
            boundary_min = sign_boundary * 1800.0

            if curr_min < boundary_min < sub_end_min - 1e-6:
                # Split into 2 parts
                sign_idx1 = min(int(curr_min // 1800.0), 11)
                table.append({
                    "number": sub_number,
                    "start_longitude": curr_min / 60.0,
                    "end_longitude": boundary_min / 60.0,
                    "sign_name": SIGN_NAMES[sign_idx1],
                    "sign_lord": SIGN_LORDS[sign_idx1],
                    "nakshatra_name": nak_name,
                    "star_lord": star_lord,
                    "sub_lord": sub_lord,
                })
                sub_number += 1

                sign_idx2 = min(int(boundary_min // 1800.0), 11)
                table.append({
                    "number": sub_number,
                    "start_longitude": boundary_min / 60.0,
                    "end_longitude": min(sub_end_min / 60.0, 360.0),
                    "sign_name": SIGN_NAMES[sign_idx2],
                    "sign_lord": SIGN_LORDS[sign_idx2],
                    "nakshatra_name": nak_name,
                    "star_lord": star_lord,
                    "sub_lord": sub_lord,
                })
                sub_number += 1
            else:
                sign_idx = min(int(curr_min // 1800.0), 11)
                table.append({
                    "number": sub_number,
                    "start_longitude": curr_min / 60.0,
                    "end_longitude": min(sub_end_min / 60.0, 360.0),
                    "sign_name": SIGN_NAMES[sign_idx],
                    "sign_lord": SIGN_LORDS[sign_idx],
                    "nakshatra_name": nak_name,
                    "star_lord": star_lord,
                    "sub_lord": sub_lord,
                })
                sub_number += 1

            curr_min = sub_end_min

    return table


def calculate_kp_chart(
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
    Computes complete KP Birth Chart:
    - Krishnamurti Ayanamsa
    - Placidus House Cusps ('P')
    - KP Planet Table with Sign Lord, Star Lord, Sub Lord, Sub-Sub Lord
    - KP Cusps Table (1-12) with Sign Lord, Star Lord, Sub Lord
    - Ruling Planets
    """
    # 1. UTC Conversion & Julian Day
    local_dt = datetime(year, month, day, hour, minute)
    offset_seconds = int(tz_offset_hours * 3600)
    utc_timestamp = local_dt.timestamp() - offset_seconds
    utc_dt = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
    decimal_hour_utc = utc_dt.hour + (utc_dt.minute / 60.0) + (utc_dt.second / 3600.0)

    jd_ut = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, decimal_hour_utc)

    # 2. Configure Krishnamurti Ayanamsa (SIDM_KRISHNAMURTI = 5)
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
    calc_flags = swe.FLG_SIDEREAL | swe.FLG_SPEED

    ayanamsa_kp = swe.get_ayanamsa_ut(jd_ut)

    # 3. Calculate Placidus House Cusps (b'P')
    cusps_raw, ascmc = swe.houses_ex(jd_ut, lat, lon, b'P')
    ascendant_lon = ascmc[0]

    # Process Placidus Cusps (1 to 12)
    cusps_kp = []
    for h in range(1, 13):
        c_lon = cusps_raw[h - 1]
        lords = get_kp_lords(c_lon)
        cusps_kp.append({
            "house": h,
            "longitude": c_lon,
            "formatted_degree": lords["formatted_degree"],
            "sign_name": lords["sign_name"],
            "sign_lord": lords["sign_lord"],
            "nakshatra_name": lords["nakshatra_name"],
            "star_lord": lords["star_lord"],
            "sub_lord": lords["sub_lord"],
            "sub_sub_lord": lords["sub_sub_lord"],
        })

    # 4. Calculate Planets Longitudes & House Placements under Placidus
    def get_placidus_house(planet_lon: float, cusps: List[float]) -> int:
        plon = planet_lon % 360.0
        for i in range(12):
            c_start = cusps[i] % 360.0
            c_next = cusps[(i + 1) % 12] % 360.0

            if c_start < c_next:
                if c_start <= plon < c_next:
                    return i + 1
            else:  # Crosses 0° Aries
                if plon >= c_start or plon < c_next:
                    return i + 1
        return 1

    planets_kp = {}
    for name, pid in PLANET_IDS.items():
        res, _ = swe.calc_ut(jd_ut, pid, calc_flags)
        plon = res[0] % 360.0
        speed = res[3]
        lords = get_kp_lords(plon)
        house_num = get_placidus_house(plon, cusps_raw)

        planets_kp[name] = {
            "name": name,
            "longitude": plon,
            "speed": speed,
            "is_retrograde": speed < 0,
            "house": house_num,
            "formatted_degree": lords["formatted_degree"],
            "sign_name": lords["sign_name"],
            "sign_lord": lords["sign_lord"],
            "nakshatra_name": lords["nakshatra_name"],
            "star_lord": lords["star_lord"],
            "sub_lord": lords["sub_lord"],
            "sub_sub_lord": lords["sub_sub_lord"],
        }

    # Ketu (opposite Rahu)
    rahu_lon = planets_kp["Rahu"]["longitude"]
    ketu_lon = (rahu_lon + 180.0) % 360.0
    ketu_lords = get_kp_lords(ketu_lon)
    ketu_house = get_placidus_house(ketu_lon, cusps_raw)
    planets_kp["Ketu"] = {
        "name": "Ketu",
        "longitude": ketu_lon,
        "speed": planets_kp["Rahu"]["speed"],
        "is_retrograde": planets_kp["Rahu"]["is_retrograde"],
        "house": ketu_house,
        "formatted_degree": ketu_lords["formatted_degree"],
        "sign_name": ketu_lords["sign_name"],
        "sign_lord": ketu_lords["sign_lord"],
        "nakshatra_name": ketu_lords["nakshatra_name"],
        "star_lord": ketu_lords["star_lord"],
        "sub_lord": ketu_lords["sub_lord"],
        "sub_sub_lord": ketu_lords["sub_sub_lord"],
    }

    # 5. Ruling Planets
    # Weekday Lord: Sunday=Sun, Monday=Moon, Tuesday=Mars, Wednesday=Mercury, Thursday=Jupiter, Friday=Venus, Saturday=Saturn
    # Note: local_dt.weekday() in Python: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
    weekday_idx = (local_dt.weekday() + 1) % 7
    day_lord = WEEKDAY_LORDS[weekday_idx]

    asc_lords = get_kp_lords(ascendant_lon)
    moon_lords = get_kp_lords(planets_kp["Moon"]["longitude"])

    ruling_planets = {
        "day_lord": day_lord,
        "ascendant_sign_lord": asc_lords["sign_lord"],
        "ascendant_star_lord": asc_lords["star_lord"],
        "ascendant_sub_lord": asc_lords["sub_lord"],
        "moon_sign_lord": moon_lords["sign_lord"],
        "moon_star_lord": moon_lords["star_lord"],
        "moon_sub_lord": moon_lords["sub_lord"],
    }

    return {
        "ayanamsa_name": "Krishnamurti Ayanamsa",
        "ayanamsa_deg": ayanamsa_kp,
        "house_system": "Placidus Cusps (P)",
        "ascendant": {
            "longitude": ascendant_lon,
            **asc_lords,
        },
        "cusps": cusps_kp,
        "planets": planets_kp,
        "ruling_planets": ruling_planets,
    }

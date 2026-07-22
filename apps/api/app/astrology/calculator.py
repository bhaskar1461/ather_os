"""
Astrology Calculation Engine

Interfaces with Swiss Ephemeris (pyswisseph) to calculate precise sidereal (Lahiri)
planetary positions, speeds, ascendant, and house cusps.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Tuple
import swisseph as swe

# Constant mapping for planet names to Swiss Ephemeris IDs
PLANET_IDS = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mercury": swe.MERCURY,
    "venus": swe.VENUS,
    "mars": swe.MARS,
    "jupiter": swe.JUPITER,
    "saturn": swe.SATURN,
    "rahu": swe.MEAN_NODE,  # Mean node is standard in Vedic systems
}

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]


def local_to_utc(year: int, month: int, day: int, hour: int, minute: int, tz_offset_hours: float) -> Tuple[datetime, float]:
    """
    Convert a local birth time to UTC and calculate the decimal hour in UTC.
    """
    # Create local naive datetime
    local_dt = datetime(year, month, day, hour, minute)
    
    # Calculate UTC timestamp (offset is subtracted to get UTC)
    # E.g. IST (+5.5) -> local time 12:00 - 5.5 = 6:30 UTC
    offset_seconds = int(tz_offset_hours * 3600)
    utc_timestamp = local_dt.timestamp() - offset_seconds
    utc_dt = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
    
    # Decimal hour in UTC
    decimal_hour_utc = utc_dt.hour + (utc_dt.minute / 60.0) + (utc_dt.second / 3600.0)
    
    return utc_dt, decimal_hour_utc


def get_julian_day(utc_dt: datetime, decimal_hour_utc: float) -> float:
    """
    Calculate the Julian Day number for a given UTC date and decimal hour.
    """
    return swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        decimal_hour_utc
    )


def calculate_chart_data(
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
    Primary astronomical calculation engine using Swiss Ephemeris.
    Computes Lahiri sidereal longitudes of planets and houses.
    """
    # 1. Convert to UTC and get Julian Day
    utc_dt, decimal_hour_utc = local_to_utc(year, month, day, hour, minute, tz_offset_hours)
    jd_ut = get_julian_day(utc_dt, decimal_hour_utc)

    # 2. Configure Sidereal Calculations (Lahiri Ayanamsa)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    calc_flags = swe.FLG_SIDEREAL | swe.FLG_SPEED

    # 3. Calculate Ayanamsa offset
    ayanamsa = swe.get_ayanamsa_ut(jd_ut)

    # 4. Calculate Planets Longitudes
    planets_raw: Dict[str, Any] = {}
    for name, pid in PLANET_IDS.items():
        res, ret_flags = swe.calc_ut(jd_ut, pid, calc_flags)
        lon_sid = res[0]
        speed_sid = res[3]
        
        planets_raw[name] = {
            "longitude": lon_sid,
            "speed": speed_sid,
            "is_retrograde": speed_sid < 0,
        }

    # Derive Ketu (always exactly 180 degrees opposite Rahu)
    rahu_lon = planets_raw["rahu"]["longitude"]
    ketu_lon = (rahu_lon + 180.0) % 360.0
    # Ketu speed matches Rahu
    planets_raw["ketu"] = {
        "longitude": ketu_lon,
        "speed": planets_raw["rahu"]["speed"],
        "is_retrograde": planets_raw["rahu"]["is_retrograde"],
    }

    # 5. Calculate House Cusps and Ascendant (Lagna)
    # Whole Sign ('W') house system divides signs exactly from 0 to 30 degrees.
    cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b'W')
    ascendant_lon = ascmc[0]
    mc_lon = ascmc[1]

    # Map longitudes to sign indices (0-11) and relative degrees (0-30)
    def map_to_sign(longitude: float) -> Tuple[str, float, int]:
        sign_idx = int(longitude // 30) % 12
        rel_deg = longitude % 30
        return SIGN_NAMES[sign_idx], rel_deg, sign_idx

    # Format Ascendant details
    asc_sign, asc_deg, asc_sign_idx = map_to_sign(ascendant_lon)

    # Build planets coordinates mapping
    planets_mapped: Dict[str, Any] = {}
    for name, data in planets_raw.items():
        sign_name, rel_deg, sign_idx = map_to_sign(data["longitude"])
        
        # Determine current house placement (Whole Sign: relative to Ascendant's sign index)
        # Lagna sign index is asc_sign_idx (1st house).
        # Planet house = (planet_sign_idx - asc_sign_idx) % 12 + 1
        house_num = (sign_idx - asc_sign_idx) % 12 + 1

        planets_mapped[name] = {
            "longitude": data["longitude"],
            "speed": data["speed"],
            "is_retrograde": data["is_retrograde"],
            "sign": sign_name,
            "sign_index": sign_idx,
            "degrees": rel_deg,
            "house": house_num,
        }

    # Format houses (1 to 12) cusps under Whole Sign
    # Format houses (1 to 12) cusps under Whole Sign
    # House 1 is the sign containing the Ascendant
    houses_mapped: Dict[str, Any] = {}
    for h in range(1, 13):
        house_sign_idx = (asc_sign_idx + h - 1) % 12
        house_sign_name = SIGN_NAMES[house_sign_idx]
        # Whole Sign cusp starts at 0 degrees of that sign
        houses_mapped[str(h)] = {
            "sign": house_sign_name,
            "sign_index": house_sign_idx,
            "start_longitude": house_sign_idx * 30.0,
        }

    # Calculate key divisional charts (Vargas)
    def calculate_varga_placements(varga_num: int, planets: Dict[str, Any], asc_lon: float) -> Dict[str, Any]:
        def get_varga_sign_idx(lon: float) -> int:
            sign_idx = int(lon // 30) % 12
            rel_deg = lon % 30
            if varga_num == 1:
                return sign_idx
            elif varga_num == 9:
                div_idx = int(rel_deg // (30.0 / 9.0))
                elem_group = sign_idx % 4
                start = {0: 0, 1: 9, 2: 6, 3: 3}[elem_group]
                return (start + div_idx) % 12
            elif varga_num == 10:
                div_idx = int(rel_deg // 3.0)
                start = sign_idx if sign_idx % 2 == 0 else (sign_idx + 8) % 12
                return (start + div_idx) % 12
            elif varga_num == 7:
                div_idx = int(rel_deg // (30.0 / 7.0))
                start = sign_idx if sign_idx % 2 == 0 else (sign_idx + 6) % 12
                return (start + div_idx) % 12
            elif varga_num == 12:
                div_idx = int(rel_deg // 2.5)
                return (sign_idx + div_idx) % 12
            elif varga_num == 24:
                div_idx = int(rel_deg // 1.25)
                start = 4 if sign_idx % 2 == 0 else 3
                return (start + div_idx) % 12
            elif varga_num == 60:
                div_idx = int(rel_deg // 0.5)
                return (sign_idx * 2 + div_idx) % 12
            return sign_idx

        v_asc_idx = get_varga_sign_idx(asc_lon)
        v_planets = {}
        for p_name, p_data in planets.items():
            p_idx = get_varga_sign_idx(p_data["longitude"])
            v_planets[p_name] = {
                "sign": SIGN_NAMES[p_idx],
                "sign_index": p_idx,
                "house": (p_idx - v_asc_idx) % 12 + 1,
                "degrees": p_data["degrees"]
            }
        return {
            "ascendant": {
                "sign": SIGN_NAMES[v_asc_idx],
                "sign_index": v_asc_idx
            },
            "planets": v_planets
        }

    divisional_charts = {}
    for v in [7, 9, 10, 12, 24, 60]:
        divisional_charts[f"D{v}"] = calculate_varga_placements(v, planets_mapped, ascendant_lon)

    return {
        "julian_day": jd_ut,
        "ayanamsa_deg": ayanamsa,
        "ascendant": {
            "longitude": ascendant_lon,
            "sign": asc_sign,
            "sign_index": asc_sign_idx,
            "degrees": asc_deg,
        },
        "midheaven": mc_lon,
        "planets": planets_mapped,
        "houses": houses_mapped,
        "divisional_charts": divisional_charts,
        "birth_details": {
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "minute": minute,
            "lat": lat,
            "lon": lon,
            "tz_offset": tz_offset_hours,
        }
    }

"""
BaZi (Four Pillars of Destiny) Astronomical Calculation Engine

Computes exact Heavenly Stems, Earthly Branches, Hidden Stems (Cang Gan),
and sexagenary cycles using Swiss Ephemeris (pyswisseph) for precise
solar longitude ecliptic calculations.

Conventions & Boundaries explicitly applied:
1. Year Boundary: Begins at Lichun (立春, solar ecliptic longitude = 315.0°).
   Births before Lichun in early Gregorian year belong to the previous BaZi year.
2. Month Boundary: Bounded by the 12 principal solar terms (Jie Qi 節氣)
   based on exact solar ecliptic longitude (e.g. 315° Yin, 345° Mao, 0° Chen).
3. Day Boundary: Traditional Zi-Hour Shift (23:00 local time). Births between
   23:00 and 24:00 use the Day Stem and Day Branch of the next calendar day.
4. Hour Pillar: Hour branch by local time; Hour stem derived via Five Rats rule (五鼠遁).
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple
import swisseph as swe

# 10 Heavenly Stems (天干 Tiān Gān)
STEMS = [
    {"index": 0, "char": "甲", "pinyin": "Jiǎ", "element": "Wood", "polarity": "Yang"},
    {"index": 1, "char": "乙", "pinyin": "Yǐ", "element": "Wood", "polarity": "Yin"},
    {"index": 2, "char": "丙", "pinyin": "Bǐng", "element": "Fire", "polarity": "Yang"},
    {"index": 3, "char": "丁", "pinyin": "Dīng", "element": "Fire", "polarity": "Yin"},
    {"index": 4, "char": "戊", "pinyin": "Wù", "element": "Earth", "polarity": "Yang"},
    {"index": 5, "char": "己", "pinyin": "Jǐ", "element": "Earth", "polarity": "Yin"},
    {"index": 6, "char": "庚", "pinyin": "Gēng", "element": "Metal", "polarity": "Yang"},
    {"index": 7, "char": "辛", "pinyin": "Xīn", "element": "Metal", "polarity": "Yin"},
    {"index": 8, "char": "壬", "pinyin": "Rén", "element": "Water", "polarity": "Yang"},
    {"index": 9, "char": "癸", "pinyin": "Guǐ", "element": "Water", "polarity": "Yin"},
]

# 12 Earthly Branches (地支 Dì Zhī)
BRANCHES = [
    {"index": 0, "char": "子", "pinyin": "Zǐ", "zodiac": "Rat", "element": "Water", "polarity": "Yang"},
    {"index": 1, "char": "丑", "pinyin": "Chǒu", "zodiac": "Ox", "element": "Earth", "polarity": "Yin"},
    {"index": 2, "char": "寅", "pinyin": "Yín", "zodiac": "Tiger", "element": "Wood", "polarity": "Yang"},
    {"index": 3, "char": "卯", "pinyin": "Mǎo", "zodiac": "Rabbit", "element": "Wood", "polarity": "Yin"},
    {"index": 4, "char": "辰", "pinyin": "Chén", "zodiac": "Dragon", "element": "Earth", "polarity": "Yang"},
    {"index": 5, "char": "巳", "pinyin": "Sì", "zodiac": "Snake", "element": "Fire", "polarity": "Yin"},
    {"index": 6, "char": "午", "pinyin": "Wǔ", "zodiac": "Horse", "element": "Fire", "polarity": "Yang"},
    {"index": 7, "char": "未", "pinyin": "Wèi", "zodiac": "Goat", "element": "Earth", "polarity": "Yin"},
    {"index": 8, "char": "申", "pinyin": "Shēn", "zodiac": "Monkey", "element": "Metal", "polarity": "Yang"},
    {"index": 9, "char": "酉", "pinyin": "Yǒu", "zodiac": "Rooster", "element": "Metal", "polarity": "Yin"},
    {"index": 10, "char": "戌", "pinyin": "Xū", "zodiac": "Dog", "element": "Earth", "polarity": "Yang"},
    {"index": 11, "char": "亥", "pinyin": "Hài", "zodiac": "Pig", "element": "Water", "polarity": "Yin"},
]

# Hidden Stems (藏干 Cáng Gān) mapping for each branch index
# Each entry is a list of tuples: (stem_index, weight_percentage, role_name)
HIDDEN_STEMS_MAP: Dict[int, List[Tuple[int, float, str]]] = {
    0: [(9, 1.0, "Main")],                           # 子 Zi: Gui 100%
    1: [(5, 0.6, "Main"), (9, 0.3, "Middle"), (7, 0.1, "Residual")],  # 丑 Chou: Ji 60%, Gui 30%, Xin 10%
    2: [(0, 0.6, "Main"), (2, 0.3, "Middle"), (4, 0.1, "Residual")],  # 寅 Yin: Jia 60%, Bing 30%, Wu 10%
    3: [(1, 1.0, "Main")],                           # 卯 Mao: Yi 100%
    4: [(4, 0.6, "Main"), (1, 0.3, "Middle"), (9, 0.1, "Residual")],  # 辰 Chen: Wu 60%, Yi 30%, Gui 10%
    5: [(2, 0.6, "Main"), (4, 0.3, "Middle"), (6, 0.1, "Residual")],  # 巳 Si: Bing 60%, Wu 30%, Geng 10%
    6: [(3, 0.7, "Main"), (5, 0.3, "Middle")],       # 午 Wu: Ding 70%, Ji 30%
    7: [(5, 0.6, "Main"), (3, 0.3, "Middle"), (1, 0.1, "Residual")],  # 未 Wei: Ji 60%, Ding 30%, Yi 10%
    8: [(6, 0.6, "Main"), (8, 0.3, "Middle"), (4, 0.1, "Residual")],  # 申 Shen: Geng 60%, Ren 30%, Wu 10%
    9: [(7, 1.0, "Main")],                           # 酉 You: Xin 100%
    10: [(4, 0.6, "Main"), (7, 0.3, "Middle"), (3, 0.1, "Residual")], # 戌 Xu: Wu 60%, Xin 30%, Ding 10%
    11: [(8, 0.7, "Main"), (0, 0.3, "Middle")],      # 亥 Hai: Ren 70%, Jia 30%
}

# 12 Principal Solar Terms (Jie Qi 節氣) and their corresponding Month Branch index
# Ecliptic Solar Longitudes:
# Lichun (315°) -> Yin (Month branch 2)
# Jingzhe (345°) -> Mao (Month branch 3)
# Qingming (0°) -> Chen (Month branch 4)
# Lixia (15°) -> Si (Month branch 5)
# Mangzhong (45°) -> Wu (Month branch 6)
# Xiaoshu (75°) -> Wei (Month branch 7)
# Liqiu (105°) -> Shen (Month branch 8)
# Bailu (135°) -> You (Month branch 9)
# Hanlu (165°) -> Xu (Month branch 10)
# Lidong (195°) -> Hai (Month branch 11)
# Daxue (225°) -> Zi (Month branch 0)
# Xiaohan (255°) -> Chou (Month branch 1)


def get_solar_longitude(year: int, month: int, day: int, decimal_hour_utc: float) -> float:
    """Calculate tropical solar ecliptic longitude (0° to 360°) using Swiss Ephemeris."""
    jd = swe.julday(year, month, day, decimal_hour_utc)
    res, _ = swe.calc_ut(jd, swe.SUN, 0)
    return float(res[0]) % 360.0


def get_julian_day_number(year: int, month: int, day: int, decimal_hour_utc: float = 0.0) -> float:
    """Return Julian Day float using Swiss Ephemeris."""
    return float(swe.julday(year, month, day, decimal_hour_utc))


def get_bazi_month_branch(solar_lon: float) -> Tuple[int, str]:
    """
    Determine Month Branch index (0-11) and Solar Term Name based on solar ecliptic longitude.
    """
    # 315° to 345°: Lichun -> Yin (2)
    # 345° to 360° or 0° to 0°: Jingzhe -> Mao (3)
    # 0° to 15°: Qingming -> Chen (4)
    # 15° to 45°: Lixia -> Si (5)
    # 45° to 75°: Mangzhong -> Wu (6)
    # 75° to 105°: Xiaoshu -> Wei (7)
    # 105° to 135°: Liqiu -> Shen (8)
    # 135° to 165°: Bailu -> You (9)
    # 165° to 195°: Hanlu -> Xu (10)
    # 195° to 225°: Lidong -> Hai (11)
    # 225° to 255°: Daxue -> Zi (0)
    # 255° to 315°: Xiaohan -> Chou (1)

    lon = solar_lon % 360.0

    if 315.0 <= lon < 345.0:
        return 2, "Lichun (立春)"
    elif lon >= 345.0 or lon < 0.0: # 345° to 360°
        return 3, "Jingzhe (驚蟄)"
    elif 0.0 <= lon < 15.0:
        return 4, "Qingming (清明)"
    elif 15.0 <= lon < 45.0:
        return 5, "Lixia (立夏)"
    elif 45.0 <= lon < 75.0:
        return 6, "Mangzhong (芒種)"
    elif 75.0 <= lon < 105.0:
        return 7, "Xiaoshu (小暑)"
    elif 105.0 <= lon < 135.0:
        return 8, "Liqiu (立秋)"
    elif 135.0 <= lon < 165.0:
        return 9, "Bailu (白露)"
    elif 165.0 <= lon < 195.0:
        return 10, "Hanlu (寒露)"
    elif 195.0 <= lon < 225.0:
        return 11, "Lidong (立冬)"
    elif 225.0 <= lon < 255.0:
        return 0, "Daxue (大雪)"
    else:  # 255.0 <= lon < 315.0
        return 1, "Xiaohan (小寒)"


def calculate_bazi_pillars(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    lat: float = 0.0,
    lon: float = 0.0,
    tz_offset_hours: float = 0.0
) -> Dict[str, Any]:
    """
    Computes the BaZi Four Pillars (Year, Month, Day, Hour) with exact astronomical boundaries.
    """
    # 1. Local Datetime & Zi Hour Check
    local_dt = datetime(year, month, day, hour, minute)
    
    # Hour Branch determination (23:00-01:00 Zi, 01:00-03:00 Chou, etc.)
    # Note: 23:00 belongs to Zi hour (index 0)
    adjusted_hour = hour
    if minute >= 60:
        adjusted_hour += 1
    hour_branch_idx = ((adjusted_hour + 1) % 24) // 2

    # Zi-Hour Day Boundary Convention:
    # Births at 23:00 or later belong to Zi hour of the next day's Day Pillar
    day_calc_dt = local_dt
    if hour >= 23:
        day_calc_dt = local_dt + timedelta(days=1)

    # 2. UTC Conversion for Ephemeris Solar Longitude
    offset_seconds = int(tz_offset_hours * 3600)
    utc_timestamp = local_dt.timestamp() - offset_seconds
    utc_dt = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
    decimal_hour_utc = utc_dt.hour + (utc_dt.minute / 60.0) + (utc_dt.second / 3600.0)

    solar_lon = get_solar_longitude(utc_dt.year, utc_dt.month, utc_dt.day, decimal_hour_utc)

    # 3. Year Pillar Calculation
    # BaZi Year starts at Lichun (315° solar longitude).
    # If birth is in Jan/early Feb and solar longitude < 315°, solar BaZi year is year - 1.
    bazi_year = utc_dt.year
    if utc_dt.month in [1, 2] and solar_lon < 315.0 and solar_lon > 180.0:
        bazi_year = utc_dt.year - 1

    # Reference year: 1984 is Jia-Zi (Stem 0, Branch 0)
    year_offset = (bazi_year - 1984) % 60
    year_stem_idx = year_offset % 10
    year_branch_idx = year_offset % 12

    # 4. Month Pillar Calculation
    # Month branch determined directly by solar ecliptic longitude
    month_branch_idx, solar_term_name = get_bazi_month_branch(solar_lon)

    # Month stem via Five Tigers Rule (五虎遁):
    # Year Stem % 5 * 2 + 2 + (month_branch - 2) % 12
    # E.g. Jia/Ji year -> Month 1 (Yin, branch 2) stem is Bing (index 2).
    m_branch_dist = (month_branch_idx - 2) % 12
    month_stem_idx = ((year_stem_idx % 5) * 2 + 2 + m_branch_dist) % 10

    # 5. Day Pillar Calculation
    # Day Julian Day number using day_calc_dt (which applies 23:00 Zi-hour shift)
    jd_day = get_julian_day_number(day_calc_dt.year, day_calc_dt.month, day_calc_dt.day, 0.0)
    jd_int = int(jd_day + 0.5)
    # Sexagenary day index formula: (int(JD + 0.5) + 49) % 60
    day_sexagenary_idx = (jd_int + 49) % 60
    day_stem_idx = day_sexagenary_idx % 10
    day_branch_idx = day_sexagenary_idx % 12

    # 6. Hour Pillar Calculation
    # Hour branch_idx was determined above (0-11)
    # Hour stem via Five Rats Rule (五鼠遁):
    # If Day Stem is Jia/Ji (0/5) -> Zi hour stem is Jia (0)
    # If Day Stem is Yi/Geng (1/6) -> Zi hour stem is Bing (2)
    # If Day Stem is Bing/Xin (2/7) -> Zi hour stem is Wu (4)
    # If Day Stem is Ding/Ren (3/8) -> Zi hour stem is Geng (6)
    # If Day Stem is Wu/Gui (4/9) -> Zi hour stem is Ren (8)
    hour_stem_idx = ((day_stem_idx % 5) * 2 + hour_branch_idx) % 10

    # Helper function to structure a single pillar
    def format_pillar(stem_i: int, branch_i: int, pillar_name: str) -> Dict[str, Any]:
        hidden_stems_raw = HIDDEN_STEMS_MAP[branch_i]
        hidden_stems_formatted = []
        for h_stem_i, weight, role in hidden_stems_raw:
            hidden_stems_formatted.append({
                "stem": STEMS[h_stem_i],
                "weight": weight,
                "role": role,
            })

        return {
            "name": pillar_name,
            "stem": STEMS[stem_i],
            "branch": BRANCHES[branch_i],
            "hidden_stems": hidden_stems_formatted,
            "sexagenary_code": f"{STEMS[stem_i]['char']}{BRANCHES[branch_i]['char']}",
            "pinyin_code": f"{STEMS[stem_i]['pinyin']} {BRANCHES[branch_i]['pinyin']}",
        }

    year_pillar = format_pillar(year_stem_idx, year_branch_idx, "Year")
    month_pillar = format_pillar(month_stem_idx, month_branch_idx, "Month")
    day_pillar = format_pillar(day_stem_idx, day_branch_idx, "Day")
    hour_pillar = format_pillar(hour_stem_idx, hour_branch_idx, "Hour")

    return {
        "solar_longitude": solar_lon,
        "solar_term": solar_term_name,
        "bazi_year": bazi_year,
        "zi_hour_shifted": hour >= 23,
        "pillars": {
            "year": year_pillar,
            "month": month_pillar,
            "day": day_pillar,
            "hour": hour_pillar,
        },
        "day_master": STEMS[day_stem_idx],
        "zodiac_animal": BRANCHES[year_branch_idx]["zodiac"],
        "methodology": {
            "year_boundary": "Lichun (立春, 315° Solar Ecliptic Longitude)",
            "month_boundary": "12 Principal Solar Terms (Jie Qi 節氣)",
            "day_boundary": "Traditional Zi-Hour Shift (23:00 local time)",
            "hour_stem_rule": "Five Rats Method (五鼠遁)",
            "month_stem_rule": "Five Tigers Method (五虎遁)",
        }
    }

"""
BaZi Five Elements & Grounded Interpretation Analysis Engine

Computes:
1. Five Elements distribution (Wood, Fire, Earth, Metal, Water) with exact weights.
2. Day Master (日主) strength using ZiPing Seasonality & Support Method (子平得令法).
3. Ten Gods (十神 Shi Shen) for all 7 other stems and hidden stems relative to Day Master.
4. Useful Gods (用神 Yong Shen) & Unfavorable Gods (忌神 Ji Shen).
5. Grounded interpretation output where every claim directly references calculated placements.
"""

from typing import Any, Dict, List, Tuple

ELEMENT_NAMES = ["Wood", "Fire", "Earth", "Metal", "Water"]

# Element Production Cycle: Wood -> Fire -> Earth -> Metal -> Water -> Wood
ELEMENT_PRODUCES = {
    "Wood": "Fire",
    "Fire": "Earth",
    "Earth": "Metal",
    "Metal": "Water",
    "Water": "Wood",
}

# Element Overcoming Cycle: Wood -> Earth -> Water -> Fire -> Metal -> Wood
ELEMENT_OVERCOMES = {
    "Wood": "Earth",
    "Earth": "Water",
    "Water": "Fire",
    "Fire": "Metal",
    "Metal": "Wood",
}

# Reverse relationships
ELEMENT_PRODUCED_BY = {v: k for k, v in ELEMENT_PRODUCES.items()}
ELEMENT_OVERCOME_BY = {v: k for k, v in ELEMENT_OVERCOMES.items()}

TEN_GODS_MAP = {
    # (element_rel, polarity_match): (Chinese, Pinyin, English)
    ("same", True): ("比肩", "Bǐ Jiān", "Friend / Peer"),
    ("same", False): ("劫財", "Jié Cái", "Rob Wealth"),
    ("produced_by_dm", True): ("食神", "Shí Shén", "Eating God"),
    ("produced_by_dm", False): ("傷官", "Shāng Guān", "Hurting Officer"),
    ("overcome_by_dm", True): ("偏財", "Piān Cái", "Indirect Wealth"),
    ("overcome_by_dm", False): ("正財", "Zhèng Cái", "Direct Wealth"),
    ("overcomes_dm", True): ("七殺", "Qī Shā", "Seven Killings / Indirect Officer"),
    ("overcomes_dm", False): ("正官", "Zhèng Guān", "Direct Officer"),
    ("produces_dm", True): ("偏印", "Piān Yìn", "Indirect Resource"),
    ("produces_dm", False): ("正印", "Zhèng Yìn", "Direct Resource"),
}


def get_ten_god(dm_element: str, dm_polarity: str, target_element: str, target_polarity: str) -> Dict[str, str]:
    """Calculate the Ten God relationship of a target stem/element to the Day Master."""
    polarity_match = (dm_polarity == target_polarity)

    if target_element == dm_element:
        rel = "same"
    elif target_element == ELEMENT_PRODUCES[dm_element]:
        rel = "produced_by_dm"
    elif target_element == ELEMENT_OVERCOMES[dm_element]:
        rel = "overcome_by_dm"
    elif target_element == ELEMENT_OVERCOME_BY[dm_element]:
        rel = "overcomes_dm"
    elif target_element == ELEMENT_PRODUCED_BY[dm_element]:
        rel = "produces_dm"
    else:
        rel = "same"

    cn_char, pinyin, english = TEN_GODS_MAP[(rel, polarity_match)]
    return {
        "chinese": cn_char,
        "pinyin": pinyin,
        "english": english,
        "relationship_type": rel,
    }


def analyze_bazi_chart(chart_pillars_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes Five Elements balance, Day Master strength, 10 Gods, and produces grounded interpretations.
    """
    pillars = chart_pillars_data["pillars"]
    day_master = chart_pillars_data["day_master"]
    dm_element = day_master["element"]
    dm_polarity = day_master["polarity"]
    dm_char = day_master["char"]

    # 1. Five Elements Weighted Scoring across 4 Heavenly Stems + 4 Earthly Branches + Hidden Stems
    element_scores = {"Wood": 0.0, "Fire": 0.0, "Earth": 0.0, "Metal": 0.0, "Water": 0.0}
    element_counts = {"Wood": 0, "Fire": 0, "Earth": 0, "Metal": 0, "Water": 0}

    # Heavenly Stems: 1.0 point each
    for p_key in ["year", "month", "day", "hour"]:
        stem = pillars[p_key]["stem"]
        elem = stem["element"]
        element_scores[elem] += 1.0
        element_counts[elem] += 1

    # Earthly Branches & Hidden Stems: Branch main element 0.5, Hidden Stems weighted by their percentage
    for p_key in ["year", "month", "day", "hour"]:
        branch = pillars[p_key]["branch"]
        b_elem = branch["element"]
        element_counts[b_elem] += 1

        hidden_stems = pillars[p_key]["hidden_stems"]
        for h in hidden_stems:
            h_elem = h["stem"]["element"]
            h_weight = h["weight"]
            element_scores[h_elem] += h_weight

    total_score = sum(element_scores.values())
    element_percentages = {
        k: round((v / total_score) * 100.0, 1) if total_score > 0 else 0.0
        for k, v in element_scores.items()
    }

    # 2. Ten Gods Mapping for Heavenly Stems & Hidden Stems
    ten_gods_result = {}
    for p_key in ["year", "month", "hour"]: # Day Stem is DM itself
        stem = pillars[p_key]["stem"]
        god = get_ten_god(dm_element, dm_polarity, stem["element"], stem["polarity"])
        ten_gods_result[f"{p_key}_stem"] = {
            "target": f"{stem['char']} ({stem['pinyin']})",
            "element": stem["element"],
            "god": god
        }

    # Day Master Month Seasonality (得令 In-Season check)
    month_branch = pillars["month"]["branch"]
    month_elem = month_branch["element"]

    is_in_season = False
    season_desc = ""
    if month_elem == dm_element:
        is_in_season = True
        season_desc = f"In-Season (得令): Month branch {month_branch['char']} is {month_elem}, sharing Day Master's element."
    elif month_elem == ELEMENT_PRODUCED_BY[dm_element]:
        is_in_season = True
        season_desc = f"In-Season (得令): Month branch {month_branch['char']} is {month_elem}, producing Day Master's element {dm_element}."
    else:
        is_in_season = False
        season_desc = f"Out-of-Season (失令): Month branch {month_branch['char']} is {month_elem}, which drains or overcomes Day Master's element {dm_element}."

    # Supporting Score Calculation (Resource + Self/Peer elements)
    supporting_elements = [dm_element, ELEMENT_PRODUCED_BY[dm_element]]
    supporting_score = sum(element_scores[e] for e in supporting_elements)
    draining_score = total_score - supporting_score

    # Day Master Strength Assessment (ZiPing Rule)
    strength_category = "Balanced"
    if supporting_score >= total_score * 0.52:
        strength_category = "Strong (身強)"
    elif supporting_score <= total_score * 0.38:
        strength_category = "Weak (身弱)"
    else:
        strength_category = "Moderate / Balanced (中和)"

    # Useful Gods (Yong Shen 用神) & Unfavorable Gods (Ji Shen 忌神)
    if "Strong" in strength_category:
        # Strong DM prefers Output, Wealth, Officer to drain/regulate excess strength
        useful_elements = [ELEMENT_PRODUCES[dm_element], ELEMENT_OVERCOMES[dm_element], ELEMENT_OVERCOME_BY[dm_element]]
        unfavorable_elements = [dm_element, ELEMENT_PRODUCED_BY[dm_element]]
        strategy_desc = "Day Master is Strong. The optimal strategy is to drain or regulate energy using Output, Wealth, and Officer elements."
    else:
        # Weak DM prefers Resource and Peer elements for support
        useful_elements = [dm_element, ELEMENT_PRODUCED_BY[dm_element]]
        unfavorable_elements = [ELEMENT_OVERCOMES[dm_element], ELEMENT_OVERCOME_BY[dm_element], ELEMENT_PRODUCES[dm_element]]
        strategy_desc = "Day Master is Weak. The optimal strategy is to strengthen energy using Resource and Peer/Companion elements."

    # 3. Grounded Interpretation Narrative Generation
    # Every statement directly cites calculated values
    year_stem = pillars["year"]["stem"]
    year_branch = pillars["year"]["branch"]
    month_stem = pillars["month"]["stem"]
    day_stem = pillars["day"]["stem"]
    hour_stem = pillars["hour"]["stem"]
    hour_branch = pillars["hour"]["branch"]

    narrative = {
        "core_identity": (
            f"Your Day Master is {dm_char} ({day_stem['pinyin']}), representing {day_stem['polarity']} {dm_element}. "
            f"The Day Master represents your core self, fundamental temperament, and inner essence. "
            f"Under the ZiPing Seasonality assessment, your chart is evaluated as {strength_category}. {season_desc}"
        ),
        "elemental_balance": (
            f"Your 8-character chart composition contains weighted scores: "
            f"Wood {element_percentages['Wood']}%, Fire {element_percentages['Fire']}%, "
            f"Earth {element_percentages['Earth']}%, Metal {element_percentages['Metal']}%, and Water {element_percentages['Water']}%. "
            f"The dominant element in your chart is {max(element_percentages, key=element_percentages.get)} "
            f"({max(element_percentages.values())}% of total elemental weight)."
        ),
        "useful_god_guidance": (
            f"{strategy_desc} "
            f"Your primary Useful Elements (用神) are {', '.join(useful_elements)}. "
            f"Unfavorable Elements (忌神) that may create imbalance are {', '.join(unfavorable_elements)}."
        ),
        "four_pillars_breakdown": [
            {
                "pillar": "Year Pillar",
                "character": f"{year_stem['char']}{year_branch['char']} ({year_stem['pinyin']} {year_branch['pinyin']})",
                "focus": "Ancestral Heritage & Youth (Ages 0–16)",
                "significance": f"Year Stem is {year_stem['polarity']} {year_stem['element']}, and Year Branch is {year_branch['zodiac']} ({year_branch['element']})."
            },
            {
                "pillar": "Month Pillar",
                "character": f"{month_stem['char']}{month_branch['char']} ({month_stem['pinyin']} {month_branch['pinyin']})",
                "focus": "Career, Parents & Growth (Ages 17–32)",
                "significance": f"Month Branch {month_branch['char']} serves as the Monthly Command (月令), setting the season of your chart."
            },
            {
                "pillar": "Day Pillar",
                "character": f"{day_stem['char']}{pillars['day']['branch']['char']} ({day_stem['pinyin']} {pillars['day']['branch']['pinyin']})",
                "focus": "Self & Marriage Palace (Ages 33–48)",
                "significance": f"Day Stem is your Day Master ({dm_char}). Day Branch ({pillars['day']['branch']['char']} {pillars['day']['branch']['zodiac']}) represents your spouse palace."
            },
            {
                "pillar": "Hour Pillar",
                "character": f"{hour_stem['char']}{hour_branch['char']} ({hour_stem['pinyin']} {hour_branch['pinyin']})",
                "focus": "Children, Aspirations & Later Life (Ages 49+)",
                "significance": f"Hour Branch is {hour_branch['char']} ({hour_branch['zodiac']}), derived via the Five Rats method for your birth hour."
            }
        ]
    }

    return {
        "element_scores": element_scores,
        "element_percentages": element_percentages,
        "element_counts": element_counts,
        "day_master_strength": {
            "status": strength_category,
            "is_in_season": is_in_season,
            "season_description": season_desc,
            "supporting_score": round(supporting_score, 2),
            "draining_score": round(draining_score, 2),
            "total_score": round(total_score, 2),
        },
        "ten_gods": ten_gods_result,
        "useful_gods": {
            "favorable_elements": useful_elements,
            "unfavorable_elements": unfavorable_elements,
            "strategy": strategy_desc,
        },
        "grounded_interpretation": narrative,
    }


# ── BaZi Synastry / Compatibility Engine ─────────────────────────────────────

# Six Harmonies (六合 Liu He) branch pairs
SIX_HARMONIES = {
    ("子", "丑"), ("丑", "子"),
    ("寅", "亥"), ("亥", "寅"),
    ("卯", "戌"), ("戌", "卯"),
    ("辰", "酉"), ("酉", "辰"),
    ("巳", "申"), ("申", "巳"),
    ("午", "未"), ("未", "午"),
}

# Three Harmonies (三合 San He) branch triads
THREE_HARMONIES_GROUPS = [
    {"申", "子", "辰"},  # Water Frame
    {"亥", "卯", "未"},  # Wood Frame
    {"寅", "午", "戌"},  # Fire Frame
    {"巳", "酉", "丑"},  # Metal Frame
]

# Six Clashes (六沖 Liu Chong) branch pairs
SIX_CLASHES = {
    ("子", "午"), ("午", "子"),
    ("丑", "未"), ("未", "丑"),
    ("寅", "申"), ("申", "寅"),
    ("卯", "酉"), ("酉", "卯"),
    ("辰", "戌"), ("戌", "辰"),
    ("巳", "亥"), ("亥", "巳"),
}

# Six Harms (六害 Liu Hai) branch pairs
SIX_HARMS = {
    ("子", "未"), ("未", "子"),
    ("丑", "午"), ("午", "丑"),
    ("寅", "巳"), ("巳", "寅"),
    ("卯", "辰"), ("辰", "卯"),
    ("申", "亥"), ("亥", "申"),
    ("酉", "戌"), ("戌", "酉"),
}


def calculate_bazi_compatibility(
    bazi_a: Dict[str, Any],
    bazi_b: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes genuine Chinese BaZi Synastry (He Sang Xiang Chong 合三相沖) compatibility
    between two computed BaZi charts.
    """
    p_a = bazi_a["pillars_data"]["pillars"]
    a_a = bazi_a["analysis"]
    dm_a = bazi_a["pillars_data"]["day_master"]

    p_b = bazi_b["pillars_data"]["pillars"]
    a_b = bazi_b["analysis"]
    dm_b = bazi_b["pillars_data"]["day_master"]

    # 1. Day Master Synergy (Max 30 pts)
    dm_elem_a = dm_a["element"]
    dm_elem_b = dm_b["element"]
    
    dm_score = 20.0
    dm_relation_desc = ""

    if dm_elem_a == dm_elem_b:
        dm_score = 24.0
        dm_relation_desc = f"Both Day Masters share the {dm_elem_a} element (Peer Relationship), fostering mutual understanding and shared values."
    elif ELEMENT_PRODUCES[dm_elem_a] == dm_elem_b:
        dm_score = 28.0
        dm_relation_desc = f"Partner A's {dm_elem_a} produces Partner B's {dm_elem_b} (Nurturing Relationship), creating a natural flow of support."
    elif ELEMENT_PRODUCES[dm_elem_b] == dm_elem_a:
        dm_score = 28.0
        dm_relation_desc = f"Partner B's {dm_elem_b} produces Partner A's {dm_elem_a} (Supportive Relationship), offering strength and grounding."
    elif ELEMENT_OVERCOMES[dm_elem_a] == dm_elem_b or ELEMENT_OVERCOMES[dm_elem_b] == dm_elem_a:
        dm_score = 18.0
        dm_relation_desc = f"Dynamic Overcoming relationship between {dm_elem_a} and {dm_elem_b}, stimulating passion and growth with clear communication needed."
    else:
        dm_score = 22.0
        dm_relation_desc = f"Harmonious neutral relationship between {dm_elem_a} and {dm_elem_b} Day Masters."

    # Yin-Yang Polarity complement bonus (+2 pts)
    if dm_a["polarity"] != dm_b["polarity"]:
        dm_score = min(30.0, dm_score + 2.0)
        dm_relation_desc += f" Balanced Yin ({min(dm_a['polarity'], dm_b['polarity'])}) and Yang ({max(dm_a['polarity'], dm_b['polarity'])}) polarities."

    # 2. Spouse Palace (Day Branch 夫妻宮) Synastry (Max 35 pts)
    db_char_a = p_a["day"]["branch"]["char"]
    db_char_b = p_b["day"]["branch"]["char"]

    spouse_score = 25.0
    spouse_desc = ""

    if (db_char_a, db_char_b) in SIX_HARMONIES:
        spouse_score = 35.0
        spouse_desc = f"Six Harmonies (六合): Spouse Branches {db_char_a} and {db_char_b} form a direct celestial alliance (+35 pts). Highest affinity for marriage."
    elif any({db_char_a, db_char_b}.issubset(g) for g in THREE_HARMONIES_GROUPS):
        spouse_score = 30.0
        spouse_desc = f"Three Harmonies (三合): Spouse Branches {db_char_a} and {db_char_b} share a powerful elemental frame (+30 pts)."
    elif (db_char_a, db_char_b) in SIX_CLASHES:
        spouse_score = 12.0
        spouse_desc = f"Six Clashes (六沖): Spouse Branches {db_char_a} and {db_char_b} clash. Requires conscious effort, flexibility, and space."
    elif (db_char_a, db_char_b) in SIX_HARMS:
        spouse_score = 15.0
        spouse_desc = f"Six Harms (六害): Spouse Branches {db_char_a} and {db_char_b} present friction or misunderstandings."
    elif db_char_a == db_char_b:
        spouse_score = 24.0
        spouse_desc = f"Same Spouse Branch ({db_char_a}): Mirror dynamics creating deep empathy but occasional shared blind spots."
    else:
        spouse_score = 25.0
        spouse_desc = f"Peaceful neutral relationship between Spouse Branches {db_char_a} ({p_a['day']['branch']['zodiac']}) and {db_char_b} ({p_b['day']['branch']['zodiac']})."

    # 3. Element Complementarity / Useful God (Yong Shen 用神) Synergy (Max 20 pts)
    element_score = 10.0
    element_desc_list = []

    fav_a = a_a["useful_gods"]["favorable_elements"]
    fav_b = a_b["useful_gods"]["favorable_elements"]

    dom_a = max(a_a["element_percentages"], key=a_a["element_percentages"].get)
    dom_b = max(a_b["element_percentages"], key=a_b["element_percentages"].get)

    if dom_b in fav_a:
        element_score += 5.0
        element_desc_list.append(f"Partner B's dominant element ({dom_b}) supplies Partner A's Useful Element (用神).")

    if dom_a in fav_b:
        element_score += 5.0
        element_desc_list.append(f"Partner A's dominant element ({dom_a}) supplies Partner B's Useful Element (用神).")

    element_score = min(20.0, element_score)
    element_desc = " ".join(element_desc_list) if element_desc_list else "Balanced elemental interchange between both charts."

    # 4. Year Branch Zodiac Affinity (Max 15 pts)
    yb_char_a = p_a["year"]["branch"]["char"]
    yb_char_b = p_b["year"]["branch"]["char"]

    zodiac_a = p_a["year"]["branch"]["zodiac"]
    zodiac_b = p_b["year"]["branch"]["zodiac"]

    zodiac_score = 10.0
    zodiac_desc = ""

    if (yb_char_a, yb_char_b) in SIX_HARMONIES:
        zodiac_score = 15.0
        zodiac_desc = f"Zodiac {zodiac_a} ({yb_char_a}) and {zodiac_b} ({yb_char_b}) form a Six Harmonies match!"
    elif any({yb_char_a, yb_char_b}.issubset(g) for g in THREE_HARMONIES_GROUPS):
        zodiac_score = 13.0
        zodiac_desc = f"Zodiac {zodiac_a} ({yb_char_a}) and {zodiac_b} ({yb_char_b}) share a Three Harmonies triad!"
    elif (yb_char_a, yb_char_b) in SIX_CLASHES:
        zodiac_score = 5.0
        zodiac_desc = f"Zodiac {zodiac_a} and {zodiac_b} have a traditional Clash relationship, encouraging growth through differences."
    else:
        zodiac_score = 10.0
        zodiac_desc = f"Harmonious background alignment between {zodiac_a} and {zodiac_b}."

    total_score = round(dm_score + spouse_score + element_score + zodiac_score, 1)

    # Classification
    if total_score >= 82.0:
        level = "Exceptional Celestial Affinity (天作之合)"
        summary = "An extraordinary BaZi match with strong Day Master synergy and Spouse Palace harmony."
    elif total_score >= 70.0:
        level = "Harmonious & Complementary (相生有情)"
        summary = "A highly compatible partnership with strong mutual support and elemental balance."
    elif total_score >= 58.0:
        level = "Balanced & Supportive (平穩和合)"
        summary = "A solid, steady connection requiring standard emotional nurturing and communication."
    else:
        level = "Dynamic & Transformative (磨合成長)"
        summary = "A dynamic relationship with individual differences that foster deep personal transformation."

    return {
        "overall_score": total_score,
        "compatibility_level": level,
        "summary": summary,
        "categories": {
            "day_master_synergy": {
                "score": round(dm_score, 1),
                "max": 30,
                "description": dm_relation_desc,
                "partner_a_dm": f"{dm_a['char']} ({dm_elem_a})",
                "partner_b_dm": f"{dm_b['char']} ({dm_elem_b})",
            },
            "spouse_palace_harmony": {
                "score": round(spouse_score, 1),
                "max": 35,
                "description": spouse_desc,
                "partner_a_branch": f"{db_char_a} ({p_a['day']['branch']['zodiac']})",
                "partner_b_branch": f"{db_char_b} ({p_b['day']['branch']['zodiac']})",
            },
            "elemental_complementarity": {
                "score": round(element_score, 1),
                "max": 20,
                "description": element_desc,
            },
            "zodiac_affinity": {
                "score": round(zodiac_score, 1),
                "max": 15,
                "description": zodiac_desc,
                "partner_a_zodiac": zodiac_a,
                "partner_b_zodiac": zodiac_b,
            }
        }
    }


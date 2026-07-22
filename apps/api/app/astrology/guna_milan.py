from typing import Any, Dict, Tuple

# 27 Nakshatras Gana classifications (0 = Deva, 1 = Manushya, 2 = Rakshasa)
NAK_GANAS = [
    0, 1, 2, 1, 0, 1, 0, 0, 2,  # 0-8: Ashwini to Ashlesha
    2, 1, 1, 0, 2, 0, 2, 0, 2,  # 9-17: Magha to Jyeshtha
    2, 1, 1, 0, 2, 2, 1, 1, 0   # 18-26: Mula to Revati
]

GANA_NAMES = {0: "Deva", 1: "Manushya", 2: "Rakshasa"}

# Nakshatra animal (Yoni) classifications (0 to 13 animal IDs)
# Animal list:
# 0: Horse, 1: Elephant, 2: Sheep, 3: Serpent, 4: Dog, 5: Cat, 6: Rat,
# 7: Cow, 8: Buffalo, 9: Tiger, 10: Hare, 11: Monkey, 12: Mongoose, 13: Lion
NAK_YONIS = [
    0, 1, 2, 3, 3, 4, 5, 2, 5,  # 0-8: Ashwini to Ashlesha
    6, 6, 7, 8, 9, 8, 9, 10, 10, # 9-17: Magha to Jyeshtha
    4, 11, 12, 11, 13, 0, 13, 7, 1 # 18-26: Mula to Revati (note: Mula is Dog, etc.)
]

YONI_NAMES = [
    "Horse (Ashva)", "Elephant (Gaja)", "Sheep (Mesha)", "Serpent (Sarpa)",
    "Dog (Shvana)", "Cat (Marjara)", "Rat (Mushaka)", "Cow (Gau)",
    "Buffalo (Mahisha)", "Tiger (Vyaghra)", "Hare (Shasha)", "Monkey (Markata)",
    "Mongoose (Nakula)", "Lion (Simha)"
]

# Yoni relationship points matrix (14x14)
# 4 = Same, 3 = Friend, 2 = Neutral, 1 = Enemy, 0 = Hostile/Mortal Enemy
YONI_MATRIX = [
    # 0   1   2   3   4   5   6   7   8   9   10  11  12  13
    [4,  2,  2,  3,  2,  2,  2,  2,  2,  1,  2,  3,  2,  1],  # 0: Horse
    [2,  4,  3,  3,  2,  2,  2,  2,  2,  1,  2,  3,  2,  0],  # 1: Elephant
    [2,  3,  4,  2,  1,  2,  2,  3,  2,  0,  3,  2,  2,  1],  # 2: Sheep
    [3,  3,  2,  4,  2,  1,  1,  2,  2,  2,  2,  2,  0,  2],  # 3: Serpent
    [2,  2,  1,  2,  4,  2,  1,  2,  2,  1,  2,  2,  2,  0],  # 4: Dog
    [2,  2,  2,  1,  2,  4,  0,  2,  2,  1,  2,  2,  2,  2],  # 5: Cat
    [2,  2,  2,  1,  1,  0,  4,  2,  2,  2,  2,  2,  2,  2],  # 6: Rat
    [2,  2,  3,  2,  2,  2,  2,  4,  3,  0,  2,  2,  2,  1],  # 7: Cow
    [2,  2,  2,  2,  2,  2,  2,  3,  4,  1,  2,  2,  2,  2],  # 8: Buffalo
    [1,  1,  0,  2,  1,  1,  2,  0,  1,  4,  1,  2,  2,  2],  # 9: Tiger
    [2,  2,  3,  2,  2,  2,  2,  2,  2,  1,  4,  2,  2,  0],  # 10: Hare
    [3,  3,  2,  2,  2,  2,  2,  2,  2,  2,  2,  4,  2,  2],  # 11: Monkey
    [2,  2,  2,  0,  2,  2,  2,  2,  2,  2,  2,  2,  4,  2],  # 12: Mongoose
    [1,  0,  1,  2,  0,  2,  2,  1,  2,  2,  0,  2,  2,  4],  # 13: Lion
]

# Moon Sign Lord mapping for Graha Maitri (0=Sun, 1=Moon, 2=Mars, 3=Mercury, 4=Jupiter, 5=Venus, 6=Saturn)
SIGN_LORDS = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4]

# Graha Maitri relationship points matrix (7x7)
# 5 = Friendly/Same, 4 = Neutral/Friend, 3 = Neutral/Neutral, 1/2 = Enemy/Neutral, 0 = Enemy/Enemy
GRAHA_MATRIX = [
    # 0   1   2   3   4   5   6 (0:Sun, 1:Moon, 2:Mars, 3:Mercury, 4:Jupiter, 5:Venus, 6:Saturn)
    [5,  5,  5,  4,  5,  0,  0],  # 0: Sun
    [5,  5,  4,  5,  4,  4,  3],  # 1: Moon
    [5,  4,  5,  0,  5,  4,  3],  # 2: Mars
    [4,  0,  3,  5,  3,  5,  4],  # 3: Mercury
    [5,  4,  4,  3,  5,  0,  3],  # 4: Jupiter
    [0,  3,  3,  5,  3,  5,  5],  # 5: Venus
    [0,  3,  0,  4,  3,  5,  5],  # 6: Saturn
]

# Nakshatra Nadis (0 = Adi/Vata, 1 = Madhya/Pitta, 2 = Antya/Kapha)
NAK_NADIS = [
    0, 1, 2, 2, 1, 0, 0, 1, 2,  # Ashwini to Ashlesha
    2, 1, 0, 0, 1, 2, 2, 1, 0,  # Magha to Jyeshtha
    0, 1, 2, 2, 1, 0, 0, 1, 2   # Mula to Revati
]

NADI_NAMES = {0: "Adi (Vata)", 1: "Madhya (Pitta)", 2: "Antya (Kapha)"}

# Rajju mapping: 0 = Pada, 1 = Kati, 2 = Udara, 3 = Kantha, 4 = Sira
NAK_RAJJUS = [
    0, 1, 2, 3, 4, 3, 2, 1, 0,  # 0-8: Ashwini to Ashlesha
    0, 1, 2, 3, 4, 3, 2, 1, 0,  # 9-17: Magha to Jyeshtha
    0, 1, 2, 3, 4, 3, 2, 1, 0   # 18-26: Mula to Revati
]
RAJJU_NAMES = ["Pada (Foot)", "Kati (Waist)", "Udara (Stomach)", "Kantha (Neck)", "Sira (Head)"]

# Vedha pairs mapping
VEDHA_PAIRS = {
    0: 17, 1: 16, 2: 15, 3: 14, 4: 22, 5: 21, 6: 20, 7: 19, 8: 18,
    9: 26, 10: 25, 11: 24, 12: 23, 13: 13,
    17: 0, 16: 1, 15: 2, 14: 3, 22: 4, 21: 5, 20: 6, 19: 7, 18: 8,
    26: 9, 25: 10, 24: 11, 23: 12
}


def calculate_guna_milan(
    groom_nak_idx: int, groom_sign_idx: int,
    bride_nak_idx: int, bride_sign_idx: int
) -> Tuple[float, Dict[str, Any]]:
    """
    Vedic Ashta Kuta Guna Milan calculator.
    Returns the total compatibility score (out of 36) and a detailed breakdown.
    """
    breakdown = {}
    total = 0.0

    # 1. Varna (Work/Spiritual alignment) - Max 1 point
    # Cancer(3), Scorpio(7), Pisces(11) = Brahmin (4)
    # Aries(0), Leo(4), Sagittarius(8) = Kshatriya (3)
    # Taurus(1), Virgo(5), Capricorn(9) = Vaishya (2)
    # Gemini(2), Libra(6), Aquarius(10) = Shudra (1)
    varna_map = {
        3: 4, 7: 4, 11: 4,  # Brahmin
        0: 3, 4: 3, 8: 3,   # Kshatriya
        1: 2, 5: 2, 9: 2,   # Vaishya
        2: 1, 6: 1, 10: 1   # Shudra
    }
    groom_varna = varna_map.get(groom_sign_idx, 1)
    bride_varna = varna_map.get(bride_sign_idx, 1)

    varna_score = 1.0 if groom_varna >= bride_varna else 0.0
    total += varna_score
    breakdown["varna"] = {
        "score": varna_score, "max": 1,
        "groom": ["Shudra", "Vaishya", "Kshatriya", "Brahmin"][groom_varna - 1],
        "bride": ["Shudra", "Vaishya", "Kshatriya", "Brahmin"][bride_varna - 1]
    }

    # 2. Vashya (Mutual influence/attraction) - Max 2 points
    vashya_groups = {
        0: 0, 1: 0, 8: 0, 9: 0, # Chatushpada (0)
        2: 1, 5: 1, 6: 1, 10: 1, # Manav (1)
        3: 2, 11: 2,             # Jalachar (2)
        4: 3,                    # Vanachar (3)
        7: 4                     # Keeta (4)
    }
    groom_vashya = vashya_groups.get(groom_sign_idx, 0)
    bride_vashya = vashya_groups.get(bride_sign_idx, 0)

    if groom_vashya == bride_vashya:
        vashya_score = 2.0
    elif (groom_vashya == 0 and bride_vashya == 2) or (groom_vashya == 2 and bride_vashya == 0):
        vashya_score = 1.0
    else:
        vashya_score = 0.5 if abs(groom_vashya - bride_vashya) == 1 else 0.0

    total += vashya_score
    vashya_names = ["Chatushpada (4-legged)", "Manav (Human)", "Jalachar (Water)", "Vanachar (Wild)", "Keeta (Insect)"]
    breakdown["vashya"] = {
        "score": vashya_score, "max": 2,
        "groom": vashya_names[groom_vashya],
        "bride": vashya_names[bride_vashya]
    }

    # 3. Tara (Destiny/Health alignment) - Max 3 points
    # Count distance from groom to bride and bride to groom nakshatras
    dist_g_to_b = (bride_nak_idx - groom_nak_idx) % 27 + 1
    dist_b_to_g = (groom_nak_idx - bride_nak_idx) % 27 + 1

    r_g = dist_g_to_b % 9
    r_b = dist_b_to_g % 9

    # Auspicious remainders (3, 5, 7, or 0)
    g_ok = r_g in [0, 3, 5, 7]
    b_ok = r_b in [0, 3, 5, 7]

    if g_ok and b_ok:
        tara_score = 3.0
    elif g_ok or b_ok:
        tara_score = 1.5
    else:
        tara_score = 0.0

    total += tara_score
    breakdown["tara"] = {
        "score": tara_score, "max": 3,
        "groom_rem": r_g, "bride_rem": r_b
    }

    # 4. Yoni (Physical compatibility) - Max 4 points
    groom_yoni = NAK_YONIS[groom_nak_idx]
    bride_yoni = NAK_YONIS[bride_nak_idx]
    yoni_score = float(YONI_MATRIX[groom_yoni][bride_yoni])

    total += yoni_score
    breakdown["yoni"] = {
        "score": yoni_score, "max": 4,
        "groom": YONI_NAMES[groom_yoni],
        "bride": YONI_NAMES[bride_yoni]
    }

    # 5. Graha Maitri (Intellectual compatibility) - Max 5 points
    groom_lord = SIGN_LORDS[groom_sign_idx]
    bride_lord = SIGN_LORDS[bride_sign_idx]
    graha_score = float(GRAHA_MATRIX[groom_lord][bride_lord])

    total += graha_score
    lord_names = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    breakdown["graha_maitri"] = {
        "score": graha_score, "max": 5,
        "groom": lord_names[groom_lord],
        "bride": lord_names[bride_lord]
    }

    # 6. Gana (Temperaments) - Max 6 points
    groom_gana = NAK_GANAS[groom_nak_idx]
    bride_gana = NAK_GANAS[bride_nak_idx]

    if groom_gana == bride_gana:
        gana_score = 6.0
    elif (groom_gana == 0 and bride_gana == 1) or (groom_gana == 1 and bride_gana == 0):
        gana_score = 5.0
    elif (groom_gana == 0 and bride_gana == 2) or (groom_gana == 2 and bride_gana == 0):
        gana_score = 1.0
    else:
        gana_score = 0.0

    total += gana_score
    breakdown["gana"] = {
        "score": gana_score, "max": 6,
        "groom": GANA_NAMES[groom_gana],
        "bride": GANA_NAMES[bride_gana]
    }

    # 7. Bhakoot (Emotional compatibility) - Max 7 points
    # Calculated based on relative Moon sign distance
    diff = (bride_sign_idx - groom_sign_idx) % 12 + 1
    # Check dwirdwadashe (2-12) or shadashtaka (6-8) or navapanchama (5-9)
    bhakoot_cancelled = False
    if diff in [2, 12, 6, 8, 5, 9]:
        # Check for Bhakoot Dosha cancellation
        groom_lord = SIGN_LORDS[groom_sign_idx]
        bride_lord = SIGN_LORDS[bride_sign_idx]
        graha_score = float(GRAHA_MATRIX[groom_lord][bride_lord])
        
        # Dosha is cancelled if sign lords are the same or mutual friends (Graha Maitri score >= 4)
        if groom_lord == bride_lord or graha_score >= 4.0:
            bhakoot_score = 7.0
            bhakoot_cancelled = True
        else:
            bhakoot_score = 0.0
    else:
        bhakoot_score = 7.0

    total += bhakoot_score
    breakdown["bhakoot"] = {
        "score": bhakoot_score, "max": 7,
        "distance": diff,
        "cancelled": bhakoot_cancelled
    }

    # 8. Nadi (Physiological harmony) - Max 8 points
    groom_nadi = NAK_NADIS[groom_nak_idx]
    bride_nadi = NAK_NADIS[bride_nak_idx]

    nadi_cancelled = False
    if groom_nadi != bride_nadi:
        nadi_score = 8.0
    else:
        # Nadi Dosha cancellation rules:
        # 1. Same Nakshatra but different signs
        # 2. Same sign but different Nakshatras
        if (groom_nak_idx == bride_nak_idx and groom_sign_idx != bride_sign_idx) or \
           (groom_sign_idx == bride_sign_idx and groom_nak_idx != bride_nak_idx):
            nadi_score = 8.0
            nadi_cancelled = True
        else:
            nadi_score = 0.0

    total += nadi_score
    breakdown["nadi"] = {
        "score": nadi_score, "max": 8,
        "groom": NADI_NAMES[groom_nadi],
        "bride": NADI_NAMES[bride_nadi],
        "cancelled": nadi_cancelled
    }

    # Advanced Upakuta calculations (not counted in Ashta Kuta 36 score)
    groom_rajju = NAK_RAJJUS[groom_nak_idx]
    bride_rajju = NAK_RAJJUS[bride_nak_idx]
    rajju_dosha = (groom_rajju == bride_rajju)
    
    vedha_dosha = (VEDHA_PAIRS.get(groom_nak_idx) == bride_nak_idx)
    
    # Mahendra Kuta
    dist_g_b = (groom_nak_idx - bride_nak_idx) % 27 + 1
    mahendra = dist_g_b in [4, 7, 10, 13, 16, 19, 22, 25]
    
    # Stri-Deergha
    dist_b_g = (groom_nak_idx - bride_nak_idx) % 27
    stri_deergha = dist_b_g >= 9

    breakdown["rajju"] = {
        "groom": RAJJU_NAMES[groom_rajju],
        "bride": RAJJU_NAMES[bride_rajju],
        "has_dosha": bool(rajju_dosha),
        "description": "Checks if both partners' Nakshatras align on the same vital energy line (Rajju). Same Rajju indicates a major dosha."
    }
    breakdown["vedha"] = {
        "has_dosha": bool(vedha_dosha),
        "description": "Checks if the Nakshatras form mutually obstructive/inimical pairings."
    }
    breakdown["mahendra"] = {
        "has_kuta": bool(mahendra),
        "description": "Signifies family growth, general wellbeing, and lineage support."
    }
    breakdown["stri_deergha"] = {
        "has_kuta": bool(stri_deergha),
        "description": "Ensures the husband's planetary energy supports the wife's longevity."
    }

    return total, breakdown

"""
Astrology Knowledge Base

Contains static traditional interpretations for Vedic placements, signs, houses,
nakshatras, and yogas/doshas.
"""

from typing import Any, Dict, List

PLANET_MEANINGS = {
    "sun": "Soul, identity, father, authority, government, self-realization, and confidence.",
    "moon": "Mind, emotions, mother, peace of mind, public perception, and nurturing capacity.",
    "mercury": "Intellect, logic, communication, commerce, math, speech, and analysis.",
    "venus": "Relationships, love, luxury, fine arts, devotion, sensory pleasures, and refinement.",
    "mars": "Energy, action, courage, drive, physical strength, siblings, and engineering.",
    "jupiter": "Wisdom, expansion, learning, spirituality, children, wealth, and guidance.",
    "saturn": "Discipline, delays, longevity, structure, duty, service, limitations, and focus.",
    "rahu": "Desires, obsession, amplification, foreign influences, technology, and ambition.",
    "ketu": "Liberation, detachment, spiritual insights, past-life skills, and isolation.",
}

SIGN_MEANINGS = {
    "Aries": "Dynamic, initiating, pioneering, ruled by Mars. Focuses on independent identity.",
    "Taurus": "Stable, grounded, beauty-oriented, ruled by Venus. Focuses on resources, speech, family.",
    "Gemini": "Curious, versatile, communicative, ruled by Mercury. Focuses on intellect, hobbies.",
    "Cancer": "Nurturing, intuitive, protective, ruled by Moon. Focuses on emotional security, home.",
    "Leo": "Noble, expressive, authoritative, ruled by Sun. Focuses on creativity, self-projection.",
    "Virgo": "Detail-oriented, analytical, service-focused, ruled by Mercury. Focuses on healing, dispute resolution.",
    "Libra": "Harmonious, partnership-driven, artistic, ruled by Venus. Focuses on balance, justice.",
    "Scorpio": "Intense, transformative, occult-oriented, ruled by Mars. Focuses on research, secrets.",
    "Sagittarius": "Philosophical, optimistic, truth-seeking, ruled by Jupiter. Focuses on wisdom, higher education.",
    "Capricorn": "Ambitious, structured, practical, ruled by Saturn. Focuses on professional status, duty.",
    "Aquarius": "Humanitarian, systemic, network-oriented, ruled by Saturn. Focuses on community, achievements.",
    "Pisces": "Imaginative, spiritual, surrender-oriented, ruled by Jupiter. Focuses on isolation, sub-conscious.",
}

HOUSE_MEANINGS = {
    "1": "Physical body, personality, general path in life, self-realization, and health.",
    "2": "Family, accumulated wealth, assets, speech, intake of food, and values.",
    "3": "Siblings, courage, self-efforts, hobbies, writing, communication, and short journeys.",
    "4": "Mother, home, domestic happiness, emotional peace, land, vehicle, and roots.",
    "5": "Children, education, past-life merits (Purva Punya), romance, creativity, and intellect.",
    "6": "Daily routines, service, health, disputes, debts, enemies, and obstacles.",
    "7": "Partnerships, marriage, spouse, business relationships, and public interactions.",
    "8": "Transformations, longevity, sudden events, secrets, occult, research, and joint finances.",
    "9": "Dharma, father, teachers/gurus, higher wisdom, spiritual values, and long-distance travels.",
    "10": "Public status, career, achievements, fame, professional duty, and actions in society.",
    "11": "Gains, networks, elder siblings, community, global goals, and cash flow.",
    "12": "Losses, expenses, isolation, hospitals, foreign lands, sleep, subconscious, and Moksha.",
}

YOGA_MEANINGS = {
    "Gaja Kesari Yoga (Jupiter in Kendra from Moon)": "Creates intelligence, respect, wisdom, prosperity, and magnetic public appeal.",
    "Ruchaka Yoga (Pancha Mahapurusha)": "Indicates physical prowess, courage, leadership, victory over enemies, and assertiveness.",
    "Bhadra Yoga (Pancha Mahapurusha)": "Indicates sharp intellect, mathematical skills, commercial success, and fluent communication.",
    "Hamsa Yoga (Pancha Mahapurusha)": "Indicates purity, wisdom, spiritual inclinations, respect, and high character.",
    "Malavya Yoga (Pancha Mahapurusha)": "Indicates luxury, artistic talent, standard of living, charm, and long-term marriage.",
    "Sasa Yoga (Pancha Mahapurusha)": "Indicates discipline, ability to build structures, focus, longevity, and administrative respect.",
    "Manglik Dosha": "Creates challenges, conflicts, or delays in marriages and partnerships, requiring balance and remedies.",
    "Kaal Sarp Dosha": "Indicates a life of intense fluctuations, hidden obstacles, and spiritual transformation.",
}


def build_knowledge_prompt_context(chart: Dict[str, Any], rules: Dict[str, Any]) -> str:
    """
    Looks up matching placements and assembles a structured knowledge context block.
    This replaces any reliance on LLM's raw memory regarding traditional Vedic meanings.
    """
    sections = []

    # 1. House Placements Context
    sections.append("## TRADITIONAL PLANETS IN HOUSES DEFINITIONS")
    for name, data in chart["planets"].items():
        house_str = str(data["house"])
        sign_name = data["sign"]
        strength = rules["strengths"].get(name, "Neutral")
        retro_str = " (Retrograde)" if data["is_retrograde"] else ""
        
        planet_desc = PLANET_MEANINGS.get(name, "")
        house_desc = HOUSE_MEANINGS.get(house_str, "")
        sign_desc = SIGN_MEANINGS.get(sign_name, "")

        sections.append(
            f"- **{name.capitalize()}{retro_str} in House {house_str} ({sign_name} - {strength})**:\n"
            f"  - Planet Nature: {planet_desc}\n"
            f"  - House Arena: {house_desc}\n"
            f"  - Zodiac Sign filter: {sign_desc}"
        )

    # 2. Nakshatra Context
    sections.append("\n## TRADITIONAL MOON NAKSHATRA MEANING")
    moon_nak = rules["nakshatras"]["moon"]
    sections.append(
        f"The Moon resides in the Nakshatra **{moon_nak['name']}** (Pada {moon_nak['pada']}) ruled by **{moon_nak['lord'].capitalize()}**.\n"
        f"- Nakshatras define the subconscious filters and early life environment."
    )

    # 3. Yogas & Doshas Context
    detected_yogas = rules["yogas"]
    detected_doshas = rules["doshas"]
    
    if detected_yogas or detected_doshas:
        sections.append("\n## TRADITIONAL YOGAS AND DOSHAS INTERPRETATIONS")
        
        # Merge list for matching
        for yoga in detected_yogas:
            desc = YOGA_MEANINGS.get(yoga, "Indicates a powerful cosmic alignment.")
            sections.append(f"- **{yoga}**: {desc}")
            
        for dosha in detected_doshas:
            # Handle generic matching for Manglik
            matching_key = "Manglik Dosha" if "Manglik" in dosha else dosha
            desc = YOGA_MEANINGS.get(matching_key, "Requires awareness and protective remedies.")
            sections.append(f"- **{dosha}**: {desc}")

    # 4. Current Dasha Context
    sections.append("\n## CURRENT DASHA LIFELINE STATUS")
    current_dasha = rules["dashas"][0]  # First entry is birth/active dasha
    sections.append(
        f"- Main Dasha: **{current_dasha['lord'].capitalize()}** cycle (starts: {current_dasha['start']} to: {current_dasha['end']})\n"
        f"- Antardasha timeline represents the active sub-period triggers."
    )

    return "\n".join(sections)

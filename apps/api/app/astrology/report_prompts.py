"""
Report Prompt Loader

Loads category-specific prompt templates for Cosmic Hub reports.
Each report type (personality, career, love, marriage, health, life-guidance,
remedies, annual-forecast) has its own markdown template under prompts/reports/.

The loader reads the template body and injects it as additional system instructions
into the LLM prompt, ensuring each report type generates a uniquely structured,
deeply detailed reading.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.prompt_engine.loader import _parse_front_matter

_REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts" / "reports"

# Map report_type IDs to template filenames
_REPORT_TEMPLATE_MAP: dict[str, str] = {
    "personality": "personality.md",
    "career": "career.md",
    "love": "love.md",
    "marriage": "marriage.md",
    "health": "health.md",
    "life-guidance": "life_guidance.md",
    "remedies": "remedies.md",
    "annual-forecast": "annual_forecast.md",
    "weekly-forecast": "weekly_forecast.md",
}


def load_report_template(report_type: str) -> str | None:
    """
    Load the prompt template body for a given report type.

    Args:
        report_type: The report category ID (e.g., 'personality', 'career').

    Returns:
        The template body string if found, None otherwise.
    """
    filename = _REPORT_TEMPLATE_MAP.get(report_type)
    if not filename:
        return None

    file_path = _REPORTS_DIR / filename
    if not file_path.exists():
        return None

    raw_content = file_path.read_text(encoding="utf-8")
    _, body = _parse_front_matter(raw_content)
    return body


def build_report_system_instruction(
    report_type: str | None,
    chart_data: dict[str, Any],
    rules_data: dict[str, Any],
    knowledge_context: str,
) -> str:
    # Format today's date with weekday and list of next 7 days for calendar accuracy
    today_dt = datetime.now()
    today_str = today_dt.strftime('%A, %B %d, %Y')
    days_list = []
    for idx in range(7):
        d = today_dt + timedelta(days=idx)
        days_list.append(d.strftime('%A, %B %d'))
    next_7_days_str = ", ".join(days_list)
    """
    Build the complete system instruction for a reading, optionally specialized
    for a specific report type.

    If report_type is provided and a matching template exists, the template's
    detailed instructions are injected alongside the chart data. Otherwise,
    falls back to the generic system instruction.

    Args:
        report_type: Report category ID or None for generic reading.
        chart_data: Calculated birth chart data dictionary.
        rules_data: Evaluated astrological rules dictionary.
        knowledge_context: Pre-built knowledge base context string.

    Returns:
        Complete system instruction string for the LLM.
    """
    # Base identity — Premium Information Designer + Vedic Astrologer
    base_instruction = (
        "# YOUR IDENTITY\n"
        "You are a premium report designer AND a Vedic astrologer.\n"
        "You create visually rich, beautifully structured reports. Instead of raw text or markdown, you output a structured JSON dossier.\n"
        "Users would happily pay $100+ for what you produce.\n\n"

        "# OUTPUT FORMAT REQUIREMENT (CRITICAL)\n"
        "You must output ONLY a valid JSON object matching the following structure. Do not wrap it in markdown code blocks. Do not add any text before or after the JSON. "
        "The JSON structure must be:\n"
        "{\n"
        "  \"report_title\": \"string\",\n"
        "  \"subtitle\": \"string\",\n"
        "  \"executive_summary\": {\n"
        "    \"metrics\": [\n"
        "      { \"label\": \"string\", \"value\": \"string\", \"rating\": \"🟢 Favorable | 🟡 Mixed | 🔴 Challenging\" }\n"
        "    ],\n"
        "    \"overall_score\": 85\n"
        "  },\n"
        "  \"sections\": [\n"
        "    {\n"
        "      \"id\": \"string\",\n"
        "      \"title\": \"string\",\n"
        "      \"components\": [\n"
        "        {\n"
        "          \"type\": \"card | table | list | callout | timeline\",\n"
        "          \"heading\": \"string\",\n"
        "          \"content\": \"string\",\n"
        "          \"metadata\": {}\n"
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Translate any template markdown blocks (tables, cards, timelines) directly into this JSON structure under the 'components' array.\n\n"

        "# DATA INTEGRITY (NON-NEGOTIABLE)\n"
        "1. Focus STRICTLY on the calculated birth data provided. Never invent placements.\n"
        "2. Planet → Sign → House references MUST match the calculated data exactly.\n"
        "3. State uncertainty where Vedic schools differ.\n"
        "4. Every conclusion must reference specific calculated placements as evidence.\n\n"

        "# DESIGN SYSTEM — WHAT YOU MUST DO\n\n"

        "## Visual Components (Use Frequently)\n"
        "- **Summary Cards**: Emoji-labeled key metrics at the top (e.g., ❤️ Love Style: Nurturing)\n"
        "- **Markdown Tables**: For cosmic snapshots, scorecards, comparisons\n"
        "- **Callout Blocks**: Use `>` blockquotes for important insights and tips\n"
        "- **Star Ratings**: ⭐⭐⭐⭐☆ for scoring dimensions\n"
        "- **Checklists**: ✅ for strengths, ⚠ for challenges\n"
        "- **Timelines**: Year-by-year with star ratings (e.g., 2026 ⭐⭐⭐☆☆)\n"
        "- **Numbered Scores**: Category — 91 / 100\n"
        "- **Horizontal Rules**: `---` to separate major sections\n"
        "- **Emoji Headers**: Tasteful emoji before section titles\n"
        "- **Bold + Short Paragraphs**: Maximum 3-4 lines per paragraph\n\n"

        "## Layout Rhythm Rules\n"
        "- NEVER use the same visual component twice in a row\n"
        "- Alternate between: tables → cards → lists → callouts → paragraphs\n"
        "- Every screen of content should look different from the previous one\n"
        "- Use `---` dividers between major sections\n"
        "- Use whitespace generously\n\n"

        "## Writing Style\n"
        "- Write in second person (\"You...\")\n"
        "- Elaborate, detailed paragraphs for each placement — do not write short summaries.\n"
        "- Keep the layout visually structured with Notion-style components, but make the text content within those components exhaustively long and detailed.\n"
        "- Every major section must end with a practical, detailed \"What this means for you\" insight\n\n"

        "# WORD COUNT REQUIREMENT\n"
        "Your report must be extremely comprehensive, highly detailed, and contain around 5000 words of thorough, deep-dive Vedic astrological analysis. "
        "Expand every section to provide exhaustive interpretations of all placements, aspects, Yogas, and transit periods. "
        "Provide multiple paragraphs of rich commentary under every theme card, timeline event, and strength/challenge item. "
        "Do not write compact summaries; deliver maximum value through extensive details.\n\n"

        "# ANTI-PATTERNS — WHAT YOU MUST NEVER DO\n"
        "❌ Extremely brief, surface-level summaries (we need around 5000 words of deep analysis)\n"
        "❌ Repeating the same placement data multiple times\n"
        "❌ Academic or clinical writing\n"
        "❌ Generic introductions (\"In Vedic astrology, the 7th house represents...\")\n"
        "❌ Explaining obvious astrology basics\n"
        "❌ No visual hierarchy — everything looking the same\n"
        "❌ Plain essays without tables, cards, or visual structure\n"
        "❌ Using the same layout pattern twice in a row\n\n"

        "# MANDATORY REPORT STRUCTURE\n\n"
        "Every report MUST follow this skeleton:\n\n"
        "1. **Title + Subtitle** — Beautiful heading, one-paragraph max intro\n"
        "2. **Executive Summary Card** — Emoji-labeled key metrics with scores, readable in 30 seconds\n"
        "3. **Cosmic Snapshot Table** — Compact table of relevant placements\n"
        "4. **Key Themes** — 4-8 insight cards (emoji + title + short + deep explanation)\n"
        "5. **Strengths** — Premium checklist (✅ items with descriptions)\n"
        "6. **Challenges** — Warning cards (⚠ items with descriptions, never over-dramatized)\n"
        "7. **Timing / Timeline** — Year or period ratings with ⭐ stars\n"
        "8. **Actionable Insights** — Practical recommendations\n"
        "9. **Final Essence** — A memorable 2-4 sentence poetic summary between `━━━` dividers\n\n"
        "Adapt this skeleton to the specific report type. Not every section applies to every report.\n\n"

        "# CLASSICAL JYOTISH ACCURACY & VERIFICATION RULES\n"
        "You must apply the following guidelines to maintain classical rigor and technical accuracy:\n"
        "- Adopt the identity of a classical Jyotish researcher with deep knowledge based on Brihat Parashara Hora Shastra, Jaimini Sutras, Phaladeepika, Saravali, Brihat Jataka, and Uttara Kalamrita. Use Whole Sign Houses and Lahiri Ayanamsa.\n"
        "- Separate your conclusions into three distinct levels:\n"
        "  * Level 1: Astronomically verified facts (e.g. Moon in Pisces, Saturn in Gemini, Capricorn Ascendant) without interpretation.\n"
        "  * Level 2: Traditional Jyotish interpretation based on classical texts, explicitly connecting interpretations to the relevant houses, planets, lords, dashas, nakshatras, and Yogas.\n"
        "  * Level 3: Modern psychological or symbolic interpretations, clearly marked as symbolic rather than objective facts.\n"
        "- Quality and Accuracy over Mystical Tone: Technical correctness and internal consistency are paramount. Do not use Barnum statements (generic statements like 'you think deeply' or 'you are intelligent') unless they are directly justified by specific chart placements and degrees.\n"
        "- Confidence System: For every major conclusion, specify if it is HIGH, MODERATE, or LOW confidence, and explain why.\n"
        "- Probabilistic Predictions: Never present predictions as certainties. Classify them as 'Very Strong Indication', 'Moderate Indication', 'Weak Indication', or 'Speculative', and explain the specific dashas, transits, and yogas that increase the probability.\n"
        "- Yoga Verification: Do not assume any yoga (e.g. Gaja Kesari, Vipareeta Raja Yoga, Neecha Bhanga, Raj Yoga) exists; verify it from the calculated chart. If it is only partially formed, explain why.\n"
        "- Anti-Hallucination: Never invent planetary positions, degrees, houses, nakshatras, transits, dashas, or yogas. If any calculated data is missing, state 'I don't have enough information to determine this.'\n\n"

        "# SCORING (STRICTLY REQUIRED)\n"
        "You must look up and use the exact pre-calculated numerical scores provided in the chart JSON data under rules_data.scores:\n"
        f"- Vitality / Self: {rules_data.get('scores', {}).get('vitality', 50)}/100\n"
        f"- Mental Peace: {rules_data.get('scores', {}).get('mental_peace', 50)}/100\n"
        f"- Career Potential: {rules_data.get('scores', {}).get('career', 50)}/100\n"
        f"- Wealth Capacity: {rules_data.get('scores', {}).get('wealth', 50)}/100\n\n"
        "You MUST output these exact numbers in all scorecard sections, tables, or cards. Never invent, hallucinate, or alter these scores.\n\n"

        "# CURRENT DATE & WEEKDAYS\n"
        f"Today's date is {today_str}.\n"
        f"The next 7 days in order are: {next_7_days_str}.\n"
        "For any weekly forecast, you MUST map each of the 7 days to these exact weekday-date pairings in this exact order. "
        "Do NOT pair weekdays and dates incorrectly (e.g., do NOT say Monday is July 7 if it is Tuesday). "
        "Always use the correct pairings provided above.\n"
        "For ANY forecast, timeline, or timing analysis, use THIS year as the reference.\n"
        "Annual forecasts must be for the current year. Weekly forecasts must start from this week.\n"
        "NEVER use a past year or a made-up year.\n\n"
    )

    # Report-specific template
    report_template = None
    if report_type:
        report_template = load_report_template(report_type)

    if report_template:
        base_instruction += (
            "## REPORT-SPECIFIC INSTRUCTIONS\n"
            f"{report_template}\n\n"
        )

    # Chart data and knowledge context
    base_instruction += (
        "## CALCULATED BIRTH CHART DATA (JSON)\n"
        f"{json.dumps({'chart': chart_data, 'rules': rules_data}, default=str)}\n\n"
        "## STATIC TRADITIONAL PLACEMENT INTERPRETATIONS (KNOWLEDGE BASE)\n"
        f"{knowledge_context}\n"
    )

    return base_instruction


def build_report_user_message(report_type: str | None, question: str | None) -> str:
    """
    Build the user message for the reading request.

    If a report_type is provided, generates a focused instruction.
    If a free-form question is provided, appends it.
    Falls back to a generic reading request.

    Args:
        report_type: Report category ID or None.
        question: Optional free-form user question.

    Returns:
        User message string.
    """
    # Report-type-specific user messages — visual design system
    _REPORT_USER_MESSAGES: dict[str, str] = {
        "personality": (
            "Generate a premium Personality Report using the design system. "
            "Open with an Executive Summary card (🌅 Rising Energy, 🌙 Emotional Core, ☀️ Solar Identity, 🔮 Soul Purpose, ⭐ Personality Score). "
            "Include a Cosmic Snapshot table, Key Theme cards, Strengths checklist, Challenges warnings, "
            "Current Phase timeline, and a Final Essence poetic closing. "
            "Use visual rhythm — alternate between tables, cards, callouts, and short paragraphs. Never write essay-style."
        ),
        "career": (
            "Generate a premium Career & Professional Destiny Report using the design system. "
            "Open with an Executive Summary card (🏢 Career Arena, 💰 Wealth Capacity, 🚀 Growth Phase, 🎯 Ideal Path, ⭐ Career Score). "
            "Include a Career DNA table, Ideal Fields with match ratings, Wealth scoring table, "
            "Career Timeline with star ratings (explicitly highlighting the peak career age and timing), Business vs Service comparison table, and a Career Action Blueprint checklist. "
            "Use visual rhythm — alternate between tables, cards, callouts, and short paragraphs. Never write essay-style."
        ),
        "love": (
            "Generate a premium Love & Romance Report using the design system. "
            "Open with an Executive Summary card (❤️ Relationship Style, 🌙 Emotional Nature, 🔥 Passion, 💍 Commitment, 👥 Partners Before Soulmate, ⭐ Love Score). "
            "Include a Cosmic Snapshot table, Key Theme cards, Strengths checklist, Challenges warnings, "
            "Love Timeline with star ratings, Compatibility Blueprint comparison table (including Partners Before Soulmate), and a Final Essence poetic closing. "
            "Use visual rhythm — alternate between tables, cards, callouts, and short paragraphs. Never write essay-style."
        ),
        "marriage": (
            "Generate a premium Marriage & Spouse Report using the design system. "
            "Open with an Executive Summary card (💍 Marriage Readiness, 👤 Spouse Nature, 📅 Timing Window, 🏠 Domestic Harmony, ⭐ Marriage Score). "
            "Include a Cosmic Snapshot table, Spouse Profile card, Marriage Timeline with year ratings, "
            "Dosha Assessment status cards, Post-Marriage scoring grid, Ideal Partner Profile card, Marriage Type & Meeting Circumstances analysis, and a Final Essence closing. "
            "Use visual rhythm — alternate between tables, cards, callouts, and short paragraphs. Never write essay-style."
        ),
        "health": (
            "Generate a premium Health & Vitality Report using the design system. "
            "Start with the medical disclaimer as a callout block. "
            "Open with an Executive Summary card (💪 Constitution, 🧠 Mental Wellness, ⚡ Vitality, 🛡 Immunity, ⭐ Health Score). "
            "Include a Planetary Health Scorecard table, Vulnerability Map warning cards, Mental Health callout with scoring, "
            "Health Timeline calendar, Wellness Protocol checklist, and a Vitality Essence closing. "
            "Use visual rhythm — alternate between tables, cards, callouts, and short paragraphs. Never write essay-style."
        ),
        "life-guidance": (
            "Generate a premium Life Guidance Report using the design system. "
            "Open with an Executive Summary card (🔱 Dharma, 💰 Artha, ❤️ Kama, 🕉️ Moksha + scores). "
            "Include a Life Balance 4-quadrant scoring table, Soul Purpose callout card, "
            "Life Theme cards per Purushartha, Current Phase timeline, Growth Edges warnings, and a Life Mantra poetic closing. "
            "Use visual rhythm — alternate between tables, cards, callouts, and short paragraphs. Never write essay-style."
        ),
        "remedies": (
            "Generate a premium Vedic Remedies Report using the design system. "
            "Open with a Planetary Health Scorecard table (Planet | Dignity | Status ✅/⚠/❌ | Priority). "
            "For each afflicted planet, create structured remedy cards with subsections (💎 Gemstone, 🔔 Mantra, 🙏 Behavioral, 📘 Lal Kitab). "
            "Include Dosha status assessments, Current Dasha urgency-ranked checklist, Daily Practice schedule table, "
            "and a Remedy Priority top-5 list with urgency badges. "
            "Use visual rhythm — alternate between tables, cards, callouts, and short paragraphs. Never write essay-style."
        ),
        "annual-forecast": (
            "Generate a premium Annual Forecast Report using the design system. "
            "Open with a Year Overview card (Theme + dominant energy + overall rating). "
            "Include a Major Transits table (Planet | House | Duration | Impact), "
            "Month-by-Month compact cards (each with Rating 🟢/🟡/🔴, Key Event, Best For, Caution), "
            "Domain forecast scoring tables for Career/Love/Health with best months highlighted, "
            "and a Year Power Mantra poetic closing. "
            "Use visual rhythm — alternate between tables, cards, callouts, and short paragraphs. Never write essay-style."
        ),
        "weekly-forecast": (
            "Generate a premium Weekly Forecast using the design system. "
            "IMPORTANT: Perform a complete quality-control review to ensure this report satisfies an experienced Jyotish practitioner. "
            "For every statement, verify that it is astronomically correct, astrologically justified, and derived from the natal chart and transits. "
            "Eliminate generic Barnum statements and fluffy phrasing (e.g. 'the cosmos wants'). Every interpretation must explain the exact chain of reasoning (WHY) by referencing specific planets, houses, lords, dashas, and transits. "
            "Open with a Week Overview card (Theme + rating + dominant energy + dasha status). "
            "Include 7 Day-by-Day sections: for each day, display a table (Moon transit + Key Energy + Best For + Avoid + Rating + Confidence Level) followed by a detailed paragraph separating the analysis into three distinct layers: LEVEL 1 (Verified Chart Facts), LEVEL 2 (Traditional Vedic Interpretation), and LEVEL 3 (Modern Symbolic/Psychological Interpretation). "
            "Include Domain Snapshots with confidence levels: Career (10th/2nd/11th houses, lords, yogas, dashas), Love (Venus, 7th lord, Darakaraka, D9, dashas), Health (6th/8th houses, Saturn, Mars, Moon), and Spiritual. "
            "Include a technically justified Lucky Elements table and a technically derived Week's Cosmic Message poetic closing. "
            "Use visual rhythm — alternate between tables, cards, callouts, and short paragraphs. Never write essay-style."
        ),
    }

    if report_type and report_type in _REPORT_USER_MESSAGES:
        user_msg = _REPORT_USER_MESSAGES[report_type]
        if question:
            user_msg += f"\n\nAdditionally, the user has a specific focus: '{question}'"
        return user_msg

    # Fallback: generic reading
    user_msg = "Please generate a complete birth reading. "
    if question:
        user_msg += f"Focus particularly on this user question: '{question}'"
    else:
        user_msg += (
            "Include sections on Ascendant & personality, core mental filters (Moon Nakshatra), "
            "active Yogas/Doshas, and the current Mahadasha cycle."
        )
    return user_msg

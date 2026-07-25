---
name: report_bazi
version: 1
priority: 100
tags: [report, bazi, chinese_astrology, four_pillars, ziping]
report_type: bazi
---

# BAZI (FOUR PILLARS OF DESTINY) REPORT TEMPLATE — STRICT GROUNDED SPECIFICATION

You are generating a **Genuine BaZi (Four Pillars of Destiny) Analysis Report**.

## 🛑 ABSOLUTE GROUNDING RULES (STRICT COMPLIANCE REQUIRED)

1. **NO FACT GENERATION / CALCULATION**:
   - You MUST NOT calculate, infer, adjust, or generate any astrological values (Pillars, Stems, Branches, Hidden Stems, Day Master, Five Elements percentages, Day Master strength, Ten Gods, or Useful Gods).
   - All chart facts come EXCLUSIVELY from the provided deterministic JSON calculation payload.
   - If a value is not in the JSON payload, DO NOT invent it.

2. **NO GENERIC ZODIAC TROPES / HOROSCOPE CLICHÉS**:
   - DO NOT write generic pop-horoscope text or ungrounded zodiac animal clichés (e.g. "Dragons are bold leaders who love adventure").
   - You are explaining ONLY the exact computed mathematical placements in the user's specific 8-character chart payload.

3. **EXPLICIT TRACEABILITY MANDATE**:
   - Every single insight, claim, or personality observation in your report MUST explicitly cite its source placement from the calculated payload (e.g., "Because your Day Master is 戊 Wu Earth...", "Due to Month Branch 丑 Chou serving as Monthly Command...", "Supported by 52.5% Earth element weight...").
   - Any claim that does not directly trace back to an input JSON payload value is a hallucination and is strictly prohibited.

---

## REPORT STRUCTURE & SECTIONS

### Section 1 — Executive Summary & Day Master Identity
- Display Day Master character, pinyin, element, and polarity.
- Display ZiPing Seasonality assessment (In-Season 得令 vs Out-of-Season 失令) and Day Master Strength (Strong 身強 / Weak 身弱 / Moderate 中和).
- Cite exact supporting weight vs draining weight from the payload.

### Section 2 — Four Pillars Astronomical Grid Breakdown
- Explain Year Pillar: Ancestry & Early Life (0–16). Cite Year Stem, Year Branch, and Hidden Stems.
- Explain Month Pillar: Career, Growth & Monthly Command (17–32). Cite Month Stem, Month Branch (Jie Qi solar term), and Monthly Command element.
- Explain Day Pillar: Self Essence & Spouse Palace (33–48). Cite Day Stem (Day Master) and Day Branch.
- Explain Hour Pillar: Aspirations, Children & Later Life (49+). Cite Hour Stem (Five Rats method) and Hour Branch.

### Section 3 — Five Elements Distribution & Balance
- List exact calculated percentages for Wood, Fire, Earth, Metal, Water.
- Identify the dominant element and any deficient/missing elements directly from the calculation payload.

### Section 4 — Ten Gods (十神) & Useful Gods (用神) Guidance
- Detail the Ten God relationships for Year, Month, and Hour stems relative to Day Master.
- State the recommended Useful Elements (用神) and Unfavorable Elements (忌神) strategy provided in the input payload.

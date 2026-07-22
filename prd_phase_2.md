# Product Requirement Document (PRD) — Cosmic Hub Phase 2

This document details the product requirements and implementation steps for Phase 2 of the Cosmic Hub Report Engine.

---

## 1. North Indian SVG Birth Chart Wheel (Frontend & Backend)

### Objective
Provide users with an elegant, interactive visual chart representing their planetary placements in the traditional North Indian diamond-chart style, rendered dynamically in dark mode with glassmorphism hover highlights.

### Functional Requirements
* **Vedic Chart Format**: The North Indian chart is a diamond-based layout of 12 houses. House 1 is always the top central diamond. The numbers written inside the houses represent the Zodiac sign indices (1 = Aries, 2 = Taurus ... 12 = Pisces).
* **SVG Layout**: Build a clean, responsive SVG component in the React frontend.
* **Planetary Mapping**: Map all planets (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu, Lagna/Ascendant) into their calculated Vedic house placements.
* **Interactive Tooltips**: Hovering over a planet or house displays a tooltip with planetary degrees, Nakshatras, and a brief description.

### Implementation Steps
1. Create a React component `apps/web/src/components/astrology/chart-wheel.tsx` which renders the traditional North Indian diamond lattice.
2. Feed calculations from the `/astrology/reading` payload (specifically `calculation.chart.planets` and `calculation.chart.ascendant`) to calculate houses and place planet symbols/names in correct SVG quadrants.
3. Add interactive tooltips displaying planet degrees, signs, and house meanings on hover.

---

## 2. Vedic Partnership Compatibility Matcher (Synastry Engine)

### Objective
Enable users to compare compatibility scores between two birth charts using the classical Vedic **Ashta Kuta (36 Gunas)** matching system.

### Functional Requirements
* **Endpoint**: Create `POST /astrology/compatibility` accepting two birth charts or profile IDs.
* **Ashta Kuta Calculations**: Determine the Moon Nakshatra and Pada for both charts and calculate the 8 classical compatibility categories:
  1. **Varna** (Spiritual capacity) — 1 point
  2. **Vashya** (Mutual attraction) — 2 points
  3. **Tara** (Life span / health) — 3 points
  4. **Yoni** (Physical / sexual intimacy) — 4 points
  5. **Graha Maitri** (Intellectual friendship of lords) — 5 points
  6. **Gana** (Temperaments: Deva, Manushya, Rakshasa) — 6 points
  7. **Bhakoot** (Emotional compatibility / relative house placement) — 7 points
  8. **Nadi** (Genetics / physical health compatibility) — 8 points
* **Total score**: Return out of 36 points. (A score of 18+ is compatible; 28+ is an excellent match).
* **AI Analysis Narrative**: Pass the numerical results to DeepSeek to generate a premium compatibility narrative (Strengths, Challenges, Actionable partnership advice).

### Implementation Steps
1. Add `guna_milan.py` inside `apps/api/app/astrology` implementing the Nakshatra relationship matrices for the 8 Kutas.
2. Create `POST /astrology/compatibility` in `astrology.py` to calculate Gunas and invoke the LLM for the compatibility narrative.
3. Build a React interface tab `apps/web/src/components/astrology/compatibility-panel.tsx` to select two profiles, view Guna score cards, and read the premium compatibility report.

---

## 3. Daily Planetary Transit Tracker (Dynamic Dashboard)

### Objective
Allow users to track how *today's* planetary alignments interact with their birth chart placements, providing daily dynamic horoscopes.

### Functional Requirements
* **Endpoint**: Create `POST /astrology/transit` taking a birth chart and current date.
* **Transit Calculations**: Compute planetary longitudes for the current UTC date. Map these current transit planets into the user's natal houses (e.g. transit Jupiter in the natal 10th house of career).
* **Aspect Detections**: Detect transit planets conjunct (same house) or aspecting (mutual aspect) natal placements.
* **Dynamic Daily Horoscope**: Feed these transits to DeepSeek to write a brief, actionable daily guidance summary.

### Implementation Steps
1. Add transit calculator functions inside `calculator.py` using Swiss Ephemeris for current date.
2. Create `/astrology/transit` endpoint in `astrology.py` returning natal-to-transit matches.
3. Build a "Daily Cosmic Transit Guidance" widget on the frontend dashboard displaying today's transit alignments.

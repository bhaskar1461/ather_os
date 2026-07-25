# Chinese Astrology (BaZi / Four Pillars of Destiny) Feature Specification — Ather OS

## Overview
This document specifies the architecture, calendrical rules, astronomical calculations, and LLM narrative grounding rules for the genuine BaZi (Four Pillars of Destiny) feature in Ather OS.

---

## 1. Calendrical & Astronomical Rules

### 1.1 Year Boundary (Lichun 立春)
- **Rule**: The BaZi solar year starts precisely at the solar term **Lichun (立春)**, when solar ecliptic longitude reaches **315.0°**, calculated via Swiss Ephemeris (`pyswisseph`).
- **Edge Case**: Births in January or early February before Lichun (solar longitude < 315°) belong to the previous solar BaZi year.
- **Explicit Choice**: We do NOT use Lunar New Year (the lunar calendar boundary popular in western horoscopes). The solar Lichun boundary is strictly enforced.

### 1.2 Month Boundary (12 Principal Solar Terms Jie Qi 節氣)
- **Rule**: Month Branches are bounded by the 12 principal solar terms based on exact solar ecliptic longitude:
  - Month 1 (Yin 寅): 315° to 345° (Lichun)
  - Month 2 (Mao 卯): 345° to 0° (Jingzhe)
  - Month 3 (Chen 辰): 0° to 15° (Qingming)
  - Month 4 (Si 巳): 15° to 45° (Lixia)
  - Month 5 (Wu 午): 45° to 75° (Mangzhong)
  - Month 6 (Wei 未): 75° to 105° (Xiaoshu)
  - Month 7 (Shen 申): 105° to 135° (Liqiu)
  - Month 8 (You 酉): 135° to 165° (Bailu)
  - Month 9 (Xu 戌): 165° to 195° (Hanlu)
  - Month 10 (Hai 亥): 195° to 225° (Lidong)
  - Month 11 (Zi 子): 225° to 255° (Daxue)
  - Month 12 (Chou 丑): 255° to 315° (Xiaohan)
- **Month Stem**: Derived via the **Five Tigers Rule (五虎遁)** based on Year Stem.

### 1.3 Day Boundary (Traditional Zi-Hour Shift 23:00)
- **Rule**: Day Pillar calculation uses Julian Day sexagenary cycle formula `(int(JD + 0.5) + 49) % 60`.
- ** Zi-Hour Shift**: Births between 23:00 and 24:00 (Zi hour) advance the Day Stem & Day Branch to the next calendar day.

### 1.4 Hour Pillar (Five Rats Method 五鼠遁)
- **Rule**: Hour Branch is determined by local birth time bi-hourly periods (23:00-01:00 Zi, 01:00-03:00 Chou, etc.).
- **Hour Stem**: Derived deterministically via the **Five Rats Rule (五鼠遁)**: `hour_stem = ((day_stem % 5) * 2 + hour_branch) % 10`.

---

## 2. Five Elements & ZiPing Day Master Analysis

### 2.1 Element Weightings & Counts
- Stems: 1.0 point each.
- Hidden Stems (藏干 Cáng Gān): Main hidden stem 0.6–1.0, Middle hidden stem 0.3, Residual hidden stem 0.1.

### 2.2 Day Master Strength (ZiPing Seasonality Method 子平得令法)
- **In-Season (得令)**: Day Master element matches or is produced by the Monthly Command (月令, Month Branch element).
- **Strength Assessment**: Evaluates supporting weight (Self + Resource) vs. draining weight (Wealth + Officer + Output):
  - Supporting ≥ 52%: **Strong (身強)**
  - Supporting ≤ 38%: **Weak (身弱)**
  - Otherwise: **Moderate / Balanced (中和)**
- **Useful Gods (用神 Yong Shen)**:
  - Strong Day Master: Regulate with Output, Wealth, or Officer.
  - Weak Day Master: Support with Resource or Peer elements.

---

## 3. LLM Narrative & Interpretation Grounding Audit Rules

### 3.1 Prose Only, Zero Fact Generation
- The LLM writes narrative prose ONLY.
- The LLM MUST NEVER calculate, infer, adjust, or generate Four Pillars, Stems, Branches, Elements, Day Master, or Strength Assessment.
- All chart facts come EXCLUSIVELY from the deterministic Python calculation code (`bazi_engine.py` & `bazi_analysis.py`).

### 3.2 Structured Input & Anti-Trope Prompting
- The LLM prompt template (`prompts/reports/bazi.md`) passes the exact computed JSON object.
- The prompt explicitly forbids open-ended zodiac clichés (e.g. generic "Wood Dragon" horoscope text) and instructs the model to explain ONLY the provided computed values.

### 3.3 Strict Traceability Mandate
- Every claim in the output narrative MUST explicitly trace back to a specific calculated placement in the input payload (e.g., Year Pillar, Day Master, Month Branch, Element score).
- Any ungrounded assertion or generic personality trope is classified as a hallucination and is strictly prohibited.

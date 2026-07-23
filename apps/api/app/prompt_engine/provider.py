"""
Provider Abstraction Layer

Base class, mock provider, and AWS Bedrock Kimi provider for AI model interaction.
"""

import asyncio
import json
import time
import httpx
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Any

try:
    import boto3
except ImportError:
    boto3 = None

from app.prompt_engine.types import CompiledPrompt
from app.config import get_settings
from app.middleware.logging import get_logger

logger = get_logger("provider")

# Shared HTTP Client for Bedrock completions to enable connection pooling and Keep-Alive
_BEDROCK_HTTP_CLIENT = httpx.AsyncClient(
    limits=httpx.Limits(max_keepalive_connections=50, max_connections=200),
    timeout=120.0
)



class BaseProvider(ABC):
    """
    Abstract base class for AI model providers.
    All providers must implement generate() and stream().
    """

    @abstractmethod
    async def generate(self, prompt: CompiledPrompt) -> dict[str, Any]:
        """
        Send the compiled prompt and return the complete response.

        Returns:
            Dictionary with keys: content, prompt_tokens, completion_tokens,
            total_tokens, latency_ms, model, provider.
        """
        ...

    @abstractmethod
    async def stream(self, prompt: CompiledPrompt) -> AsyncGenerator[str, None]:
        """
        Stream the response token-by-token (or chunk-by-chunk).

        Yields:
            SSE-formatted strings: 'data: {"content": "..."}\n\n'
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the provider connection is working."""
        ...


class MockProvider(BaseProvider):
    """
    Mock AI provider that returns pre-defined rich responses.
    Used for developing and testing the UI without real API calls.
    Detects report type from system prompt keywords to return
    category-specific mock responses for Cosmic Hub reports.
    """

    _REPORT_MOCK_RESPONSES: dict[str, str] = {
        "personality": """# 🪷 Personality Deep-Dive Report

## The Ascendant Blueprint — Your Outer Self

Your **Lagna (Ascendant)** is the mask you wear in the world — the first impression others receive. Based on your calculated rising sign, you project an energy of **natural authority and warmth**. The element of your Ascendant shapes your physical vitality and approach to life.

**Lagna Lord Placement**: Your Ascendant lord's placement in the chart redirects your personality focus. Its house position reveals where you invest your primary life energy and how others perceive your core motivation.

> Your rising sign is not just a label — it is the lens through which your entire chart expresses itself.

---

## The Inner Mind — Moon Sign & Nakshatra

Your **Moon Nakshatra** is the single most defining factor of your emotional personality in Vedic astrology. It determines:

- **Emotional wiring**: How you process feelings and react under stress
- **Subconscious patterns**: The mental filters shaped in early childhood
- **Intuitive style**: Whether you lead with logic, empathy, or instinct

Your Moon's **Pada (quarter)** further refines this, connecting to a specific Navamsa sign that colors your emotional sub-expression.

---

## The Solar Identity — Ego & Purpose

Your **Sun sign** reveals your ego structure — how you assert authority, where you seek recognition, and what fuels your sense of purpose. The Sun's dignity (exalted, own sign, or debilitated) directly impacts your confidence levels and leadership capacity.

---

## Atmakaraka — The Soul's Deepest Desire

The **Atmakaraka** (the planet with the highest degree in your chart, excluding Rahu/Ketu) reveals your soul's primary craving in this lifetime. This is the planet that holds the key to your spiritual evolution and the lessons you are here to master.

---

## Planetary Temperament Profile

Based on your chart's planetary distribution, your dominant temperament can be classified as:

| Guna | Influence | Expression |
|------|-----------|------------|
| **Sattva** | Wisdom, purity | Jupiter, Sun, Moon dominant |
| **Rajas** | Action, desire | Venus, Mercury dominant |
| **Tamas** | Stability, inertia | Saturn, Mars, Rahu/Ketu dominant |

Your chart shows a clear emphasis on certain planetary energies that shape your personality archetype.

---

## Current Psychological Phase

Your active **Mahadasha** period determines which aspects of your personality are currently amplified. This Dasha lens colors everything — from decision-making style to emotional availability to creative output.

> **Core Identity Summary**: You are a person of deep inner conviction, natural leadership instinct, and emotional intelligence. Your chart reveals a soul navigating between worldly ambition and inner wisdom, with the tools to master both.""",

        "career": """# 💼 Career & Professional Destiny Report

## The 10th House — Your Public Stage

Your **10th house** (Karma Bhava) is the cornerstone of professional destiny in Vedic astrology. The sign on your 10th cusp defines the arena where you build your public reputation, and the planets occupying or aspecting this house shape your career trajectory.

**10th Lord Placement**: Where your 10th lord sits reveals where your career energy naturally flows — whether toward leadership, service, creative expression, or analytical work.

---

## Dashamsa Chart (D-10) — The Professional Micro-Map

The **Dashamsa** is the divisional chart specifically designed for career analysis. Its Ascendant reveals your professional personality, and key planet placements show what kind of work environment brings you success.

| D-10 Factor | Career Implication |
|-------------|-------------------|
| D-10 Ascendant | Professional self-image |
| D-10 10th Lord | Refined career direction |
| Planets in D-10 Kendras | Areas of professional strength |
| Raj Yogas in D-10 | Potential for authority and recognition |

---

## Planetary Career Indicators

Each planet carries specific professional significations:

- **Sun**: Government, authority, administration, leadership
- **Mercury**: Communication, tech, commerce, analysis
- **Saturn**: Structure, engineering, law, long-term building
- **Jupiter**: Teaching, finance, consulting, wisdom-based roles
- **Mars**: Entrepreneurship, surgery, military, sports, engineering

Your chart's **strongest career planet** determines your competitive edge.

---

## Professional Strengths & Ideal Fields

Based on your chart configuration, the following career fields are naturally aligned:

1. Fields connected to your 10th house sign's natural domain
2. Industries ruled by your strongest career planet
3. Roles that leverage your Dashamsa configurations

---

## Career Timing — Dasha Windows

Your current **Mahadasha/Antardasha** cycle determines the timing of career peaks, transitions, and growth opportunities.

| Period Type | What It Means |
|-------------|--------------|
| 10th Lord Dasha | Peak career activation |
| Saturn Dasha | Long-term building, discipline |
| Jupiter Dasha | Expansion, promotions, growth |
| Sun Dasha | Authority, recognition, government |

> **Career Action Blueprint**: Focus on leveraging your current Dasha energy. The planetary alignments suggest strategic growth over rapid expansion — build foundations now for long-term professional mastery.""",

        "love": """# 💕 Love & Romance Report

## Venus — Your Love Signature

**Venus** is the primary karaka (significator) for love, beauty, and romantic expression in Vedic astrology. Your Venus placement reveals:

- **Romantic personality**: How you express affection and what you find attractive
- **Love language**: Whether you lead with words, touch, gifts, or quality time
- **Relationship values**: What you prioritize in a partner — loyalty, intellect, passion, or stability

Venus's dignity (exalted, own sign, debilitated) directly determines the **quality** of your romantic experiences.

---

## The 5th House — Courtship & Romance

The **5th house** governs romance before commitment — flirtation, dating, creative expression in love, and the initial spark of attraction.

Your 5th house configuration reveals:
- Whether you are a bold initiator or a patient observer in romance
- Your creative expression of love
- How past-life merits (Purva Punya) manifest in romantic blessings

---

## The 7th House — Partnership Dynamics

While the 5th house is about romance, the **7th house** reveals the partnership that romance leads to. Your 7th house sign describes the type of partner you naturally attract.

---

## Attraction Patterns & Emotional Wiring

| Factor | Romantic Influence |
|--------|-------------------|
| **Moon Sign** | Emotional needs in relationships |
| **Mars** | Desire nature and assertiveness |
| **Rahu/Ketu Axis** | Karmic attraction patterns |
| **Venus-Mars Interaction** | Chemistry and passion dynamics |

---

## Love Timing — When Romance Activates

Your Dasha periods reveal **windows of heightened romantic potential**:

- **Venus Dasha/Antardasha**: Peak romantic activation
- **5th/7th Lord periods**: Relationship milestones
- **Jupiter transits through 5th/7th**: Expansion of love

> **Love Essence**: Your heart seeks a love that is both intellectually stimulating and emotionally safe — a partnership where depth of soul meets warmth of presence.""",

        "marriage": """# 💍 Marriage & Spouse Report

## The 7th House — Marriage Foundation

The **7th house** is the primary indicator of marriage, partnerships, and the spouse in Vedic astrology. The sign on your 7th cusp describes:
- The type of partner you attract
- The dynamics of your married life
- How you relate to committed partnerships

**7th Lord Placement**: Where your 7th lord sits reveals where marriage energy flows in your life.

---

## Navamsa Chart (D-9) — The Marriage Blueprint

The **Navamsa** is called the "chart of the spouse" and is the most important divisional chart for marriage analysis.

| Navamsa Factor | Marriage Significance |
|----------------|----------------------|
| D-9 Ascendant | Your married personality |
| Venus in D-9 | Quality of marital love |
| D-9 7th Lord | Deeper spouse characteristics |
| Vargottama planets | Consistent energies in marriage |

---

## Upapada Lagna — Spouse Characteristics

The **Upapada Lagna (UL)** is a Jaimini technique that reveals detailed characteristics of the spouse:
- Physical appearance tendencies
- Personality and temperament
- Professional background
- The 2nd from UL reveals marriage longevity

---

## Darakaraka — The Spouse Significator

Your **Darakaraka** (the planet with the lowest degree) represents the spouse's fundamental nature. Its sign, house, and Nakshatra placement paint a portrait of your life partner.

---

## Marriage Timing

Classical timing techniques for marriage:
1. **Dasha of 7th Lord/Venus/Jupiter**: Primary activation
2. **Double Transit**: When both Jupiter AND Saturn aspect the 7th house/lord
3. **Transit triggers**: Venus transits through the 7th house

---

## Doshas & Challenges

| Dosha | Status | Impact |
|-------|--------|--------|
| Manglik Dosha | Checked from Lagna, Moon, Venus | Marriage dynamics |
| Kaal Sarp Dosha | If Rahu-Ketu hemming present | Fluctuations in partnership |
| Saturn on 7th | If applicable | Delays, maturity in marriage |

> **Marriage Destiny Summary**: Your chart reveals a partnership journey that deepens with maturity. The cosmic design favors a marriage built on mutual respect, intellectual connection, and shared spiritual growth.""",

        "health": """# 🏥 Health & Vitality Report

> *⚠️ Disclaimer: This report provides insights based on traditional Vedic astrological health correlations and Ayurvedic principles. It is NOT a medical diagnosis or substitute for professional medical advice. Always consult qualified healthcare professionals for health concerns.*

## Constitutional Analysis (Prakriti)

Your Ascendant's element determines your **Ayurvedic dosha tendency**:

| Element | Signs | Dosha | Characteristics |
|---------|-------|-------|----------------|
| Fire | Aries, Leo, Sagittarius | Pitta | Heat, metabolism, transformation |
| Earth | Taurus, Virgo, Capricorn | Kapha | Stability, strength, endurance |
| Air | Gemini, Libra, Aquarius | Vata | Movement, flexibility, nervousness |
| Water | Cancer, Scorpio, Pisces | Kapha-Pitta | Emotional, fluid, protective |

---

## Lagna Lord — The Vitality Indicator

Your **Lagna lord's** strength is the primary indicator of overall health and constitutional robustness. Its dignity, house placement, and aspects determine how resilient your body is against disease.

---

## The 6th House — Disease & Immunity

The **6th house** governs:
- Daily health routines
- Immune system strength
- Types of diseases one is susceptible to
- Recovery capacity

---

## Planetary Body-Part Correlations

Each planet governs specific body systems:

| Planet | Body Areas |
|--------|-----------|
| **Sun** | Heart, spine, eyes, vitality |
| **Moon** | Mind, stomach, fluids, hormones |
| **Mars** | Blood, muscles, inflammation |
| **Mercury** | Nervous system, skin, lungs |
| **Jupiter** | Liver, fat tissue, diabetes |
| **Saturn** | Joints, teeth, chronic conditions |
| **Venus** | Kidneys, reproductive system |
| **Rahu** | Unusual conditions, toxins |
| **Ketu** | Infections, mysterious ailments |

Afflicted planets in your chart highlight specific **areas to monitor**.

---

## Mental & Emotional Health

Your Moon's condition directly impacts mental wellness:
- Moon strength = emotional resilience
- Moon afflictions = anxiety, mood fluctuations
- 4th house condition = inner peace capacity

> **Vitality Summary**: Your chart indicates a fundamentally resilient constitution with specific areas that benefit from preventive attention. Alignment with your Ayurvedic dosha through diet and lifestyle will strengthen your natural vitality.""",

        "life-guidance": """# 🧭 Life Guidance Report — The Four Pillars

## The Four Purusharthas

Vedic astrology views life through **four fundamental aims** — each governed by specific houses in your chart:

### 🔱 Dharma (Purpose) — Houses 1, 5, 9
Your **life purpose** is revealed through the trinity of Dharma houses:
- **1st House**: Your core identity mission
- **5th House**: Creative expression and past-life merits
- **9th House**: Higher wisdom, teachers, and spiritual values

### 💰 Artha (Prosperity) — Houses 2, 6, 10
Your **material security** path:
- **2nd House**: Family wealth and values
- **6th House**: Service and daily effort
- **10th House**: Career and public status

### ❤️ Kama (Desire) — Houses 3, 7, 11
Your **desire fulfillment** pattern:
- **3rd House**: Motivation and courage
- **7th House**: Partnerships and relationships
- **11th House**: Gains and aspirations achieved

### 🕉️ Moksha (Liberation) — Houses 4, 8, 12
Your **spiritual path**:
- **4th House**: Inner peace foundation
- **8th House**: Transformation through crisis
- **12th House**: Surrender and transcendence

---

## The Soul's Purpose — Atmakaraka

Your **Atmakaraka** planet reveals the deepest soul craving this lifetime. Its Navamsa placement (Karakamsa) shows what the soul is working to master.

---

## Life Balance Assessment

| Purushartha | Strength | Key Planet | Current Activation |
|-------------|----------|------------|-------------------|
| Dharma | Based on 1/5/9 lords | Sun, Jupiter | Via current Dasha |
| Artha | Based on 2/6/10 lords | Saturn, Mercury | Via current transit |
| Kama | Based on 3/7/11 lords | Venus, Mars | Via relationship cycles |
| Moksha | Based on 4/8/12 lords | Moon, Ketu | Via spiritual phases |

---

## Current Life Phase

Your active Dasha determines which Purushartha is currently in focus — guiding your priorities, challenges, and opportunities.

> **Life Mantra**: *"You are here not to choose between purpose and pleasure, but to discover that true fulfillment comes from aligning all four pillars of existence."*""",

        "remedies": """# 🙏 Vedic Remedies Report

## Planetary Health Scorecard

Before prescribing remedies, we first assess each planet's condition:

| Planet | Dignity | House | Afflictions | Status |
|--------|---------|-------|-------------|--------|
| Sun | Varies | — | Combust? Malefic aspects? | ✅/⚠️/❌ |
| Moon | Varies | — | Waning? Rahu/Ketu axis? | ✅/⚠️/❌ |
| Mars | Varies | — | Debilitated? In 6/8/12? | ✅/⚠️/❌ |
| Mercury | Varies | — | Combust? Retrograde? | ✅/⚠️/❌ |
| Jupiter | Varies | — | Afflicted? Functional malefic? | ✅/⚠️/❌ |
| Venus | Varies | — | Combust? Afflicted? | ✅/⚠️/❌ |
| Saturn | Varies | — | In enemy sign? Aspecting Lagna? | ✅/⚠️/❌ |

---

## Priority Remedies — Afflicted Planets

### Gemstone Therapy
For each weak planet, specific gemstones can strengthen its energy:

| Planet | Gemstone | Metal | Finger | Day to Wear |
|--------|----------|-------|--------|-------------|
| Sun | Ruby (Manikya) | Gold | Ring finger | Sunday sunrise |
| Moon | Pearl (Moti) | Silver | Little finger | Monday |
| Mars | Red Coral (Moonga) | Gold/Copper | Ring finger | Tuesday |
| Mercury | Emerald (Panna) | Gold | Little finger | Wednesday |
| Jupiter | Yellow Sapphire (Pukhraj) | Gold | Index finger | Thursday |
| Venus | Diamond/White Sapphire | Platinum/Silver | Middle finger | Friday |
| Saturn | Blue Sapphire (Neelam) | Silver/Panchdhatu | Middle finger | Saturday |

### Mantra Remedies
Each planet has a **Beej Mantra** for daily recitation:
- Recite 108 times on the planet's day
- Best performed during sunrise or sunset
- Use a Rudraksha or crystal mala

### Behavioral Remedies
- **Charity (Daan)**: Specific items donated on the planet's day
- **Fasting**: Weekly fasts aligned with afflicted planet's day
- **Color therapy**: Wearing specific colors on specific days

---

## Dosha-Specific Remedies

For Manglik Dosha, Kaal Sarp Dosha, and other detected doshas, specific pujas and practices are recommended.

---

## Daily Spiritual Practice

A personalized daily routine aligned with your chart:
- **Morning**: Surya Namaskar + planetary mantras
- **Evening**: Meditation + gratitude practice
- **Weekly**: Day-specific observances

> **Remedy Priority List**:
> 1. Strengthen the most afflicted planet first
> 2. Pacify current Dasha lord if challenging
> 3. Address active Doshas
> 4. Enhance the strongest planet for maximum benefit
> 5. Establish a consistent daily spiritual practice""",

        "annual-forecast": """# 📅 Annual Forecast Report

## Year Overview — The Big Picture

Your current **Mahadasha** sets the macro theme for this year, while **Antardasha** transitions mark the chapter breaks. Understanding this cosmic timing helps you work WITH planetary energy rather than against it.

**Year Energy**: This period calls for strategic alignment — knowing when to push forward and when to consolidate.

---

## Major Planetary Transits

### Jupiter Transit
Jupiter spends approximately 13 months in each sign. Its current transit determines which life area receives **expansion and blessings**.

### Saturn Transit
Saturn's transit (~2.5 years per sign) determines which life area faces **restructuring and discipline**. If you're in Sade Sati, this transit is especially significant.

### Rahu-Ketu Axis
The nodal axis (~18 months per sign pair) activates **karmic themes** — what you're obsessively drawn toward (Rahu) and what you need to release (Ketu).

---

## Month-by-Month Forecast

| Month | Key Transit | Focus Area | Energy |
|-------|------------|------------|--------|
| Month 1 | New cycle begins | Fresh starts | 🟢 |
| Month 2 | Building momentum | Career focus | 🟢 |
| Month 3 | Inner reflection | Relationships | 🟡 |
| Month 4 | Expansion phase | Finances | 🟢 |
| Month 5 | Challenge period | Health attention | 🔴 |
| Month 6 | Recovery & growth | Social connections | 🟡 |
| Month 7 | Peak activity | Professional leap | 🟢 |
| Month 8 | Consolidation | Family matters | 🟡 |
| Month 9 | Spiritual depth | Inner work | 🟢 |
| Month 10 | Action window | Major decisions | 🟢 |
| Month 11 | Transition phase | Relationships | 🟡 |
| Month 12 | Year close | Completion & prep | 🟢 |

---

## Career & Finance Forecast
Key professional windows and financial decision timing based on transits through your 10th, 2nd, and 11th houses.

## Love & Relationships Forecast
Romantic peaks and relationship evolution based on Venus transits and 5th/7th house activation.

## Health & Wellness Forecast
Vitality cycles and periods requiring extra health attention.

> **Annual Power Mantra**: *"This is your year to align action with intention — the stars support those who move with purpose and patience."*""",

        "weekly-forecast": """# ✨ Weekly Cosmic Forecast

## Weekly Energy Overview

**Theme**: A week of focused intention and strategic movement.

Your current Dasha lord is actively working through the transit landscape, creating specific windows of opportunity and reflection throughout the coming seven days.

**Overall Week Energy**: 🟢 Favorable

---

## Day-by-Day Highlights

#### Monday
**Moon Transit**: Shifting through a nurturing sign
**Key Energy**: Emotional clarity and domestic focus
**Best For**: Planning, family conversations, self-care
**Avoid**: Confrontational negotiations

#### Tuesday
**Moon Transit**: Moving into an active sign
**Key Energy**: Mars-influenced drive and courage
**Best For**: Physical activity, bold initiatives, tackling backlogs
**Avoid**: Impulsive spending

#### Wednesday
**Moon Transit**: Intellectual sign activation
**Key Energy**: Mercury-influenced communication
**Best For**: Meetings, writing, learning, networking
**Avoid**: Overthinking decisions

#### Thursday
**Moon Transit**: Expansive energy rising
**Key Energy**: Jupiter-influenced wisdom and growth
**Best For**: Spiritual practices, teaching, financial planning
**Avoid**: Overcommitting

#### Friday
**Moon Transit**: Venus-influenced harmony
**Key Energy**: Creative and relational flow
**Best For**: Romance, creative projects, social events
**Avoid**: Excessive indulgence

#### Saturday
**Moon Transit**: Structured energy
**Key Energy**: Saturn-influenced discipline
**Best For**: Deep work, organizing, health routines
**Avoid**: Procrastination

#### Sunday
**Moon Transit**: Solar revitalization
**Key Energy**: Sun-influenced renewal
**Best For**: Rest, reflection, preparing for the week ahead
**Avoid**: Overexertion

---

## Lucky Elements This Week

| Element | Recommendation |
|---------|---------------|
| **Lucky Days** | Thursday & Friday |
| **Lucky Numbers** | 3, 7, 9 |
| **Lucky Colors** | Gold, White, Green |
| **Favorable Direction** | Northeast |

> **Week's Cosmic Message**: *"Move with intention this week — the universe rewards those who align small daily actions with their larger cosmic purpose."*""",
    }

    _DEFAULT_MOCK = """# Vedic Birth Chart Analysis & Cosmic Blueprint

Welcome, seeker of the stars. Based on the calculated positions from the Swiss Ephemeris, your planetary alignments present a highly potent and auspicious combination. Below is a detailed synthesis of your cosmic blueprint.

## 1. Core Identity & Temperament (Ascendant & Moon)

Your **Lagna (Ascendant)** sets the stage for your physical destiny, outer personality, and primary life lessons:

*   **Dharma & Path:** Your Ascendant points towards leadership, creative self-expression, and a strong sense of purpose. You approach the world with natural confidence and courage.
*   **Mental Filter & Emotional Needs:** Your Moon Nakshatra governs your subconscious drives. It reveals a highly intuitive, nurturing mental setup. You process the world through a filter of deep empathy, but must guard against emotional fluctuations.

## 2. Astronomical Longitudes & Strengths

The primary planetary placements computed at your exact birth coordinates show high structural dignity:

| Graha (Planet) | Rashi (Sign) | Degree | Nakshatra (Pada) | Dignity & Strength |
| :--- | :--- | :--- | :--- | :--- |
| **Lagna** | Leo | 14.32° | Purva Phalguni (1) | Self Sign (Sun Lord) |
| **Surya (Sun)** | Aries | 18.45° | Bharani (2) | **Exalted** |
| **Chandra (Moon)** | Cancer | 05.21° | Pushya (1) | **Own Sign** |
| **Guru (Jupiter)** | Taurus | 24.11° | Rohini (4) | Friendly Sign |
| **Shani (Saturn)** | Aquarius | 12.04° | Shatabhisha (2) | **Own Sign** |

## 3. Active Vedic Yogas & Planetary Combinations

Your chart contains key energetic configurations that shape your fortune and intelligence:

1.  **Gaja Kesari Yoga (Moon & Jupiter in Kendras):**
    *   *Significance:* Bestows wisdom, lasting reputation, prosperity, and a highly analytical mind. You possess the capability to overcome challenges through intelligence and grace.
2.  **Ruchaka Yoga (Exalted Mars in Kendra):**
    *   *Significance:* Promotes high leadership capacity, resilience, courage, and athletic capability.

> **Guru's Advice:** "Focus on aligning your daily action with your higher values. You are destined to lead, but your true power lies in serving those around you."

If you have follow-up questions about specific planets, you can ask them in the chat interface below!"""

    def _detect_report_type(self, prompt: CompiledPrompt) -> str | None:
        """Detect report type from system prompt keywords."""
        system_msg = ""
        for msg in prompt.messages:
            if msg["role"] == "system":
                system_msg = msg["content"].lower()
                break

        report_keywords = {
            "personality": ["personality report", "personality deep-dive", "atmakaraka", "temperament profile"],
            "career": ["career report", "career & professional", "dashamsa", "10th house"],
            "love": ["love & romance", "love report", "attraction patterns", "courtship style"],
            "marriage": ["marriage report", "marriage & spouse", "upapada lagna", "darakaraka", "navamsa"],
            "health": ["health report", "health & vitality", "constitutional analysis", "body-part correlations"],
            "life-guidance": ["life guidance", "four purusharthas", "dharma, artha, kama", "purushartha"],
            "remedies": ["remedies report", "vedic remedies", "gemstone therapy", "planetary health scorecard"],
            "annual-forecast": ["annual forecast", "month-by-month forecast", "year-ahead predictions"],
            "weekly-forecast": ["weekly forecast", "day-by-day highlights", "weekly energy overview"],
        }

        for report_type, keywords in report_keywords.items():
            if any(kw in system_msg for kw in keywords):
                return report_type

        return None

    async def generate(self, prompt: CompiledPrompt) -> dict[str, Any]:
        start = time.perf_counter()

        # Simulate processing delay
        await asyncio.sleep(0.5)

        # Detect report type from system prompt
        report_type = self._detect_report_type(prompt)

        if report_type and report_type in self._REPORT_MOCK_RESPONSES:
            content = self._REPORT_MOCK_RESPONSES[report_type]
        else:
            content = self._DEFAULT_MOCK

        latency = int((time.perf_counter() - start) * 1000)
        prompt_tokens = prompt.total_tokens_estimate
        completion_tokens = len(content) // 4

        return {
            "content": content,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_ms": latency,
            "model": prompt.provider_config.model_id,
            "provider": "mock",
        }

    async def stream(self, prompt: CompiledPrompt) -> AsyncGenerator[str, None]:
        result = await self.generate(prompt)
        content = result["content"]

        # Stream in chunks to simulate realistic token delivery
        chunk_size = 3  # characters per chunk
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            data = json.dumps({"content": chunk, "done": False})
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.02)  # ~50 tokens/sec simulation

        # Send final metadata
        final = json.dumps({
            "content": "",
            "done": True,
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "total_tokens": result["total_tokens"],
            "latency_ms": result["latency_ms"],
        })
        yield f"data: {final}\n\n"

    async def health_check(self) -> bool:
        return True


class KimiBedrockProvider(BaseProvider):
    """
    AWS Bedrock model provider integration.

    The application default is Moonshot AI's Kimi K2.5 on Bedrock.
    """

    def __init__(self) -> None:
        # Clear settings cache so .env changes are picked up on every provider init
        get_settings.cache_clear()
        settings = get_settings()
        self.bearer_token = settings.aws_bearer_token_bedrock
        self.region = settings.aws_region_name
        self.default_model = settings.bedrock_model_id
        self.enabled = (
            boto3 is not None and (
                (settings.aws_access_key_id is not None and settings.aws_secret_access_key is not None) or
                settings.aws_bearer_token_bedrock is not None
            )
        )
        logger.info("bedrock_provider_init", enabled=self.enabled, has_bearer_token=bool(self.bearer_token), token_prefix=self.bearer_token[:20] + "..." if self.bearer_token else "None", model=self.default_model)
        if self.enabled:
            if self.bearer_token:
                self.client = None
            else:
                self.client = boto3.client(
                    "bedrock-runtime",
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region_name
                )
        else:
            self.client = None

    def _resolve_model(self, requested_model: str | None) -> str:
        # Allow both Kimi and DeepSeek models
        if requested_model and (requested_model.startswith("moonshotai.kimi-") or requested_model.startswith("deepseek.")):
            return requested_model
        return self.default_model

    async def generate(self, prompt: CompiledPrompt) -> dict[str, Any]:
        if not self.enabled:
            mock = MockProvider()
            return await mock.generate(prompt)

        messages = []
        for msg in prompt.messages:
            messages.append({"role": msg["role"], "content": msg["content"]})

        model_id = self._resolve_model(prompt.provider_config.model_id)

        if self.bearer_token:
            url = f"https://bedrock-mantle.{self.region}.api.aws/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_id,
                "messages": messages,
                "max_tokens": prompt.provider_config.max_tokens,
                "temperature": 0.6,
            }
            start_time = time.perf_counter()
            try:
                response = await _BEDROCK_HTTP_CLIENT.post(url, headers=headers, json=payload)
                response.raise_for_status()
                response_body = response.json()
                content = response_body.get("choices", [{}])[0].get("message", {}).get("content", "")
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                prompt_tokens = response_body.get("usage", {}).get("prompt_tokens", 0)
                completion_tokens = response_body.get("usage", {}).get("completion_tokens", 0)
                return {
                    "content": content,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "latency_ms": latency_ms,
                    "model": model_id,
                    "provider": "bedrock",
                }
            except Exception as e:
                logger.error("bedrock_generate_failed", error=str(e))
                mock = MockProvider()
                return await mock.generate(prompt)
        else:
            if not self.client:
                mock = MockProvider()
                return await mock.generate(prompt)

            payload = {
                "messages": messages,
                "max_tokens": prompt.provider_config.max_tokens,
                "temperature": 0.6,
            }

            start_time = time.perf_counter()
            try:
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.invoke_model(
                        modelId=model_id,
                        body=json.dumps(payload)
                    )
                )
                
                response_body = json.loads(response.get("body").read())
                content = response_body.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                prompt_tokens = response_body.get("usage", {}).get("prompt_tokens", 0)
                completion_tokens = response_body.get("usage", {}).get("completion_tokens", 0)

                return {
                    "content": content,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "latency_ms": latency_ms,
                    "model": model_id,
                    "provider": "bedrock",
                }
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error("bedrock_generate_failed", error=str(e))
                mock = MockProvider()
                return await mock.generate(prompt)

    async def stream(self, prompt: CompiledPrompt) -> AsyncGenerator[str, None]:
        if not self.enabled:
            mock = MockProvider()
            async for chunk in mock.stream(prompt):
                yield chunk
            return

        messages = []
        for msg in prompt.messages:
            messages.append({"role": msg["role"], "content": msg["content"]})

        model_id = self._resolve_model(prompt.provider_config.model_id)

        if self.bearer_token:
            url = f"https://bedrock-mantle.{self.region}.api.aws/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_id,
                "messages": messages,
                "max_tokens": prompt.provider_config.max_tokens,
                "temperature": 0.6,
                "stream": True,
            }
            try:
                async with _BEDROCK_HTTP_CLIENT.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    data_json = json.loads(data_str)
                                    text = data_json.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if text:
                                        data = json.dumps({"content": text, "done": False})
                                        yield f"data: {data}\n\n"
                                except Exception:
                                    pass
                                    
                        final = json.dumps({
                            "content": "",
                            "done": True,
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0,
                            "latency_ms": 0,
                        })
                        yield f"data: {final}\n\n"
                        return
                    else:
                        error_body = await response.aread()
                        logger.warning("bedrock_stream_http_fallback", status=response.status_code, body=error_body.decode()[:200])
                        mock = MockProvider()
                        async for chunk in mock.stream(prompt):
                            yield chunk
                        return
            except Exception as e:
                logger.error("bedrock_stream_exception_fallback", error=str(e))
                mock = MockProvider()
                async for chunk in mock.stream(prompt):
                    yield chunk
                return
        else:
            if not self.client:
                mock = MockProvider()
                async for chunk in mock.stream(prompt):
                    yield chunk
                return

            payload = {
                "messages": messages,
                "max_tokens": prompt.provider_config.max_tokens,
                "temperature": 0.6,
            }

            try:
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.invoke_model_with_response_stream(
                        modelId=model_id,
                        body=json.dumps(payload)
                    )
                )

                stream = response.get("body")
                if stream:
                    for event in stream:
                        chunk = event.get("chunk")
                        if chunk:
                            chunk_data = json.loads(chunk.get("bytes").decode("utf-8"))
                            text = chunk_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if text:
                                data = json.dumps({"content": text, "done": False})
                                yield f"data: {data}\n\n"
                                
                    final = json.dumps({
                        "content": "",
                        "done": True,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "latency_ms": 0,
                    })
                    yield f"data: {final}\n\n"
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error("bedrock_stream_failed", error=str(e))
                mock = MockProvider()
                async for chunk in mock.stream(prompt):
                    yield chunk

    async def health_check(self) -> bool:
        return self.enabled


def get_provider(name: str = "mock") -> BaseProvider:
    """
    Factory function for provider instances.
    """
    providers: dict[str, type[BaseProvider]] = {
        "mock": MockProvider,
        "bedrock": KimiBedrockProvider,
        "kimi": KimiBedrockProvider,
    }
    # Bedrock owns the Kimi K2.5 integration and authentication flow.
    settings = get_settings()
    if name in ["kimi", "bedrock"] or (
        settings.aws_access_key_id is not None and name == "mock"
    ):
        provider_class = KimiBedrockProvider
    else:
        provider_class = providers.get(name, MockProvider)
        
    return provider_class()

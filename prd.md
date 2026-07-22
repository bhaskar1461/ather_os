# Product Requirement Document (PRD) — Cosmic Hub Enhancements

This document outlines the product requirements and step-by-step implementation plan for the next phase of the Cosmic Hub Report Engine.

---

## 1. Premium PDF Export Engine

### Objective
Provide users with a downloadable, high-fidelity PDF version of their generated astrology report. The PDF must look like a premium editorial document, featuring print-ready margins, page numbers, clean page breaks, and elegant typography (matching Apple/Stripe docs aesthetics).

### Functional Requirements
* **API Route**: Create `POST /astrology/reading/{reading_id}/export-pdf` returning the binary PDF stream.
* **HTML Generation**: Convert the stored Markdown reading into clean HTML using a template engine (e.g. Jinja2).
* **Styling & Layout**: 
  * Apply a print-specific CSS sheet (using `@media print` rules).
  * Use a premium serif or clean sans-serif typeface (e.g., Playfair Display or Inter) loaded from local or Google Fonts.
  * Format blockquotes as card structures and checklists as clean bullet components.
  * Enforce page breaks (`page-break-inside: avoid;`) on tables, summaries, and key themes to prevent ugly cuts.
  * Add a cover page featuring a custom celestial graphic and the user's birth summary.
* **Technology**: Use `WeasyPrint` (HTML-to-PDF compiler via CSS Paged Media) or `Playwright` headless PDF generation.

### Step-by-Step Implementation Steps
1. Add `weasyprint` or `playwright` to backend `requirements.txt`.
2. Create a Jinja2 HTML template `app/templates/report_pdf.html` matching the design system.
3. Implement HTML parser in backend to translate Markdown layout blocks (tables, code blocks, checklists) into corresponding HTML tags.
4. Implement the `/export-pdf` route inside `apps/api/app/routers/astrology.py`.
5. Add a "Download PDF" button in the frontend `astrology-panel.tsx` once a reading is generated.

---

## 2. Astrological Cache Layer (Redis)

### Objective
Optimize response latency and decrease API token usage by caching identical readings.

### Functional Requirements
* **Cache Key Formula**: Hash the request parameters: `MD5(year + month + day + hour + minute + latitude + longitude + timezone_offset + report_type + question)`.
* **Caching Strategy**: Cache the final validated reading text and the calculated JSON coordinates.
* **TTL (Time to Live)**: Set cached reports to expire after 7 days.
* **Bypass Option**: Allow administrative bypass for testing (`force_refresh: true` in payload).

### Step-by-Step Implementation Steps
1. Create a cache manager class in `app/redis_manager.py`.
2. Wrap the `get_reading` and `get_reading_v2` routes with a lookup function:
   * Generate MD5 hash of parameters.
   * If key exists in Redis, parse and return the JSON response immediately.
   * If key is missing, proceed to calculation/generation and store the validated result in Redis before returning.
3. Log cache hits vs misses to monitor performance and savings.

---

## 3. Deterministic Scoring Engine

### Objective
Transition from LLM-estimated numerical scores to deterministic, mathematically computed astrological indicators. This guarantees that scorecards (e.g. *Leadership: 95/100*) are fully backable by astronomical reality.

### Functional Requirements
* **Metrics to Pre-calculate**:
  * **Self & Vitality (Lagna Lord Strength)**: Calculate based on planet dignity (exaltation, own sign, debilitation) and house placement.
  * **Mental Peace (4th House & Moon)**: Check aspects from benefics vs malefics, Moon phase strength (waxing vs waning).
  * **Career Potential (10th House & Lord)**: Calculate based on 10th lord placement, planetary occupations, and D-10 alignments.
  * **Wealth capacity (2nd/11th Houses)**: Compute presence of Dhana Yogas, aspect on wealth houses.
* **Data Integration**: Inject these calculated numbers directly into the JSON context (`rules_data`) sent to the LLM system prompt. Enforce that the LLM must output these exact numbers in the scorecard tables.

### Step-by-Step Implementation Steps
1. Add numerical scoring helper functions in `app/astrology/rules.py` (e.g., `calculate_vitality_score()`, `calculate_career_score()`).
2. Update `evaluate_chart_rules()` to aggregate these scores under a `scores` dictionary.
3. Update the report system instruction system prompt in `report_prompts.py` to tell the LLM:
   > *"You must use the exact pre-calculated numerical scores provided in the chart JSON. Do not guess or invent scores."*
4. Run validation checks to verify that the generated markdown contains the exact pre-calculated scores.

---

## 4. Custom Markdown Renderer UI (Frontend)

### Objective
Replace default markdown styling with custom styled UI components (glassmorphism cards, interactive tables, colored checklists) to make the web app feel incredibly premium.

### Functional Requirements
* **Glassmorphism Cards**: Render `>` (blockquotes) as high-end cards with frosted-glass backgrounds, subtle borders, and blur filters.
* **Checklists**: Render `✅` list items as customized grid elements with green checkmark icons.
* **Warning Blocks**: Render `⚠` list items as callout banners with subtle amber borders and caution icons.
* **Custom Tables**: Render Markdown tables with dark-mode styling, sticky headers, and hover highlights.

### Step-by-Step Implementation Steps
1. Update `apps/web/src/components/chat/markdown-renderer.tsx` (or the corresponding markdown renderer).
2. Configure custom components for the Markdown engine (e.g., using `react-markdown` with customized elements for `blockquote`, `table`, and `li`).
3. Add CSS classes to `index.css` defining the custom styles (gradients, animations, glassmorphism filters).

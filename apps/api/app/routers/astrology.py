"""
Astrology Router

Endpoints for deterministic birth chart calculations and AI-based Vedic interpretations.
"""

import json
import hashlib
import asyncio
import re
from datetime import datetime, timezone as dt_tz, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession
from app.redis_manager import get_redis

from packages.database.connection import get_db
from packages.database.models import User
from app.security.dependencies import get_current_user
from app.schemas import AstrologyChartRequest, AstrologyReadingRequest, AstrologyReadingRequestV2, AstrologyPDFExportRequest, CompatibilityRequest, TransitRequest, BaZiChartRequest, BaZiCompatibilityRequest, BaZiCompatibilityChatRequest, KPCalculationRequest, KPHoraryRequest, KPEventTimingRequest, KPEventTimingChatRequest, KPReadingRequest, KPChatRequest

from app.astrology.calculator import calculate_chart_data
from app.astrology.rules import evaluate_chart_rules, calculate_vimshottari_dasha
from app.astrology.bazi_engine import calculate_bazi_pillars
from app.astrology.bazi_analysis import analyze_bazi_chart, calculate_bazi_compatibility
from app.astrology.kp_engine import calculate_kp_chart
from app.astrology.kp_analysis import calculate_kp_significators, calculate_kp_horary
from app.astrology.knowledge import build_knowledge_prompt_context
from app.astrology.validator import validate_reading_placements
from app.astrology.report_prompts import build_report_system_instruction, build_report_user_message
from app.config import get_settings
from app.prompt_engine.types import CompiledPrompt, ProviderConfig
from app.prompt_engine.provider import get_provider
from app.middleware.logging import get_logger

logger = get_logger("astrology")


router = APIRouter(prefix="/astrology", tags=["Astrology"])


@router.post("/chart", summary="Calculate birth chart astronomical coordinates")
def get_chart(
    body: AstrologyChartRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Deterministically computes planet coordinates, nakshatras, divisional charts,
    and Vedic Yogas/Doshas from birth metadata using Swiss Ephemeris.
    """
    try:
        chart_data = calculate_chart_data(
            year=body.year,
            month=body.month,
            day=body.day,
            hour=body.hour,
            minute=body.minute,
            lat=body.latitude,
            lon=body.longitude,
            tz_offset_hours=body.timezone_offset
        )
        rules_data = evaluate_chart_rules(chart_data)
        
        return {
            "status": "success",
            "chart": chart_data,
            "rules": rules_data,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Astrological calculation failure: {str(e)}"
        )


@router.post("/chart/v2", summary="Calculate birth chart from location data")
def get_chart_v2(
    body: AstrologyReadingRequestV2,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    try:
        tz_info = ZoneInfo(body.location_timezone)
        birth_dt = datetime(body.year, body.month, body.day, body.hour, body.minute, tzinfo=tz_info)
        utc_offset = birth_dt.utcoffset()
        tz_offset_hours = utc_offset.total_seconds() / 3600.0 if utc_offset else 0.0

        chart_data = calculate_chart_data(
            year=body.year,
            month=body.month,
            day=body.day,
            hour=body.hour,
            minute=body.minute,
            lat=body.location_lat,
            lon=body.location_lon,
            tz_offset_hours=tz_offset_hours
        )
        rules_data = evaluate_chart_rules(chart_data)
        return {
            "status": "success",
            "chart": chart_data,
            "rules": rules_data,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chart calculation failure: {str(e)}"
        )



def get_reading_cache_key(chart_data: dict, report_type: str | None, question: str | None) -> str:
    """Generate a deterministic Redis cache key using request parameters."""
    bd = chart_data.get("birth_details", {})
    year = bd.get("year", 0)
    month = bd.get("month", 0)
    day = bd.get("day", 0)
    hour = bd.get("hour", 0)
    minute = bd.get("minute", 0)
    lat = bd.get("lat", 0.0)
    lon = bd.get("lon", 0.0)
    tz_offset = bd.get("tz_offset", 0.0)
    
    params_str = (
        f"{year}-{month}-{day}_{hour}:{minute}_"
        f"{lat:.4f}_{lon:.4f}_{tz_offset:.2f}_"
        f"{report_type or ''}_{question or ''}"
    )
    cache_hash = hashlib.md5(params_str.encode("utf-8")).hexdigest()
    return f"reading_cache:{cache_hash}"


async def _generate_reading(
    chart_data: dict,
    rules_data: dict,
    question: str | None,
    report_type: str | None = None,
    force_refresh: bool = False,
) -> dict:
    """
    Shared reading generation pipeline used by both v1 and v2 endpoints.
    Handles knowledge context assembly, prompt compilation, Kimi-on-Bedrock invocation,
    and the self-correction hallucination validation loop.

    When report_type is provided, loads a category-specific prompt template
    (personality, career, love, marriage, health, life-guidance, remedies,
    annual-forecast) that instructs the LLM on what sections to produce
    and what Vedic techniques to focus on.
    """
    # 1. Extract Static Traditional Meanings from Knowledge Base
    knowledge_context = build_knowledge_prompt_context(chart_data, rules_data)

    # 2. Assemble Prompt Instruction (report-type-aware)
    system_instruction = build_report_system_instruction(
        report_type=report_type,
        chart_data=chart_data,
        rules_data=rules_data,
        knowledge_context=knowledge_context,
    )

    user_message = build_report_user_message(report_type, question)

    # Check cache first
    cache_key = get_reading_cache_key(chart_data, report_type, question)
    redis = get_redis()
    
    if not force_refresh:
        try:
            cached_data_str = await redis.get(cache_key)
            if cached_data_str:
                cached_data = json.loads(cached_data_str)
                logger.info("astrology_cache_hit", key=cache_key)
                return {
                    "status": "success",
                    "calculation": {
                        "chart": chart_data,
                        "rules": rules_data,
                    },
                    "reading": cached_data["reading"],
                    "validation_attempts": cached_data.get("validation_attempts", 1),
                    "validated_clean": cached_data.get("validated_clean", True),
                    "cached": True
                }
        except Exception as e:
            logger.error("astrology_cache_read_error", error=str(e))

    # 3. Generate & Validate Response Loop (Self-Correction for Hallucinations)
    provider_config = ProviderConfig(provider_name="bedrock", model_id=get_settings().bedrock_model_id, max_tokens=8192)
    provider = get_provider("bedrock")

    attempt = 1
    max_attempts = 3
    current_system_instruction = system_instruction
    final_reading = ""

    while attempt <= max_attempts:
        messages = [
            {"role": "system", "content": current_system_instruction},
            {"role": "user", "content": user_message}
        ]
        compiled_prompt = CompiledPrompt(
            messages=messages,
            provider_config=provider_config,
            total_tokens_estimate=len(current_system_instruction) // 4 + len(user_message) // 4,
        )

        result = await provider.generate(compiled_prompt)
        generated_text = result["content"]

        # Run validator checks
        is_valid, validation_errors = validate_reading_placements(
            generated_text, chart_data, rules_data, report_type=report_type
        )

        if is_valid:
            final_reading = generated_text
            break
        else:
            logger.warning("astrology_validation_failed", attempt=attempt, errors=validation_errors)
            error_summary = "\n".join([f"- {err}" for err in validation_errors])
            current_system_instruction = (
                f"{system_instruction}\n\n"
                "### IMPORTANT CORRECTION FROM VALIDATOR\n"
                "Your previous response failed the validation step due to the following factual errors:\n"
                f"{error_summary}\n\n"
                "Please rewrite the reading. Make absolute sure to fix all these placement errors and do not invent any incorrect zodiac/house positions."
            )
            attempt += 1
            final_reading = generated_text

    # Store in Redis cache
    try:
        cache_payload = {
            "reading": final_reading,
            "validation_attempts": attempt if attempt <= max_attempts else max_attempts,
            "validated_clean": attempt <= max_attempts,
        }
        await redis.set(cache_key, json.dumps(cache_payload), ex=7 * 86400)
        logger.info("astrology_cache_write", key=cache_key)
    except Exception as e:
        logger.error("astrology_cache_write_error", error=str(e))

    return {
        "status": "success",
        "calculation": {
            "chart": chart_data,
            "rules": rules_data,
        },
        "reading": final_reading,
        "validation_attempts": attempt if attempt <= max_attempts else max_attempts,
        "validated_clean": attempt <= max_attempts,
    }


@router.post("/reading", summary="Generate validated natural language birth chart reading")
async def get_reading(
    body: AstrologyReadingRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Processes astronomical coordinates, pulls relevant traditional interpretations,
    invokes Kimi through Amazon Bedrock for natural language generation, and validates
    placements to ensure zero LLM hallucinations.
    """
    try:
        chart_data = calculate_chart_data(
            year=body.year,
            month=body.month,
            day=body.day,
            hour=body.hour,
            minute=body.minute,
            lat=body.latitude,
            lon=body.longitude,
            tz_offset_hours=body.timezone_offset
        )
        rules_data = evaluate_chart_rules(chart_data)
        return await _generate_reading(
            chart_data,
            rules_data,
            body.question,
            report_type=None,
            force_refresh=body.force_refresh
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Astrological reading pipeline error: {str(e)}"
        )


@router.post("/reading/v2", summary="Generate reading from location-resolved birth data")
async def get_reading_v2(
    body: AstrologyReadingRequestV2,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    V2 endpoint that accepts location-resolved data (city name, lat, lon, IANA timezone).
    Automatically computes the UTC offset for the given birth date and timezone,
    accounting for historical DST rules, then delegates to the deterministic pipeline.
    """
    try:
        # Compute the exact UTC offset for this specific date in this timezone
        # This correctly handles historical DST transitions
        tz_info = ZoneInfo(body.location_timezone)
        birth_dt = datetime(body.year, body.month, body.day, body.hour, body.minute, tzinfo=tz_info)
        utc_offset = birth_dt.utcoffset()
        tz_offset_hours = utc_offset.total_seconds() / 3600.0 if utc_offset else 0.0

        chart_data = await asyncio.to_thread(
            calculate_chart_data,
            year=body.year,
            month=body.month,
            day=body.day,
            hour=body.hour,
            minute=body.minute,
            lat=body.location_lat,
            lon=body.location_lon,
            tz_offset_hours=tz_offset_hours
        )
        rules_data = evaluate_chart_rules(chart_data)

        # If client requests JSON instead of streaming
        if not body.stream:
            return await _generate_reading(
                chart_data,
                rules_data,
                body.question,
                report_type=body.report_type,
                force_refresh=body.force_refresh
            )

        # Streaming Mode: Check cache first
        cache_key = get_reading_cache_key(chart_data, report_type=body.report_type, question=body.question)
        redis = get_redis()

        if not body.force_refresh:
            try:
                cached_data_str = await redis.get(cache_key)
                if cached_data_str:
                    cached_data = json.loads(cached_data_str)
                    logger.info("astrology_cache_hit_stream", key=cache_key)
                    
                    async def cached_stream_generator():
                        cached_text = cached_data["reading"]
                        chunk_size = 20
                        for i in range(0, len(cached_text), chunk_size):
                            chunk = cached_text[i:i + chunk_size]
                            data = json.dumps({"content": chunk, "done": False})
                            yield f"data: {data}\n\n"
                            await asyncio.sleep(0.01)
                        final = json.dumps({
                            "content": "",
                            "done": True,
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0,
                            "latency_ms": 0
                        })
                        yield f"data: {final}\n\n"
                        
                    return StreamingResponse(
                        cached_stream_generator(),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                            "X-Accel-Buffering": "no",
                        }
                    )
            except Exception as e:
                logger.error("astrology_cache_read_stream_error", error=str(e))

        # Cache Miss: Generate stream and cache it upon completion
        knowledge_context = build_knowledge_prompt_context(chart_data, rules_data)
        system_instruction = build_report_system_instruction(
            body.report_type,
            chart_data,
            rules_data,
            knowledge_context
        )
        user_message = build_report_user_message(body.report_type, body.question)

        provider_config = ProviderConfig(provider_name="bedrock", model_id=get_settings().bedrock_model_id, max_tokens=8192)
        provider = get_provider("bedrock")

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message}
        ]
        compiled_prompt = CompiledPrompt(
            messages=messages,
            provider_config=provider_config,
            total_tokens_estimate=len(system_instruction) // 4 + len(user_message) // 4,
        )

        async def event_generator_with_caching():
            full_content = ""
            async for chunk in provider.stream(compiled_prompt):
                try:
                    if chunk.startswith("data: "):
                        data_str = chunk[6:].strip()
                        data = json.loads(data_str)
                        if not data.get("done"):
                            full_content += data.get("content", "")
                except Exception:
                    pass
                yield chunk
            
            # Cache completed stream
            try:
                is_valid, _ = validate_reading_placements(
                    full_content, chart_data, rules_data, report_type=body.report_type
                )
                cache_payload = {
                    "reading": full_content,
                    "validation_attempts": 1,
                    "validated_clean": is_valid,
                }
                await redis.set(cache_key, json.dumps(cache_payload), ex=7 * 86400)
                logger.info("astrology_cache_write_stream", key=cache_key)
            except Exception as e:
                logger.error("astrology_cache_write_stream_error", error=str(e))

        return StreamingResponse(
            event_generator_with_caching(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Astrological reading pipeline error: {str(e)}"
        )


def json_to_markdown(json_str: str) -> str:
    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            return json_str
    except Exception:
        # If it's not valid JSON, treat it as raw markdown
        return json_str

    md = []
    
    # Executive Summary
    exec_summary = data.get("executive_summary", {})
    if isinstance(exec_summary, dict):
        metrics = exec_summary.get("metrics", [])
        overall_score = exec_summary.get("overall_score")
        
        if metrics or overall_score is not None:
            md.append('<div class="summary-card">')
            md.append('<div class="summary-title">Executive Summary</div>')
            if overall_score is not None:
                md.append(f'<div class="summary-line"><strong>Overall Score</strong> <strong>{overall_score}/100</strong></div>')
            for m in metrics:
                if isinstance(m, dict):
                    label = m.get("label", "")
                    val = m.get("value", "")
                    rating = m.get("rating", "")
                    rating_str = f" ({rating})" if rating else ""
                    md.append(f'<div class="summary-line"><span>{label}</span> <span>{val}{rating_str}</span></div>')
            md.append('</div>\n')

    # Sections
    sections = data.get("sections", [])
    if isinstance(sections, list):
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            title = sec.get("title", "")
            if title:
                md.append(f"# {title}\n")
            
            components = sec.get("components", [])
            if isinstance(components, list):
                for comp in components:
                    if not isinstance(comp, dict):
                        continue
                    c_type = comp.get("type", "")
                    heading = comp.get("heading", "")
                    content = comp.get("content", "")
                    
                    if c_type == "card":
                        md.append('<div class="theme-card">')
                        if heading:
                            md.append(f'<div class="theme-title">{heading}</div>')
                        # Render content paragraphs
                        paragraphs = str(content).split("\n\n")
                        for p in paragraphs:
                            if p.strip():
                                md.append(f"<p>{p.strip()}</p>")
                        md.append('</div>\n')
                    elif c_type == "callout":
                        md.append('<blockquote>')
                        if heading:
                            md.append(f"<strong>{heading}</strong><br/>")
                        md.append(str(content))
                        md.append('</blockquote>\n')
                    elif c_type in ("table", "timeline"):
                        if heading:
                            md.append(f"### {heading}\n")
                        md.append(str(content))
                        md.append("\n")
                    else:
                        if heading:
                            md.append(f"### {heading}\n")
                        md.append(str(content))
                        md.append("\n")
                
    return "\n".join(md)


@router.post("/reading/export-pdf", summary="Export reading to PDF")
def export_reading_pdf(
    body: AstrologyPDFExportRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Renders the astrological reading into HTML using Markdown, injects it into
    a premium styled Jinja2 template, compiles to PDF via WeasyPrint, and streams
    it back to the user.
    """
    try:
        import markdown
        import weasyprint
        from io import BytesIO
        from pathlib import Path
        from jinja2 import Environment, FileSystemLoader

        # Convert markdown or JSON content to HTML
        final_markdown = json_to_markdown(body.content_markdown)
        html_content = markdown.markdown(
            final_markdown,
            extensions=["tables", "fenced_code", "nl2br"]
        )


        # Setup Jinja2 environment
        templates_dir = Path(__file__).resolve().parent.parent / "templates"
        env = Environment(loader=FileSystemLoader(str(templates_dir)))
        template = env.get_template("report_pdf.html")

        # Render HTML template
        rendered_html = template.render(
            metadata=body.metadata.model_dump(),
            content_html=html_content
        )

        # Compile HTML to PDF bytes using WeasyPrint
        pdf_bytes = weasyprint.HTML(string=rendered_html).write_pdf()

        # Stream PDF back as attachment
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="Cosmic_Hub_Report.pdf"'
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error("pdf_export_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {str(e)}"
        )


async def _generate_llm_response(system_instruction: str, user_message: str) -> str:
    """Helper to execute generic Kimi prompts through Amazon Bedrock."""
    provider_config = ProviderConfig(provider_name="bedrock", model_id=get_settings().bedrock_model_id, max_tokens=16384)
    provider = get_provider("bedrock")
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_message}
    ]
    compiled_prompt = CompiledPrompt(
        messages=messages,
        provider_config=provider_config,
        total_tokens_estimate=len(system_instruction) // 4 + len(user_message) // 4,
    )
    result = await provider.generate(compiled_prompt)
    return result["content"]


def calculate_relationship_suitability(
    score: float,
    breakdown: dict,
    venus_dist: int,
    venus_fav: bool,
    lord_7th_dist: int,
    lord_7th_fav: bool,
    kuja_compatible: bool,
    dk_fav: bool,
    ul_match_a_to_b: str,
    ul_match_b_to_a: str,
    moon_dist: int,
    jup_dist: int
) -> dict:
    """Calculates suitability percentages for four relationship categories."""
    # 1. Romantic/Marriage Score
    romantic_guna = (score / 36.0) * 50.0
    romantic_venus = 15.0 if venus_fav else 0.0
    romantic_lord7 = 15.0 if lord_7th_fav else 0.0
    romantic_kuja = 10.0 if kuja_compatible else 0.0
    
    romantic_jaimini = 0.0
    if dk_fav:
        romantic_jaimini += 5.0
    ul_a_b_has_sync = any(x in ul_match_a_to_b.lower() for x in ["conjunct", "trine", "opposite"])
    ul_b_a_has_sync = any(x in ul_match_b_to_a.lower() for x in ["conjunct", "trine", "opposite"])
    if ul_a_b_has_sync or ul_b_a_has_sync:
        romantic_jaimini += 5.0
        
    romantic_score = romantic_guna + romantic_venus + romantic_lord7 + romantic_kuja + romantic_jaimini

    # 2. Platonic Friendship Score
    friendship_graha = (breakdown.get("graha_maitri", {}).get("score", 0.0) / 5.0) * 30.0
    friendship_gana = (breakdown.get("gana", {}).get("score", 0.0) / 6.0) * 30.0
    
    friendship_placements = 0.0
    if moon_dist in [3, 11]:
        friendship_placements += 10.0
    if venus_dist in [3, 11]:
        friendship_placements += 10.0
        
    friendship_guna = (score / 36.0) * 20.0
    friendship_score = friendship_graha + friendship_gana + friendship_placements + friendship_guna

    # 3. Business & Professional Score
    business_graha = (breakdown.get("graha_maitri", {}).get("score", 0.0) / 5.0) * 25.0
    business_varna = (breakdown.get("varna", {}).get("score", 0.0) / 1.0) * 25.0
    
    business_placements = 0.0
    if moon_dist in [4, 10]:
        business_placements += 15.0
    if lord_7th_dist in [4, 10]:
        business_placements += 15.0
        
    business_guna = (score / 36.0) * 20.0
    business_score = business_graha + business_varna + business_placements + business_guna

    # 4. Mentorship & Growth Score
    mentorship_placements = 0.0
    if moon_dist in [5, 9]:
        mentorship_placements += 15.0
    if lord_7th_dist in [5, 9]:
        mentorship_placements += 15.0
        
    mentorship_jupiter = 30.0 if jup_dist in [1, 5, 7, 9] else 10.0
    mentorship_graha = (breakdown.get("graha_maitri", {}).get("score", 0.0) / 5.0) * 20.0
    mentorship_guna = (score / 36.0) * 20.0
    mentorship_score = mentorship_placements + mentorship_jupiter + mentorship_graha + mentorship_guna

    # Format to 1 decimal place and clamp between 0 and 100
    romantic_score = round(min(100.0, max(0.0, romantic_score)), 1)
    friendship_score = round(min(100.0, max(0.0, friendship_score)), 1)
    business_score = round(min(100.0, max(0.0, business_score)), 1)
    mentorship_score = round(min(100.0, max(0.0, mentorship_score)), 1)
    
    scores = {
        "romantic_marriage": romantic_score,
        "platonic_friendship": friendship_score,
        "business_professional": business_score,
        "mentorship_growth": mentorship_score
    }
    
    # Determine best suited relationship
    best_key = max(scores, key=scores.get)
    best_names = {
        "romantic_marriage": "Romantic & Marriage",
        "platonic_friendship": "Platonic Friendship",
        "business_professional": "Business & Professional",
        "mentorship_growth": "Mentorship & Growth"
    }
    
    scores["best_suited"] = best_names[best_key]
    return scores


@router.post("/compatibility", summary="Calculate Guna Milan Compatibility")
async def calculate_partnership_compatibility(
    body: CompatibilityRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Computes Moon-Nakshatra based Ashta Kuta Guna Milan (36 points) compatibility.
    Then prompts Kimi through Amazon Bedrock to generate a premium partnership synthesis report.
    """
    try:
        from app.astrology.guna_milan import calculate_guna_milan
        import hashlib

        # Calculate coordinates for Partner A
        tz_a = ZoneInfo(body.partner_a.location_timezone)
        dt_a = datetime(
            body.partner_a.year, body.partner_a.month, body.partner_a.day,
            body.partner_a.hour, body.partner_a.minute, tzinfo=tz_a
        )
        offset_a = dt_a.utcoffset()
        tz_offset_a = offset_a.total_seconds() / 3600.0 if offset_a else 0.0

        chart_a = await asyncio.to_thread(
            calculate_chart_data,
            year=body.partner_a.year, month=body.partner_a.month, day=body.partner_a.day,
            hour=body.partner_a.hour, minute=body.partner_a.minute,
            lat=body.partner_a.location_lat, lon=body.partner_a.location_lon,
            tz_offset_hours=tz_offset_a
        )
        rules_a = evaluate_chart_rules(chart_a)

        # Calculate coordinates for Partner B
        tz_b = ZoneInfo(body.partner_b.location_timezone)
        dt_b = datetime(
            body.partner_b.year, body.partner_b.month, body.partner_b.day,
            body.partner_b.hour, body.partner_b.minute, tzinfo=tz_b
        )
        offset_b = dt_b.utcoffset()
        tz_offset_b = offset_b.total_seconds() / 3600.0 if offset_b else 0.0

        chart_b = await asyncio.to_thread(
            calculate_chart_data,
            year=body.partner_b.year, month=body.partner_b.month, day=body.partner_b.day,
            hour=body.partner_b.hour, minute=body.partner_b.minute,
            lat=body.partner_b.location_lat, lon=body.partner_b.location_lon,
            tz_offset_hours=tz_offset_b
        )
        rules_b = evaluate_chart_rules(chart_b)

        # Run Guna Milan matching
        groom_nak = rules_a["nakshatras"]["moon"]["index"]
        groom_sign = chart_a["planets"]["moon"]["sign_index"]
        bride_nak = rules_b["nakshatras"]["moon"]["index"]
        bride_sign = chart_b["planets"]["moon"]["sign_index"]

        score, breakdown = calculate_guna_milan(
            groom_nak_idx=groom_nak, groom_sign_idx=groom_sign,
            bride_nak_idx=bride_nak, bride_sign_idx=bride_sign
        )

        # 1. Kuja Dosha (Manglik) calculations
        def get_manglik_status(chart: dict) -> tuple[bool, str]:
            mars_h = chart["planets"]["mars"]["house"]
            is_m = mars_h in [1, 2, 4, 7, 8, 12]
            sign = chart["planets"]["mars"]["sign"]
            # Cancellation rule: Mars in Aries, Scorpio, or Capricorn
            if is_m and sign in ["Aries", "Scorpio", "Capricorn"]:
                return False, f"Mars in {mars_h} house (cancelled due to {sign} placement)"
            return is_m, f"Mars in {mars_h} house"

        m_a, m_a_reason = get_manglik_status(chart_a)
        m_b, m_b_reason = get_manglik_status(chart_b)
        
        kuja_compatible = (m_a == m_b)
        kuja_status = "Compatible" if kuja_compatible else "Friction/Mismatch"
        if not kuja_compatible:
            kuja_reason = f"{body.partner_a_name} is {'' if m_a else 'non-'}Manglik, whereas {body.partner_b_name} is {'' if m_b else 'non-'}Manglik."
        else:
            kuja_reason = "Both partners have matching Manglik status, neutralizing the energetic imbalance."

        # 2. Venus to Venus relationship (Dwi-dwadashe, Shadashtaka, Navapanchama, etc.)
        sign_a_venus = chart_a["planets"]["venus"]["sign_index"]
        sign_b_venus = chart_b["planets"]["venus"]["sign_index"]
        venus_dist = (sign_b_venus - sign_a_venus) % 12 + 1
        
        def get_relationship_name(dist: int) -> tuple[str, bool]:
            if dist == 1: return "Conjunction (1-1)", True
            if dist in [2, 12]: return "Dwirdwadashe (2-12) - Financial/Expense Focus", False
            if dist in [3, 11]: return "3-11 Relationship - Friendly & Cooperative", True
            if dist in [4, 10]: return "Kendra (4-10) - Constructive/Action-oriented", True
            if dist in [5, 9]: return "Navapanchama (5-9) - Harmonious & Fortunate", True
            if dist in [6, 8]: return "Shadashtaka (6-8) - Obstacle/Conflict Risk", False
            if dist == 7: return "Opposition (1-7) - Attracts & Completes", True
            return "Neutral", True

        venus_relation, venus_fav = get_relationship_name(venus_dist)

        # 3. 7th Lord to 7th Lord relationship
        sign_lords = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4]
        
        h7_sign_idx_a = (chart_a["ascendant"]["sign_index"] + 6) % 12
        lord_7_a = sign_lords[h7_sign_idx_a]
        lord_7_name_a = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"][lord_7_a]
        lord_planet_name_a = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"][lord_7_a]
        sign_lord_a = chart_a["planets"][lord_planet_name_a]["sign_index"]

        h7_sign_idx_b = (chart_b["ascendant"]["sign_index"] + 6) % 12
        lord_7_b = sign_lords[h7_sign_idx_b]
        lord_7_name_b = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"][lord_7_b]
        lord_planet_name_b = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"][lord_7_b]
        sign_lord_b = chart_b["planets"][lord_planet_name_b]["sign_index"]

        lord_7_dist = (sign_lord_b - sign_lord_a) % 12 + 1
        lord_7_relation, lord_7_fav = get_relationship_name(lord_7_dist)

        # 4. Jaimini Synastry (Atmakaraka, Darakaraka, Upapada Lagna)
        def get_chara_karakas(chart: dict) -> dict:
            planets_to_use = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"]
            sorted_planets = sorted(
                planets_to_use,
                key=lambda p: chart["planets"][p]["degrees"],
                reverse=True
            )
            return {
                "Atmakaraka": sorted_planets[0].capitalize(),
                "Darakaraka": sorted_planets[-1].capitalize()
            }

        def calculate_upapada_lagna(chart: dict) -> tuple[int, str]:
            sign_lords_list = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4]
            lord_planet_names = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"]
            
            asc_idx = chart["ascendant"]["sign_index"]
            h12_idx = (asc_idx + 11) % 12
            
            h12_lord = sign_lords_list[h12_idx]
            lord_name = lord_planet_names[h12_lord]
            
            lord_sign_idx = chart["planets"][lord_name]["sign_index"]
            dist = (lord_sign_idx - h12_idx) % 12
            ul_idx = (lord_sign_idx + dist) % 12
            
            if ul_idx == h12_idx:
                ul_idx = (ul_idx + 10) % 12
            elif ul_idx == (h12_idx + 6) % 12:
                ul_idx = (ul_idx + 10) % 12
                
            sign_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
            return ul_idx, sign_names[ul_idx]

        def check_ul_match(ul_sign_idx: int, partner_chart: dict) -> dict:
            lagna_idx = partner_chart["ascendant"]["sign_index"]
            moon_idx = partner_chart["planets"]["moon"]["sign_index"]
            
            dist_lagna = (lagna_idx - ul_sign_idx) % 12
            dist_moon = (moon_idx - ul_sign_idx) % 12
            
            has_sync = dist_lagna in [0, 4, 6, 8] or dist_moon in [0, 4, 6, 8]
            details = []
            if dist_lagna == 0: details.append("Conjunct partner's Lagna")
            elif dist_lagna in [4, 8]: details.append("Trine partner's Lagna")
            elif dist_lagna == 6: details.append("Opposite partner's Lagna")
            
            if dist_moon == 0: details.append("Conjunct partner's Moon")
            elif dist_moon in [4, 8]: details.append("Trine partner's Moon")
            elif dist_moon == 6: details.append("Opposite partner's Moon")
            
            return {
                "has_sync": has_sync,
                "description": ", ".join(details) if details else "No direct aspect/conjunction to Lagna/Moon"
            }

        karakas_a = get_chara_karakas(chart_a)
        karakas_b = get_chara_karakas(chart_b)
        
        ul_idx_a, ul_sign_a = calculate_upapada_lagna(chart_a)
        ul_idx_b, ul_sign_b = calculate_upapada_lagna(chart_b)
        
        ul_match_a = check_ul_match(ul_idx_a, chart_b)
        ul_match_b = check_ul_match(ul_idx_b, chart_a)
        
        ak_a = karakas_a["Atmakaraka"]
        dk_a = karakas_a["Darakaraka"]
        ak_b = karakas_b["Atmakaraka"]
        dk_b = karakas_b["Darakaraka"]
        
        dk_planet_a = dk_a.lower()
        dk_planet_b = dk_b.lower()
        dk_sign_a = chart_a["planets"][dk_planet_a]["sign_index"]
        dk_sign_b = chart_b["planets"][dk_planet_b]["sign_index"]
        dk_dist = (dk_sign_b - dk_sign_a) % 12 + 1
        dk_relation, dk_fav = get_relationship_name(dk_dist)

        # 5. Navamsa Synastry (D9 charts)
        d9_a = chart_a.get("divisional_charts", {}).get("D9", {})
        d9_b = chart_b.get("divisional_charts", {}).get("D9", {})
        
        d9_lagna_sign_a = d9_a.get("ascendant", {}).get("sign", "Aries")
        d9_lagna_idx_a = d9_a.get("ascendant", {}).get("sign_index", 0)
        d9_lagna_sign_b = d9_b.get("ascendant", {}).get("sign", "Aries")
        d9_lagna_idx_b = d9_b.get("ascendant", {}).get("sign_index", 0)
        
        d1_lagna_b = chart_b["ascendant"]["sign_index"]
        d1_moon_b = chart_b["planets"]["moon"]["sign_index"]
        d1_lagna_a = chart_a["ascendant"]["sign_index"]
        d1_moon_a = chart_a["planets"]["moon"]["sign_index"]
        
        d9_sync_a = (d9_lagna_idx_a == d1_lagna_b) or (d9_lagna_idx_a == d1_moon_b)
        d9_sync_b = (d9_lagna_idx_b == d1_lagna_a) or (d9_lagna_idx_b == d1_moon_a)

        # Calculate relationship suitability scores
        jup_sign_a = chart_a["planets"]["jupiter"]["sign_index"]
        jup_sign_b = chart_b["planets"]["jupiter"]["sign_index"]
        jup_dist = (jup_sign_b - jup_sign_a) % 12 + 1
        moon_dist = (bride_sign - groom_sign) % 12 + 1

        suitability = calculate_relationship_suitability(
            score=score,
            breakdown=breakdown,
            venus_dist=venus_dist,
            venus_fav=venus_fav,
            lord_7th_dist=lord_7_dist,
            lord_7th_fav=lord_7_fav,
            kuja_compatible=kuja_compatible,
            dk_fav=dk_fav,
            ul_match_a_to_b=ul_match_a["description"],
            ul_match_b_to_a=ul_match_b["description"],
            moon_dist=moon_dist,
            jup_dist=jup_dist
        )

        advanced_compatibility = {
            "suitability": suitability,
            "kuja_dosha": {
                "partner_a_manglik": bool(m_a),
                "partner_a_reason": m_a_reason,
                "partner_b_manglik": bool(m_b),
                "partner_b_reason": m_b_reason,
                "status": kuja_status,
                "compatible": bool(kuja_compatible),
                "reason": kuja_reason
            },
            "venus_alignment": {
                "distance": venus_dist,
                "relationship": venus_relation,
                "favorable": bool(venus_fav)
            },
            "lord_7th_alignment": {
                "partner_a_lord": lord_7_name_a,
                "partner_b_lord": lord_7_name_b,
                "distance": lord_7_dist,
                "relationship": lord_7_relation,
                "favorable": bool(lord_7_fav)
            },
            "jaimini_synastry": {
                "partner_a_ak": ak_a,
                "partner_a_dk": dk_a,
                "partner_b_ak": ak_b,
                "partner_b_dk": dk_b,
                "darakaraka_relation": dk_relation,
                "darakaraka_favorable": bool(dk_fav),
                "partner_a_ul": ul_sign_a,
                "partner_b_ul": ul_sign_b,
                "ul_match_a_to_b": ul_match_a["description"],
                "ul_match_b_to_a": ul_match_b["description"]
            },
            "navamsa_synastry": {
                "partner_a_d9_lagna": d9_lagna_sign_a,
                "partner_b_d9_lagna": d9_lagna_sign_b,
                "partner_a_d9_sync": bool(d9_sync_a),
                "partner_b_d9_sync": bool(d9_sync_b)
            }
        }

        # Caching logic
        param_hash = hashlib.md5(
            f"{body.partner_a.model_dump()}_{body.partner_b.model_dump()}".encode("utf-8")
        ).hexdigest()
        # Version the key so previously cached, short-format reports are never
        # returned after the report experience changes.
        cache_key = f"compat_cache:v2:{param_hash}"
        redis = get_redis()

        if not body.force_refresh:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    logger.info("compat_cache_hit", key=cache_key)
                    return json.loads(cached)
            except Exception as e:
                logger.error("compat_cache_read_failed", error=str(e))

        system_instruction_2 = (
            "# COMPATIBILITY REPORT REWRITE ENGINE (Part 2 of 2)\n"
            "You are a premium relationship psychologist who happens to understand Vedic astrology. "
            "Your goal is NOT to explain astrology in the description sections, but to explain PEOPLE.\n\n"
            "## CORE PRINCIPLES\n"
            "1. Do NOT write brief summaries. This report must be extremely comprehensive and contain at least 5000 words for this part. Write multiple long, detailed paragraphs for every sub-point.\n"
            "2. Do NOT describe only one partner. Every section MUST include BOTH partners, comparing them directly.\n"
            "3. REMOVE JARGON from psychological sections: Avoid astrological terms in the Dynamic, Strengths, Challenges, and Married Life sections. Explain real-life behaviors instead.\n"
            "4. ASTROLOGICAL REASONING: Only AFTER the simple explanation, include a separate final section titled 'Why the Chart Suggests This'. "
            "For every behavioral conclusion drawn in both Part 1 and Part 2, reference the specific planetary placements, houses, lordships, aspects, yogas, dashas, and confidence levels.\n\n"
            "## SKELETON YOU MUST FOLLOW (PART 2 OF 2)\n\n"
            "# Section 4: Relationship Dynamic\n"
            "Explain how these two personalities interact. For every category, write multiple paragraphs detailing (1) What works naturally, (2) What requires effort, and (3) Practical advice:\n"
            "- Communication\n"
            "- Emotional compatibility\n"
            "- Trust\n"
            "- Conflict style\n"
            "- Romance\n"
            "- Marriage expectations\n"
            "- Lifestyle\n"
            "- Career support\n"
            "- Family life\n"
            "- Financial habits\n"
            "- Decision making\n"
            "- Physical chemistry\n"
            "- Friendship\n"
            "- Long-term compatibility\n\n"
            "# Section 5: Biggest Strengths\n"
            "List the 5 strongest parts of the relationship. Explain WHY in deep detail with plain, non-astrological English.\n\n"
            "# Section 6: Biggest Challenges\n"
            "List the 5 biggest challenges. Explain WHY in deep detail and give practical, actionable psychological solutions.\n\n"
            "# Section 7: Everyday Married Life\n"
            "Describe realistically: How arguments happen, who apologizes first, who manages money, who plans trips, who is more romantic, who needs reassurance, who needs space, how decisions are made, how parenting styles may differ, and how they grow together over 10-20 years. Write naturally and extensively.\n\n"
            "# Section 8: Relationship Timing & Timeline (From When to When)\n"
            "Explicitly analyze: (1) Is there going to be a relationship between them? (2) How long will it last? "
            "(3) Detail a chronologically mapped timeline with exact dates/windows (e.g. Month Year – Month Year) specifying when phases begin, when key milestones occur, till when specific cycles are active, and the exact years of longevity based on their Vimshottari Dashas and transits. Write in plain, clear, non-astrological language.\n\n"
            "# Section 9: Compatibility Summary & Suitability\n"
            "Explain in plain English why this is a good/challenging match and what kind of relationship this partnership is best suited for. "
            "Analyze the calculated suitability scores (Romantic & Marriage, Platonic Friendship, Business & Professional, Mentorship & Growth) provided in the advanced metrics. "
            "Explain who needs to adjust more, and whether this feels more like a Friendship, Soulmate, Companion, Growth, or Karmic relationship. Support every statement using the charts.\n\n"
            "# Section 10: Why the Chart Suggests This (Astrological Appendix)\n"
            "Provide the formal Jyotish verification reasoning. For every conclusion drawn in the report (across sections 3 to 9), reference:\n"
            "Planet → House → Lordship → Aspect → Yoga → Dasha → Confidence Level (HIGH, MEDIUM, or LOW, with reasoning).\n"
            "Include chart validations (whether Ascendants, Moon signs, Nakshatras match) and planetary coordinates.\n\n"
            "CRITICAL: Be extremely detailed and exhaustive (5000+ words for this part alone)."
        )
        
        user_message_2 = (
            f"Generate Part 2 of the psychological compatibility report.\n"
            f"RAW INPUT DETAILS:\n"
            f"Partner A: {body.partner_a_name} - Date: {body.partner_a.year}-{body.partner_a.month:02d}-{body.partner_a.day:02d}, Time: {body.partner_a.hour:02d}:{body.partner_a.minute:02d}, Lat: {body.partner_a.location_lat}, Lon: {body.partner_a.location_lon}, Tz: {body.partner_a.location_timezone}\n"
            f"Partner B: {body.partner_b_name} - Date: {body.partner_b.year}-{body.partner_b.month:02d}-{body.partner_b.day:02d}, Time: {body.partner_b.hour:02d}:{body.partner_b.minute:02d}, Lat: {body.partner_b.location_lat}, Lon: {body.partner_b.location_lon}, Tz: {body.partner_b.location_timezone}\n\n"
            f"PRECOMPUTED CHART BLUEPRINT:\n"
            f"Partner A Moon Sign: {chart_a['planets']['moon']['sign']}, Nakshatra: {rules_a['nakshatras']['moon']['name']}\n"
            f"Partner B Moon Sign: {chart_b['planets']['moon']['sign']}, Nakshatra: {rules_b['nakshatras']['moon']['name']}\n\n"
            f"Guna Score: {score}/36\n"
            f"Guna Breakdown: {json.dumps(breakdown)}\n"
            f"Advanced Metrics: {json.dumps(advanced_compatibility)}\n"
            f"Whole Sign house placements and Lahiri coordinates: {json.dumps({'partner_a': chart_a['planets'], 'partner_b': chart_b['planets']})}\n"
        )

        # Keep the analysis and the advice in one report. The previous two-part
        # format asked for 10,000+ words and often buried the useful guidance.
        system_instruction = (
            "# CLEAR, DETAILED COMPATIBILITY REPORT\n"
            "You are a thoughtful relationship counsellor who uses Vedic astrology as a reflective tool. "
            "Write one coherent, warm, evidence-led report for two ordinary people—not an academic astrology essay.\n\n"
            "## WRITING RULES\n"
            "- Use plain everyday English. Define a Vedic term in parentheses the first time it appears, then prefer the plain-English meaning.\n"
            "- Be specific to the supplied calculations. Never invent placements, events, dates, or facts that are not in the data.\n"
            "- Treat the chart as a lens for discussion, not a verdict. Do not promise a marriage, predict a breakup, assign blame, or make claims about fertility, health, or lifespan.\n"
            "- Every conclusion must say what it may feel like in real life, why the supplied data points in that direction, and one useful action the couple can take.\n"
            "- Be detailed without repeating yourself: aim for 2,000–3,000 words. Use short paragraphs, clear headings, and scannable bullets.\n"
            "- Refer to them by name and use neutral language such as Partner A and Partner B. Do not assume gender roles.\n\n"
            "## REQUIRED MARKDOWN FORMAT\n"
            "# Compatibility Report: [Partner A] & [Partner B]\n"
            "## The short answer\n"
            "Give a balanced 3–4 sentence overview: the total score, what is promising, what needs conscious care, and a reminder that choices matter.\n\n"
            "## What the score is measuring\n"
            "Explain the 36-point Guna Milan score in simple language. Identify the two strongest and two lower-scoring areas, state each score, and explain what each area is meant to reflect. Do not call any score a guarantee.\n\n"
            "## How each person may show up in a relationship\n"
            "Use two subsections, one for each partner. Cover communication, emotional needs, decision-making, strengths, and what helps them feel safe. Keep astrology terms out of this section.\n\n"
            "## How the relationship may work day to day\n"
            "Use these five subsections: Communication & conflict; Emotional closeness & trust; Romance & affection; Decisions, money & responsibilities; Long-term partnership. In every subsection include **What may come naturally**, **What may be difficult**, **Why this reading says so**, and **Try this** with a concrete habit or conversation starter.\n\n"
            "## Your strongest foundations\n"
            "Give exactly 3 clearly named strengths. For each: explain the real-life benefit and cite the relevant score or advanced metric in a final 'Why this is here' sentence.\n\n"
            "## Areas to handle with care\n"
            "Give exactly 3 clearly named watch-outs. For each: describe the likely pattern, its impact if ignored, why the calculation flags it, and a practical repair step. Use kind, non-fatalistic language.\n\n"
            "## A practical relationship plan\n"
            "Give a 30-day plan with four weekly actions: one communication check-in, one shared-planning task, one connection ritual, and one conflict-repair practice. Make every action small and usable today.\n\n"
            "## Why the chart points in this direction\n"
            "Provide a concise optional technical appendix. Translate each item into plain language first, then name the relevant Guna score, Venus alignment, seventh-lord alignment, Kuja/Manglik result, Jaimini/Upapada indicator, or Navamsa indicator supplied. Do not claim calculations not present in the input.\n\n"
            "## Bottom line\n"
            "End with one compassionate paragraph explaining the relationship type the calculated suitability scores most support, the main habit that will help most, and that mutual respect and communication matter more than any score."
        )
        user_message = (
            "Create the compatibility report using only the verified data below.\n\n"
            f"PARTNER A: {body.partner_a_name}\n"
            f"PARTNER B: {body.partner_b_name}\n"
            f"Partner A Moon sign / nakshatra: {chart_a['planets']['moon']['sign']} / {rules_a['nakshatras']['moon']['name']}\n"
            f"Partner B Moon sign / nakshatra: {chart_b['planets']['moon']['sign']} / {rules_b['nakshatras']['moon']['name']}\n"
            f"Guna Milan total: {score}/36\n"
            f"Guna breakdown: {json.dumps(breakdown)}\n"
            f"Advanced compatibility indicators: {json.dumps(advanced_compatibility)}\n"
            f"Verified chart placements: {json.dumps({'partner_a': chart_a['planets'], 'partner_b': chart_b['planets']})}\n"
        )
        reading = await _generate_llm_response(system_instruction, user_message)

        response_payload = {
            "score": score,
            "breakdown": breakdown,
            "advanced_compatibility": advanced_compatibility,
            "reading": reading,
            "partner_a_chart": {
                "planets": chart_a["planets"],
                "ascendant": chart_a["ascendant"],
            },
            "partner_b_chart": {
                "planets": chart_b["planets"],
                "ascendant": chart_b["ascendant"],
            }
        }

        # Cache response
        try:
            await redis.set(cache_key, json.dumps(response_payload), ex=7 * 86400)
        except Exception as e:
            logger.error("compat_cache_write_failed", error=str(e))

        return response_payload

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error("compatibility_calc_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during compatibility calculation."
        )


@router.post("/transit", summary="Calculate Daily Transit Horoscope")
async def calculate_daily_transit(
    body: TransitRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Computes current transiting planet placements relative to the user's natal Ascendant (Lagna).
    Prompts Kimi through Amazon Bedrock to generate a personalized daily transit guidance horoscope.
    """
    try:
        import hashlib

        # Compute user's natal chart
        birth_tz = ZoneInfo(body.birth_timezone)
        birth_dt = datetime(
            body.birth_year, body.birth_month, body.birth_day,
            body.birth_hour, body.birth_minute, tzinfo=birth_tz
        )
        birth_offset = birth_dt.utcoffset()
        birth_tz_offset = birth_offset.total_seconds() / 3600.0 if birth_offset else 0.0

        natal_chart = await asyncio.to_thread(
            calculate_chart_data,
            year=body.birth_year, month=body.birth_month, day=body.birth_day,
            hour=body.birth_hour, minute=body.birth_minute,
            lat=body.birth_lat, lon=body.birth_lon,
            tz_offset_hours=birth_tz_offset
        )

        # Compute today's transit positions at the user's current location
        current_tz = ZoneInfo(body.current_timezone)
        now_dt = datetime.now(current_tz)
        now_offset = now_dt.utcoffset()
        now_tz_offset = now_offset.total_seconds() / 3600.0 if now_offset else 0.0

        transit_chart = await asyncio.to_thread(
            calculate_chart_data,
            year=now_dt.year, month=now_dt.month, day=now_dt.day,
            hour=now_dt.hour, minute=now_dt.minute,
            lat=body.current_lat, lon=body.current_lon,
            tz_offset_hours=now_tz_offset
        )

        # Map transit planets to natal houses (relative to natal Lagna)
        natal_lagna = natal_chart["ascendant"]["longitude"]
        transit_placements = []
        for name, planet_data in transit_chart["planets"].items():
            diff = (planet_data["longitude"] - natal_lagna) % 360.0
            natal_house = int(diff // 30.0) + 1
            transit_placements.append({
                "planet": name,
                "transit_sign": planet_data["sign"],
                "natal_house": natal_house,
                "degrees": planet_data["degrees"]
            })

        # Cache check using current date YMD to ensure once-per-day refresh
        current_date_str = now_dt.strftime("%Y-%m-%d")
        param_hash = hashlib.md5(
            f"{body.birth_year}_{body.birth_month}_{body.birth_day}_{body.current_timezone}_{current_date_str}".encode("utf-8")
        ).hexdigest()
        cache_key = f"transit_cache:{param_hash}"
        redis = get_redis()

        if not body.force_refresh:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    logger.info("transit_cache_hit", key=cache_key)
                    return json.loads(cached)
            except Exception as e:
                logger.error("transit_cache_read_failed", error=str(e))

        # Build prompt & query LLM
        system_instruction = (
            "# YOUR IDENTITY\n"
            "You are a premium Vedic daily transit astrologer.\n"
            "You write a concise, premium daily horoscope based on current transit planet placements in the user's natal houses.\n"
            "Keep the response brief, highly actionable, and formatted with premium Markdown (e.g., small highlight cards for active transits).\n"
            f"Today's date is {datetime.now().strftime('%B %d, %Y')}.\n"
        )
        
        user_message = (
            f"Generate a Daily Transit Horoscope for user with:\n"
            f"Natal Ascendant (Lagna) Sign: {natal_chart['ascendant']['sign']}\n"
            f"Natal Moon Sign: {natal_chart['planets']['moon']['sign']}\n\n"
            f"Current Transit Placements (Today is {now_dt.strftime('%B %d, %Y')}):\n"
            + "\n".join([
                f"- {tp['planet'].capitalize()} is transiting in {tp['transit_sign']} (lands in user's Natal House {tp['natal_house']})"
                for tp in transit_placements
            ]) +
            "\n\nProvide daily transit horoscope and guidance summary."
        )

        horoscope = await _generate_llm_response(system_instruction, user_message)

        response_payload = {
            "date": current_date_str,
            "transit_placements": transit_placements,
            "horoscope": horoscope,
        }

        # Cache response
        try:
            await redis.set(cache_key, json.dumps(response_payload), ex=24 * 3600)  # 1 day TTL
        except Exception as e:
            logger.error("transit_cache_write_failed", error=str(e))

        return response_payload

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error("transit_calc_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transit calculation failed: {str(e)}"
        )


def normalize_age_range(value: object) -> str:
    """Return a safe, adult age range in a predictable format for the UI and image prompt."""
    ages = [int(age) for age in re.findall(r"\d{1,2}", str(value or ""))]
    if not ages:
        return "24–30"

    youngest = max(18, min(ages))
    oldest = min(80, max(ages))
    if youngest > oldest:
        youngest, oldest = 24, 30
    return f"{youngest}–{oldest}"


def get_estimated_birth_date_window(age_range: str) -> str:
    """Convert an age range into an explicitly approximate date-of-birth window."""
    ages = [int(age) for age in re.findall(r"\d{1,2}", age_range)]
    if not ages:
        return "Not available"

    youngest, oldest = min(ages), max(ages)
    today = datetime.now(dt_tz.utc).date()

    def years_ago(years: int):
        try:
            return today.replace(year=today.year - years)
        except ValueError:
            # Handles 29 February when the destination year is not a leap year.
            return today.replace(year=today.year - years, month=2, day=28)

    earliest = years_ago(oldest + 1) + timedelta(days=1)
    latest = years_ago(youngest)
    return f"{earliest:%d %b %Y} – {latest:%d %b %Y}"


async def generate_image_from_prompt(
    portrait_description: str,
    gender: str,
    age_range: str,
    seed: int,
) -> str | None:
    from app.config import get_settings
    import boto3
    import json
    import asyncio

    settings = get_settings()
    if not (settings.aws_access_key_id and settings.aws_secret_access_key):
        return None

    # Helper to invoke SDXL
    async def try_sdxl(client, full_prompt):
        body = json.dumps({
            "text_prompts": [
                {"text": full_prompt, "weight": 1.0},
                {"text": "cartoon, drawing, anime, illustration, abstract, 3d render, blurry, low quality, bad anatomy, deformed, duplicate face, extra limbs, wedding clothing, religious symbols, text, watermark", "weight": -1.0}
            ],
            "cfg_scale": 7,
            "steps": 30,
            "width": 768,
            "height": 960,
            "seed": seed,
        })
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.invoke_model(
                modelId="stability.stable-diffusion-xl-v1:0",
                contentType="application/json",
                accept="application/json",
                body=body
            )
        )
        response_body = json.loads(response.get("body").read())
        return response_body.get("artifacts")[0].get("base64")

    # Helper to invoke Titan
    async def try_titan(client, full_prompt, model_id="amazon.titan-image-generator-v1:0"):
        body = json.dumps({
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": full_prompt,
                "negativeText": "cartoon, drawing, anime, illustration, abstract, 3d render, blurry, low quality, bad anatomy, deformed, duplicate face, extra limbs, wedding clothing, religious symbols, text, watermark"
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "height": 960,
                "width": 768,
                "cfgScale": 8.0,
                "seed": seed
            }
        })
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=body
            )
        )
        response_body = json.loads(response.get("body").read())
        return response_body.get("images")[0]

    try:
        client = boto3.client(
            "bedrock-runtime",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region_name
        )

        partner_label = "woman" if gender.lower() == "female" else "man"
        full_prompt = (
            "Create a high-quality, photorealistic editorial portrait of a fictional adult person. "
            f"Subject: a {partner_label}, approximately {age_range} years old, with these visual cues: {portrait_description}. "
            "Use a vertical 4:5 head-and-shoulders composition with the face fully in frame, a relaxed natural expression, "
            "contemporary understated dark clothing, and a softly lit midnight-blue studio background. "
            "This is an artistic astrological visualization, not a real person or celebrity. "
            "Keep the image grounded and realistic; do not add wedding attire, jewellery, zodiac graphics, halos, words, or watermarks."
        )

        try:
            base64_image = await try_sdxl(client, full_prompt)
            return f"data:image/png;base64,{base64_image}"
        except Exception as e_sdxl:
            logger.warning("sdxl_generation_failed_trying_titan_v1", error=str(e_sdxl))
            try:
                base64_image = await try_titan(client, full_prompt, model_id="amazon.titan-image-generator-v1:0")
                return f"data:image/png;base64,{base64_image}"
            except Exception as e_titan_v1:
                logger.warning("titan_v1_generation_failed_trying_titan_v2", error=str(e_titan_v1))
                try:
                    base64_image = await try_titan(client, full_prompt, model_id="amazon.titan-image-generator-v2:0")
                    return f"data:image/png;base64,{base64_image}"
                except Exception as e_titan_v2:
                    logger.error("titan_v2_generation_failed", error=str(e_titan_v2))
                    return None
    except Exception as e:
        logger.error("image_generation_init_failed", error=str(e))
        return None


from pydantic import BaseModel
from typing import Optional

class SoulmatePortraitRequest(BaseModel):
    gender: str
    year: int
    month: int
    day: int
    hour: int
    minute: int
    location_lat: float
    location_lon: float
    location_timezone: str
    force_refresh: Optional[bool] = False


@router.post("/soulmate-portrait", summary="Generate interactive soulmate portrait with attributes and timelines")
async def get_soulmate_portrait(
    body: SoulmatePortraitRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    try:
        # Compute exact UTC offset
        tz_info = ZoneInfo(body.location_timezone)
        birth_dt = datetime(body.year, body.month, body.day, body.hour, body.minute, tzinfo=tz_info)
        utc_offset = birth_dt.utcoffset()
        tz_offset_hours = utc_offset.total_seconds() / 3600.0 if utc_offset else 0.0

        chart_data = await asyncio.to_thread(
            calculate_chart_data,
            year=body.year, month=body.month, day=body.day,
            hour=body.hour, minute=body.minute,
            lat=body.location_lat, lon=body.location_lon,
            tz_offset_hours=tz_offset_hours
        )
        rules_data = evaluate_chart_rules(chart_data)

        # Cache lookup
        param_hash = hashlib.md5(
            f"soulmate_{body.gender}_{body.year}_{body.month}_{body.day}_{body.hour}_{body.minute}_{body.location_lat}_{body.location_lon}".encode("utf-8")
        ).hexdigest()
        # Avoid serving older responses that used a generic, fixed fallback portrait.
        cache_key = f"soulmate_cache:v3:{param_hash}"
        redis = get_redis()

        if not body.force_refresh:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.error("soulmate_cache_read_failed", error=str(e))

        # Query LLM to dynamically generate soulmate attributes
        system_instruction = (
            "You are a master Vedic astrologer and matchmaker. Analyze the user's birth chart details (specifically 7th house, 7th lord, Venus, Moon, Darakaraka, and Navamsa) and synthesize their future soulmate characteristics.\n"
            "You must output ONLY a valid JSON object matching the following structure. Do not wrap it in markdown code blocks. Do not add any text before or after the JSON.\n"
            "JSON structure:\n"
            "{\n"
            "  \"age_range\": \"string (an adult range only, e.g. 24 - 28)\",\n"
            "  \"appearance\": \"string (2-4 concise traits describing eyes, smile, and general appearance)\",\n"
            "  \"portrait_description\": \"string (one detailed, respectful visual brief for an artistic portrait: facial structure, hair, eyes, expression, and clothing style; no celebrity or real-person references)\",\n"
            "  \"personality\": \"string (3-5 traits describing demeanor, values)\",\n"
            "  \"profession\": \"string (likely career path/domains)\",\n"
            "  \"indicators\": [\n"
            "    \"string (Astrological justification referencing 7th lord placement/aspects)\",\n"
            "    \"string (Astrological justification referencing Venus placement/aspects)\",\n"
            "    \"string (Astrological justification referencing Moon/Darakaraka)\",\n"
            "    \"string (Astrological justification referencing Navamsa alignment)\"\n"
            "  ],\n"
            "  \"relationship_timeline\": [\n"
            "    { \"date\": \"2026\", \"rating\": \"⭐⭐⭐☆☆\", \"theme\": \"Self Growth & Preparation\" },\n"
            "    { \"date\": \"2027 - 2028\", \"rating\": \"⭐⭐⭐⭐☆\", \"theme\": \"New Connection Possible\" },\n"
            "    { \"date\": \"2029 - 2030\", \"rating\": \"⭐⭐⭐⭐⭐\", \"theme\": \"Relationship Deepens & Commitment Likely\" },\n"
            "    { \"date\": \"2031+\", \"rating\": \"⭐⭐⭐⭐⭐\", \"theme\": \"Stability & Long-term Bond\" }\n"
            "  ]\n"
            "}"
        )
        user_message = (
            f"User birth chart: {json.dumps(chart_data['planets'])}. "
            f"Rules details: {json.dumps(rules_data['nakshatras'])}. "
            f"Create an adult, respectful, symbolic partner profile for a {body.gender} partner. "
            "Do not present any field as factual knowledge of a future person."
        )

        provider = get_provider("bedrock")
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message}
        ]

        compiled_prompt = CompiledPrompt(
            messages=messages,
            provider_config=ProviderConfig(provider_name="bedrock", model_id=get_settings().bedrock_model_id, max_tokens=8192)
        )
        response = await provider.generate(compiled_prompt)
        raw_text = response["content"].strip()

        # Clean markdown code wrapper blocks if present
        if raw_text.startswith("```json"):
            raw_text = raw_text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.split("```", 1)[1].rsplit("```", 1)[0].strip()

        parsed_data = json.loads(raw_text)

        age_range = normalize_age_range(parsed_data.get("age_range"))
        parsed_data["age_range"] = age_range
        parsed_data["estimated_birth_date_range"] = get_estimated_birth_date_window(age_range)
        parsed_data["birth_date_note"] = "An approximate adult birth-date window inferred from the age range, not an exact or verifiable date."

        # Use the detailed visual brief—not just two adjectives—and a chart-specific
        # seed so portraits no longer default to the same generic face.
        portrait_description = parsed_data.get("portrait_description") or parsed_data.get("appearance", "")
        portrait_seed = int(hashlib.sha256(
            f"{param_hash}:{portrait_description}".encode("utf-8")
        ).hexdigest()[:8], 16) % 2147483647
        generated_img = await generate_image_from_prompt(
            portrait_description=portrait_description,
            gender=body.gender,
            age_range=age_range,
            seed=portrait_seed,
        )

        if generated_img:
            parsed_data["image_url"] = generated_img
            parsed_data["image_source"] = "generated"
        else:
            # A symbolic fallback is more honest than showing an unrelated fixed face.
            parsed_data["image_url"] = "/images/soulmate-symbolic-fallback.svg"
            parsed_data["image_source"] = "symbolic_fallback"

        # Write to cache
        try:
            await redis.set(cache_key, json.dumps(parsed_data), ex=7 * 86400)
        except Exception as e:
            logger.error("soulmate_cache_write_failed", error=str(e))

        return parsed_data

    except Exception as e:
        logger.error("soulmate_portrait_generation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Soulmate portrait generation failed: {str(e)}"
        )


@router.post("/bazi", summary="Calculate authentic Chinese Astrology (BaZi Four Pillars) chart")
def get_bazi_chart(
    body: BaZiChartRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Computes genuine Four Pillars of Destiny (BaZi) Chinese Astrology chart using Swiss Ephemeris
    solar ecliptic longitude calculations. Enforces Lichun (315°) year boundary, 12 principal solar term
    month boundaries, Zi-hour (23:00) day shift rule, Five Rats hour stem method, and ZiPing Day Master strength.
    """
    try:
        pillars_data = calculate_bazi_pillars(
            year=body.year,
            month=body.month,
            day=body.day,
            hour=body.hour,
            minute=body.minute,
            lat=body.latitude,
            lon=body.longitude,
            tz_offset_hours=body.timezone_offset
        )
        analysis_data = analyze_bazi_chart(pillars_data)

        return {
            "status": "success",
            "pillars_data": pillars_data,
            "analysis": analysis_data,
        }
    except Exception as e:
        logger.error("bazi_calculation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BaZi astrological calculation failure: {str(e)}"
        )


@router.post("/bazi/compatibility", summary="Calculate genuine BaZi Synastry compatibility between two charts")
def get_bazi_compatibility(
    body: BaZiCompatibilityRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Computes genuine BaZi Synastry (He Sang Xiang Chong) compatibility between two charts.
    Evaluates Day Master synergy, Spouse Palace (Day Branch) harmony, Element Complementarity (Yong Shen),
    and Year Branch Zodiac affinity.
    """
    try:
        bazi_a_pillars = calculate_bazi_pillars(
            year=body.person_a.year,
            month=body.person_a.month,
            day=body.person_a.day,
            hour=body.person_a.hour,
            minute=body.person_a.minute,
            lat=body.person_a.latitude,
            lon=body.person_a.longitude,
            tz_offset_hours=body.person_a.timezone_offset
        )
        bazi_a_analysis = analyze_bazi_chart(bazi_a_pillars)

        bazi_b_pillars = calculate_bazi_pillars(
            year=body.person_b.year,
            month=body.person_b.month,
            day=body.person_b.day,
            hour=body.person_b.hour,
            minute=body.person_b.minute,
            lat=body.person_b.latitude,
            lon=body.person_b.longitude,
            tz_offset_hours=body.person_b.timezone_offset
        )
        bazi_b_analysis = analyze_bazi_chart(bazi_b_pillars)

        comp_res = calculate_bazi_compatibility(
            {"pillars_data": bazi_a_pillars, "analysis": bazi_a_analysis},
            {"pillars_data": bazi_b_pillars, "analysis": bazi_b_analysis}
        )

        return {
            "status": "success",
            "person_a": {
                "pillars_data": bazi_a_pillars,
                "analysis": bazi_a_analysis,
            },
            "person_b": {
                "pillars_data": bazi_b_pillars,
                "analysis": bazi_b_analysis,
            },
            "compatibility": comp_res,
        }
    except Exception as e:
        logger.error("bazi_compatibility_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BaZi compatibility calculation failure: {str(e)}"
        )


@router.post("/bazi/compatibility/reading", summary="Generate detailed AI relationship analysis for Chinese BaZi Synastry")
async def get_bazi_compatibility_reading(
    body: BaZiCompatibilityRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Generates a deep, plain-English AI relationship reading for Chinese BaZi Synastry.
    Explains relationship purpose, whether it is Fated/Karmic/Soulmate, Day Master & Spouse Palace dynamics,
    strengths, growth areas, and actionable guidance.
    """
    try:
        bazi_a_pillars = calculate_bazi_pillars(
            year=body.person_a.year,
            month=body.person_a.month,
            day=body.person_a.day,
            hour=body.person_a.hour,
            minute=body.person_a.minute,
            lat=body.person_a.latitude,
            lon=body.person_a.longitude,
            tz_offset_hours=body.person_a.timezone_offset
        )
        bazi_a_analysis = analyze_bazi_chart(bazi_a_pillars)

        bazi_b_pillars = calculate_bazi_pillars(
            year=body.person_b.year,
            month=body.person_b.month,
            day=body.person_b.day,
            hour=body.person_b.hour,
            minute=body.person_b.minute,
            lat=body.person_b.latitude,
            lon=body.person_b.longitude,
            tz_offset_hours=body.person_b.timezone_offset
        )
        bazi_b_analysis = analyze_bazi_chart(bazi_b_pillars)

        comp_res = calculate_bazi_compatibility(
            {"pillars_data": bazi_a_pillars, "analysis": bazi_a_analysis},
            {"pillars_data": bazi_b_pillars, "analysis": bazi_b_analysis}
        )

        cache_key = f"bazi_compat_reading:{hashlib.md5(json.dumps(body.model_dump(), sort_keys=True).encode()).hexdigest()}"
        redis = get_redis()
        try:
            cached = await redis.get(cache_key)
            if cached:
                logger.info("bazi_compat_reading_cache_hit", key=cache_key)
                return json.loads(cached)
        except Exception as e:
            logger.error("bazi_compat_cache_read_err", error=str(e))

        system_instruction = (
            "# CHINESE BAZI SYNASTRY RELATIONSHIP ANALYSIS\n"
            "You are a master Chinese BaZi (Four Pillars of Destiny) astrologer and intuitive relationship guide. "
            "Write a thorough, deeply detailed, comprehensive plain-English analysis explaining the spiritual and practical nature of this relationship.\n\n"
            "## CORE OBJECTIVE\n"
            "Translate complex Four Pillars interactions (He, Sang, Xiang, Chong, Day Master synergy, Spouse Palace, Useful Element) into plain everyday language.\n"
            "Provide an in-depth reading covering their true core strengths, their growth challenges, and practical life advice.\n\n"
            "## REQUIRED MARKDOWN FORMAT\n"
            "# BaZi Synastry Reading: Partner A & Partner B\n\n"
            "### 🔮 Relationship Archetype & Destiny Classification\n"
            "- Specify the primary classification clearly (**Fated Soulmate Connection**, **Karmic Growth Catalyst**, **Harmonic Soul Companionship**, or **Dynamic Transformative Connection**).\n"
            "- Explain in detail why the cosmic pillars assign this classification and what divine/karmic purpose brings them together.\n\n"
            "### ☯️ Soul Purpose & Higher Meaning\n"
            "Explain in 2-3 detailed, inspiring paragraphs what this connection is designed to build, transform, or heal in both partners' lives.\n\n"
            "### 🌊 Day Master & Spouse Palace Dynamics (Plain English)\n"
            "- Explain Partner A's Day Master element vs Partner B's Day Master element in simple physical terms (e.g., Water nourishing Wood, or Fire sharpening Metal).\n"
            "- Explain the Spouse Palace (Day Branch) harmony: how they make each other feel safe, loved, and supported at home.\n\n"
            "### 🌟 True Core Strengths & Harmonic Superpowers\n"
            "List 4-5 detailed bullet points highlighting the relationship's natural superpowers, emotional compatibility, and effortless alignment.\n\n"
            "### ⚠️ Areas to Work On & Hidden Growth Lessons\n"
            "List 3-4 specific potential friction points, communication pitfalls, or karmic triggers with compassionate, actionable advice on how to navigate them.\n\n"
            "### 💡 Practical Relationship Advice & Actionable Check-ins\n"
            "Provide 3-4 concrete, real-life rituals or communication practices to maximize harmony and long-term marital success."
        )

        user_message = (
            f"BAZI COMPATIBILITY DATA:\n"
            f"Overall Synastry Score: {comp_res['overall_score']}/100 ({comp_res['compatibility_level']})\n"
            f"Summary: {comp_res['summary']}\n\n"
            f"PARTNER A:\n"
            f"- Year Zodiac: {bazi_a_pillars['zodiac_animal']} ({bazi_a_pillars['pillars']['year']['stem']['element']})\n"
            f"- Day Master: {bazi_a_pillars['day_master']['char']} ({bazi_a_pillars['day_master']['element']} {bazi_a_pillars['day_master']['polarity']})\n"
            f"- Spouse Palace (Day Branch): {bazi_a_pillars['pillars']['day']['branch']['char']} ({bazi_a_pillars['pillars']['day']['branch']['zodiac']})\n"
            f"- Five Elements Balance: {json.dumps(bazi_a_analysis['element_percentages'])}\n\n"
            f"PARTNER B:\n"
            f"- Year Zodiac: {bazi_b_pillars['zodiac_animal']} ({bazi_b_pillars['pillars']['year']['stem']['element']})\n"
            f"- Day Master: {bazi_b_pillars['day_master']['char']} ({bazi_b_pillars['day_master']['element']} {bazi_b_pillars['day_master']['polarity']})\n"
            f"- Spouse Palace (Day Branch): {bazi_b_pillars['pillars']['day']['branch']['char']} ({bazi_b_pillars['pillars']['day']['branch']['zodiac']})\n"
            f"- Five Elements Balance: {json.dumps(bazi_b_analysis['element_percentages'])}\n\n"
            f"SYNASTRY CATEGORY BREAKDOWN:\n"
            f"{json.dumps(comp_res['categories'])}\n"
        )

        provider_config = ProviderConfig(provider_name="bedrock", model_id=get_settings().bedrock_model_id, max_tokens=4096)
        provider = get_provider("bedrock")
        compiled_prompt = CompiledPrompt(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ],
            provider_config=provider_config,
            total_tokens_estimate=len(system_instruction) // 4 + len(user_message) // 4,
        )

        result = await provider.generate(compiled_prompt)
        reading_text = result["content"]

        resp_payload = {
            "status": "success",
            "person_a": {
                "pillars_data": bazi_a_pillars,
                "analysis": bazi_a_analysis,
            },
            "person_b": {
                "pillars_data": bazi_b_pillars,
                "analysis": bazi_b_analysis,
            },
            "compatibility": comp_res,
            "reading": reading_text,
        }

        try:
            await redis.set(cache_key, json.dumps(resp_payload), ex=7 * 86400)
        except Exception as e:
            logger.error("bazi_compat_reading_cache_write_err", error=str(e))

        return resp_payload

    except Exception as e:
        logger.error("bazi_compatibility_reading_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BaZi compatibility reading failure: {str(e)}"
        )


@router.post("/bazi/compatibility/chat", summary="Interactive AI chat about BaZi Synastry relationship compatibility")
async def get_bazi_compatibility_chat(
    body: BaZiCompatibilityChatRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Handles follow-up questions about BaZi Synastry relationship compatibility in interactive chat mode.
    """
    try:
        bazi_a_pillars = calculate_bazi_pillars(
            year=body.person_a.year,
            month=body.person_a.month,
            day=body.person_a.day,
            hour=body.person_a.hour,
            minute=body.person_a.minute,
            lat=body.person_a.latitude,
            lon=body.person_a.longitude,
            tz_offset_hours=body.person_a.timezone_offset
        )
        bazi_a_analysis = analyze_bazi_chart(bazi_a_pillars)

        bazi_b_pillars = calculate_bazi_pillars(
            year=body.person_b.year,
            month=body.person_b.month,
            day=body.person_b.day,
            hour=body.person_b.hour,
            minute=body.person_b.minute,
            lat=body.person_b.latitude,
            lon=body.person_b.longitude,
            tz_offset_hours=body.person_b.timezone_offset
        )
        bazi_b_analysis = analyze_bazi_chart(bazi_b_pillars)

        comp_res = calculate_bazi_compatibility(
            {"pillars_data": bazi_a_pillars, "analysis": bazi_a_analysis},
            {"pillars_data": bazi_b_pillars, "analysis": bazi_b_analysis}
        )

        system_instruction = (
            "# CHINESE BAZI SYNASTRY RELATIONSHIP ASSISTANT\n"
            "You are an empathetic, expert Chinese BaZi relationship counselor. "
            "The user is asking follow-up questions about their compatibility report.\n\n"
            "## CONTEXT & GUIDELINES\n"
            "1. Use simple, warm, everyday English without confusing Chinese jargon.\n"
            "2. Answer the user's question directly using their calculated synastry metrics.\n"
            "3. Provide practical, non-fatalistic relationship advice.\n"
            "4. Keep responses clear, concise, and structured with markdown bullet points."
        )

        context_prompt = (
            f"CALCULATED SYNASTRY DATA:\n"
            f"Synastry Score: {comp_res['overall_score']}/100 ({comp_res['compatibility_level']})\n"
            f"Partner A Day Master: {bazi_a_pillars['day_master']['char']} ({bazi_a_pillars['day_master']['element']} {bazi_a_pillars['day_master']['polarity']}), Spouse Branch: {bazi_a_pillars['pillars']['day']['branch']['zodiac']}\n"
            f"Partner B Day Master: {bazi_b_pillars['day_master']['char']} ({bazi_b_pillars['day_master']['element']} {bazi_b_pillars['day_master']['polarity']}), Spouse Branch: {bazi_b_pillars['pillars']['day']['branch']['zodiac']}\n"
            f"Category Scores: {json.dumps(comp_res['categories'])}\n\n"
            f"USER QUESTION: {body.question}\n"
        )

        messages_payload = [{"role": "system", "content": system_instruction}]
        for msg in body.messages:
            if msg.get("role") in ["user", "assistant"]:
                messages_payload.append({"role": msg["role"], "content": msg["content"]})
        messages_payload.append({"role": "user", "content": context_prompt})

        provider_config = ProviderConfig(provider_name="bedrock", model_id=get_settings().bedrock_model_id, max_tokens=2048)
        provider = get_provider("bedrock")
        compiled_prompt = CompiledPrompt(
            messages=messages_payload,
            provider_config=provider_config,
            total_tokens_estimate=len(system_instruction) // 4 + len(context_prompt) // 4,
        )

        result = await provider.generate(compiled_prompt)
        return {
            "status": "success",
            "reply": result["content"]
        }

    except Exception as e:
        logger.error("bazi_compatibility_chat_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BaZi compatibility chat error: {str(e)}"
        )



@router.post("/kp", summary="Calculate authentic KP (Krishnamurti Paddhati) Astrology chart")
def get_kp_chart(
    body: KPCalculationRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Computes genuine KP (Krishnamurti Paddhati) birth chart using Krishnamurti Ayanamsa (mode 5)
    and Placidus House System ('P'). Returns Sub-Lords for all planets and cusps, 4-level house significators,
    and Ruling Planets.
    """
    try:
        chart_data = calculate_kp_chart(
            year=body.year,
            month=body.month,
            day=body.day,
            hour=body.hour,
            minute=body.minute,
            lat=body.latitude,
            lon=body.longitude,
            tz_offset_hours=body.timezone_offset
        )
        significators_data = calculate_kp_significators(chart_data)

        return {
            "status": "success",
            "chart": chart_data,
            "significators": significators_data,
        }
    except Exception as e:
        logger.error("kp_calculation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"KP astrological calculation failure: {str(e)}"
        )


@router.post("/kp/horary", summary="Calculate KP Horary (Prashna 1-249) chart")
def get_kp_horary_chart(
    body: KPHoraryRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Computes KP Prashna Horary chart for a number between 1 and 249.
    Sets the starting longitude of the 249 sub-division as the Horary Ascendant
    and derives Placidus house cusps and 4-level significators.
    """
    try:
        horary_result = calculate_kp_horary(
            horary_number=body.horary_number,
            year=body.year,
            month=body.month,
            day=body.day,
            hour=body.hour,
            minute=body.minute,
            lat=body.latitude,
            lon=body.longitude,
            tz_offset_hours=body.timezone_offset
        )
        return {
            "status": "success",
            "horary_number": body.horary_number,
            "horary_chart": horary_result["horary_chart"],
            "significators": horary_result["significators"],
        }
    except Exception as e:
        logger.error("kp_horary_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"KP Horary calculation failure: {str(e)}"
        )


@router.post("/kp/event-timing", summary="KP Event Timing & Date Predictor (Plain English)")
async def get_kp_event_timing(
    body: KPEventTimingRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Calculates exact KP Sub-Lord significators and uses AI to predict precise event timing windows
    in plain, easy-to-understand English.
    """
    try:
        cache_key = f"kp_timing_v2:{body.year}_{body.month}_{body.day}_{body.hour}_{body.minute}_{body.latitude}_{body.longitude}_{body.event_category}"
        redis_client = get_redis()
        if redis_client:
            try:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning("redis_cache_read_failed", error=str(e))

        chart_data = calculate_kp_chart(
            year=body.year,
            month=body.month,
            day=body.day,
            hour=body.hour,
            minute=body.minute,
            lat=body.latitude,
            lon=body.longitude,
            tz_offset_hours=body.timezone_offset
        )
        significators_data = calculate_kp_significators(chart_data)

        # Calculate exact Vimshottari Dasha-Antardasha timeline relative to today
        today_dt = datetime.now(dt_tz.utc)
        today_str = today_dt.strftime("%B %d, %Y")

        birth_dt = datetime(body.year, body.month, body.day, body.hour, body.minute, tzinfo=dt_tz.utc)
        moon_lon = chart_data["planets"]["Moon"]["longitude"]
        dasha_timeline = calculate_vimshottari_dasha(moon_lon, birth_dt)

        upcoming_dashas = []
        for m_dasha in dasha_timeline:
            m_end = datetime.strptime(m_dasha["end"], "%Y-%m-%d").replace(tzinfo=dt_tz.utc)
            if m_end >= today_dt:
                for a_dasha in m_dasha.get("antardashas", []):
                    a_start = datetime.strptime(a_dasha["start"], "%Y-%m-%d").replace(tzinfo=dt_tz.utc)
                    a_end = datetime.strptime(a_dasha["end"], "%Y-%m-%d").replace(tzinfo=dt_tz.utc)
                    if a_end >= today_dt and len(upcoming_dashas) < 8:
                        upcoming_dashas.append({
                            "mahadasha": m_dasha["lord"].capitalize(),
                            "antardasha": a_dasha["lord"].capitalize(),
                            "start_date": a_dasha["start"],
                            "end_date": a_dasha["end"],
                            "is_currently_active": (a_start <= today_dt <= a_end)
                        })

        TARGET_HOUSE_SETS = {
            "career_job": {2, 6, 10, 11},
            "marriage_love": {2, 7, 11},
            "property_asset": {4, 11, 12},
            "wealth_finance": {2, 6, 11},
            "travel_visa": {3, 9, 12},
            "education_exam": {4, 9, 11},
            "childbirth": {2, 5, 11},
        }

        target_set = TARGET_HOUSE_SETS.get(body.event_category, {2, 6, 10, 11})

        # Score Antardasha periods deterministically
        for item in upcoming_dashas:
            m_lord = item["mahadasha"]
            a_lord = item["antardasha"]
            m_houses = set(significators_data["planet_significators"].get(m_lord, {}).get("all_houses", []))
            a_houses = set(significators_data["planet_significators"].get(a_lord, {}).get("all_houses", []))
            score = len(m_houses.intersection(target_set)) * 2 + len(a_houses.intersection(target_set)) * 3
            item["score"] = score

        sorted_dashas = sorted(upcoming_dashas, key=lambda x: x["score"], reverse=True)
        primary_w = sorted_dashas[0] if sorted_dashas else upcoming_dashas[0]
        secondary_w = sorted_dashas[1] if len(sorted_dashas) > 1 else (upcoming_dashas[1] if len(upcoming_dashas) > 1 else primary_w)

        primary_date_range = f"{primary_w['start_date']} to {primary_w['end_date']} ({primary_w['mahadasha']}-{primary_w['antardasha']} Period)"
        secondary_date_range = f"{secondary_w['start_date']} to {secondary_w['end_date']} ({secondary_w['mahadasha']}-{secondary_w['antardasha']} Period)"

        EVENT_HOUSES_DESC = {
            "career_job": "Houses 2 (Wealth), 6 (Employment/Service), 10 (Profession/Status), 11 (Fulfillment)",
            "marriage_love": "Houses 2 (Family addition), 7 (Spouse/Partner), 11 (Desire fulfillment)",
            "property_asset": "Houses 4 (Home/Property/Assets), 11 (Gains), 12 (Investment)",
            "wealth_finance": "Houses 2 (Bank balance/Accumulated wealth), 6 (Earnings), 11 (Profits)",
            "travel_visa": "Houses 3 (Short travel), 9 (Long distance journey), 12 (Foreign residency)",
            "education_exam": "Houses 4 (Education), 9 (Higher knowledge), 11 (Success in competition)",
            "childbirth": "Houses 2 (Family addition), 5 (Progeny/Children), 11 (Fulfillment)",
        }
        target_event_desc = EVENT_HOUSES_DESC.get(body.event_category, "Houses 2, 6, 10, 11")

        system_instruction = (
            "# KP (KRISHNAMURTI PADDHATI) ASTROLOGY TIMING & EXACT DATE PREDICTOR\n"
            f"REFERENCE POINT: TODAY'S CURRENT DATE IS {today_str}.\n"
            f"DETERMINISTIC PRIMARY WINDOW: **{primary_date_range}**\n"
            f"DETERMINISTIC SECONDARY WINDOW: **{secondary_date_range}**\n\n"
            "You are a master KP Astrologer known for pinpoint precision in predicting exact dates.\n"
            "Your objective is to translate raw KP Sub-Lord math, Placidus house significators, and the user's active Dasha-Antardasha timeline into clear, exact date ranges.\n\n"
            "## ABSOLUTE MANDATE FOR DATE CONSISTENCY:\n"
            f"1. You MUST use **{primary_date_range}** as the Primary Golden Window.\n"
            f"2. You MUST use **{secondary_date_range}** as the Secondary Alignment Window.\n"
            "3. DO NOT CHANGE, ALTER, OR HALLUCINATE ANY OTHER DATES.\n\n"
            "## REQUIRED MARKDOWN OUTPUT FORMAT:\n"
            "# 📅 KP Precise Event Timing Analysis\n\n"
            "### 🎯 Selected Life Event\n"
            "State the event clearly in plain English.\n\n"
            "### ⏳ Most Likely Favorable Time Windows (Exact Dates)\n"
            f"- **Primary Golden Window**: **{primary_date_range}**. Explain in 2 sentences why this exact Dasha period activates the target KP houses.\n"
            f"- **Secondary Alignment Window**: **{secondary_date_range}**.\n\n"
            "### 🔑 KP Sub-Lord & Dasha Confirmation (Plain English)\n"
            "Explain in 2 simple paragraphs how the active Dasha Lord, Star Lord, and Sub Lord signify the event houses without confusing technical jargon.\n\n"
            "### 💡 Actionable Preparation Steps\n"
            f"Provide 3 practical steps the user should take starting today ({today_str}) to prepare for this window."
        )

        user_message = (
            f"CURRENT REFERENCE DATE: {today_str}\n"
            f"KP BIRTH CHART & SIGNIFICATORS:\n"
            f"Ascendant: {chart_data['ascendant']['formatted_degree']} (Sign Lord: {chart_data['ascendant']['sign_lord']}, Star Lord: {chart_data['ascendant']['star_lord']}, Sub Lord: {chart_data['ascendant']['sub_lord']})\n"
            f"Ruling Planets: {json.dumps(chart_data['ruling_planets'])}\n"
            f"Target Event Category: {body.event_category} ({target_event_desc})\n"
            f"Vimshottari Active & Upcoming Dasha Timeline:\n{json.dumps(upcoming_dashas, indent=2)}\n\n"
            f"House Significators Breakdown:\n{json.dumps(significators_data['house_significators'])}\n\n"
            f"Planet Significators:\n{json.dumps(significators_data['planet_significators'])}\n"
        )

        provider_config = ProviderConfig(
            provider_name="bedrock",
            model_id=get_settings().bedrock_model_id,
            max_tokens=4096,
            temperature=0.0
        )
        provider = get_provider("bedrock")
        compiled_prompt = CompiledPrompt(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ],
            provider_config=provider_config,
            total_tokens_estimate=len(system_instruction) // 4 + len(user_message) // 4,
        )

        result = await provider.generate(compiled_prompt)

        response_payload = {
            "status": "success",
            "event_category": body.event_category,
            "chart": chart_data,
            "significators": significators_data,
            "timing_analysis": result["content"]
        }

        if redis_client:
            try:
                await redis_client.setex(cache_key, 86400, json.dumps(response_payload))
            except Exception as e:
                logger.warning("redis_cache_write_failed", error=str(e))

        return response_payload

    except Exception as e:
        logger.error("kp_event_timing_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"KP event timing prediction failure: {str(e)}"
        )


@router.post("/kp/event-timing/chat", summary="Interactive AI chat about KP Event Timing & Date Predictions")
async def get_kp_event_timing_chat(
    body: KPEventTimingChatRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Handles follow-up questions about KP Event Timing and exact dates in interactive chat mode.
    """
    try:
        chart_data = calculate_kp_chart(
            year=body.year,
            month=body.month,
            day=body.day,
            hour=body.hour,
            minute=body.minute,
            lat=body.latitude,
            lon=body.longitude,
            tz_offset_hours=body.timezone_offset
        )
        significators_data = calculate_kp_significators(chart_data)

        today_dt = datetime.now(dt_tz.utc)
        today_str = today_dt.strftime("%B %d, %Y")

        birth_dt = datetime(body.year, body.month, body.day, body.hour, body.minute, tzinfo=dt_tz.utc)
        moon_lon = chart_data["planets"]["Moon"]["longitude"]
        dasha_timeline = calculate_vimshottari_dasha(moon_lon, birth_dt)

        upcoming_dashas = []
        for m_dasha in dasha_timeline:
            m_end = datetime.strptime(m_dasha["end"], "%Y-%m-%d").replace(tzinfo=dt_tz.utc)
            if m_end >= today_dt:
                for a_dasha in m_dasha.get("antardashas", []):
                    a_start = datetime.strptime(a_dasha["start"], "%Y-%m-%d").replace(tzinfo=dt_tz.utc)
                    a_end = datetime.strptime(a_dasha["end"], "%Y-%m-%d").replace(tzinfo=dt_tz.utc)
                    if a_end >= today_dt and len(upcoming_dashas) < 8:
                        upcoming_dashas.append({
                            "mahadasha": m_dasha["lord"].capitalize(),
                            "antardasha": a_dasha["lord"].capitalize(),
                            "start_date": a_dasha["start"],
                            "end_date": a_dasha["end"],
                            "is_currently_active": (a_start <= today_dt <= a_end)
                        })

        system_instruction = (
            "# KP ASTROLOGY TIMING & DATE COUNSELOR\n"
            "You are an empathetic expert KP Astrologer.\n"
            "CRITICAL INSTRUCTION: You ALREADY HAVE the user's complete birth details (DOB, Birth Time, Coordinates) and active Dasha-Antardasha timeline in the context below.\n"
            "NEVER ask the user for their birth date, birth time, or running dasha. You already know their exact birth details.\n"
            "Answer follow-up questions directly in plain, friendly, structured English using their KP Sub-Lord significators and Dasha dates."
        )

        birth_date_str = f"{body.year}-{body.month:02d}-{body.day:02d}"
        birth_time_str = f"{body.hour:02d}:{body.minute:02d}"
        user_name = getattr(current_user, 'name', None) or (current_user.email.split('@')[0].title() if getattr(current_user, 'email', None) else 'User')

        context_prompt = (
            f"USER BIRTH DETAILS & CONTEXT:\n"
            f"- Name: {user_name}\n"
            f"- Birth Date (DOB): {birth_date_str}\n"
            f"- Birth Time: {birth_time_str}\n"
            f"- Coordinates: {body.latitude}, {body.longitude}\n"
            f"- Today's Date: {today_str}\n\n"
            f"KP ASTROLOGY COMPUTED DATA:\n"
            f"- Event Category: {body.event_category}\n"
            f"- Ascendant Sub Lord: {chart_data['ascendant']['sub_lord']}\n"
            f"- Ruling Planets: {json.dumps(chart_data['ruling_planets'])}\n"
            f"- Vimshottari Active & Upcoming Dasha Timeline:\n{json.dumps(upcoming_dashas, indent=2)}\n"
            f"- House Significators: {json.dumps(significators_data['house_significators'])}\n\n"
            f"USER QUESTION: {body.question}\n"
        )

        messages_payload = [{"role": "system", "content": system_instruction}]
        for msg in body.messages:
            if msg.get("role") in ["user", "assistant"]:
                messages_payload.append({"role": msg["role"], "content": msg["content"]})
        messages_payload.append({"role": "user", "content": context_prompt})

        provider_config = ProviderConfig(provider_name="bedrock", model_id=get_settings().bedrock_model_id, max_tokens=2048)
        provider = get_provider("bedrock")
        compiled_prompt = CompiledPrompt(
            messages=messages_payload,
            provider_config=provider_config,
            total_tokens_estimate=len(system_instruction) // 4 + len(context_prompt) // 4,
        )

        result = await provider.generate(compiled_prompt)
        return {
            "status": "success",
            "reply": result["content"]
        }

    except Exception as e:
        logger.error("kp_event_timing_chat_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"KP event timing chat failure: {str(e)}"
        )


@router.post("/kp/reading", summary="Generate Deep KP AI Life & Sub-Lord Reading in Plain English")
async def get_kp_general_reading(
    body: KPReadingRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Generates a comprehensive, deep KP Astrology Life & Sub-Lord reading in plain English.
    """
    try:
        chart_data = calculate_kp_chart(
            year=body.year,
            month=body.month,
            day=body.day,
            hour=body.hour,
            minute=body.minute,
            lat=body.latitude,
            lon=body.longitude,
            tz_offset_hours=body.timezone_offset
        )
        significators_data = calculate_kp_significators(chart_data)

        today_dt = datetime.now(dt_tz.utc)
        today_str = today_dt.strftime("%B %d, %Y")
        birth_date_str = f"{body.year}-{body.month:02d}-{body.day:02d}"
        birth_time_str = f"{body.hour:02d}:{body.minute:02d}"

        system_instruction = (
            "# KP (KRISHNAMURTI PADDHATI) ASTROLOGY DEEP LIFE READING\n"
            "You are a master KP Astrologer. Synthesize the user's KP Sub-Lord placements, Placidus house significators, and ruling planets into a deep, rich, plain-English life analysis.\n\n"
            "## MANDATORY STYLED SECTIONS (MARKDOWN):\n\n"
            "# 🌌 Comprehensive KP Sub-Lord & Life Purpose Analysis\n\n"
            "### 🌟 1. Core Life Purpose & Lagna Sub-Lord Activation\n"
            "Explain what the Ascendant Sub-Lord reveals about the user's core identity, aura, and life destiny in simple plain English.\n\n"
            "### 💼 2. Career, Wealth & Abundance Potential (Houses 2, 6, 10, 11)\n"
            "Analyze the user's 2nd house (Wealth), 6th house (Service/Work), 10th house (Profession), and 11th house (Gains) significators.\n\n"
            "### ❤️ 3. Relationships & Life Partnerships (Houses 2, 7, 11)\n"
            "Analyze the 7th house Sub-Lord and how it shapes soulmate connections and marriage timing.\n\n"
            "### 💪 4. True Core Strengths & KP Superpowers\n"
            "Detail 3 major innate strengths based on favorable planet significators.\n\n"
            "### ⚠️ 5. Areas to Work On & Hidden Cosmic Growth Lessons\n"
            "Highlight 2 potential challenges or karmic lessons to overcome.\n\n"
            "### 🔮 6. Key Guidance & Golden Principles for Success\n"
            "Provide 3 actionable, inspiring takeaways."
        )

        user_name = getattr(current_user, 'name', None) or (current_user.email.split('@')[0].title() if getattr(current_user, 'email', None) else 'User')

        user_message = (
            f"USER BIRTH DETAILS:\n"
            f"- Name: {user_name}\n"
            f"- Birth Date (DOB): {birth_date_str}\n"
            f"- Birth Time: {birth_time_str}\n"
            f"- Coordinates: {body.latitude}, {body.longitude}\n\n"
            f"KP BIRTH CHART DATA:\n"
            f"Ascendant Degree: {chart_data['ascendant']['formatted_degree']}\n"
            f"Ascendant Sign Lord: {chart_data['ascendant']['sign_lord']}, Star Lord: {chart_data['ascendant']['star_lord']}, Sub Lord: {chart_data['ascendant']['sub_lord']}\n"
            f"Ruling Planets: {json.dumps(chart_data['ruling_planets'])}\n\n"
            f"Planets & Sub-Lords:\n{json.dumps(chart_data['planets'])}\n\n"
            f"House Significators:\n{json.dumps(significators_data['house_significators'])}\n"
        )

        provider_config = ProviderConfig(provider_name="bedrock", model_id=get_settings().bedrock_model_id, max_tokens=4096)
        provider = get_provider("bedrock")
        compiled_prompt = CompiledPrompt(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ],
            provider_config=provider_config,
            total_tokens_estimate=len(system_instruction) // 4 + len(user_message) // 4,
        )

        result = await provider.generate(compiled_prompt)

        return {
            "status": "success",
            "chart": chart_data,
            "significators": significators_data,
            "reading": result["content"]
        }

    except Exception as e:
        logger.error("kp_reading_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"KP reading generation failure: {str(e)}"
        )


@router.post("/kp/chat", summary="Interactive KP AI Life Counselor Chat")
async def get_kp_general_chat(
    body: KPChatRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """
    Handles general interactive questions about the user's KP chart in plain English.
    """
    try:
        chart_data = calculate_kp_chart(
            year=body.year,
            month=body.month,
            day=body.day,
            hour=body.hour,
            minute=body.minute,
            lat=body.latitude,
            lon=body.longitude,
            tz_offset_hours=body.timezone_offset
        )
        significators_data = calculate_kp_significators(chart_data)

        today_dt = datetime.now(dt_tz.utc)
        today_str = today_dt.strftime("%B %d, %Y")

        birth_dt = datetime(body.year, body.month, body.day, body.hour, body.minute, tzinfo=dt_tz.utc)
        moon_lon = chart_data["planets"]["Moon"]["longitude"]
        dasha_timeline = calculate_vimshottari_dasha(moon_lon, birth_dt)

        upcoming_dashas = []
        for m_dasha in dasha_timeline:
            m_end = datetime.strptime(m_dasha["end"], "%Y-%m-%d").replace(tzinfo=dt_tz.utc)
            if m_end >= today_dt:
                for a_dasha in m_dasha.get("antardashas", []):
                    a_start = datetime.strptime(a_dasha["start"], "%Y-%m-%d").replace(tzinfo=dt_tz.utc)
                    a_end = datetime.strptime(a_dasha["end"], "%Y-%m-%d").replace(tzinfo=dt_tz.utc)
                    if a_end >= today_dt and len(upcoming_dashas) < 8:
                        upcoming_dashas.append({
                            "mahadasha": m_dasha["lord"].capitalize(),
                            "antardasha": a_dasha["lord"].capitalize(),
                            "start_date": a_dasha["start"],
                            "end_date": a_dasha["end"],
                            "is_currently_active": (a_start <= today_dt <= a_end)
                        })

        system_instruction = (
            "# KP ASTROLOGY LIFE COUNSELOR\n"
            "You are an empathetic, expert KP Astrologer.\n"
            "CRITICAL INSTRUCTION: You ALREADY HAVE the user's complete birth details (DOB, Birth Time, Coordinates) and active Dasha-Antardasha timeline in the context below.\n"
            "NEVER ask the user for their birth date, birth time, or running dasha. You already know their exact birth details.\n"
            "Answer follow-up questions directly in plain, friendly, structured English using their KP Sub-Lord significators and Dasha dates."
        )

        birth_date_str = f"{body.year}-{body.month:02d}-{body.day:02d}"
        birth_time_str = f"{body.hour:02d}:{body.minute:02d}"
        user_name = getattr(current_user, 'name', None) or (current_user.email.split('@')[0].title() if getattr(current_user, 'email', None) else 'User')

        context_prompt = (
            f"USER BIRTH DETAILS & CONTEXT:\n"
            f"- Name: {user_name}\n"
            f"- Birth Date (DOB): {birth_date_str}\n"
            f"- Birth Time: {birth_time_str}\n"
            f"- Coordinates: {body.latitude}, {body.longitude}\n"
            f"- Today's Date: {today_str}\n\n"
            f"KP ASTROLOGY COMPUTED DATA:\n"
            f"- Ascendant Sub Lord: {chart_data['ascendant']['sub_lord']}\n"
            f"- Ruling Planets: {json.dumps(chart_data['ruling_planets'])}\n"
            f"- Vimshottari Active & Upcoming Dasha Timeline:\n{json.dumps(upcoming_dashas, indent=2)}\n"
            f"- Planets Breakdown: {json.dumps(chart_data['planets'])}\n\n"
            f"USER QUESTION: {body.question}\n"
        )

        messages_payload = [{"role": "system", "content": system_instruction}]
        for msg in body.messages:
            if msg.get("role") in ["user", "assistant"]:
                messages_payload.append({"role": msg["role"], "content": msg["content"]})
        messages_payload.append({"role": "user", "content": context_prompt})

        provider_config = ProviderConfig(provider_name="bedrock", model_id=get_settings().bedrock_model_id, max_tokens=2048)
        provider = get_provider("bedrock")
        compiled_prompt = CompiledPrompt(
            messages=messages_payload,
            provider_config=provider_config,
            total_tokens_estimate=len(system_instruction) // 4 + len(context_prompt) // 4,
        )

        result = await provider.generate(compiled_prompt)

        return {
            "status": "success",
            "reply": result["content"]
        }

    except Exception as e:
        logger.error("kp_chat_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"KP chat failure: {str(e)}"
        )



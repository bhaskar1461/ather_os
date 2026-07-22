"""
Location Router

Geocoding endpoints for city search and timezone resolution.
These endpoints power the frontend autocomplete experience
so users never need to manually enter coordinates.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from packages.database.connection import get_db
from packages.database.models import User
from app.security.dependencies import get_current_user
from app.services.geocoding import get_geocoding_service, resolve_timezone

router = APIRouter(prefix="/location", tags=["Location"])


@router.get("/search", summary="Search cities by name with autocomplete")
async def search_locations(
    q: str = Query(..., min_length=2, max_length=200, description="City name or partial query"),
    limit: int = Query(5, ge=1, le=15, description="Maximum number of results"),
    current_user: User = Depends(get_current_user),
):
    """
    Searches for cities matching the query string using geocoding providers.
    Returns structured results including city, state, country, coordinates,
    and IANA timezone — ready for Swiss Ephemeris consumption.

    Supports fuzzy matching, partial names, and common misspellings.
    Results are cached in Redis for 24 hours.
    """
    service = get_geocoding_service()
    results = await service.search(q, limit)

    return {
        "query": q,
        "count": len(results),
        "results": [r.to_dict() for r in results],
    }


@router.get("/timezone", summary="Resolve IANA timezone from coordinates")
async def get_timezone(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude"),
    current_user: User = Depends(get_current_user),
):
    """
    Resolves the IANA timezone identifier for a given latitude/longitude pair.
    Uses offline timezonefinder — no external API call required.
    """
    tz = resolve_timezone(lat, lon)
    return {
        "latitude": lat,
        "longitude": lon,
        "timezone": tz,
    }

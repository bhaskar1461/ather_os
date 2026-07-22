"""
Location Resolution Engine — Geocoding Service

Provider-abstracted geocoding service that resolves city names into
latitude, longitude, IANA timezone, and geographic metadata.

Primary Provider:  OpenStreetMap Nominatim (free, no API key)
Fallback Provider: Komoot Photon (free, no API key)

All timezone resolution is performed offline via timezonefinder
to avoid additional network dependency.

Redis caching is used to minimize external API calls.
"""

import json
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional

import httpx
from timezonefinder import TimezoneFinder

from app.redis_manager import get_redis
from app.middleware.logging import get_logger

logger = get_logger("geocoding")

# Singleton timezone finder (loaded once, ~20MB memory, extremely fast lookups)
_tz_finder: Optional[TimezoneFinder] = None


def _get_tz_finder() -> TimezoneFinder:
    """Lazily initialize the TimezoneFinder singleton."""
    global _tz_finder
    if _tz_finder is None:
        _tz_finder = TimezoneFinder()
    return _tz_finder


def resolve_timezone(lat: float, lon: float) -> str:
    """
    Resolve IANA timezone string from geographic coordinates.
    Falls back to UTC if resolution fails.
    """
    try:
        tz = _get_tz_finder().timezone_at(lng=lon, lat=lat)
        return tz or "UTC"
    except Exception:
        return "UTC"


@dataclass
class GeoResult:
    """Structured geocoding result returned to clients."""
    city: str
    state: str
    country: str
    latitude: float
    longitude: float
    timezone: str
    display_name: str
    geo_id: str

    def to_dict(self) -> dict:
        return asdict(self)


# ── Abstract Provider ─────────────────────────────────────────────────────────

class AbstractGeoProvider(ABC):
    """Base class for all geocoding providers."""

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[GeoResult]:
        """Search for locations matching the query string."""
        ...


# ── Nominatim Provider (Primary) ──────────────────────────────────────────────

class NominatimProvider(AbstractGeoProvider):
    """
    OpenStreetMap Nominatim geocoding provider.
    Free, no API key required. Rate limit: 1 req/sec (respected via single-flight).
    """

    BASE_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "AetherOS-AstrologyEngine/1.0"

    async def search(self, query: str, limit: int = 5) -> list[GeoResult]:
        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": limit,
            "dedupe": 1,
            "accept-language": "en",
        }
        headers = {"User-Agent": self.USER_AGENT}

        async with httpx.AsyncClient(timeout=2.5) as client:
            response = await client.get(self.BASE_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

        results: list[GeoResult] = []
        seen_keys: set[str] = set()

        for item in data:
            lat = float(item.get("lat", 0))
            lon = float(item.get("lon", 0))
            addr = item.get("address", {})

            city = (
                addr.get("city")
                or addr.get("town")
                or addr.get("village")
                or addr.get("municipality")
                or addr.get("county")
                or item.get("name", "Unknown")
            )
            state = addr.get("state", "")
            country = addr.get("country", "")

            # Deduplicate by city+state+country
            dedup_key = f"{city}|{state}|{country}".lower()
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            timezone = resolve_timezone(lat, lon)

            parts = [p for p in [city, state, country] if p]
            display_name = ", ".join(parts)

            results.append(GeoResult(
                city=city,
                state=state,
                country=country,
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                timezone=timezone,
                display_name=display_name,
                geo_id=str(item.get("osm_id", "")),
            ))

        return results


# ── Photon Provider (Fallback) ────────────────────────────────────────────────

class PhotonProvider(AbstractGeoProvider):
    """
    Komoot Photon geocoding provider.
    Free, no API key required. Based on OpenStreetMap data.
    """

    BASE_URL = "https://photon.komoot.io/api/"
    USER_AGENT = "AetherOS-AstrologyEngine/1.0"

    async def search(self, query: str, limit: int = 5) -> list[GeoResult]:
        params = {
            "q": query,
            "limit": limit,
            "lang": "en",
        }
        headers = {"User-Agent": self.USER_AGENT}

        async with httpx.AsyncClient(timeout=2.5) as client:
            response = await client.get(self.BASE_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

        results: list[GeoResult] = []
        seen_keys: set[str] = set()

        for feature in data.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [0, 0])

            lon = float(coords[0])
            lat = float(coords[1])

            city = (
                props.get("city")
                or props.get("name")
                or props.get("county")
                or "Unknown"
            )
            state = props.get("state", "")
            country = props.get("country", "")

            dedup_key = f"{city}|{state}|{country}".lower()
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            timezone = resolve_timezone(lat, lon)

            parts = [p for p in [city, state, country] if p]
            display_name = ", ".join(parts)

            results.append(GeoResult(
                city=city,
                state=state,
                country=country,
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                timezone=timezone,
                display_name=display_name,
                geo_id=str(props.get("osm_id", "")),
            ))

        return results


# ── Geocoding Service Orchestrator ────────────────────────────────────────────

class GeocodingService:
    """
    High-level geocoding orchestrator with provider failover and Redis caching.

    Usage:
        service = GeocodingService()
        results = await service.search("Hyderabad")
    """

    CACHE_PREFIX = "geo:search:"
    CACHE_TTL_SECONDS = 86400  # 24 hours

    def __init__(
        self,
        primary: Optional[AbstractGeoProvider] = None,
        fallback: Optional[AbstractGeoProvider] = None,
    ):
        self.primary = primary or PhotonProvider()
        self.fallback = fallback or NominatimProvider()

    def _cache_key(self, query: str, limit: int) -> str:
        """Generate a deterministic Redis cache key."""
        normalized = query.strip().lower()
        hash_input = f"{normalized}:{limit}"
        digest = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        return f"{self.CACHE_PREFIX}{digest}"

    async def search(self, query: str, limit: int = 5) -> list[GeoResult]:
        """
        Search for locations matching the query.
        Checks Redis cache first, then tries primary provider,
        falls back to secondary on failure.
        """
        if not query or not query.strip():
            return []

        cache_key = self._cache_key(query, limit)

        # 1. Check Redis cache
        try:
            redis = get_redis()
            cached = await redis.get(cache_key)
            if cached:
                logger.info("geocoding_cache_hit", query=query)
                items = json.loads(cached)
                return [GeoResult(**item) for item in items]
        except Exception as e:
            logger.warning("geocoding_cache_read_error", error=str(e))

        # 2. Try primary provider
        results: list[GeoResult] = []
        try:
            results = await self.primary.search(query, limit)
            logger.info("geocoding_primary_success", query=query, count=len(results))
        except Exception as primary_err:
            logger.warning("geocoding_primary_failed", error=str(primary_err))

            # 3. Fallback provider
            try:
                results = await self.fallback.search(query, limit)
                logger.info("geocoding_fallback_success", query=query, count=len(results))
            except Exception as fallback_err:
                logger.error("geocoding_all_providers_failed",
                             primary_error=str(primary_err),
                             fallback_error=str(fallback_err))
                return []

        # 4. Cache successful results
        if results:
            try:
                redis = get_redis()
                serialized = json.dumps([r.to_dict() for r in results])
                await redis.set(cache_key, serialized, ex=self.CACHE_TTL_SECONDS)
            except Exception as e:
                logger.warning("geocoding_cache_write_error", error=str(e))

        return results


# ── Module-level convenience instance ─────────────────────────────────────────

_service: Optional[GeocodingService] = None


def get_geocoding_service() -> GeocodingService:
    """Returns a module-level singleton GeocodingService."""
    global _service
    if _service is None:
        _service = GeocodingService()
    return _service

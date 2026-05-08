"""
Cache utilities for API v2.

Provides functions for cache invalidation after data imports or updates.
Uses Django's cache framework (Redis in Docker, LocMemCache locally).
"""

import logging
from typing import Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache TTLs (seconds)
AGGREGATE_CACHE_TTL = 3600  # 1 hour for aggregate endpoints

# Known cache key patterns used by API views
CACHE_KEY_PATTERNS = {
    'actor_detail': 'actor_detail:{actor_id}',
    'funding_summary': 'funding_summary:{actor_id}',
    'activity_by_year': 'activity_by_year:{actor_id}',
    'meetings_summary': 'meetings_summary:{actor_id}',
    'homepage_stats': 'aggregate:homepage_stats:{params_hash}',
    'party_donations': 'aggregate:party_donations:{params_hash}',
    'top_lobbying_clients': 'aggregate:top_lobbying_clients:{params_hash}',
    'department_meetings': 'aggregate:department_meetings:{params_hash}',
}


def invalidate_actor(actor_id: int) -> int:
    """
    Invalidate all cached data for a specific actor.

    Call this after importing data that affects this actor (donations, meetings, etc.).
    Returns the number of keys deleted.
    """
    keys = [
        f'actor_detail:{actor_id}',
        f'funding_summary:{actor_id}',
        f'activity_by_year:{actor_id}',
        f'meetings_summary:{actor_id}',
        f'cross_connections:{actor_id}',
    ]
    deleted = cache.delete_many(keys)
    logger.info('Invalidated cache for actor %s (%s keys)', actor_id, len(keys))
    return len(keys)


def invalidate_actors(actor_ids: list[int]) -> int:
    """
    Invalidate cached data for multiple actors.

    Call this after bulk imports that affect many actors.
    Returns the number of keys deleted.
    """
    if not actor_ids:
        return 0

    keys = []
    for actor_id in actor_ids:
        keys.append(f'actor_detail:{actor_id}')
        keys.append(f'funding_summary:{actor_id}')
        keys.append(f'activity_by_year:{actor_id}')
        keys.append(f'meetings_summary:{actor_id}')
        keys.append(f'cross_connections:{actor_id}')

    cache.delete_many(keys)
    logger.info('Invalidated cache for %s actors (%s keys)', len(actor_ids), len(keys))
    return len(keys)


def make_aggregate_cache_key(prefix: str, query_params: dict) -> str:
    """
    Build a deterministic cache key from endpoint prefix and query parameters.

    Sorts params for consistency regardless of URL parameter order.
    """
    import hashlib
    sorted_params = '&'.join(
        f'{k}={v}' for k, v in sorted(query_params.items()) if v
    )
    params_hash = hashlib.md5(sorted_params.encode()).hexdigest()[:12]
    return f'aggregate:{prefix}:{params_hash}'


def invalidate_aggregate_caches() -> None:
    """
    Invalidate all aggregate endpoint caches.

    Call this after data imports that affect homepage stats, party donations, etc.
    """
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection('default')
        keys = conn.keys('uti:1:aggregate:*')
        if keys:
            conn.delete(*keys)
            logger.info('Invalidated %s aggregate cache keys', len(keys))
    except ImportError:
        cache.clear()
        logger.info('Cleared entire cache (no Redis pattern support)')
    except Exception as e:
        cache.clear()
        logger.warning('Aggregate cache clear fallback due to: %s', e)


def invalidate_all_actor_caches() -> None:
    """
    Invalidate ALL actor-related caches.

    Use this after large bulk imports where tracking individual IDs is impractical.
    With django-redis, this uses key pattern deletion. With LocMemCache, it clears
    the entire cache (acceptable for development).
    """
    try:
        # django-redis supports key pattern deletion
        from django_redis import get_redis_connection
        conn = get_redis_connection('default')
        # Match all actor-related keys with the configured prefix
        patterns = ['uti:1:actor_detail:*', 'uti:1:funding_summary:*', 'uti:1:activity_by_year:*', 'uti:1:meetings_summary:*', 'uti:1:cross_connections:*']
        total_deleted = 0
        for pattern in patterns:
            keys = conn.keys(pattern)
            if keys:
                total_deleted += conn.delete(*keys)
        logger.info('Invalidated all actor caches (%s keys via Redis pattern)', total_deleted)
    except ImportError:
        # Not using django-redis — clear entire cache
        cache.clear()
        logger.info('Cleared entire cache (no Redis pattern support)')
    except Exception as e:
        # Redis unavailable — clear what we can
        cache.clear()
        logger.warning('Cache clear fallback due to: %s', e)


def warm_actor_cache(actor_id: int) -> Optional[dict]:
    """
    Pre-warm the cache for a specific actor by triggering the expensive queries.

    Useful after imports to avoid cold-cache penalties on first page load.
    Returns the cached data, or None if the actor doesn't exist.
    """
    from api.v2.views import FundingSummaryView, ActorDetailView
    from rest_framework.test import APIRequestFactory

    factory = APIRequestFactory()

    # Warm funding summary
    request = factory.get(f'/api/v2/actors/{actor_id}/funding-summary/?bust_cache=1')
    view = FundingSummaryView.as_view()
    response = view(request, pk=actor_id)

    if response.status_code == 200:
        logger.info('Warmed cache for actor %s', actor_id)
        return response.data

    return None

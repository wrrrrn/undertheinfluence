"""
Profiling utilities for API v2 endpoints.

Usage:
    from api.v2.profiling import profile_view

    @profile_view
    def my_view(request):
        ...
"""

import time
import logging
from functools import wraps
from django.db import connection, reset_queries

logger = logging.getLogger(__name__)


def profile_view(func):
    """
    Decorator to profile view performance including query count and timing.

    Logs:
    - Total request time
    - Number of database queries
    - Time spent in queries
    - Time spent in Python/serialization
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Reset query log
        reset_queries()

        # Time the view
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()

        # Calculate metrics
        total_time = end - start
        num_queries = len(connection.queries)
        query_time = sum(float(q['time']) for q in connection.queries)
        python_time = total_time - query_time

        # Log results
        logger.info(
            f"View {func.__name__}: "
            f"total={total_time:.3f}s, "
            f"queries={num_queries}, "
            f"db={query_time:.3f}s, "
            f"python={python_time:.3f}s"
        )

        # Also print for debugging
        print(f"\n=== PROFILING: {func.__name__} ===")
        print(f"Total time: {total_time:.3f}s")
        print(f"Database: {query_time:.3f}s ({num_queries} queries)")
        print(f"Python: {python_time:.3f}s")
        print(f"DB %: {query_time/total_time*100:.1f}%")

        if num_queries > 10:
            print(f"\n⚠️  High query count: {num_queries} queries")
            print("\nTop 5 slowest queries:")
            sorted_queries = sorted(connection.queries, key=lambda q: float(q['time']), reverse=True)
            for i, q in enumerate(sorted_queries[:5], 1):
                print(f"{i}. {q['time']}s - {q['sql'][:100]}...")

        return result

    return wrapper


def profile_queryset(qs, description="Queryset"):
    """
    Profile a queryset execution.

    Usage:
        qs = Donation.objects.filter(...)
        profile_queryset(qs, "Top donors query")
    """
    reset_queries()
    start = time.time()

    # Force evaluation
    list(qs)

    end = time.time()
    total_time = end - start
    num_queries = len(connection.queries)
    query_time = sum(float(q['time']) for q in connection.queries)

    print(f"\n=== PROFILING: {description} ===")
    print(f"Total time: {total_time:.3f}s")
    print(f"Queries: {num_queries}")
    print(f"DB time: {query_time:.3f}s")

    for i, q in enumerate(connection.queries, 1):
        print(f"\n{i}. {q['time']}s")
        print(f"   {q['sql'][:200]}...")

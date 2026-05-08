"""
Pagination classes for API v2

Provides custom pagination for aggregate endpoints and detail listings.
"""

from rest_framework.pagination import LimitOffsetPagination


class AggregatePagination(LimitOffsetPagination):
    """
    Pagination for aggregate endpoints.

    Defaults to 100 items per page for aggregate results.
    Allows clients to adjust via ?limit= parameter.
    """
    default_limit = 100
    max_limit = 500


class DetailPagination(LimitOffsetPagination):
    """
    Pagination for detail listings (donations, consultancies, etc.).

    Defaults to 50 items per page for detailed results.
    Uses a capped count to avoid expensive COUNT(*) on large tables.
    """
    default_limit = 50
    max_limit = 200
    COUNT_CAP = 5000

    def get_count(self, queryset):
        """Avoid full COUNT(*) on large result sets by using a bounded check."""
        try:
            # Check if there are more than COUNT_CAP rows cheaply
            bounded = queryset.values('pk')[:self.COUNT_CAP + 1].count()
            if bounded > self.COUNT_CAP:
                # Use EXPLAIN estimate instead of full count
                return self._get_estimated_count(queryset)
            return bounded
        except Exception:
            return super().get_count(queryset)

    def _get_estimated_count(self, queryset):
        """Use PostgreSQL EXPLAIN to estimate row count."""
        from django.db import connection
        try:
            sql, params = queryset.query.sql_with_params()
            with connection.cursor() as cursor:
                cursor.execute(f"EXPLAIN (FORMAT JSON) {sql}", params)
                plan = cursor.fetchone()[0]
                if isinstance(plan, list) and plan:
                    return int(plan[0].get('Plan', {}).get('Plan Rows', 0))
        except Exception:
            pass
        return self.COUNT_CAP

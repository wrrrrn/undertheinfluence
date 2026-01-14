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
    """
    default_limit = 50
    max_limit = 200

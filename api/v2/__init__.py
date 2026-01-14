"""
API v2 - Analysis-First API for UnderTheInfluence

This module provides aggregate endpoints and temporal query support for
political influence analysis.

Key Features:
- Aggregate endpoints for top donors, recipients, party donations
- Temporal queries with ?at_date= parameter
- Canonical field resolution for merged actors
- Comprehensive filtering with django-filter
- Redis caching for performance
- OpenAPI/Swagger documentation

Version: 2.0.0
"""

__version__ = '2.0.0'

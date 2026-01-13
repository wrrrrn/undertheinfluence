# Multi-stage Dockerfile for UnderTheInfluence Django application
# Using Python 3.7 for compatibility with current Django 1.11 + Wagtail 2.0 stack
# Will upgrade to Python 3.11+ in Phase 2.5 after Django 5.1 upgrade
FROM python:3.7-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    gettext \
    zlib1g-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project files
COPY . /app/

# Collect static files (will run in production)
# RUN python manage.py collectstatic --noinput

# Create data directory for cached imports
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Run gunicorn in production, runserver in development
CMD ["gunicorn", "undertheinfluence.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

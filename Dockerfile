# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create entrypoint script
RUN echo '#!/bin/bash\nuvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Expose the port
EXPOSE 8000

# Command to run the application
CMD ["/app/entrypoint.sh"] 
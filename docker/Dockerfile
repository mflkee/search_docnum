# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies via uv
RUN pip install --no-cache-dir uv

COPY requirements/base.txt /app/requirements/base.txt
RUN uv pip install --system --no-cache -r requirements/base.txt

# Copy project
COPY . /app/

# Create necessary directories
RUN mkdir -p uploads results logs

# Expose port
EXPOSE 8000

# Run the application through uv (ensures consistent environment)
CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

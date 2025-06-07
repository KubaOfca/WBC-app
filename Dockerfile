# Use slim Python base image
FROM python:3.10-slim

# Set environment variables early to prevent prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies in jednej warstwie
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements separately for caching
COPY requirement.txt .

# Upgrade pip + install Python dependencies
RUN pip install --upgrade pip \
    && pip install -r requirement.txt --no-cache-dir

# Copy rest of the app
COPY . .

# Flask env
ENV FLASK_APP=main
EXPOSE 5000

# Run the app
CMD ["python", "main.py"]

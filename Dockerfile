# Use Python 3.13 as the base image (alpine for slimness)
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port for FastAPI
EXPOSE 8000

# Default command (can be overridden in ECS)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

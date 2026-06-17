# Use official Python slim image for small footprint and security
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set working directory
WORKDIR /app

# Install system dependencies (optional, but good for potential package builds)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy application source code
COPY ./app ./app
COPY ./deploy.sh ./deploy.sh

# Ensure deploy.sh is executable
RUN chmod +x ./deploy.sh

# Create a non-privileged user for security best practices (avoid running as root)
RUN useradd -u 8888 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run FastAPI app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

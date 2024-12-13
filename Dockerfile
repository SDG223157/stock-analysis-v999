FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV FLASK_APP=app
ENV FLASK_ENV=production
ENV PORT=3000

# Expose port
EXPOSE 3000

# Start Gunicorn
CMD gunicorn --bind 0.0.0.0:3000 "app:create_app()"

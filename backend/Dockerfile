# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies with cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt \
    && find /usr/local/lib/python3.9/site-packages -type d -name "tests" -exec rm -rf {} + \
    && find /usr/local/lib/python3.9/site-packages -type d -name "__pycache__" -exec rm -rf {} +

# Copy application code
COPY . .

# Expose port
EXPOSE 9001

# Command to run the application
CMD ["python", "main.py"]
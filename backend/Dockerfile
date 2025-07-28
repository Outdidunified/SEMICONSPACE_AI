# Multi-stage build to reduce final image size
FROM python:3.9-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Install packages to a temporary directory
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final stage
FROM python:3.9-slim
WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /install /usr/local
COPY . .

# Clean up Python cache
RUN find /usr/local/lib/python3.9/site-packages -type d -name "tests" -exec rm -rf {} + \
    && find /usr/local/lib/python3.9/site-packages -type d -name "__pycache__" -exec rm -rf {} + \
    && rm -rf /root/.cache/pip

EXPOSE 9001
CMD ["python", "main.py"]
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (use Aliyun mirror)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies (use CPU-only torch for Docker)
RUN pip install --no-cache-dir --timeout 1000 torch --index-url https://download.pytorch.org/whl/cpu && \
    sed -i '/^torch/d' requirements.txt && \
    pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --timeout 1000 -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data/files

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

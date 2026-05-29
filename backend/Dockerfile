FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (e.g. gcc if psycopg2 is used instead of psycopg2-binary, though usually standard)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port 8000
EXPOSE 8000

# Run uvicorn server
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

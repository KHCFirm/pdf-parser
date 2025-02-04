# Use Python with Google Cloud SDK pre-installed
FROM python:3.9

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libsm6 \
    libxrender1 \
    libxext6 && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8080

# Start the Flask app with Gunicorn, listening on port 8080
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]

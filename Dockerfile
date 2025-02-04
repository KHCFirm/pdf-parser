# Use Python base image
FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV TESSDATA_PREFIX="/usr/share/tesseract-ocr/4.00/tessdata/"
ENV TESSERACT_CMD="/usr/bin/tesseract"

# Expose the port for Google Cloud Run
EXPOSE 8080

# Start the app using Gunicorn
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8080", "app:app"]

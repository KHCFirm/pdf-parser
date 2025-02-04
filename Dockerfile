# Use an official Python image with Debian-based OS
FROM python:3.9-slim

# Set environment variables to ensure non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies and Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Verify Tesseract installation
RUN tesseract --version

# Ensure tessdata exists and explicitly download eng.traineddata
RUN mkdir -p /usr/share/tesseract-ocr/4.00/tessdata/ \
    && wget -P /usr/share/tesseract-ocr/4.00/tessdata/ https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata

# Set Tesseract environment variables
ENV TESSDATA_PREFIX="/usr/share/tesseract-ocr/4.00/tessdata/"
ENV TESSERACT_CMD="/usr/bin/tesseract"

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the app port
EXPOSE 5000

# Start the Flask app with Gunicorn (better performance than `python app.py`)
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]

# Use Python 3.9 slim (small image)
FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set Tesseract environment variables
ENV TESSDATA_PREFIX="/usr/share/tesseract-ocr/4.00/tessdata/"
ENV TESSERACT_CMD="/usr/bin/tesseract"

# Expose port
EXPOSE 5000

# Start the app
CMD ["gunicorn", "-w", "2", "-t", "300", "-b", "0.0.0.0:5000", "app:app"]

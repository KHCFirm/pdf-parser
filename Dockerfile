# Use Python slim image
FROM python:3.9-slim

# Install system dependencies including Tesseract
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    wget \
    && rm -rf /var/lib/apt/lists/*

# ✅ Manually Download Tesseract Trained Data (`eng.traineddata`)
RUN mkdir -p /usr/share/tesseract-ocr/4.00/tessdata/ && \
    wget -O /usr/share/tesseract-ocr/4.00/tessdata/eng.traineddata \
    https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata

# ✅ Ensure correct environment variables
ENV TESSDATA_PREFIX="/usr/share/tesseract-ocr/4.00/tessdata/"
ENV TESSERACT_CMD="/usr/bin/tesseract"

# Set working directory
WORKDIR /app

# Copy all project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Test if Tesseract is installed correctly
RUN tesseract --version && ls -lah $TESSDATA_PREFIX

# ✅ Verify traineddata file exists
RUN test -f /usr/share/tesseract-ocr/4.00/tessdata/eng.traineddata || echo "TESSERACT DATA MISSING"

# Expose the port for Google Cloud Run
EXPOSE 8080

# Run the app
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8080", "app:app"]

# Use Python slim image
FROM python:3.9-slim

# Install system dependencies (including Tesseract OCR)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    wget \
    && rm -rf /var/lib/apt/lists/*

# ✅ Create the correct Tesseract directory manually
RUN mkdir -p /usr/share/tessdata/

# ✅ Download the traineddata file into the correct directory
RUN wget -O /usr/share/tessdata/eng.traineddata \
    https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata

# ✅ Set environment variables so Tesseract finds the traineddata file
ENV TESSDATA_PREFIX="/usr/share/tessdata/"
ENV TESSERACT_CMD="/usr/bin/tesseract"

# Set working directory
WORKDIR /app

# Copy all project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Verify traineddata file exists before running the app
RUN test -f /usr/share/tessdata/eng.traineddata || echo "TESSERACT DATA MISSING"

# ✅ Print Tesseract version for debugging
RUN tesseract --version && ls -lah $TESSDATA_PREFIX

# Expose the port for Google Cloud Run
EXPOSE 8080

# Run the app
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8080", "app:app"]

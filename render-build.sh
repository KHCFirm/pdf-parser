#!/bin/bash

# Install Tesseract OCR
apt-get update && apt-get install -y tesseract-ocr libtesseract-dev

# Install Python dependencies
pip install -r requirements.txt
